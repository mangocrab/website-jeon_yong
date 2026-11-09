import json,io,re,functools,threading,xml.etree.ElementTree as E
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from PIL import Image,ImageDraw
import numpy as np
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-natural';Y,X=np.indices((1280,1280));r=np.hypot(X+.5-640,Y+.5-640);hole=r<358;band=(r>=358)&(r<360);margin=(X<12)|(X>=1268)|(Y<12)|(Y>=1268)
class Q(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
items=json.loads((OUT/'manifest.json').read_text());assert len(items)==100
for a in items[:75]:
 im=Image.open(OUT/a['file']);assert im.size==(1280,1280);assert not np.array(im)[:,:,3][hole].any()
# Each approved independent part and every effect primitive/filter must survive unchanged.
NS='{http://www.w3.org/2000/svg}'
base=json.loads((ROOT/'assets/profile-borders-v1-repaired/manifest.json').read_text())
for a in items[75:]:
 n=a['id'];source=ROOT/'assets/profile-borders-v1-repaired'/base[n-1]['animation'] if n<91 else ROOT/f'assets/profile-borders-articulated-visible/profile_{n:03}_legendary.svg'
 old=E.parse(source).getroot();new=E.parse(OUT/a['file']).getroot()
 def signature(t):
  fx=next(e for e in t.iter() if e.get('class')=='fx')
  return [(e.tag,sorted(e.attrib.items())) for e in fx.iter()]
 assert signature(old)==signature(new),(n,'Effect geometry changed')
 def filters(t):return [(e.tag,sorted(e.attrib.items())) for e in t.iter() if e.tag in (NS+'feGaussianBlur',NS+'feDropShadow')]
 assert filters(old)==filters(new),(n,'Effect filters changed')
 def parts(t):
  parents={c:p for p in t.iter() for c in p};out=[]
  for e in t.iter(NS+'image'):
   p=parents.get(e);masked=False
   while p is not None:
    if p.tag==NS+'mask':masked=True;break
    p=parents.get(p)
   if not masked and e.get('class')!='fixed-frame':out.append(e.get('href'))
  return out
 assert parts(old)==parts(new),(n,'Independent PNG parts changed or disappeared')
print('PASS: approved part PNGs, effect shapes and effect filter sizes preserved',flush=True)
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Q,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();results=[];review=Image.new('RGB',(1600,320*5),'#dfe5ec');d=ImageDraw.Draw(review)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1280,'height':1280})
  for i,a in enumerate(items[75:]):
   n=a['id'];page.goto(f'http://127.0.0.1:{server.server_port}/assets/profile-borders-natural/'+a['file']);page.evaluate('async()=>{await Promise.all(document.getAnimations().map(async a=>{await a.ready;a.pause();await a.ready}))}')
   duration=3840 if n<91 else 6000
   for phase in [0,.5,1]:
    page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',duration*phase)
    ar=np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True))));assert not ar[:,:,3][hole|margin].any(),(n,phase,'photo or margin');assert (ar[:,:,3][band]==255).all(),(n,phase,'contour')
    if phase==0:
     im=Image.fromarray(ar);im.save(OUT/'artwork'/f'{n:03}-poster.png');im.thumbnail((310,290));xx=i%5*320;yy=i//5*320;review.paste(im,(xx,yy+20),im);d.text((xx+5,yy+5),str(n),fill='black')
   page.evaluate("document.documentElement.setAttribute('width','128');document.documentElement.setAttribute('height','128')")
   samples=[]
   for t in [0,duration/2]:
    page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',t)
    if n>=91:page.evaluate("document.querySelectorAll('.fx').forEach(e=>e.style.visibility='hidden')")
    im=Image.open(io.BytesIO(page.screenshot(omit_background=True,clip={'x':0,'y':0,'width':128,'height':128}))).convert('RGBA');bg=Image.new('RGBA',(128,128),'#dfe5ec');samples.append(np.array(Image.alpha_composite(bg,im).convert('RGB')).astype(int));im.save(OUT/'artwork'/f'{n:03}-128-{int(t)}.png')
   change=int(np.count_nonzero(abs(samples[0]-samples[1]).max(axis=2)>=20));print(n,'effect' if n<91 else 'motion without FX',change,flush=True)
   assert change>=40,(n,'not visible at 128',change)
   page.emulate_media(reduced_motion='reduce');assert page.evaluate('document.getAnimations().length')==0;page.emulate_media(reduced_motion='no-preference')
   results.append(dict(id=n,visible_pixels_128px=change,effect_only=n<91,center_transparent=True,inner_diameter_px=716))
  b.close()
finally:server.shutdown()
review.save('/tmp/natural-review.jpg');(OUT/'geometry-and-motion-validation.json').write_text(json.dumps(dict(status='passed',approved_independent_parts_preserved=True,effect_geometry_preserved=True,effect_filter_sizes_preserved=True,effect_artwork_scale=1.0,effect_screen_size_ratio=.8,part_screen_size_ratio=1.12,canvas=1280,center=[640,640],static_pngs=75,animations=25,results=results),indent=2)+'\n')
