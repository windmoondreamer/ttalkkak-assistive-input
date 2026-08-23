"""손목 받침 외피 3안 사이징 (제안 단계, CAD WRITE 없음).

코어(CONFORMAL_STOCK_EMBED_V1)는 건드리지 않는다.
덱 평면 위 -Y 쪽에 '손목 패드 쐐기' 를 얹고, 그 아래를 지면까지 받치는 형태로만 계산한다.
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
K = json.load(io.open(os.path.join(OUT, "conformal_constants.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
DECK = C["DECK_Z"]
GROUND = K["GROUND"]
U = np.array([0.0, 1.0, 0.0])
U = U - (U @ UP) * UP
U /= np.linalg.norm(U)

ANCHOR_Y = -20.0                     # 패드가 시작하는 grip Y (그립 스윕 -10.5 보다 안전측)
SHELL_T = 4.0                        # 외피 살 두께
PAD_T = 6.0                          # 손목 닿는 면 살 두께

# 현재 상태
CUR = {"Y0": min(K["SKIRT"][2], K["TAIL_SKIRT"][2]), "Y1": K["SKIRT"][3],
       "W": K["SKIRT"][1] - K["SKIRT"][0], "vol": 495615.0}


def w2g(u, h):
    """월드 (u, h) -> grip (Y, Z)."""
    return u * U[1] + h * UP[1], u * U[2] + h * UP[2]


def g2w(y, z):
    return y * U[1] + z * U[2], y * UP[1] + z * UP[2]


def ground_y(u):
    """월드 u 에서 지면 평면 위 점의 grip Y."""
    return (u - (-0.364 * GROUND)) / 1.0642


VARIANTS = [
    dict(name="W1 COMPACT", phi=8.0, L=55.0, wpad=70.0, base_u=-46.0, rad=12.0,
         desc="손목 받침 턱. 최소 확장"),
    dict(name="W2 BALANCED", phi=7.0, L=85.0, wpad=86.0, base_u=-74.0, rad=16.0,
         desc="손목 받침 + 상부 곡면화 + 측면 살짝 감쌈"),
    dict(name="W3 FULLER", phi=6.0, L=120.0, wpad=96.0, base_u=-106.0, rad=20.0,
         desc="손바닥+전완 받침. 측면 윙 포함"),
]


def main():
    au, ah = g2w(ANCHOR_Y, DECK)
    hu, hh = float(HAND @ U), float(HAND @ UP)
    cur_front_u = 1.0642 * CUR["Y0"] + (-0.364 * GROUND)

    print("=" * 92)
    print("기준 (현재 CONFORMAL_STOCK_EMBED_V1, 코어 무수정)")
    print("=" * 92)
    print(f"  HAND_REF            world (u {hu:7.2f}, h {hh:7.2f})   지면 위 {hh-GROUND:6.1f} mm")
    print(f"  패드 앵커 grip Y={ANCHOR_Y}  world (u {au:7.2f}, h {ah:7.2f})   "
          f"지면 위 {ah-GROUND:6.1f} mm")
    print(f"  손 - 앵커 높이차     {hh-ah:6.1f} mm")
    print(f"  현재 접지 앞끝       world u {cur_front_u:7.2f}   (grip Y {CUR['Y0']:.1f})")
    print(f"  현재 외형           {CUR['W']:.1f} x {CUR['Y1']-CUR['Y0']:.1f} mm, "
          f"부피 {CUR['vol']:,.0f} mm3")
    print(f"  그립 스윕 -Y 한계    덱 평면에서 Y = -10.51  -> 앵커 -20.0 은 "
          f"{-10.51-ANCHOR_Y:.1f} mm 여유")

    rows = []
    print("\n" + "=" * 92)
    for v in VARIANTS:
        phi, L, wpad = v["phi"], v["L"], v["wpad"]
        t = np.tan(np.radians(phi))
        fu = au - L                       # 패드 앞끝 world u
        fh = ah - L * t
        fy, fz = w2g(fu, fh)
        # 패드 쐐기 부피 (덱 평면 ~ 패드 평면, 삼각 단면)
        wedge = 0.5 * L * (L * t) * wpad
        # 베이스 확장: 앞으로 밀어낸 접지 구간의 셸 부피 근사
        ext_u = cur_front_u - v["base_u"]     # world 수평 확장량
        # 확장 구간의 평균 높이 (지면 -> 패드/덱 평면)
        h_mid = 0.5 * ((ah - (cur_front_u - au) * -t) + fh) - GROUND
        # 셸 근사: 둘레 x 살두께 x 높이 + 상하면
        peri = 2 * (wpad + ext_u)
        base_shell = peri * SHELL_T * h_mid * 0.5 + wpad * ext_u * PAD_T
        add_vol = wedge * 0.45 + base_shell    # 쐐기도 중공
        pad_area = wpad * L * 0.88             # 라운드 감안
        foot_add = wpad * ext_u * 0.8
        overhang = v["base_u"] - fu            # 접지 앞끝 대비 패드 돌출 (음수면 안쪽)
        tot_Y0 = ground_y(v["base_u"])
        rows.append(dict(v, fu=fu, fh=fh, fy=fy, fz=fz, wedge=wedge,
                         add_vol=add_vol, pad_area=pad_area, foot_add=foot_add,
                         overhang=overhang, tot_Y0=tot_Y0,
                         L_total=CUR["Y1"] - min(tot_Y0, fy),
                         drop=hh - fh))
        print(f"[{v['name']}]  {v['desc']}")
        print(f"   패드    상승각 {phi:.0f} deg, 길이 {L:.0f} mm, 폭 {wpad:.0f} mm, "
              f"모서리 R{v['rad']:.0f}")
        print(f"   앞끝    world (u {fu:7.2f}, h {fh:7.2f})   지면 위 {fh-GROUND:6.1f} mm"
              f"   grip (Y {fy:7.2f}, Z {fz:7.2f}, 덱 대비 {fz-DECK:+6.2f})")
        print(f"   손목 낙차 (HAND_REF -> 패드 앞끝)  {hh-fh:6.1f} mm")
        print(f"   접지 앞끝 world u {v['base_u']:7.2f}  -> grip Y {tot_Y0:8.2f}"
              f"   패드 돌출 {overhang:+6.1f} mm")
        print()

    print("=" * 92)
    print("비교표")
    print("=" * 92)
    hdr = (f"{'안':<14s} {'전체 W x L':>16s} {'최대높이':>8s} {'손목지지면적':>11s} "
           f"{'HAND_REF 변화':>12s} {'추가부피(추정)':>14s} {'접지증가':>9s}")
    print(hdr)
    for r in rows:
        print(f"{r['name']:<14s} {CUR['W']:7.1f} x{r['L_total']:7.1f} "
              f"{139.9:8.1f} {r['pad_area']:11.0f} {0.0:12.3f} "
              f"{r['add_vol']:13,.0f} {r['foot_add']:9.0f}")

    print(f"\n{'안':<14s} {'인쇄 난이도':<34s} {'serviceability 영향'}")
    notes = [
        ("W1 COMPACT",
         "쐐기 최대 7.7mm — 서포트 거의 불필요",
         "영향 없음. 캐리어/USB 포트 그대로"),
        ("W2 BALANCED",
         "쐐기 10.4mm + 측면 R16 — 소량 서포트",
         "꼬리 위를 덮음 -> USB 포트를 패드 앞면으로 재배치 필요"),
        ("W3 FULLER",
         "쐐기 12.6mm + 윙 오버행 — 서포트 필요, 베드 246mm",
         "꼬리 완전 매립 + 윙이 측면 접근 가림. 서비스 개구 추가 필요"),
    ]
    for n, p, s in notes:
        print(f"{n:<14s} {p:<34s} {s}")

    json.dump(rows, io.open(os.path.join(OUT, "wrist_shell_proposals.json"), "w",
                            encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n저장: wrist_shell_proposals.json  (CAD WRITE 0건)")


if __name__ == "__main__":
    main()
