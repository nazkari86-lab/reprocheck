from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse


PACKET_SCHEMA = "reprocheck.evidence-trial-curation-packet.v1"
ENROLLMENT_SCHEMA = "reprocheck.evidence-trial-enrollment.v1"
TIERS = {"report_only", "supplied_metrics", "raw_recomputation"}
CLAIM_ID = re.compile(r"^claim-[0-9]{3,}$")
PRIVATE_FIELDS = {
    "gold_status",
    "gold_metric",
    "gold_value",
    "gold_rationale",
    "gold_evidence_refs",
    "prediction",
    "predictions",
    "evaluator_output",
    "evaluator_outputs",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _contains_private_field(value: object) -> bool:
    if isinstance(value, dict):
        return bool(PRIVATE_FIELDS.intersection(value)) or any(
            _contains_private_field(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_private_field(item) for item in value)
    return False


def load_packet(packet_path: Path) -> dict[str, Any]:
    payload = json.loads(packet_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != PACKET_SCHEMA:
        raise ValueError("unsupported curation packet")
    if payload.get("blind_to_outcome_labels") is not True or _contains_private_field(payload):
        raise ValueError("curation packet is not structurally outcome-blind")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("curation packet contains no candidates")
    identifiers = [row.get("candidate_id") for row in candidates if isinstance(row, dict)]
    if len(identifiers) != len(candidates) or len(identifiers) != len(set(identifiers)):
        raise ValueError("curation packet candidate IDs must be unique")
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get("immutable_url"), str)
        or not row["immutable_url"].startswith("https://github.com/")
        for row in candidates
    ):
        raise ValueError("curation packet contains an unsafe immutable URL")
    if payload.get("candidate_count") != len(candidates):
        raise ValueError("curation packet candidate count does not match")
    return payload


def verify_sources(packet_path: Path, packet: dict[str, Any]) -> dict[str, Path]:
    base = packet_path.parent
    result: dict[str, Path] = {}
    for row in packet["candidates"]:
        relative = row.get("source_file")
        if not isinstance(relative, str):
            raise ValueError("candidate source path is missing")
        source = (base / "acquisition-v5" / relative).resolve()
        source_root = (base / "acquisition-v5" / "sources").resolve()
        if not source.is_relative_to(source_root) or not source.is_file():
            raise ValueError(f"candidate source is unavailable: {row['candidate_id']}")
        data = source.read_bytes()
        if len(data) != row.get("source_bytes") or _sha256(data) != row.get("source_sha256"):
            raise ValueError(f"candidate source checksum mismatch: {row['candidate_id']}")
        data.decode("utf-8")
        result[row["candidate_id"]] = source
    return result


def validate_enrollment(
    packet: dict[str, Any], source_paths: dict[str, Path], enrollment: object
) -> list[str]:
    if not isinstance(enrollment, dict):
        return ["enrollment must be a JSON object"]
    errors: list[str] = []
    allowed = {
        "schema_version",
        "curator_id",
        "independent_from_evaluator",
        "candidate_manifest_sha256",
        "claims",
    }
    extra = sorted(set(enrollment).difference(allowed))
    if extra:
        errors.append("unexpected enrollment fields: " + ", ".join(extra))
    if enrollment.get("schema_version") != ENROLLMENT_SCHEMA:
        errors.append("unsupported enrollment schema")
    curator = enrollment.get("curator_id")
    if not isinstance(curator, str) or not curator.strip():
        errors.append("curator_id must be non-empty")
    if enrollment.get("independent_from_evaluator") is not True:
        errors.append("independence must be explicitly confirmed")
    expected_manifest = packet["candidate_manifest"]["sha256"]
    if enrollment.get("candidate_manifest_sha256") != expected_manifest:
        errors.append("candidate manifest checksum does not match the curation packet")
    claims = enrollment.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("at least one claim is required")
        return errors
    seen_ids: set[str] = set()
    candidate_by_id = {row["candidate_id"]: row for row in packet["candidates"]}
    for index, claim in enumerate(claims, start=1):
        label = f"claim row {index}"
        if not isinstance(claim, dict):
            errors.append(f"{label} must be an object")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not CLAIM_ID.fullmatch(claim_id):
            errors.append(f"{label} has an invalid claim_id")
        elif claim_id in seen_ids:
            errors.append(f"{label} repeats claim_id {claim_id}")
        else:
            seen_ids.add(claim_id)
        candidate_id = claim.get("candidate_id")
        if not isinstance(candidate_id, str) or candidate_id not in candidate_by_id:
            errors.append(f"{label} references an unknown candidate")
            continue
        allowed_claim = {
            "claim_id",
            "candidate_id",
            "block",
            "claim_text",
            "declared_metric",
            "declared_value",
            "stratum",
            "evidence_tier",
        }
        unexpected = sorted(set(claim).difference(allowed_claim))
        if unexpected:
            errors.append(f"{label} has unexpected fields: {', '.join(unexpected)}")
        block = claim.get("block")
        if not isinstance(block, dict) or set(block) != {"start", "end"}:
            errors.append(f"{label} block must contain only start and end")
            continue
        start = block.get("start")
        end = block.get("end")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 1
            or end < start
        ):
            errors.append(f"{label} has an invalid line range")
            continue
        lines = source_paths[candidate_id].read_text(encoding="utf-8").splitlines()
        if end > len(lines):
            errors.append(f"{label} line range exceeds the source")
            continue
        expected_text = "\n".join(lines[start - 1 : end]).strip()
        text = claim.get("claim_text")
        if not isinstance(text, str) or text.strip() != expected_text:
            errors.append(f"{label} text does not match the frozen source lines")
        if claim.get("stratum") != "natural_unadjudicated":
            errors.append(f"{label} must use natural_unadjudicated")
        if claim.get("evidence_tier") not in TIERS:
            errors.append(f"{label} has an invalid evidence tier")
        metric = claim.get("declared_metric")
        if metric is not None and (not isinstance(metric, str) or not metric.strip()):
            errors.append(f"{label} has an invalid declared metric")
        value = claim.get("declared_value")
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)):
            errors.append(f"{label} has an invalid declared value")
    return errors


