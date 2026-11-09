"""Expose the actual independently animated PNGs, without flattening or slicing."""
from pathlib import Path
import json,base64,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/profile-borders-natural';NS='{http://www.w3.org/2000/svg}'
for n in range(91,101):
 svg=E.parse(OUT/f'legendary/profile_{n:03}_legendary.svg').getroot();parents={c:p for p in svg.iter() for c in p};folder=OUT/'layers'/'legendary'/f'{n:03}';folder.mkdir(exist_ok=True,parents=True);records=[];seen={}
 for e in svg.iter(NS+'image'):
  ancestors=[];p=parents.get(e)
  while p is not None:
   ancestors.append(p);p=parents.get(p)
  if any(p.tag==NS+'mask' for p in ancestors):continue
  cls=e.get('class','fixed-frame');stem=cls.split()[-1];seen[stem]=seen.get(stem,0)+1;name=stem+('-right' if seen[stem]>1 else '')+'.png';(folder/name).write_bytes(base64.b64decode(e.get('href').split(',',1)[1]))
  records.append(dict(file=name,class_name=cls,moving=cls!='fixed-frame',x=float(e.get('x','0')),y=float(e.get('y','0')),render_width=float(e.get('width')),render_height=float(e.get('height')),ancestors=[dict(p.attrib) for p in ancestors if p.tag!=NS+'svg']))
 (folder/'rig.json').write_text(json.dumps(dict(id=n,canvas=[1280,1280],parts=records,css=svg.find(NS+'style').text),ensure_ascii=False,indent=2)+'\n')
print('Exported actual PNG layers and rig information for 10 legendary borders')
