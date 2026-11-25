const el = (id) => document.getElementById(id);
const state = { tasks: [], strategies: [], charts: {}, timer: null, results: [] };
const api = async (url, opts) => {
  const r = await fetch(url, opts);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return r.json();
};
const stratName = (id) => (state.strategies.find((s) => s.id === id) || {}).name || id;
const taskName = (id) => (state.tasks.find((t) => t.id === id) || {}).title || id;
const pct = (x) => `${Math.round(x * 100)}%`;
const fmt = (x, d = 1) => (x == null ? "-" : Number(x).toFixed(d));
function checkbox(container, name, items, label) {
  container.innerHTML = items.map((it) => 
    `<label title="${it.description || ""}"><input type="checkbox" name="${name}" value="${it.id}" checked> <span>${label(it)}</span></label>`
  ).join("");
}
const checked = (name) => [...document.querySelectorAll(`input[name=${name}]:checked`)].map((i) => i.value);

async function init() {
  const [cfg, tasks, strategies] = await Promise.all([api("/api/config"), api("/api/tasks"), api("/api/strategies")]);
  state.tasks = tasks;
  state.strategies = strategies;
  const sel = el("provider");
  sel.innerHTML = Object.entries(cfg.providers).map(([name, ok]) => 
    `<option value="${name}" ${!ok ? "disabled" : ""}>${ok ? name : `${name} (no API key)`}</option>`
  ).join("");
  const firstReal = Object.entries(cfg.providers).find(([n, ok]) => ok && n !== "mock" && n !== "ollama");
  sel.value = firstReal ? firstReal[0] : "mock";
  updateHint();
  sel.addEventListener("change", updateHint);
  checkbox(el("taskList"), "task", tasks, (t) => `${t.title} (${t.n_tests} tests)`);
  checkbox(el("stratList"), "strat", strategies, (s) => s.name);
  el("runBtn").addEventListener("click", startRun);
  el("pastRuns").addEventListener("change", (e) => e.target.value && showRun(+e.target.value));
  loadPast();
}
function updateHint() {
  el("providerHint").textContent = el("provider").value === "mock" ? "Mock returns synthetic code so you can try the app without an API key.": "Real model calls use your API credits.";
}
async function loadPast() {
  const runs = await api("/api/runs");
  el("pastRuns").innerHTML = runs.length ?'<option value="">Choose a run</option>' + runs.map(r => `<option value="${r.id}">#${r.id} ${r.provider}/${r.model} (${r.status})</option>`).join(""):'<option value="">None yet</option>';
}
async function startRun() {
  el("formError").textContent = "";
  const body = {
    provider: el("provider").value,
    model: el("model").value.trim() || null,
    tasks: checked("task"),
    strategies: checked("strat"),
    repeats: +el("repeats").value || 1,
  };
  if (!body.tasks.length || !body.strategies.length) {
    el("formError").textContent = "Select at least one task and one strategy.";
    return;
  }
  try {
    el("runBtn").disabled = true;
    const { run_id } = await api("/api/runs", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    await loadPast();
    el("pastRuns").value = run_id;
    watch(run_id);
  } catch (e) {
    el("formError").textContent = e.message;
    el("runBtn").disabled = false;
  }
}

function watch(runId) {
  clearInterval(state.timer);
  el("empty").classList.add("hidden");
  el("report").classList.add("hidden");
  el("progressBox").classList.remove("hidden");
  const tick = async () => {
    const run = await api(`/api/runs/${runId}`);
    el("progressLabel").textContent = run.status === "failed" ? `Run failed: ${run.error}` : "Running experiment";
    el("progressCount").textContent = `${run.done} of ${run.total} samples`;
    el("progressFill").style.width = `${(run.done / run.total) * 100}%`;
    if (run.status === "finished" || run.status === "failed") {
      clearInterval(state.timer);
      el("runBtn").disabled = false;
      loadPast();
      if (run.status === "finished") { el("progressBox").classList.add("hidden"); showRun(runId); }
    }
  };
  state.timer = setInterval(tick, 700);
  tick();
}

async function showRun(runId) {
  const [run, summary, results] = await Promise.all([
    api(`/api/runs/${runId}`), api(`/api/runs/${runId}/summary`), api(`/api/runs/${runId}/results`),
  ]);
  if (run.status !== "finished") { watch(runId); return; }
  state.results = results;
  el("empty").classList.add("hidden");
  el("progressBox").classList.add("hidden");
  el("report").classList.remove("hidden");
  el("csvLink").href = `/api/runs/${runId}/export.csv`;

  const best = summary.by_strategy.find((s) => s.strategy === summary.best);
  const llmErrors = results.filter((r) => (r.error || "").startsWith("LLM error")).length;
  el("verdictText").textContent = best
    ? `${stratName(best.strategy)} performed best: ${pct(best.success_rate)} of samples passed every test, using ${Math.round(best.tokens)} tokens on average.` +
      (llmErrors ? ` ${llmErrors} samples failed because the model call errored.` : "")
    : "No results.";

  renderMatrix(summary);
  renderCharts(summary);
  renderSummary(summary);
  renderSamples(results);
}

function renderMatrix(summary) {
  const strategies = summary.by_strategy.map((s) => s.strategy);
  const taskIds = [...new Set(summary.matrix.map((m) => m.task_id))];
  const val = (s, t) => (summary.matrix.find((m) => m.strategy === s && m.task_id === t) || {}).correctness;

  el("matrix").innerHTML = "<tr><th></th>" + strategies.map((s) => `<th>${stratName(s)}</th>`).join("") + "</tr>" +
    taskIds.map((t) => `<tr><th class="rowh">${taskName(t)}</th>` +
      strategies.map((s) => {
        const c = val(s, t) ?? 0;
        return `<td><button data-s="${s}" data-t="${t}" style="background:hsl(${Math.round(c * 130)} 55% 34%)">${pct(c)}</button></td>`;
      }).join("") + "</tr>"
    ).join("");

  el("matrix").querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => {
      const r = state.results.find((x) => x.strategy === b.dataset.s && x.task_id === b.dataset.t);
      if (r) openCode(r);
    }));
}

