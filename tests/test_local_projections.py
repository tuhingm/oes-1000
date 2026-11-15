import numpy as np
import pytest

from oes1000.timeseries.local_projections import estimate_local_projections


def test_local_projections_recovers_positive_impact_direction():
    rng = np.random.default_rng(1907)
    n = 320
    shock = rng.normal(size=n)
    control = rng.normal(size=n)
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = 0.55 * y[t-1] + 0.8 * shock[t] + 0.25 * control[t] + rng.normal(scale=0.35)
    result = estimate_local_projections(y, np.column_stack([shock, control]), horizon=4, lags=2)
    assert len(result["results"]) == 5
    assert result["results"][0]["estimate"] > 0.5
    assert all(r["nobs"] > 250 for r in result["results"])
    assert all(np.isfinite(r["standard_error"]) and r["standard_error"] > 0 for r in result["results"])


def test_local_projections_rejects_bad_covariance_and_constant_shock():
    rng = np.random.default_rng(8)
    y = rng.normal(size=80)
    X = np.column_stack([np.ones(80), rng.normal(size=80)])
    with pytest.raises(ValueError):
        estimate_local_projections(y, X, cov_type="cluster")
    with pytest.raises(ValueError):
        estimate_local_projections(y, X, shock_scale="sd")
