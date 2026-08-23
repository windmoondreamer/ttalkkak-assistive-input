"""오프셋 3+1 버튼 row 배치 계산 (READ ONLY, 로컬 덤프만 읽음).

전제 변경:
  버튼 row 중심 != 그립 중심.
  분할면(s=0)을 I3/I4 경계에 두고 row 전체를 DOMINANT_SHELL 쪽으로 offset 한다.

호길이 좌표 s:
  s = 0   : 분할면 (그립 전면 중앙)
  s < 0   : DOMINANT_SHELL  (I1,I2,I3 / M1,M2,M3)
  s > 0   : OPPOSITE_SHELL  (I4 / M4)
  그립이 분할면 기준 미러 대칭이므로 s<0 은 s>0 의 거울상이다.

    python scripts/row_layout.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from section_arc import sample  # noqa: E402

# 단면 높이 (Joystick_side_profile 평면 자취선에서 산출한 추정치)
SECTION_H = {"Joystick_part_2": 16.44, "Joystick_part_3": -50.266}

LAYOUTS = {
    "A": dict(cap=8.0, gap=3.0, note="원본 규격 그대로"),
    "B": dict(cap=7.0, gap=2.5, note="축소안 (제작 하한)"),
    "C": dict(cap=7.5, gap=2.75, note="절충안"),
}

POCKET = 6.4  # #button_module_width 6 + 2 * #button_tolerance 0.2


def profile(name, from_end="P0"):
    """호길이 -> (x, y, 접선각). 접선각은 시작단 법선 기준 0도."""
    s, _ = sample(name)
    total = s[-1][0]
    if from_end == "P0":
        rows = [(a, x, y, ang) for (a, x, y, ang) in s]
        base = rows[0][3]
        return total, [(a, x, y, ang - base) for (a, x, y, ang) in rows]
    rows = [(total - a, x, y, ang) for (a, x, y, ang) in s][::-1]
    base = rows[0][3]
    out = []
    for a, x, y, ang in rows:
        d = ang - base
        while d > 180:
            d -= 360
        while d < -180:
            d += 360
        out.append((a, x, y, -d))
    return total, out


def angle_at(prof, s):
    """|s| 위치의 접선각. s<0 이면 미러 대칭이므로 부호 반전."""
    a = abs(s)
    total, rows = prof
    if a > total:
        return None
    r = min(rows, key=lambda r: abs(r[0] - a))
    ang = r[3]
    return (-ang if s < 0 else ang), r[1] * (1 if s >= 0 else -1), r[2]


def _normalize_sign(p, ref):
    """단면마다 로컬 프레임 방향이 달라 접선각 부호가 반대일 수 있다.
    호길이 10mm 지점의 부호를 기준 단면과 맞춘다."""
    def a10(pr):
        return min(pr[1], key=lambda r: abs(r[0] - 10.0))[3]
    if a10(p) * a10(ref) < 0:
        return (p[0], [(a, x, y, -ang) for (a, x, y, ang) in p[1]])
    return p


def blend_profile(h):
    """두 단면 사이를 높이로 선형 보간한 접선각 프로파일 (근사)."""
    p2 = profile("Joystick_part_2")
    p3 = _normalize_sign(profile("Joystick_part_3"), p2)
    h2, h3 = SECTION_H["Joystick_part_2"], SECTION_H["Joystick_part_3"]
    w = (h2 - h) / (h2 - h3)          # 0 = part_2, 1 = part_3
    w = max(0.0, min(1.0, w))
    total = p2[0] * (1 - w) + p3[0] * w
    rows = []
    n = 2000
    for k in range(n + 1):
        a = total * k / n
        a2 = min(a / total * p2[0], p2[0])
        a3 = min(a / total * p3[0], p3[0])
        r2 = min(p2[1], key=lambda r: abs(r[0] - a2))
        r3 = min(p3[1], key=lambda r: abs(r[0] - a3))
        rows.append((a,
                     r2[1] * (1 - w) + r3[1] * w,
                     r2[2] * (1 - w) + r3[2] * w,
                     r2[3] * (1 - w) + r3[3] * w))
    return (total, rows), w


def centers(cap, gap):
    """분할면을 I3/I4 경계 중앙에 둔 4버튼 중심 호길이."""
    pitch = cap + gap
    c4 = gap / 2 + cap / 2
    c3 = -c4
    return [c3 - 2 * pitch, c3 - pitch, c3, c4]


def press_kind(ang):
    a = abs(ang)
    if a < 20:
        return "fingertip front press"
    if a < 45:
        return "fingertip diagonal press"
    if a < 70:
        return "fingertip side press"
    return "distal phalanx side press"


def report_row(row_name, labels, h, layout_key, prof, wblend):
    L = LAYOUTS[layout_key]
    cap, gap = L["cap"], L["gap"]
    cs = centers(cap, gap)
    span_lo, span_hi = cs[0] - cap / 2, cs[3] + cap / 2
    rest = (span_lo + span_hi) / 2
    print(f"\n  --- {row_name} / LAYOUT {layout_key} "
          f"(cap {cap}mm, gap {gap}mm, row {4*cap+3*gap:.2f}mm) ---")
    print(f"      ROW_START      s = {span_lo:+8.3f} mm")
    print(f"      FINGER_REST    s = {rest:+8.3f} mm  (row 기하 중심)")
    print(f"      ROW_END        s = {span_hi:+8.3f} mm")
    print(f"      row center offset from grip center = {rest:+.3f} mm")
    print(f"      {'btn':<5} {'s[mm]':>9} {'x[mm]':>9} {'y[mm]':>9} "
          f"{'angle':>9} {'shell':<16} {'travel':>8}  press")
    for lab, s in zip(labels, cs):
        res = angle_at(prof, s)
        if res is None:
            print(f"      {lab:<5}   --- 단면 호길이 초과 ---")
            continue
        ang, x, y = res
        shell = "DOMINANT" if s < 0 else "OPPOSITE"
        e1 = angle_at(prof, s - cap / 2)
        e2 = angle_at(prof, s + cap / 2)
        span = abs(e2[0] - e1[0]) if e1 and e2 else float("nan")
        print(f"      {lab:<5} {s:+9.3f} {x:+9.3f} {y:+9.3f} {ang:+9.2f}째 "
              f"{shell:<16} {abs(s-rest):8.2f}  {press_kind(ang)}  (버튼면 각폭 {span:.1f}째)")
    return cs, rest


def main():
    print("=" * 100)
    print("OFFSET 3+1 ROW LAYOUT  —  분할면(s=0)을 I3/I4 경계에 배치")
    print("s<0 = DOMINANT_SHELL, s>0 = OPPOSITE_SHELL")
    print("=" * 100)
    print(f"\n스위치 포켓 최소폭 {POCKET} mm -> cap 하한 약 7.0 mm (shoulder 0.3mm/측)")

    for row_name, h, labels in (("INDEX row", 12.0, ["I1", "I2", "I3", "I4"]),
                                ("MIDDLE row", -6.0, ["M1", "M2", "M3", "M4"])):
        prof, w = blend_profile(h)
        print(f"\n{'='*100}\n{row_name}  (그립 높이 y = {h:+.1f})")
        print(f"  단면 보간: part_2 {100*(1-w):.1f}% + part_3 {100*w:.1f}%   "
              f"(half arc {prof[0]:.2f} mm)")
        for key in ("A", "B", "C"):
            report_row(row_name, labels, h, key, prof, w)


if __name__ == "__main__":
    main()
