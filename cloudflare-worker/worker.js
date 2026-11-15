/**
 * OES-1000 Gemini Data Cleaning Assistant
 * Deploy as a Cloudflare Worker.
 * Add GEMINI_API_KEY as a Worker secret. Never put the key in frontend code.
 */
const ALLOWED_ORIGIN = "https://tuhingm.github.io";
const MODEL = "gemini-flash-latest";
function cors(origin) {
  return {
    "Access-Control-Allow-Origin": origin === ALLOWED_ORIGIN ? ALLOWED_ORIGIN : ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin"
  };
}
function json(data, status, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...cors(origin) }
  });
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
    if (origin !== ALLOWED_ORIGIN) return json({ error: "Origin not allowed." }, 403, origin);
    if (request.method !== "POST") return json({ error: "Use POST." }, 405, origin);
    if (!env.GEMINI_API_KEY) return json({ error: "Worker secret GEMINI_API_KEY is not configured." }, 500, origin);
    const length = Number(request.headers.get("Content-Length") || 0);
    if (length > 20000) return json({ error: "Request too large." }, 413, origin);
    let input;
    try { input = await request.json(); } catch { return json({ error: "Invalid JSON." }, 400, origin); }
    const message = String(input.message || "").trim().slice(0, 2000);
    const dataset = input.dataset;
    if (!message || !dataset || !Array.isArray(dataset.columns) || dataset.columns.length > 300) {
      return json({ error: "Provide a cleaning instruction and dataset metadata." }, 400, origin);
    }
    const metadata = {
      rows: Number(dataset.rows) || 0,
      columnCount: Number(dataset.columnCount) || dataset.columns.length,
      duplicateRows: Number(dataset.duplicateRows) || 0,
      columns: dataset.columns.map(c => ({
        name: String(c.name || "").slice(0, 120),
        type: ["numeric", "text", "mixed"].includes(c.type) ? c.type : "text",
        missing: Number(c.missing) || 0,
        unique: Number(c.unique) || 0,
        min: Number.isFinite(c.min) ? c.min : null,
        max: Number.isFinite(c.max) ? c.max : null
      }))
    };
    const prompt = [
      "You are the data-cleaning assistant for OES-1000.",
      "Return only a JSON object with keys: missing, dropDuplicates, trimWhitespace, dropEmptyRows, dropEmptyColumns, rationale.",
      "missing must be exactly one of: keep, drop_rows, mean, median, zero, mode, ffill.",
      "The four other operation fields must be booleans.",
      "Do not propose winsorization, outlier deletion, interpolation, imputation beyond these choices, variable deletion, or any operation not listed.",
      "Use mean/median/zero only when appropriate for numeric columns; use mode for categorical or mixed columns where suitable.",
      "If the user's instruction is ambiguous or scientifically consequential, choose conservative settings and explain the uncertainty in rationale.",
      "Never claim that you changed the data. You are only proposing a plan.",
      "Dataset metadata (no raw records): " + JSON.stringify(metadata),
      "User instruction: " + message
    ].join("\n");
    const url = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent";
    let upstream;
    try {
      upstream = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-goog-api-key": env.GEMINI_API_KEY },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { responseMimeType: "application/json", temperature: 0.2 }
        })
      });
    } catch {
      return json({ error: "Could not connect to Gemini API." }, 502, origin);
    }
    const raw = await upstream.json().catch(() => ({}));
    if (!upstream.ok) return json({ error: raw.error?.message || "Gemini API request failed." }, upstream.status, origin);
    const text = raw.candidates?.[0]?.content?.parts?.map(p => p.text || "").join("") || "";
    let plan;
    try { plan = JSON.parse(text); } catch { return json({ error: "Gemini returned an unreadable plan. Try a more specific instruction." }, 502, origin); }
    const allowedMissing = ["keep", "drop_rows", "mean", "median", "zero", "mode", "ffill"];
    if (!allowedMissing.includes(plan.missing) ||
        typeof plan.dropDuplicates !== "boolean" ||
        typeof plan.trimWhitespace !== "boolean" ||
        typeof plan.dropEmptyRows !== "boolean" ||
        typeof plan.dropEmptyColumns !== "boolean") {
      return json({ error: "Gemini returned a plan outside the supported operations." }, 502, origin);
    }
    return json({ plan: {
      missing: plan.missing,
      dropDuplicates: plan.dropDuplicates,
      trimWhitespace: plan.trimWhitespace,
      dropEmptyRows: plan.dropEmptyRows,
      dropEmptyColumns: plan.dropEmptyColumns,
      rationale: String(plan.rationale || "").slice(0, 1200)
    } }, 200, origin);
  }
};
