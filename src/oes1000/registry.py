"""Explicit estimator registry. Catalogue entries never imply implementation status."""

from __future__ import annotations

from typing import Callable, Any

_REGISTRY: dict[str, Callable[..., Any]] = {}


def register_estimator(model_id: str):
    if not model_id or not isinstance(model_id, str):
        raise ValueError("model_id must be a non-empty string")

    def decorator(func: Callable[..., Any]):
        if model_id in _REGISTRY:
            raise ValueError(f"Estimator already registered: {model_id}")
        _REGISTRY[model_id] = func
        return func
    return decorator


def get_estimator(model_id: str):
    try:
        return _REGISTRY[model_id]
    except KeyError as exc:
        raise KeyError(f"Estimator is not implemented: {model_id}") from exc


def list_estimators() -> list[str]:
    return sorted(_REGISTRY)
