"""§20 — COMPACT / BALANCED / FULLY_ENCLOSED 패키징 변형 비교.

BALANCED / FULLY_ENCLOSED 는 무릎면 변수만 바꾼다 (재생성 불필요).
COMPACT 는 외피 규칙을 '국소 창'(허리 허용) 으로 바꿔 재생성한다.
"""
import io
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import stock_geom as sg                                  # noqa: E402
from onshape.client import BASE, session                 # noqa: E402
from onshape import write_client as wc                   # noqa: E402
import run_conformal as R                                # noqa: E402

OUT = sg.OUT
C = json.load(io.open(os.path.join(OUT, "cartridge_constants.json"), encoding="utf-8"))
UP = np.array(C["UP_LOCAL"])
HAND = np.array(C["HAND_REF"])
GEN = os.path.join(HERE, "gen_conformal_fs.py")


def setvar(name, expr, ty="LENGTH"):
    R.local_var_template()
    T = R.target()
    fid = T["varIds"][name]
    f = wc.assign_variable(name, expr, ty)
    f["featureId"] = fid
    session().post(
        f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{T['ps_eid']}"
        f"/features/featureid/{fid}",
        json={"feature": f, "rejectMicroversionSkew": False}, timeout=300)


def measure():
    T = R.target()
    s = session()
    r = s.get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{T['ps_eid']}",
              params=[("configuration", "default")], timeout=180)
    out = {}
    for p in r.json():
        if p.get("bodyType") != "solid":
            continue
        pid = p["partId"]
        m = s.get(f"{BASE}/parts/d/{wc.DID}/w/{wc.WID}/e/{T['ps_eid']}/partid/"
                  f"{pid.replace('/', '%2F')}/massproperties",
                  params=[("configuration", "default")], timeout=180).json()
        b = m["bodies"][list(m["bodies"])[0]]
        out[pid] = b["volume"][0] * 1e9
    if not out:
        return None
    hid = max(out, key=out.get)
    j = s.get(f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{T['ps_eid']}"
              "/tessellatedfaces",
              params=[("partId", hid), ("angleTolerance", "0.15"),
                      ("chordTolerance", "0.0005")], timeout=300).json()
    P = sg._tris(j) * 1000.0
    V = P.reshape(-1, 3)
    w = V @ UP
    gz = float(w.min())
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ar = np.linalg.norm(n, axis=1)
    nn = n / np.maximum(ar[:, None], 1e-12)
    ground = ar[(nn @ UP < -0.9999)].sum()
    foot = V[np.abs(w - gz) < 0.05]
    return {
        "housing_mm3": out[hid],
        "carrier_mm3": min(out.values()) if len(out) > 1 else 0.0,
        "W": float(V[:, 0].max() - V[:, 0].min()),
        "L": float(V[:, 1].max() - V[:, 1].min()),
        "H": float(w.max() - gz),
        "ground_area": float(ground),
        "foot_W": float(foot[:, 0].max() - foot[:, 0].min()) if len(foot) else 0.0,
        "foot_L": float(foot[:, 1].max() - foot[:, 1].min()) if len(foot) else 0.0,
        "B": float(HAND @ UP) - gz,
        "ground_world": gz,
    }


def regen(local_window):
    src = io.open(GEN, encoding="utf-8").read()
    if local_window:
        new = 'ab = cav[max(0, i - 1):min(len(cav), i + 2)]'
    else:
        new = 'ab = cav[max(0, i - 1):]'
    src = re.sub(r"ab = cav\[[^\]]*\]", new, src)
    io.open(GEN, "w", encoding="utf-8").write(src)
    subprocess.run([sys.executable, GEN], check=True,
                   stdout=subprocess.DEVNULL, cwd=ROOT)
    R.upload()


import re                                                # noqa: E402


def main():
    rows = []
    print("=" * 96)
    print("§20 패키징 변형 비교")
    print("=" * 96)

    # --- BALANCED (현재: 단조 외피 + 무릎 34deg @ Y18) ---
    setvar("knee_angle", "34 deg", "ANGLE")
    setvar("knee_y", "18 mm")
    m = measure()
    m["name"] = "BALANCED"
    m["desc"] = "단조 외피 + 무릎 34deg @ Y18"
    rows.append(m)

    # --- FULLY_ENCLOSED (무릎 절단 없음 = 완전 평바닥 쐐기) ---
    setvar("knee_angle", "0 deg", "ANGLE")
    m = measure()
    m["name"] = "FULLY_ENCLOSED"
    m["desc"] = "단조 외피 + 무릎 절단 없음"
    rows.append(m)

    # --- COMPACT (국소창 외피 = 허리 허용 + 무릎 42deg @ Y6) ---
    regen(True)
    setvar("knee_angle", "42 deg", "ANGLE")
    setvar("knee_y", "6 mm")
    m = measure()
    if m:
        m["name"] = "COMPACT"
        m["desc"] = "국소창 외피(허리) + 무릎 42deg @ Y6"
        rows.append(m)
    else:
        print("  COMPACT 생성 실패")

    # --- 복원: BALANCED ---
    regen(False)
    setvar("knee_angle", "34 deg", "ANGLE")
    setvar("knee_y", "18 mm")

    print(f"\n{'변형':<16s} {'하우징 W x L x H':>26s} {'접지 W x L':>16s} "
          f"{'접지면적':>9s} {'하우징 부피':>12s} {'PLA':>8s} {'B(지면->HAND)':>13s}")
    for m in rows:
        print(f"{m['name']:<16s} {m['W']:8.1f} x{m['L']:7.1f} x{m['H']:7.1f} "
              f"{m['foot_W']:7.1f} x{m['foot_L']:6.1f} {m['ground_area']:9.0f} "
              f"{m['housing_mm3']:11.0f} {m['housing_mm3']*1.24e-3:7.0f}g "
              f"{m['B']:12.2f}")
    for m in rows:
        print(f"\n[{m['name']}] {m['desc']}")
        print(f"   돌출(D) = 0.000 mm  (스톡 최저가 하우징 바닥 위 "
              f"{-165.3261 - m['ground_world']:+.3f} mm)")
    json.dump(rows, io.open(os.path.join(OUT, "conformal_variants.json"), "w",
                            encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n저장: conformal_variants.json")


if __name__ == "__main__":
    main()
