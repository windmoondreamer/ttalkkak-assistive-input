"""신규 INDEX/MIDDLE 버튼 위치의 실제 3D 내부 공간 검증 (READ ONLY).

로컬 메시 캐시(cad_dump/mesh_*.json)만 사용한다. Onshape 에 요청하지 않는다.

    python scripts/clearance_check.py [INDEX_Z] [MIDDLE_Z]

좌표: Joystick Part Studio 기준. X=좌우(분할면 X=0), Y=전후(전면 -Y), Z=그립축.
envelope 검사는 각 샘플점의 **국소 법선**으로 쏜다 (곡면에서 단일 법선을 쓰면 오판).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from mesh_probe import Mesh, at_s, axis_center, contour, outer_point  # noqa: E402

SHELL = ["Joystick_1", "Joystick_2"]
INTERNAL = ["Backplate", "Small_joystick_attachment"]
S_POS = [-27.5, -16.5, -5.5, +5.5]
CAP = 8.0
POCKET = 6.4
HOLDER_DEPTH = 10.0          # 벽 뒤로 확보하고 싶은 holder/support 깊이
NEED = 3.0 + HOLDER_DEPTH    # 외피에서부터 필요한 총 깊이

# 실측 나사 (assembly definition -> part studio 좌표). 축은 X 방향
SCREWS = {"A": (10.00, -41.87, 45.98), "B": (10.00, -14.45, 23.07),
          "C": (10.00, 15.80, -21.35)}
SCREW_R = 3.5
SCREW_X = (-6.0, 10.0)


def press_kind(deg):
    a = abs(deg)
    return ("fingertip front" if a < 20 else "fingertip diagonal" if a < 45
            else "fingertip side" if a < 70 else "distal phalanx side")


def surface_at(shell, z, s, cont_cache):
    """(z, s) 의 외피 점과 3D 법선."""
    if z not in cont_cache:
        cont_cache[z] = (contour(shell, z, n=300, span=math.pi * 0.55),
                         axis_center(shell, z))
    cont, c = cont_cache[z]
    if not cont or c is None:
        return None
    r = at_s(cont, s)
    th = math.atan2(r[1] - c[0], -(r[2] - c[1]))
    hit = outer_point(shell, c, z, th)
    if hit is None:
        return None
    p, n, _ = hit
    return np.asarray(p), np.asarray(n) / np.linalg.norm(n)


def envelope(shell, full, z0, s0, cont_cache, half=POCKET / 2, g=2):
    """pocket 단면을 (s, z) 격자로 샘플. 각 점의 국소 법선으로 안쪽을 본다."""
    walls, depths, obstr = [], [], set()
    for i in range(-g, g + 1):
        for j in range(-g, g + 1):
            z = z0 + half * j / g
            s = s0 + half * i / g
            r = surface_at(shell, z, s, cont_cache)
            if r is None:
                continue
            p, n = r
            hits = full.hits_dedup(p + n * 2.0, -n)
            seq = [(t - 2.0, full.names[full.owner[k]]) for t, k in hits]
            seq = [h for h in seq if h[0] > -0.05]
            if len(seq) < 2:
                continue
            walls.append(seq[1][0] - seq[0][0])
            if len(seq) > 2:
                depths.append(seq[2][0])
                if seq[2][0] < NEED + 5:
                    obstr.add(seq[2][1])
            else:
                depths.append(float("inf"))
    return walls, depths, obstr


def screw_clearance(p, n):
    """holder envelope(외피에서 NEED 깊이, 단면 6.4x6.4) 와 나사 원기둥의 최소 거리."""
    tang = np.cross([0.0, 0.0, 1.0], n)
    tang /= np.linalg.norm(tang)
    zdir = np.cross(n, tang)
    best = (1e9, None)
    for d in np.linspace(0, NEED, 8):
        for a in (-POCKET / 2, 0, POCKET / 2):
            for b in (-POCKET / 2, 0, POCKET / 2):
                q = p - n * d + tang * a + zdir * b
                for k, (sx, sy, sz) in SCREWS.items():
                    dx = 0.0
                    if q[0] < SCREW_X[0]:
                        dx = SCREW_X[0] - q[0]
                    elif q[0] > SCREW_X[1]:
                        dx = q[0] - SCREW_X[1]
                    dist = math.hypot(math.hypot(q[1] - sy, q[2] - sz) - SCREW_R, dx)
                    if dist < best[0]:
                        best = (dist, k)
    return best


def run(index_z, middle_z):
    shell, full = Mesh(SHELL), Mesh(SHELL + INTERNAL)
    print(f"메시: shell tris={len(shell.T)}, full tris={len(full.T)}")
    print(f"요구 깊이 = 벽 3.0 + holder {HOLDER_DEPTH} = {NEED} mm\n")
    cache = {}
    for row, z0, labels in (("INDEX", index_z, ["I1", "I2", "I3", "I4"]),
                            ("MIDDLE", middle_z, ["M1", "M2", "M3", "M4"])):
        print(f"{'='*118}\n{row} row   Z = {z0:+.1f} mm\n{'='*118}")
        print(f"  {'btn':<4}{'s':>7}{'X':>8}{'Y':>8}{'Z':>7}  {'normal':>21}"
              f"{'ang':>7}{'wall':>7}{'depth':>8}{'holder':>8}{'screw':>9}  {'fit':<9}press")
        for lab, s in zip(labels, S_POS):
            r = surface_at(shell, z0, s, cache)
            if r is None:
                print(f"  {lab:<4} 표면 없음")
                continue
            p, n = r
            ang = math.degrees(math.atan2(n[0], -n[1]))
            walls, depths, obstr = envelope(shell, full, z0, s, cache)
            wall = min(walls) if walls else float("nan")
            dep = min(depths) if depths else float("nan")
            holder = dep - wall if dep != float("inf") else float("inf")
            sc, sk = screw_clearance(p, n)
            fit = ("YES" if (dep == float("inf") or dep >= NEED + 2) and sc > 2.0
                   else "MARGINAL" if (dep == float("inf") or dep >= NEED) and sc > 0.5
                   else "NO")
            ds = "inf" if dep == float("inf") else f"{dep:.1f}"
            hs = "inf" if holder == float("inf") else f"{holder:.1f}"
            print(f"  {lab:<4}{s:+7.1f}{p[0]:8.2f}{p[1]:8.2f}{z0:7.1f}  "
                  f"({n[0]:+5.2f},{n[1]:+5.2f},{n[2]:+5.2f}){ang:+7.1f}{wall:7.2f}"
                  f"{ds:>8}{hs:>8}{sc:8.2f}({sk}) {fit:<9}{press_kind(ang)}")
        print()


if __name__ == "__main__":
    iz = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    mz = float(sys.argv[2]) if len(sys.argv) > 2 else -6.0
    run(iz, mz)
