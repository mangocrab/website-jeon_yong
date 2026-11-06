"""Export conservative repairs of the approved first-upload artwork.

Reference = commit 844e7c2. No V2 designs, sprite redraws, or radial resampling.
Only global oval-projection rectification, uniform canvas fitting and inner-edge restoration are applied
after a reference-guided local deformation repair.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import label,map_coordinates,median_filter

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/profile-borders'
OUT=ROOT/'assets/profile-borders-v1-repaired'
Y,X=np.indices((1024,1024));DX=X+.5-512;DY=Y+.5-512
R=np.hypot(DX,DY);T=np.mod(np.arctan2(DY,DX),2*np.pi)
HOLE=R<358;BAND=(R>=358)&(R<360)
MARGIN=(X<8)|(X>=1016)|(Y<8)|(Y>=1016)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def repair_export(source,baseline):
    image=Image.open(source).convert('RGBA').resize((1024,1024),Image.Resampling.LANCZOS)
    pixels=np.array(image)
    a=pixels[:,:,3]
    # A filled gray stencil is not artwork. Remove only its center-connected component.
    gray=(np.max(np.abs(pixels[:,:,:3].astype(int)-[140,150,160]),axis=2)<20)&(a>100)
    groups,_=label(gray)
    center=groups[512,512]
    if center and np.count_nonzero(groups==center)>10000:a[groups==center]=0
    components,_=label(a>=110);sizes=np.bincount(components.ravel());keep=sizes>=24;keep[0]=False
    a=np.where(keep[components]&(a>=20),a,0).astype(np.uint8)
    pixels[:,:,3]=a;pixels[a==0,:3]=0
    angles=np.arange(1440)*2*np.pi/1440;radii=np.arange(310,431,.5)
    sampled=map_coordinates(a,[512+np.sin(angles)[:,None]*radii,512+np.cos(angles)[:,None]*radii],order=1)>160
    run=sampled[:,:-3]&sampled[:,1:-2]&sampled[:,2:-1]&sampled[:,3:]
    valid=run.any(axis=1)
    if valid.mean()<.8:raise ValueError(f'Incomplete circular frame: {source}')
    edge=radii[run.argmax(axis=1)]
    px=np.cos(angles[valid])*edge[valid];py=np.sin(angles[valid])*edge[valid]
    design=np.stack([px*px,2*px*py,py*py],axis=1)
    weights=np.ones(len(px))
    for _ in range(8):
        coeff=np.linalg.lstsq(design*weights[:,None],weights,rcond=None)[0]
        residual=design@coeff-1
        spread=max(.005,float(np.median(np.abs(residual-np.median(residual))))*3)
        weights=1/np.sqrt(1+(residual/spread)**2)
    q=np.array([[coeff[0],coeff[1]],[coeff[1],coeff[2]]])
    values,vectors=np.linalg.eigh(q)
    if values.min()<=0:raise ValueError(f'Invalid opening ellipse: {source}')
    rectifier=358*(vectors@np.diag(np.sqrt(values))@vectors.T)
    yy,xx=np.nonzero(a>160)
    transformed=rectifier@np.stack([xx+.5-512,yy+.5-512])
    extent=float(np.abs(transformed).max())
    fit=min(1.,503/extent)
    forward=fit*rectifier;inverse=np.linalg.inv(forward)
    offset=np.array([512.,512.])-inverse@np.array([512.,512.])
    aligned=Image.fromarray(pixels).transform((1024,1024),Image.Transform.AFFINE,
                 (inverse[0,0],inverse[0,1],offset[0],inverse[1,0],inverse[1,1],offset[1]),Image.Resampling.BICUBIC)
    pixels=np.array(aligned);a=pixels[:,:,3]
    # Repair only a narrow inner edge, never stretch ornament pixels to a circle.
    radii=np.arange(358,431,.5)
    sampled=map_coordinates(a,[512+np.sin(angles)[:,None]*radii,512+np.cos(angles)[:,None]*radii],order=1)>160
    run=sampled[:,:-3]&sampled[:,1:-2]&sampled[:,2:-1]&sampled[:,3:]
    valid=run.any(axis=1);edge=radii[run.argmax(axis=1)]
    edge[~valid]=360;edge=median_filter(edge,size=9,mode='wrap')
    local=np.interp(T*1440/(2*np.pi),np.arange(1441),np.r_[edge,edge[0]])
    lining=(R>=358)&(R<=np.minimum(local+1,364))&(a<160)
    reference=np.array(Image.open(baseline).convert('RGBA'))
    for k in range(3):
        colors=map_coordinates(reference[:,:,k],[512+np.sin(T)*359,512+np.cos(T)*359],order=1)
        pixels[:,:,k][lining]=colors[lining]
    pixels[:,:,3][lining]=255
    # Restore opaque ink interiors; preserve partial alpha only on antialiased edges.
    pixels[:,:,3][pixels[:,:,3]>=245]=255
    pixels[BAND]=reference[BAND]
    pixels[HOLE|MARGIN]=0;pixels[pixels[:,:,3]==0,:3]=0
    return Image.fromarray(pixels),dict(uniform_canvas_fit=round(fit,8),
        opening_projection_axes_before=[round(float(1/np.sqrt(v)),3) for v in values],
        projection_rectification_matrix=forward.tolist(),
        geometry_method='global_ellipse_projection_rectification_and_uniform_canvas_fit',
        radial_warp_applied=False,inner_lining_pixels_restored=int(lining.sum()))


def main():
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,default=Path('/workspace/v1-correction-work'))
    p.add_argument('--pending-only',action='store_true',help='Keep verified exported rows and fill pending IDs only; use a full export after any source edits.')
    args=p.parse_args();catalog=json.loads((BASE/'manifest.json').read_text())
    cached={r['id']:r for r in json.loads((OUT/'manifest.json').read_text())} if args.pending_only and (OUT/'manifest.json').exists() else {}
    audit={a['id']:a for a in json.loads((args.work/'distortion-audit.json').read_text())}
    records=[];pending=[]
    for item in catalog:
        number=item['id'];baseline=BASE/item['file'];target=OUT/item['file']
        if number in cached:
            row=cached[number]
            assert sha(target)==row['sha256'] and sha(baseline)==row['reference_sha256']
            records.append(row);continue
        edit=args.work/'edits'/f'{number:03}.json'
        if audit[number]['needs_restoration'] and not edit.exists():pending.append(number);continue
        target.parent.mkdir(parents=True,exist_ok=True)
        if audit[number]['needs_restoration']:
            source=Path(json.loads(edit.read_text())['path']);image,stats=repair_export(source,baseline);image.save(target)
            status='reference_guided_deformation_repair'
        else:
            shutil.copyfile(baseline,target);stats=dict(geometry_method='unchanged_approved_png',radial_warp_applied=False);status='preserved_without_changes'
        pixels=np.array(Image.open(target).convert('RGBA'))
        assert not pixels[:,:,3][HOLE].any() and (pixels[:,:,3][BAND]==255).all()
        assert np.array_equal(pixels[BAND],np.array(Image.open(baseline).convert('RGBA'))[BAND])
        row={k:item[k] for k in ('id','name','description','tier','file')}
        row.update(reference_commit='844e7c29e9e0fa80ff2d8c9fc89322eb059e66bf',
            reference_file='../profile-borders/'+item['file'],reference_sha256=sha(baseline),
            sha256=sha(target),status=status,width=1024,height=1024,center=[512,512],inner_diameter_px=716,
            source_design='first_GitHub_upload_844e7c2',artwork_layer_separated=False,**stats)
        records.append(row)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(exported=len(records),pending=pending)))


if __name__=='__main__':main()
