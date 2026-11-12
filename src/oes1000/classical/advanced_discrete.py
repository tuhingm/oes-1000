"""Multinomial, beta, and hurdle-count likelihood estimators."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import betaln, expit, gammaln, logsumexp
from scipy.stats import norm

from oes1000.registry import register_estimator


def _design(y, X, add_constant=True):
    y = np.asarray(y)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    if X.ndim != 2 or X.shape[0] != y.size or not np.isfinite(X).all():
        raise ValueError("X must be a finite n×k design matrix")
    if add_constant:
        X = np.column_stack((np.ones(y.size), X))
    if y.size <= X.shape[1] or np.linalg.matrix_rank(X) < X.shape[1]:
        raise ValueError("Require n > k and a full-rank design matrix")
    return y, X


def _hessian(fun, theta, step=1e-4):
    d = theta.size
    h = step * np.maximum(1.0, np.abs(theta))
    H = np.empty((d, d))
    f0 = fun(theta)
    for i in range(d):
        ei = np.zeros(d); ei[i] = h[i]
        H[i, i] = (fun(theta+ei)-2*f0+fun(theta-ei))/(h[i]**2)
        for j in range(i):
            ej = np.zeros(d); ej[j] = h[j]
            H[i, j] = H[j, i] = (
                fun(theta+ei+ej)-fun(theta+ei-ej)
                -fun(theta-ei+ej)+fun(theta-ei-ej)
            )/(4*h[i]*h[j])
    return H


def _fit(model, y, X, objective, start, k, fitted, extras=None):
    fit = minimize(objective, start, method="BFGS",
                   options={"gtol": 1e-7, "maxiter": 6000})
    if not fit.success and np.linalg.norm(fit.jac) > 2e-4:
        raise RuntimeError(model+" maximum likelihood failed: "+str(fit.message))
    theta = fit.x
    H = _hessian(objective, theta)
    covariance = np.linalg.pinv(H)
    beta = theta[:k]
    cov_beta = covariance[:k, :k]
    se = np.sqrt(np.maximum(np.diag(cov_beta), 0))
    z = beta/np.where(se > 0, se, np.nan)
    out = {"model":model,"nobs":int(y.size),"params":beta,
           "covariance":cov_beta,"std_errors":se,
           "test_statistics":z,"p_values":2*norm.sf(np.abs(z)),
           "log_likelihood":float(-objective(theta)),
           "joint_parameters":theta,"joint_covariance":covariance,
           "converged":bool(fit.success or np.linalg.norm(fit.jac)<=2e-4),
           "iterations":int(fit.nit)}
    if fitted is not None:
        out["fitted_mean"] = fitted(theta)
    if extras:
        out.update(extras(theta))
    return out


@register_estimator("beta_regression")
def estimate_beta_regression(y, X, *, add_constant=True):
    """Beta regression with logit mean and constant log precision."""
    y, X = _design(np.asarray(y, dtype=float).reshape(-1), X, add_constant)
    if np.any((y <= 0) | (y >= 1)):
        raise ValueError("Beta regression requires responses strictly inside (0,1)")
    n, k = X.shape
    def nll(theta):
        mu = expit(np.clip(X@theta[:k], -25, 25))
        phi = np.exp(np.clip(theta[k], -8, 15))
        a, b = mu*phi, (1-mu)*phi
        ll = gammaln(phi)-gammaln(a)-gammaln(b)+(a-1)*np.log(y)+(b-1)*np.log1p(-y)
        return float(-np.sum(ll))
    start = np.r_[np.linalg.lstsq(X, np.log(y/(1-y)), rcond=None)[0], np.log(10.0)]
    return _fit("beta_regression",y,X,nll,start,k,
                lambda t: expit(np.clip(X@t[:k],-25,25)),
                extras=lambda t:{"precision":float(np.exp(t[k])),"link":"logit"})


@register_estimator("multinomial_logit")
def estimate_multinomial_logit(y, X, *, add_constant=True, base_category=None):
    """Baseline-category multinomial logit with joint MLE and observed Hessian."""
    y, X = _design(np.asarray(y).reshape(-1), X, add_constant)
    categories = np.unique(y)
    if categories.size < 3:
        raise ValueError("Multinomial logit requires at least three outcome categories")
    if base_category is None:
        base_category = categories[-1]
    if base_category not in categories:
        raise ValueError("base_category must be an observed outcome category")
    nonbase = [c for c in categories if c != base_category]
    n, k = X.shape
    J = len(categories)
    codes = np.column_stack([y == c for c in nonbase]).astype(float)
    def probabilities(theta):
        B = theta.reshape(J-1,k)
        eta = X@B.T
        logits = np.column_stack((eta,np.zeros(n)))
        logits -= logsumexp(logits,axis=1)[:,None]
        return np.exp(logits)
    def nll(theta):
        P = probabilities(theta)
        idx = np.array([nonbase.index(v) if v != base_category else J-1 for v in y])
        return float(-np.log(np.maximum(P[np.arange(n),idx],1e-15)).sum())
    start = np.zeros((J-1)*k)
    fit = minimize(nll,start,method="BFGS",options={"gtol":1e-7,"maxiter":6000})
    if not fit.success and np.linalg.norm(fit.jac)>2e-4:
        raise RuntimeError("Multinomial-logit MLE failed: "+str(fit.message))
    theta=fit.x; H=_hessian(nll,theta); covariance=np.linalg.pinv(H)
    B=theta.reshape(J-1,k); se=np.sqrt(np.maximum(np.diag(covariance),0)).reshape(J-1,k)
    z=B/np.where(se>0,se,np.nan)
    P=probabilities(theta)
    return {"model":"multinomial_logit","nobs":int(n),"categories":categories.tolist(),
            "base_category":base_category,"nonbase_categories":nonbase,
            "params":B,"covariance":covariance,"std_errors":se,
            "test_statistics":z,"p_values":2*norm.sf(np.abs(z)),
            "fitted_probabilities":P,"log_likelihood":float(-nll(theta)),
            "joint_parameters":theta,"joint_covariance":covariance,"converged":bool(fit.success or np.linalg.norm(fit.jac)<=2e-4),
            "iterations":int(fit.nit)}


@register_estimator("hurdle_poisson")
def estimate_hurdle_poisson(y, X, *, add_constant=True):
    """Hurdle Poisson: logit incidence plus zero-truncated Poisson counts."""
    y, X = _design(np.asarray(y,dtype=float).reshape(-1),X,add_constant)
    if np.any(y<0) or not np.allclose(y,np.round(y)):
        raise ValueError("Hurdle-Poisson response must be non-negative integer counts")
    n,k=X.shape
    positive=(y>0).astype(float)
    def nll(theta):
        bg=theta[:k]; bc=theta[k:]
        p=expit(np.clip(X@bg,-25,25))
        mu=np.exp(np.clip(X@bc,-25,25))
        log_positive_prob=np.log(-np.expm1(-mu))
        ll=np.where(y==0,np.log(np.maximum(1-p,1e-15)),
                    np.log(np.maximum(p,1e-15))+y*np.log(mu)-mu-gammaln(y+1)-log_positive_prob)
        return float(-ll.sum())
    start=np.r_[np.zeros(k),np.linalg.lstsq(X[positive==1],np.log(y[positive==1]),rcond=None)[0]]
    fit=minimize(nll,start,method="BFGS",options={"gtol":1e-7,"maxiter":6000})
    if not fit.success and np.linalg.norm(fit.jac)>2e-4:
        raise RuntimeError("Hurdle-Poisson MLE failed: "+str(fit.message))
    theta=fit.x; H=_hessian(nll,theta); covariance=np.linalg.pinv(H)
    bg,bc=theta[:k],theta[k:]
    p=expit(np.clip(X@bg,-25,25)); mu=np.exp(np.clip(X@bc,-25,25))
    se=np.sqrt(np.maximum(np.diag(covariance),0)); z=theta/np.where(se>0,se,np.nan)
    return {"model":"hurdle_poisson","nobs":int(n),"params":bc,
            "covariance":covariance[k:,k:],"std_errors":se[k:],
            "test_statistics":z[k:],"p_values":2*norm.sf(np.abs(z[k:])),
            "incidence_params":bg,"incidence_covariance":covariance[:k,:k],
            "incidence_std_errors":se[:k],"incidence_p_values":2*norm.sf(np.abs(z[:k])),
            "fitted_mean":p*mu/np.maximum(1-np.exp(-mu),1e-12),
            "positive_probability":p,"positive_count_mean":mu,
            "log_likelihood":float(-nll(theta)),"joint_parameters":theta,
            "joint_covariance":covariance,
            "converged":bool(fit.success or np.linalg.norm(fit.jac)<=2e-4),
            "iterations":int(fit.nit)}
