"""Export edited artwork to identical 1024px avatar geometry; never creates archives.

Usage: python tools/prepare_profile_borders.py /path/to/edited-mappings /path/to/catalog.json
Requires Pillow, numpy and scipy. Original generated artwork is never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d, label, map_coordinates

SIZE = 1024
CENTER = 512
INNER_RADIUS = 358
SAFE_RADIUS = 480
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/profile-borders'


def export(source, destination):
    im = np.array(Image.open(source).convert('RGBA'), dtype=np.float32)
    h, w = im.shape[:2]
    if h != w:
        raise ValueError(f'Non-square source: {source}')
    alpha = im[:, :, 3]
    # Discard disconnected alpha dust, retaining real small ornament components.
    groups, _ = label(alpha > 100)
    counts = np.bincount(groups.ravel())
    keep = counts >= 12
    keep[0] = False
    alpha = np.where(keep[groups], alpha, 0)
    angles = np.arange(1440) * (2 * np.pi / 1440)
    radii = np.arange(w * .22, w * .495, .5)
    samples = map_coordinates(alpha, [h/2 + np.sin(angles)[:, None]*radii,
                                     w/2 + np.cos(angles)[:, None]*radii], order=1)
    opaque = samples > 150
    runs = opaque[:, :-3] & opaque[:, 1:-2] & opaque[:, 2:-1] & opaque[:, 3:]
    valid = runs.any(axis=1)
    if valid.mean() < .8:
        raise ValueError(f'Cannot reliably measure inner circle: {source}, {valid.mean():.2f}')
    inner = radii[runs.argmax(axis=1)]
    idx = np.arange(len(inner))
    inner[~valid] = np.interp(idx[~valid], np.r_[idx[valid]-len(inner), idx[valid], idx[valid]+len(inner)], np.tile(inner[valid], 3))
    inner = gaussian_filter1d(inner, 2, mode='wrap')
    yy, xx = np.indices((h, w))
    source_r = np.hypot(xx-w/2, yy-h/2)
    outer = float(np.max(source_r[alpha > 150]))
    scale = min(SIZE/w, (SAFE_RADIUS-INNER_RADIUS-3)/max(outer-float(inner.min()), 1))
    y, x = np.indices((SIZE, SIZE), dtype=np.float32)
    dx, dy = x+.5-CENTER, y+.5-CENTER
    radius = np.hypot(dx, dy)
    theta = np.mod(np.arctan2(dy, dx), 2*np.pi)
    angle_index = theta * len(inner)/(2*np.pi)
    local_inner = np.interp(angle_index, np.arange(len(inner)+1), np.r_[inner, inner[0]])
    mapped_r = local_inner + (radius-INNER_RADIUS-2)/scale
    sy = h/2 + np.sin(theta)*mapped_r
    sx = w/2 + np.cos(theta)*mapped_r
    coords = [sy, sx]
    a = map_coordinates(alpha, coords, order=1, mode='constant', cval=0)
    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    for k in range(3):
        premult = im[:, :, k]*alpha/255
        v = map_coordinates(premult, coords, order=1, mode='constant', cval=0)
        rgb[:, :, k] = np.divide(v*255, a, out=np.zeros_like(v), where=a>0)
    # A two-pixel continuation of each frame's own contour provides an identical,
    # actual inner edge at every angle, including designs with an irregular hole.
    edge_r = local_inner + 2
    edge_coords = [h/2 + np.sin(theta)*edge_r, w/2 + np.cos(theta)*edge_r]
    band = (radius >= INNER_RADIUS) & (radius < INNER_RADIUS+2)
    for k in range(3):
        colors = map_coordinates(im[:, :, k], edge_coords, order=1, mode='nearest')
        rgb[:, :, k][band] = colors[band]
    a[band] = 255
    a[(radius < INNER_RADIUS) | (radius > SAFE_RADIUS)] = 0
    # Clean invisible RGB as well as alpha, so transparent pixels remain neutral.
    rgb[a == 0] = 0
    result = np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 255)]).astype(np.uint8)
    result[result[:, :, 3] == 0, :3] = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(result).save(destination, format='PNG')
    return dict(source_median_inner_diameter_px=round(float(np.median(inner))*2, 3),
                source_size=w, export_scale=round(scale, 6))


def validate(path):
    im = Image.open(path)
    assert im.mode == 'RGBA' and im.size == (SIZE, SIZE), path
    a = np.array(im.getchannel('A'))
    y, x = np.indices(a.shape)
    r = np.hypot(x+.5-CENTER, y+.5-CENTER)
    inside = r < INNER_RADIUS
    band = (r >= INNER_RADIUS) & (r < INNER_RADIUS+2)
    assert not a[inside].any(), f'Center alpha: {path}'
    assert (a[band] == 255).all(), f'Inner contour mismatch: {path}'
    assert not a[r > SAFE_RADIUS].any(), f'Safe margin: {path}'
    return dict(size=[SIZE, SIZE], mode=im.mode, center=[CENTER, CENTER],
                inner_diameter_px=INNER_RADIUS*2, central_nontransparent_pixels=0,
                inner_contour_pass=True, safe_margin_pass=True,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mappings', type=Path)
    p.add_argument('catalog', type=Path)
    args = p.parse_args()
    catalog = json.loads(args.catalog.read_text())
    manifest = []
    for item in catalog:
        mapping = args.mappings / f"{item['id']:03}.json"
        if not mapping.exists():
            continue
        source = json.loads(mapping.read_text())['path']
        relative = f"{item['tier']}/profile_{item['id']:03}_{item['tier']}.png"
        dest = OUT / relative
        stats = export(source, dest)
        manifest.append({**item, 'file': relative, **stats, **validate(dest)})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'exported': len(manifest), 'validated': len(manifest), 'inner_diameter_px': INNER_RADIUS*2}))


if __name__ == '__main__':
    main()
