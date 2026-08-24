"""Shared low-memory helpers for the Thumb Inner Housing Lab -- REV_B copy.

Copied from REV_A/10_scripts/labutil.py so that LAB resolves to REV_B and no
REV_A output can be overwritten.  REV_A is immutable from here on.

READ-ONLY outside thumb_inner_housing_lab/REV_B.  Never imports a production
generator module that writes on import.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import psutil
from build123d import (
    Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector,
    export_step, export_stl, import_step,
)
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation
from OCP.TopLoc import TopLoc_Location

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parents[1]          # -> REV_B
REV_A = LAB.parent / "REV_A"                       # read-only reference

# --- authoritative source paths (read-only) --------------------------------
SRC = {
    "JAD_LOWERED_THUMB": ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JAD_EXTERIOR_LOWERED_THUMB_V1.step",
    "JFD_LOWERED_THUMB": ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JFD_EXTERIOR_LOWERED_THUMB_V1.step",
    "JAD_FINGER_V2": ROOT / "build123d_workbench/out/finger_controls_v2/JAD_FINGER_V2.step",
    "JFD_FINGER_V2": ROOT / "build123d_workbench/out/finger_controls_v2/JFD_FINGER_V2.step",
    "JAD_CLEAN_PRE_FINGER": ROOT / "local_cad/reference/JAD_CLEAN_PRE_FINGER.step",
    "JFD_CLEAN_PRE_FINGER": ROOT / "local_cad/reference/JFD_CLEAN_PRE_FINGER.step",
    "THUMB_TARGET_EXACT_MODULE": ROOT / "build123d_workbench/out/finger_thumb_joint_feasibility/THUMB_TARGET_EXACT_MODULE.step",
    "ORIGINAL_THUMB_CARTRIDGE": ROOT / "build123d_workbench/out/original_thumb_module_reuse_audit/ORIGINAL_THUMB_CARTRIDGE.step",
    "LOWERED_ORIGINAL_THUMB_CARTRIDGE": ROOT / "build123d_workbench/out/original_thumb_module_reuse_audit/LOWERED_ORIGINAL_THUMB_CARTRIDGE.step",
    "THUMB_ORIGINAL_PRE_FINGER": ROOT / "local_cad/reference/THUMB_ORIGINAL_PRE_FINGER_REFERENCE.step",
    "N1_N2_CARRIER": ROOT / "build123d_workbench/out/n1_production_intent_mechanism/N1_N2_SHARED_CARRIER_N1_LOCAL.step",
    "SZH_WEB_REFERENCE": ROOT / "local_cad/reference/SZH_EK056_WEB_REFERENCE.step",
    "ORIGINAL_FASTENING": ROOT / "build123d_workbench/out/original_thumb_module_reuse_audit/ORIGINAL_FASTENING_REFERENCE.step",
}

# --- frozen datums (docs/53, docs/54, docs/71) -----------------------------
THUMB_DELTA = np.asarray((0.0, 12.25, -21.0), float)

DATUM_P = np.asarray((-0.21604013507035, -23.14907664213591, 40.49617911468703), float)
DATUM_N = np.asarray((-0.000181853768751, -0.598493368976127, -0.801127739015953), float)
DATUM_U = np.asarray((0.99999946034044, 0.000710605462944, -0.000757864568375), float)
DATUM_V = np.asarray((0.001022862666615, -0.801127444500238, 0.598492916767178), float)

RSS_LIMIT_MB = 20480.0
AVAILABLE_STOP_MB = 3072.0
_PROC = psutil.Process(os.getpid())
MEMORY_LOG: list[dict] = []


def memory(stage: str) -> None:
    gc.collect()
    rss = _PROC.memory_info().rss / (1024.0 * 1024.0)
    avail = psutil.virtual_memory().available / (1024.0 * 1024.0)
    MEMORY_LOG.append({"stage": stage, "rssMb": round(rss, 1), "availMb": round(avail, 1)})
    print("  [mem] %-46s rss=%8.1fMB avail=%9.1fMB" % (stage, rss, avail), flush=True)
    if rss > RSS_LIMIT_MB:
        raise MemoryError("RAM stop at %s: rss %.1f MB" % (stage, rss))
    if avail < AVAILABLE_STOP_MB:
        raise MemoryError("RAM stop at %s: available %.1f MB" % (stage, avail))


def unit(v: Iterable[float]) -> np.ndarray:
    a = np.asarray(tuple(v), float)
    n = float(np.linalg.norm(a))
    if n <= 0.0:
        raise ValueError("zero vector")
    return a / n


def xyz(v: Iterable[float]) -> Vector:
    a = tuple(float(x) for x in v)
    return Vector(a[0], a[1], a[2])


def sha256(path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def bbox_dict(shape: Shape) -> dict:
    b = shape.bounding_box()
    return {"min": [float(b.min.X), float(b.min.Y), float(b.min.Z)],
            "max": [float(b.max.X), float(b.max.Y), float(b.max.Z)],
            "size": [float(b.max.X - b.min.X), float(b.max.Y - b.min.Y), float(b.max.Z - b.min.Z)]}


def to_local(points) -> np.ndarray:
    """World -> thumb joystick local frame (u, v, n_out)."""
    d = np.atleast_2d(np.asarray(points, float)) - DATUM_P
    return np.stack([d @ DATUM_U, d @ DATUM_V, d @ (-DATUM_N)], axis=1)


def from_local(uvn) -> np.ndarray:
    a = np.atleast_2d(np.asarray(uvn, float))
    return DATUM_P + a[:, [0]] * DATUM_U + a[:, [1]] * DATUM_V + a[:, [2]] * (-DATUM_N)


def local_plane(origin_uvn=(0.0, 0.0, 0.0)) -> Plane:
    """Right-handed placement plane whose axes are (DATUM_V, DATUM_U, -DATUM_N).

    NOTE (handedness): (U, V, -N) is LEFT handed --- U x V = +N.  Building a
    Plane with x_dir=U, z_dir=-N therefore silently yields y_dir = -V and every
    box lands mirrored in v.  The valid ordering is (V, U, -N), which is also
    the frame szh_actual_fit_fixture.py uses.
    """
    return Plane(origin=xyz(from_local(np.asarray(origin_uvn, float))[0]),
                 x_dir=xyz(DATUM_V), z_dir=xyz(-DATUM_N))


def local_box(lo: Sequence[float], hi: Sequence[float], label: str) -> Shape:
    """Axis-aligned box given in local (u, v, n), placed in world coords."""
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    size = hi - lo
    plane = local_plane(lo)
    # plane axes are (v, u, n) -> swap the first two components
    box = plane * Box(float(size[1]), float(size[0]), float(size[2]),
                      align=(Align.MIN, Align.MIN, Align.MIN))
    box.label = label
    return box


def assert_local_box(lo, hi, tol: float = 1.0e-6) -> None:
    """Self-check: the built box must round-trip to the requested local bbox."""
    b = local_box(lo, hi, "SELFTEST")
    pts = np.asarray([[v.X, v.Y, v.Z] for v in b.vertices()], float)
    l = to_local(pts)
    got_lo, got_hi = l.min(axis=0), l.max(axis=0)
    if np.max(np.abs(got_lo - np.asarray(lo, float))) > 1e-6 or \
       np.max(np.abs(got_hi - np.asarray(hi, float))) > 1e-6:
        raise AssertionError("local_box frame error: got lo=%s hi=%s want lo=%s hi=%s"
                             % (got_lo, got_hi, lo, hi))


def triangles(shape: Shape, tol: float = 0.25, ang: float = 0.30) -> np.ndarray:
    """Per-face OCCT triangulation -> (n, 3, 3) array.

    Shape.tessellate() raises on shapes where a face carries no triangulation;
    the per-face BRep_Tool path simply skips those, which is what every other
    audit in this repo does.
    """
    shape.mesh(tol, ang)
    rows: list = []
    for face in shape.faces():
        loc = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, loc)
        if poly is None:
            continue
        trsf = loc.Transformation()
        pts = [poly.Node(i).Transformed(trsf) for i in range(1, poly.NbNodes() + 1)]
        rev = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        for tri in poly.Triangles():
            idx = [tri.Value(i) - 1 for i in (1, 2, 3)]
            if rev:
                idx[1], idx[2] = idx[2], idx[1]
            rows.append([[pts[i].X(), pts[i].Y(), pts[i].Z()] for i in idx])
    if not rows:
        raise RuntimeError("no triangles for " + str(shape.label))
    return np.asarray(rows, float)


def tri_arrays(shape: Shape, tol: float = 0.25, ang: float = 0.30):
    """Triangulate to (V, F) numpy arrays (V duplicated per triangle)."""
    T = triangles(shape, tol=tol, ang=ang)
    V = T.reshape(-1, 3)
    F = np.arange(len(V), dtype=int).reshape(-1, 3)
    return V, F


def surf_points(shape: Shape, n: int = 40000, tol: float = 0.25) -> np.ndarray:
    """Area-weighted uniform samples on the surface.  Never vertices-only:
    large planar faces carry almost no tessellation vertices."""
    V, F = tri_arrays(shape, tol=tol)
    if len(F) == 0:
        return V
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    total = float(area.sum())
    if total <= 0.0:
        return V
    rng = np.random.default_rng(20260824)
    counts = np.maximum(1, np.round(area / total * n).astype(int))
    idx = np.repeat(np.arange(len(F)), counts)
    r1 = rng.random(len(idx))
    r2 = rng.random(len(idx))
    s = np.sqrt(r1)
    w0 = (1.0 - s)[:, None]
    w1 = (s * (1.0 - r2))[:, None]
    w2 = (s * r2)[:, None]
    return w0 * a[idx] + w1 * b[idx] + w2 * c[idx]


def local_bbox(shape: Shape, n_samples: int = 60000) -> dict:
    pts = surf_points(shape, n_samples)
    l = to_local(pts)
    return {"min": [float(x) for x in l.min(axis=0)],
            "max": [float(x) for x in l.max(axis=0)],
            "size": [float(x) for x in (l.max(axis=0) - l.min(axis=0))]}


def load(key: str) -> Shape:
    return import_step(SRC[key])


def vol(shape: Shape) -> float:
    return float(shape.volume)


def inter_vol(a: Shape, b: Shape) -> float:
    """Intersection volume of two SINGLE solids.  Never pass Compounds:
    OCC silently returns an empty result for Compound operands."""
    r = a & b
    if r is None:
        return 0.0
    sl = list(r.solids())
    if not sl:
        return 0.0
    return float(sum(float(s.volume) for s in sl))


def as_single_solid(shape: Shape, label: str = ""):
    """Fuse a shape's solids into one solid.  Returns (solid, n_input)."""
    sl = list(shape.solids())
    if not sl:
        raise RuntimeError("no solids in " + (label or str(shape.label)))
    out = sl[0]
    for s in sl[1:]:
        out = out + s
    out = out.clean()
    lst = list(out.solids())
    if len(lst) == 1:
        out = lst[0]
    if label:
        out.label = label
    return out, len(sl)


