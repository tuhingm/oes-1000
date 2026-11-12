"""Additional linear-regression estimators for OES-1000.

The routines use NumPy/SciPy only so they can run in desktop Python and Pyodide.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linprog
from scipy.stats import norm, t

from oes1000.registry import register_estimator


def _design(y, X, add_constant=True):
    y = np.asarray(y, dtype=float).reshape(-1)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    if X.ndim != 2 or X.shape[0] != y.size:
        raise ValueError("X must be n×k and y must have n observations")
    if not np.isfinite(y).all() or not np.isfinite(X).all():
        raise ValueError("Inputs must contain only finite values")
    if add_constant:
        X = np.column_stack((np.ones(y.size), X))
    n, k = X.shape
    if n <= k:
        raise ValueError("The estimator requires n > k")
    rank = np.linalg.matrix_rank(X)
    if rank < k:
        raise ValueError(f"Design matrix is rank deficient: rank={rank}, columns={k}")
    return y, X


def _result(model, y, X, beta, covariance, *, method, df_resid=None, extra=None):
    resid = y - X @ beta
    n, k = X.shape
    df = n - k if df_resid is None else int(df_resid)
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    stat = beta / np.where(se > 0, se, np.nan)
    p = 2 * t.sf(np.abs(stat), df) if df > 0 else np.full(k, np.nan)
    ssr = float(resid @ resid)
    tss = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ssr / tss if tss > 0 else float("nan")
    out = {
        "model": model, "nobs": int(n), "df_resid": df, "params": beta,
        "covariance": covariance, "std_errors": se, "test_statistics": stat,
        "p_values": p, "fitted": X @ beta, "residuals": resid,
        "r_squared": r2, "ssr": ssr, "method": method,
    }
    if extra:
        out.update(extra)
    return out


def _sandwich(X, resid, weights=None):
    bread = np.linalg.pinv(X.T @ X)
    w = np.ones_like(resid) if weights is None else np.asarray(weights, dtype=float)
    meat = X.T @ (X * (w * resid**2)[:, None])
    return bread @ meat @ bread


@register_estimator("wls")
def estimate_wls(y, X, weights, *, add_constant=True, cov_type="HC1"):
    y, X = _design(y, X, add_constant)
    w = np.asarray(weights, dtype=float).reshape(-1)
    if w.size != y.size or not np.isfinite(w).all() or np.any(w <= 0):
        raise ValueError("weights must be finite, strictly positive, and have length n")
    xtwx = X.T @ (X * w[:, None])
    if np.linalg.matrix_rank(xtwx) < X.shape[1]:
        raise ValueError("Weighted design matrix is rank deficient")
    bread = np.linalg.inv(xtwx)
    beta = bread @ (X.T @ (w * y))
    resid = y - X @ beta
    n, k = X.shape
    if cov_type.upper() == "NONROBUST":
        sigma2 = float(np.sum(w * resid**2) / (n-k))
        covariance = sigma2 * bread
    elif cov_type.upper() in {"HC0", "HC1"}:
        meat = X.T @ (X * ((w * resid)**2)[:, None])
        covariance = bread @ meat @ bread
        if cov_type.upper() == "HC1":
            covariance *= n/(n-k)
    else:
        raise ValueError("cov_type must be NONROBUST, HC0, or HC1")
    return _result("wls", y, X, beta, covariance, method="weighted least squares",
                   extra={"weights_min": float(w.min()), "weights_max": float(w.max()), "cov_type": cov_type.upper()})


@register_estimator("gls")
def estimate_gls(y, X, sigma, *, add_constant=True):
    y, X = _design(y, X, add_constant)
    sigma = np.asarray(sigma, dtype=float)
    if sigma.shape != (y.size, y.size) or not np.isfinite(sigma).all():
        raise ValueError("sigma must be a finite n×n covariance matrix")
    if not np.allclose(sigma, sigma.T, atol=1e-10):
        raise ValueError("sigma must be symmetric")
    try:
        L = np.linalg.cholesky(sigma)
    except np.linalg.LinAlgError as exc:
        raise ValueError("sigma must be positive definite") from exc
    yw = np.linalg.solve(L, y)
    Xw = np.linalg.solve(L, X)
    bread = np.linalg.inv(Xw.T @ Xw)
    beta = bread @ Xw.T @ yw
    resid = y - X @ beta
    return _result("gls", y, X, beta, bread, method="feasible input covariance GLS",
                   extra={"logdet_sigma": float(2*np.log(np.diag(L)).sum())})


@register_estimator("fgls")
def estimate_fgls_ar1(y, X, *, add_constant=True, max_iter=100, tol=1e-8):
    y, X = _design(y, X, add_constant)
    if max_iter < 1 or tol <= 0:
        raise ValueError("max_iter must be positive and tol must be positive")
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    rho = 0.0
    converged = False
    for iteration in range(1, max_iter + 1):
        resid = y - X @ beta
        denom = float(resid[:-1] @ resid[:-1])
        rho_new = float(resid[1:] @ resid[:-1] / denom) if denom > 0 else 0.0
        rho_new = float(np.clip(rho_new, -0.99, 0.99))
        yw = y[1:] - rho_new*y[:-1]
        Xw = X[1:] - rho_new*X[:-1]
        beta_new = np.linalg.lstsq(Xw, yw, rcond=None)[0]
        if np.max(np.abs(beta_new-beta)) < tol and abs(rho_new-rho) < tol:
            beta, rho, converged = beta_new, rho_new, True
            break
        beta, rho = beta_new, rho_new
    resid = y - X @ beta
    Xw = X[1:] - rho*X[:-1]
    ew = resid[1:] - rho*resid[:-1]
    df = y.size - X.shape[1] - 1
    if df <= 0:
        raise ValueError("FGLS requires more observations after AR(1) transformation")
    sigma2 = float(ew @ ew / df)
    covariance = sigma2*np.linalg.inv(Xw.T @ Xw)
    return _result("fgls", y, X, beta, covariance, method="iterated AR(1) feasible GLS",
                   df_resid=df, extra={"rho": rho, "iterations": iteration, "converged": converged})


def _irls(y, X, score, *, max_iter=500, tol=1e-9):
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    converged = False
    for iteration in range(1, max_iter+1):
        resid = y-X@beta
        scale = 1.4826*np.median(np.abs(resid-np.median(resid)))
        scale = max(float(scale), np.finfo(float).eps)
        weights = score(resid/scale)
        weights = np.maximum(weights, 1e-10)
        xtwx = X.T@(X*weights[:,None])
        beta_new = np.linalg.solve(xtwx, X.T@(weights*y))
        if np.max(np.abs(beta_new-beta)) <= tol*(1+np.max(np.abs(beta))):
            beta, converged = beta_new, True
            break
        beta = beta_new
    resid = y-X@beta
    scale = max(float(1.4826*np.median(np.abs(resid-np.median(resid)))), np.finfo(float).eps)
    weights = np.maximum(score(resid/scale), 1e-10)
    covariance = _sandwich(X, resid, weights)
    return beta, covariance, {"scale": scale, "iterations": iteration, "converged": converged}


@register_estimator("lad")
def estimate_lad(y, X, *, add_constant=True):
    y, X = _design(y, X, add_constant)
    n, k = X.shape
    # beta is unrestricted: beta = beta_plus - beta_minus; residual = u_plus-u_minus.
    c = np.r_[np.zeros(2*k), np.full(n, 0.5), np.full(n, 0.5)]
    Aeq = np.column_stack((X, -X, np.eye(n), -np.eye(n)))
    bounds = [(0, None)]*(2*k+2*n)
    fit = linprog(c, A_eq=Aeq, b_eq=y, bounds=bounds, method="highs")
    if not fit.success:
        raise RuntimeError("LAD linear program failed: "+fit.message)
    beta = fit.x[:k]-fit.x[k:2*k]
    resid = y-X@beta
    # Quantile-regression sandwich covariance uses a kernel estimate of f_u(0).
    h = 1.06*np.std(resid, ddof=1)*n**(-1/5)
    h = max(float(h), 1e-8)
    density0 = float(np.mean(np.abs(resid) <= h)/(2*h))
    bread = np.linalg.pinv(X.T@X)
    covariance = (0.25/(density0**2))*bread @ (X.T@X) @ bread if density0>0 else np.full((k,k),np.nan)
    return _result("lad", y, X, beta, covariance, method="least absolute deviations",
                   extra={"objective": float(np.abs(resid).sum()), "residual_density_at_zero": density0})


@register_estimator("quantile_regression")
def estimate_quantile(y, X, *, quantile=0.5, add_constant=True):
    y, X = _design(y, X, add_constant)
    tau=float(quantile)
    if not 0 < tau < 1:
        raise ValueError("quantile must lie strictly between zero and one")
    n,k=X.shape
    c=np.r_[np.zeros(2*k),np.full(n,tau),np.full(n,1-tau)]
    Aeq=np.column_stack((X,-X,np.eye(n),-np.eye(n)))
    fit=linprog(c,A_eq=Aeq,b_eq=y,bounds=[(0,None)]*(2*k+2*n),method="highs")
    if not fit.success:
        raise RuntimeError("Quantile-regression linear program failed: "+fit.message)
    beta=fit.x[:k]-fit.x[k:2*k]
    resid=y-X@beta
    h=1.06*np.std(resid,ddof=1)*n**(-1/5)
    h=max(float(h),1e-8)
    density0=float(np.mean(np.abs(resid)<=h)/(2*h))
    bread=np.linalg.pinv(X.T@X)
    covariance=(tau*(1-tau)/(density0**2))*bread if density0>0 else np.full((k,k),np.nan)
    return _result("quantile_regression",y,X,beta,covariance,method="Koenker-Bassett linear quantile regression",
                   extra={"quantile":tau,"check_loss":float(np.sum(np.where(resid>=0,tau*resid,(tau-1)*resid))),"residual_density_at_zero":density0})


@register_estimator("huber_regression")
def estimate_huber(y, X, *, tuning=1.345, add_constant=True, max_iter=500, tol=1e-9):
    y,X=_design(y,X,add_constant)
    c=float(tuning)
    if c<=0: raise ValueError("tuning must be positive")
    beta,cov,info=_irls(y,X,lambda u: np.where(np.abs(u)<=c,1.0,c/np.maximum(np.abs(u),1e-15)),max_iter=max_iter,tol=tol)
    return _result("huber_regression",y,X,beta,cov,method="Huber M-estimator",extra={"tuning":c,**info})


@register_estimator("tukey_bisquare")
def estimate_tukey(y, X, *, tuning=4.685, add_constant=True, max_iter=500, tol=1e-9):
    y,X=_design(y,X,add_constant)
    c=float(tuning)
    if c<=0: raise ValueError("tuning must be positive")
    def score(u):
        z=u/c
        return np.where(np.abs(z)<1.0,(1-z*z)**2,0.0)
    beta,cov,info=_irls(y,X,score,max_iter=max_iter,tol=tol)
    return _result("tukey_bisquare",y,X,beta,cov,method="Tukey bisquare redescending M-estimator",extra={"tuning":c,**info})
