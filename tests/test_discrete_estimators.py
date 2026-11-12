import numpy as np
import pytest

from oes1000.classical.discrete import (
    estimate_cloglog, estimate_logit, estimate_negative_binomial,
    estimate_poisson, estimate_probit,
)


def binary_sample(seed=41,n=1200):
    rng=np.random.default_rng(seed)
    x=rng.normal(size=(n,2))
    p=1/(1+np.exp(-(0.3+0.8*x[:,0]-0.5*x[:,1])))
    y=rng.binomial(1,p)
    return y,x


@pytest.mark.parametrize("estimator", [estimate_logit, estimate_probit, estimate_cloglog])
def test_binary_estimators_return_finite_coefficients(estimator):
    y,x=binary_sample()
    out=estimator(y,x)
    assert np.isfinite(out["params"]).all()
    assert out["params"].shape==(3,)
    assert out["nobs"]==len(y)


def test_binary_estimators_reject_nonbinary_outcome():
    with pytest.raises(ValueError,match="only 0 and 1"):
        estimate_logit(np.arange(10),np.arange(10))


def test_poisson_recovers_count_regression_signal():
    rng=np.random.default_rng(42)
    x=rng.normal(size=(1500,2))
    mu=np.exp(0.2+0.35*x[:,0]-0.25*x[:,1])
    y=rng.poisson(mu)
    out=estimate_poisson(y,x)
    assert out["params"]==pytest.approx([0.2,0.35,-0.25],abs=0.15)
    assert np.isfinite(out["std_errors"]).all()


def test_negative_binomial_returns_positive_dispersion():
    rng=np.random.default_rng(43)
    x=rng.normal(size=(1200,1))
    mu=np.exp(0.25+0.3*x[:,0])
    alpha=0.6
    lam=rng.gamma(shape=1/alpha,scale=mu*alpha)
    y=rng.poisson(lam)
    out=estimate_negative_binomial(y,x)
    assert out["dispersion_alpha"]>0
    assert out["params"]==pytest.approx([0.25,0.3],abs=0.25)
