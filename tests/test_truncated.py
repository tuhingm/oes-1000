import numpy as np
import pytest

from oes1000.classical.truncated import estimate_truncated_regression


def test_left_truncated_normal_regression_recovers_parameters():
    rng=np.random.default_rng(401)
    n=5000
    x=rng.normal(size=(n,2))
    latent=0.45+0.8*x[:,0]-0.5*x[:,1]+rng.normal(scale=0.9,size=n)
    keep=latent>0.0
    y=latent[keep]
    x=x[keep]
    out=estimate_truncated_regression(y,x,lower=0.0)
    assert out["converged"]
    assert out["params"]==pytest.approx([0.45,0.8,-0.5],abs=0.16)
    assert out["sigma"]==pytest.approx(0.9,abs=0.12)
    assert np.isfinite(out["joint_covariance"]).all()


def test_truncated_regression_rejects_values_below_threshold():
    with pytest.raises(ValueError,match="must exceed"):
        estimate_truncated_regression(np.array([0.0,1.0,2.0,3.0,4.0]),
                                      np.arange(5.0),lower=0.0)
