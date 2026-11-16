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

The browser application exposes a searchable catalogue of 1,000 distinct model specifications, with family and lifecycle filters. The 44 accepted OES estimators remain connected through the legacy Pyodide worker bridge. Twenty-nine additional Python-native estimators (WLS, GLS, AR(1) FGLS, LAD, quantile, Huber, Tukey bisquare, logit, probit, complementary log-log, Poisson, and negative binomial, fractional logit, Gamma GLM, inverse-Gaussian GLM, quasi-Poisson, geometric count regression, NB1, zero-inflated Poisson, beta regression, multinomial logit, hurdle Poisson, ordered logit, ordered probit, Tobit, left-truncated regression, L2-penalized binomial logit, L2-penalized binomial probit, and Jordà local projections) are registered in the new package and exposed through a separate native-estimator panel and `native_run` worker command. The remaining 927 entries are planned specifications, not executable estimators. The native panel uses the Data section's CSV input and runs the new `oes1000.api.estimate_csv` adapter locally in the browser.

The `xgb` entry is visible but cannot execute in the standard Pyodide build because its native XGBoost runtime is unavailable. It is explicitly reported as unavailable rather than substituted with a different estimator. The other 43 legacy entries are routed through the browser engine, subject to their model-specific data and specification requirements. The 29 native routes have numerical unit tests and static browser-integration checks, including registry, worker-module, and UI-selector consistency. Probit and complementary log-log covariance tests verify the inverse expected Fisher information. Actual Pyodide browser smoke tests and broader cross-package benchmark validation remain outstanding.

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

## OES AI workspace

The interactive Gemini-powered research assistant is available at `web/ai/` and is linked from the main OES-1000 navigation. It provides six focused modes: Research Assistant, Econometrician, Statistical Methods, Code Laboratory, Results Interpreter, and Academic Writing.

The AI workspace is an assistance layer, not an estimation service. Gemini handles explanation, research design, interpretation guidance, and code drafting. Actual numerical estimation remains in the browser-based OES/Pyodide engine. The chat endpoint accepts conversation text and returns a structured Markdown answer; it does not receive a dataset for server-side estimation.

### Deploying the Gemini chat endpoint

1. Deploy `cloudflare-worker/worker.js` as the existing OES-1000 Cloudflare Worker.
2. Configure these Worker secrets in the Production environment:
   - `GEMINI_API_KEY`: your Google Gemini API key.
   - `OES_AI_TOKEN`: a separate high-entropy access token for the AI workspace.
   - `OES_DEV_TOKEN`: retain this separately for the restricted estimator-drafting endpoint.
3. In the OES AI workspace, enter the deployed Worker URL ending in `/chat` and the `OES_AI_TOKEN`.
4. The Gemini API key is never placed in frontend code or Git. The workspace access token is stored in session storage for the active browser session; use a private access token for controlled access and rotate it periodically.

The AI endpoint is protected by `OES_AI_TOKEN`, validates request size and conversation length, and uses the Worker-held Gemini key. The current Worker uses the supported Gemini `generateContent` REST endpoint. Google currently recommends its Interactions API for new agentic applications; a future migration can be made without changing the OES AI frontend contract.

Research notes in TXT/MD/JSON are attached as bounded text context. CSV attachments are summarized locally into column metadata before context is sent; raw CSV rows are not sent to Gemini. No uploaded dataset is passed to a server-side estimator.

## License

License selection is pending. Do not assume that code or datasets copied from another project are relicensed by this repository.

## Gemini development gateway

The Cloudflare Worker source is in `cloudflare-worker/worker.js`. It exposes:

- `POST /clean`: metadata-only data-cleaning plan generation.
- `POST /dev`: drafts one Python estimator module and its tests from a supplied model specification. The response is explicitly marked `draft_only`; generated code must be reviewed and tested before integration or catalogue status changes.

Configure these Cloudflare Worker secrets in the Production environment:

- `GEMINI_API_KEY`: Gemini API key.
- `OES_DEV_TOKEN`: a separate, high-entropy access token required by `POST /dev`, sent as the `X-OES-Dev-Token` request header. Do not put either secret in GitHub or public frontend code.

After deploying the Worker, the development endpoint is `https://YOUR-WORKER.workers.dev/dev`. Send JSON with `model_id`, `model_name`, `family`, `specification`, and optionally `package_path`. Do not send research datasets or confidential records. Gemini drafts code only; it does not commit to GitHub, run tests, or validate estimators. Those steps remain part of the maintainer review workflow.
