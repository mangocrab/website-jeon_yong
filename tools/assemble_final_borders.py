"""Collect exactly one ready-to-use asset per product, without work files."""
import json,shutil,hashlib,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-final';BASE=ROOT/'assets/profile-borders-natural'
OUT.mkdir(parents=True,exist_ok=True);items=[];cards=[]
for a in json.loads((BASE/'manifest.json').read_text()):
 n=a['id'];tier=a['tier'];extension='png' if tier in ('normal','premium','rare') else 'svg'
 source=BASE/a['file']
 rel=f'{tier}/profile_{n:03}_{tier}.{extension}';target=OUT/rel;target.parent.mkdir(exist_ok=True);shutil.copyfile(source,target)
 items.append(dict(id=n,name=a['name'],tier=tier,file=rel,animated=extension=='svg',width=1280,height=1280,center=[640,640],inner_diameter_px=716,avatar_fraction=716/1280,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
 cards.append(f'<article data-tier="{tier}"><img src="{rel}" alt="{html.escape(a["name"])}" loading="lazy"><h2>{n:03} · {html.escape(a["name"])}</h2><a href="{rel}" download>다운로드</a></article>')
(OUT/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
(OUT/'index.html').write_text('''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>프로필 테두리 최종 사용 파일</title><style>body{font:15px system-ui;background:#edf1f5;color:#20334b;padding:24px}nav{display:flex;gap:8px;flex-wrap:wrap}button{padding:10px;background:white;border:1px solid #bcc8d3;border-radius:8px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;margin-top:24px}article{background:white;padding:20px;border-radius:12px;text-align:center}article img{width:128px;height:128px;background:#dfe5ec;border-radius:8px}h2{font-size:14px}[hidden]{display:none!important}</style><h1>프로필 테두리 최종 사용 파일 100종</h1><p>일반·고급·희귀는 PNG, 영웅·전설은 이펙트와 동작이 포함된 SVG입니다. 각 항목의 파일 하나만 사이트에 사용하면 됩니다. 공통 캔버스는 1280px, 안쪽 원은 716px입니다.</p><nav>'''+''.join(f'<button data-tier="{k}">{v}</button>' for k,v in [('all','전체'),('normal','일반'),('premium','고급'),('rare','희귀'),('epic','영웅'),('legendary','전설')])+'''</nav><main>'''+''.join(cards)+'''</main><script>document.querySelectorAll('button').forEach(b=>b.onclick=()=>document.querySelectorAll('article').forEach(a=>a.hidden=b.dataset.tier!=='all'&&a.dataset.tier!==b.dataset.tier))</script></html>''')
(OUT/'README.md').write_text('''# 최종 사용 파일 — 이 폴더만 사용하세요

총 100종입니다. 각 상품에 파일 하나만 사용하면 됩니다.

| 등급 | 폴더 | 수량 | 사용 파일 |
|---|---|---:|---|
| 일반 | [normal](normal) | 30 | PNG |
| 고급 | [premium](premium) | 25 | PNG |
| 희귀 | [rare](rare) | 20 | PNG |
| 영웅 | [epic](epic) | 15 | 이펙트 SVG |
| 전설 | [legendary](legendary) | 10 | 동작·이펙트 SVG |

[전체 미리보기·개별 다운로드](index.html)

SVG에는 필요한 그림이 모두 들어 있습니다. 다른 폴더의 레이어나 원화 파일을 함께 올릴 필요가 없습니다. 작업용 파일과 이전 수정본은 이 폴더에 포함하지 않았습니다.

```html
<img src="/assets/profile-borders-final/legendary/profile_094_legendary.svg"
     width="128" height="128" alt="프로필 장식">
```

94번은 회전 기어만 테두리 뒤에 배치했습니다. 왕관과 리본 등 다른 장식은 앞에 유지합니다. 97번은 승인된 관절 구조를 유지하고 크기·배치만 보정했습니다.

모두 1280×1280px, 중심 (640,640), 안쪽 원 지름 716px이며 중앙은 투명합니다. 장식을 좁은 띠에 누르지 않도록 투명 캔버스를 넓혔습니다. 프로필 사진은 테두리 컨테이너의 가로·세로 **55.9375%**로 중앙에 배치하면 안쪽 원에 맞습니다.

`manifest.json`에서 ID·등급·이름·파일 경로를 확인할 수 있습니다. ZIP은 만들지 않았습니다.
''')
assert len(items)==100
print('Collected 75 PNGs and 25 self-contained SVGs')
