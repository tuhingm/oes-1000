"""OES-1000: browser-native econometrics and statistical estimation."""

__version__ = "0.1.0"

from .registry import get_estimator, list_estimators, register_estimator
from .classical import ols as _ols  # register OLS\nfrom .classical import linear as _linear  # register additional linear estimators

__all__ = ["get_estimator", "list_estimators", "register_estimator", "__version__"]
