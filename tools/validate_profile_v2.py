"""Check real V2 PNGs, independent layers, proportions, effects and browser motion."""
import argparse
import base64
import functools
import hashlib
import io
import json
import threading
import xml.etree.ElementTree as ET
from collections import Counter
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/profile-borders-v2'
NS={'s':'http://www.w3.org/2000/svg'}
Y,X=np.indices((1024,1024));R=np.hypot(X+.5-512,Y+.5-512)
HOLE=R<358;BAND=(R>=358)&(R<360)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check_alpha(pixels,label):
    assert pixels.shape==(1024,1024,4),label
    a=pixels[:,:,3]
    assert not a[HOLE].any(),f'Nontransparent center: {label}'
    assert (a[BAND]==255).all(),f'Different actual inner edge: {label}'
    assert not a[R>496].any(),f'Unsafe canvas edge: {label}'


def image_data(element):return base64.b64decode(element.attrib['href'].split(',',1)[1])


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def copyfile(self,source,outputfile):
        try:super().copyfile(source,outputfile)
        except (BrokenPipeError,ConnectionResetError):
            # Closing the gallery cancels in-flight lazy image downloads.
            pass


def main():
    p=argparse.ArgumentParser();p.add_argument('--browser',default='/usr/bin/chromium')
    p.add_argument('--artifacts',type=Path,default=Path('/tmp/profile-v2-review'));args=p.parse_args()
    args.artifacts.mkdir(parents=True,exist_ok=True)
    items=json.loads((OUT/'manifest.json').read_text())
    assert len(items)==100 and {a['id'] for a in items}==set(range(1,101))
    assert Counter(a['tier'] for a in items)==dict(normal=30,premium=25,rare=20,epic=15,legendary=10)
    assert len(list(OUT.glob('*/*.png')))==100
    assert len(list((OUT/'animations').glob('*/*.svg')))==25
    assert not list(OUT.rglob('*.zip'))
    independent=0;placements=0
    for a in items:
        source=OUT/a['file'];im=Image.open(source)
        assert im.mode=='RGBA';check_alpha(np.array(im),source)
        assert sha(source)==a['sha256']
        old=ROOT/'assets/profile-borders'/a['file']
        assert sha(old)!=sha(source),f'Old file was reused: {source}'
        layers=json.loads((OUT/a['layer_manifest']).read_text())
        expected=1 if a['tier']=='normal' else 9 if a['tier']=='legendary' else 3
        assert len(layers['ornaments'])==expected
        frame=OUT/layers['frame'];f=np.array(Image.open(frame))
        check_alpha(f,frame);assert not f[:,:,3][R>396].any(),'Frame layer includes old ornaments'
        assert sha(frame)==layers['frame_sha256']
        for o in layers['ornaments']:
            file=OUT/o['file'];layer=Image.open(file)
            assert layer.mode=='RGBA' and sha(file)==o['sha256']
            alpha=np.array(layer.getchannel('A'))
            assert alpha.any() and not alpha[0].any() and not alpha[-1].any() and not alpha[:,0].any() and not alpha[:,-1].any()
            assert o['independently_drawn'] and o['source_margin_px']==8
            assert o['cell_edge_opaque_pixels']<=20
            independent+=1
        for placement in a['placements']:
            w,h=placement['source_size'];sx=placement['width']/w;sy=placement['height']/h
            assert abs(sx-sy)<1e-10,'An ornament was squashed'
            assert abs(sx-placement['uniform_scale'])<1e-10
            placements+=1
        if 'animation' in a:
            path=OUT/a['animation'];svg=ET.parse(path).getroot()
            assert sha(path)==a['animation_sha256']
            assert len(svg.findall('.//s:mask',NS))==1,'Old per-piece cutout masks were reused'
            frame_element=svg.find('.//s:image[@id="frame"]',NS)
            assert image_data(frame_element)==frame.read_bytes()
            separate=[e for e in svg.findall('.//s:image',NS) if 'data-layer' in e.attrib]
            assert len(separate)==len(a['placements'])
            for element in separate:
                index=int(element.attrib['data-layer']);layer=OUT/layers['ornaments'][index]['file']
                assert image_data(element)==layer.read_bytes()
            assert svg.find('.//s:feGaussianBlur',NS) is not None
            assert svg.find('.//s:feDropShadow',NS) is not None
            assert svg.findall('.//s:linearGradient',NS)
    assert independent==300
    print(f'PASS: 100 new PNGs, {independent} independently drawn ornament PNGs, {placements} proportion-preserving placements.',flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}';results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1024,'height':1024},device_scale_factor=1,reduced_motion='no-preference')
            for item in [a for a in items if 'animation' in a]:
                page.emulate_media(reduced_motion='no-preference')
                page.goto(base+'/assets/profile-borders-v2/'+item['animation'],wait_until='networkidle')
                count=page.evaluate('''async()=>{const a=document.getAnimations();await Promise.all(a.map(async x=>{await x.ready;x.pause();await x.ready}));a.forEach(x=>x.currentTime=0);return a.length}''')
                assert count==1+(9 if item['tier']=='legendary' else 0)
                frames=[];joint_states=[]
                for phase in [0,.25,.5,.75,1]:
                    state=page.evaluate('''t=>{document.getAnimations().forEach(a=>a.currentTime=t);function m(e){const v=e.getCTM();return [v.a,v.b,v.c,v.d,v.e,v.f]}return {base:m(document.querySelector('.frame-fixed')),fx:m(document.querySelector('.fx')),opacity:Number(getComputedStyle(document.querySelector('.fx')).opacity),parts:[...document.querySelectorAll('.part')].map(m)}}''',phase*item['duration_ms'])
                    assert state['base']==[1,0,0,1,0,0] and state['fx']==[1,0,0,1,0,0]
                    expected=(.85 if item['tier']=='legendary' else .95)*(.5-.5*np.cos(2*np.pi*phase))
                    assert abs(state['opacity']-expected)<.002
                    for m in state['parts']:
                        linear=np.array([[m[0],m[2]],[m[1],m[3]]]);singular=np.linalg.svd(linear,compute_uv=False)
                        assert abs(singular[0]-singular[1])<1e-6,'Animated layer was squashed'
                    joint_states.append(state['parts'])
                    raw=page.screenshot(omit_background=True,animations='allow');array=np.array(Image.open(io.BytesIO(raw)).convert('RGBA'))
                    check_alpha(array,f'{item["id"]} phase {phase}');frames.append(array)
                    if item['id'] in (76,94,97) and phase in (0,.5):
                        (args.artifacts/f'{item["id"]:03}-phase-{phase}.png').write_bytes(raw)
                assert np.allclose(joint_states[0],joint_states[4],atol=1e-7,rtol=0),'Loop geometry changed'
                visibility={};loop_max=0
                for name,color in [('light','#f4f2ec'),('dark','#172030')]:
                    images=[]
                    for array in [frames[0],frames[2],frames[4]]:
                        bg=Image.new('RGBA',(1024,1024),color)
                        images.append(np.array(Image.alpha_composite(bg,Image.fromarray(array)).resize((128,128),Image.Resampling.LANCZOS).convert('RGB')).astype(int))
                    loop_max=max(loop_max,int(np.max(np.abs(images[0]-images[2]))))
                    visibility[name]=int(np.count_nonzero(np.max(np.abs(images[0]-images[1]),axis=2)>=16))
                    assert visibility[name]>=35,'Effect is too weak at profile size'
                assert loop_max<=4,f'Visible loop seam: {item["id"]}: {loop_max}'
                if item['tier']=='legendary':
                    page.evaluate("document.querySelector('.fx').style.setProperty('opacity','0','important')")
                    isolated=[]
                    for t in [0,item['duration_ms']/2]:
                        page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',t)
                        isolated.append(np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True,animations='allow')))))
                    assert np.count_nonzero(isolated[0]!=isolated[1])>500,'No independently drawn ornament moved'
                elif item['id']==76:
                    page.evaluate('document.getAnimations().forEach(a=>a.currentTime=1920)')
                    page.evaluate("document.querySelector('.fx>use').style.display='none'")
                    without=np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True,animations='allow'))))
                    assert np.count_nonzero(without!=frames[2])>100,'Halo filter is not rendered'
                page.emulate_media(reduced_motion='reduce')
                reduced=page.evaluate('''()=>({animations:document.getAnimations().length,opacity:getComputedStyle(document.querySelector('.fx')).opacity,transforms:[...document.querySelectorAll('.part')].map(x=>getComputedStyle(x).transform)})''')
                assert reduced['animations']==0 and float(reduced['opacity'])==0 and all(x=='none' for x in reduced['transforms'])
                results.append(dict(id=item['id'],animation_sha256=item['animation_sha256'],phases_checked=5,
                    center_transparent=True,inner_contour_identical=True,whole_frame_fixed=True,
                    independent_layer_motion=item['tier']=='legendary',aspect_ratio_preserved=True,
                    halo=True,shading=True,visible_pixels_at_128px=visibility,loop_max_delta_128px=loop_max,reduced_motion=True))
                print(f'PASS {item["id"]:03}: native alpha, uniform layer transforms, glow, shading, loop.',flush=True)
            page.emulate_media(reduced_motion='no-preference')
            page.goto(base+'/assets/profile-borders-v2/index.html',wait_until='networkidle')
            assert page.locator('meta[name="asset-version"]').get_attribute('content')=='profile-borders-v2'
            assert page.locator('article').count()==100
            page.locator('#actual-size').click();assert page.locator('.sample').first.bounding_box()['width']==128
            for tier,count in [('normal',30),('premium',25),('rare',20),('epic',15),('legendary',10)]:
                page.locator(f'[data-filter="{tier}"]').click();assert page.locator('article:visible').count()==count
            page.locator('article:visible summary').first.click()
            assert page.locator('article:visible .layers a').first.locator('img').count()==1
            assert page.locator('article:visible').first.locator('.layers a').count()==10
            page.locator('#pause').click();assert page.locator('#pause').get_attribute('aria-pressed')=='true'
            assert all('/assets/profile-borders-v2/' in u for u in page.locator('.sample>img').evaluate_all('(a)=>a.map(x=>x.src)'))
            version=browser.version;browser.close()
    finally:server.shutdown();server.server_close();thread.join()
    report=dict(status='passed',asset_version=2,browser='Chromium '+version,static_pngs_checked=100,
                independently_drawn_ornaments=independent,frame_layers=100,placements_checked=placements,
                animations_checked=len(results),rendered_phases_checked=len(results)*5,
                center=[512,512],inner_diameter_px=716,legacy_files_overwritten=False,
                gallery_version_check=True,gallery_128px_check=True,gallery_independent_layer_links=True,results=results)
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS: V2 100 frames, 300 ornaments, 25 animations; no squashing and fixed transparent apertures.')


if __name__=='__main__':main()
