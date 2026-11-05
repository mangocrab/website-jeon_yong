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
        assert len(images)==3+(len(a['articulated_parts'])+1 if a['tier']=='legendary' else 0)
        assert all(e.attrib['href'].startswith('data:image/png;base64,') for e in images)
        art=next(e for e in images if e.attrib.get('id')=='art')
        data=base64.b64decode(art.attrib['href'].split(',',1)[1])
        source=(OUT/a['static_fallback']).resolve()
        assert data==source.read_bytes(), f'Changed source art: {a["id"]}'
        assert hashlib.sha256(data).hexdigest()==a['source_sha256']
        masks={}
        for e in svg.findall('.//s:mask',NS):
            raw=base64.b64decode(e.find('s:image',NS).attrib['href'].split(',',1)[1])
            alpha=np.array(Image.open(io.BytesIO(raw)).getchannel('A'))
            masks[e.attrib['id']]=alpha
            assert np.isin(alpha,[0,255]).all()
        assert np.array_equal(masks['contourMask'],np.where(BAND,255,0))
        assert np.array_equal(masks['movingMask'],np.where((R>=360)&(R<=480),255,0))
        if a['tier']=='legendary':
            part_masks=[m for key,m in masks.items() if key.startswith('partMask')]
            union=np.zeros(R.shape,dtype=int)
            for mask in part_masks:
                assert not mask[R<372].any()
                union+=(mask>0)
            assert union.max()==1,'Source parts overlap'
            assert np.array_equal(masks['baseMask'],np.where(union==0,255,0))
            assert a['whole_frame_motion']=='none'

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
                count=page.evaluate('''async()=>{const a=document.getAnimations();await Promise.all(a.map(async x=>{await x.ready;x.pause();await x.ready}));a.forEach(x=>x.currentTime=0);return a.length}''')
                assert count==1+len(item['articulated_parts'])
                snapshots=[]
                bboxes=[]
                part_states=[]
                for phase in [0,.25,.5,.75,1]:
                    state=page.evaluate('''t=>{document.getAnimations().forEach(a=>a.currentTime=t);const fx=document.querySelector('.fx');const frame=document.querySelector('.stationary');const m=frame.getCTM();const box=fx.getBBox();const f=fx.getCTM();return {opacity:Number(getComputedStyle(fx).opacity),matrix:[m.a,m.b,m.c,m.d,m.e,m.f],fxmatrix:[f.a,f.b,f.c,f.d,f.e,f.f],bbox:[box.x,box.y,box.width,box.height],parts:[...document.querySelectorAll('.part')].map(p=>{const m=p.getCTM();return [m.a,m.b,m.c,m.d,m.e,m.f]})}}''',item['duration_ms']*phase)
                    peak=item['effect_peak_opacity']
                    assert abs(state['opacity']-(0 if phase in (0,1) else peak if phase==.5 else peak/2))<.002
                    m=state['matrix']
                    assert abs(m[0]*512+m[2]*512+m[4]-512)<.002
                    assert abs(m[1]*512+m[3]*512+m[5]-512)<.002
                    assert abs(m[0]*m[3]-m[1]*m[2]-1)<.0001
                    assert state['fxmatrix']==[1,0,0,1,0,0], 'Effect geometry moved'
                    assert m==[1,0,0,1,0,0], 'Base frame moved'
                    part_states.append(state['parts'])
                    bboxes.append(state['bbox'])
                    data=page.screenshot(omit_background=True,animations='allow')
                    pixels=np.array(Image.open(io.BytesIO(data)).convert('RGBA'))
                    alpha=pixels[:,:,3]
                    assert not alpha[HOLE].any(), f'Center alpha: {item["id"]} phase {phase}'
                    assert (alpha[BAND]==255).all(), f'Inner boundary: {item["id"]} phase {phase}'
                    assert not alpha[R>480].any(), f'Margin: {item["id"]} phase {phase}'
                    snapshots.append(pixels)
                    if item['id']==76 or (item['tier']=='legendary' and phase in (0,.5)):
                        (args.artifacts/f'{item["id"]:03}-phase-{phase}.png').write_bytes(data)
                assert all(b==bboxes[0] for b in bboxes)
                assert np.count_nonzero(snapshots[0]!=snapshots[2])>100, 'Invisible effect'
                # CSS-transformed raster layers can be re-rasterized at a new
                # sampling scale by Chromium's compositor. Check exact loop
                # geometry and displayed color continuity, rather than hidden
                # RGB values at transparent/antialiased native pixels.
                assert np.allclose(part_states[0],part_states[4],atol=1e-7,rtol=0),'Loop geometry changed'
                loop_delta=0
                for color in ['#f4f2ec','#172030']:
                    endpoints=[]
                    for rgba in (snapshots[0],snapshots[4]):
                        bg=Image.new('RGBA',(1024,1024),color)
                        endpoints.append(np.array(Image.alpha_composite(bg,Image.fromarray(rgba)).resize((128,128),Image.Resampling.LANCZOS).convert('RGB')).astype(int))
                    loop_delta=max(loop_delta,int(np.max(np.abs(endpoints[0]-endpoints[1]))))
                assert loop_delta<=4,f'Visible loop seam: {item["id"]}, color delta {loop_delta}'
                if item['tier']=='epic':assert np.array_equal(snapshots[0],snapshots[4])
                visibility={}
                if item['tier']=='epic':
                    for name,color in [('light','#f4f2ec'),('dark','#172030')]:
                        small=[]
                        for rgba in (snapshots[0],snapshots[2]):
                            background=Image.new('RGBA',(1024,1024),color)
                            merged=Image.alpha_composite(background,Image.fromarray(rgba))
                            small.append(np.array(merged.resize((128,128),Image.Resampling.LANCZOS).convert('RGB')).astype(int))
                        changed=int(np.count_nonzero(np.max(np.abs(small[0]-small[1]),axis=2)>=16))
                        assert changed>=35,f'Effect too weak at 128px: {item["id"]}, {name}, {changed}'
                        visibility[name]=changed
                else:
                    assert not np.allclose(part_states[0],part_states[2]),'Local ornaments did not articulate'
                    # Verify actual frame artwork moves independently of the blinking effect.
                    page.evaluate("document.querySelector('.fx').style.setProperty('opacity','0','important')")
                    isolated=[]
                    for t in [0,item['duration_ms']/2]:
                        page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',t)
                        isolated.append(np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True,animations='allow')))))
                    assert np.count_nonzero(isolated[0]!=isolated[1])>500,'Only the effect changed'
                    if item['id']==97:
                        assert part_states[0][0][0]<.7 and part_states[2][0][0]>.99,'Wings did not fold and unfold'
                page.emulate_media(reduced_motion='reduce')
                reduced=page.evaluate('''()=>({count:document.getAnimations().length,opacity:getComputedStyle(document.querySelector('.fx')).opacity,transforms:[...document.querySelectorAll('.stationary,.part')].map(e=>getComputedStyle(e).transform)})''')
                assert reduced['count']==0 and float(reduced['opacity'])==0
                assert all(t=='none' for t in reduced['transforms'])
                results.append({'id':item['id'],'tier':item['tier'],'svg_sha256':item['svg_sha256'],
                                'phases_checked':5,'central_alpha_pass':True,'identical_inner_contour_pass':True,
                                'safe_margin_pass':True,'stationary_effect_geometry_pass':True,
                                'loop_closure_pass':True,'reduced_motion_pass':True,
                                'whole_frame_stationary_pass':True,
                                'loop_geometry_pass':True,'loop_128px_max_channel_delta':loop_delta,
                                'articulated_parts_checked':len(item['articulated_parts']),
                                'visible_effect_pixels_at_128px':visibility})
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
