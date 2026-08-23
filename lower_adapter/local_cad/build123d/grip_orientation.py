"""OneGrip 방향(front/back) 불변량과 그 교정.

왜 필요한가
-----------
Phase 1 검증은 **각도 크기**만 봤다: 기준면 20 deg, 그립 중립축 ⟂ 기준면 90 deg.
그런데 그립을 부착축 둘레로 180 deg 돌려도 이 둘은 그대로 통과한다.

    ANGLE MAGNITUDE PASS  !=  ORIENTATION DIRECTION PASS

그래서 방향 자체를 재는 불변량을 따로 둔다.

근거 (전부 STEP 실측)
---------------------
* 스톡 Base 의 회전은 **하우징 꼬리 슬롯**이 확정한다.
  Rz(180) 간섭 0 / Rz(0) 간섭 2,621.78 mm3  ->  assembly->grip 변환은 옳다.
* OneGrip 착좌면 법선 = (+0.007857, -0.097373, -0.995217)
  Pitch 상단면 법선 = (-0.007857, +0.097373, +0.995217)
  두 부품에서 독립적으로 같은 축이 나온다. grip +Z 에서 5.606 deg
  (= 어셈블리 스냅샷의 Pitch 편향).
* 소켓 보어 내벽 4면 -> **21.0720 x 25.6720 직사각형**.
  직사각형은 축 둘레 180 deg 에 대해 자기 자신으로 간다
  -> post 물림이 **2-fold 모호**하다. 두 방향 모두 기계적으로 성립한다.

따라서 잘못된 것은 변환 부호가 아니라 **어셈블리가 고른 물림 방향**이고,
교정은 OneGrip 상부에만 거는 강체 180 deg 회전이다. 스톡/하우징은 안 건드린다.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parameters as P                                    # noqa: E402
import geometry_utils as G                                # noqa: E402

SEAT_Z = -67.878507          # 중립 착좌면 (grip frame)


# ------------------------------------------------------------------ 축 유도

def assembly_to_grip(bd):
    p = os.path.join(P.REPORTS_DIR, "01_reference_alignment.json")
    A = json.load(open(p, encoding="utf-8"))
    R = np.array(A["T_assembly_to_grip"]["R"])
    t = np.array(A["T_assembly_to_grip"]["t"])
    return bd.Location(bd.Plane(origin=tuple(t), x_dir=tuple(R[:, 0]),
                                z_dir=tuple(R[:, 2])))


def onegrip_solids(bd, asm, loc):
    js = [c for c in asm.children if (c.label or "").startswith("Joystick_")][0]
    return [s.moved(loc) for s in js.solids()]


def seat_plane(sols):
    """OneGrip 착좌면 -> (법선, 평면 오프셋). 부착축은 이 법선의 반대다."""
    best = []
    for s in sols:
        for f in s.faces():
            try:
                n = f.normal_at()
            except Exception:                              # noqa: BLE001
                continue
            nv = np.array([n.X, n.Y, n.Z])
            if nv[2] > -0.7 or float(f.area) < 500:
                continue
            c = f.center()
            best.append((float(f.area), nv, np.array([c.X, c.Y, c.Z])))
    if not best:
        raise SystemExit("STOP - OneGrip 착좌면을 찾지 못했다")
    top = sorted(best, key=lambda r: -r[0])[:2]
    n = sum(r[0] * r[1] for r in top) / sum(r[0] for r in top)
    n = n / np.linalg.norm(n)
    d = float(np.mean([n @ r[2] for r in top]))
    return n, d


def socket_axis(bd, sols, a_hint, seat_d):
    """소켓 보어 내벽 4면에서 축 통과점을 **정확히** 푼다.

    벽 두 쌍의 평면식 + 착좌면식 = 3원 1차 연립. 근사·피팅 없음.
    """
    # 축 근방을 정하는 기준점: 착좌면들의 면적가중 도심.
    # **반경 필터가 없으면** 보어 대신 그립 외벽(폭 77.4)을 잡아
    # 축이 0.6mm 어긋난다 (실제로 그렇게 틀렸다).
    seats = []
    for s in sols:
        for f in s.faces():
            try:
                n = f.normal_at()
            except Exception:                              # noqa: BLE001
                continue
            if n.Z > -0.7 or float(f.area) < 500:
                continue
            c = f.center()
            seats.append((float(f.area), np.array([c.X, c.Y, c.Z])))
    seats = sorted(seats, key=lambda r: -r[0])[:2]
    c_seat = sum(r[0] * r[1] for r in seats) / sum(r[0] for r in seats)

    def radial(cv):
        r = cv - c_seat
        return float(np.linalg.norm(r - a_hint * float(r @ a_hint)))

    walls = []
    for s in sols:
        for f in s.faces():
            try:
                n = f.normal_at()
            except Exception:                              # noqa: BLE001
                continue
            nv = np.array([n.X, n.Y, n.Z])
            if abs(float(nv @ a_hint)) > 0.01 or float(f.area) < 60:
                continue
            c = f.center()
            cv = np.array([c.X, c.Y, c.Z])
            if radial(cv) > 22.0:
                continue
            walls.append((nv, float(nv @ cv), float(f.area), cv))
    sel = [w for w in walls
           if -1.0 <= (float(w[3] @ a_hint) - (-seat_d)) <= 22.0]
    if len(sel) < 4:
        raise SystemExit(f"STOP - 소켓 내벽 후보 {len(sel)}개 (4개 필요)")
    # 법선 방향으로 군집 -> 마주보는 두 쌍
    groups = []
    for nv, d, ar, cv in sel:
        for g in groups:
            if abs(float(nv @ g["n"])) > 0.99:
                s = 1.0 if float(nv @ g["n"]) > 0 else -1.0
                g["d"].append(s * d)
                break
        else:
            groups.append({"n": nv, "d": [d]})
    pairs = [g for g in groups if (max(g["d"]) - min(g["d"])) > 5.0]
    if len(pairs) != 2:
        raise SystemExit(f"STOP - 마주보는 벽 쌍이 {len(pairs)}조 (2조 필요)")
    sizes, rows, rhs = [], [], []
    for g in pairs:
        w = max(g["d"]) - min(g["d"])
        sizes.append(w)
        rows.append(g["n"])
        rhs.append(0.5 * (max(g["d"]) + min(g["d"])))
    rows.append(a_hint)
    rhs.append(-seat_d)
    p0 = np.linalg.solve(np.array(rows), np.array(rhs))
    return p0, sorted(sizes)


def rot180(axis, p0):
    """축(axis, p0) 둘레 180 deg 회전 (R, t)."""
    a = axis / np.linalg.norm(axis)
    R = 2.0 * np.outer(a, a) - np.eye(3)
    return R, p0 - R @ p0


def loc_from_rt(bd, R, t):
    return bd.Location(bd.Plane(origin=tuple(t), x_dir=tuple(R[:, 0]),
                                z_dir=tuple(R[:, 2])))


# ------------------------------------------------------------ 방향 불변량

def grip_forward(sols):
    """GRIP_FORWARD_VECTOR — 손잡이 상단이 기우는 수평 방향.

    SIDE 프리뷰에서 눈에 보이는 바로 그 방향이다. 그립 샤프트의 주축을
    데크 평면(grip XY)에 투영해서 얻는다. 비대칭 특징이라 180 deg 를 구분한다.
    """
    V = np.vstack([np.array([[v.X, v.Y, v.Z] for v in s.vertices()])
                   for s in sols])
    sh = V[(V[:, 2] > -40) & (V[:, 2] < 70)]
    X = sh - sh.mean(0)
    ax = np.linalg.eigh(X.T @ X)[1][:, -1]
    if ax[2] < 0:
        ax = -ax
    f = np.array([ax[0], ax[1], 0.0])
    return f / np.linalg.norm(f), ax


def thumb_panel_forward(sols):
    """독립 교차검증용 — 엄지/버튼 패널 법선의 수평 성분."""
    num, den = np.zeros(3), 0.0
    for s in sols:
        for f in s.faces():
            try:
                n = f.normal_at()
            except Exception:                              # noqa: BLE001
                continue
            nv = np.array([n.X, n.Y, n.Z])
            c = f.center()
            if c.Z < 30.0 or nv[2] < 0.5 or float(f.area) < 50:
                continue
            num += nv * float(f.area)
            den += float(f.area)
    if den == 0:
        return None
    n = num / den
    h = np.array([n[0], n[1], 0.0])
    return h / np.linalg.norm(h) if np.linalg.norm(h) > 1e-6 else None


def wrist_support_direction(bd, step=None):
    """WRIST_SUPPORT_DIRECTION — 하우징에서 손목 받침이 뻗은 수평 방향.

    코어 bbox 밖으로 나간 ERGO 재료의 도심 - 코어 도심, XY 투영.
    상수를 손으로 넣지 않고 실제 형상에서 뽑는다.
    """
    core = bd.import_step(P.reference_path("conformal_core"))
    hou = sorted(core.solids(), key=lambda s: float(s.volume))[1]
    step = step or os.path.join(P.EXPORT_STEP, "ERGO_HOUSING_W2.step")
    new = bd.import_step(step).solids()[0]
    add = new - hou
    c1, c2 = add.center(), hou.center()
    d = np.array([c1.X - c2.X, c1.Y - c2.Y, 0.0])
    return d / np.linalg.norm(d)
