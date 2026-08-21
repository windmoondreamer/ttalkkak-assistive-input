"""F2 재검증에서 드러난 '개구부 바깥 쉘 벽' 제약을 넣은 재최적화 (READ ONLY 계산).

새 제약: 스위치 앞면 네 꼭짓점이 기존 8x8 개구부 안으로 투영되어야 한다.
        (그래야 앞면이 만나는 재료가 홀더 lip 뿐이고, 쉘 벽을 만나지 않는다)
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.optimize import minimize
from axis_opt import (sat, exact_gap, obb, frame, P, N0, NAMES, SW, POCKET, KEY_PAIRS)

FR0 = [frame(N0[i]) for i in range(4)]
OPEN_HALF = 4.0
TRIM = 2.8


def axf(i, p, q):
    u, v, z = FR0[i]
    a = z + p * u + q * v
    return a / np.linalg.norm(a)


def dvf(p, q):
    return math.degrees(math.atan(math.hypot(p, q)))


def n0loc(i, pt):
    u0, v0, z0 = FR0[i]
    d = np.asarray(pt) - P[i]
    return float(np.dot(d, u0)), float(np.dot(d, v0)), -float(np.dot(d, z0))


def face_corners(i, a, front):
    u, v, z = frame(a)
    return [P[i] - z * front + u * p + v * q
            for p in (-SW / 2, SW / 2) for q in (-SW / 2, SW / 2)]


def g_open(x, front, margin):
    """앞면 꼭짓점이 개구부 안에 있는가 (양수면 만족)."""
    w = 9.0
    for i in range(4):
        for c in face_corners(i, axf(i, x[2 * i], x[2 * i + 1]), front):
            x0, y0, _ = n0loc(i, c)
            w = min(w, OPEN_HALF - margin - max(abs(x0), abs(y0)))
    return w


def g_lip(x, front, lipmin):
    w = 9.0
    for i in range(4):
        for c in face_corners(i, axf(i, x[2 * i], x[2 * i + 1]), front):
            w = min(w, n0loc(i, c)[2] - TRIM - lipmin)
    return w


def pocket_x(i, a, sign, front):
    c, A, h = obb(P[i], a, POCKET, SW + 0.2, front)
    xs = [(c + A.T @ (np.array([p, q, r], float) * h))[0]
          for p in (-1, 1) for q in (-1, 1) for r in (-1, 1)]
    return max(xs) if sign > 0 else min(xs)


def g_split(x, front, wall):
    return min(-wall - pocket_x(2, axf(2, x[4], x[5]), +1, front),
               pocket_x(3, axf(3, x[6], x[7]), -1, front) - wall)


def mnclr(x, front):
    B = [obb(P[i], axf(i, x[2 * i], x[2 * i + 1]), SW, SW, front) for i in range(4)]
    m = 1e9
    for i, j in KEY_PAIRS:
        hit, v = sat(B[i], B[j])
        m = min(m, -v if hit else v)
    return m


def solve(front, tgt, wall, lipmin, margin, ntry=10, it=150):
    rng = np.random.default_rng(53); best = None
    cons_base = lambda: [
        {"type": "ineq", "fun": lambda y: mnclr(y[:8], front) - tgt},
        {"type": "ineq", "fun": lambda y: g_split(y[:8], front, wall)},
        {"type": "ineq", "fun": lambda y: g_lip(y[:8], front, lipmin)},
        {"type": "ineq", "fun": lambda y: g_open(y[:8], front, margin)}]
    for k in range(ntry):
        x0 = np.zeros(8) if k == 0 else rng.normal(0, 0.20, 8)
        y0 = np.append(x0, [max(dvf(x0[2 * i], x0[2 * i + 1]) for i in range(4)) + 3])
        cons = cons_base()
        for i in range(4):
            cons.append({"type": "ineq", "fun": (lambda y, i=i: y[8] - dvf(y[2 * i], y[2 * i + 1]))})
        r = minimize(lambda y: y[8], y0, method="SLSQP", constraints=cons,
                     bounds=[(-0.9, 0.9)] * 8 + [(0, 60)], options={"maxiter": it, "ftol": 1e-9})
        x = r.x[:8]
        if (mnclr(x, front) >= tgt - 1e-6 and g_split(x, front, wall) >= -1e-6
                and g_lip(x, front, lipmin) >= -1e-6 and g_open(x, front, margin) >= -1e-6):
            m = max(dvf(x[2 * i], x[2 * i + 1]) for i in range(4))
            if best is None or m < best[0] - 1e-4:
                best = (m, x.copy())
    return best


if __name__ == "__main__":
    out = {}
    for lip in (1.5, 2.0, 2.5):
        front = 3.0 + lip
        b = solve(front, 1.2, 1.5, 0.5, 0.1)
        k = f"lip{lip}"
        if b is None:
            out[k] = None; print(f"{k} (front {front}): 해 없음", flush=True); continue
        m, x = b
        A = [axf(i, x[2 * i], x[2 * i + 1]) for i in range(4)]
        ds = [dvf(x[2 * i], x[2 * i + 1]) for i in range(4)]
        out[k] = dict(axes=[list(map(float, a)) for a in A], dev=ds, maxdev=m,
                      front=front, clr=mnclr(x, front),
                      openmargin=g_open(x, front, 0.0), lipmin=g_lip(x, front, 0.0))
        print(f"{k} (front {front}): maxdev {m:.2f}  dev {[round(v,2) for v in ds]}  "
              f"clr {mnclr(x,front):.3f}  개구부여유 {g_open(x,front,0.0):.3f}  "
              f"lip {g_lip(x,front,0.0):.3f}", flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "cad_dump", "fix_opt.json"), "w"))
