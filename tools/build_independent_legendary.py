"""Assemble independently drawn complete ornaments; no source-image sector masks."""
import sys,json,math,base64,io,shutil
from pathlib import Path
import numpy as np
from scipy.ndimage import label,map_coordinates,find_objects
from PIL import Image
from export_v1_repairs import repair_export,HOLE,MARGIN
from build_v1_repair_animations import build_effects,mask_uri,MASK
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-legendary-independent';WORK=Path('/workspace/legendary-independent-work')
def uri(p):return 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
def isolated(im):
 a=np.array(im.convert('RGBA'));a[a[:,:,3]<30]=0
 im=Image.fromarray(a);b=im.getbbox()
 if not b:raise ValueError('Empty drawn component')
 c=im.crop(b);out=Image.new('RGBA',(c.width+24,c.height+24));out.alpha_composite(c,(12,12));return out
def main():
 OUT.mkdir(exist_ok=True);items=[];cards=[]
 for n in range(91,101):
  record=WORK/f'{n}.json'
  source=OUT/'sources'/f'{n:03}.png'
  if not source.exists():
   if not record.exists():continue
   source.parent.mkdir(exist_ok=True);shutil.copyfile(json.loads(record.read_text())['path'],source)
  sheet=Image.open(source).convert('RGBA');w,h=sheet.size
  pixels=np.array(sheet);groups,count=label(pixels[:,:,3]>80);canvases=[np.zeros_like(pixels) for _ in range(5)]
  for k,region in enumerate(find_objects(groups),1):
   if region is None:continue
   yy,xx=np.nonzero(groups[region]==k);yy+=region[0].start;xx+=region[1].start
   if len(xx)<50:continue
   cx=(xx.min()+xx.max())/2;cy=(yy.min()+yy.max())/2
   cell=min(range(5),key=lambda i:(cx-(i%3+.5)*w/3)**2+(cy-(i//3+.5)*h/2)**2)
   canvases[cell][yy,xx]=pixels[yy,xx]
  cells=[isolated(Image.fromarray(c)) for c in canvases]
  folder=OUT/'layers'/f'{n:03}';folder.mkdir(parents=True,exist_ok=True)
  f=Image.new('RGBA',(1024,1024));c=cells[0];c.thumbnail((990,990));f.alpha_composite(c,((1024-c.width)//2,(1024-c.height)//2));temp=WORK/f'{n}-frame-input.png'
  ang=np.arange(720)*2*np.pi/720;rr=np.arange(100,501);alpha=np.array(f)[:,:,3];samples=map_coordinates(alpha,[512+np.sin(ang)[:,None]*rr,512+np.cos(ang)[:,None]*rr],order=0)>160
  edge=float(np.median(rr[samples.argmax(axis=1)]));factor=350/edge;f=f.transform((1024,1024),Image.Transform.AFFINE,(1/factor,0,512-512/factor,0,1/factor,512-512/factor),Image.Resampling.BICUBIC);f.save(temp)
  f,stats=repair_export(temp,ROOT/f'assets/profile-borders/legendary/profile_{n:03}_legendary.png');fp=folder/'frame.png';f.save(fp)
  defs,fx=build_effects(n);styles=['.fx{animation:fade 4s ease-in-out infinite}@keyframes fade{0%,100%{opacity:0}50%{opacity:.85}}'];body=[f'<image width="1024" height="1024" href="{uri(fp)}"/>'];parts=[];poster=f.copy()
  for j,c in enumerate(cells[1:3] if n==96 else cells[1:]):
   path=folder/f'ornament-{j+1}.png';c.save(path)
   angles={91:[-90,-40,-140,90],92:[-90,0,180,90],93:[-140,-40,180,0],94:[-135,-45,145,-90],95:[-90,0,90,180],96:[-125,-55],97:[-140,-40,135,45],98:[-55,-155,90,20],99:[-90,0,180,90],100:[-90,0,180,90]}
   angle=angles[n][j];cardinal=angle%90==0;size=180 if n==97 else 180 if cardinal else 155;c=c.copy();c.thumbnail((size,size));a=math.radians(angle);radius=500 if n==97 else 430 if cardinal else 485;cx=512+math.cos(a)*radius;cy=512+math.sin(a)*radius
   if n==97:
    c=cells[j+1].copy();c.thumbnail((220,400) if j<2 else (270,300));cx=(40+c.width/2 if j==0 else 984-c.width/2 if j==1 else 120+c.width/2 if j==2 else 904-c.width/2);cy=(90+c.height/2 if j<2 else 640+c.height/2)
   elif n==96:
    c=cells[j+1].copy();c.thumbnail((180,250));cx=(100+c.width/2 if j==0 else 924-c.width/2);cy=40+c.height/2
   elif n==98 and j==0:
    c=cells[j+1].copy();c.thumbnail((210,210));cx=750+c.width/2;cy=50+c.height/2
   elif n==98 and j==1:cx=25+c.width/2
   elif n==98 and j==2:
    c=cells[j+1].copy();c.thumbnail((80,130));cx=512;cy=940
   x=round(cx-c.width/2);y=round(cy-c.height/2);pivot=(round(cx),round(cy+(.3*c.height if j<2 else -.3*c.height)))
   if n==97:pivot=([128,475],[896,475],[155,665],[869,665])[j]
   if n==94 and j<2:pivot=(round(cx),round(cy))
   poster.alpha_composite(c,(x,y));sgn=1 if j%2 else -1
   if n==94 and j<2:frames='0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}'
   elif n==97:frames=f'0%,100%{{transform:rotate(0deg)}}50%{{transform:rotate({[-12,12,10,-10][j]}deg)}}'
   else:frames=f'0%,100%{{transform:translate(0,0) rotate(0deg)}}50%{{transform:translate(0,-5px) rotate({sgn*4}deg)}}'
   styles.append(f'.p{j}{{transform-origin:{pivot[0]}px {pivot[1]}px;animation:a{j} 6s ease-in-out infinite}}@keyframes a{j}{{{frames}}}')
   body.append(f'<image class="p{j}" x="{x}" y="{y}" width="{c.width}" height="{c.height}" href="{uri(path)}"/>');parts.append(dict(file=str(path.relative_to(OUT)),position=[x,y],size=list(c.size),pivot=list(pivot),independently_drawn=True))
  styles.append('@media(prefers-reduced-motion:reduce){image,.fx{animation:none!important}.fx{opacity:0}}')
  svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024"><defs>{defs}<mask id="safe" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{mask_uri(MASK)}"/></mask></defs><style>{"".join(styles)}</style><g mask="url(#safe)">{"".join(body)}{fx}</g></svg>'
  sp=OUT/f'profile_{n:03}_legendary.svg';sp.write_text(svg)
  a=np.array(poster);a[HOLE|MARGIN]=0;Image.fromarray(a).save(OUT/f'profile_{n:03}_legendary.png')
  item=dict(id=n,reference_commit='844e7c2',frame=str(fp.relative_to(OUT)),parts=parts,animation=sp.name,center=[512,512],inner_diameter_px=716,sector_cutting=False);items.append(item)
  links=''.join(f'<a href="{p["file"]}"><img width="100" src="{p["file"]}"></a>' for p in parts)
  cards.append(f'<article><h2>{n}</h2><p>첫 업로드 기준 / 독립 장식 동작</p><img width="300" src="../profile-borders/legendary/profile_{n:03}_legendary.png"><img width="300" src="{sp.name}"><details><summary>독립 장식 원화 4개</summary>{links}</details></article>')
 (OUT/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>전설 독립 장식 레이어</title><style>body{background:#dfe5ec;font-family:system-ui}main{display:flex;flex-wrap:wrap}article{padding:20px}details img{object-fit:contain;height:120px}</style><h1>전설 독립 장식 레이어</h1><main>'+''.join(cards)+'</main>')
 print('Built',len(items))
if __name__=='__main__':main()
