"""Build 100 unwarped frames and 25 glow animations from independently drawn sprites.

All ornament placement is a similarity transform: one uniform scale, translation,
and optional rigid rotation. There is no polar remapping or per-axis deformation.
The source atlases are intermediate inputs; shipped layers are separate PNGs.
"""
import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageColor
from scipy.ndimage import binary_dilation,label

from build_profile_animations import effect_shapes,enlarge_effects,svg_shape

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/profile-borders-v2'
SIZE=1024
Y,X=np.indices((SIZE,SIZE))
RAD=np.hypot(X+.5-512,Y+.5-512)
APERTURE=RAD<358
SAFE=RAD<=496
BAND=(RAD>=358)&(RAD<360)
COLORS=(
 '#e4dac5 #42464d #efa89e #8bbfe4 #91ba6c #efd05c #6488ba #ded0b8 #957057 #34466f '
 '#e8a0b4 #e5d2a5 #ac95c7 #bd793e #afd6ec #4d94c5 #a8a49b #99c7dd #999da5 #cdb68d '
 '#7771b6 #d88eaa #ad9bc4 #b29db3 #e2ad5d #71a65f #c29a60 #99755f #8ebfdb #bba7cc '
 '#dca3b5 #cf889d #d2ac4b #77935c #d49291 #cebfb6 #b895bd #596381 #c18b52 #b08e77 '
 '#d6b6c1 #ad937c #ae9877 #82abc9 #d6979a #c3b3c7 #9b7561 #776aa0 #b594c0 #5ba9a4 '
 '#8a8c98 #9b91a3 #ae8a62 #ba9b89 #7a80ad #98a8c4 #c4b47b #8a93b4 #9b8ec3 #9a74bf '
 '#8cafa1 #7799bd #a45f6c #7f9e6f #ada3bf #8ebbd3 #d6a051 #718fb4 #70b6b7 #ac9b80 '
 '#b09c8c #9483b2 #779ab9 #8baa65 #648f9f #c28f51 #a1bbd1 #bc9952 #886b9d #9f5d66 '
 '#9984ac #c0b283 #a38bb6 #647f9c #86a17a #a290b7 #b4c1cf #8b9fb4 #7e6496 #b3a16b '
 '#5f94b9 #9a88bd #9c6257 #b2a162 #a080b6 #8eab6b #c8bea1 #779cb0 #b7a5c8 #aaa17b'
).split()
assert len(COLORS)==100
MOTION_LABELS={91:'별핵 맥동과 결정 떠오름',92:'은하 리본의 굽힘',93:'코로나 펼침·접힘',
 94:'왕관 승강과 기어 작동',95:'차원 파편 개폐',96:'나뭇가지·뿌리 흔들림',
 97:'개별 날개 펼침·접힘',98:'용 머리·몸 마디 움직임',99:'프리즘 결정 펼침',100:'천체 장치 개폐'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def color_mix(color,amount):
    rgb=ImageColor.getrgb(color)
    result=[round(v*(1+amount)) if amount<0 else round(v+(255-v)*amount) for v in rgb]
    return '#'+''.join(f'{max(0,min(255,v)):02x}' for v in result)


def point(angle,r):
    a=math.radians(angle);return 512+math.cos(a)*r,512+math.sin(a)*r


def png_uri(image):
    b=io.BytesIO();image.save(b,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()


def file_uri(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()


def clean_sprite(atlas,cell):
    """Export a separately drawn cell, retaining its original proportions."""
    w,h=atlas.size;col=cell%3;row=cell//3
    box=(round(col*w/3),round(row*h/3),round((col+1)*w/3),round((row+1)*h/3))
    tile=np.array(atlas.crop(box).convert('RGBA'))
    alpha=tile[:,:,3]
    groups,_=label(alpha>=100);counts=np.bincount(groups.ravel());counts[0]=0
    keep=counts>=40
    core=keep[groups]
    if core.sum()<100:raise ValueError(f'Empty sprite cell {cell}')
    solid=core&(alpha>=150)
    border=int(np.count_nonzero(solid[0])+np.count_nonzero(solid[-1])+np.count_nonzero(solid[:,0])+np.count_nonzero(solid[:,-1]))
    if border>20:raise ValueError(f'Sprite touches tile boundary: cell {cell}, {border} pixels')
    support=binary_dilation(core,iterations=3)
    tile[:,:,3]=np.where(support&(alpha>=18),alpha,0)
    tile[tile[:,:,3]==0,:3]=0
    image=Image.fromarray(tile);bounds=image.getbbox()
    image=image.crop(bounds)
    padded=Image.new('RGBA',(image.width+16,image.height+16))
    padded.paste(image,(8,8));image=padded
    return image,dict(atlas_cell=cell,source_cell_box=list(box),cell_edge_opaque_pixels=border,
                      source_bbox=list(bounds),source_margin_px=8,independently_drawn=True)


def draw_frame(number,tier,color):
    scale=3;image=Image.new('RGBA',(SIZE*scale,SIZE*scale));d=ImageDraw.Draw(image)
    width={'normal':8,'premium':14,'rare':16,'epic':20,'legendary':20}[tier]
    outer=358+width
    def circle(r,c,stroke=1):
        d.ellipse(((512-r)*scale,(512-r)*scale,(512+r)*scale,(512+r)*scale),outline=c,width=max(1,round(stroke*scale)))
    d.ellipse(((512-outer)*scale,(512-outer)*scale,(512+outer)*scale,(512+outer)*scale),fill=color)
    d.ellipse(((512-358)*scale,(512-358)*scale,(512+358)*scale,(512+358)*scale),fill=(0,0,0,0))
    dark=color_mix(color,-.38);light=color_mix(color,.35)
    circle(outer,dark,1.6);circle(359,dark,1.3);circle(outer-3,light,1.2)
    if tier!='normal':
        circle(outer-6,color_mix(color,-.1),1.2)
        for a in range(0,360,15 if tier=='premium' else 10):
            x,y=point(a,outer+3);r=1.8 if tier=='premium' else 2.2
            d.ellipse(((x-r)*scale,(y-r)*scale,(x+r)*scale,(y+r)*scale),fill=light,outline=dark,width=scale)
    if tier in ('epic','legendary'):
        gold='#d7b970' if tier=='legendary' else color_mix(color,.55)
        circle(outer+7,gold,1.6)
        for a in range(-90,270,45):
            pts=[point(a-1.5,outer+7),point(a,outer+13),point(a+1.5,outer+7),point(a,outer+1)]
            d.polygon([(x*scale,y*scale) for x,y in pts],fill=gold,outline=dark,width=scale)
    if number==7:
        for a in range(0,360,4):
            d.arc(((512-363)*scale,(512-363)*scale,(512+363)*scale,(512+363)*scale),a,a+2,fill='#d7e5f2',width=4*scale)
    if number==8:
        for a in range(0,360,5):
            d.arc(((512-363)*scale,(512-363)*scale,(512+363)*scale,(512+363)*scale),a,a+2.5,fill='#ba5d5a',width=2*scale)
    if number==21:
        for a in range(0,360,5):
            x,y=point(a,369);d.rectangle(((x-3)*scale,(y-3)*scale,(x+3)*scale,(y+3)*scale),fill=color,outline=dark,width=scale)
    if number==30:
        rainbow=['#e9abb3','#ecd59a','#b4d1a8','#a0cee0','#b5b2dc','#d3acd3']
        for k in range(36):
            d.arc(((512-364)*scale,(512-364)*scale,(512+364)*scale,(512+364)*scale),k*10,k*10+10,fill=rainbow[k%6],width=5*scale)
    image=image.resize((SIZE,SIZE),Image.Resampling.LANCZOS)
    rgba=np.array(image);rgba[APERTURE|~SAFE]=0
    rgba[BAND,3]=255;rgba[BAND,:3]=ImageColor.getrgb(color)
    rgba[rgba[:,:,3]==0,:3]=0
    return Image.fromarray(rgba),outer


def sprite_geometry(image,angle,radius,frame_outer,fixed_r=None):
    rgba=np.array(image);yy,xx=np.nonzero(rgba[:,:,3]>30)
    dx=xx+.5-image.width/2;dy=yy+.5-image.height/2
    a=math.radians(angle)
    u=dx*math.cos(a)+dy*math.sin(a)
    v=-dx*math.sin(a)+dy*math.cos(a)
    # Fit the silhouette to the annulus using a single uniform scale.
    # Wide crowns retain tangential space rather than shrinking to a tiny disk.
    uniform=radius*2.8/max(image.size)
    inner=365.;outer=485.
    for _ in range(120):
        su=uniform*u;sv=uniform*v
        if np.max(np.abs(sv))>=outer:
            uniform*=.97;continue
        upper=float(np.min(-su+np.sqrt(np.maximum(0,outer**2-sv**2))))
        inside=np.abs(sv)<inner
        lower=float(np.max(-su[inside]+np.sqrt(inner**2-sv[inside]**2))) if inside.any() else 360.
        if lower+1<=upper:
            r=lower+min(2.,(upper-lower)/2)
            break
        uniform*=.97
    else:raise ValueError('Cannot fit an unwarped ornament')
    cx,cy=point(angle,r)
    return dict(center=[cx,cy],angle=angle,radius=r,uniform_scale=uniform,
                width=image.width*uniform,height=image.height*uniform,
                source_size=list(image.size),aspect_ratio_preserved=True)


def layout(item,sprites,outer):
    n=item['id'];tier=item['tier'];placements=[]
    def add(part,angle,size,fixed=None):
        image,_=sprites[part];g=sprite_geometry(image,angle,size,outer,fixed)
        placements.append(dict(part=part,**g))
    if tier=='normal':
        angle={3:30,4:-45,5:90,9:35,11:45,12:-135,13:-120,14:-45,18:-90,20:45,25:-90,29:-45}.get(n,90)
        angles={4:[-45,140],10:[-60,45,170],13:[0,180],24:[-30,90,210],26:[45,225]}.get(n,[angle])
        for a in angles:add(0,a,33 if len(angles)==1 else 26)
    elif tier=='premium':
        if n in (39,40,43):
            for p,a in [(0,-125),(1,-55),(2,90)]:add(p,a,49 if p<2 else 47)
        elif n in (41,42,48,51,52,53,54,55):
            for p,a in [(0,-90),(1,145),(2,35)]:add(p,a,52 if p==0 else 45)
        elif n==44:
            add(0,90,51)
            for a in [-140,-40,40,140]:add(1,a,34)
            add(2,-90,34)
        else:
            for a in [-90,30,150]:add(0,a,47)
            for a in [-150,-30,90]:add(1,a,34)
            for a in [-110,10,130]:add(2,a,27)
    elif tier=='rare':
        add(0,-90,54);add(0,90,40)
        for a in [-155,25]:add(1,a,43)
        for a in [-25,155]:add(2,a,37)
    elif tier=='epic':
        add(0,-90,56);add(0,90,43)
        for a in [-140,-40,40,140]:add(1,a,43)
        for a in [0,180]:add(2,a,43)
    else:
        angles=[-90,-135,-45,180,0,135,45,90,-90]
        for p,a in enumerate(angles):add(p,a,24 if p==8 else 58,388 if p==8 else 421)
    return placements


def render_static(frame,placements,sprites):
    canvas=frame.copy()
    for p in placements:
        source=sprites[p['part']][0];s=p['uniform_scale'];cx,cy=p['center']
        inverse=(1/s,0,source.width/2-cx/s,0,1/s,source.height/2-cy/s)
        layer=source.transform((SIZE,SIZE),Image.Transform.AFFINE,inverse,Image.Resampling.BICUBIC)
        canvas=Image.alpha_composite(canvas,layer)
    rgba=np.array(canvas);rgba[APERTURE|~SAFE]=0;rgba[rgba[:,:,3]==0,:3]=0
    return Image.fromarray(rgba)


def motion(number,part,t,p):
    phase=part*.12;q=.5-.5*math.cos(2*math.pi*t);wave=math.sin(2*math.pi*(t+phase))
    dx=dy=rotation=0.;scale=1.
    if number==91:
        if part==0:scale=.92+.12*q
        elif part not in (7,8):dy=-5*wave;rotation=4*wave
    elif number==92:
        if part in (1,2):dx=6*wave;rotation=9*wave
        elif part!=8:dy=4*wave;rotation=5*wave
    elif number==93:
        if part in range(1,7):rotation=(1 if part%2 else -1)*(12-24*q)
        elif part==0:scale=.96+.07*q
    elif number==94:
        if part in (1,2):rotation=(1 if part==1 else -1)*360*t
        elif part==0:dy=-8*q
        elif part in (5,6):dy=-4*wave
    elif number==95:
        if part in range(1,7):
            a=math.radians(p['angle']);dx=8*q*math.cos(a);dy=8*q*math.sin(a);rotation=5*wave
        elif part==0:dy=-4*q
    elif number==96:
        if part in range(1,7):rotation=(6 if part<5 else 8)*wave
        elif part==0:rotation=2*wave
    elif number==97:
        if part in range(1,7):rotation=(1 if part%2 else -1)*(18-30*q)
        elif part==0:scale=.98+.04*q
    elif number==98:
        if part==0:rotation=6*wave
        elif part in (1,2,5,6):rotation=8*wave
        elif part in (3,4):dx=5*wave;dy=3*math.cos(2*math.pi*(t+phase))
    elif number==99:
        if part!=8:rotation=7*wave;dx=4*q*math.cos(math.radians(p['angle']));dy=4*q*math.sin(math.radians(p['angle']))
        if part==0:scale=.96+.08*q
    elif number==100:
        if part in (1,2):rotation=(1 if part==1 else -1)*(12-24*q)
        elif part in (3,4):rotation=(1 if part==3 else -1)*30*wave
        elif part in (5,6):dy=5*wave
        elif part==7:rotation=5*wave
    return dx,dy,rotation,scale


def write_svg(item,frame_path,placements,sprites,animated):
    number=item['id'];legend=item['tier']=='legendary'
    frames=96 if legend else 48;duration=7.68 if legend else 3.84
    defs=[];css=[];body=[];layers=[]
    mask=Image.fromarray(np.dstack([np.full(RAD.shape,255,dtype=np.uint8)]*3+[np.where(~APERTURE&SAFE,255,0).astype(np.uint8)]))
    defs.append(f'<mask id="aperture" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{png_uri(mask)}"/></mask>')
    defs.append(f'<image id="frame" width="1024" height="1024" href="{file_uri(frame_path)}"/>')
    body.append('<use class="frame-fixed" href="#frame"/>')
    for k,p in enumerate(placements):
        _,info=sprites[p['part']];source=OUT/info['file'];uri=file_uri(source)
        cx,cy=p['center'];w,h=p['width'],p['height'];class_name=f'part part-{k}' if animated and legend else 'ornament'
        hinge=number in (93,96,97,98,100) and p['part'] in range(1,7)
        if legend and 'joint' not in p:
            if hinge:
                sprite=sprites[p['part']][0]
                sy,sx=np.nonzero(np.array(sprite.getchannel('A'))>100)
                wx=cx+(sx+.5-sprite.width/2)*p['uniform_scale']
                wy=cy+(sy+.5-sprite.height/2)*p['uniform_scale']
                rr=np.hypot(wx-512,wy-512);root=rr<rr.min()+3
                p['joint']=[float(wx[root].mean()),float(wy[root].mean())]
            else:p['joint']=[cx,cy]
        body.append(f'<image class="{class_name}" data-layer="{p["part"]}" x="{cx-w/2:.6f}" y="{cy-h/2:.6f}" width="{w:.6f}" height="{h:.6f}" preserveAspectRatio="xMidYMid meet" href="{uri}"/>')
        if animated and legend:
            # The actual inner attachment pixels form a stationary hinge.
            ox,oy=p['joint']
            keys=[]
            for j in range(frames+1):
                dx,dy,rotation,s=motion(number,p['part'],j/frames,p)
                keys.append(f'{j*100/frames:.5f}%{{transform:translate({dx:.6f}px,{dy:.6f}px) rotate({rotation:.6f}deg) scale({s:.6f})}}')
            css.append(f'.part-{k}{{transform-origin:{ox:.6f}px {oy:.6f}px;animation:joint{k} {duration}s linear infinite}}@keyframes joint{k}{{'+''.join(keys)+'}')
        layers.append(dict(file=info['file'],source_sha256=info['sha256'],**p))
    if animated:
        shapes=effect_shapes(number)
        if not legend:shapes=enlarge_effects(shapes)
        # Draw shaded effect bodies, a colored halo and a soft cast shadow.
        colors=sorted({s['color'] for s in shapes});replacements={}
        for j,color in enumerate(colors):
            key=f'fx-color-{j}';replacements[color]=f'url(#{key})'
            defs.append(f'<linearGradient id="{key}" x1="0" y1="0" x2="0.4" y2="1" gradientUnits="objectBoundingBox"><stop offset="0" stop-color="{color_mix(color,.55)}"/><stop offset=".42" stop-color="{color}"/><stop offset="1" stop-color="{color_mix(color,-.38)}"/></linearGradient>')
        defs.append('<filter id="halo" x="-40%" y="-40%" width="180%" height="180%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="5"/></filter>')
        defs.append('<filter id="shade" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB"><feDropShadow dx="0" dy="2.5" stdDeviation="1.7" flood-color="#17263c" flood-opacity=".65"/></filter>')
        raw=''.join(svg_shape(s) for s in shapes)
        shaded=raw
        for color,url in replacements.items():shaded=shaded.replace(f'fill="{color}"',f'fill="{url}"')
        defs.append(f'<g id="effect-geometry">{raw}</g><g id="effect-shaded">{shaded}</g>')
        body.append('<g class="fx"><use href="#effect-geometry" filter="url(#halo)" opacity=".75"/><use href="#effect-shaded" filter="url(#shade)"/></g>')
        peak=.95 if not legend else .85
        keys=''.join(f'{j*100/frames:.5f}%{{opacity:{peak*(.5-.5*math.cos(2*math.pi*j/frames)):.6f}}}' for j in range(frames+1))
        css.append(f'.fx{{opacity:0;animation:fade {duration}s linear infinite}}@keyframes fade{{{keys}}}')
        css.append('@media(prefers-reduced-motion:reduce){.part{animation:none;transform:none}.fx{animation:none;opacity:0}}')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><title>{item["name"]}</title><defs>{"".join(defs)}</defs><style>{"".join(css)}</style><g mask="url(#aperture)">{"".join(body)}</g></svg>'
    return svg,layers


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,default=Path('/workspace/profile-v2-work'))
    p.add_argument('--from-layers',action='store_true',help='Rebuild from the shipped editable PNGs and placement JSON, preserving layer edits')
    args=p.parse_args()
    catalog_path=OUT/'manifest.json' if args.from_layers else ROOT/'assets/profile-borders/manifest.json'
    catalog=json.loads(catalog_path.read_text())
    by_id={}
    if not args.from_layers:
        for a in json.loads((args.work/'pieces.json').read_text()):by_id.setdefault(a['id'],[]).append(a)
    atlases={};manifest=[];pending=[]
    for item in catalog:
        number=item['id'];tier=item['tier'];planned=by_id.get(number,[])
        if not args.from_layers and any(not (args.work/'atlases'/f'{a["atlas"]}.json').exists() for a in planned):pending.append(number);continue
        folder=OUT/'layers'/tier/f'{number:03}';folder.mkdir(parents=True,exist_ok=True)
        sprites={}
        if args.from_layers:
            saved=json.loads((folder/'layers.json').read_text())
            for j,info in enumerate(saved['ornaments']):
                path=OUT/info['file'];image=Image.open(path).convert('RGBA');info.update(sha256=digest(path),source_size=list(image.size));sprites[j]=(image,info)
        for a in planned:
            if a['atlas'] not in atlases:
                record=json.loads((args.work/'atlases'/f'{a["atlas"]}.json').read_text());atlases[a['atlas']]=Image.open(record['path']).convert('RGBA')
            image,metadata=clean_sprite(atlases[a['atlas']],a['cell'])
            path=folder/f'ornament_{a["part"]+1:02}.png';image.save(path)
            info=dict(name=a['name'],file=str(path.relative_to(OUT)),sha256=digest(path),source_size=list(image.size),atlas=a['atlas'],**metadata)
            sprites[a['part']]=(image,info)
        frame_path=folder/'frame.png'
        if args.from_layers:
            frame=Image.open(frame_path).convert('RGBA');placements=saved['placements']
            for place in placements:
                source=sprites[place['part']][0];place.update(width=source.width*place['uniform_scale'],height=source.height*place['uniform_scale'],source_size=list(source.size))
        else:
            frame,outer=draw_frame(number,tier,COLORS[number-1]);frame.save(frame_path)
            placements=layout(item,sprites,outer)
        image=render_static(frame,placements,sprites)
        target=OUT/tier/f'profile_{number:03}_{tier}.png';target.parent.mkdir(parents=True,exist_ok=True);image.save(target)
        source_svg,layers=write_svg(item,frame_path,placements,sprites,False)
        svg_path=target.with_suffix('.svg');svg_path.write_text(source_svg)
        layer_record=dict(id=number,tier=tier,frame=str(frame_path.relative_to(OUT)),frame_sha256=digest(frame_path),
                          ornaments=[info for _,info in sprites.values()],placements=placements,
                          newly_drawn_ornaments=True,layered_from_independent_artwork=True,
                          geometry_method='uniform_scale_and_translation_only')
        (folder/'layers.json').write_text(json.dumps(layer_record,ensure_ascii=False,indent=2)+'\n')
        record={k:item[k] for k in ('id','tier','name','description')}
        record.update(file=str(target.relative_to(OUT)),svg=str(svg_path.relative_to(OUT)),sha256=digest(target),svg_sha256=digest(svg_path),
                      width=SIZE,height=SIZE,center=[512,512],inner_diameter_px=716,safe_radius_px=496,
                      layer_manifest=str((folder/'layers.json').relative_to(OUT)),aspect_ratio_preserved=True,
                      asset_version=2,build_method='independent_layers_uniform',
                      newly_drawn_ornaments=True,ornament_count=len(sprites),placements=layers)
        if tier in ('epic','legendary'):
            animated,layers=write_svg(item,frame_path,placements,sprites,True)
            animation=OUT/'animations'/tier/f'profile_{number:03}_{tier}_animated.svg';animation.parent.mkdir(parents=True,exist_ok=True);animation.write_text(animated)
            record.update(animation=str(animation.relative_to(OUT)),animation_sha256=digest(animation),
                          duration_ms=7680 if tier=='legendary' else 3840,
                          effect_halo=True,effect_shading=True,whole_frame_motion='none',
                          motion_description=MOTION_LABELS[number] if tier=='legendary' else '후광·명암이 있는 고정 이펙트 점멸')
        manifest.append(record)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(completed=len(manifest),pending=pending,layers=sum(x['ornament_count'] for x in manifest))))


if __name__=='__main__':main()
