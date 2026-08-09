const form = document.querySelector("#audit-form");
const result = document.querySelector("#result");
const download = document.querySelector("#download");
let lastAudit = null;

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener("change", () => input.closest(".drop").classList.toggle("has-file", input.files.length > 0));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  button.querySelector("span").textContent = "Проверяем доказательства…";
  result.innerHTML = '<div class="result-empty"><span class="seal">···</span><p>Считаем метрики и сравниваем splits.</p></div>';
  try {
    const response = await fetch("/api/audit", { method: "POST", body: new FormData(form) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Ошибка проверки");
    lastAudit = payload;
    download.hidden = false;
    render(payload);
  } catch (error) {
    result.innerHTML = `<div class="verdict needs_review"><h2>Ошибка входных данных</h2><p>${escapeHtml(error.message)}</p></div>`;
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "Запустить проверку";
  }
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

function render(data) {
  const claimRows = data.claims.length ? data.claims.map(({ claim, status, observed, display_kind }) => `
    <div class="metric"><div><p>${escapeHtml(claim.raw_text)}</p><small>строка ${claim.line} · заявлено ${formatMetric(claim.value, display_kind)}</small></div><b class="${status}">${label(status)}${observed === null ? "" : ` · ${formatMetric(observed, display_kind)}`}</b></div>`).join("") : "<p>Числовые утверждения не найдены.</p>";
  const leakage = data.leakage ? `<div class="leak-box"><div><strong>${percent(data.leakage.exact_overlap_rate)}</strong><span>exact overlap</span></div><div><strong>${percent(data.leakage.normalized_overlap_rate)}</strong><span>normalized overlap</span></div><div><strong>${percent(data.leakage.near_overlap_rate)}</strong><span>near overlap</span></div><div><strong>${data.leakage.overlapping_group_count}</strong><span>общих групп</span></div></div>` : "<p>Train/test не загружены.</p>";
  const notebook = data.notebook ? `<div class="leak-box"><div><strong>${data.notebook.code_cells}</strong><span>code cells</span></div><div><strong>${data.notebook.has_random_seed ? "да" : "нет"}</strong><span>seed обнаружен</span></div></div>` : "<p>Notebook не загружен.</p>";
  const findings = data.findings.length ? data.findings.map((item) => `<div class="finding ${item.severity}"><b>${escapeHtml(item.code)}</b><br>${escapeHtml(item.message)}</div>`).join("") : '<div class="finding medium">Проверяемых несоответствий не найдено.</div>';
  result.innerHTML = `<div class="verdict ${data.status}"><p class="eyebrow">ИТОГ АУДИТА</p><h2>${data.status === "passed" ? "ПРОЙДЕНО" : "ТРЕБУЕТ ПРОВЕРКИ"}</h2><p>${data.findings.length} замечаний · ${data.artifacts.length} файлов зафиксировано</p></div><h3>Утверждения</h3>${claimRows}<h3>Разделение данных</h3>${leakage}<h3>Notebook</h3>${notebook}<h3>Замечания</h3>${findings}<p class="certificate">SHA-256 сертификата: ${escapeHtml(data.certificate_sha256)}</p>`;
}

function percent(value) { return `${(value * 100).toFixed(1)}%`; }
function formatMetric(value, displayKind) { return displayKind === "percentage" ? percent(value) : Number(value).toPrecision(6).replace(/\.?0+$/, ""); }
function label(value) { return ({ verified: "пересчитано", supported: "совпало с таблицей", mismatch: "расхождение", no_evidence: "нет данных" })[value]; }
function escapeHtml(value) { const node = document.createElement("div"); node.textContent = String(value); return node.innerHTML; }
