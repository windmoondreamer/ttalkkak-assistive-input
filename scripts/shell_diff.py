"""Joystick_1 과 Joystick_2(미러) 의 형상 차이를 국소화한다 (READ ONLY).

방법: (Y,Z) 격자마다 +X 방향 레이를 한 번 쏘고 교차점 패리티로 '내부 구간'을 구한다.
두 쉘의 내부 구간 길이를 비교하면 차이가 (Y,Z) 평면 위에 지도로 나온다.
격자 셀당 부피차 = (길이차) x dy x dz.

    python scripts/shell_diff.py [step]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from mesh_probe import Mesh  # noqa: E402

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")


def mirrored_mesh(name):
    """X 를 반전한 메시를 임시 캐시로 만들어 Mesh 로 로드."""
    src = os.path.join(DUMP, f"mesh_{name}.json")
    dst = os.path.join(DUMP, f"mesh_{name}_mirX.json")
    if not os.path.exists(dst):
        with open(src, encoding="utf-8") as f:
            j = json.load(f)
        tris = []
        for t in j["tris"]:
            m = [[-p[0], p[1], p[2]] for p in t]
            tris.append([m[0], m[2], m[1]])      # 뒤집었으니 winding 복원
        j["tris"] = tris
        j["normals"] = []
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(j, f)
    return Mesh([f"{name}_mirX"])


def inside_length(mesh, y, z, x0=-6.0):
    """(y,z) 에서 +X 로 쏜 레이의 내부 구간 총 길이와 구간 목록."""
    hits = mesh.hits_dedup([x0, y, z], [1.0, 0.0, 0.0], tol=1e-3)
    ts = [t for t, _ in hits]
    if len(ts) % 2 == 1:            # 접선 등으로 홀수면 신뢰 불가
        return None, []
    segs = [(x0 + ts[i], x0 + ts[i + 1]) for i in range(0, len(ts), 2)]
    return sum(b - a for a, b in segs), segs


def main():
    step = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    a = Mesh(["Joystick_1"])
    b = mirrored_mesh("Joystick_2")
    ys = np.arange(-62, 64, step)
    zs = np.arange(-75, 80, step)
    cells = []
    bad = 0
    for z in zs:
        for y in ys:
            la, _ = inside_length(a, y, z)
            lb, _ = inside_length(b, y, z)
            if la is None or lb is None:
                bad += 1
                continue
            d = lb - la
            if abs(d) > 0.05:
                cells.append((d * step * step / 1000.0, y, z, la, lb))
    tot = sum(c[0] for c in cells)
    print(f"격자 {step} mm,  판정불가 레이 {bad}개")
    print(f"부피차 합계(J2미러 - J1) = {tot:+.3f} cm3   (massproperties 기준 +1.270)\n")

    # Z 구간별 집계
    print("Z 구간별 부피차 (cm3)")
    edges = np.arange(-80, 85, 10)
    for lo, hi in zip(edges[:-1], edges[1:]):
        v = sum(c[0] for c in cells if lo <= c[2] < hi)
        if abs(v) > 0.01:
            bar = "#" * min(60, int(abs(v) * 60))
            print(f"  Z {lo:+4.0f}..{hi:+4.0f}  {v:+8.3f}  {bar}")

    # 상위 차이 셀
    print("\n차이가 큰 상위 셀 (|부피차| 순)")
    print(f"  {'Y':>7}{'Z':>7}{'J1 len':>9}{'J2m len':>9}{'차이mm':>9}{'cm3':>9}")
    for v, y, z, la, lb in sorted(cells, key=lambda c: -abs(c[0]))[:25]:
        print(f"  {y:7.1f}{z:7.1f}{la:9.2f}{lb:9.2f}{lb-la:+9.2f}{v:+9.4f}")

    # 신규 버튼 영역(Z 9 / -6 부근) 대칭성
    print("\n신규 finger button 영역 대칭성 검사")
    for label, zc in (("INDEX Z=+9", 9.0), ("MIDDLE Z=-6", -6.0)):
        sel = [c for c in cells if abs(c[2] - zc) <= 6.0]
        v = sum(c[0] for c in sel)
        mx = max((abs(c[4] - c[3]) for c in sel), default=0.0)
        print(f"  {label:<14} Z {zc-6:+.0f}..{zc+6:+.0f}  "
              f"부피차 {v:+.4f} cm3,  최대 길이차 {mx:.2f} mm,  차이셀 {len(sel)}개")


if __name__ == "__main__":
    main()
