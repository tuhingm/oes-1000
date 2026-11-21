/* All dataset parsing, profiling and estimation happen in this dedicated browser worker. */
let pyodidePromise;
let requestQueue = Promise.resolve();

const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
const PYTHON_MODULES = ["profiling.py", "advisor.py", "estimators.py", "__init__.py"];

function withTimeout(promise, label, milliseconds) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(
      () => reject(new Error(label + " timed out after " + Math.round(milliseconds / 1000) + " seconds")),
      milliseconds
    );
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
}

async function initialize() {
  if (!pyodidePromise) {
    const attempt = (async () => {
      postMessage({ type: "status", text: "Loading Pyodide JavaScript runtime…" });
      importScripts(PYODIDE_URL + "pyodide.js");
      const py = await withTimeout(
        loadPyodide({ indexURL: PYODIDE_URL }),
        "Pyodide WebAssembly initialization",
        90_000
      );

      postMessage({ type: "status", text: "Installing NumPy, pandas, SciPy and statsmodels…" });
      await withTimeout(
        py.loadPackage(["numpy", "pandas", "scipy", "statsmodels"]),
        "Scientific Python package installation",
        150_000
      );

      py.FS.mkdirTree("/oes_intelligence/engine");
      for (const name of PYTHON_MODULES) {
        postMessage({ type: "status", text: "Loading OES engine module: " + name });
        const response = await withTimeout(
          fetch(new URL("../engine/" + name, self.location.href)),
          "Fetching OES engine module " + name,
          20_000
        );
        if (!response.ok) {
          throw new Error("Could not load engine module " + name + " (HTTP " + response.status + ")");
        }
        py.FS.writeFile(
          "/oes_intelligence/engine/" + name,
          await response.text()
        );
      }

      postMessage({ type: "status", text: "Importing OES statistical engine…" });
      py.runPython(
        "import sys; sys.path.insert(0, '/oes_intelligence'); import engine"
      );
      postMessage({ type: "ready", version: py.version });
      return py;
    })();

    pyodidePromise = attempt;
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
