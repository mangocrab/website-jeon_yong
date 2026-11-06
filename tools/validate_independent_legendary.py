import io,json,threading,functools
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from export_v1_repairs import HOLE,MARGIN,BAND
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-legendary-independent'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
items=json.loads((OUT/'manifest.json').read_text());assert len(items)==10
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();results=[]
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1024,'height':1024})
  for item in items:
   page.goto(f'http://127.0.0.1:{server.server_port}/assets/profile-borders-legendary-independent/'+item['animation'])
   page.evaluate('async()=>{await Promise.all(document.getAnimations().map(async a=>{await a.ready;a.pause();await a.ready}));}')
   clipped=[]
   for phase in [0,.25,.5,.75,1]:
    page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',phase*6000)
    a=np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True))))
    assert not a[:,:,3][HOLE|MARGIN].any(),(item['id'],phase,'aperture')
    if phase==.5:Image.fromarray(a).save(f'/tmp/independent-{item["id"]}-moving.png')
    page.evaluate("document.querySelector('svg>g').removeAttribute('mask');document.querySelector('svg>g>image').style.visibility='hidden';document.querySelector('.fx').style.display='none'")
    parts=np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True))))
    clipped.append(int(np.count_nonzero(parts[:,:,3][HOLE|MARGIN])))
    page.evaluate("document.querySelector('svg>g').setAttribute('mask','url(#safe)');document.querySelector('svg>g>image').style.visibility='';document.querySelector('.fx').style.display=''")
   print(item['id'],'unmasked ornament pixels crossing aperture/margin:',clipped,flush=True)
   results.append(dict(id=item['id'],phases=5,ornament_clip_pixels=clipped))
  b.close()
finally:server.shutdown()
(OUT/'validation.json').write_text(json.dumps(dict(status='passed' if all(not any(r['ornament_clip_pixels']) for r in results) else 'failed',animations=10,poses=50,results=results),indent=2)+'\n')
assert all(not any(r['ornament_clip_pixels']) for r in results),'Independent ornaments must remain complete through motion'
print('PASS: 10 complete layered animations; no ornament clipped in 50 poses')
