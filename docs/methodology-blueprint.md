# OES-1000 methodological blueprint

## Authority and scope

The primary methodological blueprint is the owner's existing research website:

- Time-series guide: https://tuhingm.github.io/almamun/research-guide/
- Panel-data guide: https://tuhingm.github.io/almamun/panel-data-guide/
- Causal-inference guide: https://tuhingm.github.io/almamun/causal-inference-guide/
- Machine-learning guide: https://tuhingm.github.io/almamun/ml-guide/
- Existing browser OES: https://tuhingm.github.io/almamun/oes/

These guides define the methodological coverage and the level of workflow completeness expected in OES-1000. The guides are not simply a source of estimator names. Their equations, decision rules, estimation steps, diagnostic procedures, robustness exercises, interpretations, and examples are the reference specification. OES-1000 is a separate repository and must not modify the source website.

## Model families verified in the website repository

### Time-series econometrics

Guide pages currently present:
- OLS: `research-guide/ols.html`
- ARDL: `research-guide/ardl.html`
- NARDL: `research-guide/nardl.html`
- VAR: `research-guide/var.html`
- VECM: `research-guide/vecm.html`
- GMM: `research-guide/gmm.html`

Required workflow coverage includes integration-order assessment; I(2) exclusion where bounds methods require it; lag-order selection; deterministic-term selection; cointegration/rank testing; model estimation; long-run and short-run effects; error-correction speed; dynamic multipliers where applicable; residual serial-correlation, heteroskedasticity and ARCH diagnostics; stability and structural-break checks; IRFs/FEVD for VAR systems; alternative lag structures, covariance estimators, and sample windows.

### Panel-data econometrics

Guide pages currently present:
- Pooled OLS: `panel-data-guide/pols.html`
- Fixed effects: `panel-data-guide/fe.html`
- Random effects: `panel-data-guide/re.html`
- Difference GMM: `panel-data-guide/gmm.html`
- FE with Driscoll-Kraay covariance: `panel-data-guide/fedk.html`
- Mean Group / CCE-MG: `panel-data-guide/mg.html`
- First differences: `panel-data-guide/diff.html`
- Pooled Mean Group: `panel-data-guide/pmg.html`
- Cross-sectionally augmented ARDL: `panel-data-guide/csardl.html`

Required workflow coverage includes panel indexing and balance diagnostics; pooled/FE/RE comparisons; Hausman or correlated-random-effects/Mundlak comparisons where appropriate; cross-sectional dependence; slope heterogeneity; panel unit-root and cointegration tests; serial-correlation and heteroskedasticity-robust inference; dynamic-panel instrument construction and validity diagnostics; heterogeneous long-run/short-run dynamics; CCE augmentation; sensitivity to lag orders and cross-sectional-average specifications; alternative estimators and sample restrictions.

Specific guide-driven robustness templates:
- Difference GMM: vary instrument windows and collapsed versus uncollapsed instruments; report instrument count, AR(2), Hansen/Sargan diagnostics, and persistence.
- FE-DK: compare DK bandwidths, two-way fixed effects, and CCE alternatives; report cross-sectional-dependence evidence.
- MG/CCE-MG: compare homogeneous FE baselines with heterogeneous-slope estimators and assess residual cross-sectional dependence.
- PMG: compare PMG, MG, and DFE; report Hausman comparison and adjustment speeds; make exclusion of anomalous adjustment units an explicit sensitivity option.
- CS-ARDL: vary the lag length of cross-sectional averages (including zero, one, and two lags where supported); compare long-run coefficients and residual CD.

### Causal inference

Guide pages currently present:
- Difference-in-differences: `causal-inference-guide/did.html`
- Generalized synthetic control: `causal-inference-guide/gsc.html`
- Interrupted time series: `causal-inference-guide/its.html`
- Instrumental variables: `causal-inference-guide/iv.html`
- Regression discontinuity: `causal-inference-guide/rdd.html`
- Synthetic control: `causal-inference-guide/scm.html`
- Staggered treatment adoption: `causal-inference-guide/staggered.html`

Required workflow coverage includes treatment/control and timing definitions; identifying assumptions; estimator and estimand definitions; pre-treatment fit/trend assessment; placebo and falsification exercises; sensitivity to bandwidth, donor pool, comparison group, covariate set, and event window; inference appropriate to the design; graphical event-study or counterfactual outputs; explicit interpretation of the identifying variation.

### Machine learning and statistical learning

