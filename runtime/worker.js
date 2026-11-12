/* OES-1000 Pyodide worker: all estimation occurs inside this browser worker. */
let pyodidePromise;

async function getRuntime() {
  if (!pyodidePromise) {
    importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js");
    pyodidePromise = (async () => {
      const pyodide = await loadPyodide();
      await pyodide.loadPackage(["numpy", "scipy"]);
      const base = new URL("../src/oes1000/", self.location.href);
      const files = [
        ["__init__.py", ""],
        ["registry.py", ""],
        ["classical/__init__.py", ""],
        ["classical/ols.py", ""]
      ];
      pyodide.FS.mkdirTree("/oes1000/classical");
      for (const [relative] of files) {
        const url = new URL(relative, base);
        const response = await fetch(url);
        if (!response.ok) throw new Error("Cannot load estimator module: " + url);
        const source = await response.text();
        pyodide.FS.writeFile("/oes1000/" + relative, source);
      }
      pyodide.runPython("import sys; sys.path.insert(0, '/')");
      return pyodide;
    })();
  }
  return pyodidePromise;
}

self.onmessage = async (event) => {
  const { id, action, payload } = event.data || {};
  try {
    const pyodide = await getRuntime();
    if (action === "estimate") {
      pyodide.globals.set("y_input", payload.y);
      pyodide.globals.set("x_input", payload.X);
      pyodide.globals.set("cov_input", payload.cov_type || "HC1");
      const output = await pyodide.runPythonAsync(`
import json
import numpy as np
from oes1000.classical.ols import estimate_ols
_fit = estimate_ols(np.asarray(y_input, dtype=float), np.asarray(x_input, dtype=float), cov_type=str(cov_input))
json.dumps({
 "model": _fit["model"], "nobs": _fit["nobs"],
 "params": _fit["params"].tolist(),
 "std_errors": _fit["std_errors"].tolist(),
 "t_statistics": _fit["t_statistics"].tolist(),
 "p_values": _fit["p_values"].tolist(),
 "r_squared": _fit["r_squared"],
 "adjusted_r_squared": _fit["adjusted_r_squared"],
 "cov_type": _fit["cov_type"]
})
`);
      self.postMessage({ id, ok: true, result: JSON.parse(output) });
    } else if (action === "ping") {
      self.postMessage({ id, ok: true, result: { runtime: "Pyodide", execution: "browser-worker" } });
    } else {
      throw new Error("Unknown worker action: " + action);
    }
  } catch (error) {
    self.postMessage({ id, ok: false, error: String(error && error.message || error) });
  }
};
