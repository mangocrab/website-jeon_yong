"""Restore spacing without redrawing motifs; 1280 canvas keeps the 716px aperture."""
import base64,io,json,re,shutil,hashlib,math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,label
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-natural';SRC=ROOT/'assets/profile-borders-v1-repaired';OLD=ROOT/'assets/profile-borders-articulated-visible';ART=OUT/'artwork';ART.mkdir(parents=True,exist_ok=True)
ET.register_namespace('','http://www.w3.org/2000/svg');NS='{http://www.w3.org/2000/svg}'
Y,X=np.indices((1280,1280));DX=X+.5-640;DY=Y+.5-640;RAD=np.hypot(DX,DY);HOLE=RAD<358;BAND=(RAD>=358)&(RAD<360);MARGIN=(X<12)|(X>=1268)|(Y<12)|(Y>=1268)
A=np.arange(720)*np.pi/360;rr=np.arange(220,451,.5)
def uri(im):
 b=io.BytesIO();im.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
def clean(im):
 a=np.array(im.convert('RGBA'));ids,_=label(a[:,:,3]>110);counts=np.bincount(ids.ravel());keep=counts>=24;keep[0]=False;a[:,:,3][~keep[ids]]=0;a[a[:,:,3]==0]=0;return a
mask=np.full((1280,1280,4),255,dtype=np.uint8);mask[:,:,3]=np.where(HOLE|MARGIN,0,255);MASKURI=uri(Image.fromarray(mask))
def finish(a,reference):
 ref=np.array(Image.open(reference).convert('RGBA'));yy,xx=np.indices((1024,1024));b=(np.hypot(xx+.5-512,yy+.5-512)>=358)&(np.hypot(xx+.5-512,yy+.5-512)<360)
 view=a[128:1152,128:1152];view[b]=ref[b];a[:,:,3][a[:,:,3]>=245]=255;a[HOLE|MARGIN]=0;a[a[:,:,3]==0]=0;return Image.fromarray(a)
def raw_restore(p,reference):
 a=clean(Image.open(p).resize((1024,1024),Image.Resampling.LANCZOS));s=map_coordinates(a[:,:,3],[512+np.sin(A)[:,None]*rr,512+np.cos(A)[:,None]*rr],order=1)>170
 run=s[:,:-3]&s[:,1:-2]&s[:,2:-1]&s[:,3:];valid=run.any(axis=1);edge=rr[run.argmax(axis=1)];px=np.cos(A[valid])*edge[valid];py=np.sin(A[valid])*edge[valid]
 d=np.stack([px*px,2*px*py,py*py,px,py],axis=1);w=np.ones(len(px))
 for _ in range(8):
  c=np.linalg.lstsq(d*w[:,None],w,rcond=None)[0];e=d@c-1;spread=max(.005,float(np.median(abs(e-np.median(e))))*3);w=1/np.sqrt(1+(e/spread)**2)
 q=np.array([[c[0],c[1]],[c[1],c[2]]]);center=-.5*np.linalg.solve(q,c[3:]);q=q/(1+center@q@center);vals,vec=np.linalg.eigh(q);assert vals.min()>0
 forward=358*(vec@np.diag(np.sqrt(vals))@vec.T);inv=np.linalg.inv(forward);coords=inv@np.stack([DX.ravel(),DY.ravel()]);sx=coords[0].reshape(RAD.shape)+512+center[0];sy=coords[1].reshape(RAD.shape)+512+center[1]
 out=np.stack([map_coordinates(a[:,:,k],[sy,sx],order=1,mode='constant') for k in range(4)],axis=2).astype('uint8');return finish(out,reference),dict(method='matte_preexport_global_alignment',original_center_offset=center.tolist(),global_matrix=forward.tolist())
def frame_restore(im,k,reference):
 a=clean(im);yy,xx=np.nonzero(a[:,:,3]>170);r=np.hypot(xx+.5-512,yy+.5-512);co=np.abs(xx+.5-512)/np.maximum(r,1);si=np.abs(yy+.5-512)/np.maximum(r,1);allowed=600/np.maximum(np.maximum(co,si),.001);valid=r>365
 cap=float(np.min((allowed[valid]-358)/(r[valid]-358)));k=max(1.,min(k,cap));src=358+(RAD-358)/k;fac=src/np.maximum(RAD,1);sx=512+DX*fac;sy=512+DY*fac
 out=np.stack([map_coordinates(a[:,:,j],[sy,sx],order=1,mode='constant') for j in range(4)],axis=2).astype('uint8');return finish(out,reference),k
cache=ART/'geometry-input.json'
if not cache.exists():
 audit={r['id']:r['radial_to_tangential_scale'] for r in json.loads(Path('/workspace/v1-correction-work/distortion-audit.json').read_text()) if r['id']>=76};cache.write_text(json.dumps(audit,indent=2)+'\n')
