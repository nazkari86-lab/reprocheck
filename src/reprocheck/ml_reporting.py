from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .ml_evaluation import verify_frozen_evaluation


def build_frozen_scorecard(result: dict[str, Any]) -> dict[str, Any]:
    errors = verify_frozen_evaluation(result)
    if errors:
        raise ValueError("frozen evaluation integrity failure: " + "; ".join(errors))
    system = result["system"]
    baseline = result["baseline"]
    return {
        "source_result_sha256": result["result_sha256"],
        "phase": result["phase"],
        "gate_status": result["success_gate"]["status"],
        "owners": result["counts"]["owners"],
        "eligible_claims": result["counts"]["eligible_claims"],
        "system_precision": system["precision"],
        "system_precision_wilson_low": system["precision_wilson_95"][0],
        "system_recall": system["recall"],
        "system_claim_coverage": system["claim_coverage"],
        "baseline_precision": baseline["precision"],
        "baseline_recall": baseline["recall"],
        "recall_delta": result["comparison"]["recall_delta"],
        "language": result["subgroups"]["language"],
        "domain": result["subgroups"]["domain"],
        "calibration": result["calibration_metrics"],
    }


def render_risk_coverage_svg(result: dict[str, Any], path: Path) -> None:
    errors = verify_frozen_evaluation(result)
    if errors:
        raise ValueError("frozen evaluation integrity failure: " + "; ".join(errors))
    points = result.get("risk_coverage")
    if not isinstance(points, list) or not points:
        raise ValueError("frozen evaluation has no risk-coverage points")
    coordinates = []
    for point in points:
        coverage, risk = float(point["coverage"]), float(point["risk"])
        if not 0 <= coverage <= 1 or not 0 <= risk <= 1:
            raise ValueError("risk-coverage points must be in [0, 1]")
        coordinates.append(f"{70 + coverage * 500:.2f},{330 - risk * 260:.2f}")
    source = html.escape(str(result["result_sha256"]))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="400" viewBox="0 0 640 400" role="img" aria-labelledby="title desc">
<title id="title">Risk versus automatic decision coverage</title>
<desc id="desc">Generated only from frozen result {source}</desc>
<rect width="640" height="400" fill="#fbf6eb"/>
<path d="M70 60V330H580" fill="none" stroke="#18201c" stroke-width="2"/>
<path d="M70 278H580M70 226H580M70 174H580M70 122H580" stroke="#d8cfbd"/>
<polyline points="{" ".join(coordinates)}" fill="none" stroke="#e44b2a" stroke-width="4"/>
<text x="325" y="378" text-anchor="middle" font-family="monospace" font-size="14">AUTOMATIC DECISION COVERAGE</text>
<text x="20" y="195" text-anchor="middle" transform="rotate(-90 20 195)" font-family="monospace" font-size="14">RISK = 1 - PRECISION</text>
<text x="70" y="354" font-family="monospace" font-size="11">0%</text><text x="558" y="354" font-family="monospace" font-size="11">100%</text>
<text x="42" y="334" font-family="monospace" font-size="11">0%</text><text x="32" y="73" font-family="monospace" font-size="11">100%</text>
<text x="70" y="28" font-family="monospace" font-size="9">SOURCE SHA-256: {source}</text>
</svg>\n"""
    if path.exists():
        raise ValueError(f"figure output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def load_frozen_evaluation(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load frozen evaluation: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError("frozen evaluation must be a JSON object")
    return payload
