"""Initial estimators for OES Intelligence with explicit sample and rank validation."""
from __future__ import annotations

import json
from io import StringIO

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def _frame(csv_text: str) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(csv_text))
    if frame.empty:
        raise ValueError("No observations in CSV.")
    if frame.columns.duplicated().any():
        raise ValueError("Duplicate column names are not supported.")
    return frame


def _assert_full_rank(matrix, description: str) -> None:
    """Reject aliased design columns before statsmodels uses a generalized inverse."""
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2:
        raise ValueError(f"{description} must be a two-dimensional design matrix.")
    rank = int(np.linalg.matrix_rank(values))
    if rank < values.shape[1]:
        raise ValueError(
            f"{description} is rank deficient ({rank} independent columns for "
            f"{values.shape[1]} columns). Remove or re-specify collinear regressors."
        )


def _prepare(frame: pd.DataFrame, roles: dict, require_entity: bool = False):
    outcome = roles.get("outcome")
    predictors = roles.get("predictors") or []
    if not outcome or outcome not in frame.columns:
        raise ValueError("Select a valid outcome variable.")

    predictors = [x for x in predictors if x in frame.columns and x != outcome]
    if not predictors:
        raise ValueError("Select at least one valid regressor.")

    needed = [outcome] + predictors
    entity = roles.get("entity")
    if require_entity:
        if not entity or entity not in frame.columns:
            raise ValueError("Select a valid entity identifier for the fixed-effects estimator.")
        if entity not in needed:
            needed.append(entity)

    # The entity identifier belongs in the estimation sample only for estimators
    # that actually use it. Merely selecting an entity role must not change OLS/logit.
    data = frame[needed].copy().dropna()
    minimum_columns = len(predictors) + (0 if require_entity else 1)
    if len(data) <= minimum_columns:
        raise ValueError("Insufficient complete observations for the selected specification.")

    if not all(pd.api.types.is_numeric_dtype(data[c]) for c in predictors):
        raise ValueError(
            "Regressors must be numeric. Encode categorical predictors explicitly before estimation."
        )
    if data[predictors].nunique().eq(1).any():
        raise ValueError("At least one selected regressor is constant in the estimation sample.")

    return data, outcome, predictors, entity


def _coefficient_table(result, names):
    ci = result.conf_int()
    return [
        {
            "term": str(name),
            "estimate": float(result.params.iloc[i]),
            "std_error": float(result.bse.iloc[i]),
            "statistic": float(result.tvalues.iloc[i]),
            "p_value": float(result.pvalues.iloc[i]),
            "ci_lower": float(ci.iloc[i, 0]),
            "ci_upper": float(ci.iloc[i, 1]),
        }
        for i, name in enumerate(names)
    ]


def _ols(data: pd.DataFrame, outcome: str, predictors: list[str]):
    if not pd.api.types.is_numeric_dtype(data[outcome]):
        raise ValueError("OLS requires a numeric outcome.")

    y = data[outcome].astype(float)
    X = sm.add_constant(data[predictors].astype(float), has_constant="add")
    _assert_full_rank(X.to_numpy(), "OLS design matrix")

    fitted = sm.OLS(y, X).fit(cov_type="HC3")
    residuals = np.asarray(fitted.resid)
    jb = stats.jarque_bera(residuals)

    from statsmodels.stats.stattools import durbin_watson

    diagnostics = {
        "durbin_watson": float(durbin_watson(residuals)),
        "jarque_bera_stat": float(jb.statistic),
        "jarque_bera_p": float(jb.pvalue),
    }
    return {
        "model_name": "OLS with HC3 robust covariance",
        "specification": {"outcome": outcome, "predictors": predictors},
        "coefficients": _coefficient_table(fitted, list(X.columns)),
        "summary": {
            "nobs": int(fitted.nobs),
            "r_squared": float(fitted.rsquared),
            "adjusted_r_squared": float(fitted.rsquared_adj),
            "f_statistic": float(fitted.fvalue) if np.isfinite(fitted.fvalue) else None,
        },
        "diagnostics": diagnostics,
        "notes": (
            "HC3 covariance is used for coefficient inference. Durbin–Watson and "
            "Jarque–Bera are descriptive diagnostics; they do not establish model "
            "validity or causal identification."
        ),
    }


