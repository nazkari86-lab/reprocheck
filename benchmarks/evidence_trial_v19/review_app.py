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


def load_packet(packet_path: Path) -> dict[str, Any]:
    payload = json.loads(packet_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != PACKET_SCHEMA:
        raise ValueError("unsupported blinded review packet")
    if payload.get("blind") is not True:
        raise ValueError("review packet is not marked blind")
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("review packet contains no claims")
    identifiers: list[object] = []
    for row in claims:
        if not isinstance(row, dict):
            raise ValueError("review packet claim must be an object")
        leaked = sorted(PRIVATE_FIELDS.intersection(row))
        if leaked:
            raise ValueError("review packet leaks private fields: " + ", ".join(leaked))
        claim_id = row.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            raise ValueError("review packet claim ID is missing")
        url = row.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError("review packet claim URL must use HTTPS")
        block = row.get("block")
        if (
            not isinstance(block, dict)
            or not isinstance(block.get("start"), int)
            or isinstance(block.get("start"), bool)
            or not isinstance(block.get("end"), int)
            or isinstance(block.get("end"), bool)
            or block["start"] < 1
            or block["end"] < block["start"]
        ):
            raise ValueError("review packet claim line block is invalid")
        claim_text = row.get("claim_text")
        if claim_text is not None and (not isinstance(claim_text, str) or not claim_text.strip()):
            raise ValueError("review packet embedded claim text is invalid")
        identifiers.append(claim_id)
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("review packet claim IDs must be unique")
    return payload


def validate_review(packet: dict[str, Any], packet_sha256: str, review: object) -> list[str]:
    if not isinstance(review, dict):
        return ["review must be a JSON object"]
    errors: list[str] = []
    allowed = {"schema_version", "reviewer_id", "independent", "packet_sha256", "reviews"}
    extra = sorted(set(review).difference(allowed))
    if extra:
        errors.append("unexpected review fields: " + ", ".join(extra))
    if review.get("schema_version") != REVIEW_SCHEMA:
        errors.append("unsupported review schema")
    reviewer_id = review.get("reviewer_id")
    if (
        not isinstance(reviewer_id, str)
        or not reviewer_id.strip()
        or reviewer_id.upper().startswith("REPLACE")
    ):
        errors.append("reviewer_id must be a stable non-identifying value")
    if review.get("independent") is not True:
        errors.append("reviewer independence must be explicitly confirmed")
    if review.get("packet_sha256") != packet_sha256:
        errors.append("review references a different blinded packet")
    rows = review.get("reviews")
    if not isinstance(rows, list):
        errors.append("reviews must be an array")
        return errors
    expected_ids = {row["claim_id"] for row in packet["claims"]}
    seen: set[str] = set()
    allowed_row = {"claim_id", "status", "rationale", "evidence_refs"}
    for index, row in enumerate(rows, start=1):
        label = f"review row {index}"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        unexpected = sorted(set(row).difference(allowed_row))
        if unexpected:
            errors.append(f"{label} has unexpected fields: {', '.join(unexpected)}")
        claim_id = row.get("claim_id")
        if not isinstance(claim_id, str) or claim_id not in expected_ids:
            errors.append(f"{label} references an unknown claim")
        elif claim_id in seen:
            errors.append(f"{label} repeats claim_id {claim_id}")
        else:
            seen.add(claim_id)
        if row.get("status") not in STATUSES:
            errors.append(f"{label} has an invalid status")
        rationale = row.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append(f"{label} requires a rationale")
        refs = row.get("evidence_refs")
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
        ):
            errors.append(f"{label} requires non-empty evidence_refs")
    missing = sorted(expected_ids.difference(seen))
    if missing:
        errors.append(f"review must cover every claim; {len(missing)} missing")
    return errors


def build_attestation(
    packet_sha256: str, review: dict[str, Any], packet_claim_count: int
) -> dict[str, Any]:
    review_sha256 = _sha256(_canonical_json(review))
    return {
        "schema_version": "reprocheck.evidence-trial-review-attestation.v1",
        "reviewer_id": review["reviewer_id"],
        "packet_sha256": packet_sha256,
        "review_sha256": review_sha256,
        "reviewed_claim_count": len(review["reviews"]),
        "packet_claim_count": packet_claim_count,
        "independent": True,
        "gold_labels_seen": False,
        "evaluator_outputs_seen": False,
        "other_reviewer_output_seen": False,
    }


