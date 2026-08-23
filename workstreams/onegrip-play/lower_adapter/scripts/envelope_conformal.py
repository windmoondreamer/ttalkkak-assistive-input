"""§17 — 스톡 모듈 필요 내부 포락선 계산 (CAD WRITE 없음).

    STOCK_FIXED_ENVELOPE
    STOCK_MOVING_ENVELOPE_+-10   (9자세)
    ELECTRONICS_ENVELOPE
    CABLE_SERVICE_ENVELOPE       (provisional)
    ASSEMBLY_EXTRACTION_ENVELOPE (하방 인출 스윕)
      -> REQUIRED_INTERNAL_ENVELOPE

포락선은 Z 슬라이스별 **평면 실루엣**으로 낸다. 단일 프리즘(=상자)으로 뭉개지 않는다.
전장 꼬리는 본체와 폭이 크게 다르므로 **본체 / 꼬리 두 영역으로 분리**해서 잡는다.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import stock_geom as sg                                  # noqa: E402

OUT = sg.OUT
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
PIV = np.array(C["PIVOT"])
SEAT_Z = C["SEAT_Z"]
HAND = np.array(C["HAND_REF"])

FIXED = ("Base <1>", "Roll_holder <1>", "Roll_holder_2 <1>", "Spacer <1>")
# OneGrip 상체는 Pitch post 에서 뽑히는 **별도 모듈**이다.
# 정비 순서가 "그립을 먼저 뽑고 -> 바닥판 제거 -> 짐벌 하강" 이므로
# 인출 스윕에는 그립 쉘을 넣지 않는다. (동작 포락선에는 당연히 포함한다)
GRIP_SHELL = ("Joystick_1 <1>", "Joystick_2 <1>", "Backplate <1>",
              "Small_joystick_attachment <1>", "HW504_B <1>", "HW504_B <2>")
TRAVEL = 10.0
STEP = 1.0                     # Z 슬라이스
GRID = 1.0                     # 평면 격자
FDM = 1.5                      # 이동부 여유 (편측)
FDM_FIX = 0.6                  # 고정부 여유 (편측)
TAIL_SPLIT_Y = -23.310850      # 본체 / 꼬리 경계


def rotm(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def slab_occ(pts, zs, xs, ys, half=STEP / 2):
    """정점 구름을 Z 슬라이스별 평면 점유 격자로."""
    occ = np.zeros((len(zs), len(ys), len(xs)), bool)
    ix = np.clip(((pts[:, 0] - xs[0]) / GRID).round().astype(int), 0, len(xs) - 1)
    iy = np.clip(((pts[:, 1] - ys[0]) / GRID).round().astype(int), 0, len(ys) - 1)
    for k, z in enumerate(zs):
        m = np.abs(pts[:, 2] - z) <= half
        if m.any():
            occ[k, iy[m], ix[m]] = True
    return occ


def dilate(occ, r):
    """평면 방향 사각 팽창 (여유 부여)."""
    n = int(round(r / GRID))
    if n <= 0:
        return occ
    o = occ.copy()
    for _ in range(n):
        p = o.copy()
        p[:, 1:, :] |= o[:, :-1, :]
        p[:, :-1, :] |= o[:, 1:, :]
        p[:, :, 1:] |= o[:, :, :-1]
        p[:, :, :-1] |= o[:, :, 1:]
        o = p
    return o


def rects(occ, zs, xs, ys, split=TAIL_SPLIT_Y):
    """슬라이스별 (본체, 꼬리) 경계 사각. 없으면 None."""
    jsplit = int(round((split - ys[0]) / GRID))
    out = []
    for k in range(len(zs)):
        row = {}
        for tag, sl in (("body", slice(jsplit, None)), ("tail", slice(0, jsplit))):
            sub = occ[k, sl, :]
            if not sub.any():
                row[tag] = None
                continue
            jj, ii = np.where(sub)
            y0 = ys[sl][jj.min()]
            y1 = ys[sl][jj.max()]
            row[tag] = (float(xs[ii.min()]), float(xs[ii.max()]),
                        float(y0), float(y1), int(sub.sum()))
        out.append(row)
    return out


def main():
    N = sg.load(neutral=True)
    keys = list(N)
    elec_keys = [k for k in keys if k.startswith(("micro", "atmega", "MICRO_"))]
    grip_frame = [k for k in keys if k not in FIXED and k != "Roll <1>"
                  and k not in elec_keys]

    # ---- 격자 ----
    allpts = np.concatenate([N[k].reshape(-1, 3) for k in keys])
    zmin = allpts[:, 2].min()
    zs = np.arange(np.floor(zmin), SEAT_Z + 8.0, STEP)
    xs = np.arange(-70.0, 70.01, GRID)
    ys = np.arange(-80.0, 100.01, GRID)

    # ---- 1. FIXED ----
    P = np.concatenate([N[k].reshape(-1, 3) for k in FIXED])
    occ_fix = slab_occ(P, zs, xs, ys)
    print(f"STOCK_FIXED_ENVELOPE       정점 {len(P):8d}")

    # ---- 2. MOVING (9자세) ----
    cfgs = [("neutral", 0, 0), ("X+10", TRAVEL, 0), ("X-10", -TRAVEL, 0),
            ("Y+10", 0, TRAVEL), ("Y-10", 0, -TRAVEL),
            ("X+10Y+10", TRAVEL, TRAVEL), ("X+10Y-10", TRAVEL, -TRAVEL),
            ("X-10Y+10", -TRAVEL, TRAVEL), ("X-10Y-10", -TRAVEL, -TRAVEL)]
    occ_mov = np.zeros_like(occ_fix)
    nm = 0
    for name, beta, alpha in cfgs:
        Ry = rotm("y", alpha)
        R = Ry @ rotm("x", beta)
        pts = []
        for k in grip_frame:
            Q = N[k].reshape(-1, 3)
            pts.append((Q - PIV) @ R.T + PIV)
        Q = N["Roll <1>"].reshape(-1, 3)
        pts.append((Q - PIV) @ Ry.T + PIV)
        Q = np.concatenate(pts)
        nm = len(Q)
        occ_mov |= slab_occ(Q, zs, xs, ys)
    print(f"STOCK_MOVING_ENVELOPE_+-10 자세 {len(cfgs)}, 자세당 정점 {nm:8d}")

    # ---- 3. ELECTRONICS ----
    E = np.concatenate([N[k].reshape(-1, 3) for k in elec_keys])
    occ_el = slab_occ(E, zs, xs, ys)
    el_lo, el_hi = E.min(0), E.max(0)
    print(f"ELECTRONICS_ENVELOPE       X[{el_lo[0]:7.2f},{el_hi[0]:7.2f}] "
          f"Y[{el_lo[1]:8.2f},{el_hi[1]:8.2f}] Z[{el_lo[2]:9.2f},{el_hi[2]:9.2f}]")

    # ---- 4. CABLE_SERVICE (provisional) ----
    #   스톡 CAD 에 전장 포켓/커넥터/케이블이 없다 -> 보수적 서비스 볼륨.
    #   USB 플러그 몸체(약 12 x 7)만 하우징 **안쪽**에 확보하고,
    #   굽힘 반경/스트레인 릴리프는 하우징 벽의 **포트(구멍)** 로 처리한다.
    #   -> 불필요한 큰 공동을 만들지 않는다 (지시 §13).
    CAB = {"x": (-6.5, 6.5), "y": (-72.0, -55.0),
           "z": (float(el_lo[2]) - 2.5, float(el_lo[2]) + 9.0)}
    occ_cab = np.zeros_like(occ_fix)
    for k, z in enumerate(zs):
        if CAB["z"][0] <= z <= CAB["z"][1]:
            i0 = int((CAB["x"][0] - xs[0]) / GRID)
            i1 = int((CAB["x"][1] - xs[0]) / GRID)
            j0 = max(0, int((CAB["y"][0] - ys[0]) / GRID))
            j1 = int((CAB["y"][1] - ys[0]) / GRID)
            occ_cab[k, j0:j1 + 1, i0:i1 + 1] = True
    print(f"CABLE_SERVICE_ENVELOPE     X{CAB['x']} Y{CAB['y']} Z"
          f"({CAB['z'][0]:.2f},{CAB['z'][1]:.2f})  provisional")

    # ---- 5. 여유 부여 후 합집합 ----
    req = (dilate(occ_fix | occ_el, FDM_FIX) | dilate(occ_mov, FDM) | occ_cab)

    # ---- 6. ASSEMBLY_EXTRACTION (하방 -Z 스윕) ----
    #   그립을 먼저 뽑고 **중립 상태**로 내린다.
    #   (편향 자세로 뽑지 않으므로 9자세 포락선을 스윕할 이유가 없다)
    pts = [N[k].reshape(-1, 3) for k in FIXED] +           [N[k].reshape(-1, 3) for k in elec_keys] +           [N[k].reshape(-1, 3) for k in grip_frame if k not in GRIP_SHELL] +           [N["Roll <1>"].reshape(-1, 3)]
    occ_pull = dilate(slab_occ(np.concatenate(pts), zs, xs, ys), FDM)
    ext = occ_pull.copy()
    for k in range(len(zs) - 2, -1, -1):
        ext[k] |= ext[k + 1]
    ext |= req                       # 동작 포락선은 스윕 없이 그대로 필요하다
    print("ASSEMBLY_EXTRACTION_ENVELOPE  -Z 스윕 누적 적용")

    r_req = rects(req, zs, xs, ys)
    r_ext = rects(ext, zs, xs, ys)

    print("\n" + "=" * 96)
    print("REQUIRED_INTERNAL_ENVELOPE  (Z 슬라이스별, mm)")
    print("=" * 96)
    print(f"{'Z':>9s} {'착좌면대비':>8s} | {'본체 X':>16s} {'본체 Y':>16s} {'크기':>15s} "
          f"| {'꼬리 X':>15s} {'꼬리 Y':>15s}")
    prev = None
    for k, z in enumerate(zs):
        b, t = r_ext[k]["body"], r_ext[k]["tail"]
        if b is None and t is None:
            continue
        sb = (f"{b[0]:7.1f}..{b[1]:6.1f} {b[2]:8.1f}..{b[3]:6.1f} "
              f"{b[1]-b[0]:6.1f}x{b[3]-b[2]:6.1f}") if b else " " * 47
        st = (f"{t[0]:6.1f}..{t[1]:6.1f} {t[2]:7.1f}..{t[3]:6.1f}") if t else ""
        line = sb + " | " + st
        key = (None if b is None else tuple(round(v) for v in b[:4]),
               None if t is None else tuple(round(v) for v in t[:4]))
        if key != prev:
            print(f"{z:9.2f} {z-SEAT_Z:8.2f} | {line}")
            prev = key

    # ---- 7. 요약 ----
    def glob(rr):
        xs_, ys_ = [], []
        for row in rr:
            for tag in ("body", "tail"):
                if row[tag]:
                    xs_ += [row[tag][0], row[tag][1]]
                    ys_ += [row[tag][2], row[tag][3]]
        return min(xs_), max(xs_), min(ys_), max(ys_)

    gb = glob(r_ext)
    zlo = min(z for k, z in enumerate(zs) if r_ext[k]["body"] or r_ext[k]["tail"])
    print("\n" + "=" * 96)
    print("요약")
    print("=" * 96)
    print(f"  전체 bbox        X[{gb[0]:.1f},{gb[1]:.1f}] Y[{gb[2]:.1f},{gb[3]:.1f}] "
          f"= {gb[1]-gb[0]:.1f} x {gb[3]-gb[2]:.1f}")
    print(f"  Z 범위           [{zlo:.2f}, {SEAT_Z:.2f}]  깊이 {SEAT_Z-zlo:.2f} mm")
    vol = ext.sum() * GRID * GRID * STEP
    vol_req = req.sum() * GRID * GRID * STEP
    box = (gb[1] - gb[0]) * (gb[3] - gb[2]) * (SEAT_Z - zlo)
    print(f"  포락선 부피      req {vol_req/1000:9.1f} cm3   +인출스윕 {vol/1000:9.1f} cm3")
    print(f"  단일 상자였다면   {box/1000:9.1f} cm3   -> 컨포멀 절감 {100*(1-vol/box):.1f}%")

    # 월드수직 최저
    lows = {k: float((N[k].reshape(-1, 3) @ UP).min()) for k in keys}
    worst = sorted(lows.items(), key=lambda x: x[1])[:6]
    print("\n  월드수직 최저 부품 (하우징 바닥을 결정한다)")
    for k, v in worst:
        print(f"    {k:<34s} {v:10.4f}")

    np.savez_compressed(os.path.join(OUT, "conformal_envelope.npz"),
                        zs=zs, xs=xs, ys=ys, req=req, ext=ext,
                        occ_fix=occ_fix, occ_mov=occ_mov, occ_el=occ_el, occ_cab=occ_cab)
    json.dump({"zs": zs.tolist(), "rects_ext": r_ext, "rects_req": r_req,
               "cable": CAB, "bbox": list(gb), "z_low": float(zlo),
               "vol_ext_mm3": float(vol), "vol_req_mm3": float(vol_req),
               "low_world": lows},
              io.open(os.path.join(OUT, "conformal_envelope.json"), "w",
                      encoding="utf-8"), indent=1)
    print("\n저장: conformal_envelope.npz / .json")


if __name__ == "__main__":
    main()
