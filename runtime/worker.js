/* OES-1000 browser estimation worker. All estimation and data handling remain local. */
let runtimePromise;
const ROOT = new URL("../src/oes1000/legacy/oes_engine/", self.location.href);
const MODULES = [
  "__init__.py", "_causal_core.py", "_diff_gmm.py", "_ml_core.py",
  "_panel_core.py", "_panel_tests.py", "bayes.py", "causal.py",
  "core.py", "markov.py", "ml.py", "panel.py", "pvar.py",
  "statespace_var.py", "timeseries.py"
];

async function initialize() {
  if (!runtimePromise) {
    importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js");
    runtimePromise = (async () => {
      const py = await loadPyodide();
      await py.loadPackage(["numpy", "scipy", "pandas", "statsmodels", "scikit-learn"]);
      py.FS.mkdirTree("/oes1000/legacy/oes_engine");
      for (const name of MODULES) {
        const url = new URL(name, ROOT);
        const response = await fetch(url);
        if (!response.ok) throw new Error("Could not load OES engine module: " + name);
        py.FS.writeFile("/oes1000/legacy/oes_engine/" + name, await response.text());
      }
      py.runPython("import sys; sys.path.insert(0, '/')");
      const rawCatalog = await py.runPythonAsync(
        "import json; from oes1000.legacy.oes_engine import catalog_json; catalog_json()"
      );
      return { py, catalog: JSON.parse(rawCatalog) };
    })();
  }
  return runtimePromise;
}

self.onmessage = async (event) => {
  const { id, action, payload = {} } = event.data || {};
  try {
    const { py, catalog } = await initialize();
    if (action === "ping") {
      self.postMessage({ id, ok: true, result: { runtime: "Pyodide 0.27.2", execution: "browser-worker", local: true } });
      return;
    }
    if (action === "catalog") {
      self.postMessage({ id, ok: true, result: catalog });
      return;
    }
    if (action === "estimate") {
      py.globals.set("oes_model_id", String(payload.model_id));
      py.globals.set("oes_csv_text", String(payload.csv_text));
      py.globals.set("oes_spec_json", JSON.stringify(payload.spec || {}));
      const output = await py.runPythonAsync(
        "import json; from oes1000.legacy.oes_engine import run_json; run_json(oes_model_id, oes_csv_text, oes_spec_json)"
      );
      const result = JSON.parse(output);
      if (result && result.error) throw new Error(result.error);
      self.postMessage({ id, ok: true, result });
      return;
    }
    throw new Error("Unknown worker action: " + action);
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error && error.message || error) });
  }
};