audit=json.loads(cache.read_text());catalog=json.loads((SRC/'manifest.json').read_text());records=[]
for row in catalog:
 n=row['id'];tier=row['tier'];source=SRC/row['file'] if n<76 else SRC/row['animation'] if n<91 else OLD/f'profile_{n:03}_legendary.svg';rel=f'{tier}/profile_{n:03}_{tier}.'+('png' if n<76 else 'svg');target=OUT/rel;target.parent.mkdir(exist_ok=True,parents=True);stats={}
 if n<76:
  im=Image.new('RGBA',(1280,1280));im.alpha_composite(Image.open(source).convert('RGBA'),(128,128));im.save(target)
 else:
  svg=ET.parse(source).getroot();style=svg.find(NS+'style');text=style.text;origins={}
  for m in re.finditer(r'\.([\w-]+)\{transform-origin:([\d.]+)px ([\d.]+)px',text):origins[m[1]]=(float(m[2]),float(m[3]))
  fixed=next(e for e in svg.iter(NS+'image') if e.get('class')=='fixed-frame');decoded=Image.open(io.BytesIO(base64.b64decode(fixed.get('href').split(',',1)[1]))).convert('RGBA')
  ref=ROOT/f'assets/profile-borders/{tier}/profile_{n:03}_{tier}.png'
  if n<91:
   raw=ART/f'{n:03}-matte-input.png'
   if not raw.exists():shutil.copyfile(json.loads(Path(f'/workspace/profile-borders-edited/{n:03}.json').read_text())['path'],raw)
   im,stats=raw_restore(raw,ref);factor=1.
  else:
   im,factor=frame_restore(decoded,1/float(audit[str(n)]),ref);stats=dict(method='inverse_radial_compression_on_fixed_rail',restoration_factor=factor)
  im.save(ART/f'{n:03}-frame.png');fixed.set('href',uri(im));fixed.set('width','1280');fixed.set('height','1280')
  def point(x,y):
   dx=x-512;dy=y-512;r=math.hypot(dx,dy);z=(358+(r-358)*factor)/r if r else 1;return (640+dx*z,640+dy*z)
  parents={c:p for p in svg.iter() for c in p}
  for e in list(svg.iter(NS+'image')):
   if e is fixed:continue
   p=parents.get(e);in_mask=False
   while p is not None:
    if p.tag==NS+'mask':in_mask=True;break
    p=parents.get(p)
   if in_mask:
    e.set('href',MASKURI);e.set('width','1280');e.set('height','1280');continue
   classes=e.get('class','').split();origin=next((origins[c] for c in classes if c in origins),None)
   if origin is None:
    p=parents.get(e)
    while p is not None and origin is None:
     origin=next((origins[c] for c in p.get('class','').split() if c in origins),None);p=parents.get(p)
   if origin is None:origin=(512,512)
   px,py=point(*origin);s=1.4
   if n==94 and ('part-0' in classes or 'part-1' in classes):
    vx=px-640;vy=py-640;vr=math.hypot(vx,vy);px+=25*vx/vr;py+=25*vy/vr
   oldx=float(e.get('x','0'));oldy=float(e.get('y','0'));e.set('x',str(px+(oldx-origin[0])*s));e.set('y',str(py+(oldy-origin[1])*s));e.set('width',str(float(e.get('width'))*s));e.set('height',str(float(e.get('height'))*s))
  for e in svg.iter():
   if e.get('transform')=='translate(1024 0) scale(-1 1)':e.set('transform','translate(1280 0) scale(-1 1)')
   if e.tag==NS+'mask':e.set('maskUnits','userSpaceOnUse');e.set('x','0');e.set('y','0');e.set('width','1280');e.set('height','1280')
   if e.tag==NS+'feGaussianBlur':e.set('stdDeviation','10')
   if e.tag==NS+'feDropShadow':e.set('stdDeviation','3.2');e.set('dy','4');e.set('flood-opacity','.8')

  if n==97:
   parent=parents[fixed];parent.remove(fixed);parent.insert(0,fixed)
  text=re.sub(r'transform-origin:([\d.]+)px ([\d.]+)px',lambda m:'transform-origin:%spx %spx'%point(float(m[1]),float(m[2])),text)
  def translate(m):
   vals=re.findall(r'-?[\d.]+',m[1]);return 'translate('+','.join(f'{float(v)*1.4:.4f}px' for v in vals)+')' if len(vals)==2 else m[0]
  text=re.sub(r'translate\(([^)]*)\)',translate,text);style.text=text+' .fx polygon,.fx circle,.fx path,.fx ellipse{transform-box:fill-box;transform-origin:center;transform:scale(1.4)}'
  if n==94:
   for cls in ['part-0','part-1']:
    ox,oy=origins[cls];px,py=point(ox,oy);vr=math.hypot(px-640,py-640);nx=px+25*(px-640)/vr;ny=py+25*(py-640)/vr
    style.text=style.text.replace(f'.{cls}{{transform-origin:{px}px {py}px',f'.{cls}{{transform-origin:{nx}px {ny}px')
  # Only effect artwork receives halo/shadow and the larger display transform.
  fx=next(e for e in svg.iter() if e.get('class')=='fx');parent=parents[fx];index=list(parent).index(fx);parent.remove(fx);wrapper=ET.Element(NS+'g',{'transform':'translate(640 640) scale(1.25) translate(-512 -512)'});wrapper.append(fx);parent.insert(index,wrapper)
  svg.set('width','1280');svg.set('height','1280');svg.set('viewBox','0 0 1280 1280');ET.ElementTree(svg).write(target,encoding='unicode')
 r={k:row[k] for k in ['id','name','tier']};r.update(file=rel,animated=n>=76,width=1280,height=1280,center=[640,640],inner_diameter_px=716,avatar_fraction=716/1280,geometry=stats,sha256=hashlib.sha256(target.read_bytes()).hexdigest());records.append(r);print('Built',n,stats,flush=True)
(OUT/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
