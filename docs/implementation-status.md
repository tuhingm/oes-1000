# Implementation status

## Current executable baseline

| Model ID | Estimator | Status | Inference |
|---|---|---|---|
| `ols` | Ordinary least squares | implemented; automated tests added | Classical, HC0, HC1, HC2, HC3 covariance |

The initial browser interface currently exposes OLS only. The Pyodide worker is a first runtime bridge and requires an end-to-end browser smoke test after GitHub Pages is enabled.

## Validation gates

- **Implemented:** code path exists and returns documented outputs.
- **Tested:** deterministic unit tests cover coefficient recovery, inference output shape, and failure conditions.
- **Validated:** benchmark comparison against a trusted implementation with tolerances and assumptions documented.

Do not upgrade a model's status without satisfying the corresponding gate.
