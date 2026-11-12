# Open Econometric Systems 1000 (OES-1000)

**A browser-native econometrics and statistical estimation library.**

OES-1000 is an independent, free estimation library targeting 1,000 genuinely distinct econometric and statistical models. Its primary methodological blueprint is the existing research website's Time-Series, Panel-Data, Causal-Inference, and Machine-Learning guides. The full mapping and required workflow standard are documented in [the methodology blueprint](docs/methodology-blueprint.md).

## Execution contract

- **Estimator language:** Python.
- **Runtime:** Pyodide / WebAssembly in the browser.
- **Execution:** browser-side only, in a Web Worker.
- **Estimation API:** none.
- **Dataset upload:** none; user data remains in the browser session.
- **Static assets:** the browser downloads application, Python modules, and compatible package assets from a static host/CDN. This is static asset delivery, not an estimation service.
- **Reproducibility:** deterministic seeds where supported, explicit estimator metadata, and numerical regression tests.

## Primary methodological source

- [Time-Series guide](https://tuhingm.github.io/almamun/research-guide/)
- [Panel-Data guide](https://tuhingm.github.io/almamun/panel-data-guide/)
- [Causal-Inference guide](https://tuhingm.github.io/almamun/causal-inference-guide/)
- [Machine-Learning guide](https://tuhingm.github.io/almamun/ml-guide/)
- [Existing browser OES](https://tuhingm.github.io/almamun/oes/)

Each model is intended to include its mathematical specification, data requirements, identification conditions, estimation algorithm, inference, diagnostics, guide-derived robustness procedures, numerical tests, and reproducible output. Model options such as lag length or covariance type do not inflate the distinct-model count.

## Browser integration status

The browser application now exposes the 44 existing OES estimator definitions through a generic Pyodide worker bridge. It dynamically renders each estimator's original input fields and calls the legacy engine's `run(model_id, csv_text, spec)` entry point. NumPy, SciPy, pandas, statsmodels, and scikit-learn are loaded in the browser runtime.

The `xgb` entry is visible but cannot execute in the standard Pyodide build because its native XGBoost runtime is unavailable. It is explicitly reported as unavailable rather than substituted with a different estimator. The other 43 legacy entries are routed through the browser engine, subject to their model-specific data and specification requirements.

To run locally, serve the repository over HTTP (not `file://`) and open `web/index.html`. GitHub Pages can serve the same static application from the repository root.

## Repository status

This repository is developed in validated stages. The 1,000 figure is a catalogue target, not a claim that 1,000 estimators are already complete.

| Status | Meaning |
|---|---|
| planned | Defined in the roadmap; not implemented |
| implemented | Estimator code exists |
| tested | Numerical tests pass against controlled fixtures |
| validated | Benchmark comparisons and documented assumptions are complete |

A catalogue entry is not production-ready merely because it is listed.

## Planned model allocation

| Family | Target |
|---|---:|
| Classical regression and GLM | 90 |
| Time-series econometrics | 165 |
| Panel-data econometrics | 165 |
| Causal inference and treatment effects | 105 |
| Bayesian econometrics and statistics | 110 |
| State-space, filtering and forecasting | 70 |
| Volatility and financial econometrics | 50 |
| Machine learning and statistical learning | 105 |
| Survival, duration and event-history models | 40 |
| Multivariate statistics and dimension reduction | 50 |
| Nonlinear, threshold and regime-switching models | 50 |
| **Total** | **1,000** |

## Architecture

```
oes-1000/
├── catalog/             # machine-readable model catalogue and schemas
├── src/oes1000/         # Python estimators and shared numerical routines
├── runtime/             # Pyodide Web Worker and browser bridge
├── web/                 # static browser application
├── examples/            # small, redistributable example datasets
├── tests/               # numerical, API-contract, and Pyodide tests
└── docs/                # estimator specifications and validation notes
```

## Numerical standards

Every estimator implementation must document:
1. Statistical model and parameterization.
2. Objective function, likelihood, moment conditions, or splitting criterion.
3. Estimation algorithm, initialization, tolerances, and convergence criteria.
4. Covariance estimator and inferential assumptions.
5. Identification and sample-size constraints.
6. Diagnostics and post-estimation quantities.
7. Guide-derived robustness and sensitivity procedures.
8. Reference implementation or published benchmark.
9. Unit tests, edge cases, and reproducibility behavior.
10. Pyodide compatibility and required packages.

## Development

```bash
python -m pip install -e ".[test]"
pytest
```

The browser runtime is hosted as static files. No server-side estimation endpoint is part of the design.

## License

License selection is pending. Do not assume that code or datasets copied from another project are relicensed by this repository.
