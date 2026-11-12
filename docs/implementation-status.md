# Implementation status

## Legacy OES browser integration

The existing 44-model OES engine is now wired into the OES-1000 browser application.

- The browser loads the legacy Python engine modules from the repository's static assets.
- Pyodide initializes NumPy, SciPy, pandas, statsmodels, and scikit-learn.
- The worker exposes the legacy estimator catalogue and a generic `run(model_id, csv_text, spec)` bridge.
- The browser dynamically renders each model's original input fields from the engine catalogue.
- CSV parsing and estimation execute locally in the browser worker. No estimation API or dataset upload endpoint is used.
- The existing estimator definitions and model IDs are preserved.

| Legacy integration item | Count / status |
|---|---:|
| Legacy model definitions exposed in browser UI | 44 |
| Legacy models routed through generic browser worker | 44 |
| Models with a known Pyodide native-dependency limitation | 1 (`xgb`) |
| Other legacy models available for browser execution, subject to model-specific data/specification requirements | 43 |

**XGBoost limitation:** the `xgb` model is visible in the selector, but is blocked with an explicit message because the native XGBoost runtime is not part of the standard Pyodide package set. It is not silently replaced by another estimator.

## Catalogue progress

| Measure | Count | Status |
|---|---:|---|
| Accepted legacy OES models | 44 | Retained as validated legacy estimators |
| New catalogue additions in this development batch | 956 | Planned |
| Canonical catalogue entries | 1,000 / 1,000 | Catalogue complete |
| Remaining catalogue target | 0 | Catalogue complete; implementation remains in progress |
| New Python-native estimators | 12 | Implemented; worker route and dedicated browser panel committed |
| Legacy models exposed through browser interface | 44 | Integrated; XGBoost runtime limitation documented |

The accepted 44-model OES catalogue is carried forward without re-auditing, as directed. Their existing implementation entry points and specifications are retained. The additional 956 entries are model specifications, not claims of completed implementations. The catalogue is complete at 1,000 unique IDs; these entries remain planned until estimator code, numerical tests, and benchmark validation are completed.

## Catalogue completion\n\nThe canonical catalogue contains exactly 1,000 unique model IDs: 44 retained legacy entries, 12 additional Python-native estimators marked implemented, and 944 planned specifications. The 12 additional estimators are WLS, GLS, AR(1) FGLS, LAD, quantile regression, Huber, Tukey bisquare, logit, probit, complementary log-log, Poisson, and negative binomial. They are registered in the Python package and exposed through a separate native route in the shared browser worker and a dedicated estimator panel. The browser page exposes a searchable catalogue with family and lifecycle filters. Only models with implemented estimator routes should be presented as executable.\n\n## Validation gates

- **Planned:** distinct model specification and catalogue metadata exist.
- **Implemented:** executable estimator code exists and returns documented outputs.
- **Tested:** deterministic numerical tests pass against controlled fixtures.
- **Validated:** benchmark comparison, assumptions, tolerances, diagnostics, and documented robustness procedures are complete.

The 44 legacy models retain the accepted status assigned to the existing OES implementation. Browser integration is a separate delivery status from that prior validation status.

## Native browser integration checks

A GitHub Actions workflow runs the Python test suite on pushes to `main` and pull requests. The native browser integration tests verify that all 12 estimator IDs are registered, every required Python module is loaded by `web/worker.js`, and the browser dropdown exposes exactly those 12 IDs. The test suite also includes numerical regression checks for the probit and complementary log-log expected-information covariance matrices. Static integration checks do not replace an actual Pyodide browser smoke test or broader cross-package benchmark validation.
