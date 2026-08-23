"""Render OLD vs NEW THUMB module overlay from local frozen meshes.

No Onshape or network call is made.  The new module is the exact cached
original geometry plus the approved rigid translation (0,+5.5,-6) mm.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT = 1500, 1100
TRANSLATION = np.asarray((0.0, 5.5, -6.0), dtype=float)

INDEX = np.asarray((
    (-22.224, -17.494, 9.0), (-15.970, -26.208, 9.0),
    (-5.496, -29.325, 9.0), (5.496, -29.325, 9.0),
), dtype=float)
MIDDLE = np.asarray((
    (-19.835372, -0.614992, -11.125), (-12.899418, -8.744828, -14.125),
    (-3.537874, -14.413709, -11.125), (7.444328, -13.569623, -11.125),
), dtype=float)
CAP_NAMES = (
    "Button_wide_1", "Button_side_1", "Button_corner_1", "Button_corner_2",
    "Button_side_2", "Button_wide_2", "Button_middle_1", "Button_middle_2",
)


def unit(vector: np.ndarray) -> np.ndarray:
    return vector / max(float(np.linalg.norm(vector)), 1e-12)


def load(name: str) -> np.ndarray:
    path = ROOT / "cad_dump" / f"mesh_{name}.json"
    return np.asarray(json.loads(path.read_text(encoding="utf-8"))["tris"], dtype=float)


def cube(center: np.ndarray, size: float) -> np.ndarray:
    h = size / 2.0
    v = np.asarray([
        center + (sx * h, sy * h, sz * h)
        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
    ])
    f = ((0,1,3),(0,3,2),(4,6,7),(4,7,5),(0,4,5),(0,5,1),
         (2,3,7),(2,7,6),(0,2,6),(0,6,4),(1,5,7),(1,7,3))
    return np.asarray([[v[a], v[b], v[c]] for a,b,c in f], dtype=float)


def cylinder(a: np.ndarray, b: np.ndarray, radius: float, segments: int = 30) -> np.ndarray:
    axis = unit(b - a)
    seed = np.asarray((0.0, 0.0, 1.0)) if abs(axis[2]) < 0.9 else np.asarray((0.0, 1.0, 0.0))
    u = unit(np.cross(axis, seed)); v = unit(np.cross(axis, u))
    ring_a = np.asarray([a + radius * (math.cos(2*math.pi*i/segments)*u + math.sin(2*math.pi*i/segments)*v) for i in range(segments)])
    ring_b = ring_a + (b - a)
    tris = []
    for i in range(segments):
        j = (i + 1) % segments
        tris += [(ring_a[i],ring_b[i],ring_b[j]),(ring_a[i],ring_b[j],ring_a[j]),
                 (a,ring_a[j],ring_a[i]),(b,ring_b[i],ring_b[j])]
    return np.asarray(tris, dtype=float)


def font(size: int, bold: bool = False):
    paths = (
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    )
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def camera_transform():
    camera = np.asarray((92.0, -176.0, 72.0))
    target = np.asarray((0.0, -15.0, 20.0))
    forward = unit(target - camera)
    right = unit(np.cross(forward, np.asarray((0.0, 0.0, 1.0))))
    up = unit(np.cross(right, forward))
    scale = 10.0
    return camera, right, up, forward, scale, WIDTH * 0.55, HEIGHT * 0.54


def project(points: np.ndarray, tr):
    camera, right, up, _forward, scale, ox, oy = tr
    rel = np.asarray(points) - camera
    return np.column_stack((rel @ right * scale + ox, -(rel @ up) * scale + oy))


def shade(base, normal, centroid):
    light = unit(np.asarray((70.0, -130.0, 150.0)) - centroid)
    diffuse = max(float(normal @ light), 0.0)
    factor = 0.32 + 0.68 * diffuse
    return tuple(int(np.clip(channel * factor, 0, 255)) for channel in base)


def rasterize(objects, tr, transparent: bool = False):
    yy = np.linspace(0.0, 1.0, HEIGHT)[:, None, None]
    top = np.asarray((11, 17, 25), dtype=float)[None, None, :]
    bottom = np.asarray((35, 42, 50), dtype=float)[None, None, :]
    rgb = np.repeat(top * (1.0 - yy) + bottom * yy, WIDTH, axis=1).astype(np.uint8)
    zbuf = np.full((HEIGHT, WIDTH), np.inf, dtype=np.float32)
    mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    camera, right, up, forward, scale, ox, oy = tr
    for triangles, base in objects:
        rel = triangles - camera
        sx = rel @ right * scale + ox
        sy = -(rel @ up) * scale + oy
        sz = rel @ forward
        for i, tri in enumerate(triangles):
            px, py, pz = sx[i], sy[i], sz[i]
            if np.any(pz <= 1e-5):
                continue
            xmin, xmax = max(int(np.floor(px.min())),0), min(int(np.ceil(px.max())),WIDTH-1)
            ymin, ymax = max(int(np.floor(py.min())),0), min(int(np.ceil(py.max())),HEIGHT-1)
            if xmin > xmax or ymin > ymax:
                continue
            x0,x1,x2 = px; y0,y1,y2 = py
            den = (y1-y2)*(x0-x2) + (x2-x1)*(y0-y2)
            if abs(den) < 1e-10:
                continue
            gx,gy = np.meshgrid(np.arange(xmin,xmax+1)+0.5, np.arange(ymin,ymax+1)+0.5)
            w0 = ((y1-y2)*(gx-x2)+(x2-x1)*(gy-y2))/den
            w1 = ((y2-y0)*(gx-x2)+(x0-x2)*(gy-y2))/den
            w2 = 1.0-w0-w1
            inside = (w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)
            depth = w0*pz[0]+w1*pz[1]+w2*pz[2]
            region = zbuf[ymin:ymax+1,xmin:xmax+1]
            update = inside & (depth < region)
            if not update.any():
                continue
            normal = np.cross(tri[1]-tri[0], tri[2]-tri[0])
            if np.linalg.norm(normal) < 1e-12:
                continue
            normal = unit(normal)
            if normal @ (np.asarray((70.0,-130.0,150.0))-tri.mean(0)) < 0:
                normal = -normal
            region[update] = depth[update]
            pixels = rgb[ymin:ymax+1,xmin:xmax+1]
            pixels[update] = shade(base, normal, tri.mean(0))
            mask[ymin:ymax+1,xmin:xmax+1][update] = 255
    image = Image.fromarray(rgb, "RGB").convert("RGBA")
    if transparent:
        image.putalpha(Image.fromarray(mask, "L").point(lambda p: int(p * 0.94)))
        return image
    shadow = Image.fromarray(mask, "L").filter(ImageFilter.GaussianBlur(15))
    layer = Image.new("RGBA", image.size, (0,0,0,0)); layer.putalpha(shadow.point(lambda p:int(p*0.18)))
    layer = layer.transform(image.size, Image.AFFINE, (1,0,-12,0,1,-12))
    return Image.alpha_composite(Image.alpha_composite(image, layer), image)


def convex_hull(points: np.ndarray) -> list[tuple[float, float]]:
    pts = sorted(set((float(x), float(y)) for x,y in points))
    if len(pts) <= 1:
        return pts
    def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]
    for p in pts:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0: lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(pts):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0: upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def dashed_polygon(draw: ImageDraw.ImageDraw, polygon, color, width=3, dash=10):
    if len(polygon) < 2:
        return
    for p0,p1 in zip(polygon, polygon[1:]+polygon[:1]):
        p0=np.asarray(p0); p1=np.asarray(p1); length=float(np.linalg.norm(p1-p0))
        if length < 1e-6: continue
        direction=(p1-p0)/length
        for start in np.arange(0,length,dash*2):
            end=min(start+dash,length)
            a=p0+direction*start; b=p0+direction*end
            draw.line((tuple(a),tuple(b)),fill=color,width=width)


def main():
    tr = camera_transform()
    shells = [load("INDEX_FINAL_JfD"), load("INDEX_FINAL_JaD")]
    old_backplate = load("Backplate")
    new_backplate = old_backplate + TRANSLATION
    old_caps = [load(name) for name in CAP_NAMES]
    new_caps = [tri + TRANSLATION for tri in old_caps]

    # The current exact shell mesh cache is kept dark so both control rows and
    # the interface remain readable.  New shell openings are represented by
    # the exact 36-face interface datum translated with the Backplate.
    objects = [(shells[0], (54,88,112)), (shells[1], (63,100,124))]
    objects += [(cube(center, 7.6), (62,157,194)) for center in INDEX]
    objects += [(cube(center, 8.0), (92,180,139)) for center in MIDDLE]
    objects += [(cylinder(np.asarray((-6,-14.45,23.07)),np.asarray((10,-14.45,23.07)),3.5), (195,62,62))]
    image = rasterize(objects, tr)
    xray_module = [(new_backplate, (190,135,55))]
    xray_module += [(tri, (239,119,48)) for tri in new_caps]
    image = Image.alpha_composite(image, rasterize(xray_module, tr, transparent=True))
    overlay = Image.new("RGBA", image.size, (0,0,0,0)); draw = ImageDraw.Draw(overlay)

    # Original location is a magenta dashed ghost.  The relocated position is
    # exact solid geometry, not a reconstructed approximation.
    dashed_polygon(draw, convex_hull(project(old_backplate.reshape(-1,3),tr)), (232,98,182,230), 4, 12)
    for triangles in old_caps:
        dashed_polygon(draw, convex_hull(project(triangles.reshape(-1,3),tr)), (245,132,207,230), 3, 9)

    title = font(39, True); sub = font(22); label = font(19, True); small = font(17)
    draw.text((46,34), "ONEGRIP PLAY / THUMB MODULE RESEAT", font=title, fill=(242,246,249,255))
    draw.text((48,84), "OLD GHOST  →  RIGID TRANSLATION (0, +5.5, -6.0) mm  →  NEW SEATED MODULE", font=sub, fill=(175,193,205,255))

    # Labels point into the control region.
    labels = [
        ("INDEX row", INDEX.mean(0), (62,157,194,255), (1040,205)),
        ("MIDDLE row", MIDDLE.mean(0), (92,180,139,255), (1040,268)),
        ("NEW shell interface / Backplate", new_backplate.reshape(-1,3).mean(0), (221,163,70,255), (930,365)),
        ("Screw B  /  8.584 mm", np.asarray((2,-14.45,23.07)), (218,74,74,255), (1010,448)),
    ]
    for text, world, color, box in labels:
        p=project(np.asarray([world]),tr)[0]
        draw.line((tuple(p),box),fill=color,width=3)
        draw.ellipse((p[0]-5,p[1]-5,p[0]+5,p[1]+5),fill=color)
        draw.rounded_rectangle((box[0]-12,box[1]-10,box[0]+340,box[1]+32),radius=9,fill=(10,15,22,215),outline=color,width=2)
        draw.text((box[0],box[1]-4),text,font=label,fill=(236,241,245,255))

    draw.rounded_rectangle((46,HEIGHT-132,1080,HEIGHT-42),radius=15,fill=(10,15,22,215),outline=(90,108,120,220),width=2)
    legend = (("OLD position",(232,98,182,255)),("NEW thumb",(239,119,48,255)),("INDEX",(62,157,194,255)),("MIDDLE",(92,180,139,255)),("Screw B",(218,74,74,255)))
    x=70
    for text,color in legend:
        draw.ellipse((x,HEIGHT-101,x+20,HEIGHT-81),fill=color)
        draw.text((x+30,HEIGHT-107),text,font=small,fill=(224,232,238,255)); x+=190
    draw.text((70,HEIGHT-72),"30 solids unchanged  |  36 original opening faces relocated  |  no pedestal / no added fragment",font=small,fill=(160,181,194,255))
    image = Image.alpha_composite(image, overlay)
    out = ROOT / "renders" / "thumb_reseat_old_new_overlay.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out, quality=96)
    print(f"wrote {out} {image.size}")


if __name__ == "__main__":
    main()