function chart(id, type, labels, datasets, extra = {}) {
  if (state.charts[id]) state.charts[id].destroy();
  state.charts[id] = new Chart(el(id), { type, data: { labels, datasets }, options: { responsive: true, plugins: { legend: { display: datasets.length > 1 } }, ...extra } });
}

function renderCharts(summary) {
  const rows = summary.by_strategy;
  const labels = rows.map((r) => stratName(r.strategy));
  const base = { borderWidth: 0 };
  chart("chSuccess", "bar", labels, [{ ...base, data: rows.map((r) => Math.round(r.success_rate * 100)), backgroundColor: "#0e6b8c" }], { scales: { y: { min: 0, max: 100 } } });
  chart("chTokens", "bar", labels, [{ ...base, data: rows.map((r) => Math.round(r.tokens)), backgroundColor: "#b7791f" }]);
  chart("chLatency", "bar", labels, [{ ...base, data: rows.map((r) => +r.latency.toFixed(2)), backgroundColor: "#5b6b7a" }]);
  chart("chScores", "bar", labels, [
    { ...base, label: "Quality", data: rows.map((r) => Math.round(r.quality)), backgroundColor: "#2f7d4f" },
    { ...base, label: "Security", data: rows.map((r) => Math.round(r.security)), backgroundColor: "#7a4fa0" },
  ], { scales: { y: { min: 0, max: 100 } } });
}

function renderSummary(summary) {
  const head = ["Strategy", "Samples", "Solved all tests", "Avg tests passed", "Runs without error", "Quality", "Security", "Latency (s)", "Tokens", "Attempts"];
  el("summary").innerHTML = "<tr>" + head.map((x) => `<th>${x}</th>`).join("") + "</tr>" +
    summary.by_strategy.map((s) => `<tr class="${s.strategy === summary.best ? "best" : ""}">` +
      `<td>${stratName(s.strategy)}</td><td>${s.n}</td><td>${pct(s.success_rate)}</td><td>${pct(s.avg_correctness)}</td><td>${pct(s.exec_rate)}</td>` +
      `<td>${fmt(s.quality, 0)}</td><td>${fmt(s.security, 0)}</td><td>${fmt(s.latency, 2)}</td><td>${Math.round(s.tokens)}</td><td>${fmt(s.attempts, 1)}</td>` +
    `</tr>`).join("");
}

function renderSamples(results) {
  const head = ["Task", "Strategy", "Run", "Result", "Tests", "Quality", "Security", "Tokens", "Latency (s)", "Attempts", ""];
  el("samples").innerHTML = "<tr>" + head.map((x, i) => `<th class="${i < 2 ? "left" : ""}">${x}</th>`).join("") + "</tr>" +
    results.map((r, i) => `<tr>` +
      `<td>${taskName(r.task_id)}</td><td>${stratName(r.strategy)}</td><td>${r.repeat}</td>` +
      `<td><span class="badge ${r.solved ? "ok" : "no"}">${r.solved ? "Pass" : "Fail"}</span></td>` +
      `<td>${r.passed}/${r.total_tests}</td><td>${fmt(r.quality, 0)}</td><td>${fmt(r.security, 0)}</td>` +
      `<td>${r.in_tokens + r.out_tokens}</td><td>${fmt(r.latency, 2)}</td><td>${r.attempts}</td>` +
      `<td><button class="mini" data-i="${i}">View code</button></td>` +
    `</tr>`).join("");
  el("samples").querySelectorAll("button.mini").forEach((b) => b.addEventListener("click", () => openCode(results[+b.dataset.i])));
}
function openCode(r) {
  el("dlgTitle").textContent = `${taskName(r.task_id)} with ${stratName(r.strategy)}`;
  el("dlgMeta").textContent = `${r.passed}/${r.total_tests} tests passed, quality ${fmt(r.quality, 0)}, security ${fmt(r.security, 0)}, ${r.attempts} attempt(s)`;
  el("dlgCode").textContent = r.code || "(no code generated)";
  el("dlgError").textContent = r.error || "";
  el("codeDialog").showModal();
}
init().catch((e) => { el("formError").textContent = `Could not reach the backend: ${e.message}`; });