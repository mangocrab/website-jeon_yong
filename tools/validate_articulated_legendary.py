import io,json,threading,functools
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import numpy as np
from PIL import Image,ImageDraw
from playwright.sync_api import sync_playwright
from export_v1_repairs import HOLE,MARGIN,BAND
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-articulated-visible'
class Q(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Q,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();results=[];review=Image.new('RGB',(1500,1240),'#dfe5ec');draw=ImageDraw.Draw(review)
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1024,'height':1024})
  for i,n in enumerate(range(91,101)):
   page.goto(f'http://127.0.0.1:{server.server_port}/assets/profile-borders-articulated-visible/profile_{n:03}_legendary.svg')
   page.evaluate('async()=>{await Promise.all(document.getAnimations().map(async a=>{await a.ready;a.pause();await a.ready}))}')
   joints=[]
   for phase in [0,.25,.5,.75,1]:
    page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',phase*6000)
    matrix=page.evaluate('()=>{let m=document.querySelector(".fixed-frame").getCTM();return [m.a,m.b,m.c,m.d,m.e,m.f]}');assert matrix==[1,0,0,1,0,0]
    a=np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True))))
    assert not a[:,:,3][HOLE|MARGIN].any(),(n,phase,'transparency')
    assert (a[:,:,3][BAND]==255).all(),(n,phase,'circle')
    if n==97:
     joint=page.evaluate('''()=>[...document.querySelectorAll('.bone-upper')].map(g=>{let m=g.getCTM();return [m.a*128+m.c*500+m.e,m.b*128+m.d*500+m.f]})''');joints.append(joint)
     # The elbow remains on its parent arm, rather than moving as an unattached sticker.
     error=page.evaluate('''()=>Math.max(...[...document.querySelectorAll('.elbow')].map(g=>{let a=g.getCTM(),b=g.parentNode.getCTM();return Math.hypot((a.a-b.a)*165+(a.c-b.c)*385+a.e-b.e,(a.b-b.b)*165+(a.d-b.d)*385+a.f-b.f)}))''');assert error<1e-5
    if phase in (0,.5):
     page.evaluate("document.querySelectorAll('.fx').forEach(e=>e.style.visibility='hidden')")
     pose=Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA');pose.save(OUT/f'profile_{n:03}_{"closed" if phase==0 else "open"}.png')
     x=(i%5)*300;y=(i//5)*620+(0 if phase==0 else 310);pose.thumbnail((290,290));review.paste(pose,(x,y+20),pose);draw.text((x+3,y+3),f'{n} '+('closed' if phase==0 else 'open'),fill='black')
     page.evaluate("document.querySelectorAll('.fx').forEach(e=>e.style.visibility='')")
   visible_pixels=None
   if n!=97:
    page.evaluate("document.querySelectorAll('.fx').forEach(e=>e.style.visibility='hidden');let s=document.documentElement;s.setAttribute('width','128');s.setAttribute('height','128')")
    samples=[]
    for t in [0,1500,3000]:
     page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',t)
     im=Image.open(io.BytesIO(page.screenshot(omit_background=True,clip={'x':0,'y':0,'width':128,'height':128}))).convert('RGBA')
     bg=Image.new('RGBA',(128,128),'#dfe5ec');samples.append(np.array(Image.alpha_composite(bg,im).convert('RGB')).astype(int))
     im.save(OUT/f'profile_{n:03}_128_{t}.png')
    visible_pixels=max(int(np.count_nonzero(np.abs(samples[0]-im).max(axis=2)>=20)) for im in samples[1:])
    print('128px motion, effects OFF:',n,visible_pixels,flush=True)
    assert visible_pixels>=80,(n,'Motion too small at actual profile size',visible_pixels)
    page.evaluate("document.documentElement.setAttribute('width','1024');document.documentElement.setAttribute('height','1024')")
   if joints:assert all(np.allclose(joints[0],j,atol=1e-5) for j in joints)
   page.emulate_media(reduced_motion='reduce');assert page.evaluate('document.getAnimations().length')==0;page.emulate_media(reduced_motion='no-preference')
   results.append(dict(id=n,poses=5,fixed_frame=True,center_transparent=True,inner_diameter_px=716,anatomical_root_checks=(n==97),motion_pixels_128px_effects_off=visible_pixels));print('PASS',n,flush=True)
  b.close()
finally:server.shutdown()
review.save('/tmp/articulated-all-review.jpg');(OUT/'validation.json').write_text(json.dumps(dict(status='passed',results=results),indent=2)+'\n')
print('PASS 10 rigs, 50 poses; inspect visual comparison separately')
