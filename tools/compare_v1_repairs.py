"""Make review sheets from the frozen first-upload PNGs and repaired PNGs."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/profile-borders'
OUT=ROOT/'assets/profile-borders-v1-repaired'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('/tmp/v1-comparison'));args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    items=json.loads((OUT/'manifest.json').read_text())
    for start in range(0,100,20):
        rows=[a for a in items if start<a['id']<=start+20]
        sheet=Image.new('RGB',(1440,280*((len(rows)+3)//4)),(224,229,236));draw=ImageDraw.Draw(sheet)
        for i,item in enumerate(rows):
            x=(i%4)*360;y=(i//4)*280
            draw.text((x+5,y+8),f"{item['id']:03} / 844e7c2             REPAIR",fill='#243044')
            for j,path in enumerate([BASE/item['file'],OUT/item['file']]):
                image=Image.open(path).convert('RGBA');image.thumbnail((176,240));sheet.paste(image,(x+j*180,y+42),image)
        if rows:sheet.save(args.output/f"compare-{start+1:03}-{start+20:03}.jpg",quality=94)
    print(f'{len(items)} first-upload comparisons')

if __name__=='__main__':main()
