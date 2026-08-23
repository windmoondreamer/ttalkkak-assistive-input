"""사전 검증 A(C1/C2 나사 스택업) + B(배선 경로).

CAD WRITE 없음. 캐시된 중립 형상만 쓴다.
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

import stock_geom as sg                                    # noqa: E402

OUT = sg.OUT
SEAT = sg.SEAT_Z


def bbox(P):
    Q = np.asarray(P).reshape(-1, 3)
    return Q.min(0), Q.max(0)


def seg_hits(P, o, d, tmax, tmin=-60.0):
    """반직선(양방향) o+t*d 가 삼각형망 P 와 만나는 t 목록 (Moller-Trumbore)."""
    v0, v1, v2 = P[:, 0], P[:, 1], P[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    m = np.abs(a) > 1e-12
    f = np.zeros_like(a)
    f[m] = 1.0 / a[m]
    s = o - v0
    u = f * (s * h).sum(1)
    q = np.cross(s, e1)
    v = f * (q * d).sum(1)
    t = f * (e2 * q).sum(1)
    ok = m & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > tmin) & (t < tmax)
    return np.sort(t[ok])


def spans(ts, tol=1e-4):
    """정렬된 교차점 -> (진입, 이탈) 구간 목록."""
    ts = [t for i, t in enumerate(ts) if i == 0 or t - ts[i - 1] > tol]
    return [(ts[i], ts[i + 1]) for i in range(0, len(ts) - 1, 2)]


def main():
    N = sg.load(neutral=True)
    hw = json.load(io.open(os.path.join(OUT, "stock_hardware.json"), encoding="utf-8"))
    fr = json.load(io.open(os.path.join(OUT, "stock_frames.json"), encoding="utf-8"))
    Nb = np.array(fr["N"]["BASE"])
    piv = np.array(fr["PIVOT"])

    base = N["Base <1>"]
    rh1 = N["Roll_holder <1>"]
    rh2 = N["Roll_holder_2 <1>"]
    spacer = N["Spacer <1>"]
    lo_b, hi_b = bbox(base)
    BOT = lo_b[2]

    print("=" * 78)
    print("A. C1 / C2 나사 스택업")
    print("=" * 78)
    print(f"  Base 밑면 Z = {BOT:.4f}   (착좌면 아래 {SEAT - BOT:.3f} mm)")

    # --- 나사 위치를 중립 좌표로 ---
    rows = []
    for k, v in hw.items():
        if not v["base"].startswith("Hex socket head cap screw M3"):
            continue
        o = np.array(v["origin_deflected"])
        d = np.array(v["axis_deflected"])
        # 나사는 전부 BASE 프레임 체결 -> BASE 중립화 적용
        o = (o - piv) @ Nb.T + piv
        d = Nb @ d
        rows.append((k, o, d))

    print(f"\n  M3x16 나사 {len(rows)}개 (중립 좌표):")
    cand = []
    for k, o, d in sorted(rows, key=lambda r: (round(r[1][1], 2), round(r[1][0], 2))):
        # 밑면에서 접근 가능한가: 축이 대체로 +Z 이고 원점이 밑면 근처인가
        dn = d / np.linalg.norm(d)
        acc = abs(dn[2]) > 0.99 and abs(o[2] - BOT) < 3.0
        tag = "  <== 밑면 접근" if acc else ""
        print(f"    {k:<44s} o=({o[0]:7.2f},{o[1]:7.2f},{o[2]:9.2f}) "
              f"axis=({dn[0]:+.3f},{dn[1]:+.3f},{dn[2]:+.3f}){tag}")
        if acc:
            cand.append((k, o, dn))

    # --- 스택업: 각 후보 축을 따라 어떤 부품을 언제 통과하는가 ---
    parts = {"Base": base, "Roll_holder": rh1, "Roll_holder_2": rh2, "Spacer": spacer,
             "Roll": N["Roll <1>"], "Pitch": N["Pitch <1>"],
             "Spring_holder": N["Spring_holder <1>"]}
    print("\n  축방향 스택업 (t=0 은 나사 원점, +t 는 나사가 들어가는 방향):")
    stack = {}
    for k, o, dn in cand:
        # 나사 축을 +Z 로 통일 (밑면에서 위로)
        d = dn if dn[2] > 0 else -dn
        info = []
        for pn, P in parts.items():
            ts = seg_hits(P, o, d, tmax=80.0, tmin=-20.0)
            for a, b in spans(ts):
                info.append((a, b, pn))
        info.sort()
        name = "C1" if o[1] > 20 else "C2"
        stack[name] = {"key": k, "origin": o.tolist(), "axis": d.tolist(), "spans": info}
        print(f"\n    [{name}] XY=({o[0]:.3f}, {o[1]:.3f})  머리면 Z={o[2]:.3f} "
              f"(밑면 대비 {o[2]-BOT:+.3f} mm)")
        for a, b, pn in info:
            print(f"        t {a:8.3f} .. {b:8.3f}  ({b-a:6.3f} mm)  {pn}")

    json.dump({k: {kk: (vv if not isinstance(vv, list) or kk != 'spans'
                        else [[float(a), float(b), c] for a, b, c in vv])
                   for kk, vv in v.items()} for k, v in stack.items()},
              io.open(os.path.join(OUT, "c1c2_stackup.json"), "w", encoding="utf-8"),
              indent=1)

    # =============== B. 배선 ===============
    print("\n" + "=" * 78)
    print("B. 전장 / 배선 경로")
    print("=" * 78)
    elec = {k: v for k, v in N.items()
            if k.startswith(("micro", "atmega", "MICRO_", "Part "))}
    for k in sorted(elec):
        lo, hi = bbox(elec[k])
        print(f"  {k:<34s} X[{lo[0]:7.2f},{hi[0]:7.2f}] Y[{lo[1]:8.2f},{hi[1]:8.2f}] "
              f"Z[{lo[2]:9.2f},{hi[2]:9.2f}]")

    grp = [k for k in elec if k.startswith(("micro", "atmega", "MICRO_"))]
    E = np.concatenate([elec[k].reshape(-1, 3) for k in grp])
    lo, hi = E.min(0), E.max(0)
    print(f"\n  [MCU/USB 묶음] X[{lo[0]:.2f},{hi[0]:.2f}] Y[{lo[1]:.2f},{hi[1]:.2f}] "
          f"Z[{lo[2]:.2f},{hi[2]:.2f}]")
    print(f"     크기 {hi[0]-lo[0]:.2f} x {hi[1]-lo[1]:.2f} x {hi[2]-lo[2]:.2f} mm")
    print(f"     Base 밑면(Z={BOT:.3f}) 대비: 최저 {lo[2]-BOT:+.3f}  최고 {hi[2]-BOT:+.3f} mm")
    print(f"     Base -Y 끝(Y={lo_b[1]:.3f}) 대비: 최소 Y {lo[1]-lo_b[1]:+.3f} mm")

    hall = [k for k in elec if k.startswith("Part ")]
    H = np.concatenate([elec[k].reshape(-1, 3) for k in hall])
    hl, hh = H.min(0), H.max(0)
    print(f"\n  [홀 센서 2조] X[{hl[0]:.2f},{hh[0]:.2f}] Y[{hl[1]:.2f},{hh[1]:.2f}] "
          f"Z[{hl[2]:.2f},{hh[2]:.2f}]")
    print(f"     Base 윗면(Z={hi_b[2]:.3f}) 위 {hl[2]-hi_b[2]:+.3f} mm 부터")

    json.dump({"mcu_usb_bbox": [lo.tolist(), hi.tolist()],
               "hall_bbox": [hl.tolist(), hh.tolist()],
               "base_bbox": [lo_b.tolist(), hi_b.tolist()]},
              io.open(os.path.join(OUT, "wiring_envelope.json"), "w", encoding="utf-8"),
              indent=1)


if __name__ == "__main__":
    main()
