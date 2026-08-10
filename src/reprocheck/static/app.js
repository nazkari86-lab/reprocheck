const form = document.querySelector("#audit-form");
const result = document.querySelector("#result");
const download = document.querySelector("#download");
const demoButton = document.querySelector("#demo");
const submitButton = form.querySelector('button[type="submit"]');
const explorer = document.querySelector("#evidence-explorer");
const svg = document.querySelector("#evidence-svg");
const inspector = document.querySelector("#node-inspector");
const fileFilters = document.querySelector("#file-filters");
const graphStats = document.querySelector("#graph-stats");
const pipeline = document.querySelector("#audit-pipeline");
const graphBoundary = document.querySelector("#graph-boundary");
const SVG_NS = "http://www.w3.org/2000/svg";
const MAX_VISIBLE_NODES = 160;

const PIPELINE_STAGES = [
  ["files", "01", "Файлы", "SHA-256 и роли"],
  ["claims", "02", "Утверждения", "числа и строки"],
  ["evidence", "03", "Пересчёт", "метрики из evidence"],
  ["matching", "04", "Сопоставление", "совпадения и утечки"],
  ["certificate", "05", "Сертификат", "граф и digest"],
];

const KIND_LABELS = {
  artifact: "Файл",
  context: "Контекст",
  metric: "Метрика",
  claim: "Вывод",
  finding: "Замечание",
  experiment: "Аудит",
};

const RELATION_LABELS = {
  input_to: "входит в аудит",
  contains: "содержит",
  reports: "сообщает",
  recomputes: "пересчитывает",
  supports: "подтверждает",
  contradicts: "противоречит",
  qualifies: "уточняет",
  scopes: "задаёт контекст",
  flags: "указывает на",
  raises: "вызывает",
  reports_finding: "фиксирует",
};

let lastAudit = null;
let graphState = null;

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => {
    const drop = input.closest(".drop");
    drop.classList.toggle("has-file", input.files.length > 0);
    if (input.files.length > 1) drop.dataset.filename = `${input.files.length} файлов · ${topFolder(input.files[0])}`;
    else if (input.files.length > 0) drop.dataset.filename = input.files[0].name;
    else delete drop.dataset.filename;
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const projectInput = document.querySelector("#project-files");
  const reportInput = form.querySelector('input[name="report"]');
  if (!projectInput.files.length && !reportInput.files.length) {
    result.innerHTML = '<div class="verdict needs_review"><p class="eyebrow">НУЖНЫ ФАЙЛЫ</p><h2>Выберите проект</h2><p>Загрузите папку проекта или отдельно укажите научный отчёт.</p></div>';
    return;
  }
  const payload = new FormData(form);
  payload.delete("project_files");
  [...projectInput.files].forEach((file) => payload.append("project_files", file, file.webkitRelativePath || file.name));
  await executeProjectAudit(payload);
});

demoButton.addEventListener("click", async () => {
  await executeAudit("/api/demo", { method: "POST" }, true);
});

download.addEventListener("click", () => {
  if (!lastAudit) return;
  const blob = new Blob([`${JSON.stringify(lastAudit, null, 2)}\n`], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "reprocheck-certificate.json";
  link.click();
  URL.revokeObjectURL(link.href);
});

document.querySelector("#replay-graph").addEventListener("click", replayGraph);
document.querySelector("#reset-graph").addEventListener("click", () => focusNode(null));

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-focus-node]");
  if (target && graphState) focusNode(target.dataset.focusNode);
});

async function executeAudit(url, options, isDemo = false) {
  const loading = startLoading(isDemo);
  setBusy(true);
  try {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Ошибка проверки");
    await loading.complete();
    lastAudit = payload;
    download.hidden = false;
    render(payload, isDemo);
  } catch (error) {
    loading.stop();
    result.innerHTML = `<div class="verdict needs_review"><p class="eyebrow">ОШИБКА</p><h2>Не удалось проверить</h2><p>${escapeHtml(error.message)}</p></div>`;
  } finally {
    setBusy(false);
  }
}

