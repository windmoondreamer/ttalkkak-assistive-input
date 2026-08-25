from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import ConvexHull

from build123d import CenterOf, Vector, import_step


ROOT = Path(r"C:\Users\User\Desktop\OneGrip-Play")
REV = ROOT / "thumb_inner_housing_lab" / "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE"
OUT = ROOT / "codex_audits" / "C07_FDM_PRINTABILITY"
STEP = REV / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
STL = REV / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.stl"
BUILDER = REV / "10_scripts" / "i10_c07_refine.py"
META = REV / "07_prototype" / "i10_c07.json"
PROJECT_SCRIPTS = REV / "10_scripts"

COS45 = math.cos(math.radians(45.0))


def unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def vec(v) -> np.ndarray:
    return np.array([float(v.X), float(v.Y), float(v.Z)])


def read_binary_stl(path: Path):
    raw = path.read_bytes()
    if len(raw) < 84:
        raise ValueError("STL shorter than binary header")
    n = struct.unpack_from("<I", raw, 80)[0]
    expected = 84 + 50 * n
    if len(raw) != expected:
        raise ValueError(f"not a canonical binary STL: expected {expected}, got {len(raw)}")
    rec = np.frombuffer(raw, dtype=np.dtype([
        ("normal", "<f4", (3,)), ("vertices", "<f4", (9,)), ("attr", "<u2")
    ]), offset=84, count=n)
    return rec["vertices"].astype(float).reshape(-1, 3, 3), rec["normal"].astype(float)


def triangle_geometry(T: np.ndarray):
    cross = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    twice = np.linalg.norm(cross, axis=1)
    area = 0.5 * twice
    normals = np.zeros_like(cross)
    good = twice > 1.0e-14
    normals[good] = cross[good] / twice[good, None]
    return normals, area


def topology_metrics(T: np.ndarray, stored_normals: np.ndarray):
    # Vertex welding is only for topology interrogation; source coordinates are untouched.
    q = np.round(T.reshape(-1, 3) / 1.0e-6).astype(np.int64)
    uq, inv = np.unique(q, axis=0, return_inverse=True)
    F = inv.reshape(-1, 3)
    E_dir = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=0)
    E = np.sort(E_dir, axis=1)
    ue, ei, ec = np.unique(E, axis=0, return_inverse=True, return_counts=True)
    open_edges = int(np.sum(ec == 1))
    nonmanifold_edges = int(np.sum(ec > 2))

    edge_faces: dict[int, list[int]] = defaultdict(list)
    for k, eidx in enumerate(ei):
        edge_faces[int(eidx)].append(int(k % len(F)))
    adj = [[] for _ in range(len(F))]
    for faces in edge_faces.values():
        if len(faces) == 2:
            a, b = faces
            adj[a].append(b)
            adj[b].append(a)
    comps = []
    seen = np.zeros(len(F), bool)
    _, area = triangle_geometry(T)
    for start in range(len(F)):
        if seen[start]:
            continue
        todo = [start]
        seen[start] = True
        ids = []
        while todo:
            i = todo.pop()
            ids.append(i)
            for j in adj[i]:
                if not seen[j]:
                    seen[j] = True
                    todo.append(j)
        comps.append({"triangles": len(ids), "areaMm2": float(area[ids].sum())})
    comps.sort(key=lambda x: -x["areaMm2"])

    bad_oriented_edges = 0
    for eidx, count in enumerate(ec):
        if count != 2:
            continue
        rows = np.nonzero(ei == eidx)[0]
        signs = []
        for row in rows:
            a, b = E_dir[row]
            signs.append(1 if a < b else -1)
        if signs[0] == signs[1]:
            bad_oriented_edges += 1

    calc_n, tri_area = triangle_geometry(T)
    stored_len = np.linalg.norm(stored_normals, axis=1)
    stored_unit = np.zeros_like(stored_normals)
    nz = stored_len > 1.0e-12
    stored_unit[nz] = stored_normals[nz] / stored_len[nz, None]
    normal_dot = np.einsum("ij,ij->i", calc_n, stored_unit)
    normal_mismatch = int(np.sum((tri_area > 1.0e-12) & (normal_dot < 0.99)))
    degenerate = int(np.sum(tri_area <= 1.0e-10))
    signed_volume = float(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0)

    return {
        "triangles": int(len(T)),
        "uniqueVertices": int(len(uq)),
        "openEdges": open_edges,
        "nonManifoldEdges": nonmanifold_edges,
        "badOrientedSharedEdges": bad_oriented_edges,
        "connectedComponents": len(comps),
        "components": comps,
        "degenerateTriangles": degenerate,
        "storedNormalMismatches": normal_mismatch,
        "signedVolumeMm3": signed_volume,
        "absoluteVolumeMm3": abs(signed_volume),
        "faceIndex": F,
    }


def segment_triangle_intersection(p0, p1, tri, eps=1.0e-8):
    d = p1 - p0
    e1 = tri[1] - tri[0]
    e2 = tri[2] - tri[0]
    h = np.cross(d, e2)
    a = float(e1 @ h)
    if abs(a) < eps:
        return False
    f = 1.0 / a
    s = p0 - tri[0]
    u = f * float(s @ h)
    if u <= eps or u >= 1.0 - eps:
        return False
    q = np.cross(s, e1)
    v = f * float(d @ q)
    if v <= eps or u + v >= 1.0 - eps:
        return False
    t = f * float(e2 @ q)
    return eps < t < 1.0 - eps


