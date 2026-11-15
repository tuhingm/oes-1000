# OES-1000 synthetic datasets

All files in this directory are independently generated synthetic fixtures. They contain no copied source-site example data and no empirical observations. Fixed generator seed: 727. They are designed for software demonstrations and estimator tests, not substantive inference.

| File | Structure | Rows | Main use |
|---|---:|---:|---|
| synthetic_macro_quarterly.csv | Quarterly time series | 240 | Dynamic time-series models and VAR/LP demonstrations |
| synthetic_labor_panel.csv | Firm-year panel | 432 | Panel estimators and heterogeneous effects |
| synthetic_policy_panel.csv | Region-year panel with staggered adoption | 576 | DiD, event-study and treatment-effect methods |
| synthetic_building_energy.csv | Cross-section | 420 | Prediction, regularization and nonlinear ML |
| synthetic_bayesian_monthly.csv | Monthly multivariate series | 180 | Bayesian time-series and VAR illustrations |
| synthetic_regime_series.csv | Regime-switching series | 600 | Markov-switching and volatility models |

The regime indicator in the final file is a simulation-only validation field. Estimation examples should omit it unless evaluating latent-state recovery. adoption_year is blank for never-treated units. The policy panel treatment effect is built into the synthetic DGP and should be treated as known only for simulation validation.
