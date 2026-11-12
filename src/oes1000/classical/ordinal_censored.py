"""Ordinal-response and censored-normal maximum-likelihood estimators."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import norm

from oes1000.registry import register_estimator


def _prepare(y, X, add_constant):
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


def _hessian(fun, theta):
    d = theta.size
    h = 1e-4 * np.maximum(1.0, np.abs(theta))
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


def _ordered(y, X, link, add_constant=True, max_iter=6000):
    # A free intercept is not identified separately from unrestricted cutpoints.
    y, X = _prepare(y, X, False)
    categories = np.unique(y)
    if categories.size < 3 or not np.allclose(categories, np.round(categories)):
        raise ValueError("Ordered response must contain at least three integer-coded categories")
    codes = np.searchsorted(categories, y)
    n, k = X.shape
    J = categories.size
    cdf = expit if link == "logit" else norm.cdf

    def cutpoints(theta):
        raw = theta[k:]
        return np.r_[raw[0], raw[0] + np.cumsum(np.exp(np.clip(raw[1:], -15, 15)))]

    def probabilities(theta):
        eta = X @ theta[:k]
        cuts = cutpoints(theta)
        F = cdf(cuts[None, :] - eta[:, None])
        P = np.column_stack((F[:, 0], np.diff(F, axis=1), 1-F[:, -1]))
        return np.maximum(P, 1e-14)

    def nll(theta):
        P = probabilities(theta)
        return float(-np.log(P[np.arange(n), codes]).sum())

    initial_cuts = np.quantile(codes, np.arange(1, J)/J)
    initial_cuts = np.maximum.accumulate(initial_cuts + np.arange(J-1)*0.2)
    increments = np.diff(initial_cuts)
    raw = np.r_[initial_cuts[0], np.log(np.maximum(increments, 0.2))]
    start = np.r_[np.zeros(k), raw]
    fit = minimize(nll, start, method="BFGS",
                   options={"gtol": 1e-7, "maxiter": max_iter})
    if not fit.success and np.linalg.norm(fit.jac) > 2e-4:
        raise RuntimeError(link+" ordered regression failed: "+str(fit.message))
    theta = fit.x
    H = _hessian(nll, theta)
    joint_cov = np.linalg.pinv(H)
    beta_cov = joint_cov[:k, :k]
    beta = theta[:k]
    se = np.sqrt(np.maximum(np.diag(beta_cov), 0))
    z = beta/np.where(se > 0, se, np.nan)
    P = probabilities(theta)
    return {
        "model": "ordered_"+link, "nobs": int(n), "params": beta,
        "covariance": beta_cov, "std_errors": se, "test_statistics": z,
        "p_values": 2*norm.sf(np.abs(z)), "cutpoints": cutpoints(theta),
        "categories": categories.tolist(), "fitted_probabilities": P,
        "fitted_category": categories[np.argmax(P, axis=1)],
        "log_likelihood": float(-nll(theta)), "joint_parameters": theta,
        "joint_covariance": joint_cov,
        "converged": bool(fit.success or np.linalg.norm(fit.jac) <= 2e-4),
        "iterations": int(fit.nit), "link": link,
    }


@register_estimator("ordered_logit")
def estimate_ordered_logit(y, X, *, add_constant=True, max_iter=6000):
    """Proportional-odds ordered logit with unrestricted ordered cutpoints."""
    return _ordered(y, X, "logit", add_constant, max_iter)


@register_estimator("ordered_probit")
def estimate_ordered_probit(y, X, *, add_constant=True, max_iter=6000):
    """Ordered probit with standard-normal latent disturbance."""
    return _ordered(y, X, "probit", add_constant, max_iter)


@register_estimator("tobit")
def estimate_tobit(y, X, *, add_constant=True, lower=0.0, upper=np.inf,
                   max_iter=6000):
    """Type-I Tobit with known lower/upper censoring points and normal errors."""
    y, X = _prepare(y, X, add_constant)
    lower = float(lower)
    upper = float(upper)
    if not lower < upper:
        raise ValueError("Tobit lower censoring point must be below upper point")
    if np.any(y < lower) or np.any(y > upper):
        raise ValueError("Observed Tobit outcomes cannot lie outside censoring bounds")
    n, k = X.shape
    low = np.isclose(y, lower) if np.isfinite(lower) else np.zeros(n, dtype=bool)
    high = np.isclose(y, upper) if np.isfinite(upper) else np.zeros(n, dtype=bool)
    middle = ~(low | high)
    if middle.sum() <= k:
        raise ValueError("Tobit requires more uncensored observations than regressors")

    beta0 = np.linalg.lstsq(X[middle], y[middle], rcond=None)[0]
    sigma0 = max(float(np.std(y[middle]-X[middle]@beta0)), 1e-3)

    def nll(theta):
        beta = theta[:k]
        sigma = np.exp(np.clip(theta[k], -12, 12))
        eta = X @ beta
        z = (y-eta)/sigma
        ll = np.empty(n)
        ll[low] = norm.logcdf((lower-eta[low])/sigma)
        ll[high] = norm.logsf((upper-eta[high])/sigma)
        ll[middle] = norm.logpdf(z[middle])-np.log(sigma)
        return float(-ll.sum())

    start = np.r_[beta0, np.log(sigma0)]
    fit = minimize(nll, start, method="BFGS",
                   options={"gtol": 1e-7, "maxiter": max_iter})
    if not fit.success and np.linalg.norm(fit.jac) > 2e-4:
        raise RuntimeError("Tobit maximum likelihood failed: "+str(fit.message))
    theta = fit.x
    H = _hessian(nll, theta)
    joint_cov = np.linalg.pinv(H)
    beta = theta[:k]
    beta_cov = joint_cov[:k, :k]
    se = np.sqrt(np.maximum(np.diag(beta_cov), 0))
    zstat = beta/np.where(se > 0, se, np.nan)
    sigma = float(np.exp(theta[k]))
    eta = X @ beta
    return {
        "model": "tobit", "nobs": int(n), "params": beta,
        "covariance": beta_cov, "std_errors": se,
        "test_statistics": zstat, "p_values": 2*norm.sf(np.abs(zstat)),
        "sigma": sigma, "fitted_latent_mean": eta,
        "fitted_mean": eta, "lower": lower, "upper": upper,
        "n_censored_lower": int(low.sum()), "n_censored_upper": int(high.sum()),
        "n_uncensored": int(middle.sum()), "log_likelihood": float(-nll(theta)),
        "joint_parameters": theta, "joint_covariance": joint_cov,
        "converged": bool(fit.success or np.linalg.norm(fit.jac) <= 2e-4),
        "iterations": int(fit.nit),
    }
