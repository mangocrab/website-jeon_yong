"""Build separate transparent SVG animations without changing source PNGs.

Epic: stationary themed effect geometry, opacity only.
Legendary: themed articulation of individual ornaments, with a fixed base ring.
The SVG retains the exact opaque inner contour and transparent aperture.
"""
import argparse
import base64
import hashlib
import html
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from profile_motion_rigs import MOTIONS,make_rig,part_transform

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'assets/profile-borders'
OUT = ROOT / 'assets/profile-borders-animated'
SIZE = 1024
RADIUS = 358
FRAME_MS = 80
N_EPIC = 48
N_LEGENDARY = 96
EPIC_PEAK_OPACITY = .95
LEGENDARY_PEAK_OPACITY = .75
EPIC_EFFECT_SCALE = 2.2


def point(degrees, radius):
    a = math.radians(degrees)
    return (512 + math.cos(a)*radius, 512 + math.sin(a)*radius)


def effect_shapes(number):
    """Stationary themed vector recipes; only their opacity is animated."""
    shapes = []

    def line(points, color, width=3):
        shapes.append(dict(kind='line', points=points, color=color, width=width))

    def polygon(points, color):
        shapes.append(dict(kind='polygon', points=points, color=color))

    def ellipse(x, y, rx, ry, color, width=3, fill=False):
        shapes.append(dict(kind='ellipse', box=[x-rx, y-ry, x+rx, y+ry],
                           color=color, width=width, fill=fill))

    def dot(angle, radius, color, size=3):
        x, y = point(angle, radius)
        ellipse(x, y, size, size, color, fill=True)

    def star(angle, radius, color, size=13):
        x, y = point(angle, radius)
        vertices = []
        for k in range(8):
            a = k*math.pi/4
            r = size if k % 2 == 0 else size*.25
            vertices.append((x+math.cos(a)*r, y+math.sin(a)*r))
        polygon(vertices, color)

    def leaf(angle, radius, color, size=14):
        x, y = point(angle, radius)
        a = math.radians(angle)
        tangent = np.array([-math.sin(a), math.cos(a)])
        normal = np.array([math.cos(a), math.sin(a)])
        center = np.array([x, y])
        polygon([tuple(center+tangent*size), tuple(center+normal*size*.45),
                 tuple(center-tangent*size), tuple(center-normal*size*.45)], color)

    def arc(radius, start, end, color, width=3):
        shapes.append(dict(kind='arc', radius=radius, start=start, end=end,
                           color=color, width=width))

    def bolt(angle, radius, color, size=24):
        x, y = point(angle, radius)
        polygon([(x+2,y-size), (x-11,y+2), (x-1,y+2),
                 (x-5,y+size), (x+12,y-5), (x+2,y-5)], color)

    def snow(angle, radius, color):
        x, y = point(angle, radius)
        for k in range(3):
            a = math.radians(k*60)
            line([(x-math.cos(a)*13,y-math.sin(a)*13),
                  (x+math.cos(a)*13,y+math.sin(a)*13)], color, 3)

    def ticks(color, angles):
        for a in angles:
            line([point(a, 445), point(a, 459)], color, 3)

    if number == 76:  # Phoenix embers, no travelling particles.
        for a in [-125,-72,-22,42,112,168]:
            leaf(a, 442, '#ffb64b', 13)
            dot(a+8, 459, '#ef7153')
    elif number == 77:
        for a in [-110,-35,38,126,204]: snow(a, 443, '#a9e9f4')
    elif number == 78:
        for a in [-90,-27,39,106,171,229]: star(a, 444, '#f6cf67', 11)
        ticks('#efd88a', [-64,-57,153,160])
    elif number == 79:
        for a in [-135,-76,-20,47,114,179]: leaf(a, 443, '#b984d5', 16)
        for a in [-110,15,145]: dot(a, 463, '#d9b6ed', 3)
    elif number == 80:
        for a in [-155,-35,85]: arc(452, a, a+48, '#df625f', 4)
        for a in [-91,27,149]: star(a, 443, '#ffaaa1', 8)
    elif number == 81:
        ticks('#d9b46c', range(-175,180,30))
        for a in [-70,65,175]:
            x,y=point(a,433);ellipse(x,y,13,13,'#aabbe8',2)
            line([(x,y-7),(x,y),(x+6,y+4)],'#d9b46c',2)
    elif number == 82:
        for a in [-150,-115,-65,-30,55,125]:
            line([point(a,434),point(a,460)],'#f7dc91',4)
        for a in [-90,90]: star(a,447,'#fff1cf',14)
    elif number == 83:
        for a in [-125,-10,105]:
            arc(446,a,a+43,'#c5cafa',3);star(a+45,446,'#f1d48a',12)
            for j in range(3): dot(a+j*9,455,'#b1b9ea',2+j*.6)
    elif number == 84:
        for a in [-120,-35,55,145]: bolt(a,445,'#73d5f5',20)
        for a in [-77,11,101,190]:dot(a,455,'#b6edfa',3)
    elif number == 85:
        for a in [-135,-65,5,75,145]:
            leaf(a,446,'#80d3bb',12)
            line([point(a-3,430),point(a,438),point(a+3,430)],'#e7c777',3)
    elif number == 86:
        for a in [-105,25,140]:
            x,y=point(a,444);ellipse(x,y,10,10,'#bdb1e8',3,True)
            ellipse(x,y,21,6,'#ead28e',2)
    elif number == 87:
        for a in [-150,-30,50,130]:
            leaf(a,442,'#cfecf5',20);arc(457,a-10,a+12,'#8bc8e5',3)
    elif number == 88:
        for a in [-128,-42,42,120,202]:
            x,y=point(a,448);ellipse(x,y,7,7,'#97dfdf',2)
            dot(a+8,460,'#cce8ea',3)
        for a in [-90,90]:star(a,438,'#d8cd9e',9)
    elif number == 89:
        for a in [-134,-54,26,106,186]:
            leaf(a,444,'#ac78d7',20);leaf(a+5,459,'#d8aae9',9)
    elif number == 90:
        for a in [-126,-37,54,144]:bolt(a,445,'#bb9beb',22)
        for a in [-90,0,90,180]:star(a,457,'#f0cd6b',8)
    elif number == 91:
        for a in [-90,-30,30,90,150,210]:star(a,445,'#f1cf79',12 if a==-90 else 9)
        for a in [-62,47,161]:arc(457,a,a+25,'#92cce8',3)
    elif number == 92:
        for a in [-155,-35,85]:
            arc(445,a,a+64,'#b4a7e3',4);arc(459,a+14,a+45,'#88cbdc',2)
            star(a+68,445,'#e9d7ad',8)
    elif number == 93:
        ticks('#dbb66c', range(-175,180,20))
        for a in [-145,-25,95]:arc(439,a,a+47,'#dc7867',4)
    elif number == 94:
        ticks('#e8c271', range(-165,180,30))
        for a in [-105,15,135]:leaf(a,445,'#87bfdc',16)
    elif number == 95:
        for a in [-135,-75,-15,45,105,165]:
            x,y=point(a,446)
            polygon([(x-10,y-16),(x+13,y-7),(x+5,y+18)],'#80c9d5' if a%120==45 else '#bf98e4')
    elif number == 96:
        for a in [-145,-95,-45,20,80,140]:
            leaf(a,445,'#cfbf75',16);leaf(a+7,456,'#8cbd8b',10)
    elif number == 97:
        for a in [-150,-120,-60,-30,55,125]:
            leaf(a,445,'#dbe4ed',20)
            line([point(a,430),point(a,460)],'#e4cb88',2)
        for a in [-90,90]:star(a,447,'#d0e6f4',11)
    elif number == 98:
        for a in [-130,-10,110]:
            x,y=point(a,445)
            ellipse(x-8,y,12,8,'#b9dce8',3)
            ellipse(x+7,y-4,14,10,'#b9dce8',3)
            arc(459,a+15,a+34,'#e2c877',3)
    elif number == 99:
        colors=['#e6acbc','#d2b4e8','#a3d2e1','#a9d5bc','#e9d299','#dfb8d8']
        for a,c in zip([-135,-75,-15,45,105,165],colors):
            x,y=point(a,445)
            polygon([(x,y-19),(x+11,y),(x,y+19),(x-11,y)],c)
            line([(x,y-12),(x+5,y),(x,y+12)],'#f0e9e0',2)
    elif number == 100:
        for j,a in enumerate([-150,-30,90]):
            arc(437+j*9,a,a+65,'#d9c17d' if j%2==0 else '#a0b9df',3)
            star(a+70,437+j*9,'#e9d4a2',11)
        for a in [-95,25,145]:dot(a,462,'#b8cde8',4)
    else:
        raise ValueError(number)
    return shapes


