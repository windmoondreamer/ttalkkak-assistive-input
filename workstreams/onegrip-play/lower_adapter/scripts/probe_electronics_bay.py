"""Base 꼬리부(전장 베이) 단면 — Arduino/USB 와 Base 재료의 실제 관계."""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import stock_geom as sg                                  # noqa: E402
from probe_c1c2_holes import z_spans                     # noqa: E402


def main():
    N = sg.load(neutral=True)
    B = N["Base <1>"]
    elec = {k: N[k] for k in N if k.startswith(("micro", "atmega", "MICRO_"))}
    E = np.concatenate([v.reshape(-1, 3) for v in elec.values()])

    print("Base 꼬리부 Z 단면 (X=0 라인)")
    for y in np.arange(-66.0, -18.0, 3.0):
        sp = z_spans(B, [(0.0, y)])[0]
        se = [s for k, v in elec.items() for s in z_spans(v, [(0.0, y)])[0]]
        print(f"  Y={y:7.1f}  Base " + (", ".join(f"[{a:9.3f},{b:9.3f}]" for a, b in sp)
                                        or "없음")
              + "   전장 " + (", ".join(f"[{a:9.3f},{b:9.3f}]" for a, b in sorted(se))
                            or "없음"))

    print("\n꼬리부 폭 (Y 별 X 범위)")
    for y in np.arange(-66.0, -18.0, 3.0):
        xs = [x for x in np.arange(-30, 30.01, 0.5) if z_spans(B, [(x, y)])[0]]
        if xs:
            print(f"  Y={y:7.1f}  X [{min(xs):7.2f}, {max(xs):7.2f}]  폭 {max(xs)-min(xs)+0.5:6.2f}")
        else:
            print(f"  Y={y:7.1f}  (재료 없음)")

    # Base 와 전장의 실제 간섭/간격
    print("\nBase vs 전장 관계")
    Vb = B.reshape(-1, 3)
    tail = Vb[(Vb[:, 1] < -20)]
    print(f"  꼬리부 Base 정점 Z [{tail[:,2].min():.3f}, {tail[:,2].max():.3f}]")
    print(f"  전장 Z            [{E[:,2].min():.3f}, {E[:,2].max():.3f}]")

    # 전장이 Base 재료 안에 들어와 있는가
    inside = 0
    samp = E[:: max(1, len(E) // 3000)]
    for p in samp:
        sp = z_spans(B, [(p[0], p[1])])[0]
        if any(a <= p[2] <= b for a, b in sp):
            inside += 1
    print(f"  전장 표본 {len(samp)}점 중 Base 재료 내부 {inside}점 "
          f"({100*inside/len(samp):.1f}%)")


if __name__ == "__main__":
    main()
