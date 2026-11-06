"""Effects on an intact epic PNG; original-pixel layers only for legendary.

The fixed frame includes repainted hidden backing under the original ornaments. Complete ornament
PNG layers sit behind that mount. At rest, the CPU layer composite is exactly
the repaired PNG: no icons, decorations or frame geometry are substituted.
"""
import base64
import hashlib
import io
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image,ImageColor,ImageDraw
from scipy.ndimage import binary_dilation

from build_profile_animations import effect_shapes,enlarge_effects,svg_shape
from profile_motion_rigs import MOTIONS
from export_v1_repairs import HOLE,MARGIN,R,BAND,repair_export

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/profile-borders-v1-repaired'
VISIBLE=(R>=410)&~MARGIN
MASK=(~HOLE)&~MARGIN


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def uri(image):
    data=io.BytesIO();image.save(data,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(data.getvalue()).decode()


def file_uri(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()


def mask_uri(condition):
    rgba=np.full((1024,1024,4),255,dtype=np.uint8);rgba[:,:,3]=np.where(condition,255,0)
    return uri(Image.fromarray(rgba))


def ornament_rig(number,pixels):
    y,x=np.indices(R.shape);angle=np.degrees(np.arctan2(y+.5-512,x+.5-512));parts=[]
    def point(a,r=382):return (512+math.cos(math.radians(a))*r,512+math.sin(math.radians(a))*r)
    def sector(name,a,width,inner=374):
        delta=(angle-a+180)%360-180
        parts.append(dict(name=name,mask=(abs(delta)<width/2)&(R>=inner),origin=point(a)))
    if number==91:
        sector('star_core',-90,34)
        for j,a in enumerate([-140,-40,40,140]):sector(f'crystal_{j}',a,32,382)
    elif number==92:
        for j,a in enumerate([-140,-40,40,140]):sector(f'ribbon_{j}',a,70)
    elif number==93:
        for j,a in enumerate([-150,-90,-30,30,90,150]):sector(f'corona_{j}',a,48,379)
    elif number==94:
        sector('crown',-90,38)
        for j,(cx,cy,radius) in enumerate([(239,245,35),(780,781,57)]):
            parts.append(dict(name=f'gear_{j}',mask=(x-cx)**2+(y-cy)**2<radius**2,origin=(cx,cy)))
        for j,a in enumerate([-35,145]):sector(f'time_crystal_{j}',a,25,384)
    elif number==95:
        for j,a in enumerate([-150,-90,-30,30,90,150]):sector(f'portal_shard_{j}',a,46)
    elif number==96:
        for j,a in enumerate([-145,-112,-68,-35]):sector(f'branch_{j}',a,30,378)
        for j,a in enumerate([55,90,125]):sector(f'root_{j}',a,32,375)
    elif number==98:
        sector('dragon_head',-55,42,376)
        for j,a in enumerate([-150,-5,70,145]):sector(f'body_joint_{j}',a,48,375)
    elif number==99:
        for j,a in enumerate([-150,-90,-30,30,90,150]):sector(f'prism_facet_{j}',a,40,375)
    elif number==100:
        for j,a in enumerate([-135,-90,-45,0,45,90,135,180]):sector(f'orbit_bracket_{j}',a,34,376)
    else:raise ValueError(number)
    return parts


def layer_masks(number,pixels):
    if number==97:
        rgb=pixels[:,:,:3].astype(float);y,x=np.indices(R.shape)
        white=(rgb[:,:,0]>95)&(rgb[:,:,1]>110)&(rgb[:,:,2]>135)&(rgb[:,:,2]>=rgb[:,:,0]-3)
        # Feather silhouettes only: exclude silver rails, crown highlights and ribbons.
        upper=[(38,510),(35,350),(65,245),(115,160),(280,65),(224,155),(245,194),(280,193),(250,240),(213,292),(173,356),(142,423),(111,476)]
        lower=[(174,752),(230,759),(270,793),(315,824),(360,863),(394,910),(390,943),(302,940),(220,886),(182,830)]
        specs=[('left_upper_wing',upper,(218,290),-1),
               ('right_upper_wing',[(1024-a,b) for a,b in upper],(806,290),1),
               ('left_lower_wing',lower,(300,836),1),
               ('right_lower_wing',[(1024-a,b) for a,b in lower],(724,836),-1)]
        parts=[]
        for name,points,origin,sign in specs:
            zone=Image.new('1',(1024,1024));ImageDraw.Draw(zone).polygon(points,fill=1)
            zone=np.array(zone,dtype=bool)
            zone=binary_dilation(zone,iterations=10 if 'upper' in name else 2)
            ink=(rgb[:,:,2]>rgb[:,:,0]+4)&(rgb[:,:,0]<100)
            gold=(rgb[:,:,0]>110)&(rgb[:,:,1]>75)&(rgb[:,:,2]<rgb[:,:,1]*.68)&(rgb[:,:,0]>rgb[:,:,2]*1.5)
            feather=(binary_dilation(white,iterations=8)|ink)&zone&~binary_dilation(gold,iterations=1)
            parts.append(dict(name=name,mask=feather,origin=origin))
    else:
        original=ornament_rig(number,pixels)
        # Recover ink outlines and attachment pixels around the annotated parts.
        parts=[dict(name=p['name'].replace('-','_'),mask=binary_dilation(p['mask'],iterations=4),origin=p['origin']) for p in original]
    used=np.zeros(R.shape,dtype=bool)
    for p in parts:
        p['mask']=p['mask']&~used&(pixels[:,:,3]>0)&~HOLE
        assert p['mask'].sum()>40,(number,p['name'])
        used|=p['mask']
    return parts,used


def make_layers(item,image):
    number=item['id'];pixels=np.array(image)
    parts,union=layer_masks(number,pixels)
    folder=OUT/'layers/legendary'/f'{number:03}';folder.mkdir(parents=True,exist_ok=True)
    backing_path=folder/'underpaint.png'
    if not backing_path.exists():
        mapping=Path('/workspace/v1-correction-work/underpaint')/f'{number}.json'
        assert mapping.exists(),f'Missing artist underpainting for {number}'
        backing_source=Path(json.loads(mapping.read_text())['path'])
        backing,_=repair_export(backing_source,OUT/item['file']);backing.save(backing_path)
    backing=np.array(Image.open(backing_path).convert('RGBA'))
    visible_union=np.zeros(R.shape,dtype=bool)
    frame=pixels.copy()
    for part in parts:
        part['fixed_mount_radius']=360 if number==94 and 'gear' in part['name'] else 386 if number==97 and 'upper' in part['name'] else 410
        part['visible']=(R>=part['fixed_mount_radius'])&~MARGIN
        selected=part['mask']&part['visible'];visible_union|=selected;frame[selected]=0
    # Hidden paint is covered by fully opaque original pixels at rest.
    hidden=visible_union&(pixels[:,:,3]==255)&(backing[:,:,3]>=160)&(R<435)
    frame[hidden]=backing[hidden];frame[:,:,3][hidden]=255
    frame_path=folder/'frame.png';Image.fromarray(frame).save(frame_path)
    records=[];reconstructed=Image.fromarray(frame)
    for i,part in enumerate(parts):
        layer=np.zeros_like(pixels);layer[part['mask']]=pixels[part['mask']]
        file=folder/(part['name']+'.png');Image.fromarray(layer).save(file)
        visible=layer.copy();visible[~part['visible']]=0
        reconstructed=Image.alpha_composite(reconstructed,Image.fromarray(visible))
        records.append(dict(name=part['name'],file=str(file.relative_to(OUT)),origin=list(part['origin']),
                            sha256=sha(file),source_pixels=int(part['mask'].sum()),fixed_mount_radius=part['fixed_mount_radius']))
    delta=int(np.count_nonzero(np.array(reconstructed)!=pixels))
    assert delta==0,(number,'Rest composition changed original pixels',delta)
    info=dict(id=number,reference_commit=item['reference_commit'],source_sha256=item['sha256'],
              frame=str(frame_path.relative_to(OUT)),frame_sha256=sha(frame_path),parts=records,
              rest_composite_changed_values=delta,layer_canvas=[1024,1024],
              fixed_mount_radius=410,original_ornaments_replaced=False,
              underpaint_file=str(backing_path.relative_to(OUT)),underpaint_sha256=sha(backing_path),
              hidden_backing_pixels=int(hidden.sum()))
    (folder/'layers.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
    return info


def motion(number,index,name,t):
    q=.5-.5*math.cos(2*math.pi*t)
    wave=.5*(math.sin(2*math.pi*(t+index*.13))-math.sin(2*math.pi*index*.13))
    dx=dy=rotation=0.;scale=1.
    if number==91:
        if 'core' in name:scale=1+.04*q
        else:dy=-4*q;rotation=3*wave
    elif number==92:rotation=2.5*wave;dx=1.5*wave
    elif number==93:rotation=(1 if index%2 else -1)*4*q
    elif number==94:
        if 'gear' in name:rotation=(1 if index%2 else -1)*360*t
        elif 'crown' in name:dy=-5*q
        else:dy=-2*wave
    elif number==95:
        angle=math.radians(-150+60*index);dx=6*q*math.cos(angle);dy=6*q*math.sin(angle);rotation=2*wave
    elif number==96:rotation=(4 if 'branch' in name else 3)*wave
    elif number==97:rotation=[-4,4,4,-4][index]*q
    elif number==98:rotation=(3 if 'head' in name else 2)*wave
    elif number==99:rotation=4*wave;dy=-3*q
    elif number==100:rotation=(1 if index<4 else -1)*2*q;dy=2*wave
    return dx,dy,rotation,scale


def mix(color,amount):
    rgb=ImageColor.getrgb(color)
    values=[round(v*(1+amount)) if amount<0 else round(v+(255-v)*amount) for v in rgb]
    return '#'+''.join(f'{max(0,min(255,v)):02x}' for v in values)


def build_effects(number):
    shapes=effect_shapes(number)
    if number<91:shapes=enlarge_effects(shapes)
    defs=[];shaded=''.join(svg_shape(s) for s in shapes);raw=shaded
    for i,color in enumerate(sorted({s['color'] for s in shapes})):
        key=f'effect-color-{i}'
        defs.append(f'<linearGradient id="{key}" x1="0" y1="0" x2=".4" y2="1"><stop offset="0" stop-color="{mix(color,.55)}"/><stop offset=".4" stop-color="{color}"/><stop offset="1" stop-color="{mix(color,-.38)}"/></linearGradient>')
        shaded=shaded.replace(f'fill="{color}"',f'fill="url(#{key})"')
    defs.append('<filter id="halo" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="5"/></filter>')
    defs.append('<filter id="shade" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB"><feDropShadow dx="0" dy="2.5" stdDeviation="1.7" flood-color="#17263c" flood-opacity=".6"/></filter>')
    body=f'<g class="fx"><g class="halo" filter="url(#halo)" opacity=".7">{raw}</g><g class="shaded" filter="url(#shade)">{shaded}</g></g>'
    return ''.join(defs),body


def main():
    items=json.loads((OUT/'manifest.json').read_text())
    for item in items:
        if item['tier'] not in ('epic','legendary'):continue
        number=item['id'];legend=item['tier']=='legendary';duration=7.68 if legend else 3.84;count=96 if legend else 48
        defs=[f'<mask id="aperture" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{mask_uri(MASK)}"/></mask>']
        css=[];body=[]
        if legend:
            layers=make_layers(item,Image.open(OUT/item['file']).convert('RGBA'))
            for mount in sorted({p['fixed_mount_radius'] for p in layers['parts']}):
                defs.append(f'<mask id="attachment-{mount}" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024" style="mask-type:alpha"><image width="1024" height="1024" href="{mask_uri((R>=mount)&~MARGIN)}"/></mask>')
            body.append(f'<image class="fixed-frame" width="1024" height="1024" href="{file_uri(OUT/layers["frame"])}"/>')
            fragments=[]
            for i,part in enumerate(layers['parts']):
                frames=[]
                for k in range(count+1):
                    dx,dy,rotation,scale=motion(number,i,part['name'],k/count)
                    frames.append(f'{k*100/count:.5f}%{{transform:translate({dx:.6f}px,{dy:.6f}px) rotate({rotation:.6f}deg) scale({scale:.6f})}}')
                ox,oy=part['origin'];css.append(f'.part-{i}{{transform-origin:{ox}px {oy}px;animation:joint{i} {duration}s linear infinite}}@keyframes joint{i}{{'+''.join(frames)+'}')
                fragments.append(f'<g mask="url(#attachment-{part["fixed_mount_radius"]})"><image class="part part-{i}" data-part="{part["name"]}" width="1024" height="1024" href="{file_uri(OUT/part["file"])}"/></g>')
            body.append(''.join(fragments))
            item.update(artwork_layer_separated=True,layer_manifest=f'layers/legendary/{number:03}/layers.json',
                        part_count=len(layers['parts']),rest_composite_changed_values=0,motion_description=MOTIONS[number][1])
        else:
            body.append(f'<image class="fixed-frame" width="1024" height="1024" href="{file_uri(OUT/item["file"])}"/>')
            item.update(artwork_layer_separated=False,part_count=0,motion_description='V1 완성 PNG 고정 + 후광·명암 이펙트 점멸')
        effect_defs,effect_body=build_effects(number);defs.append(effect_defs);body.append(effect_body)
        peak=.85 if legend else .95
        keys=''.join(f'{k*100/count:.5f}%{{opacity:{peak*(.5-.5*math.cos(2*math.pi*k/count)):.6f}}}' for k in range(count+1))
        css.append(f'.fx{{opacity:0;animation:fade {duration}s linear infinite}}@keyframes fade{{{keys}}}')
        css.append('@media(prefers-reduced-motion:reduce){.fx{animation:none;opacity:0}.part{animation:none;transform:none}}')
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><title>V1 repair {number:03} {item["name"]}</title><defs>{"".join(defs)}</defs><style>{"".join(css)}</style><g mask="url(#aperture)">{"".join(body)}</g></svg>'
        path=OUT/'animations'/item['tier']/f'profile_{number:03}_{item["tier"]}_animated.svg';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(svg)
        item.update(animation=str(path.relative_to(OUT)),animation_sha256=sha(path),duration_ms=round(duration*1000),
                    effect_peak_opacity=peak,effect_halo=True,effect_shading=True,whole_frame_motion='none')
        print(f'Built {number:03}: '+('original-pixel legendary layers' if legend else 'intact epic PNG + effect'),flush=True)
    (OUT/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