Y,X = np.indices((SIZE,SIZE))
DISTANCE = np.hypot(X+.5-512,Y+.5-512)
HOLE = DISTANCE < RADIUS
BAND = (DISTANCE >= RADIUS) & (DISTANCE < RADIUS+2)
OUTSIDE = DISTANCE > 480


def opacity_at(t,peak):
    return peak * (.5-.5*math.cos(2*math.pi*t))


def enlarge_effects(shapes):
    """Bake larger geometry, not a moving scale animation."""
    output=[]
    for original in shapes:
        s=dict(original)
        s['width']=s.get('width',1)*2.4
        s['contrast_outline']=True
        if s['kind'] in ('line','polygon'):
            points=np.array(s['points']);center=points.mean(axis=0)
            s['points']=(center+(points-center)*EPIC_EFFECT_SCALE).tolist()
        elif s['kind']=='ellipse':
            x1,y1,x2,y2=s['box'];cx=(x1+x2)/2;cy=(y1+y2)/2
            rx=(x2-x1)/2*EPIC_EFFECT_SCALE;ry=(y2-y1)/2*EPIC_EFFECT_SCALE
            s['box']=[cx-rx,cy-ry,cx+rx,cy+ry]
        output.append(s)
    return output


def svg_shape(s):
    color=s['color']
    width=s.get('width',1)
    if s['kind'] in ('line','polygon'):
        points=' '.join(f'{x:.3f},{y:.3f}' for x,y in s['points'])
        if s['kind']=='polygon':return f'<polygon points="{points}" fill="{color}"'+(' stroke="#25364a" stroke-width="2" stroke-linejoin="round" paint-order="stroke fill"' if s.get('contrast_outline') else '')+'/>'
        under=f'<polyline points="{points}" fill="none" stroke="#25364a" stroke-width="{width+2}" stroke-linecap="round" stroke-linejoin="round"/>' if s.get('contrast_outline') else ''
        return under+f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
    if s['kind']=='ellipse':
        x1,y1,x2,y2=s['box'];cx=(x1+x2)/2;cy=(y1+y2)/2
        style=(f'fill="{color}"'+(' stroke="#25364a" stroke-width="2"' if s.get('contrast_outline') else '')) if s['fill'] else f'fill="none" stroke="{color}" stroke-width="{width}"'
        return f'<ellipse cx="{cx:.3f}" cy="{cy:.3f}" rx="{(x2-x1)/2:.3f}" ry="{(y2-y1)/2:.3f}" {style}/>'
    if s['kind']=='arc':
        x1,y1=point(s['start'],s['radius']);x2,y2=point(s['end'],s['radius']);r=s['radius']
        return f'<path d="M{x1:.3f},{y1:.3f} A{r},{r} 0 0 1 {x2:.3f},{y2:.3f}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
    raise ValueError(s)