def _entity_fe(data: pd.DataFrame, outcome: str, predictors: list[str], entity: str):
    if not pd.api.types.is_numeric_dtype(data[outcome]):
        raise ValueError("Entity fixed effects requires a numeric outcome.")
    if not entity or entity not in data.columns:
        raise ValueError("Select a valid entity identifier for the fixed-effects estimator.")

    groups = data[entity]
    counts = groups.value_counts()
    if len(counts) < 2 or counts.min() < 2:
        raise ValueError(
            "Entity fixed effects require at least two entities and repeated observations "
            "for each included entity."
        )

    y = data[outcome].astype(float)
    X = data[predictors].astype(float)
    y_dm = y - y.groupby(groups).transform("mean")
    X_dm = X - X.groupby(groups).transform("mean")

    if (X_dm.std() < 1e-12).any():
        raise ValueError(
            "A regressor has no within-entity variation and is absorbed by entity fixed effects."
        )
    _assert_full_rank(X_dm.to_numpy(), "Within-transformed fixed-effects design matrix")

    fitted = sm.OLS(y_dm, X_dm).fit(
        cov_type="cluster",
        cov_kwds={"groups": groups},
    )
    warning = (
        "There are fewer than 30 entity clusters; conventional cluster-robust inference "
        "may be unreliable."
        if groups.nunique() < 30
        else "Cluster-robust inference is based on entity clusters; assess the number of "
        "clusters and dependence structure."
    )
    return {
        "model_name": "One-way entity fixed effects (within estimator)",
        "specification": {"outcome": outcome, "predictors": predictors, "entity": entity},
        "coefficients": _coefficient_table(fitted, list(X.columns)),
        "summary": {
            "nobs": int(fitted.nobs),
            "entities": int(groups.nunique()),
            "within_r_squared": float(fitted.rsquared),
        },
        "diagnostics": {
            "entity_clusters": int(groups.nunique()),
            "min_obs_per_entity": int(counts.min()),
            "max_obs_per_entity": int(counts.max()),
        },
        "notes": (
            "Entity means were removed before estimation. Time-invariant regressors are "
            "not identified. " + warning
        ),
    }


def _logit(data: pd.DataFrame, outcome: str, predictors: list[str]):
    categories = list(pd.unique(data[outcome]))
    if len(categories) != 2:
        raise ValueError("Logit requires exactly two observed outcome categories.")

    y = (data[outcome] == categories[1]).astype(int)
    X = sm.add_constant(data[predictors].astype(float), has_constant="add")
    _assert_full_rank(X.to_numpy(), "Logit design matrix")

    fitted = sm.Logit(y, X).fit(disp=False, maxiter=200, cov_type="HC3")
    table = _coefficient_table(fitted, list(X.columns))
    for row in table:
        row["odds_ratio"] = float(np.exp(row["estimate"]))

    return {
        "model_name": "Binary logistic regression with HC3 covariance",
        "specification": {
            "outcome": outcome,
            "predictors": predictors,
            "event_category": str(categories[1]),
        },
        "coefficients": table,
        "summary": {
            "nobs": int(fitted.nobs),
            "pseudo_r_squared_mcfadden": float(fitted.prsquared),
            "log_likelihood": float(fitted.llf),
            "converged": bool(fitted.mle_retvals.get("converged", False)),
        },
        "diagnostics": {
            "event_category": str(categories[1]),
            "event_rate": float(y.mean()),
            "iterations": int(fitted.mle_retvals.get("iterations", 0)),
        },
        "notes": (
            "Odds ratios are exponentiated log-odds coefficients. Check separation, "
            "calibration, functional form, and independence assumptions. HC3 does not "
            "correct model misspecification."
        ),
    }


def estimate_frame(frame: pd.DataFrame, model: str, roles: dict):
    requires_entity = model == "entity_fe"
    data, outcome, predictors, entity = _prepare(
        frame, roles, require_entity=requires_entity
    )

    if model == "ols_hc3":
        return _ols(data, outcome, predictors)
    if model == "entity_fe":
        return _entity_fe(data, outcome, predictors, entity)
    if model == "logit":
        return _logit(data, outcome, predictors)
    raise ValueError(f"Estimator '{model}' is not implemented in this release.")


def estimate_json(csv_text: str, model: str, roles_json: str):
    frame = _frame(csv_text)
    roles = json.loads(roles_json or "{}")
    result = estimate_frame(frame, model, roles)

    # nobs is the exact sample passed to the estimator after its own complete-case
    # rules (including entity IDs for FE). Do not recalculate it using a different
    # subset of columns.
    result["specification"]["complete_cases"] = int(result["summary"]["nobs"])
    return json.dumps(result, allow_nan=False)
