"""Normal regression for samples truncated at a known lower threshold."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr
from scipy.stats import norm

from oes1000.registry import register_estimator


def _hessian(fun, theta):
    d=theta.size; h=1e-4*np.maximum(1.0,np.abs(theta)); H=np.empty((d,d)); f0=fun(theta)
    for i in range(d):
        ei=np.zeros(d); ei[i]=h[i]
        H[i,i]=(fun(theta+ei)-2*f0+fun(theta-ei))/(h[i]**2)
        for j in range(i):
            ej=np.zeros(d); ej[j]=h[j]
            H[i,j]=H[j,i]=(fun(theta+ei+ej)-fun(theta+ei-ej)-fun(theta-ei+ej)+fun(theta-ei-ej))/(4*h[i]*h[j])
    return H


@register_estimator("truncated_regression")
def estimate_truncated_regression(y, X, *, add_constant=True, lower=0.0,
                                  max_iter=6000):
    """Left-truncated Gaussian regression, conditional on observing Y > lower.

    The log likelihood is sum(log f(y_i|x_i) - log P(Y_i > lower|x_i)).
    """
    y=np.asarray(y,dtype=float).reshape(-1); X=np.asarray(X,dtype=float)
    if X.ndim==1: X=X[:,None]
    if X.ndim!=2 or X.shape[0]!=y.size or not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError("Inputs must be finite and conformable")
    if add_constant: X=np.column_stack((np.ones(y.size),X))
    if y.size<=X.shape[1] or np.linalg.matrix_rank(X)<X.shape[1]:
        raise ValueError("Require n > k and a full-rank design matrix")
    lower=float(lower)
    if np.any(y<=lower):
        raise ValueError("Every observed outcome must exceed the left-truncation threshold")
    n,k=X.shape
    beta0=np.linalg.lstsq(X,y,rcond=None)[0]
    sigma0=max(float(np.std(y-X@beta0)),0.1)
    def nll(theta):
        beta=theta[:k]; sigma=np.exp(np.clip(theta[k],-12,12)); eta=X@beta
        z=(y-eta)/sigma
        log_survival=log_ndtr(-(lower-eta)/sigma)
        return float(-np.sum(norm.logpdf(z)-np.log(sigma)-log_survival))
    fit=minimize(nll,np.r_[beta0,np.log(sigma0)],method="BFGS",
                 options={"gtol":1e-7,"maxiter":max_iter})
    if not fit.success and np.linalg.norm(fit.jac)>2e-4:
        raise RuntimeError("Truncated-regression MLE failed: "+str(fit.message))
    theta=fit.x; H=_hessian(nll,theta); joint_cov=np.linalg.pinv(H)
    beta=theta[:k]; cov=joint_cov[:k,:k]; se=np.sqrt(np.maximum(np.diag(cov),0))
    zstat=beta/np.where(se>0,se,np.nan); sigma=float(np.exp(theta[k]))
    eta=X@beta
    return {"model":"truncated_regression","nobs":int(n),"params":beta,
            "covariance":cov,"std_errors":se,"test_statistics":zstat,
            "p_values":2*norm.sf(np.abs(zstat)),"sigma":sigma,
            "fitted_latent_mean":eta,"fitted_mean":eta,
            "truncation_lower":lower,"log_likelihood":float(-nll(theta)),
            "joint_parameters":theta,"joint_covariance":joint_cov,
            "converged":bool(fit.success or np.linalg.norm(fit.jac)<=2e-4),
            "iterations":int(fit.nit)}
