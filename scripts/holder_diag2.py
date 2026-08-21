"""INDEX holder wall 정밀 진단 v2 (READ ONLY, 로컬 계산만).

v1 대비 수정:
  - pocket 경계(|s|=3.2) 정확히에서 판정하면 경계 오차로 0 이 나오므로 3.2+eps 에서 시작
  - stage A/B/C 예측을 **4개 버튼 전부의 박스**로 재구성 (인접 버튼 간섭 포함)
  - 인접 버튼 박스 간 실제 겹침 정량화
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from mesh_probe import Mesh                      # noqa: E402
from holder_diag import FS_IDX, basis, segments  # noqa: E402

CAP_W, POCKET_W, HOLDER_W = 8.0, 6.4, 12.4
SHELL_WALL, FUSE, HOLDER_DEPTH = 3.0, 0.2, 10.0
EPS = 0.05
DEPTHS = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]

BT = []
for nm, p, nr, dom, clip in FS_IDX:
    u, v, z = basis(nr)
    BT.append(dict(nm=nm, p=np.array(p), u=u, v=v, z=z, dom=dom, clip=clip,
                   shell="Joystick_2" if p[0] < 0 else "Joystick_1"))


def local(b, q):
    """전역 좌표 q 를 버튼 b 의 로컬 (x=u, y=v, depth) 로."""
    d = q - b["p"]
    return np.dot(d, b["u"]), np.dot(d, b["v"]), -np.dot(d, b["z"])


def in_opening(b, q):
    x, y, d = local(b, q)
    return abs(x) <= CAP_W / 2 and abs(y) <= CAP_W / 2 and -3.0 <= d <= 12.0


def in_holder(b, q):
    x, y, d = local(b, q)
    if not (abs(x) <= HOLDER_W / 2 and abs(y) <= HOLDER_W / 2
            and (SHELL_WALL - FUSE) <= d <= (SHELL_WALL + HOLDER_DEPTH)):
        return False
    if b["clip"]:
        if b["dom"] and q[0] > 0:
            return False
        if (not b["dom"]) and q[0] < 0:
            return False
    return True


def in_pocket(b, q):
    x, y, d = local(b, q)
    return abs(x) <= POCKET_W / 2 and abs(y) <= POCKET_W / 2 and -1.0 <= d <= 14.0


def stage_material(q, base_inside, same_shell):
    """stage A/B/C 재료 판정. same_shell 에 속한 버튼의 박스만 적용."""
    op = any(in_opening(b, q) for b in same_shell)
    ho = any(in_holder(b, q) for b in same_shell)
    po = any(in_pocket(b, q) for b in same_shell)
    B = (base_inside and not op) or ho
    return B, (B and not po)


def wall(pred_or_seg, side, kind, half=POCKET_W / 2, step=0.02, limit=15.0):
    s0 = side * half
    s = s0 + side * EPS
    if not pred_or_seg(s):
        return 0.0
    while abs(s - s0) < limit:
        s += side * step
        if not pred_or_seg(s):
            break
    return abs(s - s0) - step


def main():
    cur = {n: Mesh([n]) for n in ("Joystick_1", "Joystick_2")}
    base = {n: Mesh([n + "_baseline"]) for n in ("Joystick_1", "Joystick_2")}

    print("=" * 118)
    print("A) 인접 버튼 박스 간섭 — 각 버튼 holder 안으로 다른 버튼의 pocket/opening 이 들어오는가")
    print("=" * 118)
    print("   (곡면이 볼록하므로 안쪽으로 갈수록 버튼 축이 수렴 -> 깊은 곳에서 겹침이 커진다)")
    print(f"\n   {'버튼':<5}{'depth':>7}{'인접축 간 거리':>14}   침범하는 이웃 pocket")
    for i, b in enumerate(BT):
        for d in (3.0, 8.0, 13.0):
            c = b["p"] - b["z"] * d
            others = []
            for j, o in enumerate(BT):
                if i == j or o["shell"] != b["shell"]:
                    continue
                oc = o["p"] - o["z"] * d
                dist = float(np.linalg.norm(oc - c))
                # b 의 holder 벽 영역(|x| 3.2~6.2) 안으로 o 의 pocket 이 들어오는지 샘플링
                hit = False
                for s in np.arange(3.25, 6.21, 0.1):
                    for side in (1, -1):
                        for ax in (b["u"], b["v"]):
                            q = c + ax * side * s
                            if in_pocket(o, q):
                                hit = True
                if hit:
                    others.append(f"{o['nm']}(축간 {dist:.1f}mm)")
            if others:
                print(f"   {b['nm']:<5}{d:7.1f}{'':>14}   {', '.join(others)}")
            elif d == 13.0:
                print(f"   {b['nm']:<5}{d:7.1f}{'':>14}   (없음)")

    print()
    print("=" * 118)
    print("B) effective structural wall (mm) — pocket 경계에서 첫 VOID 까지")
    print("   act = 현재 CAD 실측 | C = 예측(stage C) | B = 예측(pocket 뚫기 전)")
    print("=" * 118)
    summary = {}
    for b in BT:
        M, MB = cur[b["shell"]], base[b["shell"]]
        same = [x for x in BT if x["shell"] == b["shell"]]
        print(f"\n  --- {b['nm']} ({b['shell']})")
        print(f"      {'depth':>6} |{'u- act':>7}{'C':>6}{'B':>6} |{'u+ act':>7}{'C':>6}{'B':>6}"
              f" |{'v- act':>7}{'C':>6}{'B':>6} |{'v+ act':>7}{'C':>6}{'B':>6}")
        mins = []
        for d in DEPTHS:
            c = b["p"] - b["z"] * d
            row = []
            for ax in (b["u"], b["v"]):
                seg = segments(M, c, ax)
                segb = segments(MB, c, ax)

                def act(s, seg=seg):
                    return any(a - 1e-6 <= s <= bb + 1e-6 for a, bb in seg)

                def make(stage, ax=ax, segb=segb, c=c):
                    def f(s):
                        q = c + ax * s
                        bi = any(a - 1e-6 <= s <= bb + 1e-6 for a, bb in segb)
                        B_, C_ = stage_material(q, bi, same)
                        return C_ if stage == "C" else B_
                    return f
                for side in (-1, 1):
                    row.append((wall(act, side, "act"),
                                wall(make("C"), side, "C"),
                                wall(make("B"), side, "B")))
            # row 순서: u-, u+, v-, v+
            print(f"      {d:6.1f} |{row[0][0]:7.2f}{row[0][1]:6.2f}{row[0][2]:6.2f}"
                  f" |{row[1][0]:7.2f}{row[1][1]:6.2f}{row[1][2]:6.2f}"
                  f" |{row[2][0]:7.2f}{row[2][1]:6.2f}{row[2][2]:6.2f}"
                  f" |{row[3][0]:7.2f}{row[3][1]:6.2f}{row[3][2]:6.2f}")
            if d >= 4.0:
                mins.append(min(r[0] for r in row))
        summary[b["nm"]] = min(mins) if mins else float("nan")
    print("\n  깊이 4~12mm 구간 최소 effective wall:")
    for k, v in summary.items():
        print(f"     {k}: {v:.2f} mm")
    return summary


if __name__ == "__main__":
    main()
