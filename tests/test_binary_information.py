import numpy as np
from scipy.special import ndtr

from oes1000.classical.discrete import estimate_cloglog, estimate_probit


def _fixture():
    rng = np.random.default_rng(20261113)
    x = rng.normal(size=500)
    X = x[:, None]
    return rng, X


def test_probit_covariance_uses_expected_fisher_information():
    rng, X = _fixture()
    beta = np.array([-0.25, 0.8])
    design = np.column_stack((np.ones(X.shape[0]), X))
    probability = ndtr(design @ beta)
    y = rng.binomial(1, probability)
    result = estimate_probit(y, X)
    eta = design @ result["params"]
    p = np.clip(ndtr(eta), 1e-12, 1 - 1e-12)
    density = np.exp(-0.5 * eta**2) / np.sqrt(2 * np.pi)
    information = design.T @ ((density**2 / (p * (1 - p)))[:, None] * design)
    np.testing.assert_allclose(result["covariance"], np.linalg.inv(information), rtol=1e-7, atol=1e-9)


def test_cloglog_covariance_uses_expected_fisher_information():
    rng, X = _fixture()
    beta = np.array([-1.0, 0.55])
    design = np.column_stack((np.ones(X.shape[0]), X))
    z = np.exp(design @ beta)
    probability = -np.expm1(-z)
    y = rng.binomial(1, probability)
    result = estimate_cloglog(y, X)
    eta = design @ result["params"]
    z = np.exp(np.clip(eta, -30, 30))
    q = np.exp(-z)
    p = np.clip(-np.expm1(-z), 1e-12, 1 - 1e-12)
    information = design.T @ (((z**2 * q / p))[:, None] * design)
    np.testing.assert_allclose(result["covariance"], np.linalg.inv(information), rtol=1e-7, atol=1e-9)


def test_binary_model_reports_finite_covariance_and_probabilities():
    rng, X = _fixture()
    design = np.column_stack((np.ones(X.shape[0]), X))
    y = rng.binomial(1, ndtr(design @ np.array([0.1, 0.6])))
    for estimator in (estimate_probit, estimate_cloglog):
        result = estimator(y, X)
        assert result["converged"]
        assert np.isfinite(result["covariance"]).all()
        probabilities = result["fitted_probabilities"]
        assert np.all((probabilities >= 0) & (probabilities <= 1))