async function executeProjectAudit(formData) {
  const loading = startProjectLoading(formData);
  setBusy(true);
  try {
    const response = await fetch("/api/audit/jobs", { method: "POST", body: formData });
    const created = await response.json();
    if (!response.ok) throw new Error(created.detail || "Не удалось создать аудит");
    loading.update(created);
    let snapshot = created;
    while (!["completed", "failed"].includes(snapshot.status)) {
      await delay(140);
      const statusResponse = await fetch(`/api/audit/jobs/${created.job_id}`);
      snapshot = await statusResponse.json();
      if (!statusResponse.ok) throw new Error(snapshot.detail || "Audit job потерян");
      loading.update(snapshot);
    }
    if (snapshot.status === "failed") throw new Error(snapshot.error || "Проверка завершилась ошибкой");
    lastAudit = snapshot.result;
    download.hidden = false;
    render(snapshot.result, false, snapshot);
  } catch (error) {
    loading.stop();
    result.innerHTML = `<div class="verdict needs_review"><p class="eyebrow">ОШИБКА</p><h2>Не удалось проверить</h2><p>${escapeHtml(error.message)}</p></div>`;
  } finally {
    setBusy(false);
  }
}

function setBusy(busy) {
  submitButton.disabled = busy;
  demoButton.disabled = busy;
  submitButton.querySelector("span").textContent = busy ? "Проверяем доказательства…" : "Запустить проверку";
}

function startLoading(isDemo) {
  explorer.hidden = true;
  const title = isDemo ? "Запускаем контролируемый пример" : "Разбираем ваш эксперимент";
  result.innerHTML = `<div class="loading-audit"><p class="eyebrow">LIVE AUDIT</p><h2>${title}</h2><div class="loading-stages">${PIPELINE_STAGES.map(([, number, name], index) => `<div class="loading-stage${index === 0 ? " active" : ""}"><span>${number}</span><b>${name}</b><i></i></div>`).join("")}</div><p class="loading-note">ReproCheck не запускает загруженный код. Он проверяет предоставленные артефакты.</p></div>`;
  const elements = [...result.querySelectorAll(".loading-stage")];
  let current = 0;
  const timer = window.setInterval(() => {
    elements[current]?.classList.replace("active", "done");
    current = Math.min(current + 1, elements.length - 2);
    elements[current]?.classList.add("active");
  }, 360);
  return {
    stop() { window.clearInterval(timer); },
    async complete() {
      window.clearInterval(timer);
      for (let index = current; index < elements.length; index += 1) {
        elements[index].classList.remove("active");
        elements[index].classList.add("done");
        await delay(70);
      }
    },
  };
}

function startProjectLoading(formData) {
  explorer.hidden = true;
  const projectFiles = formData.getAll("project_files");
  const manualFiles = [...formData.entries()].filter(([, value]) => value instanceof File && value.size > 0 && !projectFiles.includes(value));
  const inputCount = projectFiles.length + manualFiles.length;
  result.innerHTML = `
    <div class="loading-audit real-pipeline">
      <p class="eyebrow">BACKEND AUDIT / REAL TIME</p>
      <h2>Проверяем ваш проект.</h2>
      <p class="live-input-count">Передано файлов: <b>${inputCount}</b>. Прогресс меняется только после ответа backend.</p>
      <div class="loading-stages">${PIPELINE_STAGES.map(([stage, number, name, detail]) => `
        <div class="loading-stage" data-stage="${stage}">
          <span>${number}</span><div><b>${name}</b><small>${detail}</small></div><i></i>
        </div>`).join("")}</div>
      <div class="detected-files" hidden></div>
      <p class="loading-note">Загруженный Python-код не выполняется. Анализируются отчёты, evidence, splits, notebooks и их происхождение.</p>
    </div>`;
  const shell = result.querySelector(".real-pipeline");
  return {
    update(snapshot) {
      const stageById = new Map((snapshot.stages || []).map((stage) => [stage.stage, stage]));
      PIPELINE_STAGES.forEach(([stageId]) => {
        const row = shell.querySelector(`[data-stage="${stageId}"]`);
        const stage = stageById.get(stageId);
        row.classList.toggle("active", stage?.state === "started");
        row.classList.toggle("done", stage?.state === "completed");
        if (stage?.message) {
          const duration = stage.duration_ms === undefined ? "" : ` · ${formatDuration(stage.duration_ms)}`;
          row.querySelector("small").textContent = `${stage.message}${duration}`;
        }
      });
      const filesStage = stageById.get("files");
      if (filesStage?.files) renderDetectedFiles(shell.querySelector(".detected-files"), filesStage);
    },
    stop() {},
  };
}