Guide pages currently present:
- Causal forest: `ml-guide/causal-forest.html`
- Double/debiased ML — IRM: `ml-guide/dml-irm.html`
- Double/debiased ML — IV: `ml-guide/dml-iv.html`
- Double/debiased ML — PLR: `ml-guide/dml-plr.html`
- Elastic net: `ml-guide/enet.html`
- Lasso: `ml-guide/lasso.html`
- Random forest: `ml-guide/rf.html`
- Ridge: `ml-guide/ridge.html`
- Gradient boosting / XGBoost guide: `ml-guide/xgb.html`

Required workflow coverage includes preprocessing and feature definitions; train/test or cross-fitting splits; tuning and validation; out-of-sample metrics; regularization and feature selection; uncertainty and stability checks; treatment-effect heterogeneity for causal learners; sensitivity to folds, seeds, learners, and tuning grids. The XGBoost guide is a methodological reference; browser deployment must use a compatible implementation or a clearly identified alternative, not silently claim the external package is available in Pyodide.

## Cross-cutting implementation contract

Every catalogue entry must define:
1. Unique model ID and family.
2. Mathematical specification and estimand/parameterization.
3. Required data shape, variable roles, and sample constraints.
4. Identification assumptions and pre-estimation decision rules.
5. Objective function, likelihood, moment conditions, or splitting criterion.
6. Estimation algorithm, optimizer, initialization, tolerances, and convergence reporting.
7. Covariance estimator, standard errors, confidence intervals, and test distributions.
8. Diagnostics and post-estimation quantities.
9. Guide-derived robustness menu, including what changes and what is held fixed.
10. Numerical reference fixture, expected outputs/tolerances, and test status.
11. Pyodide compatibility and required packages.
12. Output tables, plots, and export schema.

A model is not complete merely because the point estimator runs. Its guide-specific diagnostics and robustness workflow must also be implemented or explicitly marked as unavailable with a reason.

## Counting and status policy

The 1,000 target counts distinct statistical specifications or estimators. Changing only lag length, deterministic terms, covariance type, bandwidth, prior hyperparameters, or tuning values does not create a new model. Those are options or robustness configurations of the parent estimator.

Use the repository lifecycle labels strictly:
- `planned`: specification/catalogue entry exists.
- `implemented`: executable estimator code exists.
- `tested`: controlled numerical tests pass.
- `validated`: benchmark comparison, assumptions, and documented tolerances are complete.

Never infer implementation or validation from a guide page or a catalogue record.

## Browser execution architecture

All estimation runs in Python within Pyodide in a Web Worker. The website downloads static application and package assets only. There is no estimation API, server-side Python execution, or dataset upload endpoint. The worker must return structured results, diagnostics, warnings, and errors to the UI. Heavy computations must not block the browser main thread.

Prefer NumPy/SciPy/Pandas implementations and Pyodide-compatible dependencies. External libraries unavailable in Pyodide must be replaced by a documented numerical implementation or excluded from the browser runtime; do not silently change an estimator's statistical definition.

## Source inventory and migration policy

The source website remains authoritative and separate. OES-1000 may port the owner's Python implementation files into this repository, preserving method names and behavior where feasible, but each port must receive independent tests and a Pyodide compatibility review. Guide HTML is methodological documentation; it should be represented in OES-1000 as structured specifications and concise implementation documentation rather than copied wholesale into the application.

The website also contains guide-specific implementation folders and example datasets. These are part of the source inventory and should be mapped into OES-1000 fixtures when suitable. Dataset provenance, licensing, and redistribution permission must be recorded before packaging data.

## Primary source URLs

- https://github.com/tuhingm/almamun/tree/main/research-guide
- https://github.com/tuhingm/almamun/tree/main/panel-data-guide
- https://github.com/tuhingm/almamun/tree/main/causal-inference-guide
- https://github.com/tuhingm/almamun/tree/main/dsge-guide
- https://github.com/tuhingm/almamun/tree/main/ml-guide
- https://github.com/tuhingm/almamun/tree/main/panel-data-guide/implementations
- https://github.com/tuhingm/almamun/tree/main/causal-inference-guide/implementations
- https://github.com/tuhingm/almamun/tree/main/research-guide/examples
- https://github.com/tuhingm/almamun/tree/main/panel-data-guide/examples
- https://github.com/tuhingm/almamun/tree/main/causal-inference-guide/examples
- https://github.com/tuhingm/almamun/tree/main/ml-guide/examples