def mask_uri(condition):
    """Native-size raster masks preserve the PNG's exact inner-edge pixels."""
    pixels=np.full((SIZE,SIZE,4),255,dtype=np.uint8)
    pixels[:,:,3]=np.where(condition,255,0).astype(np.uint8)
    buffer=io.BytesIO();Image.fromarray(pixels).save(buffer,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode('ascii')


def write_svg(path,source,shapes,number,n_frames,name):
    data=base64.b64encode(source.read_bytes()).decode('ascii')
    duration=n_frames*FRAME_MS/1000
    peak=EPIC_PEAK_OPACITY if number<91 else LEGENDARY_PEAK_OPACITY
    fades=''.join(f'{j*100/n_frames:.5f}%{{opacity:{opacity_at(j/n_frames,peak):.6f}}}' for j in range(n_frames+1))
    moving_mask=mask_uri((DISTANCE>=360)&~OUTSIDE)
    contour_mask=mask_uri(BAND)
    part_defs=[];part_css=[];part_groups=[]
    if number>=91:
        parts,used=make_rig(number,np.array(Image.open(source).convert('RGBA')))
        part_defs.append(f'<mask id="baseMask" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{mask_uri(~used)}"/></mask>')
        for j,part in enumerate(parts):
            part_defs.append(f'<mask id="partMask{j}" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{mask_uri(part["mask"])}"/></mask>')
            keys=''.join(f'{k*100/n_frames:.5f}%{{transform:{part_transform(part,k/n_frames)}}}' for k in range(n_frames+1))
            ox,oy=part['origin']
            part_css.append(f'.part-{j}{{transform-origin:{ox:.4f}px {oy:.4f}px;animation:joint{j} {duration:.3f}s linear infinite}}@keyframes joint{j}{{{keys}}}')
            part_groups.append(f'<g class="part part-{j}" data-part="{part["name"]}"><g mask="url(#partMask{j})"><use href="#art"/></g></g>')
        frame=f'<g class="stationary" mask="url(#baseMask)"><use href="#art"/></g>'+''.join(part_groups)
    else:
        parts=[]
        frame='<g class="stationary"><use href="#art"/></g>'
    title=html.escape(name)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024" role="img" aria-labelledby="title">
<title id="title">{title}</title>
<defs><image id="art" width="1024" height="1024" href="data:image/png;base64,{data}"/><mask id="movingMask" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{moving_mask}"/></mask><mask id="contourMask" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{contour_mask}"/></mask>{''.join(part_defs)}</defs>
<style>.fx{{opacity:0;animation:fade {duration:.3f}s linear infinite}}@keyframes fade{{{fades}}}{''.join(part_css)}@media(prefers-reduced-motion:reduce){{.fx{{animation:none;opacity:0}}.part{{animation:none;transform:none}}}}</style>
<g mask="url(#movingMask)">{frame}</g>
<g mask="url(#movingMask)"><g class="fx">{''.join(svg_shape(s) for s in shapes)}</g></g>
<g mask="url(#contourMask)"><use href="#art"/></g>
</svg>'''
    path.write_text(svg)
    return parts


def build(item,tool_hash):
    source=STATIC/item['file']
    stem=f"profile_{item['id']:03}_{item['tier']}_animated"
    directory=OUT/item['tier'];directory.mkdir(parents=True,exist_ok=True)
    svg=directory/f'{stem}.svg'
    legendary=item['tier']=='legendary'
    n_frames=N_LEGENDARY if legendary else N_EPIC
    shapes=effect_shapes(item['id'])
    if not legendary:shapes=enlarge_effects(shapes)
    parts=write_svg(svg,source,shapes,item['id'],n_frames,item['name'])
    record={k:item[k] for k in ('id','name','tier')}
    record.update(svg=str(svg.relative_to(OUT)),
                  static_fallback='../profile-borders/'+item['file'],
                  width=SIZE,height=SIZE,center=[512,512],inner_diameter_px=716,
                  loop=True,duration_ms=n_frames*FRAME_MS,keyframe_interval_ms=FRAME_MS,
                  frame_motion=MOTIONS[item['id']][0] if legendary else 'none',
                  motion_description=MOTIONS[item['id']][1] if legendary else '고정 이펙트 점멸',
                  whole_frame_motion='none',effect_motion='opacity_only',
                  articulated_parts=[dict(name=p['name'],origin=p['origin'],source_pixels=int(p['mask'].sum())) for p in parts],
                  effect_peak_opacity=LEGENDARY_PEAK_OPACITY if legendary else EPIC_PEAK_OPACITY,
                  effect_geometry_scale=1 if legendary else EPIC_EFFECT_SCALE,lossless=True,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  tool_sha256=tool_hash,
                  svg_sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),
                  svg_bytes=svg.stat().st_size)
    return record


def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',type=int,nargs='+')
    args=p.parse_args()
    catalog=json.loads((STATIC/'manifest.json').read_text())
    items=[a for a in catalog if a['tier'] in ('epic','legendary') and (not args.ids or a['id'] in args.ids)]
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=OUT/'manifest.json'
    records={r['id']:r for r in json.loads(manifest.read_text())} if manifest.exists() else {}
    tool_hash=hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name('profile_motion_rigs.py').read_bytes()).hexdigest()
    for item in items:
        old=records.get(item['id'])
        source_hash=hashlib.sha256((STATIC/item['file']).read_bytes()).hexdigest()
        if old and old['tool_sha256']==tool_hash and old['source_sha256']==source_hash and (OUT/old['svg']).exists():
            print(f"Cached {item['id']:03}",flush=True)
            continue
        records[item['id']]=build(item,tool_hash)
        manifest.write_text(json.dumps(sorted(records.values(),key=lambda x:x['id']),ensure_ascii=False,indent=2)+'\n')
        row=records[item['id']]
        print(f"Built {item['id']:03}: SVG {row['svg_bytes']/1024:.0f} KiB",flush=True)


if __name__=='__main__':
    main()
