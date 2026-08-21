"""Render one local exploded audit image from frozen INDEX meshes.

No Onshape calls are made.  ITS bodies/actuators/fixed roots are visual audit
overlays, not CAD parts.  A tiny PIL/numpy software rasterizer keeps the render
reproducible without an OpenGL dependency.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_middle_prewrite as geom  # noqa: E402
import audit_its1105_physical_sample as physical  # noqa: E402
import audit_stock_6x6_switch as stock  # noqa: E402


WIDTH, HEIGHT = 1500, 1125
SS = 1
EXPLODE = 10.0
ROLLS = (0, 0, 90, 90)


def load_mesh(name: str) -> np.ndarray:
    path = ROOT / "cad_dump" / f"mesh_{name}.json"
    return np.asarray(json.loads(path.read_text(encoding="utf-8"))["tris"], dtype=float)


def obb_triangles(box) -> np.ndarray:
    vertices = geom.corners(box)
    faces = (
        (0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
        (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
        (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3),
    )
    return np.asarray([[vertices[i], vertices[j], vertices[k]] for i, j, k in faces])


def cylinder_triangles(point, axis, radius: float, front: float, rear: float, segments: int = 24):
    u, v, z = geom.frame(axis)
    top = np.asarray(point) - z * front
    bottom = np.asarray(point) - z * rear
    rings = []
    for center in (top, bottom):
        rings.append(np.asarray([
            center + radius * (math.cos(2 * math.pi * i / segments) * u + math.sin(2 * math.pi * i / segments) * v)
            for i in range(segments)
        ]))
    tris = []
    for i in range(segments):
        j = (i + 1) % segments
        tris.extend(((rings[0][i], rings[1][i], rings[1][j]), (rings[0][i], rings[1][j], rings[0][j])))
        tris.append((top, rings[0][j], rings[0][i]))
        tris.append((bottom, rings[1][i], rings[1][j]))
    return np.asarray(tris, dtype=float)


def shifted(triangles: np.ndarray, dx: float) -> np.ndarray:
    result = triangles.copy()
    result[:, :, 0] += dx
    return result


def project(points: np.ndarray, transform):
    camera, right, up, scale, offset_x, offset_y = transform
    rel = np.asarray(points) - camera
    return np.column_stack((rel @ right * scale + offset_x, -(rel @ up) * scale + offset_y))


def color_shade(base, normal, centroid, light_position):
    light = light_position - centroid
    light /= max(np.linalg.norm(light), 1e-12)
    diffuse = max(float(np.dot(normal, light)), 0.0)
    # Cool rim light improves separation on the blue shells.
    rim = max(float(np.dot(normal, geom.unit(np.asarray((-0.5, 0.2, 0.85))))), 0.0)
    factor = 0.34 + 0.56 * diffuse + 0.10 * rim
    return tuple(int(np.clip(channel * factor, 0, 255)) for channel in base)


def font(size: int, bold: bool = False):
    candidates = (
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def rasterize(objects):
    all_points = np.concatenate([tris.reshape(-1, 3) for tris, _ in objects], axis=0)
    target = np.asarray((0.0, 0.0, 1.0))
    camera = np.asarray((155.0, 185.0, 105.0))
    forward = geom.unit(target - camera)
    right = geom.unit(np.cross(forward, np.asarray((0.0, 0.0, 1.0))))
    up = geom.unit(np.cross(right, forward))
    rel = all_points - camera
    projected_x = rel @ right
    projected_y = rel @ up
    usable_w, usable_h = WIDTH * 0.82, HEIGHT * 0.82
    scale = min(usable_w / max(np.ptp(projected_x), 1e-9), usable_h / max(np.ptp(projected_y), 1e-9))
    offset_x = WIDTH / 2.0 - scale * (projected_x.min() + projected_x.max()) / 2.0
    offset_y = HEIGHT / 2.0 + scale * (projected_y.min() + projected_y.max()) / 2.0 + 24

    yy = np.linspace(0, 1, HEIGHT)[:, None]
    bg_top = np.asarray((12, 18, 27), dtype=float)
    bg_bottom = np.asarray((31, 39, 50), dtype=float)
    background = np.repeat((bg_top * (1 - yy[..., None]) + bg_bottom * yy[..., None]), WIDTH, axis=1).astype(np.uint8)
    image = background.copy()
    zbuf = np.full((HEIGHT, WIDTH), np.inf, dtype=np.float32)
    mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    light_position = np.asarray((100.0, 140.0, 180.0))

    for triangles, base in objects:
        rel = triangles - camera
        x = rel @ right
        y = rel @ up
        z = rel @ forward
        sx = x * scale + offset_x
        sy = -y * scale + offset_y
        for index in range(len(triangles)):
            px, py, pz = sx[index], sy[index], z[index]
            if np.any(pz <= 1e-6):
                continue
            xmin = max(int(math.floor(px.min())), 0)
            xmax = min(int(math.ceil(px.max())), WIDTH - 1)
            ymin = max(int(math.floor(py.min())), 0)
            ymax = min(int(math.ceil(py.max())), HEIGHT - 1)
            if xmin > xmax or ymin > ymax:
                continue
            x0, x1, x2 = px
            y0, y1, y2 = py
            denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(denominator) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
            w0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / denominator
            w1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / denominator
            w2 = 1.0 - w0 - w1
            inside = (w0 >= -1e-8) & (w1 >= -1e-8) & (w2 >= -1e-8)
            if not inside.any():
                continue
            depth = w0 * pz[0] + w1 * pz[1] + w2 * pz[2]
            region = zbuf[ymin:ymax + 1, xmin:xmax + 1]
            update = inside & (depth < region)
            if not update.any():
                continue
            tri = triangles[index]
            normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            norm = np.linalg.norm(normal)
            if norm < 1e-12:
                continue
            normal /= norm
            # Tessellation winding differs between source parts; two-sided
            # shading keeps the exploded audit render stable.
            to_light = light_position - tri.mean(axis=0)
            if np.dot(normal, to_light) < 0:
                normal = -normal
            shaded = color_shade(base, normal, tri.mean(axis=0), light_position)
            region[update] = depth[update]
            pixels = image[ymin:ymax + 1, xmin:xmax + 1]
            pixels[update] = shaded
            mask[ymin:ymax + 1, xmin:xmax + 1][update] = 255

    rgb = Image.fromarray(image, mode="RGB")
    silhouette = Image.fromarray(mask, mode="L")
    shadow = silhouette.filter(ImageFilter.GaussianBlur(18))
    shadow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shadow_layer.putalpha(shadow.point(lambda p: int(p * 0.22)))
    shadow_layer = shadow_layer.transform((WIDTH, HEIGHT), Image.AFFINE, (1, 0, -14, 0, 1, -16))
    result = Image.alpha_composite(rgb.convert("RGBA"), shadow_layer)
    result = Image.alpha_composite(result, rgb.convert("RGBA"))
    return result, (camera, right, up, scale, offset_x, offset_y)


def main():
    objects = []
    xray_bodies = []
    xray_roots = []
    # Explode the two frozen shell halves and their owned downstream parts.
    objects.append((shifted(load_mesh("INDEX_FINAL_JfD"), -EXPLODE), (69, 128, 166)))
    objects.append((shifted(load_mesh("INDEX_FINAL_JaD"), +EXPLODE), (87, 151, 181)))
    objects.append((shifted(load_mesh("INDEX_FINAL_RWID"), -EXPLODE), (203, 211, 217)))
    objects.append((shifted(load_mesh("INDEX_FINAL_RZKD"), +EXPLODE), (214, 151, 53)))

    for i in range(4):
        axis = geom.unit(geom.INDEX_AXES[i])
        shift_x = -EXPLODE if i < 3 else EXPLODE
        body = physical.physical_body_box(i, ROLLS[i], physical.BODY_X, physical.BODY_Y)
        body_tris = shifted(obb_triangles(body), shift_x)
        objects.append((body_tris, (225, 92, 47)))
        body_corners = geom.corners(body)
        body_corners[:, 0] += shift_x
        xray_bodies.append((f"I{i + 1}", body_corners))
        actuator = cylinder_triangles(
            geom.INDEX_CENTERS[i], axis, physical.ACTUATOR_D / 2.0,
            stock.INDEX_FRONT - physical.ACTUATOR_PROJECTION, stock.INDEX_FRONT,
        )
        objects.append((shifted(actuator, shift_x), (241, 126, 63)))
        roots = physical.physical_root_boxes(i, ROLLS[i], physical.BODY_X)
        for box in roots:
            objects.append((shifted(obb_triangles(box), shift_x), (205, 166, 75)))
            root_corners = geom.corners(box)
            root_corners[:, 0] += shift_x
            xray_roots.append(root_corners)
        # Current cap solids are exact 7.6 x 7.6 x 4 cuboids in the old-normal frame.
        cap = geom.obb(geom.INDEX_CENTERS[i], geom.unit(stock.INDEX_NORMALS[i]), 7.6, 4.0, -1.4)
        objects.append((shifted(obb_triangles(cap), shift_x), (48, 54, 64)))

    render, projection = rasterize(objects)
    xray = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    xdraw = ImageDraw.Draw(xray)
    edges = ((0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7))
    for corners in xray_roots:
        pts = project(corners, projection)
        for a, b in edges:
            xdraw.line((tuple(pts[a]), tuple(pts[b])), fill=(236, 188, 72, 150), width=2)
    label_font = font(17, True)
    for name, corners in xray_bodies:
        pts = project(corners, projection)
        for a, b in edges:
            xdraw.line((tuple(pts[a]), tuple(pts[b])), fill=(255, 102, 48, 220), width=3)
        centre = pts.mean(axis=0)
        xdraw.rounded_rectangle((centre[0] - 17, centre[1] - 13, centre[0] + 17, centre[1] + 13), radius=7, fill=(16, 21, 29, 215), outline=(255, 112, 58, 240), width=2)
        box = xdraw.textbbox((0, 0), name, font=label_font)
        xdraw.text((centre[0] - (box[2] - box[0]) / 2, centre[1] - (box[3] - box[1]) / 2 - 2), name, font=label_font, fill=(255, 225, 211, 255))
    render = Image.alpha_composite(render, xray)
    draw = ImageDraw.Draw(render)
    title_font = font(40, True)
    sub_font = font(22, False)
    small_font = font(18, False)
    draw.text((48, 38), "ONEGRIP PLAY  /  INDEX FINAL", font=title_font, fill=(239, 244, 248, 255))
    draw.text((50, 88), "ITS-1105 PHYSICAL SAMPLE  /  0-0-90-90 CARDINAL AUDIT", font=sub_font, fill=(167, 185, 199, 255))
    draw.rounded_rectangle((48, HEIGHT - 108, 750, HEIGHT - 42), radius=14, fill=(10, 15, 22, 205), outline=(88, 104, 118, 220), width=2)
    draw.ellipse((72, HEIGHT - 84, 94, HEIGHT - 62), fill=(225, 92, 47, 255))
    draw.text((106, HEIGHT - 90), "ITS housing / actuator", font=small_font, fill=(225, 232, 238, 255))
    draw.ellipse((326, HEIGHT - 84, 348, HEIGHT - 62), fill=(205, 166, 75, 255))
    draw.text((360, HEIGHT - 90), "fixed roots", font=small_font, fill=(225, 232, 238, 255))
    draw.ellipse((490, HEIGHT - 84, 512, HEIGHT - 62), fill=(214, 151, 53, 255))
    draw.text((524, HEIGHT - 90), "RZKD", font=small_font, fill=(225, 232, 238, 255))
    draw.text((WIDTH - 345, HEIGHT - 64), "CAD WRITE 0  |  LOCAL OVERLAY", font=small_font, fill=(157, 174, 188, 255))

    output_dir = ROOT / "renders"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "index_final_its1105_physical_sample_render.png"
    render.convert("RGB").save(output, quality=95)
    print(f"wrote {output} {render.size}")


if __name__ == "__main__":
    main()
