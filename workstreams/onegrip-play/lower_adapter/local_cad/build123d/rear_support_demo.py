"""A(후방 접지 연장) + C(무게추) 데모. SLOPE25 위에 얹어 형상으로 보여준다.

A: 뒤쪽에서 22~28mm 떠 있는 부분을 지면까지 내려 접지선을 뒤로 민다.
C: 경사면 중공 안 **앞쪽**에 무게추 베이. 뒤로 넘어짐은 뒤 접지선을 축으로
   돌므로 무게추를 뒤에 두면 축에 붙어 효과가 없다. 앞에 둬야 팔이 길어진다.
"""
from __future__ import annotations
import os, sys
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import parameters as P, geometry_utils as G

UP=np.array(P.FROZEN_UP_LOCAL); UH=np.array(P.FROZEN_U_HAT); GH=P.FROZEN_GROUND_WORLD_H
BASE="ERGO_HOUSING_W2_SLOPE25"

def gz(y):
    return (GH-0.3420201433256687*y)/0.9396926207859084

def main():
    bd=G.b3d()
    from build123d import Box, Location, Plane
    s0=bd.import_step(os.path.join(P.EXPORT_STEP,BASE+".step")).solids()[0]
    print(f"기준 {BASE}  vol {float(s0.volume):,.0f}")

    # ---- A: 후방 발 ----
    y0,y1 = 74.0, 94.0
    zt = -186.0                       # 기존 뒤쪽 밑면보다 살짝 위에서 시작
    zb = gz(y1)-12.0                  # 지면 아래로 넉넉히 (뒤에서 자른다)
    foot = Box(120.0, y1-y0, zt-zb).locate(
        Location((0.0, 0.5*(y0+y1), 0.5*(zt+zb))))
    big=500.0
    from build123d import BuildSketch, Locations, RectangleRounded, extrude
    def halfspace_below_ground():
        pl=Plane(origin=tuple(UP*GH), z_dir=tuple(UP))
        with BuildSketch(pl) as sk:
            with Locations((0,0)): RectangleRounded(big,big,1.0)
        return extrude(sk.sketch, amount=-big)
    foot = foot - halfspace_below_ground()
    foot = G.heal(foot, label="REAR_FOOT")
    print(f"  후방 발 vol {float(foot.volume):,.0f}")

    new = G.heal(s0 + foot, label="AC_HOUSING")
    G.export_all(new, "ERGO_HOUSING_W2_SLOPE25_AC",
                 tolerance=0.015, angular_tolerance=0.08)

    # ---- C: 무게추 베이 (시각화용 별도 body) ----
    bay = Box(60.0, 38.0, 30.0).locate(Location((0.0, -192.0, -95.0)))
    bay = bay & s0.bounding_box() if False else bay
    G.export_all(bay, "BALLAST_BAY_DEMO", tolerance=0.05, angular_tolerance=0.2)
    bv=float(bay.volume)
    print(f"  무게추 베이 {bv:,.0f} mm3  -> 강구슬(4.5 g/cm3) {bv*4.5e-3:.0f} g / "
          f"납(11.3) {bv*11.3e-3:.0f} g")

    # ---- 수치 ----
    t=G.read_stl_tris(os.path.join(P.EXPORT_STL,"ERGO_HOUSING_W2_SLOPE25_AC.stl"))
    V=t.reshape(-1,3); u=V@UH; h=V@UP-GH
    v0,v1,v2=t[:,0],t[:,1],t[:,2]
    cr=np.cross(v1,v2); s6=np.einsum("ij,ij->i",v0,cr)
    C=((v0+v1+v2)*s6[:,None]).sum(0)/(4*s6.sum())
    g=h<0.5
    print(f"\n  접지 u [{u[g].min():.1f}, {u[g].max():.1f}]  (기존 뒤끝 81.5)")
    print(f"  도심 u {float(C@UH):.2f}")
    return 0

if __name__=="__main__":
    sys.exit(main())
