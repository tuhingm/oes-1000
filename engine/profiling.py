"""Local CSV schema inspection and descriptive data profiling."""
from __future__ import annotations
import json
from io import StringIO
import numpy as np
import pandas as pd


def read_frame(csv_text: str) -> pd.DataFrame:
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise ValueError("The CSV file is empty.")
    frame = pd.read_csv(StringIO(csv_text))
    if frame.empty:
        raise ValueError("The CSV contains no observations.")
    if frame.columns.duplicated().any():
        raise ValueError("The CSV contains duplicate column names. Rename them before analysis.")
    return frame


def _json_default(value):
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return None if not np.isfinite(value) else float(value)
    if pd.isna(value): return None
    return str(value)


def schema_json(csv_text: str) -> str:
    frame = read_frame(csv_text)
    return json.dumps({"rows": int(len(frame)), "columns": [str(c) for c in frame.columns]}, default=_json_default)


def profile_frame(frame: pd.DataFrame, roles: dict | None = None) -> dict:
    roles = roles or {}
    variables = []
    for name in frame.columns:
        series = frame[name]
        nonmissing = series.dropna()
        numeric = pd.api.types.is_numeric_dtype(series)
        if numeric:
            kind = "numeric"
            if nonmissing.empty:
                summary = "No observed values"
            else:
                summary = f"mean {nonmissing.mean():.4g}; SD {nonmissing.std():.4g}; range [{nonmissing.min():.4g}, {nonmissing.max():.4g}]"
        else:
            kind = "categorical / text"
            top = nonmissing.astype(str).value_counts().head(1)
            summary = "No observed values" if top.empty else f"most frequent: {top.index[0]} ({int(top.iloc[0])})"
        variables.append({
            "name": str(name), "kind": kind, "missing": int(series.isna().sum()),
            "missing_pct": float(series.isna().mean() * 100), "unique": int(series.nunique(dropna=True)),
            "summary": summary,
        })
    missing = int(frame.isna().sum().sum())
    return {
        "summary": {"rows": int(len(frame)), "columns": int(frame.shape[1]),
                    "missing_cells": missing, "duplicate_rows": int(frame.duplicated().sum())},
        "variables": variables,
        "roles": roles,
    }


def profile_json(csv_text: str, roles_json: str = "{}") -> str:
    from .advisor import recommend
    frame = read_frame(csv_text)
    roles = json.loads(roles_json or "{}")
    result = profile_frame(frame, roles)
    result["recommendations"] = recommend(frame, roles)
    return json.dumps(result, default=_json_default, allow_nan=False)
