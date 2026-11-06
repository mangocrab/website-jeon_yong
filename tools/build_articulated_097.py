"""Prototype: complete hand-drawn feather groups sharing fixed anatomical roots."""
import json,shutil,base64,math,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from scipy.ndimage import label,find_objects
from export_v1_repairs import repair_export
from build_v1_repair_animations import mask_uri,MASK,build_effects
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-articulated';W=Path('/workspace/legendary-articulated-work')
def uri(p):return 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
def groups(path):
 a=np.array(Image.open(path).convert('RGBA'));lab,num=label(a[:,:,3]>110);layers=[np.zeros_like(a) for _ in range(3)]
 for k,reg in enumerate(find_objects(lab),1):
  if reg is None:continue
  yy,xx=np.nonzero(lab[reg]==k);yy+=reg[0].start;xx+=reg[1].start
  if len(xx)<60:continue
  idx=min(2,int(xx.mean()*3/a.shape[1]));layers[idx][yy,xx]=a[yy,xx]
 result=[]
 for a in layers:
  a[:,:,3][a[:,:,3]>240]=255;im=Image.fromarray(a);im=im.crop(im.getbbox());result.append(im)
 return result
OUT.mkdir(exist_ok=True);sources=OUT/'sources';sources.mkdir(exist_ok=True)
for name in ['frame','upper','lower']:
 p=sources/f'097-{name}.png'
 if not p.exists():shutil.copyfile(json.loads((W/f'{name}.json').read_text())['path'],p)
frame,stats=repair_export(sources/'097-frame.png',ROOT/'assets/profile-borders/legendary/profile_097_legendary.png');frame.save(OUT/'097-frame.png')
body=[];css=[];records=[]
for name,num,x,y,height in [('upper',1,70,130,400)]:
 source=ROOT/f'assets/profile-borders-legendary-independent/layers/097/ornament-{num}.png'
 c=Image.open(source).convert('RGBA');c=c.crop(c.getbbox());c=c.resize((round(c.width*height/c.height),height),Image.Resampling.LANCZOS);p=OUT/f'097-{name}-body.png';c.save(p)
 part=f'<g class="bone-{name}"><image class="wing-body" x="{x}" y="{y}" width="{c.width}" height="{c.height}" href="{uri(p)}"/></g>'
 body.append(part);body.append(f'<g transform="translate(1024 0) scale(-1 1)">{part}</g>')
for lower,name,root,sizes,opened,closed in [(False,'upper',(128,500),[110,125,130,120,80],[-20,-40,-60,-75,-90],[-22,-35,-52,-65,-80]),(True,'lower',(398,900),[145,110,85],[65,75,80],[69,72,74])]:
 gs=groups(sources/f'097-{name}.png')
 if not lower:gs=[gs[1],gs[1],gs[1],gs[1],gs[1]]
 for i,g in enumerate(gs):
  root=([(215,265),(195,320),(165,385),(140,445),(128,500)] if not lower else [(370,890),(315,865),(260,830)])[i]
  if not lower:g=ImageOps.mirror(g)
  ratio=sizes[i]/g.height;g=g.resize((round(g.width*ratio),sizes[i]),Image.Resampling.LANCZOS)
  # Shared full feather roots: upper group bottom-left, lower group top-right.
  local=(g.width*.04,g.height*.96) if not lower else (g.width*.96,g.height*.04)
  x=root[0]-local[0];y=root[1]-local[1];file=OUT/f'097-{name}-feathers-{i}.png';g.save(file)
  ident=f'{name}{i}';css.append(f'.{ident}{{transform-origin:{root[0]}px {root[1]}px;animation:{ident} 6s cubic-bezier(.4,0,.6,1) infinite}}@keyframes {ident}{{0%,100%{{transform:rotate({closed[i]}deg)}}50%{{transform:rotate({opened[i]}deg)}}}}')
  part=f'<image class="feather {ident}" style="--rest:{closed[i]}deg" x="{x}" y="{y}" width="{g.width}" height="{g.height}" href="{uri(file)}"/>'
  if not lower and i<3:part='<g class="elbow">'+part+'</g>'
  part='<g class="bone-'+name+'">'+part+'</g>'
  body.append(part);body.append(f'<g transform="translate(1024 0) scale(-1 1)">{part}</g>')
  records.append(dict(name=ident,file=file.name,root=list(root),position=[x,y],size=list(g.size),closed_angle=closed[i],open_angle=opened[i],mirrored_right=True))
# The complete mounting rail covers the hidden feather roots; never moves.
body.append(f'<image class="fixed-frame" width="1024" height="1024" href="{uri(OUT/"097-frame.png")}"/>')
css.append('.bone-upper{transform-origin:128px 500px;animation:shoulder 6s ease-in-out infinite}.elbow{transform-origin:165px 385px;animation:elbow 6s ease-in-out infinite}.bone-lower{transform-origin:398px 900px;animation:lowerbone 6s ease-in-out infinite}@keyframes shoulder{0%,100%{transform:rotate(0deg)}50%{transform:rotate(-2deg)}}@keyframes elbow{0%,100%{transform:rotate(0deg)}50%{transform:rotate(-3deg)}}@keyframes lowerbone{0%,100%{transform:rotate(0deg)}50%{transform:rotate(2deg)}}')
css.append('@media(prefers-reduced-motion:reduce){.feather{animation:none;transform:rotate(var(--rest,0deg))}.bone-upper,.elbow,.bone-lower{animation:none;transform:none}}')
effect_defs,effect_body=build_effects(97);body.append(effect_body);css.append('.fx{opacity:0;animation:effects 6s ease-in-out infinite}@keyframes effects{0%,100%{opacity:0}50%{opacity:.85}}@media(prefers-reduced-motion:reduce){.fx{animation:none;opacity:0}}')
svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024"><defs>{effect_defs}<mask id="safe" maskUnits="userSpaceOnUse" style="mask-type:alpha"><image width="1024" height="1024" href="{mask_uri(MASK)}"/></mask></defs><style>{"".join(css)}</style><g mask="url(#safe)">{"".join(body)}</g></svg>'
(OUT/'profile_097_legendary.svg').write_text(svg)
(OUT/'097-rig.json').write_text(json.dumps(dict(reference_commit='844e7c2',shared_roots=True,parts=records),indent=2)+'\n')
print('Built 097 articulated prototype')
