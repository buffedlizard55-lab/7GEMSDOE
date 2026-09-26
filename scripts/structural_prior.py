"""H3: local fault-tangent continuation, not a geothermal discovery claim.

PCA is fitted ONLY to visible catalogue coordinates inside a 500 m radius.
Nearest-source ellipses follow that tangent; junctions with low anisotropy emit
only a short isotropic halo. No hidden labels enter feature construction.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree


def structural_geometry(visible, radius=5, random_seed=None):
    visible = np.asarray(visible, dtype=bool)
    if visible.ndim != 2 or not visible.any():
        raise ValueError("visible must be a nonempty 2D fault mask")
    points = np.argwhere(visible)
    tree = cKDTree(points)
    angle = np.zeros(visible.shape, dtype=np.float32)
    coherent = np.zeros(visible.shape, dtype=bool)
    for point, neighbors in zip(points, tree.query_ball_point(points, radius)):
        if len(neighbors) < 3:
            continue
        xy = points[neighbors].astype(float)
        xy -= xy.mean(axis=0)
        eigenvalues, axes = np.linalg.eigh(xy.T @ xy / len(xy))
        y, x = point
        if eigenvalues[1] > 0 and (eigenvalues[1] - eigenvalues[0]) / eigenvalues.sum() >= .6:
            angle[y, x] = np.arctan2(axes[0, 1], axes[1, 1])
            coherent[y, x] = True
    # Null ablation: replace source tangents, preserving source/coherence/support.
    # One angle per source (not per target pixel) keeps each emitted ellipse coherent.
    if random_seed is not None:
        angle[visible] = np.random.default_rng(random_seed).uniform(0, np.pi, len(points))
    dist, nearest = distance_transform_edt(~visible, return_indices=True)
    theta = angle[tuple(nearest)]
    yy, xx = np.ogrid[:visible.shape[0], :visible.shape[1]]
    dy, dx = yy - nearest[0], xx - nearest[1]
    along = np.abs(dy * np.sin(theta) + dx * np.cos(theta)).astype('float32')
    cross = np.abs(dy * np.cos(theta) - dx * np.sin(theta)).astype('float32')
    return dist.astype('float32'), along, cross, coherent[tuple(nearest)]


def prior(visible, geometry, along_radius=15, cross_radius=3, height=.6):
    if min(along_radius, cross_radius) <= 0 or not 0 <= height <= 1:
        raise ValueError("positive radii and height in [0,1] required")
    dist, along, cross, coherent = geometry
    ellipse = np.hypot(along / along_radius, cross / cross_radius)
    scaled = np.where(coherent, ellipse, dist / cross_radius)
    field = (height * np.maximum(1 - scaled, 0)).astype('float32')
    field[visible] = .95
    return field
