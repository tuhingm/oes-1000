import numpy as np
import pytest

from oes1000.classical.advanced_discrete import (
    estimate_beta_regression,
    estimate_hurdle_poisson,
    estimate_multinomial_logit,
)


def test_beta_regression_estimates_mean_and_precision():
    rng=np.random.default_rng(211)
    x=rng.normal(size=(900,1))
    mu=1/(1+np.exp(-(-0.25+0.55*x[:,0])))
    y=rng.beta(mu*14,(1-mu)*14)
    out=estimate_beta_regression(y,x)
    assert out["converged"]
    assert out["params"]==pytest.approx([-0.25,0.55],abs=0.18)
    assert out["precision"]>0
    assert np.isfinite(out["joint_covariance"]).all()


def test_multinomial_logit_returns_baseline_category_probabilities():
    rng=np.random.default_rng(212)
    x=rng.normal(size=(1200,2))
    X=np.column_stack((np.ones(len(x)),x))
    B=np.array([[0.2,0.6,-0.3],[-0.4,-0.2,0.5]])
    eta=X@B.T
    logits=np.column_stack((eta,np.zeros(len(x))))
    logits-=logits.max(axis=1)[:,None]
    p=np.exp(logits); p/=p.sum(axis=1)[:,None]
    y=np.array([rng.choice([0,1,2],p=row) for row in p])
    out=estimate_multinomial_logit(y,x,base_category=2)
    assert out["converged"]
    assert out["params"].shape==(2,3)
    assert out["fitted_probabilities"].shape==(len(y),3)
    np.testing.assert_allclose(out["fitted_probabilities"].sum(axis=1),1.0,atol=1e-10)
    assert np.isfinite(out["joint_covariance"]).all()


def test_hurdle_poisson_estimates_incidence_and_positive_count_parts():
    rng=np.random.default_rng(213)
    x=rng.normal(size=(1000,1))
    X=np.column_stack((np.ones(len(x)),x))
    p=1/(1+np.exp(-(-0.2+0.35*x[:,0])))
    mu=np.exp(0.2+0.25*x[:,0])
    y=np.zeros(len(x),dtype=int)
    active=rng.binomial(1,p).astype(bool)
    for i in np.where(active)[0]:
        value=0
        while value==0:
            value=rng.poisson(mu[i])
        y[i]=value
    out=estimate_hurdle_poisson(y,x)
    assert out["converged"]
    assert out["params"]==pytest.approx([0.2,0.25],abs=0.22)
    assert out["incidence_params"]==pytest.approx([-0.2,0.35],abs=0.25)
    assert np.isfinite(out["joint_covariance"]).all()
