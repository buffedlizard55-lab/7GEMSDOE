import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from spatial_validation import fold_windows, split_fold, masked_components, match_mass, policies
from structural_prior import structural_geometry
from metric import dtvi_components


def test_windows_partition_odd_grid():
    count=np.zeros((103,107),int)
    for y0,y1,x0,x1 in fold_windows(count.shape): count[y0:y1,x0:x1]+=1
    assert (count==1).all()


def test_whole_crossing_trace_purged_and_buffer():
    truth=np.zeros((120,120),bool); valid=np.ones_like(truth)
    truth[40,5:110]=1 # crosses fold, must remove entire component
    truth[95,90:100]=1 # independent visible trace
    truth[65,10:20]=1 # in 10-pixel buffer, must remove
    visible, hidden, _, score, meta=split_fold(truth,valid,(0,60,0,60))
    assert not visible[40].any() and not visible[65].any()
    assert visible[95,95] and hidden[40,30]
    assert not (visible & score).any()
    assert meta['excluded_components']==2
    assert not score[:3].any() and not score[:,:3].any()


def test_masked_metric_matches_full_metric():
    rng=np.random.default_rng(2)
    p=rng.random((13,17)); g=rng.random((13,17))>.9
    a=masked_components(p,g,np.ones_like(g)); b=dtvi_components(p,g)
    for k,v in b.items(): assert a[k]==pytest.approx(v)


def test_metric_keeps_context_and_charges_only_score():
    p=np.zeros((9,9)); g=np.zeros_like(p,bool); mask=g.copy()
    mask[4,4]=1; g[4,4]=1; p[4,3]=1
    out=masked_components(p,g,mask)
    assert out['TP_w']==pytest.approx(2/3)
    assert out['FP_w']==0 and out['predicted_mass']==0
    g[:]=False; g[4,3]=1; p[:]=0; p[4,4]=1
    out=masked_components(p,g,mask)
    assert out['dti'] is None and out['FP_w']==pytest.approx(1/3)


@pytest.mark.parametrize('bad',[-.01,1.01,np.inf,np.nan])
def test_invalid_prediction(bad):
    with pytest.raises(ValueError): masked_components(np.array([[bad]]),[[1]],[[1]])


def test_mass_matching_zero_and_nonzero():
    a=np.array([[.2,.5],[.3,.7]],dtype=np.float32); b=a/3
    mask=np.array([[1,0],[1,1]],bool)
    x,y=match_mass(a,b,mask)
    assert x[mask].sum()==pytest.approx(y[mask].sum())
    assert np.all(x<=a) and np.all(y<=b)
    x,y=match_mass(a,b*0,mask)
    assert not x.any() and not y.any()


def test_null_reproducibility_and_preserves_geometry():
    visible=np.zeros((70,70),bool); visible[35,25:45]=1
    a=structural_geometry(visible); b=structural_geometry(visible,random_seed=3)
    c=structural_geometry(visible,random_seed=3)
    for x,y in zip(b,c): np.testing.assert_array_equal(x,y)
    np.testing.assert_array_equal(a[0],b[0]); np.testing.assert_array_equal(a[3],b[3])
    assert not np.allclose(a[1],b[1])


def test_no_visible_faults_returns_zero_not_crash():
    z=np.zeros((20,20),bool)
    assert all(not p.any() for p in policies(z,~z,1).values())


def test_report_has_every_policy_in_every_fold():
    import json
    report=json.loads((Path(__file__).resolve().parents[1]/'knowledge/session3/spatial_experiment.json').read_text())
    for name, agg in report['aggregates'].items():
        assert agg['scored_folds']==4
        assert len([r for r in report['rows'] if r['policy']==name])==4
    for fold in range(4):
        rows={r['policy']:r for r in report['rows'] if r['fold']==fold}
        for control in ['isotropic15','random_tangent','random_tangent_2','random_tangent_3']:
            assert rows['strike_matched_to_'+control]['predicted_mass']==pytest.approx(rows[control+'_matched']['predicted_mass'],abs=1e-5)


def test_expert_training_excludes_hidden_system_and_samples_no_duplicates():
    from spatial_experts import training_mask, sample_training
    truth=np.zeros((120,120),bool); valid=np.ones_like(truth)
    truth[40,5:110]=1; truth[95,90:100]=1
    allowed=training_mask(truth,valid,(0,60,0,60))
    assert not allowed[:70,:70].any()
    assert not allowed[40,5:110].any()
    assert allowed[95,95]
    ids,y=sample_training(truth,allowed,7)
    assert allowed.ravel()[ids].all() and len(np.unique(ids))==len(ids)
    np.testing.assert_array_equal(y,truth.ravel()[ids])
    ids2,y2=sample_training(truth,allowed,7)
    np.testing.assert_array_equal(ids,ids2)
    with pytest.raises(ValueError): sample_training(truth,np.zeros_like(valid),7)


def test_hardening_arbitrary_false_positive_can_reduce_dti():
    from metric import dtvi
    truth=np.zeros((15,15),bool);truth[2,2]=True
    p=np.zeros_like(truth,dtype=float);p[2,2]=1;p[12,12]=.1
    before=dtvi(p,truth);p[12,12]=1
    assert dtvi(p,truth)<before


def test_grid_mismatch_fails_closed():
    from types import SimpleNamespace
    from spatial_validation import assert_same_grid
    a=SimpleNamespace(shape=(2,2),crs='EPSG:32611',transform=(1,0,0,0,-1,0))
    assert_same_grid(a,a)
    for field,value in [('shape',(3,2)),('crs','EPSG:26911'),('transform',(1,0,1,0,-1,0))]:
        b=SimpleNamespace(**vars(a));setattr(b,field,value)
        with pytest.raises(ValueError,match='grid mismatch'): assert_same_grid(a,b)