def build_attestation(
    packet: dict[str, Any], enrollment: dict[str, Any], reviewed_candidate_ids: object
) -> dict[str, Any]:
    expected = sorted(row["candidate_id"] for row in packet["candidates"])
    if not isinstance(reviewed_candidate_ids, list) or sorted(reviewed_candidate_ids) != expected:
        raise ValueError("all candidate files must be marked reviewed exactly once")
    enrollment_bytes = _canonical_json(enrollment)
    return {
        "schema_version": "reprocheck.evidence-trial-curation-attestation.v1",
        "curator_id": enrollment["curator_id"],
        "candidate_manifest_sha256": packet["candidate_manifest"]["sha256"],
        "curation_packet_sha256": packet["packet_sha256"],
        "enrollment_sha256": _sha256(enrollment_bytes),
        "reviewed_candidate_ids": expected,
        "reviewed_candidate_count": len(expected),
        "claim_count": len(enrollment["claims"]),
        "outcome_labels_seen": False,
        "evaluator_outputs_seen": False,
    }


class CurationServer(ThreadingHTTPServer):
    packet: dict[str, Any]
    source_paths: dict[str, Path]


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
        server = cast(CurationServer, self.server)
        path = urlparse(self.path).path
        if path == "/":
            self._send(HTTPStatus.OK, HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/app.js":
            self._send(HTTPStatus.OK, JAVASCRIPT.encode("utf-8"), "text/javascript; charset=utf-8")
            return
        if path == "/app.css":
            self._send(HTTPStatus.OK, CSS.encode("utf-8"), "text/css; charset=utf-8")
            return
        if path == "/api/packet":
            public = dict(server.packet)
            public["candidates"] = [dict(row) for row in public["candidates"]]
            self._json(HTTPStatus.OK, public)
            return
        if path.startswith("/api/source/"):
            candidate_id = unquote(path.removeprefix("/api/source/"))
            source = server.source_paths.get(candidate_id)
            if source is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "unknown candidate"})
                return
            self._send(
                HTTPStatus.OK,
                source.read_bytes(),
                mimetypes.guess_type(source.name)[0] or "text/plain; charset=utf-8",
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        server = cast(CurationServer, self.server)
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
        enrollment = request.get("enrollment")
        errors = validate_enrollment(server.packet, server.source_paths, enrollment)
        if errors:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"errors": errors})
            return
        assert isinstance(enrollment, dict)
        try:
            attestation = build_attestation(
                server.packet, enrollment, request.get("reviewed_candidate_ids")
            )
        except ValueError as error:
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"errors": [str(error)]})
            return
        self._json(
            HTTPStatus.OK,
            {
                "enrollment": enrollment,
                "attestation": attestation,
                "enrollment_canonical_sha256": attestation["enrollment_sha256"],
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(packet_path: Path, host: str, port: int) -> None:
    packet = load_packet(packet_path)
    packet_bytes = packet_path.read_bytes()
    packet["packet_sha256"] = _sha256(packet_bytes)
    source_paths = verify_sources(packet_path, packet)
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("curation server may bind only to loopback")
    server = CurationServer((host, port), Handler)
    server.packet = packet
    server.source_paths = source_paths
    print(f"Source-only curator: http://{host}:{server.server_port}")
    print(f"Verified candidates: {len(source_paths)}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local source-only Evidence Trial curator")
    parser.add_argument(
        "--packet", type=Path, default=Path(__file__).with_name("curation-packet.json")
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    serve(args.packet, args.host, args.port)
    return 0


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReproCheck Source-only Curator</title><link rel="stylesheet" href="/app.css"></head>
<body><header><div><p class="eyebrow">Evidence Trial v19</p><h1>Source-only curator</h1></div>
<div class="stats"><strong id="reviewed">0/60 reviewed</strong><strong id="claimCount">0 claims</strong></div></header>
<main><aside><label for="candidateSearch">Candidates</label><input id="candidateSearch" placeholder="Search repository or ID">
<div id="candidateList" class="candidate-list"></div></aside><section class="workspace">
<div id="empty" class="empty">Choose a candidate to inspect its frozen, commit-pinned source.</div>
<div id="editor" hidden tabindex="-1"><div class="source-head"><div><span id="candidateId" class="pill"></span><h2 id="repository"></h2>
<a id="immutableUrl" target="_blank" rel="noreferrer">Open immutable GitHub source</a></div>
<label class="review-toggle"><input id="reviewedToggle" type="checkbox"> Entire file inspected</label></div>
<div class="source-layout"><pre id="source" aria-label="Frozen source lines"></pre><form id="claimForm">
<h3>Enroll exact claim</h3><div class="range"><label>Start line<input id="start" type="number" min="1" required></label>
<label>End line<input id="end" type="number" min="1" required></label></div>
<label>Exact source text<textarea id="claimText" rows="7" readonly required></textarea></label>
<label>Declared metric<input id="metric" placeholder="accuracy or blank"></label>
<label>Normalized value<input id="value" type="number" step="any" placeholder="0.91 or blank"></label>
<label>Evidence available<select id="tier"><option value="report_only">Report only</option>
<option value="supplied_metrics">Supplied metrics</option><option value="raw_recomputation">Raw recomputation</option></select></label>
<button type="submit">Add claim</button><p id="formError" class="error" role="alert"></p></form></div>
<h3>Claims from this candidate</h3><div id="claims"></div></div></section></main>
<footer><div><label>Curator ID<input id="curatorId" placeholder="stable non-identifying ID"></label>
<label class="independence"><input id="independent" type="checkbox"> I am independent from the evaluator and sampled repository authors.</label></div>
<button id="export" class="primary">Validate and export</button><p id="exportError" class="error" role="alert"></p></footer>
<script src="/app.js"></script></body></html>"""


CSS = """:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#16221c;background:#f4f7f3;line-height:1.45}
*{box-sizing:border-box}body{margin:0}header{display:flex;justify-content:space-between;align-items:center;padding:20px 28px;background:#102d21;color:#fff}h1,h2,h3,p{margin-top:0}.eyebrow{margin:0;color:#9dd3b8;text-transform:uppercase;letter-spacing:.12em;font-size:12px}.stats{display:flex;gap:12px}.stats strong,.pill{background:#28523f;padding:7px 10px;border-radius:999px;font-size:13px}main{display:grid;grid-template-columns:320px 1fr;min-height:calc(100vh - 190px)}aside{padding:20px;border-right:1px solid #cfdbd3;background:#fff}input,textarea,select,button{font:inherit}input,textarea,select{width:100%;border:1px solid #aabbb0;border-radius:8px;padding:9px;background:#fff}label{display:block;font-weight:650;margin-bottom:12px}.candidate-list{margin-top:14px;max-height:calc(100vh - 260px);overflow:auto}.candidate{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #e4ebe6;background:#fff;padding:11px 8px;cursor:pointer}.candidate:hover,.candidate.active{background:#e8f3ed}.candidate.done::after{content:'✓';float:right;color:#147646}.candidate small{display:block;color:#607167}.workspace{padding:24px;min-width:0}.empty{padding:60px;text-align:center;color:#607167}.source-head{display:flex;justify-content:space-between;gap:20px}.source-head h2{margin:8px 0 4px}.review-toggle{align-self:center}.source-layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:18px}.source-layout pre{margin:0;background:#112019;color:#e8f5ed;padding:12px;border-radius:10px;overflow:auto;max-height:58vh;font:13px/1.55 ui-monospace,SFMono-Regular,monospace}.source-layout pre .line{display:block;min-width:max-content;width:100%;border:0;border-radius:0;padding:0 12px 0 0;text-align:left;background:transparent;color:inherit;font:inherit}.line:hover,.line:focus-visible{background:#254234;outline:2px solid #9dd3b8;outline-offset:-2px}.line.selected{background:#3b674f}.line-no{display:inline-block;width:52px;color:#8eb49f;text-align:right;margin-right:12px;user-select:none}form{background:#fff;border:1px solid #d5dfd8;border-radius:10px;padding:16px}.range{display:grid;grid-template-columns:1fr 1fr;gap:10px}button{border:1px solid #1d6544;border-radius:8px;padding:9px 13px;background:#fff;color:#164d35;cursor:pointer}button.primary,form button{background:#17633f;color:#fff}.claim{background:#fff;border:1px solid #d5dfd8;border-radius:8px;padding:10px;margin:8px 0}.claim button{float:right;padding:4px 8px}.error{color:#a42525;margin:8px 0 0}footer{position:sticky;bottom:0;display:flex;justify-content:space-between;align-items:end;gap:18px;padding:14px 24px;background:#fff;border-top:1px solid #ccd8d0}footer>div{display:flex;gap:18px;align-items:end}.independence{max-width:480px}a{color:#197049}@media(max-width:900px){main{grid-template-columns:1fr}aside{border-right:0}.candidate-list{max-height:220px}.source-layout{grid-template-columns:1fr}.source-head,footer,footer>div{display:block}footer{position:static}.stats{display:block}.stats strong{display:block;margin:4px}}
"""


JAVASCRIPT = r"""'use strict';
const stateKey='reprocheck-v19-curation-v1';let packet,currentId,sourceLines=[];
let state=JSON.parse(localStorage.getItem(stateKey)||'{"claims":[],"reviewed":[]}');
const $=id=>document.getElementById(id);const save=()=>localStorage.setItem(stateKey,JSON.stringify(state));
const esc=s=>String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
function refreshStats(){ $('reviewed').textContent=`${state.reviewed.length}/${packet.candidate_count} reviewed`;$('claimCount').textContent=`${state.claims.length} claims`; }
function renderList(filter=''){const q=filter.toLowerCase();$('candidateList').innerHTML=packet.candidates.filter(c=>`${c.candidate_id} ${c.repository} ${c.path}`.toLowerCase().includes(q)).map(c=>`<button class="candidate ${c.candidate_id===currentId?'active':''} ${state.reviewed.includes(c.candidate_id)?'done':''}" data-id="${esc(c.candidate_id)}"><b>${esc(c.candidate_id)}</b><small>${esc(c.repository)} · ${esc(c.path)}</small></button>`).join('');document.querySelectorAll('.candidate').forEach(b=>b.onclick=()=>openCandidate(b.dataset.id));}
async function openCandidate(id){currentId=id;const c=packet.candidates.find(x=>x.candidate_id===id);const text=await fetch(`/api/source/${encodeURIComponent(id)}`).then(r=>{if(!r.ok)throw Error('Source request failed');return r.text()});sourceLines=text.split(/\r?\n/);$('empty').hidden=true;$('editor').hidden=false;$('candidateId').textContent=id;$('repository').textContent=c.repository;$('immutableUrl').href=c.immutable_url;$('reviewedToggle').checked=state.reviewed.includes(id);renderSource();renderClaims();renderList($('candidateSearch').value);$('editor').focus({preventScroll:true});}
function renderSource(){ $('source').innerHTML=sourceLines.map((line,i)=>`<button type="button" class="line" data-line="${i+1}" aria-label="Select source line ${i+1}"><span class="line-no">${i+1}</span>${esc(line)||' '}</button>`).join('');document.querySelectorAll('.line').forEach(el=>el.onclick=e=>{const n=Number(el.dataset.line);if(e.shiftKey&&$('start').value){$('end').value=n}else{$('start').value=n;$('end').value=n}syncRange();});syncRange();}
function syncRange(){const a=Number($('start').value),b=Number($('end').value);document.querySelectorAll('.line').forEach(el=>{const selected=Number(el.dataset.line)>=a&&Number(el.dataset.line)<=b;el.classList.toggle('selected',selected);el.setAttribute('aria-pressed',String(selected));});$('claimText').value=a>0&&b>=a&&b<=sourceLines.length?sourceLines.slice(a-1,b).join('\n').trim():'';}
function renderClaims(){const rows=state.claims.filter(c=>c.candidate_id===currentId);$('claims').innerHTML=rows.length?rows.map(c=>`<div class="claim"><button data-remove="${esc(c.local_id)}" aria-label="Remove claim">Remove</button><b>Lines ${c.block.start}–${c.block.end}</b> · ${esc(c.evidence_tier)}<p>${esc(c.claim_text)}</p></div>`).join(''):'<p>No claims enrolled from this file.</p>';document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{state.claims=state.claims.filter(c=>c.local_id!==b.dataset.remove);save();renderClaims();refreshStats();});}
$('claimForm').onsubmit=e=>{e.preventDefault();$('formError').textContent='';const start=Number($('start').value),end=Number($('end').value),text=$('claimText').value.trim();if(!text||start<1||end<start||end>sourceLines.length){$('formError').textContent='Choose a valid exact source-line range.';return}const value=$('value').value.trim();state.claims.push({local_id:crypto.randomUUID(),candidate_id:currentId,block:{start,end},claim_text:text,declared_metric:$('metric').value.trim()||null,declared_value:value===''?null:Number(value),stratum:'natural_unadjudicated',evidence_tier:$('tier').value});save();renderClaims();refreshStats();$('metric').value='';$('value').value='';};
$('start').oninput=syncRange;$('end').oninput=syncRange;$('candidateSearch').oninput=e=>renderList(e.target.value);
$('reviewedToggle').onchange=e=>{state.reviewed=e.target.checked?[...new Set([...state.reviewed,currentId])]:state.reviewed.filter(x=>x!==currentId);save();renderList($('candidateSearch').value);refreshStats();};
function download(name,payload){const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}
$('export').onclick=async()=>{const curator=$('curatorId').value.trim();const claims=[...state.claims].sort((a,b)=>a.candidate_id.localeCompare(b.candidate_id)||a.block.start-b.block.start||a.block.end-b.block.end).map((c,i)=>{const {local_id,...row}=c;return {...row,claim_id:`claim-${String(i+1).padStart(3,'0')}`}});const enrollment={schema_version:'reprocheck.evidence-trial-enrollment.v1',curator_id:curator,independent_from_evaluator:$('independent').checked,candidate_manifest_sha256:packet.candidate_manifest.sha256,claims};$('exportError').textContent='';const r=await fetch('/api/finalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enrollment,reviewed_candidate_ids:state.reviewed})});const result=await r.json();if(!r.ok){$('exportError').textContent=result.errors.join(' · ');return}download('enrollment.json',result.enrollment);download('curation-attestation.json',result.attestation);};
fetch('/api/packet').then(r=>r.json()).then(p=>{packet=p;renderList();refreshStats();}).catch(e=>$('empty').textContent=e.message);
"""


if __name__ == "__main__":
    raise SystemExit(main())
