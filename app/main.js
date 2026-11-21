import { OESWorkerClient } from "./worker-client.js";
import { downloadJSON, downloadHTML } from "./report.js";

const $ = (id) => document.getElementById(id);
const status = (message) => { $("global-status").textContent = message; };
const runtime = new OESWorkerClient((message, state) => {
  $("runtime-label").textContent = state === "ready" ? "Browser Python runtime ready" : state === "error" ? "Runtime error" : "Initializing browser runtime…";
  $("runtime-detail").textContent = message;
  $("runtime-dot").className = "status-dot " + (state === "ready" ? "ready" : state === "error" ? "error" : "");
});
let csvText = "", fileName = "", currentProfile = null, currentResult = null, currentManifest = null, fileHash = null;

function setOptions(select, columns, firstLabel, includeEmpty = true) {
  select.innerHTML = includeEmpty ? `<option value="">${firstLabel}</option>` : "";
  for (const column of columns) {
    const option = document.createElement("option"); option.value = column; option.textContent = column; select.append(option);
  }
  select.disabled = false;
}
function selectedValues(select) { return [...select.selectedOptions].map(o => o.value).filter(Boolean); }
async function sha256(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, "0")).join("");
}
async function loadFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".csv")) { status("Please select a CSV file."); return; }
  csvText = await file.text(); fileName = file.name; currentProfile = null; currentResult = null;
  fileHash = await sha256(csvText);
  $("file-label").textContent = file.name;
  $("file-subtitle").textContent = `${(file.size / 1024).toFixed(1)} KB · SHA-256 fingerprint generated locally`;
  $("profile-button").disabled = false;
  $("profile-status").textContent = "File loaded";
  $("profile-results").textContent = "Select the outcome and optional panel roles, then analyze the dataset.";
  $("recommendations").textContent = "Run the data profile to receive recommendations with explicit reasoning.";
  $("results").textContent = "Run an estimator to see results.";
  $("estimate-button").disabled = true; $("download-json").disabled = true; $("download-html").disabled = true;
  status("CSV loaded and fingerprinted locally. No dataset upload was made.");
  try {
    const schema = await runtime.request("schema", { csv_text: csvText });
    setOptions($("outcome-select"), schema.columns, "Select outcome");
    setOptions($("entity-select"), schema.columns, "Not a panel / none");
    setOptions($("time-select"), schema.columns, "None");
    $("predictors-select").innerHTML = "";
    for (const col of schema.columns) { const o = document.createElement("option"); o.value = col; o.textContent = col; $("predictors-select").append(o); }
    $("predictors-select").disabled = false;
    status(`Loaded ${schema.rows.toLocaleString()} rows and ${schema.columns.length} columns. Choose an outcome.`);
  } catch (error) { status("Could not read CSV: " + error.message); }
}
$("file-input").addEventListener("change", e => loadFile(e.target.files[0]));
const dropzone = $("dropzone");
dropzone.addEventListener("dragover", e => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", e => { e.preventDefault(); dropzone.classList.remove("drag"); loadFile(e.dataTransfer.files[0]); });

$("profile-button").addEventListener("click", async () => {
  if (!csvText) return;
  try {
    status("Profiling variables and evaluating model suitability…");
    const roles = { outcome: $("outcome-select").value, entity: $("entity-select").value, time: $("time-select").value };
    if (!roles.outcome) { status("Select an outcome variable first."); return; }
    currentProfile = await runtime.request("profile", { csv_text: csvText, roles });
    renderProfile(currentProfile);
    renderRecommendations(currentProfile.recommendations || []);
    $("estimate-button").disabled = !(currentProfile.recommendations || []).some(r => r.implemented);
    $("profile-status").textContent = "Profile complete";
    status("Data profile complete. Review the recommendations and choose an estimator.");
  } catch (error) { status("Profiling failed: " + error.message); }
});

function renderProfile(p) {
  const stats = p.summary;
  $("profile-results").innerHTML = `<div class="stats-grid">
    <div class="stat-card"><small>OBSERVATIONS</small><strong>${stats.rows.toLocaleString()}</strong></div>
    <div class="stat-card"><small>VARIABLES</small><strong>${stats.columns}</strong></div>
    <div class="stat-card"><small>MISSING CELLS</small><strong>${stats.missing_cells.toLocaleString()}</strong></div>
    <div class="stat-card"><small>DUPLICATE ROWS</small><strong>${stats.duplicate_rows.toLocaleString()}</strong></div>
  </div><div class="result-table-wrap"><table class="data-table"><thead><tr><th>Variable</th><th>Type</th><th>Missing</th><th>Unique</th><th>Summary</th></tr></thead><tbody>${p.variables.map(v => `<tr><td>${esc(v.name)}</td><td>${esc(v.kind)}</td><td>${v.missing_pct.toFixed(1)}%</td><td>${v.unique}</td><td>${esc(v.summary)}</td></tr>`).join("")}</tbody></table></div>`;
}
function renderRecommendations(items) {
  $("recommendations").innerHTML = items.length ? items.map((r, i) => `<article class="recommendation ${i === 0 ? "best" : ""}"><div class="rec-head"><strong>${esc(r.name)}</strong><span class="rec-label">${r.implemented ? "AVAILABLE" : "ROADMAP"}</span></div><p>${esc(r.reason)}</p><div class="rec-head"><span class="muted">Assumptions: ${esc(r.assumptions.join("; "))}</span><button data-model="${esc(r.id)}" ${r.implemented ? "" : "disabled"}>Select method</button></div></article>`).join("") : '<div class="empty-state">No recommendation could be generated. Check the outcome role and variable types.</div>';
  $("model-select").innerHTML = '<option value="">Select estimator</option>' + items.filter(r => r.implemented).map(r => `<option value="${esc(r.id)}">${esc(r.name)}</option>`).join("");
  $("model-select").disabled = !items.some(r => r.implemented);
  $("recommendations").querySelectorAll("button[data-model]").forEach(b => b.addEventListener("click", () => { $("model-select").value = b.dataset.model; status("Selected " + b.dataset.model); }));
}
$("model-select").addEventListener("change", () => { $("estimate-button").disabled = !$("model-select").value || !currentProfile; });

$("estimate-button").addEventListener("click", async () => {
  if (!currentProfile) return;
  const model = $("model-select").value;
  const outcome = $("outcome-select").value;
  const predictors = selectedValues($("predictors-select")).filter(v => v !== outcome);
  const roles = { outcome, predictors, entity: $("entity-select").value, time: $("time-select").value };
  if (!model || !outcome || !predictors.length) { status("Choose an estimator, outcome, and at least one regressor."); return; }
  try {
    status("Running " + model + " in the local Pyodide worker…");
    currentResult = await runtime.request("estimate", { csv_text: csvText, model, roles });
    currentManifest = { product: "OES Intelligence", created_at: new Date().toISOString(), source_file_name: fileName, dataset_sha256: fileHash, runtime: "Pyodide / WebAssembly", computation_location: "browser Web Worker", model_id: model, specification: roles };
    renderResults(currentResult);
    $("result-status").textContent = "Estimation complete";
    $("download-json").disabled = false; $("download-html").disabled = false;
    status("Estimation complete. Review diagnostics and assumptions before interpretation.");
  } catch (error) { status("Estimation failed: " + error.message); $("result-status").textContent = "Estimation failed"; }
});
function renderResults(r) {
  $("results").innerHTML = `<div class="stats-grid">${Object.entries(r.summary).map(([k,v]) => `<div class="stat-card"><small>${esc(k.replaceAll("_"," ").toUpperCase())}</small><strong>${typeof v === "number" ? v.toFixed(3) : esc(v)}</strong></div>`).join("")}</div><div class="result-table-wrap"><table class="data-table"><thead><tr><th>Term</th><th>Estimate</th><th>Std. error</th><th>Statistic</th><th>p-value</th></tr></thead><tbody>${r.coefficients.map(c => `<tr><td>${esc(c.term)}</td><td>${num(c.estimate)}</td><td>${num(c.std_error)}</td><td>${num(c.statistic)}</td><td>${num(c.p_value)}</td></tr>`).join("")}</tbody></table></div><h3>Diagnostics</h3><div class="diagnostic-grid">${Object.entries(r.diagnostics || {}).map(([k,v]) => `<div class="diagnostic"><small>${esc(k.replaceAll("_"," ").toUpperCase())}</small><strong>${typeof v === "number" ? num(v) : esc(JSON.stringify(v))}</strong></div>`).join("")}</div><p class="fine-print">${esc(r.notes || "")}</p>`;
}
$("download-json").addEventListener("click", () => currentResult && downloadJSON(currentResult, currentManifest));
$("download-html").addEventListener("click", () => currentResult && downloadHTML(currentResult, currentManifest));
function num(v) { return Number.isFinite(Number(v)) ? Number(v).toFixed(5) : "—"; }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])); }