def orient2(a, b, c):
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def seg2_cross(a, b, c, d, eps=1.0e-10):
    o1, o2, o3, o4 = orient2(a, b, c), orient2(a, b, d), orient2(c, d, a), orient2(c, d, b)
    return ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps)) and ((o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps))


def point_in_tri2(p, t, eps=1.0e-10):
    o = [orient2(t[i], t[(i + 1) % 3], p) for i in range(3)]
    return (all(x >= -eps for x in o) or all(x <= eps for x in o)) and all(abs(x) > eps for x in o)


def coplanar_overlap(a, b, normal):
    drop = int(np.argmax(np.abs(normal)))
    aa = np.delete(a, drop, axis=1)
    bb = np.delete(b, drop, axis=1)
    for i in range(3):
        for j in range(3):
            if seg2_cross(aa[i], aa[(i + 1) % 3], bb[j], bb[(j + 1) % 3]):
                return True
    return point_in_tri2(aa[0], bb) or point_in_tri2(bb[0], aa)


def self_intersections(T: np.ndarray, F: np.ndarray, limit=50):
    lo = T.min(axis=1)
    hi = T.max(axis=1)
    nrm, area = triangle_geometry(T)
    out = []
    for i in range(len(T) - 1):
        cand = np.nonzero(np.all(hi[i] + 1e-8 >= lo[i + 1:], axis=1) & np.all(hi[i + 1:] + 1e-8 >= lo[i], axis=1))[0] + i + 1
        if not len(cand):
            continue
        vi = set(F[i].tolist())
        for j in cand:
            if vi.intersection(F[j].tolist()):
                continue
            if area[i] <= 1e-12 or area[j] <= 1e-12:
                continue
            parallel = abs(float(nrm[i] @ nrm[j])) > 1.0 - 1e-8
            cop = parallel and abs(float((T[j, 0] - T[i, 0]) @ nrm[i])) < 1e-7
            hit = coplanar_overlap(T[i], T[j], nrm[i]) if cop else False
            if not hit:
                for k in range(3):
                    if segment_triangle_intersection(T[i, k], T[i, (k + 1) % 3], T[j]):
                        hit = True
                        break
            if not hit:
                for k in range(3):
                    if segment_triangle_intersection(T[j, k], T[j, (k + 1) % 3], T[i]):
                        hit = True
                        break
            if hit:
                out.append([int(i), int(j)])
                if len(out) >= limit:
                    return out, True
    return out, False


def basis_for_up(up: np.ndarray, points: np.ndarray):
    up = unit(up)
    centered = points - points.mean(axis=0)
    lateral = centered - np.outer(centered @ up, up)
    cov = lateral.T @ lateral
    vals, dirs = np.linalg.eigh(cov)
    x = dirs[:, np.argmax(vals)]
    x = unit(x - up * float(x @ up))
    y = unit(np.cross(up, x))
    x = unit(np.cross(y, up))
    return x, y, up


def local_triangles(T: np.ndarray, up: np.ndarray):
    x, y, z = basis_for_up(up, T.reshape(-1, 3))
    R = np.column_stack([x, y, z])
    return T @ R, R


def component_groups(indices: np.ndarray, F: np.ndarray):
    selected = set(int(i) for i in indices)
    vert_faces = defaultdict(list)
    for i in selected:
        for v in F[i]:
            vert_faces[int(v)].append(i)
    adj = defaultdict(set)
    for faces in vert_faces.values():
        for a in faces:
            adj[a].update(faces)
    groups = []
    while selected:
        start = selected.pop()
        todo = [start]
        group = [start]
        while todo:
            a = todo.pop()
            for b in adj[a]:
                if b in selected:
                    selected.remove(b)
                    todo.append(b)
                    group.append(b)
        groups.append(group)
    return groups


def ray_hit_distances(T: np.ndarray, origin: np.ndarray, direction: np.ndarray):
    d = unit(direction)
    e1 = T[:, 1] - T[:, 0]
    e2 = T[:, 2] - T[:, 0]
    h = np.cross(np.broadcast_to(d, e2.shape), e2)
    a = np.einsum("ij,ij->i", e1, h)
    good = np.abs(a) > 1.0e-10
    f = np.zeros_like(a)
    f[good] = 1.0 / a[good]
    s = origin - T[:, 0]
    u = f * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, e1)
    v = f * (q @ d)
    tt = f * np.einsum("ij,ij->i", e2, q)
    hit = good & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9) & (tt > 0.05)
    return np.sort(tt[hit])


