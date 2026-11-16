/**
 * OES-1000 Gemini Assistant Gateway
 * Routes:
 *   POST /clean  -> proposes safe, metadata-only data-cleaning operations
 *   POST /dev    -> drafts one estimator module and its tests for human review
 *
 * Cloudflare Worker secret required: GEMINI_API_KEY
 * Never place the Gemini key in browser code or repository files.
 */
const ALLOWED_ORIGIN = "https://tuhingm.github.io";
const MODEL = "gemini-flash-latest";
const GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent";

function cors() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-OES-Dev-Token, X-OES-AI-Token",
    "Vary": "Origin"
  };
}
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...cors() }
  });
}
async function callGemini(env, prompt, maxOutputTokens = 8192) {
  const response = await fetch(GEMINI_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-goog-api-key": env.GEMINI_API_KEY
    },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: {
        responseMimeType: "application/json",
        temperature: 0.15,
        maxOutputTokens
      }
    })
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.error?.message || "Gemini API request failed.";
    throw new Error("Gemini (" + response.status + "): " + message);
  }
  const output = payload.candidates?.[0]?.content?.parts?.map(part => part.text || "").join("") || "";
  if (!output) throw new Error("Gemini returned an empty response.");
  try {
    return JSON.parse(output);
  } catch {
    throw new Error("Gemini returned invalid JSON. Retry with a narrower specification.");
  }
}
function safeText(value, max = 4000) {
  return String(value ?? "").trim().slice(0, max);
}
function validIdentifier(value) {
  return /^[a-z][a-z0-9_]{1,63}$/.test(value);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      const origin = request.headers.get("Origin") || "";
      if (origin !== ALLOWED_ORIGIN) return new Response(null, { status: 403 });
      return new Response(null, { status: 204, headers: cors() });
    }
    if ((request.headers.get("Origin") || "") !== ALLOWED_ORIGIN) {
      return new Response("Origin not allowed.", { status: 403 });
    }
    if (request.method !== "POST") return json({ error: "Use POST." }, 405);
    if (!env.GEMINI_API_KEY) return json({ error: "Worker secret GEMINI_API_KEY is not configured." }, 500);

    const url = new URL(request.url);
    const route = url.pathname.replace(/\/+$/, "") || "/";
    if (route !== "/clean" && route !== "/dev" && route !== "/chat" && route !== "/") {
      return json({ error: "Unknown endpoint. Use /clean, /dev, or /chat." }, 404);
    }

    const declaredLength = Number(request.headers.get("Content-Length") || 0);
    if (declaredLength > 30000) return json({ error: "Request too large." }, 413);
    let input;
    try {
      const body = await request.text();
      if (body.length > 30000) return json({ error: "Request too large." }, 413);
      input = JSON.parse(body);
    } catch {
      return json({ error: "Invalid JSON." }, 400);
    }

    if (route === "/chat") {
      if (!env.OES_AI_TOKEN || request.headers.get("X-OES-AI-Token") !== env.OES_AI_TOKEN) {
        return json({ error: "Workspace access token is missing or invalid." }, 401);
      }
      const mode = safeText(input.mode, 32);
      const instruction = safeText(input.instruction, 3000);
      if (!instruction || !Array.isArray(input.messages) || input.messages.length < 1 || input.messages.length > 14) {
        return json({ error: "Provide an assistant instruction and between 1 and 14 conversation messages." }, 400);
      }
      const messages = input.messages.map(item => ({
        role: item && item.role === "model" ? "model" : "user",
        text: safeText(item && item.text, 6000)
      })).filter(item => item.text);
      if (!messages.length || messages[messages.length - 1].role !== "user") {
        return json({ error: "The final conversation message must be a non-empty user message." }, 400);
      }
      const conversation = messages.map((item, index) =>
        (item.role === "model" ? "ASSISTANT" : "USER") + " MESSAGE " + (index + 1) + ":\n" + item.text
      ).join("\n\n");
      const prompt = [
        "You are OES AI, the research intelligence layer of Open Econometric Systems 1000 (OES-1000).",
        "Your AI provider is Google Gemini. You assist with quantitative economics, econometrics, mathematical statistics, empirical research and reproducible scientific computing.",
        "ACTIVE MODE: " + mode,
        "MODE INSTRUCTIONS: " + instruction,
        "SYSTEM RULES:",
        "1. Be technically rigorous, direct and structured. Define notation and state assumptions when discussing estimators or mathematical results.",
        "2. Never fabricate papers, authors, DOIs, citations, numerical estimates, test statistics, p-values, or claims of code execution. If uncertain, say so.",
        "3. Distinguish theoretical explanation, suggested methodology, generated code, and empirically verified results.",
        "4. OES-1000 is the estimation engine. Gemini must not pretend it has executed OES estimators or inspected a user's local dataset. Numerical estimation must be performed by the OES browser/Pyodide runtime.",
        "5. When code is requested, provide complete runnable code and identify dependencies and assumptions. Do not claim that generated code has been tested.",
        "6. Do not ask users to paste API keys or secrets. Do not request raw confidential datasets.",
        "7. Return a JSON object with exactly one key named answer. The answer value must be a Markdown-formatted string. No other top-level keys.",
        "CONVERSATION:",
        conversation
      ].join("\n\n");
      try {
        const result = await callGemini(env, prompt, 8192);
        if (typeof result.answer !== "string" || !result.answer.trim()) {
          return json({ error: "Gemini returned an invalid assistant response. Please retry." }, 502);
        }
        return json({ answer: result.answer.slice(0, 24000), mode });
      } catch (error) {
        return json({ error: safeText(error.message, 1200) }, 502);
      }
    }

    if (route === "/dev") {
      if (!env.OES_DEV_TOKEN || request.headers.get("X-OES-Dev-Token") !== env.OES_DEV_TOKEN) {
        return json({ error: "Development endpoint unauthorized. Configure OES_DEV_TOKEN and send it in X-OES-Dev-Token." }, 401);
      }
      const modelId = safeText(input.model_id, 64);
      const modelName = safeText(input.model_name, 180);
      const family = safeText(input.family, 80);
      const specification = safeText(input.specification, 5000);
      const packagePath = safeText(input.package_path, 160);
      if (!validIdentifier(modelId) || !modelName || !family || !specification) {
        return json({ error: "Provide model_id, model_name, family, and a detailed specification." }, 400);
      }
      const prompt = [
        "You are a senior statistical-computing engineer contributing to OES-1000.",
        "Generate a DRAFT implementation for exactly one estimator. Do not claim it is validated.",
        "Return one JSON object with exactly these keys: model_id, module_code, test_code, mathematical_specification, assumptions, dependencies, validation_plan.",
        "Target runtime: Python 3 in Pyodide/WebAssembly. Prefer numpy, scipy, pandas, and statsmodels only when necessary. Do not use network access, subprocess, filesystem assumptions, or packages not listed.",
        "The estimator must expose estimate(data, options=None) and return a JSON-serializable dictionary with model_id, estimates, standard_errors, test_statistics, p_values, diagnostics, model_summary.",
        "Validate required columns, numeric types, sample size, missingness, and rank/identification conditions. Raise informative ValueError exceptions for invalid inputs.",
        "Implement the stated estimator, not a proxy or a similarly named simpler estimator. Do not fabricate inferential statistics. State when inference is unavailable or requires bootstrap.",
        "Use numerically stable linear algebra, explicit optimization convergence checks, deterministic random seeds for stochastic procedures, and clear docstrings.",
        "Include tests for a known synthetic data-generating process, coefficient recovery, malformed inputs, and edge cases. Tests must be runnable with pytest-compatible assertions or plain Python assertions.",
        "No TODOs, pseudocode, ellipses, placeholder functions, or claims of validation. If the specification is insufficient to implement the estimator rigorously, return a JSON error object with keys error and missing_information instead of inventing details.",
        "OES package destination: " + (packagePath || "oes1000/" + family),
        "Model ID: " + modelId,
        "Model name: " + modelName,
        "Methodological family: " + family,
        "Required model specification and constraints: " + specification
      ].join("\n");
      try {
        const draft = await callGemini(env, prompt, 12000);
        if (draft.error) return json({ error: safeText(draft.error, 1000), missing_information: draft.missing_information || [] }, 422);
        if (draft.model_id !== modelId || typeof draft.module_code !== "string" ||
            typeof draft.test_code !== "string" || draft.module_code.length < 100 ||
            draft.test_code.length < 50) {
          return json({ error: "Gemini output failed the draft structure checks. Retry this model." }, 502);
        }
        return json({
          status: "draft_only",
          warning: "This code has not been reviewed or validated. Do not mark the catalogue entry validated.",
          draft: {
            model_id: modelId,
            module_code: draft.module_code,
            test_code: draft.test_code,
            mathematical_specification: safeText(draft.mathematical_specification, 5000),
            assumptions: Array.isArray(draft.assumptions) ? draft.assumptions : [],
            dependencies: Array.isArray(draft.dependencies) ? draft.dependencies : [],
            validation_plan: Array.isArray(draft.validation_plan) ? draft.validation_plan : []
          }
        });
      } catch (error) {
        return json({ error: safeText(error.message, 1200) }, 502);
      }
    }

    const message = safeText(input.message, 2000);
    const dataset = input.dataset;
    if (!message || !dataset || !Array.isArray(dataset.columns) || dataset.columns.length > 300) {
      return json({ error: "Provide a cleaning instruction and dataset metadata." }, 400);
    }
    const metadata = {
      rows: Number(dataset.rows) || 0,
      columnCount: Number(dataset.columnCount) || dataset.columns.length,
      duplicateRows: Number(dataset.duplicateRows) || 0,
      columns: dataset.columns.map(column => ({
        name: safeText(column.name, 120),
        type: ["numeric", "text", "mixed"].includes(column.type) ? column.type : "text",
        missing: Number(column.missing) || 0,
        unique: Number(column.unique) || 0,
        min: Number.isFinite(column.min) ? column.min : null,
        max: Number.isFinite(column.max) ? column.max : null
      }))
    };
    const prompt = [
      "You are the data-cleaning assistant for OES-1000.",
      "Return only JSON with keys: missing, dropDuplicates, trimWhitespace, dropEmptyRows, dropEmptyColumns, rationale.",
      "missing must be one of: keep, drop_rows, mean, median, zero, mode, ffill.",
      "The four operation fields must be booleans.",
      "Do not propose unsupported operations or claim the data has been changed.",
      "Choose conservative settings when the instruction is ambiguous and explain uncertainty.",
      "Dataset metadata only; no raw records: " + JSON.stringify(metadata),
      "User instruction: " + message
    ].join("\n");
    try {
      const plan = await callGemini(env, prompt, 2048);
      const allowedMissing = ["keep", "drop_rows", "mean", "median", "zero", "mode", "ffill"];
      if (!allowedMissing.includes(plan.missing) ||
          typeof plan.dropDuplicates !== "boolean" ||
          typeof plan.trimWhitespace !== "boolean" ||
          typeof plan.dropEmptyRows !== "boolean" ||
          typeof plan.dropEmptyColumns !== "boolean") {
        return json({ error: "Gemini returned a plan outside the supported operations." }, 502);
      }
      return json({
        plan: {
          missing: plan.missing,
          dropDuplicates: plan.dropDuplicates,
          trimWhitespace: plan.trimWhitespace,
          dropEmptyRows: plan.dropEmptyRows,
          dropEmptyColumns: plan.dropEmptyColumns,
          rationale: safeText(plan.rationale, 1200)
        }
      });
    } catch (error) {
      return json({ error: safeText(error.message, 1200) }, 502);
    }
  }
};
