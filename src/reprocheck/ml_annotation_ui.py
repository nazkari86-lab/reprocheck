from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def render_annotation_ui(packet: dict[str, Any]) -> str:
    if packet.get("schema_version") != "reprocheck.ml-annotation-packet.v1":
        raise ValueError("unsupported annotation packet")
    blocks = packet.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("annotation packet contains no blocks")
    reviewer = str(packet.get("reviewer", "")).strip()
    if not reviewer:
        raise ValueError("annotation packet has no reviewer")
    payload = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(f"ReproCheck — {reviewer}")
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
:root{{--ink:#172033;--muted:#667085;--line:#d0d5dd;--blue:#2563eb;--bg:#f4f7fb}}
*{{box-sizing:border-box}}body{{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:900px;margin:auto;padding:28px 18px 80px}}.card{{min-width:0;background:white;border:1px solid var(--line);border-radius:18px;padding:24px;box-shadow:0 10px 30px #17203312}}
h1{{font-size:26px;margin:0 0 8px;overflow-wrap:anywhere}}.muted{{color:var(--muted)}}progress{{width:100%;height:14px}}pre{{max-width:100%;white-space:pre-wrap;overflow-wrap:anywhere;background:#f8fafc;border:1px solid var(--line);padding:18px;border-radius:12px;max-height:42vh;overflow:auto}}
.decision{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:18px 0}}button,label.choice{{border:1px solid var(--line);background:white;border-radius:10px;padding:12px;cursor:pointer}}label.choice:has(input:checked){{border-color:var(--blue);background:#eff6ff}}input,select,textarea{{width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font:inherit}}label:not(.choice){{display:block;margin-top:18px}}.claim{{display:grid;grid-template-columns:1fr 1fr 130px;gap:8px;margin:10px 0}}#add{{margin-top:4px}}.actions{{display:flex;gap:10px;justify-content:space-between;margin-top:20px;flex-wrap:wrap}}button.primary{{background:var(--blue);color:white;border-color:var(--blue)}}.warning{{color:#b42318}}@media(max-width:650px){{main{{padding:14px 10px 50px}}.card{{padding:18px 14px}}.claim,.decision{{grid-template-columns:1fr}}.actions button{{width:100%}}}}
</style></head><body><main><section class="card">
<h1>Разметка научных результатов</h1><p class="muted">Рецензент: {html.escape(reviewer)}. Работайте самостоятельно и не обсуждайте ответы со вторым рецензентом.</p>
<progress id="progress"></progress><p id="counter" class="muted"></p><pre id="text"></pre>
<p><strong>Есть ли здесь численный результат модели или системы?</strong></p>
<div class="decision"><label class="choice"><input type="radio" name="decision" value="yes"> Да, есть результат</label><label class="choice"><input type="radio" name="decision" value="no"> Нет</label></div>
<div id="claims"></div><button id="add" type="button">+ Добавить ещё один результат</button>
<label>Заметка рецензента<textarea id="notes" rows="2"></textarea></label><p id="error" class="warning"></p>
<div class="actions"><button id="prev">← Назад</button><button id="save">Сохранить ответ</button><button id="next" class="primary">Далее →</button><button id="export">Экспортировать заполненный JSON</button></div>
</section></main><script id="packet" type="application/json">{payload}</script><script>
const packet=JSON.parse(document.getElementById('packet').textContent);const key='reprocheck-review-'+packet.mapping_sha256+'-'+packet.reviewer;
let answers=JSON.parse(localStorage.getItem(key)||'{{}}'),index=0;
const $=id=>document.getElementById(id);function claimRow(value={{}}){{const d=document.createElement('div');d.className='claim';d.innerHTML=`<input class="metric" placeholder="Точное название метрики" value="${{escapeHtml(value.metric_text||'')}}"><input class="value" placeholder="Точное число, например 94%" value="${{escapeHtml(value.value_text||'')}}"><select class="unit"><option value="scalar">Число</option><option value="percent">Процент</option></select>`;d.querySelector('.unit').value=value.unit||'scalar';return d}}
function escapeHtml(s){{return String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}function toggleClaims(){{const yes=document.querySelector('[name=decision]:checked')?.value==='yes';$('claims').style.display=yes?'block':'none';$('add').style.display=yes?'inline-block':'none'}}
function show(){{const b=packet.blocks[index],a=answers[b.blind_id];$('text').textContent=b.raw_text;$('counter').textContent=`Задание ${{index+1}} из ${{packet.blocks.length}} · заполнено ${{Object.keys(answers).length}}`;$('progress').max=packet.blocks.length;$('progress').value=Object.keys(answers).length;$('claims').innerHTML='';$('notes').value=a?.reviewer_notes||'';document.querySelectorAll('[name=decision]').forEach(x=>x.checked=false);if(a){{document.querySelector(`[name=decision][value=${{a.contains_eligible_claim?'yes':'no'}}]`).checked=true;(a.claims||[]).forEach(c=>$('claims').append(claimRow(c)))}}if(!$('claims').children.length)$('claims').append(claimRow());toggleClaims();$('error').textContent='';}}
function save(){{const b=packet.blocks[index],decision=document.querySelector('[name=decision]:checked');if(!decision){{$('error').textContent='Выберите «Да» или «Нет».';return false}}const yes=decision.value==='yes',claims=[...$('claims').children].map(d=>({{metric_text:d.querySelector('.metric').value.trim(),value_text:d.querySelector('.value').value.trim(),unit:d.querySelector('.unit').value}})).filter(c=>c.metric_text||c.value_text);if(yes&&(!claims.length||claims.some(c=>!c.metric_text||!c.value_text))){{$('error').textContent='Для ответа «Да» укажите точную метрику и число.';return false}}answers[b.blind_id]={{contains_eligible_claim:yes,claims:yes?claims:[],reviewer_notes:$('notes').value.trim()}};localStorage.setItem(key,JSON.stringify(answers));$('error').textContent='Сохранено.';return true}}
document.querySelectorAll('[name=decision]').forEach(x=>x.onchange=toggleClaims);$('add').onclick=()=> $('claims').append(claimRow());$('save').onclick=save;$('prev').onclick=()=>{{save();index=Math.max(0,index-1);show()}};$('next').onclick=()=>{{if(save()){{index=Math.min(packet.blocks.length-1,index+1);show()}}}};
$('export').onclick=()=>{{if(!save())return;const missing=packet.blocks.filter(b=>!answers[b.blind_id]);if(missing.length){{$('error').textContent=`Сначала заполните все задания. Осталось: ${{missing.length}}`;return}}const out={{...packet,blocks:packet.blocks.map(b=>({{...b,...answers[b.blind_id]}}))}},blob=new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=packet.reviewer+'-completed.json';a.click();URL.revokeObjectURL(a.href)}};show();
</script></body></html>"""


def write_annotation_ui(packet_path: Path, output_path: Path) -> None:
    if output_path.exists():
        raise ValueError("annotation UI output already exists")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    output_path.write_text(render_annotation_ui(packet), encoding="utf-8")