def orientation_metric(T: np.ndarray, F: np.ndarray, up: np.ndarray, label: str, com_world: np.ndarray, details=True):
    Tl, R = local_triangles(T, up)
    n, area = triangle_geometry(Tl)
    vz = Tl[:, :, 2]
    z0, z1 = float(vz.min()), float(vz.max())
    ndot = n[:, 2]
    bed = (ndot < -0.95) & (vz.max(axis=1) <= z0 + 0.05)
    need = (ndot < -COS45) & ~bed
    bed_ids = np.nonzero(bed)[0]
    support_ids = np.nonzero(need)[0]
    bed_groups = component_groups(bed_ids, F) if len(bed_ids) else []
    bed_group_areas = sorted([float(area[g].sum()) for g in bed_groups], reverse=True)
    groups = component_groups(support_ids, F) if details and len(support_ids) else []
    regions = []
    for g in groups:
        a = float(area[g].sum())
        if a < 0.05:
            continue
        p = Tl[g, :, :2].reshape(-1, 2)
        region_centroid = np.average(Tl[g].mean(axis=1), axis=0, weights=np.maximum(area[g], 1e-12))
        clear_best = 0
        clear_3d_best = 0
        down_open = False
        field_local = Field(Tl)
        # Probe several points just below the supported face; a region is called
        # trapped only if none of 16 horizontal tool directions escapes at any probe.
        ga = area[g]
        probe_ids = np.asarray(g)[np.argsort(ga)[-min(5, len(g)):]]
        for pi in probe_ids:
            face_point = Tl[pi].mean(axis=0)
            origin = face_point + n[pi] * 0.20
            hh = field_local.hits(float(face_point[0]) + 3.1e-7, float(face_point[1]) + 1.9e-7)
            lower_tops = [hh[k + 1] for k in range(0, len(hh) - 1, 2) if hh[k + 1] < face_point[2] - 0.08]
            if not lower_tops:
                down_open = True
            clear = 0
            clear_3d = 0
            for theta in np.arange(0.0, 2.0 * math.pi, math.pi / 8.0):
                direction = np.array([math.cos(theta), math.sin(theta), 0.0])
                if len(ray_hit_distances(Tl, origin, direction)) == 0:
                    clear += 1
                for elev_deg in (-25.0, -50.0, -75.0):
                    elev = math.radians(elev_deg)
                    direction3 = np.array([math.cos(theta) * math.cos(elev), math.sin(theta) * math.cos(elev), math.sin(elev)])
                    if len(ray_hit_distances(Tl, origin, direction3)) == 0:
                        clear_3d += 1
            clear_best = max(clear_best, clear)
            clear_3d_best = max(clear_3d_best, clear_3d)
        regions.append({
            "triangleIds": [int(q) for q in g],
            "areaMm2": a,
            "spanXmm": float(np.ptp(p[:, 0])),
            "spanYmm": float(np.ptp(p[:, 1])),
            "maxSpanMm": float(max(np.ptp(p[:, 0]), np.ptp(p[:, 1]))),
            "meanHeightMm": float(Tl[g, :, 2].mean() - z0),
            "centroidLocalMm": [float(region_centroid[0]), float(region_centroid[1]), float(region_centroid[2] - z0)],
            "accessClearBearingsOf16": int(clear_best),
            "accessClearDownwardRaysOf48": int(clear_3d_best),
            "openDownwardToBed": bool(down_open),
            "trapped": bool(clear_best == 0 and clear_3d_best == 0 and not down_open),
        })
    regions.sort(key=lambda r: -r["areaMm2"])
    bed_pts = Tl[bed_ids].reshape(-1, 3)[:, :2] if len(bed_ids) else np.zeros((0, 2))
    tipping_margin = 0.0
    bed_span = [0.0, 0.0]
    com_local = com_world @ R
    if len(bed_pts) >= 3:
        bed_span = [float(np.ptp(bed_pts[:, 0])), float(np.ptp(bed_pts[:, 1]))]
        try:
            hull = ConvexHull(bed_pts)
            eq = hull.equations
            tipping_margin = float(np.min(-(eq[:, :2] @ com_local[:2] + eq[:, 2]) / np.linalg.norm(eq[:, :2], axis=1)))
        except Exception:
            tipping_margin = 0.0
    return {
        "label": label,
        "upWorld": unit(up).tolist(),
        "heightMm": z1 - z0,
        "bedContactAreaMm2": float(area[bed].sum()),
        "bedTriangleComponents": len(bed_groups),
        "bedTriangleComponentAreasMm2": bed_group_areas,
        "bedSpanMm": bed_span,
        "comTippingMarginMm": tipping_margin,
        "supportAreaMm2": float(area[need].sum()),
        "supportFraction": float(area[need].sum() / area.sum()),
        "supportRegionCount": len(regions),
        "trappedSupportRegions": int(sum(1 for r in regions if r["trapped"])),
        "largestSupportRegions": regions[:10],
        "bedIds": bed_ids,
        "supportIds": support_ids,
        "localTriangles": Tl,
        "rotation": R,
    }


class Field:
    def __init__(self, T: np.ndarray):
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        self.a, self.e1, self.e2 = a, b - a, c - a
        self.x0, self.x1 = T[:, :, 0].min(axis=1), T[:, :, 0].max(axis=1)
        self.y0, self.y1 = T[:, :, 1].min(axis=1), T[:, :, 1].max(axis=1)
        self.det = self.e1[:, 0] * self.e2[:, 1] - self.e1[:, 1] * self.e2[:, 0]
        self.ok = np.abs(self.det) > 1.0e-14
        self.order = np.argsort(self.x0)
        self.x0s = self.x0[self.order]

    def hits(self, x, y):
        cand = self.order[:np.searchsorted(self.x0s, x, side="right")]
        cand = cand[self.x1[cand] >= x]
        sel = cand[(self.y0[cand] <= y) & (self.y1[cand] >= y)]
        if not len(sel):
            return np.zeros(0)
        A, E1, E2 = self.a[sel], self.e1[sel], self.e2[sel]
        d, o = self.det[sel], self.ok[sel]
        dx, dy = x - A[:, 0], y - A[:, 1]
        s = np.where(o, (dx * E2[:, 1] - dy * E2[:, 0]) / np.where(o, d, 1.0), -1.0)
        t = np.where(o, (E1[:, 0] * dy - E1[:, 1] * dx) / np.where(o, d, 1.0), -1.0)
        good = o & (s >= -1e-10) & (t >= -1e-10) & (s + t <= 1.0 + 1e-10)
        if not good.any():
            return np.zeros(0)
        h = np.sort(A[good, 2] + s[good] * E1[good, 2] + t[good] * E2[good, 2])
        keep = np.ones(len(h), bool)
        keep[1:] = np.diff(h) > 1.0e-6
        return h[keep]


