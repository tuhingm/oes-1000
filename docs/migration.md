# Migration from the existing OES engine

The original 44-model OES catalogue and its Python implementation modules have been preserved in this repository as a compatibility baseline.

- Catalogue snapshot: `catalog/legacy-oes-catalog.json`
- Reference fixtures: `tests/legacy-expected.json`
- Python package snapshot: `src/oes1000/legacy/oes_engine/`

The migrated package is intentionally kept under a `legacy` namespace at this stage. It has not yet been promoted wholesale into the OES-1000 public registry. Each model must be audited for import dependencies, Pyodide wheel availability, output-contract consistency, and numerical tests before it is marked implemented or validated in the new catalogue.

The initial OES-1000 browser application currently calls the new OLS implementation. Subsequent migration work will expose additional estimators through the new registry and UI while preserving the original implementations for reference and regression comparison.
