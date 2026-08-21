"""그립 단면(로프트 section)의 호길이 / 접선각을 계산한다 (READ ONLY, 로컬 덤프만 읽음).

Onshape의 BTCurveGeometryInterpolatedSpline 을 clamped cubic spline 으로 재구성해서
- 분할면(x=0)에서 시작하는 호길이
- 각 위치의 표면 법선 방향
를 구한다. 버튼 열이 곡면을 감쌀 수 있는지 판정하는 데 사용한다.

    python scripts/section_arc.py                 # 4개 단면 요약
    python scripts/section_arc.py Joystick_part_2 # 특정 단면 상세 + 버튼열 배치 검토
"""
import json
import math
import os
import sys

DUMP = os.path.join(os.path.dirname(__file__), "..", "cad_dump")
M2MM = 1000.0


def clamped_cubic(ts, vs, d0, d1):
    """clamped cubic spline 계수. 각 구간의 (a,b,c,d) 반환."""
    n = len(ts) - 1
    h = [ts[i + 1] - ts[i] for i in range(n)]
    # 2차 도함수 M 을 푸는 삼중대각 시스템
    A = [[0.0] * (n + 1) for _ in range(n + 1)]
    r = [0.0] * (n + 1)
    A[0][0] = 2 * h[0]
    A[0][1] = h[0]
    r[0] = 6 * ((vs[1] - vs[0]) / h[0] - d0)
    A[n][n - 1] = h[n - 1]
    A[n][n] = 2 * h[n - 1]
    r[n] = 6 * (d1 - (vs[n] - vs[n - 1]) / h[n - 1])
    for i in range(1, n):
        A[i][i - 1] = h[i - 1]
        A[i][i] = 2 * (h[i - 1] + h[i])
        A[i][i + 1] = h[i]
        r[i] = 6 * ((vs[i + 1] - vs[i]) / h[i] - (vs[i] - vs[i - 1]) / h[i - 1])
    # 가우스 소거
    for i in range(1, n + 1):
        f = A[i][i - 1] / A[i - 1][i - 1]
        for k in range(i - 1, min(i + 2, n + 1)):
            A[i][k] -= f * A[i - 1][k]
        r[i] -= f * r[i - 1]
    Mv = [0.0] * (n + 1)
    Mv[n] = r[n] / A[n][n]
    for i in range(n - 1, -1, -1):
        s = r[i] - (A[i][i + 1] * Mv[i + 1] if i + 1 <= n else 0.0)
        Mv[i] = s / A[i][i]
    return Mv, h


def eval_spline(ts, vs, Mv, h, t):
    n = len(ts) - 1
    i = min(max(0, sum(1 for k in range(n) if ts[k + 1] <= t) ), n - 1)
    dt = t - ts[i]
    A = (ts[i + 1] - t) / h[i]
    B = dt / h[i]
    val = (A * vs[i] + B * vs[i + 1]
           + ((A ** 3 - A) * Mv[i] + (B ** 3 - B) * Mv[i + 1]) * (h[i] ** 2) / 6.0)
    der = ((vs[i + 1] - vs[i]) / h[i]
           + (-(3 * A ** 2 - 1) * Mv[i] + (3 * B ** 2 - 1) * Mv[i + 1]) * h[i] / 6.0)
    return val, der


def load_section(name):
    with open(os.path.join(DUMP, "features_Joystick.json"), encoding="utf-8") as f:
        j = json.load(f)
    ft = next(f for f in j["features"] if f["name"] == name and f["featureType"] == "newSketch")
    for e in ft["entities"]:
        g = e.get("geometry", {}) or {}
        ip = g.get("interpolationPoints")
        if ip:
            pts = [(ip[i] * M2MM, ip[i + 1] * M2MM) for i in range(0, len(ip), 2)]
            d0 = (g.get("startDerivativeX", 0.0) * M2MM, g.get("startDerivativeY", 0.0) * M2MM)
            d1 = (g.get("endDerivativeX", 0.0) * M2MM, g.get("endDerivativeY", 0.0) * M2MM)
            return pts, d0, d1
    raise SystemExit(f"{name}: interpolated spline 없음")


def sample(name, n=2000):
    pts, d0, d1 = load_section(name)
    # 코드 길이 파라미터화
    ts = [0.0]
    for i in range(len(pts) - 1):
        ts.append(ts[-1] + math.dist(pts[i], pts[i + 1]))
    total_t = ts[-1]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    # 끝점 도함수를 파라미터 스케일에 맞춤
    sx0, sy0 = d0
    sx1, sy1 = d1
    nrm0 = math.hypot(sx0, sy0) or 1.0
    nrm1 = math.hypot(sx1, sy1) or 1.0
    Mx, hx = clamped_cubic(ts, xs, sx0 / nrm0, sx1 / nrm1)
    My, hy = clamped_cubic(ts, ys, sy0 / nrm0, sy1 / nrm1)
    out = []
    arc = 0.0
    prev = None
    for k in range(n + 1):
        t = total_t * k / n
        x, dx = eval_spline(ts, xs, Mx, hx, t)
        y, dy = eval_spline(ts, ys, My, hy, t)
        if prev is not None:
            arc += math.dist((x, y), prev)
        prev = (x, y)
        out.append((arc, x, y, math.degrees(math.atan2(dy, dx))))
    return out, pts


def at_arc(samples, s):
    best = min(samples, key=lambda r: abs(r[0] - s))
    return best


def main():
    names = sys.argv[1:] or ["Joystick_part_1", "Joystick_part_2",
                             "Joystick_part_3", "Joystick_part_4"]
    for name in names:
        s, pts = sample(name)
        total = s[-1][0]
        print(f"\n=== {name} ===")
        print(f"  보간점 {len(pts)}개, x=0 -> x=0 (분할면에서 분할면까지 한쪽 면)")
        print(f"  half arc length = {total:8.3f} mm   (full = {2*total:8.3f} mm)")
        print(f"  half-width max  = {max(abs(r[1]) for r in s):8.3f} mm")
        print(f"  depth           = {min(r[2] for r in s):8.3f} .. {max(r[2] for r in s):8.3f} mm")
        print(f"\n  분할면(P0)에서의 호길이별 위치와 접선각:")
        print(f"    {'arc[mm]':>9} {'x[mm]':>9} {'y[mm]':>9} {'tangent[deg]':>13} {'Δangle':>9}")
        base = None
        for target in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
            if target > total:
                break
            a, x, y, ang = at_arc(s, target)
            if base is None:
                base = ang
            print(f"    {a:9.2f} {x:9.3f} {y:9.3f} {ang:13.2f} {ang-base:9.2f}")


if __name__ == "__main__":
    main()
