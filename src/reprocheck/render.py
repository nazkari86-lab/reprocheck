from __future__ import annotations

import html
from pathlib import Path

from .models import AuditReport


def render_html(report: AuditReport, output: Path) -> None:
    checks = (
        "".join(
            f"<tr><td>{html.escape(check.claim.metric)}</td>"
            f"<td>{check.claim.value:.3f}</td>"
            f"<td>{'—' if check.observed is None else f'{check.observed:.3f}'}</td>"
            f"<td><span class='status {check.status}'>{_status(check.status)}</span></td></tr>"
            for check in report.claims
        )
        or "<tr><td colspan='4'>Числовые утверждения не найдены.</td></tr>"
    )
    findings = (
        "".join(
            f"<li class='{item['severity']}'><b>{html.escape(str(item['code']))}</b> — "
            f"{html.escape(str(item['message']))}</li>"
            for item in report.findings
        )
        or "<li>Проверяемых несоответствий не найдено.</li>"
    )
    leakage = "Проверка split не выполнялась."
    if report.leakage:
        leakage = (
            f"Exact overlap: <b>{report.leakage.exact_overlap_rate:.1%}</b>; "
            f"normalized overlap: <b>{report.leakage.normalized_overlap_rate:.1%}</b>; "
            f"near overlap: <b>{report.leakage.near_overlap_rate:.1%}</b>; "
            f"group overlap: <b>{len(report.leakage.overlapping_groups)}</b>."
        )
    notebook = "Notebook audit не выполнялся."
    if report.notebook:
        notebook = (
            f"Code cells: <b>{report.notebook.code_cells}</b>; "
            f"seed detected: <b>{'yes' if report.notebook.has_random_seed else 'no'}</b>; "
            f"execution order: <b>{'monotonic' if report.notebook.execution_order_monotonic else 'suspect'}</b>."
        )
    output.write_text(
        f"""<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ReproCheck audit</title>
<style>
body{{font:17px/1.55 Georgia,serif;max-width:900px;margin:48px auto;padding:0 24px;color:#17211d;background:#f4f0e7}}
h1{{font-size:48px;line-height:1;margin:0 0 12px}} .card{{background:#fff;border:1px solid #c9c0ad;padding:24px;margin:20px 0;box-shadow:7px 7px 0 #17211d}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}
.status{{font:bold 12px monospace;text-transform:uppercase;padding:4px 7px}}.verified{{background:#cdebd8}}.supported{{background:#dce9f5}}.mismatch{{background:#ffc7b8}}.no_evidence{{background:#ffe8a8}}
.high{{color:#9b2518}}code{{font-family:monospace}}small{{color:#5b655f}}
</style>
<h1>ReproCheck</h1><p>Паспорт вычислительных доказательств</p>
<section class="card"><h2>Вердикт: {_overall(report.status)}</h2><p>{len(report.findings)} замечаний. Создан {html.escape(report.created_at)}.</p></section>
<section class="card"><h2>Утверждения</h2><table><tr><th>Метрика</th><th>Заявлено</th><th>Получено</th><th>Статус</th></tr>{checks}</table></section>
<section class="card"><h2>Разделение данных</h2><p>{leakage}</p></section>
<section class="card"><h2>Notebook</h2><p>{notebook}</p></section>
<section class="card"><h2>Замечания</h2><ul>{findings}</ul></section>
<small>ReproCheck {html.escape(report.tool_version)} · schema {html.escape(report.schema_version)}<br>certificate: {html.escape(report.certificate_sha256)}</small>
</html>""",
        encoding="utf-8",
    )


def _status(value: str) -> str:
    return {
        "verified": "пересчитано",
        "supported": "совпало с таблицей",
        "mismatch": "расхождение",
        "no_evidence": "нет данных",
    }[value]


def _overall(value: str) -> str:
    return "ТРЕБУЕТ ПРОВЕРКИ" if value == "needs_review" else "ПРОЙДЕНО"
