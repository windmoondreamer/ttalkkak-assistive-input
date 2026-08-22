"""모션 포락선 캐시를 **교정된 그립 방향**으로 변환한다.

캐시(`motion_configs.npz`)는 9자세의 이동부 점군인데 그 안에 OneGrip 상부가
들어 있다 (덱 위 점 246만 개). 그립을 180 deg 돌렸으면 캐시를 **그대로 쓰면
안 된다**. 자세마다 그 자세의 부착축 둘레로 그립 점만 돌린다.

근거 (전부 로컬 실측)
---------------------
* 부착축은 **짐벌 피벗을 지난다**: STEP 에서 구한 snapshot 축 통과점 p0 가
  피벗을 지나는 직선에서 벗어난 양 **0.0068 mm**, 축방향 거리 **46.982 mm**
  (CLAUDE.md 의 46.98 과 일치). 피벗은 어느 자세에서도 고정이다.
* 자세 k 의 축 방향 = B_k(0,0,1). B_k 는 `Pitch <1>` 점군의
  neutral -> k Kabsch 로 정확히 나온다 (자세 간 점 개수 일치 확인됨).

따라서 pose k 의 180 deg 는 (피벗, B_k·z) 둘레 회전이다.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402

PIVOT = np.array([0.0, 27.275842, -114.860854])
GRIP_PARTS = ("Backplate <1>", "HW504_B <1>", "HW504_B <2>",
              "Joystick_1 <1>", "Joystick_2 <1>",
              "Small_joystick_attachment <1>")
REF_PART = "Pitch <1>"
OUT = os.path.join(P.CACHE_DIR, "motion_configs_gripfix.npz")


def kabsch(A, B):
    """A -> B 정합 (대응점 순서 동일)."""
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    return R, cb - R @ ca


def main():
    mc = np.load(P.CACHE_MOTION)
    keys = list(mc.files)
    cfgs = sorted(set(k.split("|")[0] for k in keys))
    print("=" * 78)
    print("모션 포락선 그립 방향 교정  (TRANSFORMED / CACHED ENVELOPE)")
    print("=" * 78)
    print(f"자세 {len(cfgs)}   그립 부품 {len(GRIP_PARTS)}")

    An = mc[f"neutral|{REF_PART}"].reshape(-1, 3)
    out, moved_pts = {}, 0
    print(f"\n{'자세':<12s} {'Kabsch잔차':>11s} {'피벗고정':>10s} "
          f"{'축(그립Z에서)':>13s}  축방향")
    for c in cfgs:
        Ak = mc[f"{c}|{REF_PART}"].reshape(-1, 3)
        R, t = kabsch(An, Ak)
        res = float(np.abs(An @ R.T + t - Ak).max())
        pfix = float(np.linalg.norm(R @ PIVOT + t - PIVOT))
        a = R @ np.array([0.0, 0.0, 1.0])
        a = a / np.linalg.norm(a)
        ang = float(np.degrees(np.arccos(min(1.0, abs(a[2])))))
        print(f"{c:<12s} {res:11.3e} {pfix:10.4f} {ang:12.4f}   "
              f"({a[0]:+.6f},{a[1]:+.6f},{a[2]:+.6f})")
        R180 = 2.0 * np.outer(a, a) - np.eye(3)
        t180 = PIVOT - R180 @ PIVOT
        for k in keys:
            if not k.startswith(c + "|"):
                continue
            part = k.split("|", 1)[1]
            A = mc[k].reshape(-1, 3)
            if part in GRIP_PARTS:
                A = A @ R180.T + t180
                moved_pts += len(A)
            out[k] = A.reshape(mc[k].shape)

    np.savez_compressed(OUT, **out)
    print(f"\n회전된 점 {moved_pts:,}   저장 {os.path.relpath(OUT, P.LOCAL_CAD)}"
          f"  ({os.path.getsize(OUT)/1048576:.1f} MB)")

    # 스톡 이동부가 하나도 안 변했는지 확인
    same = True
    for k in keys:
        if k.split("|", 1)[1] in GRIP_PARTS:
            continue
        if not np.array_equal(out[k], mc[k]):
            same = False
            print("  [FAIL] 스톡 이동부가 변했다:", k)
    print(f"  [{'PASS' if same else 'FAIL'}] 스톡 이동부 점군 완전 무변화")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
