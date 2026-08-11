from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import AuditReport


_ACTION_CATEGORY = {
    "metric_evidence_conflict": "reconcile_metrics",
    "claim_metric_mismatch": "reconcile_metrics",
    "claim_without_evidence": "add_metric_evidence",
    "no_metric_claims_detected": "add_metric_claims",
    "exact_split_overlap": "rebuild_splits",
    "normalized_split_overlap": "rebuild_splits",
    "group_split_overlap": "rebuild_splits",
    "near_text_split_overlap": "review_near_duplicates",
    "preprocessing_before_split": "fix_training_order",
    "fit_on_test_data": "remove_test_training",
    "fit_on_test_dataflow": "remove_test_training",
    "non_monotonic_notebook_execution": "rerun_notebook",
    "random_seed_not_detected": "declare_seed",
    "unparsed_notebook_cells": "review_notebook_cells",
    "nothing_auditable_detected": "add_auditable_inputs",
}

_ACTION_COPY = {
    "reconcile_metrics": (
        "Сверьте числа в отчёте",
        "Пересчитайте метрики из тех же predictions и исправьте отчёт либо входные evidence.",
    ),
    "add_metric_evidence": (
        "Добавьте доказательство метрик",
        "Приложите predictions.csv или metrics.json, чтобы числовые выводы можно было проверить.",
    ),
    "add_metric_claims": (
        "Свяжите evidence с выводом",
        "Укажите поддерживаемую метрику в отчёте, чтобы ReproCheck сопоставил число и источник.",
    ),
    "rebuild_splits": (
        "Пересоберите train/test",
        "Разделяйте по объекту или группе до обучения и повторно сохраните оба split-файла.",
    ),
    "review_near_duplicates": (
        "Проверьте похожие объекты",
        "Просмотрите near-match примеры и удалите семантически одинаковые записи между split-ами.",
    ),
    "fix_training_order": (
        "Разделите данные до fit",
        "Сначала создайте train/test, затем обучайте preprocessing только на train.",
    ),
    "remove_test_training": (
        "Исключите test из обучения",
        "Уберите test-derived данные из fit/fit_transform и пересчитайте результат на чистом test.",
    ),
    "rerun_notebook": (
        "Перезапустите notebook с нуля",
        "Restart Kernel + Run All устранит скрытую зависимость от порядка выполнения ячеек.",
    ),
    "declare_seed": (
        "Зафиксируйте random seed",
        "Задайте seed для используемых библиотек и сохраните его рядом с параметрами эксперимента.",
    ),
    "review_notebook_cells": (
        "Проверьте непроанализированные ячейки",
        "Вынесите notebook magics или неполные фрагменты так, чтобы статический анализ видел код.",
    ),
    "add_auditable_inputs": (
        "Добавьте проверяемый материал",
        "Нужен числовой вывод, пара train/test или notebook с вычислительным экспериментом.",
    ),
    "audit_splits": (
        "Добавьте train и test",
        "Это включит независимую проверку точных, нормализованных, групповых и near-duplicate утечек.",
    ),
    "audit_notebook": (
        "Добавьте notebook",
        "Статический аудит проверит порядок выполнения, seed и попадание test-данных в fit.",
    ),
    "preserve_certificate": (
        "Сохраните сертификат вместе с результатом",
        "Опубликуйте JSON-сертификат и исходные артефакты, чтобы проверку можно было повторить.",
    ),
}

_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}


def build_audit_guide(report: AuditReport) -> dict[str, Any]:
    total_claims = len(report.claims)
    with_evidence = sum(check.status != "no_evidence" for check in report.claims)
    independently_recomputed = sum(check.evidence_level == "recomputed" for check in report.claims)
    matched = sum(check.status in {"verified", "supported"} for check in report.claims)
    mismatched = sum(check.status == "mismatch" for check in report.claims)
    recomputed_metrics = sum(
        item.evidence_level == "recomputed" for item in report.metric_evidence.values()
    )

    layers = [
        {
            "id": "claims",
            "status": "checked" if total_claims else "not_provided",
            "detail": f"{total_claims} числовых выводов найдено",
        },
        {
            "id": "metrics",
            "status": (
                "checked"
                if recomputed_metrics
                else "partial"
                if report.metric_evidence
                else "not_provided"
            ),
            "detail": (
                f"{recomputed_metrics} метрик независимо пересчитано"
                if recomputed_metrics
                else f"{len(report.metric_evidence)} готовых метрик прочитано"
                if report.metric_evidence
                else "predictions или metrics не предоставлены"
            ),
        },
        {
            "id": "splits",
            "status": "checked" if report.leakage else "not_provided",
            "detail": (
                f"{report.leakage.train_rows} train / {report.leakage.test_rows} test"
                if report.leakage
                else "train/test не предоставлены"
            ),
        },
        {
            "id": "notebook",
            "status": "checked" if report.notebook else "not_provided",
            "detail": (
                f"{report.notebook.code_cells} code cells проверено"
                if report.notebook
                else "notebook не предоставлен"
            ),
        },
        {
            "id": "certificate",
            "status": "checked",
            "detail": f"SHA-256 {report.certificate_sha256[:12]}...",
        },
    ]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in sorted(
        report.findings,
        key=lambda item: (_SEVERITY_RANK.get(str(item.get("severity")), 4), str(item.get("code"))),
    ):
        category = _ACTION_CATEGORY.get(str(finding.get("code")))
        if category is not None:
            grouped[category].append(finding)

    actions = [_action(category, findings) for category, findings in grouped.items()]
    existing = {item["id"] for item in actions}
    if not report.metric_evidence and total_claims and "add_metric_evidence" not in existing:
        actions.append(_coverage_action("add_metric_evidence"))
    if report.leakage is None and "rebuild_splits" not in existing:
        actions.append(_coverage_action("audit_splits"))
    if report.notebook is None and not existing.intersection(
        {"fix_training_order", "remove_test_training", "rerun_notebook", "declare_seed"}
    ):
        actions.append(_coverage_action("audit_notebook"))
    if not actions:
        actions.append(_coverage_action("preserve_certificate"))

    return {
        "schema_version": "reprocheck.guide.v1",
        "derived_from_certificate_sha256": report.certificate_sha256,
        "claim_coverage": {
            "total": total_claims,
            "with_evidence": with_evidence,
            "independently_recomputed": independently_recomputed,
            "matched": matched,
            "mismatched": mismatched,
        },
        "layers": layers,
        "actions": actions[:4],
        "boundary": (
            "Паспорт описывает покрытие предоставленных артефактов. "
            "Он не доказывает научную истинность гипотезы и не заменяет внешнюю репликацию."
        ),
    }


def _action(category: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    severities = {str(item.get("severity")) for item in findings}
    priority = (
        "critical" if "high" in severities else "important" if "medium" in severities else "improve"
    )
    title, detail = _ACTION_COPY[category]
    return {
        "id": category,
        "priority": priority,
        "title": title,
        "detail": detail,
        "source_codes": sorted({str(item.get("code")) for item in findings}),
    }


def _coverage_action(category: str) -> dict[str, Any]:
    title, detail = _ACTION_COPY[category]
    return {
        "id": category,
        "priority": "coverage",
        "title": title,
        "detail": detail,
        "source_codes": [],
    }
