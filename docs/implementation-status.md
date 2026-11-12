# Implementation status

## Catalogue progress

| Measure | Count | Status |
|---|---:|---|
| Accepted legacy OES models | 44 | Retained as validated legacy estimators |
| New catalogue additions in this development batch | 180 | Planned |
| Canonical catalogue entries | 224 / 1,000 | In progress |
| Remaining catalogue target | 776 | Not yet catalogued |
| New browser-native estimator implementations | 1 | OLS |

The accepted 44-model OES catalogue is carried forward without re-auditing, as directed. Its existing legacy implementation entry point is preserved. The additional 180 entries are model specifications, not claims of completed implementations.

## Current browser-native executable baseline

| Model ID | Estimator | Status | Inference |
|---|---|---|---|
| `ols` | Ordinary least squares | implemented and tested in the new Pyodide worker | Classical, HC0, HC1, HC2, HC3 covariance |

The existing legacy models retain their established OES engine entry point. The current new browser interface still exposes the new OLS path; legacy browser wiring and the new catalogue models are separate implementation tasks.

## Validation gates

- **Planned:** distinct model specification and catalogue metadata exist.
- **Implemented:** executable estimator code exists and returns documented outputs.
- **Tested:** deterministic numerical tests pass against controlled fixtures.
- **Validated:** benchmark comparison, assumptions, tolerances, diagnostics, and documented robustness procedures are complete.

The 44 legacy models retain the accepted status assigned to the existing OES implementation. New entries remain planned until their estimator code and tests are added.