function renderDetectedFiles(container, stage) {
  container.hidden = false;
  const experiment = stage.experiment_id ? ` · ${stage.experiment_id}${stage.experiment_count > 1 ? ` (1/${stage.experiment_count})` : ""}` : "";
  container.innerHTML = `<div class="detected-title"><b>Backend распознал роли</b><span>${escapeHtml(stage.inference_source || "manual")}${escapeHtml(experiment)}</span></div><div class="detected-grid">${stage.files.slice(0, 18).map((file) => `<div><span>${escapeHtml(file.role)}</span><b>${escapeHtml(file.filename)}</b><small>${escapeHtml(file.source)}</small></div>`).join("")}</div>${stage.files.length > 18 ? `<p>Ещё файлов в сертификате: ${stage.files.length - 18}</p>` : ""}`;
}

function render(data, isDemo, trace = null) {
  const claimRows = data.claims.length ? data.claims.map(({ claim, status, observed, display_kind }, index) => `
    <button class="metric trace-link" type="button" data-focus-node="claim:${index}">
      <span><strong>${escapeHtml(claim.raw_text)}</strong><small>${escapeHtml(findReportName(data))}, строка ${claim.line} · заявлено ${formatMetric(claim.value, display_kind)}</small></span>
      <b class="${status}">${label(status)}${observed === null ? "" : ` · ${formatMetric(observed, display_kind)}`}</b>
    </button>`).join("") : "<p>Числовые утверждения не найдены.</p>";
  const artifacts = data.artifacts.map((artifact, index) => `
    <button class="artifact-row trace-link" type="button" data-focus-node="artifact:${index}">
      <span class="file-icon">${fileExtension(artifact.filename)}</span>
      <span><b>${escapeHtml(artifact.filename)}</b><small>${escapeHtml(artifact.role)} · ${formatBytes(artifact.size_bytes)}</small></span>
      <code>${escapeHtml(artifact.sha256.slice(0, 10))}…</code>
    </button>`).join("");
  const leakage = data.leakage ? `<div class="leak-box"><div><strong>${percent(data.leakage.exact_overlap_rate)}</strong><span>exact overlap</span></div><div><strong>${percent(data.leakage.normalized_overlap_rate)}</strong><span>normalized overlap</span></div><div><strong>${percent(data.leakage.near_overlap_rate)}</strong><span>near overlap</span></div><div><strong>${data.leakage.overlapping_group_count}</strong><span>общих групп</span></div></div>` : "<p>Train/test не загружены.</p>";
  const notebook = data.notebook ? `<div class="leak-box"><div><strong>${data.notebook.code_cells}</strong><span>code cells</span></div><div><strong>${data.notebook.has_random_seed ? "да" : "нет"}</strong><span>seed обнаружен</span></div></div>` : "<p>Notebook не загружен.</p>";
  const findings = data.findings.length ? data.findings.map((item, index) => `<button class="finding ${escapeHtml(item.severity)} trace-link" type="button" data-focus-node="finding:${index}"><b>${escapeHtml(item.code)}</b><span>${escapeHtml(item.message)}</span></button>`).join("") : '<div class="finding medium"><b>ЧИСТО</b><span>Проверяемых несоответствий не найдено.</span></div>';
  const executionTrace = trace ? renderExecutionTrace(trace) : "";
  result.innerHTML = `
    <div class="verdict ${data.status}"><p class="eyebrow">${isDemo ? "КОНТРОЛИРУЕМЫЙ ПРИМЕР" : "ИТОГ АУДИТА"}</p><h2>${data.status === "passed" ? "ПРОЙДЕНО" : "ТРЕБУЕТ ПРОВЕРКИ"}</h2><p>${data.findings.length} замечаний · ${data.artifacts.length} файлов зафиксировано</p></div>
    ${executionTrace}
    <h3>Зафиксированные файлы</h3>${artifacts}
    <h3>Утверждения</h3>${claimRows}
    <h3>Разделение данных</h3>${leakage}
    <h3>Notebook</h3>${notebook}
    <h3>Замечания</h3>${findings}
    <button class="open-graph" type="button" data-open-graph><span>Открыть карту доказательств</span><b>↘</b></button>
    <p class="certificate">SHA-256 сертификата: ${escapeHtml(data.certificate_sha256)}</p>`;
  result.querySelector("[data-open-graph]").addEventListener("click", () => explorer.scrollIntoView({ behavior: "smooth", block: "start" }));
  renderExplorer(data, trace);
}

