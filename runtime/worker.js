/* All dataset parsing, profiling and estimation happen in this dedicated browser worker. */
let pyodidePromise;
let requestQueue = Promise.resolve();

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
const PYTHON_MODULES = ["profiling.py", "advisor.py", "estimators.py", "__init__.py"];

async function initialize() {
  if (!pyodidePromise) {
    const attempt = (async () => {
      importScripts(PYODIDE_URL + "pyodide.js");
      postMessage({ type: "status", text: "Loading Pyodide WebAssembly runtime…" });
      const py = await loadPyodide({ indexURL: PYODIDE_URL });
      postMessage({ type: "status", text: "Loading NumPy, pandas, SciPy and statsmodels…" });
      await py.loadPackage(["numpy", "pandas", "scipy", "statsmodels"]);

      py.FS.mkdirTree("/oes_intelligence/engine");
      for (const name of PYTHON_MODULES) {
        const response = await fetch(new URL("../engine/" + name, self.location.href));
        if (!response.ok) {
          throw new Error("Could not load engine module " + name);
        }
        py.FS.writeFile(
          "/oes_intelligence/engine/" + name,
          await response.text()
        );
      }

      py.runPython(
        "import sys; sys.path.insert(0, '/oes_intelligence'); import engine"
      );
      postMessage({ type: "ready", version: py.version });
      return py;
    })();

    pyodidePromise = attempt;
    // A failed initialization must not permanently poison the worker. A later
    // request can retry after a transient CDN or package-loading failure.
    attempt.catch(() => {
      if (pyodidePromise === attempt) {
        pyodidePromise = undefined;
      }
    });
  }
  return pyodidePromise;
}

async function handleRequest(data) {
  const { id, action, payload = {} } = data || {};
  try {
    const py = await initialize();

    if (action === "schema") {
      py.globals.set("oes_csv", payload.csv_text);
      const raw = await py.runPythonAsync(
        "from engine.profiling import schema_json; schema_json(oes_csv)"
      );
      postMessage({ id, ok: true, result: JSON.parse(raw) });
      return;
    }

    if (action === "profile") {
      py.globals.set("oes_csv", payload.csv_text);
      py.globals.set("oes_roles", JSON.stringify(payload.roles || {}));
      const raw = await py.runPythonAsync(
        "from engine.profiling import profile_json; profile_json(oes_csv, oes_roles)"
      );
      postMessage({ id, ok: true, result: JSON.parse(raw) });
      return;
    }

    if (action === "estimate") {
      py.globals.set("oes_csv", payload.csv_text);
      py.globals.set("oes_model", payload.model);
      py.globals.set("oes_roles", JSON.stringify(payload.roles || {}));
      const raw = await py.runPythonAsync(
        "from engine.estimators import estimate_json; " +
        "estimate_json(oes_csv, oes_model, oes_roles)"
      );
      postMessage({ id, ok: true, result: JSON.parse(raw) });
      return;
    }

    throw new Error("Unknown worker action: " + action);
  } catch (error) {
    postMessage({ id, ok: false, error: String(error?.message || error) });
  }
}

// Pyodide's Python globals are shared by all requests. Serialize requests so
// concurrent UI actions cannot overwrite one another's inputs mid-estimation.
self.onmessage = ({ data }) => {
  requestQueue = requestQueue.then(() => handleRequest(data));
};