class ReviewServer(ThreadingHTTPServer):
    packet: dict[str, Any]
    packet_sha256: str


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
            (json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        server = cast(ReviewServer, self.server)
        path = urlparse(self.path).path
        if path == "/":
            self._send(HTTPStatus.OK, HTML.encode(), "text/html; charset=utf-8")
        elif path == "/app.js":
            self._send(HTTPStatus.OK, JAVASCRIPT.encode(), "text/javascript; charset=utf-8")
        elif path == "/app.css":
            self._send(HTTPStatus.OK, CSS.encode(), "text/css; charset=utf-8")
        elif path == "/api/packet":
            self._json(
                HTTPStatus.OK,
                {"packet": server.packet, "packet_sha256": server.packet_sha256},
            )
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        server = cast(ReviewServer, self.server)
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
        review = request.get("review") if isinstance(request, dict) else None
        errors = validate_review(server.packet, server.packet_sha256, review)
        if errors:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"errors": errors})
            return
        assert isinstance(review, dict)
        attestation = build_attestation(server.packet_sha256, review, len(server.packet["claims"]))
        self._json(HTTPStatus.OK, {"review": review, "attestation": attestation})

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(packet_path: Path, host: str, port: int) -> None:
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("review server may bind only to loopback")
    packet_bytes = packet_path.read_bytes()
    packet = load_packet(packet_path)
    server = ReviewServer((host, port), Handler)
    server.packet = packet
    server.packet_sha256 = _sha256(packet_bytes)
    print(f"Blinded reviewer: http://{host}:{server.server_port}")
    print(f"Verified blind claims: {len(packet['claims'])}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local blinded Evidence Trial reviewer")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    serve(args.packet, args.host, args.port)
    return 0


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReproCheck Blinded Reviewer</title><link rel="stylesheet" href="/app.css"></head><body>
<header><div><p class="eyebrow">Evidence Trial v19</p><h1>Blinded claim review</h1></div><strong id="progress">0/0 complete</strong></header>
<section class="definitions" aria-label="Verdict definitions"><p><b>Supported</b> — cited evidence verifies the claim.</p><p><b>Contradicted</b> — cited evidence conflicts with the claim.</p><p><b>Not verifiable</b> — available evidence cannot decide.</p></section>
<main><aside><label for="search">Claims</label><input id="search" placeholder="Search claim or repository"><nav id="claims" aria-label="Review claims"></nav></aside>
<article><div id="empty">Choose a claim. Evaluator predictions and gold labels are not available here.</div><div id="editor" hidden tabindex="-1">
<p><span id="claimId" class="pill"></span> <span id="repository"></span></p><h2 id="claimText"></h2><p id="metadata"></p><a id="source" target="_blank" rel="noreferrer">Open immutable source</a>
<form id="decision"><fieldset><legend>Independent verdict</legend><label><input type="radio" name="status" value="supported" required> Supported</label><label><input type="radio" name="status" value="contradicted"> Contradicted</label><label><input type="radio" name="status" value="not_verifiable"> Not verifiable</label></fieldset>
<label>Rationale<textarea id="rationale" rows="6" required></textarea></label><label>Evidence references, one per line<textarea id="refs" rows="4" required></textarea></label><button type="submit">Save decision</button><p id="formError" class="error" role="alert"></p></form></div></article></main>
<footer><div><label>Reviewer ID<input id="reviewerId" placeholder="stable non-identifying ID"></label><label class="independence"><input id="independent" type="checkbox"> I am independent from the evaluator, curator, and sampled repository authors.</label></div><button id="export">Validate and export</button><p id="exportError" class="error" role="alert"></p></footer>
<script src="/app.js"></script></body></html>"""


CSS = """:root{font-family:ui-sans-serif,system-ui,sans-serif;color:#172019;background:#f4f7f3;line-height:1.45}*{box-sizing:border-box}body{margin:0}header{display:flex;justify-content:space-between;align-items:center;padding:20px 28px;background:#102d21;color:#fff}h1,h2,p{margin-top:0}.eyebrow{margin:0;color:#9dd3b8;text-transform:uppercase;letter-spacing:.12em;font-size:12px}header strong,.pill{background:#28523f;color:#fff;padding:7px 10px;border-radius:999px}.definitions{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:12px 24px;background:#e7f0ea}.definitions p{margin:0}main{display:grid;grid-template-columns:330px 1fr;min-height:calc(100vh - 270px)}aside{padding:20px;background:#fff;border-right:1px solid #cfdbd3}input,textarea,button{font:inherit}input,textarea{width:100%;border:1px solid #9fb2a6;border-radius:8px;padding:9px}nav{margin-top:12px;max-height:58vh;overflow:auto}.claim-link{display:block;width:100%;padding:10px 8px;text-align:left;border:0;border-bottom:1px solid #e2e9e4;background:#fff;color:#173f2c;cursor:pointer}.claim-link.active,.claim-link:hover{background:#e8f3ed}.claim-link.done:after{content:'✓';float:right}.claim-link small{display:block;color:#607167}article{padding:28px;min-width:0}#empty{padding:70px;text-align:center;color:#607167}#claimText{max-width:900px;white-space:pre-wrap}form{max-width:760px;margin-top:24px;background:#fff;border:1px solid #cfdbd3;border-radius:10px;padding:18px}fieldset{display:flex;gap:20px;border:0;padding:0;margin:0 0 16px}fieldset label{font-weight:650}fieldset input,.independence input{width:auto}label{display:block;font-weight:650;margin-bottom:14px}button{border:1px solid #17633f;border-radius:8px;padding:10px 14px;background:#17633f;color:#fff;cursor:pointer}a{color:#147249}.error{color:#a42525;margin:8px 0 0}footer{display:flex;align-items:end;justify-content:space-between;gap:18px;padding:14px 24px;background:#fff;border-top:1px solid #cfdbd3}footer>div{display:flex;gap:18px;align-items:end}.independence{max-width:520px}@media(max-width:760px){header,.definitions,main,footer,footer>div{display:block}.definitions p{margin-bottom:8px}nav{max-height:220px}fieldset{display:block}footer button{margin-top:12px}}
"""


JAVASCRIPT = r"""'use strict';
let packet,packetSha,currentId,state={reviews:{}};const $=id=>document.getElementById(id);const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stateKey=()=>`reprocheck-v19-review-${packetSha}`;const save=()=>localStorage.setItem(stateKey(),JSON.stringify(state));
function progress(){const n=Object.keys(state.reviews).length;$('progress').textContent=`${n}/${packet.claims.length} complete`;}
function renderList(filter=''){const q=filter.toLowerCase();$('claims').innerHTML=packet.claims.filter(c=>`${c.claim_id} ${c.repository||''} ${c.claim_text}`.toLowerCase().includes(q)).map(c=>`<button class="claim-link ${c.claim_id===currentId?'active':''} ${state.reviews[c.claim_id]?'done':''}" data-id="${esc(c.claim_id)}"><b>${esc(c.claim_id)}</b><small>${esc(c.repository||'')} · ${esc(c.declared_metric||'unspecified metric')}</small></button>`).join('');document.querySelectorAll('.claim-link').forEach(b=>b.onclick=()=>openClaim(b.dataset.id));}
function openClaim(id){currentId=id;const c=packet.claims.find(x=>x.claim_id===id),prior=state.reviews[id];$('empty').hidden=true;$('editor').hidden=false;$('claimId').textContent=id;$('repository').textContent=c.repository||'';$('claimText').textContent=c.claim_text||'Claim text is not embedded in this legacy packet; inspect the immutable source block.';$('metadata').textContent=`Lines ${c.block?.start||'?'}–${c.block?.end||'?'} · ${c.evidence_tier||'unspecified evidence'}`;$('source').href=c.url||'#';document.querySelectorAll('[name=status]').forEach(el=>el.checked=prior?.status===el.value);$('rationale').value=prior?.rationale||'';$('refs').value=(prior?.evidence_refs||[`${c.url}#L${c.block?.start}-L${c.block?.end}`]).join('\n');renderList($('search').value);$('editor').focus({preventScroll:true});}
$('decision').onsubmit=e=>{e.preventDefault();$('formError').textContent='';const status=document.querySelector('[name=status]:checked')?.value,rationale=$('rationale').value.trim(),refs=$('refs').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);if(!status||!rationale||!refs.length){$('formError').textContent='Verdict, rationale, and at least one evidence reference are required.';return}state.reviews[currentId]={claim_id:currentId,status,rationale,evidence_refs:refs};save();renderList($('search').value);progress();};
$('search').oninput=e=>renderList(e.target.value);function download(name,payload){const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}
$('export').onclick=async()=>{const review={schema_version:'reprocheck.evidence-trial-review.v1',reviewer_id:$('reviewerId').value.trim(),independent:$('independent').checked,packet_sha256:packetSha,reviews:packet.claims.map(c=>state.reviews[c.claim_id]).filter(Boolean)};$('exportError').textContent='';const r=await fetch('/api/finalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({review})});const result=await r.json();if(!r.ok){$('exportError').textContent=result.errors.join(' · ');return}download(`review-${review.reviewer_id}.json`,result.review);download(`review-attestation-${review.reviewer_id}.json`,result.attestation);};
fetch('/api/packet').then(r=>r.json()).then(x=>{packet=x.packet;packetSha=x.packet_sha256;state=JSON.parse(localStorage.getItem(stateKey())||'{"reviews":{}}');renderList();progress();}).catch(e=>$('empty').textContent=e.message);
"""


if __name__ == "__main__":
    raise SystemExit(main())
