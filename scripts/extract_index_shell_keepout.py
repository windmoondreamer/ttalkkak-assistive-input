"""Extract frozen INDEX-created JaD/JfD surfaces from final-vs-original meshes.

Local-only and deterministic.  A final shell triangle is retained when at
least one of its vertices or centroid is more than 0.05 mm from the original
pre-INDEX shell surface.  The output contains INDEX openings, holders and
positive fastening surfaces while dropping unchanged original shell faces.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "cad_dump"
THRESHOLD_MM = 0.05
REGION_MIN = np.asarray((-32.0, -38.0, -6.0))
REGION_MAX = np.asarray((20.0, 6.0, 32.0))


def load(name: str) -> np.ndarray:
    data = json.loads((DUMP / f"mesh_{name}.json").read_text(encoding="utf-8"))
    return np.asarray(data["tris"], dtype=float)


def point_triangle_distances(point: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Vectorized exact point-to-triangle distance for one point."""
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    ab, ac, ap = b - a, c - a, point - a
    d1 = np.einsum("ni,ni->n", ab, ap)
    d2 = np.einsum("ni,ni->n", ac, ap)
    out = np.full(len(triangles), np.inf)

    mask = (d1 <= 0.0) & (d2 <= 0.0)
    out[mask] = np.linalg.norm(ap[mask], axis=1)

    bp = point - b
    d3 = np.einsum("ni,ni->n", ab, bp)
    d4 = np.einsum("ni,ni->n", ac, bp)
    mask = (d3 >= 0.0) & (d4 <= d3)
    out[mask] = np.minimum(out[mask], np.linalg.norm(bp[mask], axis=1))

    vc = d1 * d4 - d3 * d2
    mask = (vc <= 0.0) & (d1 >= 0.0) & (d3 <= 0.0)
    denom = d1 - d3
    valid = mask & (np.abs(denom) > 1e-18)
    v = np.zeros(len(triangles))
    v[valid] = d1[valid] / denom[valid]
    q = a + v[:, None] * ab
    out[valid] = np.minimum(out[valid], np.linalg.norm(point - q[valid], axis=1))

    cp = point - c
    d5 = np.einsum("ni,ni->n", ab, cp)
    d6 = np.einsum("ni,ni->n", ac, cp)
    mask = (d6 >= 0.0) & (d5 <= d6)
    out[mask] = np.minimum(out[mask], np.linalg.norm(cp[mask], axis=1))

    vb = d5 * d2 - d1 * d6
    mask = (vb <= 0.0) & (d2 >= 0.0) & (d6 <= 0.0)
    denom = d2 - d6
    valid = mask & (np.abs(denom) > 1e-18)
    w = np.zeros(len(triangles))
    w[valid] = d2[valid] / denom[valid]
    q = a + w[:, None] * ac
    out[valid] = np.minimum(out[valid], np.linalg.norm(point - q[valid], axis=1))

    va = d3 * d6 - d5 * d4
    mask = (va <= 0.0) & ((d4 - d3) >= 0.0) & ((d5 - d6) >= 0.0)
    denom = (d4 - d3) + (d5 - d6)
    valid = mask & (np.abs(denom) > 1e-18)
    w = np.zeros(len(triangles))
    w[valid] = (d4[valid] - d3[valid]) / denom[valid]
    q = b + w[:, None] * (c - b)
    out[valid] = np.minimum(out[valid], np.linalg.norm(point - q[valid], axis=1))

    interior = ~np.isfinite(out)
    if interior.any():
        denom = va + vb + vc
        valid = interior & (np.abs(denom) > 1e-18)
        v = np.zeros(len(triangles)); w = np.zeros(len(triangles))
        v[valid] = vb[valid] / denom[valid]
        w[valid] = vc[valid] / denom[valid]
        q = a + v[:, None] * ab + w[:, None] * ac
        out[valid] = np.linalg.norm(point - q[valid], axis=1)
    return out


def nearest_distance(point: np.ndarray, original: np.ndarray) -> float:
    # AABB lower-bound pruning keeps large original planar faces exact.
    tmin, tmax = original.min(axis=1), original.max(axis=1)
    delta = np.maximum(np.maximum(tmin - point, point - tmax), 0.0)
    lower = np.linalg.norm(delta, axis=1)
    candidate = original[lower <= max(2.0, float(lower.min()) + 0.5)]
    return float(point_triangle_distances(point, candidate).min())


def extract(final_name: str, original_name: str) -> np.ndarray:
    final, original = load(final_name), load(original_name)
    fmin, fmax = final.min(axis=1), final.max(axis=1)
    region = np.all(fmax >= REGION_MIN, axis=1) & np.all(fmin <= REGION_MAX, axis=1)
    candidates = final[region]
    kept = []
    for index, triangle in enumerate(candidates):
        samples = np.vstack((triangle, triangle.mean(axis=0)))
        if max(nearest_distance(point, original) for point in samples) > THRESHOLD_MM:
            kept.append(triangle)
        if index and index % 1000 == 0:
            print(f"{final_name}: {index}/{len(candidates)} kept={len(kept)}", flush=True)
    return np.asarray(kept, dtype=float)


def main() -> None:
    jad = extract("INDEX_FINAL_JaD", "Joystick_1_baseline")
    jfd = extract("INDEX_FINAL_JfD", "Joystick_2_baseline")
    combined = np.concatenate((jad, jfd), axis=0)
    payload = {
        "name": "INDEX_FINAL_SHELL_KEEPOUT",
        "sourceVersion": "03ede76e83b5c865d9a69c35",
        "configuration": "default",
        "thresholdMm": THRESHOLD_MM,
        "JaDTriangles": len(jad),
        "JfDTriangles": len(jfd),
        "tris": combined.tolist(),
    }
    path = DUMP / "mesh_INDEX_FINAL_SHELL_KEEPOUT.json"
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {path} triangles={len(combined)}")
    if len(combined):
        points = combined.reshape(-1, 3)
        print("bbox", points.min(axis=0), points.max(axis=0))


if __name__ == "__main__":
    main()
