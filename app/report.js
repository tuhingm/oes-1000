export function downloadJSON(result, manifest) {
  const blob = new Blob([JSON.stringify({ manifest, result }, null, 2)], { type: "application/json" });
  download(blob, "oes-intelligence-analysis.json");
}
export function downloadHTML(result, manifest) {
  const rows = (result.coefficients || []).map(r => `<tr><td>${escapeHTML(r.term)}</td><td>${fmt(r.estimate)}</td><td>${fmt(r.std_error)}</td><td>${fmt(r.statistic)}</td><td>${fmt(r.p_value)}</td></tr>`).join("");
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>OES Intelligence Analysis Report</title><style>body{font:14px Arial;max-width:900px;margin:45px auto;color:#18263a}h1{color:#173c68}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #ccd5df;text-align:right}td:first-child,th:first-child{text-align:left}.meta{color:#56677a;font-size:12px;line-height:1.7}</style></head><body><h1>OES Intelligence — Analysis Report</h1><p class="meta">Generated: ${escapeHTML(manifest.created_at)}<br>Estimator: ${escapeHTML(result.model_name)}<br>Dataset SHA-256: ${escapeHTML(manifest.dataset_sha256)}</p><h2>Specification</h2><p>Outcome: ${escapeHTML(result.specification.outcome)}<br>Regressors: ${escapeHTML(result.specification.predictors.join(", "))}</p><h2>Coefficient estimates</h2><table><thead><tr><th>Term</th><th>Estimate</th><th>Std. error</th><th>Statistic</th><th>p-value</th></tr></thead><tbody>${rows}</tbody></table><h2>Model summary</h2><pre>${escapeHTML(JSON.stringify(result.summary, null, 2))}</pre><h2>Diagnostics</h2><pre>${escapeHTML(JSON.stringify(result.diagnostics, null, 2))}</pre><p class="meta">This report is generated from browser-local analysis. Review model assumptions, identification, sample definition, and diagnostics before substantive interpretation.</p></body></html>`;
  download(new Blob([html], { type: "text/html" }), "oes-intelligence-report.html");
}
function fmt(x) { return Number.isFinite(Number(x)) ? Number(x).toFixed(5) : "—"; }
function escapeHTML(value) { return String(value ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c])); }
function download(blob, name) {
  const url = URL.createObjectURL(blob); const a = document.createElement("a");
  a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
}
