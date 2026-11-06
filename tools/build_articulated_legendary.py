"""Authored placements and motif-specific joint motion; no generic sprite ring layout."""
import json,math,shutil,base64
from pathlib import Path
from PIL import Image
from export_v1_repairs import repair_export
from build_v1_repair_animations import build_effects,mask_uri,MASK
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-articulated';OLD=ROOT/'assets/profile-borders-legendary-independent';WORK=Path('/workspace/legendary-articulated-work')
# Center x/y and fitted width/height, authored against the 844e7c2 composition.
LAYOUT={91:[(512,100,185,100),(795,240,95,115),(229,240,95,115),(512,914,175,95)],92:[(512,105,170,85),(908,512,85,130),(116,512,85,130),(512,914,170,90)],93:[(205,275,110,160),(819,275,110,160),(121,512,70,100),(903,512,70,100)],94:[(268,215,95,110),(756,215,85,100),(145,620,80,140),(512,110,180,100)],95:[(512,110,175,95),(908,512,80,125),(512,913,170,90),(159,330,90,140)],96:[(305,190,150,200),(719,190,150,200)],98:[(768,185,210,175),(192,278,110,95),(512,920,65,105),(897,611,90,120)],99:[(512,105,175,100),(908,512,85,135),(116,512,85,135),(512,914,175,90)],100:[(512,110,180,95),(908,512,90,135),(116,512,90,135),(512,913,170,95)]}
def uri(p):return 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
items=[]
for n,layout in LAYOUT.items():
 source=OUT/'sources'/f'{n:03}-frame.png';source.parent.mkdir(exist_ok=True,parents=True)
 if not source.exists():shutil.copyfile(json.loads((WORK/f'frame-{n}.json').read_text())['path'],source)
 frame,stats=repair_export(source,ROOT/f'assets/profile-borders/legendary/profile_{n:03}_legendary.png');folder=OUT/'layers'/f'{n:03}';folder.mkdir(exist_ok=True,parents=True);fp=folder/'frame.png';frame.save(fp)
 defs,fx=build_effects(n);css=['.fx{opacity:0;animation:effects 6s ease-in-out infinite}@keyframes effects{0%,100%{opacity:0}50%{opacity:.85}}'];parts=[];records=[]
 for j,(cx,cy,w,h) in enumerate(layout):
  src=OLD/'layers'/f'{n:03}'/f'ornament-{j+1}.png';p=folder/src.name;shutil.copyfile(src,p);im=Image.open(p);im.thumbnail((w,h));w,h=im.size;x=cx-w/2;y=cy-h/2
  # Mechanical axles, branch roots and hanging attachments each have their own joint.
  pivot=(cx,cy)
  if n==94 and j<2:pivot=(cx,y+h*.4)
  elif n==96:pivot=(x+w*.45,y+h*.94)
  elif n==98:pivot=(x+w*.25,y+h*.85) if j==0 else (cx,y+5) if j==2 else (cx,cy)
  elif n in (93,100):pivot=(cx,cy+(.35*h if cy<512 else -.35*h))
  sign=-1 if cx<512 else 1
  if n==94 and j<2:keys='0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}';timing='linear'
  else:
   timing='cubic-bezier(.4,0,.6,1)'
   if n==91:pose='translate(0,-3px) scale(1.025)' if j in (1,2) else 'scale(1.025)'
   elif n==92:pose='scale(1.045)'
   elif n==93:pose=f'rotate({sign*3}deg) scale(1.015)'
   elif n==94:pose='translate(0,-3px)'
   elif n==95:
    a=math.atan2(cy-512,cx-512);pose=f'translate({math.cos(a)*3:.3f}px,{math.sin(a)*3:.3f}px)'
   elif n==96:pose=f'rotate({sign*2.5}deg)'
   elif n==98:pose='rotate(-2deg)' if j==0 else 'rotate(3deg)' if j==2 else 'translate(0,-4px)'
   elif n==99:
    a=math.atan2(cy-512,cx-512);pose=f'translate({math.cos(a)*2:.3f}px,{math.sin(a)*2:.3f}px) scale(1.015)'
   else:pose=f'rotate({sign*3}deg)'
   keys=f'0%,100%{{transform:translate(0,0) rotate(0deg) scale(1)}}50%{{transform:{pose}}}'
  css.append(f'.part-{j}{{transform-origin:{pivot[0]}px {pivot[1]}px;animation:part{j} 6s {timing} infinite}}@keyframes part{j}{{{keys}}}')
  parts.append(f'<image class="part part-{j}" x="{x}" y="{y}" width="{w}" height="{h}" href="{uri(p)}"/>');records.append(dict(file=str(p.relative_to(OUT)),position=[x,y],size=[w,h],pivot=list(pivot),motion=keys))
 css.append('@media(prefers-reduced-motion:reduce){.part,.fx{animation:none;transform:none}.fx{opacity:0}}')
 # Only fixed complete rail overpaint occludes the physically hidden attachment ends.
 body=''.join(parts)+f'<image class="fixed-frame" width="1024" height="1024" href="{uri(fp)}"/>'+fx
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><defs>{defs}<mask id="safe" maskUnits="userSpaceOnUse" style="mask-type:alpha"><image width="1024" height="1024" href="{mask_uri(MASK)}"/></mask></defs><style>{"".join(css)}</style><g mask="url(#safe)">{body}</g></svg>'
 (OUT/f'profile_{n:03}_legendary.svg').write_text(svg);items.append(dict(id=n,reference_commit='844e7c2',frame=str(fp.relative_to(OUT)),parts=records,geometry=stats))
rig=json.loads((OUT/'097-rig.json').read_text());items.append(dict(id=97,reference_commit='844e7c2',frame='097-frame.png',parts=rig['parts'],bones=dict(shoulder=[128,500],elbow=[165,385],lower=[398,900])))
items.sort(key=lambda x:x['id'])
(OUT/'manifest.json').write_text(json.dumps(items,indent=2)+'\n');print('Built',len(items),'authored legendary rigs; 097 has separate anatomical feather rig')
