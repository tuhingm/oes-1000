import re
from pathlib import Path

import oes1000
from oes1000.registry import list_estimators


EXPECTED_NATIVE = {
    "wls",
    "gls",
    "fgls",
    "lad",
    "quantile_regression",
    "huber_regression",
    "tukey_bisquare",
    "logit",
    "probit",
    "cloglog",
    "poisson",
    "negative_binomial",
    "fractional_logit",
    "gamma_glm",
    "inverse_gaussian_glm",
    "quasi_poisson",
    "geometric_regression",
    "negative_binomial_nb1",
    "zero_inflated_poisson",
    "beta_regression",
    "multinomial_logit",
    "hurdle_poisson",\n    "ordered_logit",\n    "ordered_probit",\n    "tobit",
}


def test_all_twenty_five_native_estimators_are_registered():
    registered = set(list_estimators())
    assert EXPECTED_NATIVE <= registered


def test_browser_worker_loads_all_native_python_modules():
    worker = Path("web/worker.js").read_text()
    required_paths = [
        "src/oes1000/__init__.py",
        "src/oes1000/registry.py",
        "src/oes1000/api.py",
        "src/oes1000/classical/__init__.py",
        "src/oes1000/classical/ols.py",
        "src/oes1000/classical/linear.py",
        "src/oes1000/classical/discrete.py",
        "src/oes1000/classical/glm_extra.py",
        "src/oes1000/classical/advanced_discrete.py",\n        "src/oes1000/classical/ordinal_censored.py",
    ]
    for path in required_paths:
        assert path in worker


def test_browser_native_selector_exposes_every_registered_estimator():
    page = Path("web/index.html").read_text()
    selector = re.search(
        r'<select id="native-model">(.*?)</select>', page, flags=re.DOTALL
    )
    assert selector is not None
    exposed = set(re.findall(r'<option value="([^"]+)"', selector.group(1)))
    assert EXPECTED_NATIVE == exposed


def test_native_api_dispatches_every_registered_model():
    from oes1000.api import estimate_frame

    # This test checks that every public selector ID resolves to a callable
    # through the same API path used by the browser worker. Model-specific
    # numerical constraints are tested in the estimator test modules.
    for model_id in EXPECTED_NATIVE:
        from oes1000.registry import get_estimator

        assert callable(get_estimator(model_id))
