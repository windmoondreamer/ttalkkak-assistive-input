"""M15 검증 — 틸트 한계 / 최소 살두께 / 절삭 위치."""
from __future__ import annotations
import os, sys, math
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import parameters as P, geometry_utils as G
import build123d as bd
from OCP.BRepTools import BRepTools
LOCAL=os.path.dirname(HERE); ADAPTER=os.path.dirname(LOCAL)
DECK=-61.878507; PIV=np.array([0.0,27.269160,DECK-52.9823])
def tris(name, tol=0.06):
    p=name if os.path.isabs(name) else os.path.join(P.EXPORT_STEP,name+".step")
    s=bd.import_step(p); sol=s.solids(); sh=sol[0] if len(sol)==1 else s
    BRepTools.Clean_s(sh.wrapped)
    f=os.path.join(P.EXPORT_STL,"_m.stl"); bd.export_stl(sh,f,tolerance=tol,angular_tolerance=0.35)
    T=G.read_stl_tris(f); os.remove(f); return T
def main():
    A=tris("ERGO_HOUSING_25_WRAP_W134_BLEND")   # V3 (절삭 전)
    B=tris("ERGO_HOUSING_25_WRAP_W134_M15")     # 절삭 후
    print("V3 삼각형 %d / M15 삼각형 %d"%(len(A),len(B)))
    d=np.load(os.path.join(ADAPTER,"cad_dump","motion_configs_gripfix.npz"))
    GR=("Joystick_1","Joystick_2","HW504_B","Small_joystick_attachment","Backplate","Magnet","Pitch")
    N=np.vstack([d[k] for k in d.keys() if k.split("|")[0]=="neutral"
                 and any(k.split("|")[1].startswith(g) for g in GR)])
    m=(N[:,2]>DECK-20)&(N[:,2]<DECK+30); S=N[m]
    rng=np.random.default_rng(0); S=S[rng.choice(len(S),min(9000,len(S)),replace=False)]
    def rot(ax,deg):
        t=math.radians(deg); c,s=math.cos(t),math.sin(t)
        R=np.array([[1,0,0],[0,c,-s],[0,s,c]]) if ax=="X" else np.array([[c,0,s],[0,1,0],[-s,0,c]])
        return (S-PIV)@R.T+PIV
    print("\n틸트 한계 (충돌 점 수)   V3 / M15")
    print("  축 방향    10도        12         14         15         16         18")
    for ax in ("X","Y"):
        for sg in (+1,-1):
            row=[]
            for deg in (10,12,14,15,16,18):
                p=rot(ax,sg*deg)
                row.append("%4d/%4d"%(int(G.mesh_inside(A,p).sum()),int(G.mesh_inside(B,p).sum())))
            print("  %s %+d   %s"%(ax,sg,"  ".join(row)))
    # 콘 전방향 15도
    print("\n원뿔 전방향 15도 (24방향)  V3 충돌 / M15 충돌")
    def R2(ax,deg):
        t=math.radians(deg); c,s=math.cos(t),math.sin(t)
        return np.array([[1,0,0],[0,c,-s],[0,s,c]]) if ax=="X" else np.array([[c,0,s],[0,1,0],[-s,0,c]])
    ta=tb=0
    for i in range(24):
        ph=2*math.pi*i/24
        M=R2("X",15*math.cos(ph))@R2("Y",15*math.sin(ph))
        p=(S-PIV)@M.T+PIV
        ta+=int(G.mesh_inside(A,p).sum()); tb+=int(G.mesh_inside(B,p).sum())
    print("   합계  %d / %d"%(ta,tb))
    return 0
if __name__=="__main__":
    sys.exit(main())
