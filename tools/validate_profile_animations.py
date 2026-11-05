"""Validate all SVGs in a real browser, including the alpha at animation phases.

Requires Playwright and Chromium. Run with --browser /path/to/chromium if needed.
Screenshots for visual review are saved outside the checkout by default.
"""
import argparse
import base64
import functools
import hashlib
import io
import json
import threading
import xml.etree.ElementTree as ET
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/profile-borders-animated'
NS={'s':'http://www.w3.org/2000/svg'}
Y,X=np.indices((1024,1024))
R=np.hypot(X+.5-512,Y+.5-512)
HOLE=R<358
BAND=(R>=358)&(R<360)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--browser')
    parser.add_argument('--artifacts',type=Path,default=Path('/tmp/profile-animation-review'))
    args=parser.parse_args();args.artifacts.mkdir(parents=True,exist_ok=True)
    items=json.loads((OUT/'manifest.json').read_text())
    assert len(items)==25 and {a['id'] for a in items}==set(range(76,101))
    assert Counter(a['tier'] for a in items)=={'epic':15,'legendary':10}
    assert len(list(OUT.glob('*/*.svg')))==25
    assert not list(OUT.rglob('*.zip'))
    for a in items:
        path=OUT/a['svg'];svg=ET.parse(path).getroot()
        assert svg.attrib['viewBox']=='0 0 1024 1024'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==a['svg_sha256']
        assert not svg.findall('.//s:script',NS)
        images=svg.findall('.//s:image',NS)
        assert len(images)==3
        assert all(e.attrib['href'].startswith('data:image/png;base64,') for e in images)
        art=next(e for e in images if e.attrib.get('id')=='art')
        data=base64.b64decode(art.attrib['href'].split(',',1)[1])
        source=(OUT/a['static_fallback']).resolve()
        assert data==source.read_bytes(), f'Changed source art: {a["id"]}'
        assert hashlib.sha256(data).hexdigest()==a['source_sha256']
        for e in svg.findall('.//s:mask',NS):
            raw=base64.b64decode(e.find('s:image',NS).attrib['href'].split(',',1)[1])
            alpha=np.array(Image.open(io.BytesIO(raw)).getchannel('A'))
            expected=BAND if e.attrib['id']=='contourMask' else (R>=360)&(R<=480)
            assert np.array_equal(alpha,np.where(expected,255,0))

    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    results=[]
    try:
        with sync_playwright() as p:
            launch={'headless':True,'args':['--no-sandbox']}
            if args.browser:launch['executable_path']=args.browser
            browser=p.chromium.launch(**launch)
            page=browser.new_page(viewport={'width':1024,'height':1024},device_scale_factor=1,
                                  reduced_motion='no-preference')
            for item in items:
                page.emulate_media(reduced_motion='no-preference')
                response=page.goto(base+'/assets/profile-borders-animated/'+item['svg'],wait_until='networkidle')
                assert response.status==200
                count=page.evaluate('''async()=>{const a=document.getAnimations();await Promise.all(a.map(x=>x.ready));a.forEach(x=>x.pause());return a.length}''')
                assert count==(2 if item['tier']=='legendary' else 1)
                snapshots=[]
                bboxes=[]
                for phase in [0,.25,.5,.75,1]:
                    state=page.evaluate('''t=>{document.getAnimations().forEach(a=>a.currentTime=t);const fx=document.querySelector('.fx');const frame=document.querySelector('.motion,.stationary');const m=frame.getCTM();const box=fx.getBBox();const f=fx.getCTM();return {opacity:Number(getComputedStyle(fx).opacity),matrix:[m.a,m.b,m.c,m.d,m.e,m.f],fxmatrix:[f.a,f.b,f.c,f.d,f.e,f.f],bbox:[box.x,box.y,box.width,box.height]}}''',item['duration_ms']*phase)
                    assert abs(state['opacity']-(0 if phase in (0,1) else .55 if phase==.5 else .275))<.002
                    m=state['matrix']
                    assert abs(m[0]*512+m[2]*512+m[4]-512)<.002
                    assert abs(m[1]*512+m[3]*512+m[5]-512)<.002
                    assert abs(m[0]*m[3]-m[1]*m[2]-1)<.0001
                    assert state['fxmatrix']==[1,0,0,1,0,0], 'Effect geometry moved'
                    if item['tier']=='epic':assert m==[1,0,0,1,0,0], 'Epic frame moved'
                    bboxes.append(state['bbox'])
                    data=page.screenshot(omit_background=True,animations='allow')
                    pixels=np.array(Image.open(io.BytesIO(data)).convert('RGBA'))
                    alpha=pixels[:,:,3]
                    assert not alpha[HOLE].any(), f'Center alpha: {item["id"]} phase {phase}'
                    assert (alpha[BAND]==255).all(), f'Inner boundary: {item["id"]} phase {phase}'
                    assert not alpha[R>480].any(), f'Margin: {item["id"]} phase {phase}'
                    snapshots.append(pixels)
                    if item['id'] in (76,91):
                        (args.artifacts/f'{item["id"]:03}-phase-{phase}.png').write_bytes(data)
                assert all(b==bboxes[0] for b in bboxes)
                assert np.count_nonzero(snapshots[0]!=snapshots[2])>100, 'Invisible effect'
                assert np.array_equal(snapshots[0],snapshots[4]), 'Loop does not close'
                if item['tier']=='legendary':
                    assert np.count_nonzero(snapshots[1]!=snapshots[3])>100, 'Frame did not move'
                page.emulate_media(reduced_motion='reduce')
                reduced=page.evaluate('''()=>({count:document.getAnimations().length,opacity:getComputedStyle(document.querySelector('.fx')).opacity,transform:getComputedStyle(document.querySelector('.motion,.stationary')).transform})''')
                assert reduced['count']==0 and float(reduced['opacity'])==0
                assert reduced['transform']=='none'
                results.append({'id':item['id'],'tier':item['tier'],'svg_sha256':item['svg_sha256'],
                                'phases_checked':5,'central_alpha_pass':True,'identical_inner_contour_pass':True,
                                'safe_margin_pass':True,'stationary_effect_geometry_pass':True,
                                'loop_closure_pass':True,'reduced_motion_pass':True})
                print(f'PASS {item["id"]:03}: five phases, exact aperture, motion and reduced motion',flush=True)
            version=browser.version
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
    report={'status':'passed','browser':'Chromium '+version,'assets_checked':len(results),
            'rendered_phases_checked':len(results)*5,'center':[512,512],'inner_diameter_px':716,
            'original_pngs_modified':False,'results':results}
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS: 25 animations / 125 rendered phases; identical openings, transparent centers, seamless loops.')


if __name__=='__main__':
    main()
