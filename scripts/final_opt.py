"""front lip / 분할면 벽 / 스위치 여유를 동시에 만족하는 축 최적화 (READ ONLY)."""
import sys, json, math, os
sys.path.insert(0, os.path.dirname(__file__))
from axis_opt import *
import numpy as np
from scipy.optimize import minimize

FR = [frame(N0[i]) for i in range(4)]
TRIM = 2.8                      # holder 앞면 트림 평면 (원래 법선 n0 기준 깊이)


def axf(i, p, q):
    u, v, z = FR[i]
    a = z + p * u + q * v
    return a / np.linalg.norm(a)


def dvf(p, q):
    return math.degrees(math.atan(math.hypot(p, q)))


def n0depth(i, pt):
    return -float(np.dot(np.asarray(pt) - P[i], FR[i][2]))


def lip_min(i, a, front):
    """스위치 앞면 네 꼭짓점의 n0 깊이 최소 - 트림면. (평면 위 아핀함수이므로 꼭짓점만)"""
    u, v, z = frame(a)
    return min(n0depth(i, P[i] - z * front + u * p + v * q)
               for p in (-SW / 2, SW / 2) for q in (-SW / 2, SW / 2)) - TRIM


def pocket_x(i, a, sign, front):
    c, A, h = obb(P[i], a, POCKET, SW + 0.2, front)
    xs = [(c + A.T @ (np.array([p, q, r], float) * h))[0]
          for p in (-1, 1) for q in (-1, 1) for r in (-1, 1)]
    return max(xs) if sign > 0 else min(xs)


def mnclr(x, front):
    B = [obb(P[i], axf(i, x[2 * i], x[2 * i + 1]), SW, SW, front) for i in range(4)]
    m = 1e9
    for i, j in KEY_PAIRS:
        hit, v = sat(B[i], B[j])
        m = min(m, -v if hit else v)
    return m


def g_split(x, wall, front):
    a3 = axf(2, x[4], x[5]); a4 = axf(3, x[6], x[7])
    return min(-wall - pocket_x(2, a3, +1, front), pocket_x(3, a4, -1, front) - wall)


def g_lip(x, lipmin, front):
    return min(lip_min(i, axf(i, x[2 * i], x[2 * i + 1]), front) for i in range(4)) - lipmin


def solve(front, tgt, wall, lipmin, ntry=12, it=160):
    rng = np.random.default_rng(29); best = None
    for k in range(ntry):
        x0 = np.zeros(8) if k == 0 else rng.normal(0, 0.22, 8)
        y0 = np.append(x0, [max(dvf(x0[2 * i], x0[2 * i + 1]) for i in range(4)) + 3])
        cons = [{"type": "ineq", "fun": lambda y: mnclr(y[:8], front) - tgt},
                {"type": "ineq", "fun": lambda y: g_split(y[:8], wall, front)},
                {"type": "ineq", "fun": lambda y: g_lip(y[:8], lipmin, front)}]
        for i in range(4):
            cons.append({"type": "ineq", "fun": (lambda y, i=i: y[8] - dvf(y[2 * i], y[2 * i + 1]))})
        r = minimize(lambda y: y[8], y0, method="SLSQP", constraints=cons,
                     bounds=[(-0.9, 0.9)] * 8 + [(0, 60)], options={"maxiter": it, "ftol": 1e-9})
        x = r.x[:8]
        if (mnclr(x, front) >= tgt - 1e-6 and g_split(x, wall, front) >= -1e-6
                and g_lip(x, lipmin, front) >= -1e-6):
            m = max(dvf(x[2 * i], x[2 * i + 1]) for i in range(4))
            if best is None or m < best[0] - 1e-4:
                best = (m, x.copy())
    if best is None:
        return None
    m, x = best
    W = [1.0, 1.0, 1.4, 2.5]
    cons = [{"type": "ineq", "fun": lambda z: mnclr(z, front) - tgt},
            {"type": "ineq", "fun": lambda z: g_split(z, wall, front)},
            {"type": "ineq", "fun": lambda z: g_lip(z, lipmin, front)},
            {"type": "ineq", "fun": lambda z: m + 0.03 - max(dvf(z[2 * i], z[2 * i + 1]) for i in range(4))}]
    r = minimize(lambda z: sum(W[i] * dvf(z[2 * i], z[2 * i + 1]) for i in range(4)), x,
                 method="SLSQP", constraints=cons, bounds=[(-0.9, 0.9)] * 8,
                 options={"maxiter": 250, "ftol": 1e-10})
    if (mnclr(r.x, front) >= tgt - 1e-6 and g_split(r.x, wall, front) >= -1e-6
            and g_lip(r.x, lipmin, front) >= -1e-6):
        x = r.x
    return x


if __name__ == "__main__":
    out = {}
    for lip in (1.0, 1.2, 1.5):
        front = SHELL_WALL + lip
        for tgt in (1.0, 1.2):
            x = solve(front, tgt, 1.5, 0.5)
            k = f"lip{lip}_t{tgt}"
            if x is None:
                out[k] = None; print(k, "-> 해 없음", flush=True); continue
            A = [axf(i, x[2 * i], x[2 * i + 1]) for i in range(4)]
            ds = [dvf(x[2 * i], x[2 * i + 1]) for i in range(4)]
            L = [lip_min(i, A[i], front) for i in range(4)]
            out[k] = dict(axes=[list(map(float, a)) for a in A], dev=ds, maxdev=max(ds),
                          clr=mnclr(x, front), lip=L, front=front,
                          i3wall=-pocket_x(2, A[2], 1, front))
            print(f"{k}: maxdev {max(ds):.2f}  dev {[round(v,2) for v in ds]}  "
                  f"clr {mnclr(x,front):.3f}  lip최소 {min(L):.3f}  분할벽 {-pocket_x(2,A[2],1,front):.2f}",
                  flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "cad_dump", "axis_final2.json"), "w"))
