"""Build a self-contained catalog page referencing the individual PNG files."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'assets/profile-borders'
items = json.loads((ROOT/'manifest.json').read_text())
cards = []
for a in items:
    cards.append(f'<article data-tier="{a["tier"]}"><div class="sample"><div class="avatar"></div><img src="{a["file"]}" alt="{a["name"]}" loading="lazy"></div><p>{a["id"]:03} · {a["name"]}</p><small>{a["tier"]}</small></article>')
page = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>프로필 테두리 컬렉션</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f4f2ec;color:#222c36;font:15px system-ui;padding:32px}header{max-width:900px;margin-bottom:28px}h1{font-size:30px;margin:0 0 12px}p{line-height:1.6}nav{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}button{border:1px solid #b9c2c9;border-radius:20px;background:white;color:#293442;padding:8px 14px;cursor:pointer}button[aria-pressed=true]{background:#293442;color:white}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:18px}article{background:white;border:1px solid #dce0e2;border-radius:14px;padding:12px}.sample{aspect-ratio:1;position:relative;background:#e6e9ec;border-radius:10px}.avatar{position:absolute;width:69.921875%;height:69.921875%;border-radius:50%;left:15.0390625%;top:15.0390625%;background:#a5b6c6}.sample img{position:absolute;width:100%;height:100%;object-fit:contain}article p{margin:10px 0 2px}small{color:#607080}body.dark .sample{background:#18202c}body.dark .avatar{background:#35465b}body.no-avatar .avatar{display:none}[hidden]{display:none!important}.count{font-variant-numeric:tabular-nums}</style>
<header><h1>프로필 테두리 컬렉션</h1><p>평면 일러스트 100종 · 1024×1024 RGBA PNG<br>안쪽 원 지름 716px · 중심 (512, 512) · 중앙 완전 투명</p><p>중앙의 회색 원은 적용 확인용입니다. PNG 파일에는 포함되지 않습니다.</p>
<nav aria-label="등급 필터"><button data-filter="all" aria-pressed="true">전체</button><button data-filter="normal">일반 · 30</button><button data-filter="premium">고급 · 25</button><button data-filter="rare">희귀 · 20</button><button data-filter="epic">영웅 · 15</button><button data-filter="legendary">전설 · 10</button></nav>
<button id="background">밝은 / 어두운 배경</button> <button id="avatar">프로필 원 표시 / 숨기기</button> <span class="count" id="count"></span></header><main class="grid">'''+''.join(cards)+'''</main><script>const cards=[...document.querySelectorAll('article')];document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));cards.forEach(x=>x.hidden=b.dataset.filter!=='all'&&x.dataset.tier!==b.dataset.filter);document.querySelector('#count').textContent=cards.filter(x=>!x.hidden).length+'종';}));document.querySelector('#background').onclick=()=>document.body.classList.toggle('dark');document.querySelector('#avatar').onclick=()=>document.body.classList.toggle('no-avatar');document.querySelector('#count').textContent=cards.length+'종';</script></html>'''
(ROOT/'index.html').write_text(page)
print('Preview items:', len(items))
