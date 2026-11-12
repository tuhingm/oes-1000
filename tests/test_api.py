import json
import pandas as pd
import pytest
from oes1000.api import estimate_csv, estimate_frame

def test_frame_adapter_runs_ols_and_reports_complete_cases():
    frame = pd.DataFrame({"y":[1,3,5,7,9],"x":[0,1,2,3,4]})
    out = estimate_frame(frame,"ols",{"dependent":"y","regressors":["x"]})
    assert out["nobs"] == 5
    assert out["params"] == pytest.approx([1,2])
    assert out["nobs_dropped"] == 0

def test_csv_adapter_returns_strict_json_and_supports_quantile_options():
    raw = estimate_csv("y,x\n1,0\n3,1\n5,2\n7,3\n9,4\n","quantile_regression",
        json.dumps({"dependent":"y","regressors":["x"],"quantile":0.5}))
    out = json.loads(raw)
    assert out["params"] == pytest.approx([1,2])
    assert out["quantile"] == 0.5

def test_wls_requires_positive_weight_column():
    frame = pd.DataFrame({"y":[1,2,3,4],"x":[1,2,3,4],"w":[1,0,1,1]})
    with pytest.raises(ValueError,match="strictly positive"):
        estimate_frame(frame,"wls",{"dependent":"y","regressors":["x"],"weights":"w"})

def test_gls_does_not_infer_covariance_matrix():
    frame = pd.DataFrame({"y":[1,2,3,4],"x":[1,2,3,4]})
    with pytest.raises(ValueError,match="explicit"):
        estimate_frame(frame,"gls",{"dependent":"y","regressors":["x"]})
