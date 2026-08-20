from __future__ import annotations

import argparse
import hashlib
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse


PACKET_SCHEMA = "reprocheck.evidence-trial-review-packet.v1"
REVIEW_SCHEMA = "reprocheck.evidence-trial-review.v1"
STATUSES = {"supported", "contradicted", "not_verifiable"}
PRIVATE_FIELDS = {
    "gold_status",
    "gold_metric",
    "gold_value",
    "gold_rationale",
    "gold_evidence_refs",
    "prediction",
    "predictions",
    "evaluator_output",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _load_object(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def build_disagreement_packet(packet_path: Path, reviewer_paths: list[Path]) -> dict[str, Any]:
    if len(reviewer_paths) != 2:
        raise ValueError("exactly two review files are required")
    packet_bytes = packet_path.read_bytes()
    packet = _load_object(packet_path, "review packet")
    if packet.get("schema_version") != PACKET_SCHEMA or packet.get("blind") is not True:
        raise ValueError("unsupported or unblinded review packet")
    claims = packet.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("review packet contains no claims")
    claim_by_id: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("claim_id"), str):
            raise ValueError("review packet has an invalid claim")
        if PRIVATE_FIELDS.intersection(claim):
            raise ValueError("review packet leaks private evaluator or gold fields")
        url = claim.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError("review packet claim URL must use HTTPS")
        if claim["claim_id"] in claim_by_id:
            raise ValueError("review packet claim IDs must be unique")
        claim_by_id[claim["claim_id"]] = claim
    packet_sha256 = _sha256(packet_bytes)
    reviewers: list[tuple[str, dict[str, dict[str, Any]], str]] = []
    for path in reviewer_paths:
        payload = _load_object(path, "review")
        if payload.get("schema_version") != REVIEW_SCHEMA:
            raise ValueError("unsupported review schema")
        if set(payload) != {
            "schema_version",
            "reviewer_id",
            "independent",
            "packet_sha256",
            "reviews",
        }:
            raise ValueError("review contains unexpected fields")
        reviewer_id = payload.get("reviewer_id")
        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            raise ValueError("reviewer ID is missing")
        if payload.get("independent") is not True:
            raise ValueError("review independence is not confirmed")
        if payload.get("packet_sha256") != packet_sha256:
            raise ValueError("review references a different blinded packet")
        rows = payload.get("reviews")
        if not isinstance(rows, list):
            raise ValueError("review rows are missing")
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            if (
                not isinstance(row, dict)
                or set(row) != {"claim_id", "status", "rationale", "evidence_refs"}
                or row.get("status") not in STATUSES
                or not isinstance(row.get("rationale"), str)
                or not row["rationale"].strip()
                or not isinstance(row.get("evidence_refs"), list)
                or not row["evidence_refs"]
                or any(not isinstance(ref, str) or not ref.strip() for ref in row["evidence_refs"])
            ):
                raise ValueError("review contains an invalid row")
            claim_id = row.get("claim_id")
            if not isinstance(claim_id, str) or claim_id in by_id:
                raise ValueError("review claim IDs must be unique")
            by_id[claim_id] = row
        if set(by_id) != set(claim_by_id):
            raise ValueError("review must cover every packet claim exactly once")
        reviewers.append((reviewer_id, by_id, _sha256(path.read_bytes())))
    if reviewers[0][0] == reviewers[1][0]:
        raise ValueError("reviewer IDs must be distinct")
    disagreements = []
    for claim_id in sorted(claim_by_id):
        first = reviewers[0][1][claim_id]
        second = reviewers[1][1][claim_id]
        if first["status"] != second["status"]:
            disagreements.append(
                {
                    "claim": claim_by_id[claim_id],
                    "reviewer_a": {
                        key: first[key] for key in ("status", "rationale", "evidence_refs")
                    },
                    "reviewer_b": {
                        key: second[key] for key in ("status", "rationale", "evidence_refs")
                    },
                }
            )
    return {
        "schema_version": "reprocheck.evidence-trial-adjudication-packet.v1",
        "blind_to_evaluator_outputs": True,
        "packet_sha256": packet_sha256,
        "review_sha256": [reviewers[0][2], reviewers[1][2]],
        "claim_count": len(claim_by_id),
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
    }


def validate_adjudication(
    packet: dict[str, Any], adjudication: object, adjudicator_id: object, independent: object
) -> list[str]:
    errors: list[str] = []
    if not isinstance(adjudicator_id, str) or not adjudicator_id.strip():
        errors.append("adjudicator_id must be a stable non-identifying value")
    if independent is not True:
        errors.append("adjudicator independence must be explicitly confirmed")
    if not isinstance(adjudication, dict) or set(adjudication) != {"adjudications"}:
        return errors + ["adjudication must contain only adjudications"]
    rows = adjudication.get("adjudications")
    if not isinstance(rows, list):
        return errors + ["adjudications must be an array"]
    expected = {row["claim"]["claim_id"] for row in packet["disagreements"]}
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        label = f"adjudication row {index}"
        if not isinstance(row, dict) or set(row) != {
            "claim_id",
            "status",
            "rationale",
            "evidence_refs",
        }:
            errors.append(f"{label} has invalid fields")
            continue
        claim_id = row.get("claim_id")
        if not isinstance(claim_id, str) or claim_id not in expected:
            errors.append(f"{label} references a non-disagreement claim")
        elif claim_id in seen:
            errors.append(f"{label} repeats claim_id {claim_id}")
        else:
            seen.add(claim_id)
        if row.get("status") not in STATUSES:
            errors.append(f"{label} has an invalid status")
        if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            errors.append(f"{label} requires a rationale")
        refs = row.get("evidence_refs")
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
        ):
            errors.append(f"{label} requires non-empty evidence_refs")
    if seen != expected:
        errors.append(f"adjudication must resolve all {len(expected)} disagreements exactly once")
    return errors


