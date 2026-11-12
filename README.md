# Open Econometric Systems 1000 (OES-1000)

**A browser-native econometrics and statistical estimation library.**

OES-1000 is designed to provide a broad catalogue of econometric and statistical estimators executed locally in the user's browser with Python running in Pyodide. The application uses Web Workers to keep estimation work off the UI thread.

## Execution contract

- **Estimator language:** Python.
- **Runtime:** Pyodide / WebAssembly in the browser.
- **Execution:** browser-side only, in a Web Worker.
- **Estimation API:** none.
- **Dataset upload:** none; user data remains in the browser session.
- **Static assets:** the browser downloads the application, Python modules, and compatible package assets from the static host/CDN. This is static asset delivery, not an estimation service.
- **Reproducibility:** deterministic seeds where supported, explicit estimator metadata, and numerical regression tests.

## Repository status

This repository is the independent home for OES-1000. It is being developed in validated stages. The target catalogue size is 1,000 genuinely distinct estimators/specifications; the target is not represented as 1,000 completed implementations.

Model lifecycle labels:

| Status | Meaning |
|---|---|
| planned | Defined in the roadmap; not implemented |
| implemented | Estimator code exists |
| tested | Numerical tests pass against controlled fixtures |
| validated | Benchmark comparisons and documented assumptions are complete |

A model must not be counted as production-ready merely because it appears in the catalogue.

## Planned model allocation

| Family | Target |
|---|---:|
| Classical regression and GLM | 100 |
| Time-series econometrics | 150 |
| Panel-data econometrics | 150 |
| Causal inference and treatment effects | 100 |
| Bayesian econometrics and statistics | 120 |
| State-space, filtering and forecasting | 80 |
| Volatility and financial econometrics | 60 |
| Machine learning and statistical learning | 100 |
| Survival, duration and event-history models | 40 |
| Multivariate statistics and dimension reduction | 50 |
| Nonlinear, threshold and regime-switching models | 50 |
| **Total** | **1,000** |

## Architecture

```text
oes-1000/
├── catalog/             # machine-readable model catalogue and schemas
├── src/oes1000/         # Python estimators and shared numerical routines
│   ├── classical/
│   ├── timeseries/
│   ├── panel/
│   ├── causal/
│   ├── bayesian/
│   ├── statespace/
│   ├── volatility/
│   ├── machine_learning/
│   ├── survival/
│   ├── multivariate/
│   └── nonlinear/
├── runtime/             # Pyodide Web Worker and browser bridge
├── web/                 # static browser application
├── examples/            # small, redistributable example datasets
├── tests/               # numerical, API-contract, and Pyodide tests
└── docs/                # estimator specifications and validation notes
```

## Numerical standards

Every estimator implementation must document:

1. Statistical model and parameterization.
2. Objective function / likelihood / moment conditions.
3. Estimation algorithm and convergence criteria.
4. Covariance estimator and inferential assumptions.
5. Identification and sample-size constraints.
6. Diagnostics and post-estimation quantities.
7. Reference implementation or published benchmark.
8. Unit tests, edge cases, and reproducibility behavior.

The catalogue records estimator identity separately from options such as lag order, covariance type, deterministic terms, and prior hyperparameters. Such options do not inflate the model count.

## Development

Python-native tests can be run with:

```bash
python -m pip install -e ".[test]"
pytest
```

The browser runtime is hosted as static files. No server-side estimation endpoint is part of the design.

## License

License selection is pending. Do not assume that code or datasets copied from another project are relicensed by this repository.