function renderExecutionTrace(trace) {
  const stageById = new Map(trace.stages.map((stage) => [stage.stage, stage]));
  const filesStage = stageById.get("files");
  const cards = PIPELINE_STAGES.map(([id, number, name]) => {
    const stage = stageById.get(id);
    return `<div><span>${number}</span><b>${name}</b><strong>${stage?.duration_ms === undefined ? "—" : formatDuration(stage.duration_ms)}</strong><small>${escapeHtml(stage?.message || "Нет события")}</small></div>`;
  }).join("");
  const experiment = filesStage?.experiment_id ? `<span><b>experiment</b>${escapeHtml(filesStage.experiment_id)}${filesStage.experiment_count > 1 ? ` · 1/${filesStage.experiment_count}` : ""}</span>` : "";
  const roles = experiment + (filesStage?.files || []).filter((file) => !file.role.startsWith("project_")).map((file) => `<span><b>${escapeHtml(file.role)}</b>${escapeHtml(file.filename)}</span>`).join("");
  return `<section class="execution-proof"><div class="execution-heading"><div><p class="eyebrow">ФАКТИЧЕСКИЙ ХОД BACKEND</p><h3>Это не таймер: стадии измерены сервером.</h3></div><code>${escapeHtml(trace.job_id.slice(0, 12))}</code></div><div class="execution-cards">${cards}</div><div class="execution-roles">${roles}</div></section>`;
}

function renderExplorer(data, trace = null) {
  if (!data.evidence_graph) {
    explorer.hidden = true;
    return;
  }
  explorer.hidden = false;
  const graph = data.evidence_graph;
  graphState = {
    data,
    graph,
    nodeById: new Map(graph.nodes.map((node) => [node.id, node])),
    selectedId: null,
  };
  graphStats.innerHTML = `<div><strong>${graph.nodes.length}</strong><span>вершин</span></div><div><strong>${graph.edges.length}</strong><span>связей</span></div><div><strong>${data.claims.length}</strong><span>выводов</span></div>`;
  const stageById = new Map((trace?.stages || []).map((stage) => [stage.stage, stage]));
  pipeline.innerHTML = PIPELINE_STAGES.map(([id, number, name, detail], index) => {
    const measured = stageById.get(id);
    const text = measured ? `${measured.message} · ${formatDuration(measured.duration_ms)}` : detail;
    return `<div class="pipeline-stage" style="--stage:${index}"><span>${number}</span><div><b>${name}</b><small>${escapeHtml(text)}</small></div><i>✓</i></div>`;
  }).join("");
  fileFilters.innerHTML = graph.nodes.filter((node) => node.kind === "artifact").map((node) => `<button type="button" data-focus-node="${escapeHtml(node.id)}"><span>${fileExtension(node.attributes.filename || node.label)}</span>${escapeHtml(node.attributes.filename || node.label)}</button>`).join("");
  graphBoundary.textContent = `Граф: ${graph.graph_sha256}. Связи показывают происхождение данных, но сами по себе не доказывают научную истинность вывода.`;
  drawGraph();
  replayGraph();
}

