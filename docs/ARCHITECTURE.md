# OES Intelligence architecture

## Execution boundary

The browser application owns the selected file and sends its CSV text to a dedicated Web Worker. The worker initializes Pyodide, loads the compatible scientific Python packages, and executes the profiling, recommendation, and estimator modules in WebAssembly. The application has no endpoint for uploading datasets or running estimation remotely.

## Components

- `index.html`: single-page research workspace.
- `app/main.js`: user workflow, roles, recommendation selection, results rendering.
- `app/worker-client.js`: request/response correlation with the worker.
- `app/report.js`: local JSON and HTML report downloads.
- `runtime/worker.js`: Pyodide initialization and Python module execution.
- `engine/profiling.py`: CSV schema and descriptive profile.
- `engine/advisor.py`: deterministic recommendation rules with explicit rationale and assumptions.
- `engine/estimators.py`: OLS-HC3, one-way entity fixed effects, and binary logit.
- `tests/`: numerical and recommendation unit tests.

## Decision-support contract

Recommendations are conditional on observed data types and user-selected roles. They do not establish identification, exogeneity, correct functional form, or causal validity. The researcher must inspect the stated assumptions and choose the final model.

## Reproducibility

The initial browser manifest records a SHA-256 fingerprint of the exact CSV text, file name, timestamp, model, roles, and runtime family. The next reproducibility iteration should canonicalize parsed data and include transformations, estimator version, package versions, random generator/seed where applicable, convergence metadata, and a complete environment manifest.

## SaaS boundary

Authentication, billing, persistent workspace synchronization, team administration, and institutional entitlements are not implemented in this foundation. When introduced, the backend must not receive raw datasets. Entitlements must be verified by trusted server-side code; frontend flags cannot grant paid access.
