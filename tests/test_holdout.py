import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import tune_policy


def test_hidden_truth_cannot_change_training_sample(monkeypatch):
    selected=[]
    class Recorder:
        def __init__(self, **kwargs): pass
        def fit(self,X,y): selected.append((X.copy(),y.copy()))
    monkeypatch.setattr(tune_policy,'HistGradientBoostingClassifier',Recorder)
    shape=(90,90)
    valid=np.ones(shape,dtype=bool)
    truth=np.zeros(shape,dtype=bool); truth[10,10:30]=True; truth[65,60:70]=True
    held=np.zeros(shape,dtype=bool); held[55:80,55:80]=True
    X=np.arange(np.prod(shape)).reshape(-1,1)
    rows=X.ravel()
    tune_policy.train_blind(X,valid,truth,held,rows,42)
    truth[held]=False
    tune_policy.train_blind(X,valid,truth,held,rows,42)
    np.testing.assert_array_equal(selected[0][0],selected[1][0])
    np.testing.assert_array_equal(selected[0][1],selected[1][1])
    assert not held.ravel()[selected[0][0].ravel()].any()
