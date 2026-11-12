import numpy as np
import pytest

from oes1000.classical.penalized import (
    estimate_penalized_logit,
    estimate_penalized_probit,
)


@pytest.mark.parametrize("estimator", [estimate_penalized_logit, estimate_penalized_probit])
def test_penalized_binary_glm_returns_finite_probabilities_and_covariance(estimator):
    rng=np.random.default_rng(601)
    x=rng.normal(size=(1400,2))
    eta=-0.25+0.7*x[:,0]-0.4*x[:,1]
    p=1/(1+np.exp(-eta)) if estimator is estimate_penalized_logit else 0.5*(1+np.vectorize(__import__("math").erf)(eta/np.sqrt(2)))
    y=rng.binomial(1,p)
    out=estimator(y,x,penalty=0.25)
    assert out["converged"]
    assert out["params"].shape==(3,)
    assert out["params"]==pytest.approx([-0.25,0.7,-0.4],abs=0.18)
    assert np.isfinite(out["covariance"]).all()
    assert np.all((out["fitted_probabilities"]>0)&(out["fitted_probabilities"]<1))


def test_penalized_logit_rejects_negative_penalty():
    with pytest.raises(ValueError,match="non-negative"):
        estimate_penalized_logit(np.array([0,1,0,1,0,1]),np.arange(6.0),penalty=-1)
