# OES Intelligence product roadmap

## Stage 1 — Intelligent browser foundation

- [x] Browser-local CSV workflow
- [x] Data schema and missingness profile
- [x] Transparent outcome-aware recommendation rules
- [x] OLS with HC3 covariance
- [x] One-way entity fixed effects with entity-clustered covariance
- [x] Binary logistic regression with HC3 covariance
- [x] JSON and HTML report downloads
- [ ] Execute browser/Pyodide smoke tests in CI
- [ ] Broader reference validation and edge-case coverage

## Stage 2 — Statistical intelligence

- Variable transformation and coding advisor
- Missing-data diagnostics and explicit handling strategies
- Functional-form and multicollinearity diagnostics
- Heteroskedasticity, serial-correlation, cross-sectional-dependence, and stationarity workflows where design permits
- Time-series and panel identification decision trees
- Robustness-specification generator with researcher approval
- Model comparison with clearly defined comparable samples and criteria

## Stage 3 — Reproducible research

- Canonical dataset fingerprint
- Full analysis manifest and software environment
- Reproducible Python script export
- LaTeX tables and structured DOCX reports
- Local project history and rerunnable specifications

## Stage 4 — Commercial SaaS

- Supabase authentication and organization accounts
- Server-verified entitlements and subscription lifecycle
- Stripe billing and signed webhook processing
- Workspace metadata synchronization, excluding raw datasets
- Institutional roles, collaboration, and administration

## Stage 5 — Specialized products

- Advanced quantitative risk and financial econometrics
- Separate clinical-trial design and biostatistics module
- Group sequential designs, alpha spending, power, sample size, survival analysis, and simulation with independent validation

## Release rule

A catalogue entry is not executable because it appears in a menu. A method is released only after implementation, unit tests, reference-result comparison, edge-case testing, browser-runtime verification, and documented assumptions.