def rasterize_triangles(Tl: np.ndarray, ids: np.ndarray, pitch: float, z_mode=False):
    x0, x1 = float(Tl[:, :, 0].min()), float(Tl[:, :, 0].max())
    y0, y1 = float(Tl[:, :, 1].min()), float(Tl[:, :, 1].max())
    X = np.arange(x0 - pitch, x1 + 1.5 * pitch, pitch)
    Y = np.arange(y0 - pitch, y1 + 1.5 * pitch, pitch)
    mask = np.zeros((len(Y), len(X)), bool)
    zmap = np.full(mask.shape, np.inf)
    for i in ids:
        t = Tl[int(i)]
        ix0 = max(0, int(math.floor((t[:, 0].min() - X[0]) / pitch)))
        ix1 = min(len(X) - 1, int(math.ceil((t[:, 0].max() - X[0]) / pitch)))
        iy0 = max(0, int(math.floor((t[:, 1].min() - Y[0]) / pitch)))
        iy1 = min(len(Y) - 1, int(math.ceil((t[:, 1].max() - Y[0]) / pitch)))
        if ix1 < ix0 or iy1 < iy0:
            continue
        xx, yy = np.meshgrid(X[ix0:ix1 + 1], Y[iy0:iy1 + 1])
        a, b, c = t
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        u = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / den
        v = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / den
        inside = (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9)
        view = mask[iy0:iy1 + 1, ix0:ix1 + 1]
        view |= inside
        if z_mode:
            z = u * a[2] + v * b[2] + (1.0 - u - v) * c[2]
            zv = zmap[iy0:iy1 + 1, ix0:ix1 + 1]
            zv[inside] = np.minimum(zv[inside], z[inside])
    return X, Y, mask, zmap


def first_layer_and_thickness(Tl: np.ndarray, pitch=0.20):
    field = Field(Tl)
    x0, x1 = float(Tl[:, :, 0].min()), float(Tl[:, :, 0].max())
    y0, y1 = float(Tl[:, :, 1].min()), float(Tl[:, :, 1].max())
    z0 = float(Tl[:, :, 2].min())
    X = np.arange(x0 + 0.5 * pitch, x1, pitch)
    Y = np.arange(y0 + 0.5 * pitch, y1, pitch)
    plan = np.zeros((len(Y), len(X)), bool)
    layer = np.zeros_like(plan)
    thickness = np.zeros_like(plan, dtype=float)
    odd = 0
    for iy, y in enumerate(Y):
        for ix, x in enumerate(X):
            h = field.hits(x, y)
            if len(h) % 2:
                odd += 1
                continue
            if len(h):
                plan[iy, ix] = True
                thickness[iy, ix] = sum(h[k + 1] - h[k] for k in range(0, len(h), 2))
                zz = z0 + 0.20
                layer[iy, ix] = any(h[k] - 1e-6 <= zz <= h[k + 1] + 1e-6 for k in range(0, len(h), 2))
    labels, ncomp = ndimage.label(layer, structure=np.ones((3, 3), int))
    comp_areas = sorted([float(np.sum(labels == k) * pitch * pitch) for k in range(1, ncomp + 1)], reverse=True)
    edge_distance = ndimage.distance_transform_edt(plan, sampling=pitch)
    thin = plan & (thickness < 1.20) & (edge_distance > 1.0)
    return {
        "pitchMm": pitch,
        "x": X,
        "y": Y,
        "field": field,
        "plan": plan,
        "firstLayerMask": layer,
        "firstLayerAreaMm2": float(layer.sum() * pitch * pitch),
        "firstLayerComponents": int(ncomp),
        "firstLayerComponentAreasMm2": comp_areas,
        "oddRayColumns": odd,
        "interiorAreaBelow1p2Mm2": float(thin.sum() * pitch * pitch),
        "thicknessPercentilesMm": {str(q): float(np.percentile(thickness[plan], q)) for q in (1, 5, 25, 50, 75, 95)},
    }


def support_landing_analysis(metric, pitch=0.25):
    Tl = metric["localTriangles"]
    X, Y, mask, zmap = rasterize_triangles(Tl, metric["supportIds"], pitch, z_mode=True)
    field = Field(Tl)
    direct_bed = deck_top = other_model = unresolved = 0
    base_map = np.zeros(mask.shape, np.uint8)
    for iy, ix in zip(*np.nonzero(mask)):
        target = zmap[iy, ix]
        h = field.hits(X[ix], Y[iy])
        if len(h) % 2:
            unresolved += 1
            continue
        tops = [h[k + 1] for k in range(0, len(h), 2) if h[k + 1] < target - 0.08]
        if not tops:
            direct_bed += 1
            base_map[iy, ix] = 1
        else:
            top = max(tops)
            if 2.75 <= top - float(Tl[:, :, 2].min()) <= 3.25:
                deck_top += 1
                base_map[iy, ix] = 2
            else:
                other_model += 1
                base_map[iy, ix] = 3
    cell = pitch * pitch
    return {
        "pitchMm": pitch,
        "projectedSupportAreaMm2": float(mask.sum() * cell),
        "directFromBedAreaMm2": float(direct_bed * cell),
        "wouldBaseOnDeckTopAreaMm2": float(deck_top * cell),
        "wouldBaseOnOtherModelAreaMm2": float(other_model * cell),
        "unresolvedAreaMm2": float(unresolved * cell),
        "x": X, "y": Y, "mask": mask, "baseMap": base_map,
    }


