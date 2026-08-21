"""칸막이(포켓 간격) 제약을 넣은 재최적화 — F2 재검증 결과 반영 (READ ONLY)."""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.optimize import minimize
from axis_opt import sat, exact_gap, obb, frame, P, N0, NAMES, SW, POCKET, KEY_PAIRS

FR0 = [frame(N0[i]) for i in range(4)]


def axf(i, p, q):
    u, v, z = FR0[i]
    a = z + p * u + q * v
    return a / np.linalg.norm(a)


def dvf(p, q):
    return math.degrees(math.atan(math.hypot(p, q)))


def gaps(x, front, size, length):
    B = [obb(P[i], axf(i, x[2 * i], x[2 * i + 1]), size, length, front) for i in range(4)]
    m = 1e9
    for i, j in KEY_PAIRS:
        hit, v = sat(B[i], B[j])
        m = min(m, -v if hit else v)
    return m


def pocket_x(i, a, sign, front):
    c, A, h = obb(P[i], a, POCKET, SW + 0.2, front)
    xs = [(c + A.T @ (np.array([p, q, r], float) * h))[0]
          for p in (-1, 1) for q in (-1, 1) for r in (-1, 1)]
    return max(xs) if sign > 0 else min(xs)


def g_split(x, front, wall):
    return min(-wall - pocket_x(2, axf(2, x[4], x[5]), +1, front),
               pocket_x(3, axf(3, x[6], x[7]), -1, front) - wall)


def solve(front, div, swt, wall, ntry=12, it=160):
    rng = np.random.default_rng(77); best = None
    for k in range(ntry):
        x0 = np.zeros(8) if k == 0 else rng.normal(0, 0.24, 8)
        y0 = np.append(x0, [max(dvf(x0[2 * i], x0[2 * i + 1]) for i in range(4)) + 4])
        cons = [{"type": "ineq", "fun": lambda y: gaps(y[:8], front, POCKET, SW + 0.2) - div},
                {"type": "ineq", "fun": lambda y: gaps(y[:8], front, SW, SW) - swt},
                {"type": "ineq", "fun": lambda y: g_split(y[:8], front, wall)}]
        for i in range(4):
            cons.append({"type": "ineq", "fun": (lambda y, i=i: y[8] - dvf(y[2 * i], y[2 * i + 1]))})
        r = minimize(lambda y: y[8], y0, method="SLSQP", constraints=cons,
                     bounds=[(-0.9, 0.9)] * 8 + [(0, 60)], options={"maxiter": it, "ftol": 1e-9})
        x = r.x[:8]
        if (gaps(x, front, POCKET, SW + 0.2) >= div - 1e-6
                and gaps(x, front, SW, SW) >= swt - 1e-6
                and g_split(x, front, wall) >= -1e-6):
            m = max(dvf(x[2 * i], x[2 * i + 1]) for i in range(4))
            if best is None or m < best[0] - 1e-4:
                best = (m, x.copy())
    return best


if __name__ == "__main__":
    out = {}
    for front in (4.5, 5.0, 5.3):
        b = solve(front, 0.80, 1.20, 1.5)
        k = f"front{front}"
        if b is None:
            out[k] = None; print(f"{k}: 해 없음", flush=True); continue
        m, x = b
        A = [axf(i, x[2 * i], x[2 * i + 1]) for i in range(4)]
        ds = [dvf(x[2 * i], x[2 * i + 1]) for i in range(4)]
        out[k] = dict(axes=[list(map(float, a)) for a in A], dev=ds, maxdev=m, front=front,
                      div=gaps(x, front, POCKET, SW + 0.2), sw=gaps(x, front, SW, SW),
                      split=-pocket_x(2, A[2], 1, front))
        print(f"{k}: maxdev {m:.2f}  dev {[round(v,2) for v in ds]}  "
              f"칸막이 {gaps(x,front,POCKET,SW+0.2):.3f}  스위치 {gaps(x,front,SW,SW):.3f}  "
              f"분할벽 {-pocket_x(2,A[2],1,front):.2f}", flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "cad_dump", "fix_opt2.json"), "w"))
