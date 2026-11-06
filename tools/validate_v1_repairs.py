"""Verify approved-reference identity, restricted layer scope and real rendering."""
import argparse
import base64
import functools
import hashlib
import io
import json
import subprocess
import threading
import xml.etree.ElementTree as ET
from collections import Counter
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from export_v1_repairs import HOLE,BAND,MARGIN,R

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-v1-repaired'
NS={'s':'http://www.w3.org/2000/svg'}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def copyfile(self,source,output):
        try:super().copyfile(source,output)
        except (BrokenPipeError,ConnectionResetError):pass


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check(pixels,label):
    assert pixels.shape==(1024,1024,4),label
    assert not pixels[:,:,3][HOLE].any(),f'Center alpha: {label}'
    assert (pixels[:,:,3][BAND]==255).all(),f'Inner edge: {label}'
    assert not pixels[:,:,3][MARGIN].any(),f'Margin: {label}'


def displayed(pixels,color):
    bg=Image.new('RGBA',(1024,1024),color)
    return np.array(Image.alpha_composite(bg,Image.fromarray(pixels)).resize((128,128),Image.Resampling.LANCZOS).convert('RGB')).astype(int)


def main():
    p=argparse.ArgumentParser();p.add_argument('--browser',default='/usr/bin/chromium');p.add_argument('--artifacts',type=Path,default=Path('/tmp/v1-repair-review'));args=p.parse_args();args.artifacts.mkdir(exist_ok=True,parents=True)
    items=json.loads((OUT/'manifest.json').read_text())
    assert len(items)==100 and {a['id'] for a in items}==set(range(1,101))
    assert Counter(a['tier'] for a in items)==dict(normal=30,premium=25,rare=20,epic=15,legendary=10)
    assert len(list(OUT.glob('*/*.png')))==100
    assert not list(OUT.rglob('*.zip'))
    assert sorted(p.name for p in (OUT/'layers').iterdir())==['legendary']
    references=[]
    for a in items:
        original=subprocess.check_output(['git','show','844e7c2:assets/profile-borders/'+a['file']],cwd=ROOT)
        assert hashlib.sha256(original).hexdigest()==a['reference_sha256']
        assert a['reference_commit'].startswith('844e7c2')
        pixels=np.array(Image.open(OUT/a['file']).convert('RGBA'));check(pixels,a['id'])
        baseline=np.array(Image.open(io.BytesIO(original)).convert('RGBA'))
        assert np.array_equal(pixels[BAND],baseline[BAND]),'The original inner contour was changed'
        assert sha(OUT/a['file'])==a['sha256'] and not a['radial_warp_applied']
        if a['status']=='preserved_without_changes':assert (OUT/a['file']).read_bytes()==original
        if a['tier']!='legendary':
            assert not a['artwork_layer_separated'] and not a.get('layer_manifest')
        else:
            assert a['artwork_layer_separated']
            layers=json.loads((OUT/a['layer_manifest']).read_text())
            assert layers['source_sha256']==a['sha256'] and layers['rest_composite_changed_values']==0
            frame=Image.open(OUT/layers['frame']).convert('RGBA');reconstructed=frame.copy();frame_pixels=np.array(frame)
            assert sha(OUT/layers['underpaint_file'])==layers['underpaint_sha256']
            backing=np.array(Image.open(OUT/layers['underpaint_file']).convert('RGBA'))
            for part in layers['parts']:
                assert sha(OUT/part['file'])==part['sha256']
                layer=np.array(Image.open(OUT/part['file']).convert('RGBA'));part_visible=(R>=part['fixed_mount_radius'])&~MARGIN
                overlap=(layer[:,:,3]>0)&part_visible&(frame_pixels[:,:,3]>0)
                assert (layer[:,:,3][overlap]==255).all(),'Hidden backing changes semitransparent original edges'
                assert np.array_equal(frame_pixels[:,:,:3][overlap],backing[:,:,:3][overlap]),'Moving ornament was duplicated instead of using hidden backing'
                layer[~part_visible]=0;reconstructed=Image.alpha_composite(reconstructed,Image.fromarray(layer))
            assert np.array_equal(np.array(reconstructed),pixels),'Original-pixel layer reconstruction changed artwork'
        if a['tier'] in ('epic','legendary'):
            assert sha(OUT/a['animation'])==a['animation_sha256']
            svg=ET.parse(OUT/a['animation']).getroot();fixed=svg.find('.//s:image[@class="fixed-frame"]',NS)
            data=base64.b64decode(fixed.attrib['href'].split(',',1)[1])
            expected=OUT/a['file'] if a['tier']=='epic' else OUT/layers['frame']
            assert data==expected.read_bytes()
            assert svg.find('.//s:feGaussianBlur',NS) is not None and svg.find('.//s:feDropShadow',NS) is not None
            if a['tier']=='epic':assert not svg.findall('.//s:image[@data-part]',NS)
        references.append(dict(id=a['id'],reference_sha256=a['reference_sha256'],sha256=a['sha256'],status=a['status']))
    print('PASS: 100 first-upload references verified; artwork layers exist only for 10 legendary frames.',flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}';results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1024,'height':1024},reduced_motion='no-preference')
            for item in [a for a in items if a['tier'] in ('epic','legendary')]:
                page.emulate_media(reduced_motion='no-preference');page.goto(base+'/assets/profile-borders-v1-repaired/'+item['animation'],wait_until='networkidle')
                animations=page.evaluate('''async()=>{const a=document.getAnimations();await Promise.all(a.map(async x=>{await x.ready;x.pause();await x.ready}));a.forEach(x=>x.currentTime=0);return a.length}''')
                assert animations==1+item['part_count']
                frames=[];states=[]
                for phase in [0,.25,.5,.75,1]:
                    state=page.evaluate('''t=>{document.getAnimations().forEach(a=>a.currentTime=t);const m=document.querySelector('.fixed-frame').getCTM();return {frame:[m.a,m.b,m.c,m.d,m.e,m.f],opacity:Number(getComputedStyle(document.querySelector('.fx')).opacity),parts:[...document.querySelectorAll('.part')].map(p=>{const m=p.getCTM();return [m.a,m.b,m.c,m.d,m.e,m.f]})}}''',phase*item['duration_ms'])
                    assert state['frame']==[1,0,0,1,0,0]
                    assert abs(state['opacity']-item['effect_peak_opacity']*(.5-.5*np.cos(2*np.pi*phase)))<.002
                    for m in state['parts']:
                        singular=np.linalg.svd([[m[0],m[2]],[m[1],m[3]]],compute_uv=False)
                        assert abs(singular[0]-singular[1])<1e-6,'Animated ornament is squashed'
                    raw=page.screenshot(omit_background=True,animations='allow');rgba=np.array(Image.open(io.BytesIO(raw)).convert('RGBA'));check(rgba,f'{item["id"]} / {phase}');frames.append(rgba);states.append(state['parts'])
                    if item['id'] in (76,97) and phase in (0,.5):(args.artifacts/f'{item["id"]:03}-phase-{phase}.png').write_bytes(raw)
                assert np.allclose(states[0],states[4],atol=1e-7,rtol=0),'Loop geometry changed'
                visibility={};loop_max=0
                for name,color in [('light','#f4f2ec'),('dark','#172030')]:
                    a,b,c=[displayed(x,color) for x in (frames[0],frames[2],frames[4])]
                    loop_max=max(loop_max,int(np.abs(a-c).max()));visibility[name]=int(np.count_nonzero(np.abs(a-b).max(axis=2)>=16))
                    assert visibility[name]>=30,'Effect is invisible at profile size'
                assert loop_max<=4,f'Loop sampling discontinuity: {item["id"]}, {loop_max}'
                poster=np.array(Image.open(OUT/item['file']).convert('RGBA'))
                pose_difference=max(int(np.abs(displayed(poster,c)-displayed(frames[0],c)).max()) for c in ['#f4f2ec','#172030'])
                assert pose_difference<=4,f'SVG rest pose changes the original repaired drawing: {item["id"]}, {pose_difference}'
                if item['tier']=='legendary':
                    page.evaluate("document.querySelector('.fx').style.setProperty('opacity','0','important')");isolated=[]
                    for t in [0,item['duration_ms']/2]:
                        page.evaluate('t=>document.getAnimations().forEach(a=>a.currentTime=t)',t)
                        isolated.append(np.array(Image.open(io.BytesIO(page.screenshot(omit_background=True,animations='allow')))))
                    assert np.count_nonzero(isolated[0]!=isolated[1])>200,'No actual original ornament moves'
                page.emulate_media(reduced_motion='reduce');reduced=page.evaluate('''()=>({count:document.getAnimations().length,opacity:getComputedStyle(document.querySelector('.fx')).opacity,parts:[...document.querySelectorAll('.part')].map(x=>getComputedStyle(x).transform)})''')
                assert reduced['count']==0 and float(reduced['opacity'])==0 and all(x=='none' for x in reduced['parts'])
                results.append(dict(id=item['id'],animation_sha256=item['animation_sha256'],phases_checked=5,frame_fixed=True,original_png_rest_pose=True,rest_pose_max_color_delta_128px=pose_difference,inner_contour_preserved=True,center_alpha_zero=True,layer_separated=item['artwork_layer_separated'],visible_effect_pixels_128px=visibility,reduced_motion=True))
                print(f'PASS {item["id"]:03}: original PNG pose, fixed frame, alpha, effect and scoped layers.',flush=True)
            page.emulate_media(reduced_motion='no-preference');page.goto(base+'/assets/profile-borders-v1-repaired/index.html',wait_until='networkidle')
            assert page.locator('meta[name="asset-reference"]').get_attribute('content')=='844e7c2'
            assert page.locator('article').count()==100
            for tier,count in [('normal',30),('premium',25),('rare',20),('epic',15),('legendary',10)]:
                page.locator(f'[data-filter="{tier}"]').click();assert page.locator('article:visible').count()==count
                assert page.locator('article:visible details').count()==(10 if tier=='legendary' else 0)
            page.locator('#actual-size').click();assert page.locator('.sample:visible').first.bounding_box()['width']==128
            page.locator('#effects').click();assert page.locator('#effects').get_attribute('aria-pressed')=='true'
            version=browser.version;browser.close()
    finally:server.shutdown();server.server_close();thread.join()
    report=dict(status='passed',reference_commit='844e7c29e9e0fa80ff2d8c9fc89322eb059e66bf',static_pngs_checked=100,legendary_layer_sets=10,epic_layer_sets=0,ordinary_layer_sets=0,animations_checked=25,rendered_phases_checked=125,center=[512,512],inner_diameter_px=716,browser='Chromium '+version,reference_files=references,results=results)
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PASS: approved first-upload baseline; only legendary split; 100 PNGs / 25 animations.')


if __name__=='__main__':main()
