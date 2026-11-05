"""Local articulation of existing PNG ornaments; the circular frame stays fixed."""
import math

import numpy as np
from scipy.ndimage import binary_dilation

Y,X=np.indices((1024,1024))
DX,DY=X+.5-512,Y+.5-512
R=np.hypot(DX,DY)
ANGLE=np.degrees(np.arctan2(DY,DX))

MOTIONS={
    91:('stellar_core_bloom','별핵 수축·팽창과 별 결정 펼침'),
    92:('galaxy_ribbon_flex','은하 리본의 교차 굽힘'),
    93:('solar_corona_unfold','태양 코로나 펼침·접힘'),
    94:('clockwork_crown','왕관 승강과 개별 기어 작동'),
    95:('portal_shards_open','차원 파편 벌어짐·맞물림'),
    96:('world_tree_growth','가지 흔들림과 뿌리 뻗음'),
    97:('angel_wings_fold','좌우 깃털 날개 펼침·접힘'),
    98:('dragon_body_flex','용의 머리 들기와 몸 마디 굽힘'),
    99:('prism_facets_open','프리즘 결정 펼침·접힘'),
    100:('celestial_mechanism','천체 장치의 대향 브래킷 개폐'),
}


def point(angle,radius):
    a=math.radians(angle)
    return (512+math.cos(a)*radius,512+math.sin(a)*radius)


def sector(angle,width,inner=378):
    delta=(ANGLE-angle+180)%360-180
    return (np.abs(delta)<width/2)&(R>=inner)&(R<=480)


def make_rig(number,pixels):
    parts=[]
    used=np.zeros((1024,1024),dtype=bool)

    def add(name,mask,origin,closed=(0,0,1,1,0,0),opened=(0,0,1,1,0,0),phase=0):
        nonlocal used
        # Disjoint source ownership avoids doubled/missing ornament pixels.
        mask=mask&~used&(R>=372)&(pixels[:,:,3]>0)
        if mask.sum()<40:
            raise ValueError(f'Empty motion part {number}: {name}')
        used|=mask
        parts.append(dict(name=name,mask=mask,origin=origin,closed=closed,
                          opened=opened,phase=phase))

    def radial(name,angle,width=38,inner=378,travel=12,closed_scale=1,phase=0):
        a=math.radians(angle)
        # Fully open is the uncropped source pose. Fold inward to create room
        # for motion rather than pushing the original tips past the safe margin.
        fold=max(.68,min(.9,closed_scale-.12))
        add(name,sector(angle,width,inner),point(angle,382),
            (-math.cos(a)*travel*.35,-math.sin(a)*travel*.35,fold,fold,0,0),
            (0,0,1,1,0,0),phase)

    if number==91:
        radial('star-core',-90,34,376,7,.80)
        for j,a in enumerate([-140,-40,40,140]):
            radial(f'crystal-{j}',a,32,382,12,.96)
    elif number==92:
        for j,a in enumerate([-140,-40,40,140]):
            tangent=math.radians(a+90)
            add(f'ribbon-{j}',sector(a,70,374),point(a,380),
                (-math.cos(tangent)*9,-math.sin(tangent)*9,1,.94,-4,0),
                (math.cos(tangent)*9,math.sin(tangent)*9,1,1.04,4,0),j*.17)
    elif number==93:
        for j,a in enumerate([-150,-90,-30,30,90,150]):
            radial(f'corona-{j}',a,48,379,13,.84)
    elif number==94:
        add('crown',sector(-90,38,374),(512,142),
            (0,12,.88,.84,0,0),(0,0,1,1,0,0))
        gold=(pixels[:,:,0]>110)&(pixels[:,:,1]>75)&(pixels[:,:,2]<155)
        for j,a in enumerate([-135,45]):
            cx,cy=point(a,405)
            mask=((X-cx)**2+(Y-cy)**2<42**2)&binary_dilation(gold,iterations=2)
            add(f'gear-{j}',mask,(cx,cy),
                (0,0,1,1,0,-18 if j==0 else 18),
                (0,0,1,1,0,18 if j==0 else -18))
        for j,a in enumerate([-35,145]):
            radial(f'time-crystal-{j}',a,25,384,9,.96,.2)
    elif number==95:
        for j,a in enumerate([-150,-90,-30,30,90,150]):
            radial(f'portal-shard-{j}',a,46,374,18,.90)
    elif number==96:
        for j,a in enumerate([-145,-112,-68,-35]):
            sign=-1 if a<-90 else 1
            add(f'branch-{j}',sector(a,30,378),point(a,378),
                (-sign*5,3,.95,.94,-sign*4,0),
                (0,0,1,1,0,0),j*.12)
        for j,a in enumerate([55,90,125]):
            radial(f'root-{j}',a,32,375,13,.88,j*.08)
    elif number==97:
        # Isolate feather colors and their ink outlines, leaving gold rails fixed.
        rgb=pixels[:,:,:3].astype(float)
        feathers=(rgb[:,:,0]>95)&(rgb[:,:,1]>110)&(rgb[:,:,2]>135)&(rgb[:,:,2]>=rgb[:,:,0]-3)
        feathers=binary_dilation(feathers,iterations=3)&(R>=380)
        zones=[('left-upper-wing',(X<470)&(Y<540),(180,430),(.62,.84)),
               ('right-upper-wing',(X>554)&(Y<540),(844,430),(.62,.84)),
               ('left-lower-wing',(X<512)&(Y>=540),(280,840),(.74,.82)),
               ('right-lower-wing',(X>=512)&(Y>=540),(744,840),(.74,.82))]
        for name,zone,origin,(sx,sy) in zones:
            add(name,feathers&zone,origin,(0,0,sx,sy,0,0),(0,0,1,1,0,0))
    elif number==98:
        add('dragon-head',sector(-55,42,376),point(-55,385),
            (-3,7,.94,.85,-2,0),(0,0,1,1,0,0))
        for j,a in enumerate([-150,-5,70,145]):
            tx,ty=math.cos(math.radians(a+90))*9,math.sin(math.radians(a+90))*9
            add(f'body-joint-{j}',sector(a,48,375),point(a,380),
                (-tx,-ty,.92,.90,-4,0),(0,0,1,1,0,0),j*.18)
    elif number==99:
        for j,a in enumerate([-150,-90,-30,30,90,150]):
            angle=math.radians(a)
            add(f'prism-facet-{j}',sector(a,40,375),point(a,382),
                (-math.cos(angle)*3,-math.sin(angle)*3,.70,.95,0,0),
                (0,0,1,1,0,0))
    elif number==100:
        for j,a in enumerate([-135,-90,-45,0,45,90,135,180]):
            sign=-1 if j%2 else 1
            add(f'orbit-bracket-{j}',sector(a,34,376),point(a,380),
                (-sign*3,3,.84,.92,-sign*3,0),
                (0,0,1,1,0,0),0 if j%2 else .5)
    else:
        raise ValueError(number)
    return parts,used


def part_transform(part,t):
    q=.5-.5*math.cos(2*math.pi*(t+part['phase']))
    tx,ty,sx,sy,skew,rotation=[a+(b-a)*q for a,b in zip(part['closed'],part['opened'])]
    return (f'translate({tx:.5f}px,{ty:.5f}px) rotate({rotation:.5f}deg) '
            f'skewX({skew:.5f}deg) scale({sx:.6f},{sy:.6f})')
