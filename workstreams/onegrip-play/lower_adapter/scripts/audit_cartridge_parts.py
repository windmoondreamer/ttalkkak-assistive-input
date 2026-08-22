"""생성된 두 부품의 형상 감사 — 구멍 존재 / 최소 살 / 부피 / 프린트 방향."""
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
from onshape.client import BASE, session                 # noqa: E402
from onshape import write_client as wc                   # noqa: E402
from verify_cartridge import C, T, fetch, inside_mesh    # noqa: E402

OUT = sg.OUT
UP = np.array(C["UP_LOCAL"])
SCREWS = [(55.0, 45.0), (-55.0, 45.0), (55.0, 0.0), (-55.0, 0.0),
          (55.0, -45.0), (-55.0, -45.0), (30.0, 55.0), (-30.0, 55.0)]


def volume(P):
    v0, v1, v2 = P[:, 0], P[:, 1], P[:, 2]
    return float(np.abs((np.cross(v0, v1) * v2).sum() / 6.0))


def zspans(P, xy):
    v0, v1, v2 = P[:, 0], P[:, 1], P[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    d = np.array([0.0, 0.0, 1.0])
    h = np.cross(d, e2)
    a = (e1 * h).sum(1)
    m = np.abs(a) > 1e-12
    f = np.where(m, 1.0 / np.where(m, a, 1.0), 0.0)
    out = []
    for x, y in xy:
        s = np.stack([x - v0[:, 0], y - v0[:, 1], -1e4 - v0[:, 2]], 1)
        u = f * (s * h).sum(1)
        q = np.cross(s, e1)
        v = f * (q * d).sum(1)
        t = f * (e2 * q).sum(1)
        ok = m & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
        ts = np.sort(t[ok]) - 1e4
        ts = [z for i, z in enumerate(ts) if i == 0 or z - ts[i - 1] > 1e-4]
        out.append([(ts[i], ts[i + 1]) for i in range(0, len(ts) - 1, 2)])
    return out


def main():
    M = fetch()
    CAR, HOUSE = M["JHD"], [M[k] for k in M if k != "JHD"][0]
    print("=" * 74)
    print("부피 / 질량 (PLA 1.24 g/cm3 가정)")
    print("=" * 74)
    for nm, P in (("CARRIER_PLATE", CAR), ("DECK_HOUSING", HOUSE)):
        v = volume(P)
        print(f"  {nm:<16s} {v:10.1f} mm3   {v * 1.24e-3:7.1f} g")

    print("\n" + "=" * 74)
    print("CARRIER — 구멍 검사")
    print("=" * 74)
    for lab, xy in (("C1", C["C1"]), ("C2", C["C2"])):
        sp = zspans(CAR, [tuple(xy)])[0]
        print(f"  {lab} 축 (X={xy[0]:.3f}, Y={xy[1]:.3f})  재료 구간: "
              + (", ".join(f"[{a:.3f},{b:.3f}]" for a, b in sp) or "없음 (관통)"))
    # 카운터보어 폭 확인
    for lab, xy in (("C1", C["C1"]), ("C2", C["C2"])):
        for z, tag in ((C["CAR_BOT"] + 1.0, "카운터보어"), (C["CAR_BOT"] + 5.0, "관통부")):
            w = []
            for x in np.arange(xy[0] - 6, xy[0] + 6, 0.1):
                sp = zspans(CAR, [(x, xy[1])])[0]
                if not any(a <= z <= b for a, b in sp):
                    w.append(x)
            print(f"  {lab} {tag:<8s} Z={z:9.3f}  빈 폭 {max(w)-min(w)+0.1:6.3f} mm"
                  if w else f"  {lab} {tag} 빈 공간 없음")
    ok = 0
    for sx, sy in SCREWS:
        x, y = C["CX"] + sx, C["CY"] + sy
        sp = zspans(CAR, [(x, y)])[0]
        if not sp:
            ok += 1
    print(f"  캐리어<->하우징 나사 관통 {ok} / {len(SCREWS)}")

    print("\n" + "=" * 74)
    print("HOUSING — 인서트 구멍 / 립 / 창")
    print("=" * 74)
    ok = 0
    for sx, sy in SCREWS:
        x, y = C["CX"] + sx, C["CY"] + sy
        sp = zspans(HOUSE, [(x, y)])[0]
        top = [b for a, b in sp if abs(a - (C["CAR_TOP"] + C["INSERT_L"])) < 0.2]
        hit = any(abs(a - (C["CAR_TOP"] + C["INSERT_L"])) < 0.2 for a, b in sp)
        if hit:
            ok += 1
    print(f"  인서트 블라인드 구멍 (깊이 {C['INSERT_L']:.1f}) {ok} / {len(SCREWS)}")
    # 립 존재
    sp = zspans(HOUSE, [(C["CX"] + 54.0, C["CY"])])[0]
    print("  립 위치 재료 구간 (X+54, CY): "
          + ", ".join(f"[{a:.3f},{b:.3f}]" for a, b in sp))
    # 덱 개구
    sp = zspans(HOUSE, [(C["OP_CX"], C["OP_CY"])])[0]
    print("  덱 개구 중심 재료 구간: " + (", ".join(f"[{a:.3f},{b:.3f}]" for a, b in sp)
                                or "없음 (관통) OK"))

    print("\n" + "=" * 74)
    print("최소 살 두께 (수직 레이 기준, 0.5 mm 격자)")
    print("=" * 74)
    for nm, P in (("CARRIER_PLATE", CAR), ("DECK_HOUSING", HOUSE)):
        V = P.reshape(-1, 3)
        lo, hi = V.min(0), V.max(0)
        xs = np.arange(lo[0] + 0.25, hi[0], 0.5)
        ys = np.arange(lo[1] + 0.25, hi[1], 0.5)
        thin = []
        for y in ys:
            for sp in zspans(P, [(x, y) for x in xs]):
                for a, b in sp:
                    thin.append(b - a)
        thin = np.array(thin)
        thin = thin[thin > 0.05]
        print(f"  {nm:<16s} 수직 재료 구간 {len(thin)}개  "
              f"최소 {thin.min():.3f}  5퍼센타일 {np.percentile(thin, 5):.3f}  "
              f"중앙 {np.median(thin):.3f}")

    print("\n" + "=" * 74)
    print("프린트 방향 (서포트 관점)")
    print("=" * 74)
    for nm, P in (("CARRIER_PLATE", CAR), ("DECK_HOUSING", HOUSE)):
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ar = np.linalg.norm(n, axis=1)
        nn = n / np.maximum(ar[:, None], 1e-12)
        best = None
        for cand, lab in (((0, 0, -1), "그립 -Z 를 아래로"),
                          ((0, 0, 1), "그립 +Z 를 아래로"),
                          (tuple(-UP), "지면(20도) 을 아래로"),
                          (tuple(UP), "지면 반대")):
            c = np.array(cand, dtype=float)
            over = (nn @ c > np.cos(np.radians(45.0)))   # 45도 이상 오버행 하향면
            frac = ar[over].sum() / ar.sum()
            print(f"  {nm:<16s} {lab:<20s} 서포트 필요 하향면 {100*frac:5.1f}% "
                  f"({ar[over].sum():8.1f} mm2)")
        print()

    json.dump({"volume_mm3": {"CARRIER_PLATE": volume(CAR),
                              "DECK_HOUSING": volume(HOUSE)}},
              io.open(os.path.join(OUT, "cartridge_audit.json"), "w", encoding="utf-8"),
              indent=1)


if __name__ == "__main__":
    main()
