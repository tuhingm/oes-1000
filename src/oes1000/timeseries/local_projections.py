"""Jorda-style local projections with HAC or heteroskedasticity-robust inference."""
from __future__ import annotations

import numpy as np
from scipy.stats import t as student_t
from oes1000.registry import register_estimator


def _hac_covariance(X: np.ndarray, residuals: np.ndarray, bandwidth: int) -> np.ndarray:
    n, k = X.shape
    scores = X * residuals[:, None]
    meat = scores.T @ scores
    for lag in range(1, min(int(bandwidth), n - 1) + 1):
        weight = 1.0 - lag / (int(bandwidth) + 1.0)
        gamma = scores[lag:].T @ scores[:-lag]
        meat += weight * (gamma + gamma.T)
    bread = np.linalg.pinv(X.T @ X)
    return bread @ meat @ bread


@register_estimator("local_projections")
def estimate_local_projections(
    y,
    X,
    horizon: int = 12,
    lags: int = 4,
    shock_index: int = 0,
    cov_type: str = "hac",
    bandwidth: int | None = None,
    shock_scale: str = "unit",
    add_constant: bool = True,
):
    """Estimate horizon-specific OLS local projections.

    X[:, shock_index] is the contemporaneous shock. Remaining columns are
    contemporaneous controls. Lags of y and all X columns enter each horizon
    regression. The dependent variable is y[t+h].
    """
    y = np.asarray(y, dtype=float).reshape(-1)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    if X.ndim != 2 or X.shape[0] != y.size:
        raise ValueError("X must be a 2D array with the same number of rows as y.")
    if not np.isfinite(y).all() or not np.isfinite(X).all():
        raise ValueError("Local projections require finite, complete numeric input.")
    if y.size < 20:
        raise ValueError("At least 20 observations are required.")
    if not 0 <= int(shock_index) < X.shape[1]:
        raise ValueError("shock_index is outside the explanatory-variable columns.")
    if int(horizon) < 0 or int(lags) < 0:
        raise ValueError("horizon and lags must be non-negative.")
    cov_type = str(cov_type).lower()
    if cov_type not in {"hac", "robust"}:
        raise ValueError("cov_type must be 'hac' or 'robust'.")
    if shock_scale not in {"unit", "sd"}:
        raise ValueError("shock_scale must be 'unit' or 'sd'.")

    shock_sd = float(np.std(X[:, int(shock_index)], ddof=1))
    if shock_scale == "sd" and shock_sd <= np.finfo(float).eps:
        raise ValueError("The shock has zero variance and cannot be standardized.")
    scale = shock_sd if shock_scale == "sd" else 1.0
    results = []
    T = y.size
    p = int(lags)
    for h in range(int(horizon) + 1):
        start, stop = p, T - h
        if stop - start <= max(8, X.shape[1] + p * (X.shape[1] + 1) + 2):
            raise ValueError(f"Insufficient observations for horizon {h} and {p} lags.")
        rows = []
        targets = []
        for time in range(start, stop):
            row = [X[time, int(shock_index)]]
            row.extend(X[time, j] for j in range(X.shape[1]) if j != int(shock_index))
            for lag in range(1, p + 1):
                row.append(y[time - lag])
                row.extend(X[time - lag, j] for j in range(X.shape[1]))
            if add_constant:
                row.append(1.0)
            rows.append(row)
            targets.append(y[time + h])
        design = np.asarray(rows, dtype=float)
        target = np.asarray(targets, dtype=float)
        n, k = design.shape
        if n <= k:
            raise ValueError(f"Not enough residual degrees of freedom at horizon {h}.")
        beta = np.linalg.lstsq(design, target, rcond=None)[0]
        residuals = target - design @ beta
        if cov_type == "hac":
            bw = int(bandwidth) if bandwidth is not None else h + 1
            if bw < 0:
                raise ValueError("bandwidth must be non-negative.")
            covariance = _hac_covariance(design, residuals, min(bw, n - 1))
        else:
            bread = np.linalg.pinv(design.T @ design)
            meat = design.T @ ((residuals ** 2)[:, None] * design)
            covariance = bread @ meat @ bread
        covariance *= n / max(n - k, 1)
        se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
        shock_beta = float(beta[0] * scale)
        shock_se = float(se[0] * scale)
        stat = shock_beta / shock_se if shock_se > 0 else float("nan")
        pvalue = float(2 * student_t.sf(abs(stat), df=n-k)) if np.isfinite(stat) else float("nan")
        results.append({
            "horizon": h,
            "estimate": shock_beta,
            "standard_error": shock_se,
            "t_statistic": float(stat),
            "p_value": pvalue,
            "nobs": int(n),
            "r_squared": float(1 - (residuals @ residuals) / np.sum((target-target.mean())**2)) if np.sum((target-target.mean())**2)>0 else None,
            "coefficients": beta.tolist(),
            "covariance": covariance.tolist(),
        })
    return {
        "model": "local_projections",
        "cov_type": cov_type,
        "lags": p,
        "horizon": int(horizon),
        "shock_index": int(shock_index),
        "shock_scale": shock_scale,
        "shock_standard_deviation": shock_sd,
        "results": results,
    }