function drawGraph() {
  const { graph } = graphState;
  svg.replaceChildren();
  const nodes = chooseVisibleNodes(graph.nodes);
  const visibleIds = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  const positions = layoutNodes(nodes);
  const maxY = Math.max(...[...positions.values()].map((position) => position.y), 500);
  const width = 1264;
  const height = Math.max(680, maxY + 130);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.append(makeDefinitions());

  const edgeLayer = createSvg("g", { class: "edge-layer" });
  const routes = routeEdges(edges, positions);
  edges.forEach((edge, index) => {
    const route = routes[index];
    const structural = ["input_to", "contains", "reports_finding", "scopes"].includes(edge.relation);
    const group = createSvg("g", {
      class: `edge-group relation-${edge.relation}${structural ? " is-structural" : " is-semantic"}`,
      "data-source": edge.source,
      "data-target": edge.target,
      "data-edge-index": String(index),
    });
    group.style.setProperty("--edge-delay", `${Math.min(index * 28, 900)}ms`);
    const halo = createSvg("path", { class: "edge-halo", d: route.d });
    const path = createSvg("path", {
      class: "graph-edge",
      d: route.d,
      "marker-end": "url(#arrow)",
      pathLength: "1",
    });
    const startPort = createSvg("circle", { class: "edge-port edge-port-start", cx: String(route.startX), cy: String(route.startY), r: "3.2" });
    const endPort = createSvg("circle", { class: "edge-port edge-port-end", cx: String(route.endX), cy: String(route.endY), r: "3.2" });
    group.append(halo, path, startPort, endPort, makeEdgeTag(edge.relation, route.labelX, route.labelY));
    edgeLayer.append(group);
  });
  svg.append(edgeLayer);

  const nodeLayer = createSvg("g", { class: "node-layer" });
  nodes.forEach((node, index) => {
    const position = positions.get(node.id);
    const group = createSvg("g", {
      class: `graph-node kind-${node.kind}`,
      transform: `translate(${position.x},${position.y})`,
      tabindex: "0",
      role: "button",
      "aria-label": `${KIND_LABELS[node.kind] || node.kind}: ${node.label}`,
      "data-node-id": node.id,
    });
    group.style.setProperty("--node-delay", `${Math.min(index * 45, 1200)}ms`);
    group.append(createSvg("rect", { width: "224", height: "72", rx: "4" }));
    const kind = createSvg("text", { class: "node-kind", x: "14", y: "20" });
    kind.textContent = KIND_LABELS[node.kind] || node.kind;
    const label = createSvg("text", { class: "node-label", x: "14", y: "45" });
    label.textContent = truncate(node.label, 28);
    const hint = createSvg("text", { class: "node-hint", x: "14", y: "62" });
    hint.textContent = nodeHint(node);
    group.append(kind, label, hint);
    group.addEventListener("click", () => focusNode(node.id));
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") focusNode(node.id);
    });
    nodeLayer.append(group);
  });
  svg.append(nodeLayer);
  graphState.visibleNodes = nodes;
  graphState.visibleEdges = edges;
  graphState.positions = positions;
  graphBoundary.classList.toggle("truncated", graph.nodes.length > nodes.length);
  if (graph.nodes.length > nodes.length) {
    graphBoundary.textContent = `Показано ${nodes.length} из ${graph.nodes.length} вершин для читаемости. Выбор файла сохраняет все его видимые цепочки. ${graphBoundary.textContent}`;
  }
}

function chooseVisibleNodes(nodes) {
  if (nodes.length <= MAX_VISIBLE_NODES) return nodes;
  const priority = { artifact: 0, finding: 1, claim: 2, metric: 3, context: 4, experiment: 5 };
  return [...nodes]
    .sort((left, right) => (priority[left.kind] ?? 9) - (priority[right.kind] ?? 9))
    .slice(0, MAX_VISIBLE_NODES);
}

function layoutNodes(nodes) {
  const layerByKind = { artifact: 0, context: 1, metric: 1, claim: 2, finding: 3 };
  const groups = new Map();
  nodes.forEach((node) => {
    if (node.kind === "experiment") return;
    const layer = layerByKind[node.kind] ?? 4;
    if (!groups.has(layer)) groups.set(layer, []);
    groups.get(layer).push(node);
  });
  const maxCount = Math.max(...[...groups.values()].map((items) => items.length), 1);
  const height = Math.max(620, maxCount * 108 + 180);
  const positions = new Map();
  groups.forEach((items, layer) => {
    const gap = (height - 180) / (items.length + 1);
    items.forEach((node, index) => {
      positions.set(node.id, { x: 40 + layer * 320, y: 150 + gap * (index + 1) - 36, layer });
    });
  });
  const root = nodes.find((node) => node.kind === "experiment");
  if (root) positions.set(root.id, { x: 520, y: 24, layer: 1 });
  return positions;
}

