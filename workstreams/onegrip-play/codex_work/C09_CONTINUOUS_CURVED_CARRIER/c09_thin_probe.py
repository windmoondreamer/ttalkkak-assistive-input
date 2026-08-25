"""Locate JOY-up sampled columns below 1.20 mm for C09 QA."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import CenterOf, import_step
from scipy import ndimage

ROOT = Path(r"C:\Users\User\Desktop\OneGrip-Play")
WORK = ROOT / "codex_work" / "C09_CONTINUOUS_CURVED_CARRIER"
sys.path.insert(0, str(ROOT / "codex_work" / "C07_1_FDM_SIMPLIFICATION"))
sys.path.insert(0, str(ROOT / "thumb_inner_housing_lab" / "REV_K_C08_LOCAL_CONFORMAL_RECEIVER" / "10_scripts"))
import labutil as L  # noqa: E402
from validate_c07_1_fdm import Field, orientation_metric, read_binary_stl, topology_metrics  # noqa: E402


def vec(v):
    return np.asarray([float(v.X), float(v.Y), float(v.Z)], float)


def main():
    step = WORK / "outputs" / "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.step"
    stl = WORK / "outputs" / "C09_CONTINUOUS_CURVED_CARRIER_THUMB_CORE.stl"
    joy = json.loads((ROOT / "thumb_inner_housing_lab" / "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE" /
                      "06_current_core" / "i06b_joystick_current_stack.json").read_text())
    up = L.unit(np.asarray(joy["joyAxisWorld"], float))
    shape = import_step(str(step))
    T, n = read_binary_stl(stl)
    topo = topology_metrics(T, n); F = topo.pop("faceIndex")
    m = orientation_metric(T, F, up, "JOY_AXIS_UP", vec(shape.center(CenterOf.MASS)))
    Tl, R = m["localTriangles"], m["rotation"]
    field = Field(Tl)
    pitch = 0.20
    x0, x1 = float(Tl[:, :, 0].min()), float(Tl[:, :, 0].max())
    y0, y1 = float(Tl[:, :, 1].min()), float(Tl[:, :, 1].max())
    X = np.arange(x0 + 0.5 * pitch, x1, pitch)
    Y = np.arange(y0 + 0.5 * pitch, y1, pitch)
    plan = np.zeros((len(Y), len(X)), bool)
    thick = np.zeros(plan.shape, float)
    intervals = {}
    for iy, y in enumerate(Y):
        for ix, x in enumerate(X):
            h = field.hits(x, y)
            if len(h) and len(h) % 2 == 0:
                plan[iy, ix] = True
                thick[iy, ix] = sum(h[k + 1] - h[k] for k in range(0, len(h), 2))
                intervals[(iy, ix)] = h.tolist()
    edge = ndimage.distance_transform_edt(plan, sampling=pitch)
    thin = plan & (thick < 1.20) & (edge > 1.0)
    rows = []
    for iy, ix in zip(*np.nonzero(thin)):
        p0 = np.asarray((X[ix], Y[iy], np.mean(intervals[(iy, ix)])), float)
        world = p0 @ R.T
        rows.append({"localXY": [float(X[ix]), float(Y[iy])],
                     "worldApprox": world.tolist(), "thicknessMm": float(thick[iy, ix]),
                     "edgeDistanceMm": float(edge[iy, ix]),
                     "intervals": intervals[(iy, ix)]})
    out = {"pitchMm": pitch, "thinAreaMm2": len(rows) * pitch * pitch, "samples": rows}
    (WORK / "validation" / "C09_THIN_PROBE.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
