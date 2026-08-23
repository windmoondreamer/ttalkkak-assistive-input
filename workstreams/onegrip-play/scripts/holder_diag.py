"""INDEX holder 접선방향 wall thickness 정밀 진단 (READ ONLY, 로컬 계산만).

핵심 원칙:
  holder body 만 따로 세지 않는다. shell 3mm 벽과 holder 가 UNION 되어 하나가 된
  영역도 구조재로 인정하고, 6.4mm pocket 경계에서 가장 가까운 VOID 까지의
  실제 solid 두께(effective structural wall)를 측정한다.

측정 방법:
  버튼 축에 수직인 선(u축 / v축)을 따라 레이를 한 번 쏘아 재료 구간을 모두 얻고,
  pocket 경계(|s|=3.2)에서 바깥으로 연속된 재료가 끝나는 지점까지의 거리를 잰다.
  (점별 parity 판정은 곡면/접선 교차에서 불안정하므로 쓰지 않는다.)

예측(stage A/B/C)은 baseline 메시 + 해석적 박스로 재구성한다.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from mesh_probe import Mesh  # noqa: E402

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")

# cad/OneGrip_FingerButtons.fs 의 IDX 상수와 동일한 값 (FS 가 실제로 쓰는 값)
FS_IDX = [
    ("I1", (-22.224, -17.494, 9.000), (-0.9291, -0.2385, -0.2828), True, False),
    ("I2", (-15.970, -26.208, 9.000), (-0.4724, -0.7368, -0.4838), True, False),
    ("I3", (-5.496, -29.325, 9.000), (-0.0383, -0.9556, -0.2921), True, True),
    ("I4", (5.496, -29.325, 9.000), (0.0383, -0.9556, -0.2921), False, True),
]

CAP_W = 8.0        # 개구부
POCKET_W = 6.4     # 스위치 포켓
HOLDER_W = 12.4    # pocket 6.4 + 2 x 3.0
SHELL_WALL = 3.0
FUSE = 0.2
HOLDER_DEPTH = 10.0
DEPTHS = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]


def basis(n_raw):
    """FS 와 동일한 순서로 basis 를 만든다: zA=normalize(n), xA=norm(cross(z_glob,zA)), yA=cross(zA,xA)."""
    n = np.asarray(n_raw, dtype=float)
    zA = n / np.linalg.norm(n)
    xA = np.cross([0.0, 0.0, 1.0], zA)
    xA = xA / np.linalg.norm(xA)
    yA = np.cross(zA, xA)
    return xA, yA, zA


def segments(mesh, origin, direction, span=200.0):
    """origin 을 지나는 직선을 따라 재료 구간 [(a,b), ...] 을 좌표(부호 포함)로 반환."""
    d = np.asarray(direction, dtype=float)
    d = d / np.linalg.norm(d)
    start = np.asarray(origin, dtype=float) - d * span
    hits = mesh.hits_dedup(start, d, tol=1e-3)
    ts = [t - span for t, _ in hits]
    if len(ts) % 2 == 1:            # 접선 교차 등으로 홀수면 마지막을 버린다
        ts = ts[:-1]
    return [(ts[i], ts[i + 1]) for i in range(0, len(ts), 2)]


def in_segments(segs, s, eps=1e-6):
    return any(a - eps <= s <= b + eps for a, b in segs)


def wall_from_pocket(segs, side, half=POCKET_W / 2, step=0.02, limit=15.0):
    """pocket 경계에서 side(+1/-1) 방향으로 연속 재료가 끝나는 지점까지의 두께."""
    s0 = side * half
    if not in_segments(segs, s0):
        return 0.0
    s = s0
    while abs(s - s0) < limit:
        s += side * step
        if not in_segments(segs, s):
            break
    return abs(s - s0) - step


def analytic_material(local_xy_axis_idx, x, depth, p, bas, dom, clip, base_segs_lookup):
    """해석적 stage C 판정은 호출부에서 처리 (여기서는 박스 판정만)."""
    raise NotImplementedError


def box_flags(x, y, depth):
    """로컬 좌표(x=u, y=v, depth) 가 각 박스 안인지."""
    op = abs(x) <= CAP_W / 2 and abs(y) <= CAP_W / 2 and -3.0 <= depth <= 12.0
    ho = (abs(x) <= HOLDER_W / 2 and abs(y) <= HOLDER_W / 2
          and (SHELL_WALL - FUSE) <= depth <= (SHELL_WALL + HOLDER_DEPTH))
    po = abs(x) <= POCKET_W / 2 and abs(y) <= POCKET_W / 2 and -1.0 <= depth <= 14.0
    return op, ho, po


def load():
    cur = {"Joystick_1": Mesh(["Joystick_1"]), "Joystick_2": Mesh(["Joystick_2"])}
    base = {"Joystick_1": Mesh(["Joystick_1_baseline"]),
            "Joystick_2": Mesh(["Joystick_2_baseline"])}
    return cur, base


def run():
    cur, base = load()
    print("=" * 108)
    print("1) FeatureScript basis 직교정규성 검증 (FS 가 실제로 쓰는 반올림된 법선 기준)")
    print("=" * 108)
    print(f"  {'btn':<4}{'|n_raw|':>10}{'|u|':>8}{'|v|':>8}{'|n|':>8}"
          f"{'u·v':>12}{'v·n':>12}{'u·n':>12}{'handed':>9}")
    B = {}
    for nm, p, nr, dom, clip in FS_IDX:
        u, v, z = basis(nr)
        B[nm] = (np.array(p), u, v, z, dom, clip)
        hand = float(np.dot(np.cross(u, v), z))
        print(f"  {nm:<4}{np.linalg.norm(nr):10.6f}{np.linalg.norm(u):8.5f}"
              f"{np.linalg.norm(v):8.5f}{np.linalg.norm(z):8.5f}"
              f"{np.dot(u, v):12.2e}{np.dot(v, z):12.2e}{np.dot(u, z):12.2e}{hand:9.5f}")

    print()
    print("=" * 108)
    print("2) effective structural wall — pocket(6.4mm) 경계에서 첫 VOID 까지 (mm)")
    print("   actual = 현재 CAD 실측 / predicted = baseline + 해석적 박스로 재구성한 stage C")
    print("=" * 108)
    result = {}
    for nm, p, nr, dom, clip in FS_IDX:
        _, u, v, z, _, _ = B[nm]
        shell = "Joystick_2" if p[0] < 0 else "Joystick_1"
        M, MB = cur[shell], base[shell]
        print(f"\n  --- {nm}  ({shell})  center=({p[0]:.3f},{p[1]:.3f},{p[2]:.3f})")
        print(f"      {'depth':>6} | {'u- act':>7}{'u- pre':>8} | {'u+ act':>7}{'u+ pre':>8}"
              f" | {'v- act':>7}{'v- pre':>8} | {'v+ act':>7}{'v+ pre':>8}")
        rows = {}
        for d in DEPTHS:
            c = np.array(p) - z * d
            out = {}
            for axis, ax in (("u", u), ("v", v)):
                seg_a = segments(M, c, ax)
                seg_b = segments(MB, c, ax)          # baseline (수정 전)

                def pred_in(s):
                    x = s if axis == "u" else 0.0
                    y = 0.0 if axis == "u" else s
                    op, ho, po = box_flags(x, y, d)
                    if clip:
                        q = c + ax * s
                        if dom and q[0] > 0:
                            ho = False
                        if (not dom) and q[0] < 0:
                            ho = False
                    mat = (in_segments(seg_b, s) and not op) or ho
                    return mat and not po

                def pred_wall(side, step=0.02, limit=15.0):
                    s0 = side * POCKET_W / 2
                    if not pred_in(s0):
                        return 0.0
                    s = s0
                    while abs(s - s0) < limit:
                        s += side * step
                        if not pred_in(s):
                            break
                    return abs(s - s0) - step

                out[axis + "-"] = (wall_from_pocket(seg_a, -1), pred_wall(-1))
                out[axis + "+"] = (wall_from_pocket(seg_a, +1), pred_wall(+1))
            rows[d] = out
            print(f"      {d:6.1f} | {out['u-'][0]:7.2f}{out['u-'][1]:8.2f} |"
                  f" {out['u+'][0]:7.2f}{out['u+'][1]:8.2f} |"
                  f" {out['v-'][0]:7.2f}{out['v-'][1]:8.2f} |"
                  f" {out['v+'][0]:7.2f}{out['v+'][1]:8.2f}")
        result[nm] = rows
    return B, result


if __name__ == "__main__":
    run()
