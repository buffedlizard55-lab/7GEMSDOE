import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from dem_pilot import scarp_features


def test_flat_dem_does_not_emit_nodata_edges():
    z=np.ones((256,256),dtype='float32')*100
    valid=np.ones(z.shape,dtype=bool); valid[100:110,100:110]=False
    z[~valid]=-9999
    edge,safe=scarp_features(z,valid)
    assert np.max(edge[safe]) == 0
    assert not safe[105,105] and not safe[0].any()
    assert np.isnan(edge[~safe]).all()