function focusNode(nodeId) {
  if (!graphState) return;
  graphState.selectedId = nodeId;
  const active = nodeId ? semanticNeighborhood(nodeId) : new Set(graphState.visibleNodes.map((node) => node.id));
  svg.querySelectorAll(".graph-node").forEach((element) => {
    const id = element.dataset.nodeId;
    element.classList.toggle("is-dimmed", !active.has(id));
    element.classList.toggle("is-selected", id === nodeId);
  });
  svg.querySelectorAll(".edge-group").forEach((element) => {
    const isActive = active.has(element.dataset.source) && active.has(element.dataset.target);
    const isDirect = Boolean(nodeId) && (element.dataset.source === nodeId || element.dataset.target === nodeId);
    element.classList.toggle("is-dimmed", !isActive);
    element.classList.toggle("is-active", isActive && Boolean(nodeId));
    element.classList.toggle("is-direct", isDirect);
  });
  document.querySelectorAll("[data-focus-node]").forEach((element) => element.classList.toggle("is-selected", element.dataset.focusNode === nodeId));
  if (nodeId) renderInspector(nodeId);
  else inspector.innerHTML = '<p class="eyebrow">ВЫБРАННЫЙ УЗЕЛ</p><div class="inspector-placeholder">Выберите элемент графа, чтобы увидеть его источник, значение и криптографический отпечаток.</div>';
}

function semanticNeighborhood(startId) {
  const active = new Set([startId]);
  const queue = [startId];
  const semanticEdges = graphState.visibleEdges.filter((edge) => {
    if (startId === graphState.graph.root_id) return true;
    return edge.source !== graphState.graph.root_id && edge.target !== graphState.graph.root_id;
  });
  while (queue.length) {
    const current = queue.shift();
    semanticEdges.forEach((edge) => {
      let next = null;
      if (edge.source === current) next = edge.target;
      if (edge.target === current) next = edge.source;
      if (next && !active.has(next)) {
        active.add(next);
        queue.push(next);
      }
    });
  }
  return active;
}

function renderInspector(nodeId) {
  const node = graphState.nodeById.get(nodeId);
  if (!node) return;
  const connections = graphState.graph.edges
    .filter((edge) => edge.source === nodeId || edge.target === nodeId)
    .slice(0, 12)
    .map((edge) => {
      const otherId = edge.source === nodeId ? edge.target : edge.source;
      const other = graphState.nodeById.get(otherId);
      return `<button type="button" data-focus-node="${escapeHtml(otherId)}"><span>${escapeHtml(RELATION_LABELS[edge.relation] || edge.relation)}</span><b>${escapeHtml(other?.label || otherId)}</b></button>`;
    }).join("");
  const attributes = Object.entries(node.attributes || {})
    .filter(([, value]) => value !== null && value !== "" && !(typeof value === "object" && Object.keys(value).length === 0))
    .map(([key, value]) => `<div><dt>${escapeHtml(attributeLabel(key))}</dt><dd>${escapeHtml(formatAttribute(value))}</dd></div>`)
    .join("");
  inspector.innerHTML = `
    <p class="eyebrow">${escapeHtml(KIND_LABELS[node.kind] || node.kind)} / ${escapeHtml(node.id)}</p>
    <h3>${escapeHtml(node.label)}</h3>
    <dl class="node-attributes">${attributes || "<div><dt>Детали</dt><dd>Нет дополнительных атрибутов</dd></div>"}</dl>
    <div class="digest-card"><span>NODE SHA-256</span><code>${escapeHtml(node.digest_sha256)}</code></div>
    <h4>Связанные элементы</h4>
    <div class="connection-list">${connections || "<p>Прямых связей нет.</p>"}</div>`;
}

