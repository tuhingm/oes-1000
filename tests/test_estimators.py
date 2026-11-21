import numpy as np
import pandas as pd
import pytest
from engine.estimators import estimate_frame


def test_ols_recovers_linear_coefficients():
    x = np.arange(1., 31.)
    frame = pd.DataFrame({"y": 2.0 + 3.0*x + np.sin(x)*0.01, "x": x})
    result = estimate_frame(frame, "ols_hc3", {"outcome": "y", "predictors": ["x"]})
    coef = {r["term"]: r["estimate"] for r in result["coefficients"]}
    assert abs(coef["x"] - 3.0) < 0.002
    assert abs(coef["const"] - 2.0) < 0.03


def test_entity_fixed_effects_within_estimator():
    frame = pd.DataFrame({"id": [1,1,1,2,2,2,3,3,3], "x": [1,2,3,2,3,4,4,5,6], "y": [12,14,16,23,25,27,34,36,38]})
    result = estimate_frame(frame, "entity_fe", {"outcome": "y", "predictors": ["x"], "entity": "id"})
    assert abs(result["coefficients"][0]["estimate"] - 2.0) < 1e-8
    assert result["summary"]["entities"] == 3


def test_logit_binary_outcome():
    x = np.linspace(-2, 2, 200)
    y = (x + 0.2*np.sin(np.arange(200)) > 0).astype(int)
    frame = pd.DataFrame({"y": y, "x": x})
    result = estimate_frame(frame, "logit", {"outcome": "y", "predictors": ["x"]})
    assert result["summary"]["converged"] is True
    assert result["coefficients"][1]["estimate"] > 0


def test_entity_fe_requires_entity_id():
    frame = pd.DataFrame({"y": [1.,2.,3.,4.], "x": [1.,2.,3.,4.]})
    with pytest.raises(ValueError):
        estimate_frame(frame, "entity_fe", {"outcome": "y", "predictors": ["x"]})
