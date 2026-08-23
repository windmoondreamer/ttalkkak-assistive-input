"""각 버튼의 n0 좌표계에서 쉘 '안쪽면' n0 깊이를 실측해 격자로 저장한다 (READ ONLY)."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from axis_opt import load_tris, frame, P, N0, NAMES

T = load_tris("JfD_f2", "JaD_f2")
V0, V1, V2 = T[:, 0], T[:, 1], T[:, 2]
E1, E2 = V1 - V0, V2 - V0


def ray_ts(orig, direc):
    """광선과 메시의 모든 교차 t (정렬)."""
    pv = np.cross(direc, E2); det = (E1 * pv).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    tv = orig - V0
    u = (tv * pv).sum(1) * inv
    qv = np.cross(tv, E1)
    v = (direc * qv).sum(1) * inv
    t = (E2 * qv).sum(1) * inv
    hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-7)
    return np.sort(t[hit])


def inner_depth(i, x0, y0, start=-25.0):
    """(x0,y0) 에서 n0 을 따라 들어갈 때, 바깥 벽의 '안쪽면' n0 깊이. 재료 없으면 None."""
    u0, v0, z0 = frame(N0[i])
    orig = P[i] + u0 * x0 + v0 * y0 + z0 * (-start)   # 바깥쪽에서 출발
    ts = ray_ts(orig, -z0)
    if len(ts) < 2:
        return None
    # t 는 출발점 기준. n0 깊이 = t + start
    return float(ts[1] + start)


if __name__ == "__main__":
    G = np.arange(-7.0, 7.01, 0.5)
    out = {}
    for i in range(4):
        grid = []
        for x0 in G:
            row = []
            for y0 in G:
                d = inner_depth(i, float(x0), float(y0))
                row.append(None if d is None else round(d, 4))
            grid.append(row)
        out[NAMES[i]] = grid
        vals = [c for r in grid for c in r if c is not None]
        print(f"  {NAMES[i]}: 안쪽면 깊이 {min(vals):.2f} ~ {max(vals):.2f} mm  (표본 {len(vals)})", flush=True)
    json.dump({"grid": list(map(float, G)), "inner": out},
              open(os.path.join(os.path.dirname(__file__), "..", "cad_dump", "inner_surface.json"), "w"))