function replayGraph() {
  if (!svg.childNodes.length) return;
  if (graphState?.replayTimer) window.clearTimeout(graphState.replayTimer);
  svg.classList.remove("is-playing");
  void svg.getBoundingClientRect();
  svg.classList.add("is-playing");
  graphState.replayTimer = window.setTimeout(() => svg.classList.remove("is-playing"), 1550);
}

function makeDefinitions() {
  const defs = createSvg("defs");
  const marker = createSvg("marker", { id: "arrow", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "6", markerHeight: "6", orient: "auto-start-reverse" });
  marker.append(createSvg("path", { d: "M 1 1 L 9 5 L 1 9 z" }));
  defs.append(marker);
  return defs;
}

function createSvg(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, value));
  return element;
}

function routeEdges(edges, positions) {
  const outgoing = new Map();
  const incoming = new Map();
  edges.forEach((edge, index) => {
    if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
    if (!incoming.has(edge.target)) incoming.set(edge.target, []);
    outgoing.get(edge.source).push(index);
    incoming.get(edge.target).push(index);
  });
  outgoing.forEach((indices) => indices.sort((left, right) => positions.get(edges[left].target).y - positions.get(edges[right].target).y));
  incoming.forEach((indices) => indices.sort((left, right) => positions.get(edges[left].source).y - positions.get(edges[right].source).y));

  const longEdgeSlots = new Map();
  const slotByGroup = new Map();
  edges.forEach((edge, index) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (Math.abs(target.layer - source.layer) > 1 || edge.relation === "input_to" || edge.relation === "reports_finding") {
      const groupKey = edge.relation === "input_to" || edge.relation === "flags"
        ? `${edge.relation}:to:${edge.target}`
        : `${edge.relation}:from:${edge.source}`;
      if (!slotByGroup.has(groupKey)) slotByGroup.set(groupKey, slotByGroup.size);
      longEdgeSlots.set(index, slotByGroup.get(groupKey));
    }
  });

  return edges.map((edge, index) => {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    const forward = target.x >= source.x;
    const sourceIndices = outgoing.get(edge.source);
    const targetIndices = incoming.get(edge.target);
    const startX = forward ? source.x + 224 : source.x;
    const endX = forward ? target.x : target.x + 224;
    let startY = portY(source.y, sourceIndices.indexOf(index), sourceIndices.length);
    let endY = portY(target.y, targetIndices.indexOf(index), targetIndices.length);
    if (["contains", "reports_finding"].includes(edge.relation)) startY = source.y + 36;
    if (["input_to", "flags"].includes(edge.relation)) endY = target.y + 36;
    const longSlot = longEdgeSlots.get(index);
    if (longSlot !== undefined) {
      const laneY = 112 + longSlot * 9;
      return {
        d: overheadPath(startX, startY, endX, endY, laneY, forward),
        startX, startY, endX, endY,
        labelX: (startX + endX) / 2,
        labelY: laneY,
      };
    }
    const gap = endX - startX;
    if (Math.abs(startY - endY) < 5) {
      return { d: `M ${startX} ${startY} H ${endX}`, startX, startY, endX, endY, labelX: (startX + endX) / 2, labelY: startY };
    }
    const sourceOrder = sourceIndices.indexOf(index) - (sourceIndices.length - 1) / 2;
    const laneX = startX + gap * 0.5 + sourceOrder * 5;
    return {
      d: roundedOrthogonalPath(startX, startY, laneX, endY, endX),
      startX, startY, endX, endY,
      labelX: laneX,
      labelY: (startY + endY) / 2,
    };
  });
}

function portY(nodeY, index, total) {
  return nodeY + 14 + ((index + 1) * 44) / (total + 1);
}

function roundedOrthogonalPath(startX, startY, laneX, endY, endX) {
  const direction = endX >= startX ? 1 : -1;
  const verticalDirection = endY >= startY ? 1 : -1;
  const radius = Math.min(10, Math.abs(endY - startY) / 2, Math.abs(laneX - startX) / 2, Math.abs(endX - laneX) / 2);
  return `M ${startX} ${startY} H ${laneX - direction * radius} Q ${laneX} ${startY} ${laneX} ${startY + verticalDirection * radius} V ${endY - verticalDirection * radius} Q ${laneX} ${endY} ${laneX + direction * radius} ${endY} H ${endX}`;
}