def mesh_inside(field: Field, p: np.ndarray) -> bool:
    h = field.hits(float(p[0]) + 3.7e-7, float(p[1]) + 2.1e-7)
    if len(h) % 2:
        return False
    return any(h[k] - 1.0e-6 <= p[2] <= h[k + 1] + 1.0e-6 for k in range(0, len(h), 2))


def air_run(field, center, axis, half_range, step=0.01):
    ts = np.arange(-half_range, half_range + 0.5 * step, step)
    air = np.array([not mesh_inside(field, center + axis * t) for t in ts])
    i0 = int(np.argmin(np.abs(ts)))
    if not air[i0]:
        return 0.0, [0.0, 0.0]
    lo = hi = i0
    while lo > 0 and air[lo - 1]:
        lo -= 1
    while hi + 1 < len(ts) and air[hi + 1]:
        hi += 1
    return float(ts[hi] - ts[lo] + step), [float(ts[lo] - 0.5 * step), float(ts[hi] + 0.5 * step)]


def seat_slot_audit(T, joy_up):
    sys.path.insert(0, str(PROJECT_SCRIPTS))
    from b01_true_axes import ORDER
    from h03_placement import seat_solids

    core = json.loads((REV / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    field = Field(T)
    rows = []
    seat_rows = []
    for name in [x for x in ORDER if x != "JOY"]:
        r = core["seats"][name]
        w = unit(np.asarray(r["axisWorld"], float))
        u = seat_solids(np.asarray(r["capUndersideWorld"], float), w, name)
        top = np.asarray(u["plateTopPoint"], float)
        ex, ey = unit(np.asarray(u["ex"], float)), unit(np.asarray(u["ey"], float))
        slot_data = []
        for sign in (-1.0, 1.0):
            c = top + ex * (sign * 2.60) - w * 0.80
            width, wb = air_run(field, c, ex, 1.15, 0.01)
            length, lb = air_run(field, c, ey, 4.00, 0.02)
            clear_depth_samples = [not mesh_inside(field, top + ex * (sign * 2.60) - w * d) for d in np.arange(0.10, 8.01, 0.10)]
            slot_data.append({
                "side": "-" if sign < 0 else "+",
                "widthMm": width,
                "lengthMm": length,
                "widthBoundsLocalMm": wb,
                "lengthBoundsLocalMm": lb,
                "clearDepthSamples": int(sum(clear_depth_samples)),
                "depthSamples": len(clear_depth_samples),
            })
            rows.append({"seat": name, **slot_data[-1]})
        inner_sep = 5.20 - 0.5 * (slot_data[0]["widthMm"] + slot_data[1]["widthMm"])
        outer_lig = 4.80 - (2.60 + 0.5 * max(slot_data[0]["widthMm"], slot_data[1]["widthMm"]))

        # Area of material immediately under the frozen 6.02 x 6.04 bearing footprint.
        pitch = 0.10
        xs = np.arange(-3.01 + pitch / 2, 3.01, pitch)
        ys = np.arange(-3.02 + pitch / 2, 3.02, pitch)
        count = 0
        for x in xs:
            for y in ys:
                if mesh_inside(field, top + ex * x + ey * y - w * 0.05):
                    count += 1
        bearing_area = count * pitch * pitch
        ang = math.degrees(math.acos(np.clip(abs(float(w @ joy_up)), -1.0, 1.0)))
        seat_rows.append({
            "seat": name,
            "bearingAreaSampledMm2": bearing_area,
            "bearingPlaneOffBedDeg": ang,
            "slotInnerWallSeparationMm": inner_sep,
            "minimumOuterLigamentMm": outer_lig,
            "slots": slot_data,
        })
    return rows, seat_rows


def face_ribbon_and_pad_audit(shape, joy_up):
    ribbons = []
    pad_faces = []
    for idx, f in enumerate(shape.faces()):
        verts, tris = f.tessellate(0.03, 0.10)
        P = np.array([vec(v) for v in verts])
        if len(P) < 3:
            continue
        c = P.mean(axis=0)
        _, _, vh = np.linalg.svd(P - c, full_matrices=False)
        uv = (P - c) @ vh[:2].T
        spans = sorted([float(np.ptp(uv[:, 0])), float(np.ptp(uv[:, 1]))])
        try:
            normal = unit(vec(f.normal_at()))
        except Exception:
            normal, _ = triangle_geometry(P[np.asarray(tris, int)])
            normal = unit(normal.mean(axis=0))
        area = float(f.area)
        if spans[0] < 1.20 and area > 0.02:
            ribbons.append({
                "face": idx,
                "areaMm2": area,
                "pcaSpanMm": spans,
                "centroidWorld": c.tolist(),
                "normalDotPrintUp": float(normal @ joy_up),
            })
        square_7p4 = 7.15 <= spans[0] <= 7.65 and 7.15 <= spans[1] <= 7.65
        pad_sized = 6.5 <= spans[0] <= 8.0 and 6.5 <= spans[1] <= 8.0 and area >= 15.0
        if 53.5 <= area <= 56.0 or square_7p4 or pad_sized:
            pad_faces.append({
                "face": idx,
                "areaMm2": area,
                "pcaSpanMm": spans,
                "centroidWorld": c.tolist(),
                "normalWorld": normal.tolist(),
                "normalDotPrintUp": float(normal @ joy_up),
                "requires45DegSupport": bool(float(normal @ joy_up) < -COS45),
                "matches7p4mmSquare": bool(square_7p4),
                "padSizedPlanarFace": bool(pad_sized),
            })
    ribbons.sort(key=lambda x: x["pcaSpanMm"][0])
    return ribbons, pad_faces


def render_mesh(Tl, support_ids, bed_ids, path: Path, underside=False):
    view = unit(np.array([1.0, -1.15, -0.75 if underside else 0.75]))
    su = unit(np.cross(np.array([0.0, 0.0, 1.0]), view))
    sv = unit(np.cross(view, su))
    p = Tl.reshape(-1, 3)
    uv = np.column_stack([p @ su, p @ sv]).reshape(-1, 3, 2)
    depth = (Tl.mean(axis=1) @ view)
    order = np.argsort(depth)
    mn, mx = uv.reshape(-1, 2).min(axis=0), uv.reshape(-1, 2).max(axis=0)
    W, H, margin = 1200, 900, 55
    scale = min((W - 2 * margin) / (mx[0] - mn[0]), (H - 2 * margin) / (mx[1] - mn[1]))
    im = Image.new("RGB", (W, H), (248, 248, 246))
    d = ImageDraw.Draw(im)
    support_set, bed_set = set(map(int, support_ids)), set(map(int, bed_ids))
    normals, _ = triangle_geometry(Tl)
    light = unit(np.array([-0.4, -0.3, 1.0]))
    for i in order:
        pts = [(margin + (x - mn[0]) * scale, H - margin - (y - mn[1]) * scale) for x, y in uv[i]]
        if int(i) in support_set:
            color = (225, 92, 55)
        elif int(i) in bed_set:
            color = (53, 143, 171)
        else:
            shade = int(165 + 65 * max(0.0, float(normals[i] @ light)))
            color = (shade, shade, min(245, shade + 8))
        d.polygon(pts, fill=color, outline=(95, 95, 95))
    title = "C07 underside: orange = >45 deg support surfaces" if underside else "C07 JOY_AXIS_UP: blue = true bed contact, orange = support surfaces"
    d.rectangle((0, 0, W, 38), fill=(255, 255, 255))
    d.text((15, 12), title, fill=(20, 20, 20))
    im.save(path)


def render_mask(mask, path: Path, title: str, colors=None):
    arr = np.asarray(mask)
    if arr.dtype == bool:
        rgb = np.zeros((*arr.shape, 3), np.uint8)
        rgb[:] = (248, 248, 246)
        rgb[arr] = (48, 135, 166)
    else:
        palette = colors or {0: (248, 248, 246), 1: (76, 170, 98), 2: (215, 64, 48), 3: (230, 151, 44)}
        rgb = np.zeros((*arr.shape, 3), np.uint8)
        for k, c in palette.items():
            rgb[arr == k] = c
    im = Image.fromarray(np.flipud(rgb), "RGB")
    scale = max(2, min(8, int(1000 / max(im.size))))
    im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (im.width, im.height + 42), (255, 255, 255))
    canvas.paste(im, (0, 42))
    ImageDraw.Draw(canvas).text((12, 14), title, fill=(20, 20, 20))
    canvas.save(path)


def render_slots(seat_rows, path: Path):
    W, H = 1100, 720
    im = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(im)
    d.text((20, 15), "C07 actual STEP sampling: 8 switch seats / 16 terminal slots", fill=(20, 20, 20))
    for idx, r in enumerate(seat_rows):
        col, row = idx % 4, idx // 4
        ox, oy = 30 + col * 265, 65 + row * 310
        d.rectangle((ox, oy, ox + 220, oy + 220), outline=(60, 60, 60), width=2, fill=(220, 224, 226))
        # Schematic uses measured widths and lengths, scaled at 20 px/mm.
        for si, s in enumerate(r["slots"]):
            cx = ox + 110 + (-52 if si == 0 else 52)
            ww = max(4, int(s["widthMm"] * 20))
            ll = max(4, int(s["lengthMm"] * 20))
            d.rectangle((cx - ww // 2, oy + 110 - ll // 2, cx + ww // 2, oy + 110 + ll // 2), fill=(250, 250, 248), outline=(201, 72, 50), width=2)
        d.text((ox, oy + 232), f"{r['seat']}  slots {r['slots'][0]['widthMm']:.2f}/{r['slots'][1]['widthMm']:.2f} x {r['slots'][0]['lengthMm']:.2f} mm", fill=(20, 20, 20))
        d.text((ox, oy + 250), f"bearing ~{r['bearingAreaSampledMm2']:.2f} mm2; tilt {r['bearingPlaneOffBedDeg']:.2f} deg", fill=(20, 20, 20))
        d.text((ox, oy + 268), f"inner web {r['slotInnerWallSeparationMm']:.2f}; outer ligament {r['minimumOuterLigamentMm']:.2f} mm", fill=(20, 20, 20))
    im.save(path)


def serializable_metric(m):
    return {k: v for k, v in m.items() if k not in {"bedIds", "supportIds", "localTriangles", "rotation"}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text(encoding="utf-8"))
    joy = unit(np.asarray(meta["printUpWorld"], float))

    source_info = {
        "step": str(STEP), "stl": str(STL), "builder": str(BUILDER),
        "stepModified": STEP.stat().st_mtime, "stlModified": STL.stat().st_mtime,
        "builderModified": BUILDER.stat().st_mtime,
        "sha256": {"step": sha256(STEP), "stl": sha256(STL), "builder": sha256(BUILDER)},
    }

    print("stage: STEP import", flush=True)
    shape = import_step(str(STEP))
    bb = shape.bounding_box()
    step_info = {
        "imported": True,
        "type": type(shape).__name__,
        "solids": len(list(shape.solids())),
        "shells": len(list(shape.shells())),
        "faces": len(list(shape.faces())),
        "valid": bool(shape.is_valid),
        "volumeMm3": float(shape.volume),
        "bboxMinWorldMm": vec(bb.min).tolist(),
        "bboxMaxWorldMm": vec(bb.max).tolist(),
        "bboxSizeWorldMm": vec(bb.size).tolist(),
    }
    try:
        com = vec(shape.center(CenterOf.MASS))
    except Exception:
        com = 0.5 * (vec(bb.min) + vec(bb.max))
    step_info["centerOfMassWorldMm"] = com.tolist()

    brep_vertices = np.array([vec(v) for v in shape.vertices()])
    brep_z0 = float((brep_vertices @ joy).min())
    brep_bed_faces = []
    for idx, face in enumerate(shape.faces()):
        fv = np.array([vec(v) for v in face.vertices()])
        if not len(fv):
            continue
        try:
            fn = unit(vec(face.normal_at()))
        except Exception:
            continue
        if float((fv @ joy).max()) <= brep_z0 + 1.0e-5 and float(fn @ joy) < -0.999:
            brep_bed_faces.append({"face": idx, "areaMm2": float(face.area)})
    step_info["exactCoplanarBedFaces"] = brep_bed_faces
    step_info["exactCoplanarBedAreaMm2"] = float(sum(f["areaMm2"] for f in brep_bed_faces))

    print("stage: STL topology", flush=True)
    T, stored_normals = read_binary_stl(STL)
    topology = topology_metrics(T, stored_normals)
    F = topology.pop("faceIndex")
    print("stage: STL self-intersections", flush=True)
    intersections, capped = self_intersections(T, F)
    stl_bb_min, stl_bb_max = T.reshape(-1, 3).min(axis=0), T.reshape(-1, 3).max(axis=0)
    stl_info = {
        **topology,
        "bboxMinWorldMm": stl_bb_min.tolist(),
        "bboxMaxWorldMm": stl_bb_max.tolist(),
        "bboxSizeWorldMm": (stl_bb_max - stl_bb_min).tolist(),
        "selfIntersectionPairs": intersections,
        "selfIntersectionSearchCapped": capped,
    }
    stl_info["bboxMaxAbsDifferenceVsStepMm"] = float(max(np.max(np.abs(stl_bb_min - vec(bb.min))), np.max(np.abs(stl_bb_max - vec(bb.max)))))
    stl_info["volumeDifferenceVsStepMm3"] = float(abs(stl_info["absoluteVolumeMm3"] - step_info["volumeMm3"]))
    stl_info["volumeDifferenceVsStepPercent"] = 100.0 * stl_info["volumeDifferenceVsStepMm3"] / step_info["volumeMm3"]

    # Independent orientation set: intended, inverted, two PCA major-side directions,
    # plus a surface-normal search for any materially better bed-facing candidate.
    _, Rj = local_triangles(T, joy)
    side_x, side_y = Rj[:, 0], Rj[:, 1]
    candidates = [
        ("JOY_AXIS_UP", joy), ("INVERTED", -joy),
        ("MAJOR_SIDE_A", side_x), ("MAJOR_SIDE_A_INVERTED", -side_x),
        ("MAJOR_SIDE_B", side_y), ("MAJOR_SIDE_B_INVERTED", -side_y),
    ]
    print("stage: orientation candidates", flush=True)
    metrics = [orientation_metric(T, F, up, label, com) for label, up in candidates]

    normals, areas = triangle_geometry(T)
    normal_keys = {}
    for n, a in zip(normals, areas):
        if a < 0.20:
            continue
        k = tuple(np.round(n, 3))
        normal_keys[k] = normal_keys.get(k, 0.0) + float(a)
    search = []
    for k, grouped_area in sorted(normal_keys.items(), key=lambda kv: -kv[1])[:240]:
        m = orientation_metric(T, F, -unit(np.asarray(k, float)), "SURFACE_SEARCH", com, details=False)
        if m["bedContactAreaMm2"] >= 10.0:
            m["score"] = m["supportAreaMm2"] + 18.0 * m["heightMm"] + 18000.0 / (m["bedContactAreaMm2"] + 1.0)
            search.append(m)
    search.sort(key=lambda x: x["score"])
    search_best = serializable_metric(search[0]) if search else None

    print("stage: first layer and support paths", flush=True)
    joy_metric = metrics[0]
    first = first_layer_and_thickness(joy_metric["localTriangles"], 0.20)
    support = support_landing_analysis(joy_metric, 0.25)
    print("stage: 16 actual slots and 8 seats", flush=True)
    slot_rows, seat_rows = seat_slot_audit(T, joy)
    print("stage: BRep narrow faces and standoff ends", flush=True)
    ribbons, pad_faces = face_ribbon_and_pad_audit(shape, joy)

    # True bed-face raster at finer pitch, used to verify coherent contact rather than
    # accepting an area sum alone.
    bx, by, bed_mask, _ = rasterize_triangles(joy_metric["localTriangles"], joy_metric["bedIds"], 0.15)
    blab, bn = ndimage.label(bed_mask, structure=np.ones((3, 3), int))
    bed_components = sorted([float(np.sum(blab == k) * 0.15 * 0.15) for k in range(1, bn + 1)], reverse=True)
    bed_erode = []
    for radius in (0.45, 0.90, 1.50, 2.10, 3.00):
        it = max(1, int(round(radius / 0.15)))
        e = ndimage.binary_erosion(bed_mask, iterations=it)
        _, nc = ndimage.label(e, structure=np.ones((3, 3), int))
        bed_erode.append({"erosionRadiusMm": radius, "remainingAreaMm2": float(e.sum() * 0.15 * 0.15), "components": int(nc)})

    # Identify the actual aperture dimensions from the first layer's central void.
    fl = first["firstLayerMask"]
    inv = ~fl
    void_labels, nv = ndimage.label(inv, structure=np.ones((3, 3), int))
    central_voids = []
    for k in range(1, nv + 1):
        yy, xx = np.nonzero(void_labels == k)
        if not len(xx):
            continue
        touches = xx.min() == 0 or yy.min() == 0 or xx.max() == fl.shape[1] - 1 or yy.max() == fl.shape[0] - 1
        if not touches:
            central_voids.append({
                "areaMm2": float(len(xx) * 0.04),
                "spanXmm": float((xx.max() - xx.min() + 1) * 0.20),
                "spanYmm": float((yy.max() - yy.min() + 1) * 0.20),
            })
    central_voids.sort(key=lambda x: -x["areaMm2"])

    render_mesh(joy_metric["localTriangles"], joy_metric["supportIds"], joy_metric["bedIds"], OUT / "01_joy_axis_up.png")
    render_mesh(joy_metric["localTriangles"], joy_metric["supportIds"], joy_metric["bedIds"], OUT / "02_underside_support_risk.png", underside=True)
    render_mask(bed_mask, OUT / "03_true_bed_contact.png", "True coplanar bed footprint (one connected annular deck footprint)")
    render_mask(support["baseMap"], OUT / "04_support_landing_paths.png", "Support projection: green bed / red deck-top base / orange other-model base")
    render_slots(seat_rows, OUT / "05_switch_seats_terminal_slots.png")
    trapped_ids = np.array([q for r in joy_metric["largestSupportRegions"] if r["trapped"] for q in r["triangleIds"]], dtype=int)
    if len(trapped_ids):
        trapped_sub = joy_metric["localTriangles"][trapped_ids]
        render_mesh(trapped_sub, np.arange(len(trapped_sub)), np.array([], dtype=int), OUT / "07_trapped_region_isolated.png", underside=True)

    out = {
        "source": source_info,
        "step": step_info,
        "stl": stl_info,
        "stepStlAgreement": {
            "bboxMaxAbsDifferenceMm": stl_info["bboxMaxAbsDifferenceVsStepMm"],
            "volumeDifferenceMm3": stl_info["volumeDifferenceVsStepMm3"],
            "volumeDifferencePercent": stl_info["volumeDifferenceVsStepPercent"],
        },
        "orientationCandidates": [serializable_metric(m) for m in metrics],
        "surfaceNormalSearchBest": search_best,
        "firstLayer": {
            k: v for k, v in first.items() if k not in {"x", "y", "field", "plan", "firstLayerMask"}
        } | {
            "trueBedFaceRasterPitchMm": 0.15,
            "trueBedFaceRasterAreaMm2": float(bed_mask.sum() * 0.15 * 0.15),
            "trueBedFootprintComponents": int(bn),
            "trueBedFootprintComponentAreasMm2": bed_components,
            "erosionConnectivity": bed_erode,
            "internalFirstLayerVoids": central_voids[:5],
        },
        "supportLanding": {k: v for k, v in support.items() if k not in {"x", "y", "mask", "baseMap"}},
        "terminalSlots": slot_rows,
        "switchSeats": seat_rows,
        "narrowBRepFaceCandidates": ribbons[:80],
        "candidateStandoffEndFaces": pad_faces,
        "builderClaimsRelevantToAudit": {
            "columnXYmm": meta["columnXY"],
            "bridgeWidthMm": meta["bridgeWidth"],
            "slabThicknessMm": meta["slabThicknessMm"],
            "deckThicknessMm": meta["deckThicknessMm"],
            "deckApertureMetadataMm": meta["deckApertureMm"],
            "verticalWallThicknessMm": meta["wallThicknessMm"],
            "standoffs": meta["standoffs"],
            "padXYmetadataMm": meta["padXY"],
            "padChamferMetadataMm": meta["padChamferMm"],
        },
        "renderFiles": [
            "01_joy_axis_up.png", "02_underside_support_risk.png", "03_true_bed_contact.png",
            "04_support_landing_paths.png", "05_switch_seats_terminal_slots.png", "07_trapped_region_isolated.png",
        ],
    }
    (OUT / "C07_PRINT_RISK_REGIONS.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({
        "step": step_info,
        "stl": stl_info,
        "orientations": [serializable_metric(m) for m in metrics],
        "searchBest": search_best,
        "firstLayer": out["firstLayer"],
        "supportLanding": out["supportLanding"],
        "slots": slot_rows,
        "seats": seat_rows,
        "padFaces": pad_faces,
        "narrowFacesTop10": ribbons[:10],
    }, indent=2))


if __name__ == "__main__":
    main()