def build_attestation(
    packet: dict[str, Any], adjudication: dict[str, Any], adjudicator_id: str
) -> dict[str, Any]:
    return {
        "schema_version": "reprocheck.evidence-trial-adjudication-attestation.v1",
        "adjudicator_id": adjudicator_id,
        "packet_sha256": packet["packet_sha256"],
        "review_sha256": packet["review_sha256"],
        "adjudication_sha256": _sha256(_canonical_json(adjudication)),
        "resolved_disagreement_count": len(adjudication["adjudications"]),
        "independent": True,
        "evaluator_outputs_seen": False,
    }


class AdjudicationServer(ThreadingHTTPServer):
    packet: dict[str, Any]


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: object) -> None:
        self._send(
            status,
            (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode(),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        server = cast(AdjudicationServer, self.server)
        path = urlparse(self.path).path
        if path == "/":
            self._send(HTTPStatus.OK, HTML.encode(), "text/html; charset=utf-8")
        elif path == "/app.js":
            self._send(HTTPStatus.OK, JAVASCRIPT.encode(), "text/javascript; charset=utf-8")
        elif path == "/app.css":
            self._send(HTTPStatus.OK, CSS.encode(), "text/css; charset=utf-8")
        elif path == "/api/packet":
            self._json(HTTPStatus.OK, server.packet)
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        server = cast(AdjudicationServer, self.server)
        if urlparse(self.path).path != "/api/finalize":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"errors": ["invalid Content-Length"]})
            return
        if length <= 0 or length > 5_000_000:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"errors": ["invalid body size"]})
            return
        try:
            request = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"errors": ["body must be UTF-8 JSON"]})
            return
        if not isinstance(request, dict):
            self._json(HTTPStatus.BAD_REQUEST, {"errors": ["body must be a JSON object"]})
            return
        adjudication = request.get("adjudication")
        errors = validate_adjudication(
            server.packet,
            adjudication,
            request.get("adjudicator_id"),
            request.get("independent"),
        )
        if errors:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"errors": errors})
            return
        assert isinstance(adjudication, dict)
        attestation = build_attestation(
            server.packet, adjudication, cast(str, request["adjudicator_id"])
        )
        self._json(HTTPStatus.OK, {"adjudication": adjudication, "attestation": attestation})

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(packet: dict[str, Any], host: str, port: int) -> None:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("adjudication server may bind only to loopback")
    server = AdjudicationServer((host, port), Handler)
    server.packet = packet
    print(f"Independent adjudicator: http://{host}:{server.server_port}")
    print(f"Disagreements: {packet['disagreement_count']}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local Evidence Trial disagreement adjudicator")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--reviewer", type=Path, action="append", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args(argv)
    packet = build_disagreement_packet(args.packet, args.reviewer)
    if packet["disagreement_count"] == 0:
        print("No disagreements: trial-lock-gold requires no adjudication file.")
        return 0
    serve(packet, args.host, args.port)
    return 0


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReproCheck Independent Adjudicator</title><link rel="stylesheet" href="/app.css"></head><body>
<header><div><p class="eyebrow">Evidence Trial v19</p><h1>Resolve reviewer disagreements</h1></div><strong id="progress">0/0 resolved</strong></header><p class="notice">Only disagreements are shown. ReproCheck predictions and gold labels are unavailable.</p>
<main><nav id="list" aria-label="Disagreements"></nav><article><div id="empty">Choose a disagreement.</div><div id="editor" hidden tabindex="-1"><span id="claimId" class="pill"></span><h2 id="claimText"></h2><a id="source" target="_blank" rel="noreferrer">Open immutable source</a><section class="reviews"><div><h3>Reviewer A</h3><b id="aStatus"></b><p id="aRationale"></p><ul id="aRefs"></ul></div><div><h3>Reviewer B</h3><b id="bStatus"></b><p id="bRationale"></p><ul id="bRefs"></ul></div></section><form id="decision"><fieldset><legend>Final evidence-based verdict</legend><label><input type="radio" name="status" value="supported" required> Supported</label><label><input type="radio" name="status" value="contradicted"> Contradicted</label><label><input type="radio" name="status" value="not_verifiable"> Not verifiable</label></fieldset><label>Rationale<textarea id="rationale" rows="5" required></textarea></label><label>Evidence references, one per line<textarea id="refs" rows="4" required></textarea></label><button type="submit">Save resolution</button><p id="formError" class="error" role="alert"></p></form></div></article></main>
<footer><div><label>Adjudicator ID<input id="adjudicatorId" placeholder="stable non-identifying ID"></label><label><input id="independent" type="checkbox"> I am independent from the evaluator, curator, reviewers, and sampled authors.</label></div><button id="export">Validate and export</button><p id="exportError" class="error" role="alert"></p></footer><script src="/app.js"></script></body></html>"""


CSS = """:root{font-family:ui-sans-serif,system-ui,sans-serif;color:#1e221f;background:#f5f6f3;line-height:1.45}*{box-sizing:border-box}body{margin:0}header{display:flex;justify-content:space-between;align-items:center;padding:20px 28px;background:#352a16;color:#fff}h1,h2,p{margin-top:0}.eyebrow{margin:0;color:#efd99f;text-transform:uppercase;letter-spacing:.12em;font-size:12px}header strong,.pill{background:#6b5426;color:#fff;padding:7px 10px;border-radius:999px}.notice{margin:0;padding:12px 24px;background:#f7eac8}main{display:grid;grid-template-columns:290px 1fr;min-height:calc(100vh - 250px)}nav{padding:18px;background:#fff;border-right:1px solid #ddd3bd;overflow:auto;max-height:70vh}.item{display:block;width:100%;padding:11px 8px;text-align:left;border:0;border-bottom:1px solid #eee6d5;background:#fff;color:#3d3019;cursor:pointer}.item small{display:block;color:#6f6042}.item.active,.item:hover{background:#faf0d9}.item.done:after{content:'✓';float:right;color:#6b5426}article{padding:28px}.reviews{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:22px 0}.reviews>div,form{background:#fff;border:1px solid #ddd3bd;border-radius:10px;padding:16px}fieldset{display:flex;gap:18px;border:0;padding:0;margin-bottom:14px}label{display:block;font-weight:650;margin-bottom:12px}input,textarea,button{font:inherit}input:not([type=radio]):not([type=checkbox]),textarea{width:100%;padding:9px;border:1px solid #b9aa8c;border-radius:8px}button{padding:10px 14px;border:1px solid #6b5426;border-radius:8px;background:#6b5426;color:#fff;cursor:pointer}.error{color:#a42525}a{color:#765a1b}footer{display:flex;justify-content:space-between;align-items:end;gap:18px;padding:14px 24px;background:#fff;border-top:1px solid #ddd3bd}footer>div{display:flex;gap:18px;align-items:end}footer label:last-child{max-width:520px}@media(max-width:760px){header,main,footer,footer>div,.reviews{display:block}nav{max-height:220px}fieldset{display:block}footer button{margin-top:12px}}
"""


JAVASCRIPT = r"""'use strict';
let packet,currentId,state={rows:{}};const $=id=>document.getElementById(id);const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const key=()=>`reprocheck-v19-adjudication-${packet.packet_sha256}-${packet.review_sha256.join('-')}`;const save=()=>localStorage.setItem(key(),JSON.stringify(state));
function progress(){ $('progress').textContent=`${Object.keys(state.rows).length}/${packet.disagreement_count} resolved`; }function renderList(){$('list').innerHTML=packet.disagreements.map(d=>{const id=d.claim.claim_id;return `<button class="item ${id===currentId?'active':''} ${state.rows[id]?'done':''}" data-id="${esc(id)}"><b>${esc(id)}</b><small>${esc(d.reviewer_a.status)} ↔ ${esc(d.reviewer_b.status)}</small></button>`}).join('');document.querySelectorAll('.item').forEach(b=>b.onclick=()=>openItem(b.dataset.id));}
function refs(id,items){$(id).innerHTML=items.map(x=>`<li>${esc(x)}</li>`).join('')}function openItem(id){currentId=id;const d=packet.disagreements.find(x=>x.claim.claim_id===id),prior=state.rows[id];$('empty').hidden=true;$('editor').hidden=false;$('claimId').textContent=id;$('claimText').textContent=d.claim.claim_text||'Claim text is unavailable; inspect the immutable source.';$('source').href=d.claim.url||'#';$('aStatus').textContent=d.reviewer_a.status;$('aRationale').textContent=d.reviewer_a.rationale;refs('aRefs',d.reviewer_a.evidence_refs);$('bStatus').textContent=d.reviewer_b.status;$('bRationale').textContent=d.reviewer_b.rationale;refs('bRefs',d.reviewer_b.evidence_refs);document.querySelectorAll('[name=status]').forEach(el=>el.checked=prior?.status===el.value);$('rationale').value=prior?.rationale||'';$('refs').value=(prior?.evidence_refs||[]).join('\n');renderList();$('editor').focus({preventScroll:true});}
$('decision').onsubmit=e=>{e.preventDefault();const status=document.querySelector('[name=status]:checked')?.value,rationale=$('rationale').value.trim(),evidence_refs=$('refs').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);$('formError').textContent='';if(!status||!rationale||!evidence_refs.length){$('formError').textContent='Verdict, rationale, and evidence references are required.';return}state.rows[currentId]={claim_id:currentId,status,rationale,evidence_refs};save();renderList();progress();};function download(name,payload){const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}
$('export').onclick=async()=>{const request={adjudicator_id:$('adjudicatorId').value.trim(),independent:$('independent').checked,adjudication:{adjudications:packet.disagreements.map(d=>state.rows[d.claim.claim_id]).filter(Boolean)}};$('exportError').textContent='';const r=await fetch('/api/finalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});const result=await r.json();if(!r.ok){$('exportError').textContent=result.errors.join(' · ');return}download('adjudication.json',result.adjudication);download('adjudication-attestation.json',result.attestation);};fetch('/api/packet').then(r=>r.json()).then(p=>{packet=p;state=JSON.parse(localStorage.getItem(key())||'{"rows":{}}');renderList();progress();}).catch(e=>$('empty').textContent=e.message);
"""


if __name__ == "__main__":
    raise SystemExit(main())
