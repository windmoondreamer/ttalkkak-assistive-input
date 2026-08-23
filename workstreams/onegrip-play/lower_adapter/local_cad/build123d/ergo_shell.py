"""W2 인체공학 외피 생성 (build123d).

동결 레퍼런스:
    CONFORMAL_CORE_REFERENCE.step  ->  HOUSING (코어) + BOTTOM_CARRIER (동결)

전략 (§6 Strategy B, 명시적 keep-out 보호):
    NEW = HOUSING  ∪  ( SMOOTH_ENVELOPE − HOUSING − CAVITY_PROTECT )

  - HOUSING 은 **한 번도 자르지 않는다** -> 정확한 내부 공동/인터페이스가 그대로 보존된다.
  - 새 재료는 HOUSING 바깥에만 붙는다.
  - CAVITY_PROTECT 가 공동을 지킨다:
        검증된 내부 포락선(conformal_envelope, 그립 프레임)
        + 캐리어 하방 인출 스윕 (CARRIER STEP 을 -Z 로 sweep)
    -> 새 재료가 공동/서비스 경로로 들어가는 것이 **구성상 불가능**하다.
  - SMOOTH_ENVELOPE 는 HOUSING 의 Z 단면 실측 경계를 **덮는** multi-section loft 라
    계단이 새 매끈한 면 아래로 묻힌다.

Strategy A(외부 재료만 교체)는 채택하지 않았다: 공동이 상/하로 열려 있어
STEP 만으로 공동 solid 를 분리 추출할 수 없고, HOUSING 을 자르면 검증된 내부
형상을 깨뜨릴 위험이 있다. 사유는 리포트에 기록한다.

실행:
    .venv-build123d/Scripts/python lower_adapter/local_cad/build123d/ergo_shell.py
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


# ------------------------------------------------------------------ 기하 상수

UP = np.array(P.FROZEN_UP_LOCAL)
UH = np.array(P.FROZEN_U_HAT)
DECK = P.FROZEN_DECK_Z
GROUND_H = P.FROZEN_GROUND_WORLD_H


def ground_z(y):
    """월드 지면 평면이 grip Y 에서 갖는 grip Z."""
    return (GROUND_H - UP[1] * y) / UP[2]


def pad_plane():
    """손목 패드 평면을 grip (Y,Z) 직선으로. (앵커점, 앞끝점, 기울기)"""
    ay = P.WRIST_ANCHOR_Y
    au = ay * UH[1] + DECK * UH[2]
    ah = ay * UP[1] + DECK * UP[2]
    fu = au - P.WRIST_PAD_LENGTH
    fh = ah - P.WRIST_PAD_LENGTH * math.tan(math.radians(P.WRIST_PAD_ANGLE))
    fy = fu * UH[1] + fh * UP[1]
    fz = fu * UH[2] + fh * UP[2]
    slope = (fz - DECK) / (fy - ay)
    return (ay, DECK), (fy, fz), slope


def pad_z(y, anchor, slope):
    return anchor[1] + slope * (y - anchor[0])


# ------------------------------------------------------------------ 단면 유틸

def rr_sketch(bd, plane, w, h, r, cx=0.0, cy=0.0):
    """평면 위 둥근 사각 스케치 (Sketch 객체)."""
    r = max(0.1, min(r, 0.49 * min(w, h)))
    from build123d import BuildSketch, Locations, RectangleRounded
    with BuildSketch(plane) as sk:
        with Locations((cx, cy)):
            RectangleRounded(w, h, r)
    return sk.sketch


# ---- 전면 지면 블렌드 변형 (s = front 에서 -Y 로 나간 거리, h = 지면 위 월드 높이) ----
# 제약: 월드 수평 이동 du = -1.0642*s + 0.364*dh  ->  dh/ds <= 2.923 이어야 오버행이
# 생기지 않는다. 아래 값은 전부 이 한계 안에 있다.
H_FRONT0 = 96.2         # 현재 손목 앞단의 지면 위 월드 높이 (실측)
DROP_RATE_MAX = 2.923   # dh/ds 한계. 넘으면 실루엣이 오버행이 된다


def _front_sections(kind):
    """전면 블렌드 단면 목록 [(s, h_world, wfrac)].

    s = front 에서 -Y 로 나간 거리, h = 지면 위 월드 높이.
    월드 수평 이동이 du = -1.0642*s + 0.364*dh 이므로 dh/ds 가
    DROP_RATE_MAX 를 넘으면 위가 아래보다 앞으로 튀어나온다(=지금의 결함).
    """
    out = []
    if kind == "A":
        # 직선 등강하. 안전 한계 바로 아래 속도로 최단 길이.
        rate, smax, step = 2.85, 18.0, 6.0
        s_ = step
        while s_ <= smax + 1e-9:
            out.append((s_, H_FRONT0 - rate * s_, 0.72 - 0.06 * (s_ / smax)))
            s_ += step
    else:
        # 지면 블렌드. h(s) = H0*(1-s/S)^q -> 위는 가파르고 지면 근처는 완만.
        S, q, step, lip = 42.0, 1.35, 3.0, 5.0
        s_ = step
        while s_ <= S + 1e-9:
            h = max(lip, H_FRONT0 * (1.0 - min(1.0, s_ / 45.0)) ** q)
            out.append((s_, h, 0.72 - 0.14 * (s_ / S)))
            s_ += step
    return out


FRONT_VARIANTS = {"A": _front_sections("A"), "B": _front_sections("B")}
WRIST_UNDER = 20.0      # 바깥 단면을 지면 아래로 얼마나 더 내릴지
WRIST_UNDER_IN = 25.0   # 안쪽(중공) 단면


def seg_loft(loft_fn, sk, ruled=True):
    """인접 두 섹션씩 loft 해서 union.

    섹션이 많고 크기 변화가 큰 경우 build123d 의 multi-section loft 는
    invalid solid 를 낸다 (실측: A 8섹션 valid=False, 부피도 882,321 로
    구간별 union 940,221 보다 6.6% 모자란다 = 실제로 망가진 형상).
    구간별로 나누면 각 loft 가 단순해져 유효성이 보장된다.
    """
    out = None
    for i in range(len(sk) - 1):
        piece = loft_fn([sk[i], sk[i + 1]], ruled=ruled)
        out = piece if out is None else out + piece
    return out


def ramp_z(y, deg, u_tip, h_tip):
    """등Y 단면과 전면 램프 직선의 교점 -> 그 단면의 top Z.

    등Y 단면을 (u,h) 로 보내면  h = 2.923786*y - 2.747477*u - GROUND_H  이고
    램프는  h = h_tip + tan(deg)*(u - u_tip)  이다. 둘을 연립해 u 를 얻는다.
    (loft 결과에 맡기지 않고 프로파일에서 직접 계산 — 이전 라운드와 같은 원칙)
    """
    t = math.tan(math.radians(deg))
    u = (2.923786 * y - GROUND_H - h_tip + t * u_tip) / (t + 2.747477)
    return (0.9396926207859084 * y - u) / 0.3420201433256687


def ramp_tip_y(deg, u_tip, h_tip, lip_h):
    """램프가 lip_h 까지 내려오는 지점의 Y."""
    run = (h_tip - lip_h) / math.tan(math.radians(deg))
    u_end = u_tip - run
    return (0.9396926207859084 * u_end
            + 0.3420201433256687 * (lip_h + GROUND_H)), run


def top_z_at(y, h_world):
    """지면 위 월드 높이 h 를 갖는 grip Z."""
    return ground_z(y) + h_world / UP[2]


def yz_plane(bd, y):
    """Y 법선 평면. **축을 명시한다.**

    `Plane(origin, z_dir=(0,1,0))` 은 x_dir 을 자동으로 (0,0,1) 로 잡아
    local x -> world Z, local y -> world X 가 된다. 그대로 쓰면 손목 단면이
    90도 돌아간 채 X 로 날아가 (실측 X~-118) 평면 절단에 통째로 사라진다.
    여기서는 local (x, y) -> world (X, Z) 가 되도록 못박는다.
    """
    return bd.Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))


def housing_profile(bd, hou, n=26):
    """HOUSING 의 Z 단면 실측 경계 (loft 가 덮어야 할 최소 범위)."""
    bb = hou.bounding_box()
    zs = np.linspace(bb.min.Z + 1.0, bb.max.Z - 0.2, n)
    out = []
    for z in zs:
        thin = bd.Box(400, 400, 0.05).locate(bd.Location((0, 0, float(z))))
        try:
            cut = hou & thin
            b2 = cut.bounding_box()
            if b2.size.X <= 0.01:
                continue
            out.append({"z": float(z), "x0": float(b2.min.X), "x1": float(b2.max.X),
                        "y0": float(b2.min.Y), "y1": float(b2.max.Y)})
        except Exception:                                  # noqa: BLE001
            continue
    return out


def _v(label, obj):
    """중간 단계 유효성/shell 수 — 어디서 처음 깨지는지 특정용."""
    from OCP.BRepCheck import BRepCheck_Analyzer
    try:
        n = len(list(obj.shells()))
        bad = [f for f in obj.faces()
               if not BRepCheck_Analyzer(f.wrapped).IsValid()]
        loc = "  ".join(f"({b.center().X:.1f},{b.center().Y:.1f},"
                        f"{b.center().Z:.1f})"
                        for b in (f.bounding_box() for f in bad[:4]))
        print(f"    · {label:<12s} valid={G.shape_valid(obj)!s:<5s} shells={n} "
              f"badface={len(bad)}  vol={float(obj.volume):,.1f}  {loc}")
    except Exception as e:                                   # noqa: BLE001
        print(f"    · {label:<12s} 검사 실패: {e}")


def _ekey(e):
    """모서리 식별 키 (필렛 후 핸들이 무효가 되므로 좌표로 잡는다)."""
    b = e.bounding_box()
    c = b.center()
    return (round(c.X, 4), round(c.Y, 4), round(c.Z, 4), round(float(e.length), 4))


def _dihedral_deg(solid, e, emap, allf):
    """모서리의 이면각. 0 에 가까우면 **인공 이음매**(같은 평면)라 필렛 대상이 아니다.

    `seg_loft` 로 인접 단면을 union 하면 평면 위에 각도 0 인 이음매가 남는다.
    실측: LEFT/RIGHT_WRIST_CONTACT 와 PAD_PERIMETER 후보가 전부 0.000 deg 였고,
    그래서 R2.0/R1.5 필렛이 전부 실패했다 (실패가 정상이다).
    """
    import math as _m
    i = emap.FindIndex(e.wrapped)
    if not i:
        return float("nan")
    ns = []
    for fw in emap.FindFromIndex(i):
        for f in allf:
            if f.wrapped.IsSame(fw):
                try:
                    n = f.normal_at(e.center())
                    ns.append(np.array([n.X, n.Y, n.Z]))
                except Exception:                          # noqa: BLE001
                    pass
                break
    if len(ns) < 2:
        return float("nan")
    return _m.degrees(_m.acos(max(-1.0, min(1.0, float(ns[0] @ ns[1])))))


def _edge_groups(bd, solid, anchor, front, slope, min_dihedral=5.0):
    """의미 기반 모서리 그룹. 매번 **현재 solid 에서 다시** 고른다
    (필렛 한 번 걸 때마다 앞서 잡아 둔 Edge 핸들이 무효가 된다).

    이전 `WRIST_SIDE` 는 `|X| > 30` 만 봐서 208~210개를 잡았다 — 대부분
    ruled 이음매(둘레 방향 crease)라 사용자 접촉 외곽이 아니다.
    여기서는 **패드 평면 위 + 길이방향(Y지배) + 상면 높이** 세 조건으로
    실제 접촉 외곽만 고른다 (좌/우 각 3~4개).

    `GROUND_TRANSITION` 은 전면 수직면(u = U_TIP) 위의 낮은 모서리 =
    뜬 립과 지면 블렌드 스커트가 만나는 곳이다.

    지면에 닿는 모서리는 제외한다 (필렛하면 립이 지면에서 떠오른다).
    """
    import side_profile as SP
    pn = np.array([0.0, -slope, 1.0])
    pn = pn / np.linalg.norm(pn)
    pd = float(pn[1] * anchor[0] + pn[2] * anchor[1])
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_ShapeEnum
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    emap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid.wrapped, TopAbs_ShapeEnum.TopAbs_EDGE,
                                   TopAbs_ShapeEnum.TopAbs_FACE, emap)
    allf = list(solid.faces())
    g = {"GROUND_TRANSITION": [], "LEFT_WRIST_CONTACT": [],
         "RIGHT_WRIST_CONTACT": [], "FRONT_LIP": [], "PAD_PERIMETER": []}
    for e in solid.edges():
        if float(e.length) < 4.0:
            continue
        bb = e.bounding_box()
        c = bb.center()
        if c.Y > anchor[0] + 1.0:                  # 손목 구역 밖
            continue
        pts = np.array([[v.X, v.Y, v.Z] for v in e.vertices()])
        if len(pts) == 0:
            continue
        hs = pts @ UP - GROUND_H
        us = pts @ UH
        if float(hs.min()) < 1.0:                  # 지면 접촉 모서리
            continue
        d = _dihedral_deg(solid, e, emap, allf)
        if not (d == d) or d < min_dihedral:      # NaN 또는 인공 이음매
            continue
        on_front = abs(float(us.mean()) - SP.U_TIP) < 0.5
        if on_front:
            (g["GROUND_TRANSITION"] if float(hs.max()) < 20.0
             else g["FRONT_LIP"]).append(e)
            continue
        if float(np.abs(pts @ pn - pd).max()) > 0.5:   # 패드 평면 밖
            continue
        if float(hs.min()) < 85.0:                     # 상면 높이 아님
            continue
        y_dom = bb.size.Y > 2.0 * max(bb.size.X, bb.size.Z)
        if y_dom and abs(c.X) > 15.0:
            g["LEFT_WRIST_CONTACT" if c.X < 0 else
              "RIGHT_WRIST_CONTACT"].append(e)
        else:
            g["PAD_PERIMETER"].append(e)
    return g


# 그룹별 반경 스케줄 (§3, §4). 앞에서 실패하면 뒤 반경으로 강등한다.
# (그룹, 반경 스케줄, 이분분할 허용).
# FRONT_LIP 이분분할에서 OCC 가 **segfault(exit 139)** 로 죽었다 — 예외가 아니라
# 프로세스가 죽으므로 try 로 못 잡는다. 그래서 그 그룹은 분할을 끈다.
FILLET_PLAN = [
    ("GROUND_TRANSITION", (2.0, 1.5, 1.0), True),
    ("LEFT_WRIST_CONTACT", (2.0, 1.5), False),
    ("RIGHT_WRIST_CONTACT", (2.0, 1.5), False),
    ("FRONT_LIP", (2.0, 1.5, 1.0), False),
    ("PAD_PERIMETER", (3.0, 2.5, 2.0), False),
]


def apply_fillets(bd, solid, anchor, front, slope, skip=()):
    """의미 그룹별 필렛. 그룹이 통째로 실패하면 이분 분할로 되는 것만 살린다.

    `fillet` 은 집합에 실패 모서리가 하나라도 있으면 전체가 실패하므로
    그룹을 나누고, 성공한 필렛은 뒤 실패 때문에 되돌리지 않는다.
    """
    print("  필렛")
    for name, radii, allow_split in FILLET_PLAN:
        if name in skip:
            print(f"    {name:<20s} 건너뜀 (A/B 테스트 지정)")
            continue
        done = False
        for r in radii:
            es = _edge_groups(bd, solid, anchor, front, slope)[name]
            es = [e for e in es if float(e.length) > 2.0 * r]
            if not es:
                print(f"    {name:<20s} 대상 모서리 없음 - 건너뜀")
                done = True
                break
            try:
                cand = bd.fillet(es, radius=r)
                if not G.shape_valid(cand):
                    raise RuntimeError("결과 solid invalid")
                solid = cand
                print(f"    {name:<20s} R{r:.1f}  모서리 {len(es)}개  "
                      f"vol {float(solid.volume):,.1f}")
                done = True
                break
            except Exception as e:                            # noqa: BLE001
                print(f"    {name:<20s} R{r:.1f} 실패 ({type(e).__name__}) - 강등")
        if done or not allow_split:
            if not done:
                print(f"    {name:<20s} 전 반경 실패 - 이 그룹은 필렛 없이 둔다")
            continue
        r = radii[-1]
        ok_n = [0]

        def try_set(keys):
            nonlocal solid
            if not keys:
                return
            es = _edge_groups(bd, solid, anchor, front, slope)[name]
            sel = [e for e in es if _ekey(e) in keys]
            if not sel:
                return
            try:
                cand = bd.fillet(sel, radius=r)
                if not G.shape_valid(cand):
                    raise RuntimeError("invalid")
                solid = cand
                ok_n[0] += len(sel)
                return
            except Exception:                                 # noqa: BLE001
                pass
            if len(keys) == 1:
                return
            mid = len(keys) // 2
            try_set(keys[:mid])
            try_set(keys[mid:])

        es0 = _edge_groups(bd, solid, anchor, front, slope)[name]
        es0 = [e for e in es0 if float(e.length) > 2.0 * r]
        if len(es0) > 80:
            print(f"    {name:<20s} 모서리 {len(es0)}개 - 이분분할 생략")
            continue
        try_set([_ekey(e) for e in es0])
        print(f"    {name:<20s} 이분분할 R{r:.1f}  성공 {ok_n[0]}/{len(es0)}"
              f"  vol {float(solid.volume):,.1f}")
    return solid


def stock_keepout(bd, body, clr=0.4):
    """어셈블리 부품과 실제로 겹치는 것들의 bbox keep-out (여유 clr).

    **신규 재료에만** 적용한다. 동결 코어가 이미 갖고 있던 간섭
    (M3 나사 머리 138.2772 mm3) 은 이 범위 밖이라 건드리지 않는다.
    """
    A = json.load(open(os.path.join(P.REPORTS_DIR,
                                    "01_reference_alignment.json"),
                       encoding="utf-8"))
    R3 = np.array(A["T_assembly_to_grip"]["R"])
    t3 = np.array(A["T_assembly_to_grip"]["t"])
    loc = bd.Location(bd.Plane(origin=tuple(t3), x_dir=tuple(R3[:, 0]),
                               z_dir=tuple(R3[:, 2])))
    asm = bd.import_step(P.reference_path("assembly")).moved(loc)
    bb = body.bounding_box()
    tools = []
    for s2 in asm.solids():
        b2 = s2.bounding_box()
        if (b2.max.X < bb.min.X or b2.min.X > bb.max.X or b2.max.Y < bb.min.Y
                or b2.min.Y > bb.max.Y or b2.max.Z < bb.min.Z
                or b2.min.Z > bb.max.Z):
            continue
        it = body & s2
        if it is None or float(it.volume) <= 1e-6:
            continue
        tools.append(bd.Box(b2.size.X + 2 * clr, b2.size.Y + 2 * clr,
                            b2.size.Z + 2 * clr).locate(bd.Location(
                                (b2.center().X, b2.center().Y, b2.center().Z))))
    if not tools:
        return None
    u = tools[0]
    for t in tools[1:]:
        u = u + t
    print(f"  스톡 keep-out {len(tools)}개 (여유 {clr} mm)  "
          f"vol {float(u.volume):,.1f}")
    return u


def motion15_protect(bd):
    """±15도 모션 포락선 keep-out (원본 `#joystick_angle = 15 deg`).

    - 도달집합은 반각 15도 **원뿔이 아니라 정사각형** |roll|<=15 & |pitch|<=15 다.
      코너 (15,15) 의 합성 편향은 acos(cos^2 15) = 21.06도 로 원뿔 밖이라,
      원뿔로 만들면 코너 4자세에서 간섭이 남는다 (실측 48~129점).
    - 밴드는 볼록껍질 반경 32각형이다. 축정렬 사각형(bbox)으로 자르면 둥근
      포락선의 대각선을 최대 40% 과다 절삭해 살이 0.55mm 까지 얇아졌다.
    - 밴드를 프리즘으로 **쌓지 않고 로프트**한다. 쌓으면 1mm 밴드 계단이 남아
      0.8mm(=1.0-2*PROT_EPS) 짜리 턱이 사방에 생긴다 (실측).

    데이터는 `envelope15.py` 가 만든다 — 합성 회전이 캐시된 ±10도 자세를
    0.0012mm 오차로 재현함을 확인한 뒤 15도로 확장한 것이다. 형상 재구성이 아니다.
    """
    path = os.path.join(P.CACHE_DIR, "motion_envelope15.json")
    if not os.path.exists(path):
        print("  motion_envelope15.json 없음 - 건너뜀")
        return None
    J = json.load(open(path, encoding="utf-8"))
    zs = J["zs"]; pg = J.get("polys15")
    if not pg:
        print("  polys15 없음 - 건너뜀")
        return None
    e = P.PROT_EPS
    runs = []
    cur = []
    for i, z in enumerate(zs):
        if pg[i] and len(pg[i]) >= 3:
            cur.append(i)
        else:
            if len(cur) >= 2: runs.append(cur)
            cur = []
    if len(cur) >= 2: runs.append(cur)
    parts = []
    for run in runs:
        for k in range(len(run) - 1):
            i0, i1 = run[k], run[k + 1]
            z0 = zs[i0] - (e if k == 0 else 0.0)
            z1 = zs[i1] + (e if k == len(run) - 2 else 0.0)
            s0 = bd.Plane(origin=(0, 0, z0)) * bd.Polygon(*[tuple(v) for v in pg[i0]],
                                                          align=None)
            s1 = bd.Plane(origin=(0, 0, z1)) * bd.Polygon(*[tuple(v) for v in pg[i1]],
                                                          align=None)
            parts.append(bd.loft([s0, s1], ruled=True))
    if not parts:
        return None
    out = parts[0]
    for q in parts[1:]:
        out = out + q
    return out


def cavity_protect(bd):
    """검증된 내부 포락선 + 캐리어 인출 스윕으로 공동 보호 solid 를 만든다.

    포락선 데이터는 Onshape 에서 검증된 **모션 포락선 캐시**다 (§16 CACHED).
    형상 재구성이 아니라 keep-out 용이다.
    """
    from build123d import Box, Location
    path = os.path.join(P.CACHE_DIR, "conformal_envelope.json")
    J = json.load(open(path, encoding="utf-8"))
    zs = J["zs"]
    rects = J["rects_ext"]
    parts = []
    i = 0
    while i < len(zs):
        r = rects[i]
        if not r.get("body") and not r.get("tail"):
            i += 1
            continue
        j = i
        while (j + 1 < len(zs) and rects[j + 1].get("body") == r.get("body")
               and rects[j + 1].get("tail") == r.get("tail")):
            j += 1
        z0, z1 = zs[i], zs[j] + (zs[1] - zs[0])
        for key in ("body", "tail"):
            b = r.get(key)
            if not b:
                continue
            w, d = b[1] - b[0], b[3] - b[2]
            if w <= 0.1 or d <= 0.1:
                continue
            # PROT_EPS: 밴드 경계가 안쪽 loft 면과 **정확히** 일치하면 OCC 가
            # 두께 0 접합을 만들고 (Y=-25 / X=+-49 에서 실제로 발생) solid 가
            # invalid 가 된다. keep-out 은 키우는 쪽이 보수적이므로 부풀린다.
            # 하우징은 뒤에서 통째로 다시 union 되므로 형상 손실이 없다.
            e = P.PROT_EPS
            parts.append(Box(w + 2 * e, d + 2 * e, (z1 - z0) + 2 * e).locate(
                Location((0.5 * (b[0] + b[1]), 0.5 * (b[2] + b[3]),
                          0.5 * (z0 + z1)))))
        i = j + 1
    prot = parts[0]
    for p in parts[1:]:
        prot = prot + p
    return prot


# ------------------------------------------------------------------ 메인

def build(variant=None, lower_kind=None, skip_fillets=(), ramp_deg=None,
          slope_deg=None, rear_support=False, pad_width=None,
          skirt_top=None, slope_rear=False, slope_blend=False,
          motion15=False):
    bd = G.b3d()
    from build123d import Location, loft

    req, _ = P.missing_references()
    if req:
        print("STOP - 동결 레퍼런스 STEP 없음:", req)
        return None

    print("=" * 78)
    print("W2 인체공학 외피 생성 (build123d)")
    print("=" * 78)

    core = bd.import_step(P.reference_path("conformal_core"))
    sol = sorted(core.solids(), key=lambda s: float(s.volume))
    carrier, housing = sol[0], sol[1]
    print(f"  HOUSING {float(housing.volume):,.2f} mm3   "
          f"CARRIER {float(carrier.volume):,.2f} mm3")

    anchor, front, slope = pad_plane()
    PADW = pad_width or P.WRIST_PAD_WIDTH   # 팔받침 폭 (기본 86, flush 는 133.6)
    print(f"  손목 패드 평면  앵커 (Y {anchor[0]:.1f}, Z {anchor[1]:.4f})  "
          f"앞끝 (Y {front[0]:.3f}, Z {front[1]:.3f})  기울기 {slope:.5f}")

    prof = housing_profile(bd, housing)
    print(f"  HOUSING Z 단면 {len(prof)} 스테이션 측정")

    # ---------------- SMOOTH_ENVELOPE : 본체 (Z 스택 loft) ----------------
    # 각 스테이션은 HOUSING 실측 경계를 **덮는다** (계단이 새 면 아래로 묻힌다).
    MARG = 2.5          # 실측 경계 위 여유 (계단을 덮는 스킨)
    # 경계값(bound) 기준으로 다룬다. 크기만 max 하고 중심을 그대로 두면
    # 단면이 엉뚱한 쪽으로 부푼다 (실제로 +Y 가 22 mm 부풀었다).
    bnds = []
    for p in prof:
        bnds.append([p["z"], p["x0"] - MARG, p["x1"] + MARG,
                     p["y0"] - MARG, p["y1"] + MARG])
    # 단조 스무딩: 아래 단면은 위쪽 모든 단면을 **덮는다** (역단/허리 제거)
    for i in range(len(bnds) - 2, -1, -1):
        for k, op in ((1, min), (2, max), (3, min), (4, max)):
            bnds[i][k] = op(bnds[i][k], bnds[i + 1][k])
    secs = [(z, x1 - x0, y1 - y0, 0.5 * (x0 + x1), 0.5 * (y0 + y1))
            for z, x0, x1, y0, y1 in bnds]
    # 코너 반경: 아래 넓게 -> 위 작게
    body_sk = []
    for k, (z, w, d, cx, cy) in enumerate(secs):
        r = 14.0 - 4.0 * (k / max(1, len(secs) - 1))
        body_sk.append(rr_sketch(bd, bd.Plane(origin=(0, 0, z)), w, d, r, cx, cy))
    # ruled=True: 스테이션 13->14 에서 깊이가 5mm Z 구간 동안 160->113 으로
    # 급변한다 (덱 개구부 구간). 스플라인 loft 는 여기서 overshoot 해 바깥/안쪽
    # 곡면이 교차하고, 그 결과 `body - body_in` 에 invalid face 가 생겼다.
    # 선형 보간은 균일 인셋을 정확히 보존하므로 벽이 음수가 될 수 없다.
    body = loft(body_sk, ruled=True)
    print(f"  본체 envelope loft  {len(body_sk)} 섹션  vol {float(body.volume):,.0f}")
    body_in_sk = []
    for k, (z, w, d, cx, cy) in enumerate(secs):
        r = max(2.0, 14.0 - 4.0 * (k / max(1, len(secs) - 1)) - P.SHELL_WALL)
        body_in_sk.append(rr_sketch(bd, bd.Plane(origin=(0, 0, z)),
                                    max(2.0, w - 2 * P.SHELL_WALL),
                                    max(2.0, d - 2 * P.SHELL_WALL), r, cx, cy))
    body_in = loft(body_in_sk, ruled=True)

    # ---------------- WRIST : Y 스택 loft (§9 multi-section) ----------------
    ys = [front[0], front[0] + 18, front[0] + 38, front[0] + 58, anchor[0]]
    labels = ["front lip", "early wrist", "mid wrist", "palm heel", "transition"]
    wfrac = [0.72, 0.86, 1.00, 1.00, 1.00]      # 앞이 좁다 (§8 상면 흐름)
    tops = [None] * len(ys)                     # None = 패드 평면을 따른다
    if variant:
        extra = FRONT_VARIANTS[variant]
        for sfwd, hw, wf in reversed(extra):    # y 증가 순서로 앞에 붙인다
            ys.insert(0, front[0] - sfwd)
            labels.insert(0, f"blend s{sfwd:.0f}")
            wfrac.insert(0, wf)
            tops.insert(0, hw)
    if slope_deg:
        # **단일 연속 경사** — 7도 손목 패드를 없애고 한 면으로 지면까지 내린다.
        #
        # 기준점이 핵심이다. 하우징 상면(덱)은 **이미 20도로 앞으로 내려간다**.
        # 그립 능선에서 20도보다 가파르게 내리면 하우징 위 구간에서 덱 밑으로
        # 묻히고, 묻힌 벽이 안쪽 loft 에 먹혀 앞부분이 분리된다
        # (실측: shell 이 2조각, heal 에서 solid 2개로 분할).
        # 그래서 **하우징 앞끝 상단**을 기준으로 잡는다. 20도면 덱을 그대로
        # 연장해 꺾임 0 이고, 그보다 가파르면 (theta-20)도 만큼만 꺾인다.
        import side_profile as SP
        hb = housing.bounding_box()
        y_front_body = float(hb.min.Y) - MARG
        z_a = DECK + 0.5                     # 덱보다 살짝 위 (동일 평면 회피)
        u_a = (0.9396926207859084 * y_front_body
               - 0.3420201433256687 * z_a)
        h_a = (0.3420201433256687 * y_front_body
               + 0.9396926207859084 * z_a - GROUND_H)
        y_tip, run = ramp_tip_y(slope_deg, u_a, h_a, SP.LIP_H)
        _slope_anchor = (y_front_body, y_tip)
        # 뒤끝. **코어 앞부분은 지면 근처 스커트뿐이고 덱 높이 몸통은
        # Y >= -30 에서만 있다.** -35 에서 끊으면 코어 몸통과 안 겹쳐
        # 중간 높이가 빈다(실측: Y -33, Z -70~-116 에 재료 없음).
        # 그립 착좌 발자국이 Y -10.2 부터라 그 앞까지만 물린다.
        # 기본 -15 에서 끊으면 램프(133.6 폭)와 하우징 블록(113 폭) 사이에
        # 단차가 남고, 그 접합부에 초승달 관통 슬릿이 생긴다 (좌우 대칭, 실측).
        # slope_rear=True 면 하우징 뒤끝까지 연장해 바깥 면을 연속으로 만든다.
        y_rear = (float(hb.max.Y) + MARG) if slope_rear else (anchor[0] + 5.0)
        n_s = max(6, int(round((y_rear - y_tip) / 6.0)))
        ys = [y_tip + (y_rear - y_tip) * k / n_s for k in range(n_s + 1)]
        labels = [f"slope {k:02d}" for k in range(n_s + 1)]
        # 폭은 **하우징 앞끝(y_front_body)에서 1.00 에 도달**해야 한다.
        # 뒤끝(Y=-15) 기준으로 잡으면 접합부에서 아직 0.91 이라
        # TOP 실루엣이 122.3 -> 133.6 으로 튄다 (실측 편측 5.9mm 단차).
        # 그 뒤 구간은 1.00 으로 유지해 하우징 옆선과 이어진다.
        # slope_blend: 하우징 앞끝에서 1.00 을 찍은 뒤, 겹치는 구간에서
        # **하우징 자체 폭(113.0)까지 부드럽게 좁힌다.** 그래야 램프가 끝나는
        # Y=-15 에서 단차가 0 이 되어 접합부 초승달 슬릿이 안 생긴다.
        # (뒤끝까지 연장하는 방식은 코어에서 8.3mm 떠 이중벽 + 관통이 됐다.)
        W_BLOCK = 113.0
        f_end = W_BLOCK / (pad_width or P.WRIST_PAD_WIDTH)
        wfrac = []
        for k in range(n_s + 1):
            yk = ys[k]
            f = (yk - y_tip) / (y_front_body - y_tip)
            f = min(1.0, max(0.0, f))
            w = 0.68 + (1.00 - 0.68) * f
            if slope_blend and yk > y_front_body:
                g = (yk - y_front_body) / (y_rear - y_front_body)
                w = 1.00 + (f_end - 1.00) * min(1.0, max(0.0, g))
            wfrac.append(w)
        tops = [("RAMP", slope_deg, u_a, h_a)] * (n_s + 1)
        print(f"  단일경사 {slope_deg:.0f}deg  기준(하우징 앞끝) u {u_a:.2f} "
              f"h {h_a:.2f}  수평런 {run:.1f}  팁 Y {y_tip:.2f}  섹션 {n_s+1}"
              f"  (덱 대비 꺾임 {slope_deg-20:.0f}deg)")
    elif ramp_deg:
        # 전면 램프: 현재 패드 앞끝에서 **앞으로 덧붙이는 새 경사면**.
        # 손목 접촉면 / HAND_REF / 20도 기준면은 손대지 않는다.
        # 밑면은 전 구간 지면이다 (예전의 뜬 립 프로파일은 램프가 대체한다 —
        # 그대로 두면 램프 밑면과 립 사이에 노치가 생긴다).
        import side_profile as SP
        h_tip = (0.3420201433256687 * front[0]
                 + 0.9396926207859084 * pad_z(front[0], anchor, slope)
                 - GROUND_H)
        y_tip, run = ramp_tip_y(ramp_deg, SP.U_TIP, h_tip, SP.LIP_H)
        n_ext = max(2, int(round((front[0] - y_tip) / 5.0)))
        print(f"  램프 {ramp_deg:.0f}deg  앞끝 h {h_tip:.2f}  수평런 {run:.1f}  "
              f"팁 Y {y_tip:.2f}  섹션 {n_ext}")
        for k in range(n_ext, 0, -1):
            yy = y_tip + (front[0] - y_tip) * (k - 1) / n_ext
            ys.insert(0, yy)
            labels.insert(0, f"ramp {front[0]-yy:6.1f}")
            wfrac.insert(0, 0.72 - 0.10 * (front[0] - yy) / (front[0] - y_tip))
            tops.insert(0, ("RAMP", ramp_deg, SP.U_TIP, h_tip))
    if lower_kind:
        # 하부 프로파일 방식: **윗면 규칙은 손대지 않는다**. 앞으로 확장한
        # 단면들도 top = 패드 평면이고, 뒤에서 전면 수직면으로 잘라낸다.
        import side_profile as SP
        y_lip = (0.9396926207859084 * SP.U_TIP
                 + 0.3420201433256687 * (SP.LIP_H + GROUND_H))
        n_ext = max(1, int(round((front[0] - y_lip) / 4.0)))
        for k in range(n_ext, 0, -1):
            yy = y_lip + (front[0] - y_lip) * (k - 1) / n_ext
            ys.insert(0, yy)
            labels.insert(0, f"skirt {front[0]-yy:5.1f}")
            wfrac.insert(0, 0.72 - 0.06 * (front[0] - yy) / (front[0] - y_lip))
            tops.insert(0, None)

    def _bottoms(ys_):
        """각 단면의 (바깥 zbot, 안쪽 zbot). 하부 프로파일에서 직접 계산 (§12)."""
        if not lower_kind:
            return [(ground_z(y) - WRIST_UNDER, ground_z(y) - WRIST_UNDER_IN)
                    for y in ys_]
        import side_profile as SP
        wall_z = P.NECK_WALL / UP[2]
        out = []
        for y in ys_:
            sol = SP.zbot_for_y(y, lower_kind)
            zb = sol[0] if sol else ground_z(y)
            hp = float(SP.lower_fn(lower_kind)(sol[1])) if sol else 0.0
            # 지면 구간과 뜬 립 구간의 전환.
            # **바깥 밑면을 블렌드로 끌어내리면 안 된다** — 전환 구간의 밑면이
            # 프로파일보다 낮아져 지면에 일찍 닿는다 (실측: 접지 u 가 설계 -60
            # 대신 -70.9, 하부 최대각 15.8도 대신 84.4도). 불연속은 **지면 아래**
            # 에서만 일어나므로 지면 절단이 알아서 지운다. 그래서 하드 스위치.
            if hp <= 0.05:                       # 지면에 앉는 구간 -> 아래로 열어 둔다
                zo = zb - WRIST_UNDER
                zi = ground_z(y) - WRIST_UNDER_IN
            else:                                # 뜬 립 구간 -> 바닥을 닫는다
                zo = zb
                zi = zb + wall_z
            out.append((zo, zi))
        return out

    bots = _bottoms(ys)
    wrist_sk = []
    print(f"  손목 섹션  (변형 {variant or lower_kind or 'W2(기준)'})")
    for y, lab, wf, ht, (zo, zi) in zip(ys, labels, wfrac, tops, bots):
        if ht is None:
            ztop = pad_z(y, anchor, slope)
        elif isinstance(ht, tuple):
            ztop = ramp_z(y, ht[1], ht[2], ht[3])
            if slope_deg:
                # 25도는 덱(20도)보다 가팔라 뒤로 갈수록 덱 위로 솟는다
                # (실측 Y=-15 에서 6.3mm). 덱에서 잘라 하우징 상면과 맞춘다.
                ztop = min(ztop, DECK)
        else:
            ztop = top_z_at(y, ht)
        # **바깥 단면도 지면 아래까지 내린다.** 예전에는 zbot = ground_z(y) 였는데
        # 그러면 바깥 코너 R16 이 안쪽 단면(그 높이에서 더 넓다)에 통째로 먹혀서
        # 손목이 지면에서 4.88mm 떠 버렸다 (실측 4.41~4.66).
        zbot = zo
        w = PADW * wf
        h = ztop - zbot
        cz = 0.5 * (ztop + zbot)
        r = min(P.WRIST_PAD_RADIUS, 0.45 * w, 0.45 * h)
        wrist_sk.append(rr_sketch(bd, yz_plane(bd, y), w, h, r, 0.0, cz))
        hw = (ztop - ground_z(y)) * UP[2]
        hb = (zbot - ground_z(y)) * UP[2]
        print(f"    {lab:<13s} Y {y:8.2f}  W {w:6.1f}  상면 {hw:6.1f}  "
              f"밑면 {hb:6.1f}  R{r:.1f}")
    wrist = (seg_loft(loft, wrist_sk) if (variant or lower_kind or ramp_deg or slope_deg)
             else loft(wrist_sk))
    _v("wrist", wrist)
    print(f"  손목 loft  vol {float(wrist.volume):,.0f}")
    wrist_in_sk = []
    for y, wf, ht, (zo, zi) in zip(ys, wfrac, tops, bots):
        if ht is None:
            base = pad_z(y, anchor, slope)
        elif isinstance(ht, tuple):
            base = ramp_z(y, ht[1], ht[2], ht[3])
            if slope_deg:
                base = min(base, DECK)
        else:
            base = top_z_at(y, ht)
        ztop = base - P.WRIST_WALL
        zbot = zi
        w = max(2.0, PADW * wf - 2 * P.NECK_WALL)
        h = max(1.0, ztop - zbot)
        cz = 0.5 * (ztop + zbot)
        r = max(1.0, min(P.WRIST_PAD_RADIUS - P.NECK_WALL, 0.45 * w, 0.45 * h))
        wrist_in_sk.append(rr_sketch(bd, yz_plane(bd, y), w, h, r, 0.0, cz))
    wrist_in = (seg_loft(loft, wrist_in_sk) if (variant or lower_kind or ramp_deg or slope_deg)
                else loft(wrist_in_sk))

    env = body + wrist
    env_in = body_in + wrist_in
    print(f"  안쪽 loft (중공용) vol {float(env_in.volume):,.0f}")
    print(f"  SMOOTH_ENVELOPE 합집합  vol {float(env.volume):,.0f}")

    # ---------------- 바닥 / 상부 평면 절단 ----------------
    from build123d import Plane as BPlane
    big = 900.0   # 20deg 팁이 u~-277 이라 500(=+-250)로는 지면 절단이 못 미친다
    # 지면 평면 아래 제거
    gn = UP
    gpt = gn * GROUND_H
    cutter = bd.Box(big, big, big).locate(bd.Location(
        bd.Plane(origin=tuple(gpt - gn * (big / 2)),
                 z_dir=tuple(gn)).location.position,
        (0, 0, 0)))
    # 간단히: 지면 아래 반공간을 sketch+extrude 로
    pl = BPlane(origin=tuple(gpt), z_dir=tuple(gn))
    half = bd.extrude(rr_sketch(bd, pl, big, big, 1.0), amount=-big)
    env = env - half
    # 덱 평면 위 제거 (패드 영역 제외)
    top = bd.Box(big, big, big).locate(bd.Location((0, 0, DECK + big / 2)))
    fy_min = min(ys) - 40.0
    fy_max = max(anchor[0], max(ys) + 2.0)
    keep_pad = bd.Box(big, abs(fy_max - fy_min), big).locate(
        bd.Location((0, 0.5 * (fy_max + fy_min), DECK + big / 2)))
    env = env - (top - keep_pad)
    # 패드 평면 위 제거
    pn = np.array([0.0, -slope, 1.0])
    pn = pn / np.linalg.norm(pn)
    pd = float(pn[1] * anchor[0] + pn[2] * anchor[1])
    ppl = BPlane(origin=tuple(pn * pd), z_dir=tuple(pn))
    if not slope_deg:
        env = env - bd.extrude(rr_sketch(bd, ppl, big, big, 1.0), amount=big)
    if lower_kind:
        # 전면 **수직** 절단면. 손목 앞끝 u 를 그대로 유지하면서,
        # 지금의 등Y(월드 70도, 오버행) 전면을 월드 수직면으로 바꾼다.
        import side_profile as SP
        fpl = BPlane(origin=tuple(UH * SP.U_TIP), z_dir=tuple(UH))
        env = env - bd.extrude(rr_sketch(bd, fpl, big, big, 1.0), amount=-big)
        print(f"  전면 수직 절단 (u >= {SP.U_TIP:.2f})  vol {float(env.volume):,.0f}")
    print(f"  평면 절단 후 envelope  vol {float(env.volume):,.0f}")

    # ---------------- 공동 보호 + 하우징 제외 ----------------
    prot = cavity_protect(bd)
    print(f"  CAVITY_PROTECT vol {float(prot.volume):,.0f}")
    carr_sweep = carrier
    for dz in range(4, 104, 4):
        carr_sweep = carr_sweep + carrier.moved(bd.Location((0, 0, -float(dz))))
    print(f"  캐리어 인출 스윕 vol {float(carr_sweep.volume):,.0f}")

    # 중공화: 안쪽 loft 를 빼서 셸로 만든다 (아래로 열림)
    _v("env", env); _v("env_in", env_in)
    shell = env - env_in
    _v("shell", shell)
    print(f"  중공 셸 vol {float(shell.volume):,.0f}  "
          f"(통짜 대비 -{float(env.volume) - float(shell.volume):,.0f})")
    # `- housing` 은 집합적으로 불필요하다: (E-H-C) u H == (E-C) u H.
    # 그런데 그 한 단계가 HOUSING 외피와 동일면 접합을 만들어 두께 0.2mm 짜리
    # 내부 공동 shell 을 남겼고, 그 결과 NEW 가 invalid 가 되어 이후 boolean 이
    # 전부 빈 결과를 돌려줬다. 그래서 뺄셈 대상에서 housing 을 제거한다.
    keep = shell - prot - carr_sweep
    _v("keep", keep)
    add = keep - housing                      # 보고용(순증분)에만 쓴다
    print(f"  ERGO_ADD vol {float(add.volume):,.0f}")

    new = keep + housing
    new = G.heal(new, label="NEW_HOUSING")
    if P.EDGE_FILLET > 0:
        new = apply_fillets(bd, new, anchor, front, slope, skip_fillets)
        # 오목 모서리 필렛은 재료를 **더한다**. 실측에서 그게 공동/캐리어
        # keep-out 을 침범했다 (캐리어 t=0 에서 201.5 mm3). 그래서 필렛 뒤에
        # keep-out 을 다시 빼고 동결 코어를 다시 합쳐 불변량을 복원한다.
        ko = stock_keepout(bd, new - housing)
        new = new - prot - carr_sweep
        if ko is not None:
            new = new - ko
        new = new + housing
        new = G.heal(new, label="NEW_FILLETED")
        print(f"  필렛 후 keep-out 복원  vol {float(new.volume):,.1f}")
    if rear_support:
        y_front_body, y_tip = _slope_anchor
        # ---- A: 측면+후방 스커트 (통짜) ----
        # 20도 경사 때문에 뒤로 갈수록 지면이 멀어져 뒤/옆이 22~55mm 떠 있다.
        # 하우징 **외곽선을 그대로** 지면까지 내린다. 캐리어(X +-59)가 -Z 로
        # 인출되므로 그 경로만 비우면 측면 |X| 59~66.8 과 후방은 내릴 수 있다.
        z0s, w0s, d0s, cx0s, cy0s = secs[0]
        # **하우징 안쪽에서 시작해야 붙는다.** 바닥 스테이션(-187.87)에서
        # 내리면 무릎 절단부(Y 64~72, 하우징 최저 -146.96)와 41mm 떠서
        # 조각들이 공중에 남는다 (실측: union 후에도 solid 9개).
        # 기본 -140 은 **블록 구간 옆면에 노치를 남긴다** (실측: Y>-13 에서
        # X 58~66.8 의 재료 최상단이 Z -129~-137, 램프 구간은 -63.6).
        # 그 10.3mm 단차가 3/4 방향에서 뚫린 틈처럼 보인다.
        # skirt_top 을 덱까지 올리면 바깥 면이 램프에서 덱까지 연속이 된다.
        sk_top = -140.0 if skirt_top is None else float(skirt_top)
        # 지면이 가장 낮은 곳은 **뒤쪽 Y** 다 (20도 경사라 뒤로 갈수록 멀어진다).
        # 앞쪽 Y 로 잡으면 뒤에서 44mm 못 미쳐 스커트가 공중에 뜬다 (실측).
        sk_bot = (GROUND_H - UP[1] * (cy0s + 0.5 * d0s)) / UP[2] - 20.0
        skirt = bd.extrude(
            rr_sketch(bd, bd.Plane(origin=(0, 0, sk_top)), w0s, d0s, 14.0,
                      cx0s, cy0s), amount=-(sk_top - sk_bot))
        # 캐리어 인출 통로는 **여유를 두고** 비운다. carr_sweep 로만 자르면
        # 접촉면이 남아 t=10 에서 1.061mm3 가 걸린다 (실측).
        cb = carrier.bounding_box()
        clr = 0.5
        cz_top = float(cb.max.Z) + clr
        cz_bot = float(cb.min.Z) - 120.0
        carr_clear = bd.Box(float(cb.size.X) + 2 * clr,
                            float(cb.size.Y) + 2 * clr, cz_top - cz_bot).locate(
            bd.Location((float(cb.center().X), float(cb.center().Y),
                         0.5 * (cz_top + cz_bot))))
        skirt = skirt - half - carr_clear - prot
        # 캐리어 인출 경로가 가운데를 관통하므로 좌우 레일 / 후방이 **분리되는
        # 것이 정상**이다 (실측 11조각). 하우징에 union 하면 다시 하나가 되므로
        # 여기서 단독 heal 을 걸지 않는다. 부스러기만 걸러낸다.
        # 하우징과 실제로 겹치는 조각만 남긴다. keep-out 사이에 낀 부스러기
        # (실측 155 / 155 / 1,058 mm3) 는 union 해도 공중에 남는다.
        allp = list(skirt.solids())
        pieces = []
        for sp in allp:
            ov = new & sp
            if ov is not None and float(ov.volume) > 1.0:
                pieces.append(sp)
        drop = len(allp) - len(pieces)
        print(f"  측면+후방 스커트 {len(pieces)}조각 "
              f"vol {sum(float(sp.volume) for sp in pieces):,.0f}"
              f"{f'  (부스러기 {drop}개 제거)' if drop else ''}")
        skirt = pieces

        # **한 번의 다중 fuse 로 합친다.** 하나씩 `new = new + sp` 로 더하면
        # 첫 union 뒤 new 가 Compound 가 되고, Compound 를 피연산자로 준 부울은
        # 조용히 잘못된 결과를 낸다 (이전 라운드에 기록한 함정).
        for i, sp in enumerate(skirt):
            b = sp.bounding_box()
            print(f"    조각{i} vol {float(sp.volume):9,.0f}  "
                  f"X[{b.min.X:7.2f},{b.max.X:7.2f}] Y[{b.min.Y:7.2f},{b.max.Y:7.2f}] "
                  f"Z[{b.min.Z:8.2f},{b.max.Z:8.2f}]")
        new = new.fuse(*skirt)
        # 스커트는 필렛/keep-out 재적용 **뒤에** 붙으므로 그 처리를 다시 준다.
        new = new - prot - carr_clear
        ko2 = stock_keepout(bd, new - housing)
        if ko2 is not None:
            new = new - ko2
        new = new + housing
        new = G.heal(new, label="REAR_SUPPORT")

    if motion15:
        m15 = motion15_protect(bd)
        if m15 is not None:
            before = float(new.volume)
            new = new - m15
            new = G.heal(new, label="MOTION15")
            print(f"  MOTION15 절삭  {before - float(new.volume):,.1f} mm3 제거"
                  f"  -> vol {float(new.volume):,.1f}")

    print(f"  NEW_HOUSING vol {float(new.volume):,.0f}  "
          f"(HOUSING 대비 +{float(new.volume) - float(housing.volume):,.0f})")
    return {"new": new, "housing": housing, "carrier": carrier,
            "add": add, "env": env, "anchor": anchor, "front": front,
            "slope": slope}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    variant = lower = None
    skip = ()
    ramp = slope = None
    rear = False
    padw = None
    skirt_top = None; slope_rear = False; slope_blend = False; motion15 = False
    if arg and arg.startswith("S") and arg.endswith("AWB15") and arg[1:-5].isdigit():
        # 15 = ±15도 모션 포락선까지 확보 (동결 코어 공동벽 국소 절삭)
        slope = float(arg[1:-5]); rear = True; padw = 133.6
        slope_blend = True; motion15 = True
        name = f"ERGO_HOUSING_{int(slope)}_WRAP_W134_M15"
    elif arg and arg.startswith("S") and arg.endswith("AWB") and arg[1:-3].isdigit():
        # B = 접합 구간에서 램프 폭을 하우징 폭까지 블렌드 (단차/슬릿 제거)
        slope = float(arg[1:-3]); rear = True; padw = 133.6; slope_blend = True
        name = f"ERGO_HOUSING_{int(slope)}_WRAP_W134_BLEND"
    elif arg and arg.startswith("S") and arg.endswith("AWR") and arg[1:-3].isdigit():
        # R = 램프 단면을 하우징 뒤끝까지 연장 (옆면 단차/슬릿 제거)
        slope = float(arg[1:-3]); rear = True; padw = 133.6; slope_rear = True
        name = f"ERGO_HOUSING_{int(slope)}_WRAP_W134_CONT"
    elif arg and arg.startswith("S") and arg.endswith("AWT") and arg[1:-3].isdigit():
        # T = skirt Top -> 스커트를 덱까지 올려 옆면 노치를 없앤다
        slope = float(arg[1:-3]); rear = True; padw = 133.6
        skirt_top = DECK
        name = f"ERGO_HOUSING_{int(slope)}_WRAP_W134_FULLSIDE"
    elif arg and arg.startswith("S") and arg.endswith("AW") and arg[1:-2].isdigit():
        slope = float(arg[1:-2]); rear = True; padw = 133.6
        name = f"ERGO_HOUSING_{int(slope)}_WRAP_W134"
    elif arg and arg.startswith("S") and arg.endswith("A") and arg[1:-1].isdigit():
        slope = float(arg[1:-1]); rear = True
        name = f"ERGO_HOUSING_W2_SLOPE{int(slope)}_A"
    elif arg and arg.startswith("S") and arg[1:].isdigit():
        slope = float(arg[1:])
        name = f"ERGO_HOUSING_W2_SLOPE{int(slope)}"
    elif arg and arg.startswith("R") and arg[1:].isdigit():
        ramp = float(arg[1:])
        name = f"ERGO_HOUSING_W2_RAMP{int(ramp)}"
    elif arg in ("F1", "F0"):
        lower = "B"
        name = f"ERGO_HOUSING_W2_TEST_{arg}"
        if arg == "F0":
            skip = ("GROUND_TRANSITION",)
    elif arg == "PRINT":
        lower, skip = "B", ("GROUND_TRANSITION",)
        name = "ERGO_HOUSING_W2_PRINT_FINAL"
    elif arg in ("LA", "LB"):
        lower = arg[1]
        name = f"ERGO_HOUSING_W2_GROUND_{lower}"
    elif arg:
        variant = arg
        name = f"ERGO_HOUSING_W2_GROUND_{arg}"
    else:
        name = "ERGO_HOUSING_W2"
    r = build(variant, lower, skip, ramp, slope, rear, padw, skirt_top, slope_rear,
              slope_blend, motion15)
    if r is None:
        return 2
    G.export_all(r["new"], name, tolerance=0.015, angular_tolerance=0.08)
    print("\n출력: export/step|stl|brep/ERGO_HOUSING_W2.*")
    return 0


if __name__ == "__main__":
    sys.exit(main())
