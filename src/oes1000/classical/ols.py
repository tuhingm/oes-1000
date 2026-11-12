"""OLS with conventional and HC0-HC3 covariance estimators."""

from __future__ import annotations

import numpy as np

from oes1000.registry import register_estimator


@register_estimator("ols")
def estimate_ols(y, X, *, add_constant: bool = True, cov_type: str = "HC1"):
    y = np.asarray(y, dtype=float).reshape(-1)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    if X.ndim != 2 or y.shape[0] != X.shape[0]:
        raise ValueError("X must be n×k and y must have n observations")
    if not np.isfinite(y).all() or not np.isfinite(X).all():
        raise ValueError("Inputs must contain only finite values")
    if add_constant:
        X = np.column_stack((np.ones(X.shape[0]), X))
    n, k = X.shape
    if n <= k:
        raise ValueError("OLS requires n > k")
    rank = np.linalg.matrix_rank(X)
    if rank < k:
        raise ValueError(f"Design matrix is rank deficient: rank={rank}, columns={k}")

    bread = np.linalg.inv(X.T @ X)
    beta = bread @ X.T @ y
    resid = y - X @ beta
    h = np.einsum("ij,jk,ik->i", X, bread, X)
    cov_type = cov_type.upper()
    if cov_type in {"NONROBUST", "CLASSIC", "CLASSICAL"}:
        sigma2 = float(resid @ resid / (n - k))
        covariance = sigma2 * bread
        df_resid = n - k
    else:
        if cov_type not in {"HC0", "HC1", "HC2", "HC3"}:
            raise ValueError("cov_type must be NONROBUST, HC0, HC1, HC2, or HC3")
        if cov_type == "HC0":
            omega = resid**2
        elif cov_type == "HC1":
            omega = resid**2 * n / (n - k)
        elif cov_type == "HC2":
            omega = resid**2 / np.maximum(1.0 - h, 1e-12)
        else:
            omega = resid**2 / np.maximum(1.0 - h, 1e-12)**2
        meat = X.T @ (X * omega[:, None])
        covariance = bread @ meat @ bread
        df_resid = n - k

    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    tstat = beta / np.where(se > 0, se, np.nan)
    try:
        from scipy.stats import t
        pvalues = 2 * t.sf(np.abs(tstat), df_resid)
    except Exception:
        pvalues = np.full(k, np.nan)

    ssr = float(resid @ resid)
    centered = y - y.mean()
    tss = float(centered @ centered)
    r2 = 1.0 - ssr / tss if tss > 0 else float("nan")
    return {
        "model": "ols",
        "nobs": int(n),
        "df_model": int(k - int(add_constant)),
        "df_resid": int(df_resid),
        "params": beta,
        "covariance": covariance,
        "std_errors": se,
        "t_statistics": tstat,
        "p_values": pvalues,
        "residuals": resid,
        "fitted": X @ beta,
        "r_squared": r2,
        "adjusted_r_squared": 1 - (1-r2)*(n-1)/(n-k) if np.isfinite(r2) else float("nan"),
        "ssr": ssr,
        "cov_type": cov_type,
        "design_rank": int(rank),
    }
