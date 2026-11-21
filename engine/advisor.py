"""Transparent, deterministic methodological recommendation rules."""
from __future__ import annotations
import pandas as pd


def recommend(frame: pd.DataFrame, roles: dict) -> list[dict]:
    outcome = roles.get("outcome")
    entity = roles.get("entity")
    if not outcome or outcome not in frame.columns:
        return []
    y = frame[outcome].dropna()
    if y.empty:
        return []
    numeric = pd.api.types.is_numeric_dtype(y)
    unique = int(y.nunique())
    binary = unique == 2
    results = []
    if binary:
        results.append({
            "id": "logit", "name": "Binary logistic regression", "implemented": True,
            "reason": "The selected outcome has exactly two observed categories. A binary logit model estimates the conditional probability of one outcome category; verify the event coding and model specification.",
            "assumptions": ["Independent observations unless dependence is modeled", "Correct conditional mean specification", "No complete or quasi-complete separation"],
        })
    elif numeric:
        if entity and entity in frame.columns and frame[entity].nunique() > 1:
            results.append({
                "id": "entity_fe", "name": "One-way entity fixed effects", "implemented": True,
                "reason": "An entity identifier was supplied and the outcome is numeric. The within estimator removes time-invariant entity-level components. This is not a substitute for checking the panel structure, time effects, serial correlation, or identification assumptions.",
                "assumptions": ["Repeated observations per entity", "Within-entity variation in regressors", "Strict exogeneity for the conventional FE interpretation"],
            })
        results.append({
            "id": "ols_hc3", "name": "OLS with HC3 robust covariance", "implemented": True,
            "reason": "The selected outcome is numeric. OLS provides a baseline conditional-mean model, while HC3 covariance adjusts standard errors for heteroskedasticity under its regularity conditions.",
            "assumptions": ["Linear conditional mean is an appropriate approximation", "No perfect multicollinearity", "Independent sampling for conventional HC3 inference"],
        })
    else:
        results.append({
            "id": "not_supported", "name": "Categorical outcome — specification required", "implemented": False,
            "reason": "The outcome is non-numeric and has more than two observed categories. Recode or explicitly specify an ordinal or multinomial model before estimation.",
            "assumptions": ["Outcome scale and category ordering must be established"],
        })
    return results
