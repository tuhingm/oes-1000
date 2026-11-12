"""DataFrame/CSV adapter for the OES-1000 estimator registry."""
from __future__ import annotations
import json
from typing import Any
import numpy as np
import pandas as pd
import oes1000  # noqa: F401 - register estimator modules
from oes1000.registry import get_estimator

def _jsonable(value: Any):
    if isinstance(value, dict): return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray): return _jsonable(value.tolist())
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.floating): return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_): return bool(value)
    if isinstance(value, float) and not np.isfinite(value): return None
    return value

def estimate_frame(frame: pd.DataFrame, model_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Run a registered estimator on named DataFrame columns."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("The input dataset is empty.")
    if not isinstance(spec, dict): raise TypeError("spec must be a dictionary.")
    dependent, regressors = spec.get("dependent"), spec.get("regressors")
    if not dependent or dependent not in frame.columns:
        raise ValueError("Choose a valid dependent-variable column.")
    if isinstance(regressors, str): regressors = [regressors]
    if not isinstance(regressors, list) or not regressors:
        raise ValueError("Choose at least one explanatory variable.")
    if dependent in regressors:
        raise ValueError("The dependent variable cannot also be an explanatory variable.")
    missing = [c for c in regressors if c not in frame.columns]
    if missing: raise ValueError("Unknown explanatory column(s): " + ", ".join(missing))
    selected = frame[[dependent, *regressors]].apply(pd.to_numeric, errors="coerce").dropna()
    y = selected[dependent].to_numpy(dtype=float)
    X = selected[regressors].to_numpy(dtype=float)
    kwargs = {"add_constant": bool(spec.get("add_constant", True))}
    if model_id == "wls":
        weight_col = spec.get("weights")
        if not weight_col or weight_col not in frame.columns:
            raise ValueError("WLS requires a valid positive weights column.")
        w = pd.to_numeric(frame.loc[selected.index, weight_col], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(w).all() or np.any(w <= 0):
            raise ValueError("WLS weights must be finite and strictly positive.")
        kwargs["weights"], kwargs["cov_type"] = w, spec.get("cov_type", "HC1")
    elif model_id == "gls":
        sigma = spec.get("sigma")
        if sigma is None:
            raise ValueError("GLS requires an explicit n×n covariance matrix in spec['sigma']; no covariance structure is inferred.")
        kwargs["sigma"] = np.asarray(sigma, dtype=float)
    elif model_id == "quantile_regression":
        kwargs["quantile"] = float(spec.get("quantile", 0.5))
    elif model_id in {"huber_regression", "tukey_bisquare"}:
        kwargs["tuning"] = float(spec.get("tuning", 1.345 if model_id == "huber_regression" else 4.685))
    result = dict(get_estimator(model_id)(y, X, **kwargs))
    result.update({"model": model_id, "nobs_input": int(len(frame)),
                   "nobs_dropped": int(len(frame)-len(selected)),
                   "dependent": dependent, "regressors": regressors})
    return _jsonable(result)

def estimate_csv(csv_text: str, model_id: str, spec_json: str) -> str:
    """CSV/JSON adapter for Pyodide and browser workers."""
    import io
    spec = json.loads(spec_json)
    frame = pd.read_csv(io.StringIO(csv_text), sep=None, engine="python")
    return json.dumps(estimate_frame(frame, model_id, spec), allow_nan=False)
