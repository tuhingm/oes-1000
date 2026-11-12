import numpy as np
import pytest

from oes1000.classical.ols import estimate_ols


def test_ols_recovers_exact_coefficients():
    x = np.arange(1.0, 31.0)
    y = 2.5 + 1.75 * x
    result = estimate_ols(y, x, cov_type="NONROBUST")
    assert result["params"] == pytest.approx([2.5, 1.75], abs=1e-10)
    assert result["r_squared"] == pytest.approx(1.0)


def test_ols_hc1_has_finite_standard_errors():
    rng = np.random.default_rng(20261113)
    X = rng.normal(size=(300, 2))
    y = 1.0 + X @ np.array([0.5, -0.8]) + rng.normal(size=300)
    result = estimate_ols(y, X, cov_type="HC1")
    assert result["params"][1:] == pytest.approx([0.5, -0.8], abs=0.2)
    assert np.isfinite(result["std_errors"]).all()


def test_ols_rejects_rank_deficiency():
    x = np.arange(10.0)
    with pytest.raises(ValueError, match="rank deficient"):
        estimate_ols(x, np.column_stack([x, 2*x]))
