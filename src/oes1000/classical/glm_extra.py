"""Additional classical GLM and count-data estimators.

These routines use explicit likelihoods or estimating equations and return
model-based or sandwich covariance matrices as appropriate.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, gammaln
from scipy.stats import norm

from oes1000.registry import register_estimator


def _design(y, X, add_constant=True):
    y = np.asarray(y, dtype=float).reshape(-1)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    if X.ndim != 2 or X.shape[0] != y.size:
        raise ValueError("X must be n×k and y must have n observations")
    if not np.isfinite(y).all() or not np.isfinite(X).all():
        raise ValueError("Inputs must be finite")
    if add_constant:
        X = np.column_stack((np.ones(y.size), X))
    if y.size <= X.shape[1] or np.linalg.matrix_rank(X) < X.shape[1]:
        raise ValueError("Require n > k and a full-column-rank design matrix")
    return y, X


def _finish(model, y, X, beta, covariance, fitted, *, extra=None):
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    z = beta / np.where(se > 0, se, np.nan)
    out = {
        "model": model, "nobs": int(y.size), "params": beta,
        "covariance": covariance, "std_errors": se,
        "test_statistics": z, "p_values": 2 * norm.sf(np.abs(z)),
        "fitted_mean": fitted,
    }
    if extra:
        out.update(extra)
    return out


@register_estimator("fractional_logit")
def estimate_fractional_logit(y, X, *, add_constant=True, max_iter=3000):
    """Papke-Wooldridge fractional logit QMLE with HC0 sandwich inference."""
    y, X = _design(y, X, add_constant)
    if np.any((y < 0) | (y > 1)):
        raise ValueError("Fractional-logit response must lie in [0, 1]")

    def objective(beta):
        eta = np.clip(X @ beta, -35, 35)
        mu = expit(eta)
        return float(-np.sum(y * np.log(np.maximum(mu, 1e-15)) +
                             (1-y) * np.log(np.maximum(1-mu, 1e-15))))

    def gradient(beta):
        return X.T @ (expit(np.clip(X @ beta, -35, 35)) - y)

    fit = minimize(objective, np.zeros(X.shape[1]), jac=gradient,
                   method="BFGS", options={"gtol": 1e-8, "maxiter": max_iter})
    if not fit.success and np.linalg.norm(fit.jac) > 1e-5:
        raise RuntimeError("Fractional-logit QMLE failed: " + str(fit.message))
    beta = fit.x
    mu = expit(np.clip(X @ beta, -35, 35))
    bread = np.linalg.pinv(X.T @ ((mu*(1-mu))[:, None] * X))
    score = X * (y-mu)[:, None]
    covariance = bread @ (score.T @ score) @ bread
    return _finish("fractional_logit", y, X, beta, covariance, mu,
                   extra={"quasi_log_likelihood": -objective(beta),
                          "converged": bool(fit.success or np.linalg.norm(fit.jac) <= 1e-5),
                          "iterations": int(fit.nit), "cov_type": "HC0"})


@register_estimator("gamma_glm")
def estimate_gamma_glm(y, X, *, add_constant=True, max_iter=3000):
    """Gamma GLM with log link, estimated by gamma likelihood."""
    y, X = _design(y, X, add_constant)
    if np.any(y <= 0):
        raise ValueError("Gamma GLM requires strictly positive responses")

    def nll(beta):
        eta = np.clip(X @ beta, -30, 30)
        mu = np.exp(eta)
        # Shape is profiled from Pearson dispersion; beta score is the GLM score.
        return float(np.sum(y/mu + np.log(mu)))
    def grad(beta):
        mu = np.exp(np.clip(X @ beta, -30, 30))
        return X.T @ (1-y/mu)
    fit = minimize(nll, np.linalg.lstsq(X, np.log(y), rcond=None)[0],
                   jac=grad, method="BFGS",
                   options={"gtol": 1e-8, "maxiter": max_iter})
    if not fit.success and np.linalg.norm(fit.jac) > 1e-5:
        raise RuntimeError("Gamma GLM failed: " + str(fit.message))
    beta = fit.x
    mu = np.exp(np.clip(X @ beta, -30, 30))
    pearson = (y-mu)/mu
    dispersion = float(pearson @ pearson / (y.size-X.shape[1]))
    bread = np.linalg.pinv(X.T @ X)
    covariance = dispersion * bread
    return _finish("gamma_glm", y, X, beta, covariance, mu,
                   extra={"dispersion": dispersion, "iterations": int(fit.nit),
                          "converged": bool(fit.success or np.linalg.norm(fit.jac) <= 1e-5),
                          "link": "log", "variance": "mu^2"})


@register_estimator("inverse_gaussian_glm")
def estimate_inverse_gaussian_glm(y, X, *, add_constant=True, max_iter=3000):
    """Inverse-Gaussian GLM with log link using Fisher scoring."""
    y, X = _design(y, X, add_constant)
    if np.any(y <= 0):
        raise ValueError("Inverse-Gaussian GLM requires strictly positive responses")
    beta = np.linalg.lstsq(X, np.log(y), rcond=None)[0]
    converged = False
    for iteration in range(1, max_iter+1):
        mu = np.exp(np.clip(X @ beta, -30, 30))
        # Log-link score: X' (y-mu)/mu^2; expected information: X' diag(1/mu) X / phi.
        weight = 1/mu
        information = X.T @ (X * weight[:, None])
        score = X.T @ ((y-mu)/(mu**2))
        step = np.linalg.solve(information, score)
        beta_new = beta + step
        if np.max(np.abs(beta_new-beta)) < 1e-9:
            beta, converged = beta_new, True
            break
        beta = beta_new
    mu = np.exp(np.clip(X @ beta, -30, 30))
    pearson = (y-mu)/(mu**1.5)
    dispersion = float(pearson @ pearson/(y.size-X.shape[1]))
    covariance = dispersion*np.linalg.pinv(X.T @ (X*(1/mu)[:, None]))
    return _finish("inverse_gaussian_glm", y, X, beta, covariance, mu,
                   extra={"dispersion": dispersion, "iterations": iteration,
                          "converged": converged, "link": "log", "variance": "mu^3"})


@register_estimator("quasi_poisson")
def estimate_quasi_poisson(y, X, *, add_constant=True, max_iter=3000):
    """Quasi-Poisson log-link regression with Pearson scale and robust score."""
    y, X = _design(y, X, add_constant)
    if np.any(y < 0):
        raise ValueError("Quasi-Poisson response must be non-negative")
    beta = np.linalg.lstsq(X, np.log(y+0.1), rcond=None)[0]
    converged = False
    for iteration in range(1, max_iter+1):
        mu = np.exp(np.clip(X @ beta, -30, 30))
        score = X.T @ (y-mu)
        information = X.T @ (X*mu[:, None])
        step = np.linalg.solve(information, score)
        beta_new = beta + step
        if np.max(np.abs(beta_new-beta)) < 1e-9:
            beta, converged = beta_new, True
            break
        beta = beta_new
    mu = np.exp(np.clip(X @ beta, -30, 30))
    dispersion = float(np.sum((y-mu)**2/mu)/(y.size-X.shape[1]))
    bread = np.linalg.pinv(X.T @ (X*mu[:, None]))
    scores = X*(y-mu)[:, None]
    covariance = bread@(scores.T@scores)@bread
    return _finish("quasi_poisson", y, X, beta, covariance, mu,
                   extra={"dispersion": dispersion, "iterations": iteration,
                          "converged": converged, "cov_type": "HC0"})


@register_estimator("geometric_regression")
def estimate_geometric_regression(y, X, *, add_constant=True, max_iter=3000):
    """Geometric count regression (NB2 with fixed alpha=1)."""
    y, X = _design(y, X, add_constant)
    if np.any(y < 0) or not np.allclose(y, np.round(y)):
        raise ValueError("Geometric response must be non-negative integer counts")
    def nll(beta):
        mu = np.exp(np.clip(X@beta, -30, 30))
        return float(-np.sum(-np.log1p(mu)+y*(np.log(mu)-np.log1p(mu))))
    def grad(beta):
        mu=np.exp(np.clip(X@beta,-30,30))
        return X.T@((1-y/mu)*mu/(1+mu))
    fit=minimize(nll,np.zeros(X.shape[1]),jac=grad,method="BFGS",
                 options={"gtol":1e-8,"maxiter":max_iter})
    if not fit.success and np.linalg.norm(fit.jac)>1e-5:
        raise RuntimeError("Geometric regression failed: "+str(fit.message))
    beta=fit.x; mu=np.exp(np.clip(X@beta,-30,30))
    info=X.T@(X*(mu/(1+mu))[:,None])
    covariance=np.linalg.pinv(info)
    ll=-nll(beta)
    return _finish("geometric_regression",y,X,beta,covariance,mu,
                   extra={"log_likelihood":ll,"dispersion_alpha":1.0,
                          "converged":bool(fit.success or np.linalg.norm(fit.jac)<=1e-5),
                          "iterations":int(fit.nit)})


@register_estimator("negative_binomial_nb1")
def estimate_negative_binomial_nb1(y, X, *, add_constant=True, max_iter=5000):
    """NB1 count regression, Var(Y|X)=mu*(1+alpha), alpha>0."""
    y, X = _design(y, X, add_constant)
    if np.any(y < 0) or not np.allclose(y, np.round(y)):
        raise ValueError("NB1 response must be non-negative integer counts")
    n,k=X.shape
    def ll(theta):
        beta=theta[:k]; alpha=np.exp(np.clip(theta[k],-10,8))
        mu=np.exp(np.clip(X@beta,-30,30))
        size=mu/alpha; prob=1/(1+alpha)
        return float(np.sum(gammaln(y+size)-gammaln(size)-gammaln(y+1)
                            +size*np.log(prob)+y*np.log1p(-prob)))
    fit=minimize(lambda t:-ll(t),np.r_[np.zeros(k),np.log(0.2)],
                 method="Nelder-Mead",options={"maxiter":max_iter,"xatol":1e-8,"fatol":1e-8})
    if not fit.success:
        raise RuntimeError("NB1 maximum likelihood failed: "+str(fit.message))
    theta=fit.x; beta=theta[:k]; alpha=float(np.exp(theta[k]))
    # Numerical observed Hessian for joint beta/log-alpha inference.
    d=k+1; h=2e-4; H=np.empty((d,d)); f0=-ll(theta)
    for i in range(d):
        ei=np.zeros(d); ei[i]=h
        H[i,i]=(-ll(theta+ei)+2*f0-ll(theta-ei))/(h*h)
        for j in range(i):
            ej=np.zeros(d); ej[j]=h
            H[i,j]=H[j,i]=(-ll(theta+ei+ej)+ll(theta+ei-ej)+ll(theta-ei+ej)-ll(theta-ei-ej))/(4*h*h)
    cov=np.linalg.pinv(H)
    mu=np.exp(np.clip(X@beta,-30,30))
    return _finish("negative_binomial_nb1",y,X,beta,cov[:k,:k],mu,
                   extra={"dispersion_alpha":alpha,"log_likelihood":ll(theta),
                          "joint_parameters":theta,"joint_covariance":cov,
                          "converged":True,"iterations":int(fit.nit)})


@register_estimator("zero_inflated_poisson")
def estimate_zero_inflated_poisson(y, X, *, add_constant=True, max_iter=5000):
    """Zero-inflated Poisson with logit inflation probability and log-mean."""
    y, X = _design(y, X, add_constant)
    if np.any(y < 0) or not np.allclose(y, np.round(y)):
        raise ValueError("ZIP response must be non-negative integer counts")
    n,k=X.shape
    # Separate inflation intercept; joint numerical optimization is stable for modest dimensions.
    def ll(theta):
        beta=theta[:k]; gamma=theta[k:]
        mu=np.exp(np.clip(X@beta,-25,25)); pi=expit(np.clip(X@gamma,-25,25))
        logp0=np.logaddexp(np.log(np.maximum(pi,1e-15)),
                           np.log(np.maximum(1-pi,1e-15))-mu)
        logpy=np.log(np.maximum(1-pi,1e-15))+y*np.log(mu)-mu-gammaln(y+1)
        return float(np.sum(np.where(y==0,logp0,logpy)))
    start=np.r_[np.linalg.lstsq(X,np.log(y+0.1),rcond=None)[0],np.full(k,-1.5)]
    fit=minimize(lambda t:-ll(t),start,method="BFGS",
                 options={"gtol":1e-7,"maxiter":max_iter})
    if not fit.success and np.linalg.norm(fit.jac)>1e-4:
        raise RuntimeError("ZIP maximum likelihood failed: "+str(fit.message))
    theta=fit.x; beta=theta[:k]; mu=np.exp(np.clip(X@beta,-25,25)); pi=expit(X@theta[k:])
    d=2*k; h=1e-4; H=np.empty((d,d)); f0=-ll(theta)
    for i in range(d):
        ei=np.zeros(d); ei[i]=h
        H[i,i]=(-ll(theta+ei)+2*f0-ll(theta-ei))/(h*h)
        for j in range(i):
            ej=np.zeros(d); ej[j]=h
            H[i,j]=H[j,i]=(-ll(theta+ei+ej)+ll(theta+ei-ej)+ll(theta-ei+ej)-ll(theta-ei-ej))/(4*h*h)
    cov=np.linalg.pinv(H)
    return _finish("zero_inflated_poisson",y,X,beta,cov[:k,:k],(1-pi)*mu,
                   extra={"inflation_coefficients":theta[k:],"inflation_probabilities":pi,
                          "log_likelihood":ll(theta),"joint_parameters":theta,
                          "joint_covariance":cov,
                          "converged":bool(fit.success or np.linalg.norm(fit.jac)<=1e-4),
                          "iterations":int(fit.nit)})
