"""치마/벽 개념 목업 — **최종 형상 아님.** 렌더 확인용 임시 STL.

사용자 스케치(빨간 선) 해석: 하우징 바깥 면을 덱에서 끊지 말고 **위로 계속 이어서**
조이스틱 거치부를 한 바퀴 감싸는 벽으로 만든다. 그러면 덱보다 3~6mm 낮은
그립 치마가 벽 뒤로 숨어 정면 틈이 사라진다.

내경 한계 79.3 x 76 : 정비 때 그립 치마(77.5 x 72.4)가 위로 통과해야 한다.
"""
from __future__ import annotations
import os, sys
import build123d as bd
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
DECK=-61.878507
CY_OUT=20.80          # 덱 상면 윤곽 중심
CY_IN=27.269160       # 그립 축
STL=os.path.join(os.path.dirname(HERE),"export","stl")

def rr(w,h,r,z,cy):
    return bd.Plane(origin=(0,cy,z))*bd.RectangleRounded(w,h,r)

def tube(sections,cy):
    sk=[rr(w,h,r,z,cy) for (w,h,r,z) in sections]
    out=None
    for a,b in zip(sk[:-1],sk[1:]):
        s=bd.loft([a,b]); out=s if out is None else out.fuse(s)
    return out

def build(name, outer, inner, hcut=None):
    O=tube(outer,CY_OUT); I=tube(inner,CY_IN)
    c=O.cut(I)
    sol=c.solids(); c=max(sol,key=lambda s:s.volume)
    bd.export_stl(c, os.path.join(STL,name+".stl"), tolerance=0.05, angular_tolerance=0.3)
    print("  %-18s solid %d  부피 %9.1f mm3  높이 %.1f mm"
          %(name,len(sol),c.volume,outer[-1][3]-DECK))
    return c

# 바깥: 덱에서 113 x 119.4 로 시작해 위로 오므린다 (빨간 선)
# 안쪽: 79.3 x 76 고정 (그립 통과)
IN=[(79.3,76.0,14,DECK-3.0),(79.3,76.0,14,DECK+20.0)]

W10=[(113.0,119.4,16,DECK-0.5),(105.0,111.0,15,DECK+5.0),(97.0,103.0,14,DECK+10.0)]
W14=[(113.0,119.4,16,DECK-0.5),(106.0,112.0,15,DECK+6.0),
     (99.0,105.0,14,DECK+11.0),(93.0,99.0,13,DECK+14.0)]

def main():
    print("벽 목업 (임시, 최종 형상 아님)")
    build("MOCK_WALL_H10", W10, IN)
    build("MOCK_WALL_H14", W14, IN)
    return 0

if __name__=="__main__":
    sys.exit(main())