function overheadPath(startX, startY, endX, endY, laneY, forward) {
  const direction = forward ? 1 : -1;
  const startLaneX = startX + direction * 24;
  const endLaneX = endX - direction * 24;
  const startVertical = laneY >= startY ? 1 : -1;
  const endVertical = endY >= laneY ? 1 : -1;
  const radius = 9;
  return `M ${startX} ${startY} H ${startLaneX - direction * radius} Q ${startLaneX} ${startY} ${startLaneX} ${startY + startVertical * radius} V ${laneY - startVertical * radius} Q ${startLaneX} ${laneY} ${startLaneX + direction * radius} ${laneY} H ${endLaneX - direction * radius} Q ${endLaneX} ${laneY} ${endLaneX} ${laneY + endVertical * radius} V ${endY - endVertical * radius} Q ${endLaneX} ${endY} ${endLaneX + direction * radius} ${endY} H ${endX}`;
}

function makeEdgeTag(relation, x, y) {
  const label = RELATION_LABELS[relation] || relation;
  const width = Math.max(68, label.length * 5.7 + 16);
  const group = createSvg("g", { class: "edge-tag", transform: `translate(${x - width / 2},${y - 12})` });
  group.append(createSvg("rect", { width: String(width), height: "24", rx: "12" }));
  const text = createSvg("text", { x: String(width / 2), y: "15" });
  text.textContent = label;
  group.append(text);
  return group;
}

function nodeHint(node) {
  if (node.kind === "artifact") return `${node.attributes.role || "artifact"} · ${formatBytes(node.attributes.size_bytes || 0)}`;
  if (node.kind === "claim") return `строка ${node.attributes.line} · ${label(node.attributes.status)}`;
  if (node.kind === "metric") return node.attributes.evidence_level === "recomputed" ? "пересчитано из данных" : "из таблицы метрик";
  if (node.kind === "finding") return node.attributes.severity || "finding";
  return node.id;
}

function findReportName(data) {
  return data.artifacts.find((artifact) => artifact.role === "report")?.filename || "отчёт";
}

function attributeLabel(key) {
  return ({ filename: "Файл", role: "Роль", line: "Строка", raw_text: "Исходный текст", value: "Значение", observed: "Пересчитано", status: "Статус", source: "Источник", method: "Метод", sample_count: "Объектов", evidence_level: "Уровень evidence", content_sha256: "SHA-256 файла", size_bytes: "Размер", metric: "Метрика", message: "Описание", code: "Код" })[key] || key.replaceAll("_", " ");
}

function formatAttribute(value) {
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "number" && !Number.isInteger(value)) return Number(value).toPrecision(7).replace(/\.?0+$/, "");
  return String(value);
}

function fileExtension(filename) {
  const extension = String(filename).split(".").pop();
  return extension && extension !== filename ? extension.slice(0, 4).toUpperCase() : "FILE";
}

function formatBytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function topFolder(file) { return file.webkitRelativePath?.split("/")[0] || "папка проекта"; }
function formatDuration(milliseconds) {
  if (milliseconds < 1) return "<1 ms";
  if (milliseconds < 10) return `${milliseconds.toFixed(1)} ms`;
  if (milliseconds < 1000) return `${Math.round(milliseconds)} ms`;
  return `${(milliseconds / 1000).toFixed(2)} s`;
}
function truncate(value, length) { return value.length > length ? `${value.slice(0, length - 1)}…` : value; }
function delay(milliseconds) { return new Promise((resolve) => window.setTimeout(resolve, milliseconds)); }
function percent(value) { return `${(value * 100).toFixed(1)}%`; }
function formatMetric(value, displayKind) { return displayKind === "percentage" ? percent(value) : Number(value).toPrecision(6).replace(/\.?0+$/, ""); }
function label(value) { return ({ verified: "пересчитано", supported: "совпало с таблицей", mismatch: "расхождение", no_evidence: "нет данных", passed: "пройдено", needs_review: "требует проверки" })[value] || value; }
function escapeHtml(value) { const node = document.createElement("div"); node.textContent = String(value); return node.innerHTML; }
