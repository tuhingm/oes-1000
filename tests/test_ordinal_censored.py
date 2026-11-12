import numpy as np
import pytest

from oes1000.classical.ordinal_censored import (
    estimate_ordered_logit,
    estimate_ordered_probit,
    estimate_tobit,
)


def _ordered_sample(seed=301, n=1800):
    rng=np.random.default_rng(seed)
    x=rng.normal(size=(n,2))
    latent=0.65*x[:,0]-0.4*x[:,1]+rng.logistic(size=n)
    y=np.digitize(latent,[-0.7,0.45,1.35])
    return y,x


def test_ordered_logit_recovers_slopes_and_valid_probabilities():
    y,x=_ordered_sample()
    out=estimate_ordered_logit(y,x)
    assert out["converged"]
    assert out["params"]==pytest.approx([0.65,-0.4],abs=0.18)
    assert out["fitted_probabilities"].shape==(len(y),4)
    np.testing.assert_allclose(out["fitted_probabilities"].sum(axis=1),1.0,atol=1e-10)
    assert np.all(np.diff(out["cutpoints"])>0)
    assert np.isfinite(out["joint_covariance"]).all()


def test_ordered_probit_recovers_slopes_and_ordered_thresholds():
    rng=np.random.default_rng(302)
    x=rng.normal(size=(1800,2))
    latent=0.7*x[:,0]-0.35*x[:,1]+rng.normal(size=len(x))
    y=np.digitize(latent,[-0.6,0.5,1.4])
    out=estimate_ordered_probit(y,x)
    assert out["converged"]
    assert out["params"]==pytest.approx([0.7,-0.35],abs=0.18)
    assert np.all(np.diff(out["cutpoints"])>0)
    np.testing.assert_allclose(out["fitted_probabilities"].sum(axis=1),1.0,atol=1e-10)


def test_tobit_recovers_censored_normal_regression():
    rng=np.random.default_rng(303)
    x=rng.normal(size=(2200,2))
    latent=0.8+0.9*x[:,0]-0.55*x[:,1]+rng.normal(scale=0.8,size=len(x))
    y=np.maximum(latent,0.0)
    out=estimate_tobit(y,x,lower=0.0)
    assert out["converged"]
    assert out["params"]==pytest.approx([0.8,0.9,-0.55],abs=0.15)
    assert out["sigma"]==pytest.approx(0.8,abs=0.1)
    assert out["n_censored_lower"]>0
    assert out["n_uncensored"]>len(out["params"])
    assert np.isfinite(out["joint_covariance"]).all()
