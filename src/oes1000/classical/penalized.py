"""L2-penalized binary-response likelihood estimators."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, log_ndtr
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


def _penalized_binary(y, X, link, *, add_constant=True, penalty=1.0, max_iter=6000):
    y=np.asarray(y,dtype=float).reshape(-1); X=np.asarray(X,dtype=float)
    if X.ndim==1: X=X[:,None]
    if X.ndim!=2 or X.shape[0]!=y.size or not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError("Inputs must be finite and conformable")
    if not np.isin(y,[0,1]).all():
        raise ValueError("Binary response must contain only 0 and 1")
    if add_constant: X=np.column_stack((np.ones(y.size),X))
    if y.size<=X.shape[1] or np.linalg.matrix_rank(X)<X.shape[1]:
        raise ValueError("Require n > k and a full-rank design matrix")
    penalty=float(penalty)
    if penalty<0 or not np.isfinite(penalty):
        raise ValueError("L2 penalty must be finite and non-negative")
    k=X.shape[1]
    penalty_mask=np.ones(k)
    if add_constant: penalty_mask[0]=0.0
    def nll(beta):
        eta=np.clip(X@beta,-35,35)
        if link=="logit":
            logp=-np.logaddexp(0,-eta)
            logq=-np.logaddexp(0,eta)
        else:
            logp=log_ndtr(eta)
            logq=log_ndtr(-eta)
        ll=np.sum(y*logp+(1-y)*logq)
        return float(-ll+0.5*penalty*np.sum(penalty_mask*beta**2))
    fit=minimize(nll,np.zeros(k),method="BFGS",options={"gtol":1e-7,"maxiter":max_iter})
    if not fit.success and np.linalg.norm(fit.jac)>2e-4:
        raise RuntimeError("Penalized "+link+" regression failed: "+str(fit.message))
    beta=fit.x; eta=X@beta
    p=expit(eta) if link=="logit" else norm.cdf(eta)
    H=_hessian(nll,beta); cov=np.linalg.pinv(H)
    se=np.sqrt(np.maximum(np.diag(cov),0)); z=beta/np.where(se>0,se,np.nan)
    return {"model":"glm_binomial_"+link+"_penalized","nobs":int(y.size),
            "params":beta,"covariance":cov,"std_errors":se,
            "test_statistics":z,"p_values":2*norm.sf(np.abs(z)),
            "fitted_probabilities":p,"fitted_mean":p,
            "log_likelihood":float(np.sum(y*np.log(np.maximum(p,1e-15))+(1-y)*np.log(np.maximum(1-p,1e-15)))),
            "penalized_objective":float(nll(beta)),"penalty":penalty,
            "penalty_type":"L2; intercept excluded when included",
            "converged":bool(fit.success or np.linalg.norm(fit.jac)<=2e-4),
            "iterations":int(fit.nit),"link":link}


@register_estimator("glm_binomial_logit_penalized")
def estimate_penalized_logit(y,X,*,add_constant=True,penalty=1.0,max_iter=6000):
    """L2-penalized binomial logit; penalty applies to slopes, not intercept."""
    return _penalized_binary(y,X,"logit",add_constant=add_constant,penalty=penalty,max_iter=max_iter)


@register_estimator("glm_binomial_probit_penalized")
def estimate_penalized_probit(y,X,*,add_constant=True,penalty=1.0,max_iter=6000):
    """L2-penalized binomial probit; penalty applies to slopes, not intercept."""
    return _penalized_binary(y,X,"probit",add_constant=add_constant,penalty=penalty,max_iter=max_iter)