def write_json(path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    print("  -> " + str(path))


# ---------------------------------------------------------------------------
# Robust occupancy sampling in the local Thumb frame
# ---------------------------------------------------------------------------

def local_triangles(shape: Shape, tol: float = 0.20, ang: float = 0.25) -> np.ndarray:
    """Triangles of `shape` expressed in local (u, v, n)."""
    T = triangles(shape, tol=tol, ang=ang)
    return to_local(T.reshape(-1, 3)).reshape(-1, 3, 3)


class Occupancy:
    """Column ray-parity point-in-solid test in the local Thumb frame.

    A single ray is cast along +n for every (u, v) column, so the cost is
    O(columns) rather than O(points).  Intersection parameters are de-duplicated
    because a ray that grazes a shared edge otherwise reports the same t twice
    and flips the parity (an actual defect hit in earlier repo work).
    """

    def __init__(self, shape: Shape, tol: float = 0.20, ang: float = 0.25):
        self.T = local_triangles(shape, tol=tol, ang=ang)
        self.lo = self.T.reshape(-1, 3).min(axis=0)
        self.hi = self.T.reshape(-1, 3).max(axis=0)

    def inside(self, U: np.ndarray, V: np.ndarray, N: np.ndarray) -> np.ndarray:
        """U, V are 1-D column coordinates; N is the 1-D sample ladder.

        Returns a boolean array of shape (len(U), len(V), len(N)).
        """
        T = self.T
        a, b, c = T[:, 0], T[:, 1], T[:, 2]
        e1 = b - a
        e2 = c - a
        # 2-D (u, v) triangle bboxes for column culling
        tu0 = np.minimum(np.minimum(a[:, 0], b[:, 0]), c[:, 0])
        tu1 = np.maximum(np.maximum(a[:, 0], b[:, 0]), c[:, 0])
        tv0 = np.minimum(np.minimum(a[:, 1], b[:, 1]), c[:, 1])
        tv1 = np.maximum(np.maximum(a[:, 1], b[:, 1]), c[:, 1])
        out = np.zeros((len(U), len(V), len(N)), bool)
        order = np.argsort(tu0)
        tu0s = tu0[order]
        for iu, u in enumerate(U):
            hi_idx = np.searchsorted(tu0s, u, side="right")
            cand = order[:hi_idx]
            cand = cand[tu1[cand] >= u]
            if cand.size == 0:
                continue
            for iv, v in enumerate(V):
                sel = cand[(tv0[cand] <= v) & (tv1[cand] >= v)]
                if sel.size == 0:
                    continue
                A = a[sel]
                E1 = e1[sel]
                E2 = e2[sel]
                # ray origin (u, v, -inf) direction (0, 0, 1)
                # solve barycentric in the (u, v) plane
                det = E1[:, 0] * E2[:, 1] - E1[:, 1] * E2[:, 0]
                ok = np.abs(det) > 1.0e-14
                if not ok.any():
                    continue
                du = u - A[:, 0]
                dv = v - A[:, 1]
                s = np.where(ok, (du * E2[:, 1] - dv * E2[:, 0]) / np.where(ok, det, 1.0), -1.0)
                t = np.where(ok, (E1[:, 0] * dv - E1[:, 1] * du) / np.where(ok, det, 1.0), -1.0)
                good = ok & (s >= 0.0) & (t >= 0.0) & (s + t <= 1.0)
                if not good.any():
                    continue
                hits = A[good, 2] + s[good] * E1[good, 2] + t[good] * E2[good, 2]
                hits = np.sort(hits)
                if hits.size:
                    keep = np.ones(hits.size, bool)
                    keep[1:] = np.diff(hits) > 1.0e-7
                    hits = hits[keep]
                if hits.size % 2:
                    continue  # ray degenerate at this column; leave empty
                idx = np.searchsorted(hits, N)
                out[iu, iv] = (idx % 2) == 1
        return out


def grid_axes(lo, hi, pitch: float):
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    return [np.arange(lo[i] + 0.5 * pitch, hi[i], pitch) for i in range(3)]
