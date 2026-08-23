"""W2 인체공학 외피 FeatureScript 생성 (템플릿 + 실측 상수).

내부 공동/캐리어/스톡 인터페이스 상수는 컨포멀 코어에서 **그대로 가져온다**.
새로 계산하는 것은 로프트 스테이션(연속 외피) 과 USB 라우팅뿐이다.
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
CAD = os.path.join(ROOT, "lower_adapter", "cad")
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
K = json.load(io.open(os.path.join(OUT, "conformal_constants.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
DECK = C["DECK_Z"]
GROUND = K["GROUND"]
WALL = 5.0
N_STATION = 14           # 메인 로프트 스테이션 수


def fs_arr(rows, p=3):
    return "[" + ", ".join("[" + ", ".join(f"{v:.{p}f}" for v in r) + "]"
                           for r in rows) + "]"


def fs_num(v, p=4):
    return "[" + ", ".join(f"{x:.{p}f}" for x in v) + "]"


def main():
    cav = K["cav"]
    zlo = K["CAR_TOP"]

    # ---------- 메인 로프트 스테이션 ----------
    # outer(z) = (z 주변 창의 공동 최대) + WALL.  창을 스테이션 간격만큼 잡아야
    # 스테이션 사이 선형 보간이 항상 공동 + WALL 이상이 된다.
    zs = list(np.linspace(zlo, DECK, N_STATION))
    h = (DECK - zlo) / (N_STATION - 1)
    prof, rads = [], []
    for z in zs:
        lo, hi = z - h, z + h
        sel = [m for m in cav if m["z1"] > lo and m["z0"] < hi]
        if not sel:
            sel = [cav[0]]
        x0 = min(m["x0"] for m in sel) - WALL
        x1 = max(m["x1"] for m in sel) + WALL
        y0 = min(m["y0"] for m in sel) - WALL
        y1 = max(m["y1"] for m in sel) + WALL
        prof.append([x0, x1, y0, y1])
        rads.append(12.0)
    # 최하단 스테이션은 스커트(착좌 환형 + 접지) 폭
    prof[0] = list(K["SKIRT"])
    rads[0] = 14.0
    # 두 번째도 부드럽게 이어지도록 절반 확장
    prof[1] = [(prof[0][i] + prof[1][i]) / 2 for i in range(4)]
    rads[1] = 13.0

    # 검증: 모든 z 에서 공동 + WALL 이상인가 (선형 보간 기준)
    bad = 0
    for zz in np.arange(zlo, DECK, 0.5):
        t = np.clip((zz - zlo) / (DECK - zlo) * (N_STATION - 1), 0, N_STATION - 1.001)
        i = int(t)
        f = t - i
        p = [prof[i][k] + f * (prof[i + 1][k] - prof[i][k]) for k in range(4)]
        for m in cav:
            if not (m["z1"] > zz >= m["z0"]):
                continue
            if (m["x0"] - p[0] < WALL - 0.01 or p[1] - m["x1"] < WALL - 0.01
                    or m["y0"] - p[2] < WALL - 0.01 or p[3] - m["y1"] < WALL - 0.01):
                bad += 1
    print(f"로프트 벽 두께 검사: 위반 {bad} 지점 (0 이어야 한다)")

    # ---------- 손목 넥 로프트 스테이션 (Z 와 보간계수만; 폭은 FS 가 계산) ----------
    fz = list(np.linspace(K["GROUND"] and (GROUND - 0.342 * (-140)) / 0.9397 - 25.0
                          or zlo, DECK, 5))
    fz = list(np.linspace(-200.0, DECK, 5))
    ft = [(z - fz[0]) / (fz[-1] - fz[0]) for z in fz]

    # ---------- USB 라우팅 ----------
    ez = json.load(io.open(os.path.join(OUT, "wiring_envelope.json"), encoding="utf-8"))
    ulo, uhi = ez["mcu_usb_bbox"]
    # 채널 바닥을 커넥터 바로 아래까지만 내려야 지면 평면과 늦게 만난다
    # (지면은 -Y 로 갈수록 grip Z 가 가파르게 올라온다)
    USB_Z0 = ulo[2] - 0.8
    USB_Z1 = ulo[2] + 10.2
    # A: 커넥터 앞 플러그 공간 (-Y).  지면 평면이 Y=-78 부근에서 USB_Z0 를 만나므로
    #    그보다 앞으로는 못 간다 -> 직각(90deg) 플러그 전제.
    y_break = (GROUND - 0.9397 * USB_Z0) / 0.342
    USB_A = [-10.0, 10.0, max(y_break + 2.0, -80.0), -52.0]
    # B: 측면(-X) 인출
    USB_B = [-70.0, 0.0, USB_A[2], USB_A[2] + 13.0]
    print(f"USB  Z [{USB_Z0:.2f}, {USB_Z1:.2f}]   지면 교차 Y = {y_break:.2f}")
    print(f"  A(플러그 공간) {USB_A}   커넥터면(-63.95) 앞 {abs(USB_A[2]+63.95):.1f} mm")
    print(f"  B(측면 인출)   {USB_B}")

    L = []
    a = L.append
    a("// ---- 스톡 인터페이스 (코어와 동일, 변경 금지) ----")
    for k, v in (("CX", C["CX"]), ("CY", C["CY"]), ("BODY_W", 100.0),
                 ("BODY_D", 100.0), ("BASE_BOT", C["BASE_BOT"]),
                 ("TAIL_CX", 0.3544), ("TAIL_W0", 28.0), ("C_X", C["C1"][0]),
                 ("C1_Y", C["C1"][1]), ("C2_Y", C["C2"][1]), ("C_SLOT_L", 11.4),
                 ("CAR_TOP", K["CAR_TOP"]), ("CAR_BOT", K["CAR_BOT"]),
                 ("M3_CLR", 3.4), ("M3_CB", 6.6), ("CB_D", 3.5),
                 ("INSERT_D", 4.0), ("INSERT_L", 8.0),
                 ("DECK_Z", DECK), ("D_GROUND", GROUND),
                 ("GROUND_ZMIN", -220.5519)):
        a(f"const {k} = {v:.6f};")
    a("")
    a("// ---- 내부 공동 (코어와 **완전히 동일**) ----")
    a(f"const CAV = {fs_arr([[m['x0'], m['x1'], m['y0'], m['y1']] for m in cav])};")
    a(f"const CAV_Z = {fs_num([m['z0'] for m in cav] + [cav[-1]['z1']])};")
    a(f"const TAIL_CAV = {fs_arr([K['TAIL_CAV']])[1:-1]};")
    a(f"const TAIL_CAV_Z = {fs_num(K['TAIL_CAV_Z'])};")
    a(f"const CAR_OPEN = {fs_arr([K['CAR_OPEN']])[1:-1]};")
    a(f"const TAIL_CAR_OPEN = {fs_arr([K['TAIL_CAR_OPEN']])[1:-1]};")
    a(f"const CARRIER = {fs_arr([K['CARRIER']])[1:-1]};")
    a(f"const SKIRT = {fs_arr([K['SKIRT']])[1:-1]};")
    a(f"const SCREWS = {fs_arr(K['SCREWS'])};")
    a("")
    a("// ---- 연속 외피 로프트 스테이션 (신규) ----")
    a(f"const MAIN_PROF = {fs_arr(prof)};")
    a(f"const MAIN_Z = {fs_num(zs)};")
    a(f"const MAIN_R = {fs_num(rads, 2)};")
    a(f"const FRONT_Z = {fs_num(fz)};")
    a(f"const FRONT_T = {fs_num(ft)};")
    a("")
    a("// ---- USB / 케이블 라우팅 (측면 -X 인출) ----")
    a(f"const USB_A = {fs_arr([USB_A])[1:-1]};")
    a(f"const USB_B = {fs_arr([USB_B])[1:-1]};")
    a(f"const USB_Z0 = {USB_Z0:.4f};")
    a(f"const USB_Z1 = {USB_Z1:.4f};")

    tmpl = io.open(os.path.join(CAD, "OneGrip_Ergo.fs.tmpl"), encoding="utf-8").read()
    io.open(os.path.join(CAD, "OneGrip_Ergo.fs"), "w", encoding="utf-8").write(
        tmpl.replace("//GENERATED", "\n".join(L)))

    print(f"\n메인 로프트 스테이션 {len(zs)}개  Z {zs[0]:.2f} .. {zs[-1]:.2f}")
    for z, p, r in zip(zs, prof, rads):
        print(f"   Z {z:9.3f}  {p[1]-p[0]:7.2f} x {p[3]-p[2]:7.2f}   "
              f"X {p[0]:7.2f}..{p[1]:6.2f}  Y {p[2]:7.2f}..{p[3]:6.2f}  R{r:.0f}")
    print(f"\n손목 넥 스테이션 {len(fz)}개  Z {fz[0]:.1f} .. {fz[-1]:.2f}")
    print("\n생성: lower_adapter/cad/OneGrip_Ergo.fs")


if __name__ == "__main__":
    main()
