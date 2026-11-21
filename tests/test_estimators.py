import json

import numpy as np
import pandas as pd
import pytest

from engine.estimators import estimate_frame, estimate_json


def _coefficient_map(result):
    return {row["term"]: row for row in result["coefficients"]}


def test_ols_recovers_linear_coefficients():
    x = np.arange(1.0, 31.0)
    frame = pd.DataFrame({"y": 2.0 + 3.0 * x + np.sin(x) * 0.01, "x": x})
    result = estimate_frame(frame, "ols_hc3", {"outcome": "y", "predictors": ["x"]})
    coef = _coefficient_map(result)
    assert abs(coef["x"]["estimate"] - 3.0) < 0.002
    assert abs(coef["const"]["estimate"] - 2.0) < 0.03


def test_ols_hc3_standard_errors_match_independent_sandwich_calculation():
    x = np.array([0.2, 0.7, 1.1, 1.8, 2.4, 3.2, 4.1, 5.3], dtype=float)
    y = np.array([1.1, 1.4, 2.0, 2.6, 3.1, 4.0, 4.2, 5.8], dtype=float)
    frame = pd.DataFrame({"y": y, "x": x})

    result = estimate_frame(frame, "ols_hc3", {"outcome": "y", "predictors": ["x"]})
    observed = _coefficient_map(result)

    design = np.column_stack([np.ones(len(x)), x])
    bread = np.linalg.inv(design.T @ design)
    beta = bread @ design.T @ y
    residuals = y - design @ beta
    leverage = np.einsum("ij,jk,ik->i", design, bread, design)
    adjusted = residuals / (1.0 - leverage)
    meat = design.T @ (design * (adjusted**2)[:, None])
    covariance = bread @ meat @ bread
    expected_se = np.sqrt(np.diag(covariance))

    assert observed["const"]["estimate"] == pytest.approx(beta[0], abs=1e-10)
    assert observed["x"]["estimate"] == pytest.approx(beta[1], abs=1e-10)
    assert observed["const"]["std_error"] == pytest.approx(expected_se[0], rel=1e-10)
    assert observed["x"]["std_error"] == pytest.approx(expected_se[1], rel=1e-10)


def test_ols_rejects_perfect_multicollinearity():
    x = np.arange(1.0, 21.0)
    frame = pd.DataFrame({"y": 1.0 + x, "x1": x, "x2": 2.0 * x})
    with pytest.raises(ValueError, match="rank deficient"):
        estimate_frame(
            frame,
            "ols_hc3",
            {"outcome": "y", "predictors": ["x1", "x2"]},
        )


def test_entity_fixed_effects_within_estimator():
    frame = pd.DataFrame(
        {
            "id": [1, 1, 1, 2, 2, 2, 3, 3, 3],
            "x": [1, 2, 3, 2, 3, 4, 4, 5, 6],
            "y": [12, 14, 16, 23, 25, 27, 34, 36, 38],
        }
    )
    result = estimate_frame(
        frame,
        "entity_fe",
        {"outcome": "y", "predictors": ["x"], "entity": "id"},
    )
    assert abs(result["coefficients"][0]["estimate"] - 2.0) < 1e-8
    assert result["summary"]["entities"] == 3


def test_entity_fe_rejects_collinearity_after_within_transformation():
    x = np.tile([1.0, 2.0, 3.0], 3)
    ids = np.repeat([1, 2, 3], 3)
    frame = pd.DataFrame(
        {"id": ids, "x1": x, "x2": 2.0 * x, "y": 2.0 * x + ids}
    )
    with pytest.raises(ValueError, match="rank deficient"):
        estimate_frame(
            frame,
            "entity_fe",
            {"outcome": "y", "predictors": ["x1", "x2"], "entity": "id"},
        )


def test_logit_binary_outcome():
    x = np.linspace(-2, 2, 200)
    y = (x + 0.2 * np.sin(np.arange(200)) > 0).astype(int)
    frame = pd.DataFrame({"y": y, "x": x})
    result = estimate_frame(frame, "logit", {"outcome": "y", "predictors": ["x"]})
    assert result["summary"]["converged"] is True
    assert result["coefficients"][1]["estimate"] > 0


def test_non_fe_estimator_does_not_drop_rows_for_missing_unused_entity():
    frame = pd.DataFrame(
        {
            "id": ["a", "a", "b", "b", None],
            "x": [1.0, 2.0, 3.0, 4.0, 5.0],
            "y": [2.0, 4.0, 6.0, 8.0, 10.0],
        }
    )
    result = estimate_frame(
        frame,
        "ols_hc3",
        {"outcome": "y", "predictors": ["x"], "entity": "id"},
    )
    assert result["summary"]["nobs"] == 5


def test_fe_complete_cases_include_nonmissing_entity_identifier():
    csv_text = (
        "id,x,y\n"
        "a,1,2\n"
        "a,2,4\n"
        "b,1,5\n"
        "b,2,7\n"
        ",3,9\n"
    )
    result = json.loads(
        estimate_json(
            csv_text,
            "entity_fe",
            json.dumps(
                {"outcome": "y", "predictors": ["x"], "entity": "id"}
            ),
        )
    )
    assert result["summary"]["nobs"] == 4
    assert result["specification"]["complete_cases"] == 4


def test_entity_fe_requires_entity_id():
    frame = pd.DataFrame({"y": [1.0, 2.0, 3.0, 4.0], "x": [1.0, 2.0, 3.0, 4.0]})
    with pytest.raises(ValueError):
        estimate_frame(frame, "entity_fe", {"outcome": "y", "predictors": ["x"]})
