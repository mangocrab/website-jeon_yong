"""Validate the shipped PNGs directly, including their actual inner contours."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'assets/profile-borders'
EXPECTED = {'normal': 30, 'premium': 25, 'rare': 20, 'epic': 15, 'legendary': 10}


def main():
    items = json.loads((ROOT/'manifest.json').read_text())
    assert len(items) == 100
    assert {a['id'] for a in items} == set(range(1, 101))
    assert Counter(a['tier'] for a in items) == EXPECTED
    assert len(list(ROOT.glob('*/*.png'))) == 100
    y, x = np.indices((1024, 1024))
    radius = np.hypot(x+.5-512, y+.5-512)
    circle = radius < 358
    contour = (radius >= 358) & (radius < 360)
    hashes = set()
    for item in items:
        p = ROOT/item['file']
        assert p.name == f"profile_{item['id']:03}_{item['tier']}.png"
        with Image.open(p) as im:
            assert im.format == 'PNG' and im.mode == 'RGBA' and im.size == (1024, 1024), p
            alpha = np.array(im.getchannel('A'))
        assert (alpha[circle] == 0).all(), f'Nontransparent center: {p}'
        assert (alpha[contour] == 255).all(), f'Different actual inner edge: {p}'
        assert (alpha[radius > 480] == 0).all(), f'Clipped margin: {p}'
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        assert digest == item['sha256'], f'Manifest mismatch: {p}'
        assert digest not in hashes, f'Duplicate PNG: {p}'
        hashes.add(digest)
    assert not list(ROOT.rglob('*.zip'))
    print('PASS: 100 individual RGBA PNGs; correct tier counts; identical 716px inner contours; transparent centers; 32px safe margins; unique files; SHA-256 matches.')


if __name__ == '__main__':
    main()
