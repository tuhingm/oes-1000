import numpy as np
import pytest

from oes1000.classical.glm_extra import (
    estimate_fractional_logit,
    estimate_gamma_glm,
    estimate_inverse_gaussian_glm,
    estimate_quasi_poisson,
    estimate_geometric_regression,
    estimate_negative_binomial_nb1,
    estimate_zero_inflated_poisson,
)


def test_fractional_logit_handles_boundary_values_and_returns_sandwich():
    rng = np.random.default_rng(101)
    x = rng.normal(size=(900, 2))
    mu = 1 / (1 + np.exp(-(-0.2 + 0.7*x[:, 0] - 0.35*x[:, 1])))
    y = rng.binomial(8, mu) / 8
    y[:3] = [0.0, 1.0, 0.5]
    out = estimate_fractional_logit(y, x)
    assert out["converged"]
    assert np.isfinite(out["covariance"]).all()
    assert np.all((out["fitted_mean"] > 0) & (out["fitted_mean"] < 1))


def test_gamma_glm_log_link_recovers_mean_structure():
    rng = np.random.default_rng(102)
    x = rng.normal(size=(1200, 1))
    mu = np.exp(0.25 + 0.4*x[:, 0])
    y = rng.gamma(shape=5.0, scale=mu/5.0)
    out = estimate_gamma_glm(y, x)
    assert out["converged"]
    assert out["params"] == pytest.approx([0.25, 0.4], abs=0.12)
    assert out["dispersion"] > 0


def test_inverse_gaussian_glm_returns_finite_inference():
    rng = np.random.default_rng(103)
    x = rng.normal(size=(800, 1))
    mu = np.exp(-0.1 + 0.25*x[:, 0])
    y = rng.wald(mean=mu, scale=0.7)
    out = estimate_inverse_gaussian_glm(y, x)
    assert np.isfinite(out["params"]).all()
    assert np.isfinite(out["covariance"]).all()
    assert out["covariance"].shape == (2, 2)


def test_quasi_poisson_recovers_log_mean_structure():
    rng = np.random.default_rng(104)
    x = rng.normal(size=(1000, 1))
    mu = np.exp(0.15 + 0.3*x[:, 0])
    y = rng.negative_binomial(2, 2/(2+mu))
    out = estimate_quasi_poisson(y, x)
    assert out["converged"]
    assert out["params"] == pytest.approx([0.15, 0.3], abs=0.16)
    assert out["dispersion"] > 0


def test_geometric_regression_has_expected_nb2_alpha_one_variance():
    rng = np.random.default_rng(105)
    x = rng.normal(size=(1200, 1))
    mu = np.exp(0.2 + 0.25*x[:, 0])
    y = rng.negative_binomial(1, 1/(1+mu))
    out = estimate_geometric_regression(y, x)
    assert out["dispersion_alpha"] == 1.0
    assert out["params"] == pytest.approx([0.2, 0.25], abs=0.16)
    assert np.isfinite(out["covariance"]).all()


def test_nb1_estimates_positive_dispersion():
    rng = np.random.default_rng(106)
    x = rng.normal(size=(700, 1))
    mu = np.exp(0.15 + 0.2*x[:, 0])
    alpha = 0.45
    size = mu/alpha
    y = rng.negative_binomial(size, 1/(1+alpha))
    out = estimate_negative_binomial_nb1(y, x)
    assert out["dispersion_alpha"] > 0
    assert out["params"] == pytest.approx([0.15, 0.2], abs=0.22)
    assert np.isfinite(out["joint_covariance"]).all()


def test_zero_inflated_poisson_returns_inflation_and_count_components():
    rng = np.random.default_rng(107)
    x = rng.normal(size=(900, 1))
    mu = np.exp(0.2 + 0.25*x[:, 0])
    structural_zero = rng.binomial(1, 0.3, size=x.shape[0]).astype(bool)
    y = rng.poisson(mu)
    y[structural_zero] = 0
    out = estimate_zero_inflated_poisson(y, x)
    assert out["converged"]
    assert np.all((out["inflation_probabilities"] > 0) & (out["inflation_probabilities"] < 1))
    assert np.isfinite(out["joint_covariance"]).all()
