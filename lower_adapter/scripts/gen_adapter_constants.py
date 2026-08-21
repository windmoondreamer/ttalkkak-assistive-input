"""하부 어댑터 FeatureScript 상수 생성 + 사전 검증 (READ ONLY, 로컬 메시만 사용).

    python lower_adapter/scripts/gen_adapter_constants.py

출력:
    lower_adapter/cad_dump/adapter_constants.json   (수치)
    lower_adapter/cad/_profiles.fs.inc              (FS 프로파일 배열)

Onshape 에 접근하지 않는다.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
CADDIR = os.path.join(ROOT, "lower_adapter", "cad")

from mesh_probe import Mesh  # noqa: E402

# ---- 검증된 상체 인터페이스 (lower_adapter/docs/00) ----
FLANGE_Z = -67.878507
BOSS_Z = -73.878507
SOCKET_TOP = -52.878507
AXIS_Y = 27.269160
SOCKET_W, SOCKET_D = 21.072, 25.672
POST_W, POST_D = 20.272, 25.272
BOSS_W, BOSS_D = 31.072, 35.672
CENTROID = np.array([0.0, 25.996])
TILT_DEG = 20.0

# ---- 설계 파라미터 ----
RIM_CLR = 0.30      # 림 안쪽 여유
RIM_WALL = 4.00     # 림 벽 두께
RIM_H = 3.85        # 림 높이 = 클램프 링 밑면
CRADLE_DEPTH = 10.20
POCKET_CLR = 0.30
POCKET_DEPTH = 6.20
POST_TOP_GAP = 1.00     # post 끝 ~ 보어 막힌 끝
POST_WALL = 4.00
LIP_CAP = 5.00      # 립 물림(반경방향)
RING_T = 4.00
EAR_OD = 9.00
EAR_OUT = 5.00      # 이어 중심 = 플랜지 + 5.0
EAR_ANGLES = [30, 90, 150, 210, 270, 330]
BOLTS_CW = [(26.0, 8.0), (-26.0, 8.0), (26.0, 46.0), (-26.0, 46.0)]
SCREW_CLR_D = 3.40      # M3 관통
SCREW_PILOT_D = 2.50    # M3 셀프탭 하공
SPOTFACE_D = 6.50
SPOTFACE_DEPTH = 5.00
WEDGE_MIN = 10.00
GIMBAL_E1, GIMBAL_E2 = 28.0, 22.0
N = 72

R0, RC = 150.0, CENTROID


def main():
    mesh = Mesh(["INDEX_FINAL_JaD", "INDEX_FINAL_JfD"])

    def cast(o, d):
        h = mesh.raycast(o, d)
        h = h[0] if isinstance(h, tuple) else h
        try:
            t = np.asarray([e[0] for e in h], dtype=float)
        except Exception:
            t = np.asarray(h, dtype=float)
        return np.sort(t)

    th = np.deg2rad(np.arange(0, 360, 360.0 / N))

    def radii(z):
        out = []
        for t in th:
            d = np.array([-np.cos(t), -np.sin(t), 0.0])
            o = np.array([RC[0] + R0 * np.cos(t), RC[1] + R0 * np.sin(t), z])
            out.append(R0 - cast(o, d)[0])
        return np.array(out)

    r_fl = radii(-66.5)
    flange = np.column_stack([RC[0] + r_fl * np.cos(th), RC[1] + r_fl * np.sin(th)])

    ring_under = FLANGE_Z + RIM_H
    cradle_bot = FLANGE_Z - CRADLE_DEPTH
    pocket_floor = FLANGE_Z - POCKET_DEPTH
    post_top = SOCKET_TOP - POST_TOP_GAP
    r_body = radii(ring_under + 0.02)
    overhang = r_fl - r_body

    print("=" * 78)
    print("A. 프로파일")
    print("=" * 78)
    print(f"  플랜지 반경        {r_fl.min():.3f} ~ {r_fl.max():.3f} mm")
    print(f"  링 밑면 Z          {ring_under:.4f}  (= FLANGE_Z + {RIM_H})")
    print(f"  그 높이 본체 반경  {r_body.min():.3f} ~ {r_body.max():.3f}")
    print(f"  립 오버행          {overhang.min():.3f} ~ {overhang.max():.3f} mm")
    ok_lip = overhang.min() >= LIP_CAP + 0.5
    print(f"  립 물림 {LIP_CAP} + 본체여유 0.5 <= 오버행 min : {'PASS' if ok_lip else 'FAIL'} "
          f"(여유 {overhang.min() - LIP_CAP - 0.5:+.3f} mm)")

    worst = -1e9
    for i in range(N):
        u = np.array([np.cos(th[i]), np.sin(th[i])])
        for f in np.linspace(r_fl[i] - LIP_CAP, r_fl[i], 14):
            p = RC + u * f
            a = cast([p[0], p[1], -40.0], [0, 0, -1.0])
            if a.size:
                worst = max(worst, -40.0 - a[0])
    gap = ring_under - worst
    print(f"  립 밴드 어깨 최고 Z {worst:.4f}  -> 수직 유격 {gap:+.4f} mm "
          f"{'PASS' if gap > 0.15 else 'FAIL'}")

    print()
    print("=" * 78)
    print("B. 크래들")
    print("=" * 78)
    print(f"  착좌면 Z           {FLANGE_Z:.6f}")
    print(f"  바닥 Z             {cradle_bot:.6f}   두께 {CRADLE_DEPTH:.2f} mm")
    print(f"  보스 포켓          {BOSS_W + 2 * POCKET_CLR:.3f} x {BOSS_D + 2 * POCKET_CLR:.3f} "
          f"x 깊이 {POCKET_DEPTH:.2f}  (바닥 Z {pocket_floor:.4f})")
    print(f"  포켓 바닥 살       {pocket_floor - cradle_bot:.3f} mm")
    print(f"  post               {POST_W:.3f} x {POST_D:.3f}, Z {pocket_floor:.4f} -> {post_top:.4f} "
          f"(높이 {post_top - pocket_floor:.3f})")
    print(f"  보어 물림          {post_top - BOSS_Z:.3f} mm  / 직진 보어 {SOCKET_TOP - BOSS_Z:.3f}")
    print(f"  post 여유          X {(SOCKET_W - POST_W) / 2:.3f}  Y {(SOCKET_D - POST_D) / 2:.3f} mm/side")
    print(f"  케이블 보어        {POST_W - 2 * POST_WALL:.3f} x {POST_D - 2 * POST_WALL:.3f} mm")

    rim_out_max = r_fl + RIM_WALL + RIM_CLR
    plan = np.column_stack([RC[0] + rim_out_max * np.cos(th), RC[1] + rim_out_max * np.sin(th)])
    print(f"  림 외곽 plan       X[{plan[:, 0].min():.3f},{plan[:, 0].max():.3f}] "
          f"Y[{plan[:, 1].min():.3f},{plan[:, 1].max():.3f}]")

    print()
    print("  크래들->웨지 볼트 4개 (바닥에서 위로 탭)")
    for (x, y) in BOLTS_CW:
        v = np.array([x, y]) - RC
        r = np.linalg.norm(v)
        a = np.mod(np.degrees(np.arctan2(v[1], v[0])), 360)
        k = int(round(a / (360.0 / N))) % N
        d_pocket = max(abs(x) - (BOSS_W / 2 + POCKET_CLR), 0)
        d_cable = abs(x) - (POST_W / 2 - POST_WALL)
        print(f"    ({x:+6.1f},{y:+5.1f})  플랜지여유 {r_fl[k] - r:5.2f}  "
              f"포켓까지 {d_pocket:5.2f}  케이블보어까지 {d_cable:5.2f}  탭깊이 8.0/{CRADLE_DEPTH}")

    ears = []
    for a in EAR_ANGLES:
        k = int(round(a / (360.0 / N))) % N
        u = np.array([np.cos(th[k]), np.sin(th[k])])
        ears.append((RC + u * (r_fl[k] + EAR_OUT)).tolist())
    print(f"  클램프 이어 6개 OD {EAR_OD}, 중심 = 플랜지+{EAR_OUT} "
          f"(안쪽끝 플랜지+{EAR_OUT - EAR_OD / 2:.2f} >= 림여유 {RIM_CLR})")

    print()
    print("=" * 78)
    print("C. 웨지 — 20도 경사")
    print("=" * 78)
    t = np.deg2rad(TILT_DEG)
    up = np.array([0.0, np.sin(t), np.cos(t)])
    e1 = np.array([1.0, 0.0, 0.0])
    e2 = np.cross(up, e1)
    O = np.array([0.0, AXIS_Y, FLANGE_Z])
    print(f"  UP_LOCAL (월드 수직, 그립좌표)  ({up[0]:.6f}, {up[1]:.6f}, {up[2]:.6f})")
    print(f"  angle(UP_LOCAL, 소켓축 +Z)      {np.degrees(np.arccos(up[2])):.6f} deg")
    print(f"  e2 (월드 수평 오르막)           ({e2[0]:.6f}, {e2[1]:.6f}, {e2[2]:.6f})")

    ymin, ymax = plan[:, 1].min(), plan[:, 1].max()
    crit = np.array([0.0, ymin, cradle_bot]) - O
    H = WEDGE_MIN - float(np.dot(crit, up))
    H = float(np.ceil(H * 10) / 10)
    base_pt = O - H * up

    def thick(y):
        return float(np.dot(np.array([0.0, y, cradle_bot]) - O, up)) + H

    print(f"  스택 높이 H (기준면 -> MOUNT_ORIGIN)  {H:.3f} mm")
    print(f"  기준면 통과점 (그립좌표)  ({base_pt[0]:.4f}, {base_pt[1]:.4f}, {base_pt[2]:.4f})")
    print(f"  웨지 두께  최소 {thick(ymin):.3f} (y={ymin:.2f})  최대 {thick(ymax):.3f} (y={ymax:.2f})")

    def bottom_z(y):
        return FLANGE_Z - (H + (y - AXIS_Y) * up[1]) / up[2]

    print("  스포트페이스 (볼트머리 자리, +Z 축 평면)")
    spots = []
    for (x, y) in BOLTS_CW:
        bz = bottom_z(y)
        spots.append({"x": x, "y": y, "bottomZ": bz, "faceZ": bz + SPOTFACE_DEPTH})
        print(f"    ({x:+6.1f},{y:+5.1f})  웨지 밑면 Z {bz:9.3f}  머리자리 Z {bz + SPOTFACE_DEPTH:9.3f}")

    print("  짐벌 인터페이스 볼트 4개 (기준면 국소좌표 e1 x e2)")
    gim = []
    for sx in (+1, -1):
        for sy in (+1, -1):
            p = base_pt + sx * GIMBAL_E1 * e1 + sy * GIMBAL_E2 * e2
            v = p[:2] - RC
            r = np.linalg.norm(v)
            a = np.mod(np.degrees(np.arctan2(v[1], v[0])), 360)
            k = int(round(a / (360.0 / N))) % N
            depth = (cradle_bot - p[2]) / up[2]
            gim.append({"e1": sx * GIMBAL_E1, "e2": sy * GIMBAL_E2, "p": p.tolist(),
                        "edge": float(rim_out_max[k] - r), "thick": float(depth)})
            print(f"    e1{sx * GIMBAL_E1:+6.1f} e2{sy * GIMBAL_E2:+6.1f} -> 그립 "
                  f"({p[0]:+7.2f},{p[1]:+7.2f},{p[2]:+8.2f})  외곽여유 {rim_out_max[k] - r:5.2f}  "
                  f"재료두께 {depth:5.2f}  탭 8.0 {'PASS' if depth >= 10 and rim_out_max[k] - r >= 3 else 'FAIL'}")

    print()
    print("=" * 78)
    print("D. 최소 살두께 요약")
    print("=" * 78)
    walls = {
        "크래들 포켓 바닥": pocket_floor - cradle_bot,
        "post 벽": POST_WALL,
        "림 벽": RIM_WALL,
        "클램프 링": RING_T,
        "이어 벽(나사 2.5)": (EAR_OD - SCREW_PILOT_D) / 2,
        "웨지 최소": thick(ymin),
        "보스 슬리브 여유(정보)": POCKET_CLR,
    }
    for k, v in walls.items():
        print(f"  {k:24s} {v:6.3f} mm")

    cons = {
        "FLANGE_Z": FLANGE_Z, "BOSS_Z": BOSS_Z, "SOCKET_TOP": SOCKET_TOP, "AXIS_Y": AXIS_Y,
        "TILT_DEG": TILT_DEG, "UP_LOCAL": up.tolist(), "E2": e2.tolist(),
        "RIM_CLR": RIM_CLR, "RIM_WALL": RIM_WALL, "RIM_H": RIM_H,
        "CRADLE_DEPTH": CRADLE_DEPTH, "CRADLE_BOT": cradle_bot,
        "POCKET_W": BOSS_W + 2 * POCKET_CLR, "POCKET_D": BOSS_D + 2 * POCKET_CLR,
        "POCKET_DEPTH": POCKET_DEPTH, "POCKET_FLOOR": pocket_floor,
        "POST_W": POST_W, "POST_D": POST_D, "POST_TOP": post_top, "POST_WALL": POST_WALL,
        "LIP_CAP": LIP_CAP, "RING_T": RING_T, "RING_UNDER": ring_under,
        "EAR_OD": EAR_OD, "EARS": ears, "BOLTS_CW": BOLTS_CW, "SPOTS": spots,
        "SCREW_CLR_D": SCREW_CLR_D, "SCREW_PILOT_D": SCREW_PILOT_D,
        "SPOTFACE_D": SPOTFACE_D, "SPOTFACE_DEPTH": SPOTFACE_DEPTH,
        "STACK_H": H, "BASE_PT": base_pt.tolist(), "GIMBAL": gim,
        "WEDGE_MIN": thick(ymin), "WEDGE_MAX": thick(ymax),
        "FLANGE": flange.tolist(), "SPLIT_Y": float(CENTROID[1]),
        "lip_overhang_min": float(overhang.min()), "shoulder_gap": float(gap),
    }
    with open(os.path.join(OUT, "adapter_constants.json"), "w", encoding="utf-8") as f:
        json.dump(cons, f, indent=1)

    lines = ["// auto-generated by lower_adapter/scripts/gen_adapter_constants.py",
             "// flange outline %d pts, measured at Z=-66.5 (prismatic band)" % N,
             "const FLANGE_PTS = ["]
    for i, p in enumerate(flange):
        sep = "," if i < len(flange) - 1 else ""
        lines.append(f"    vector({p[0]:.4f}, {p[1]:.4f}) * millimeter{sep}")
    lines.append("];")
    lines.append("const EAR_PTS = [")
    for i, p in enumerate(ears):
        sep = "," if i < len(ears) - 1 else ""
        lines.append(f"    vector({p[0]:.4f}, {p[1]:.4f}) * millimeter{sep}")
    lines.append("];")
    with open(os.path.join(CADDIR, "_profiles.fs.inc"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print()
    print(f"  -> {os.path.join(OUT, 'adapter_constants.json')}")
    print(f"  -> {os.path.join(CADDIR, '_profiles.fs.inc')}")


if __name__ == "__main__":
    main()
