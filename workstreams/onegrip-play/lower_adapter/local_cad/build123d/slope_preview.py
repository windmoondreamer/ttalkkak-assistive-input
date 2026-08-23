"""단일 연속 경사 4안 비교 (22/25/28/30). 동일 카메라·스케일."""
from __future__ import annotations
import os, sys, math
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import preview_render as PR
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
LOCAL = os.path.dirname(HERE); STL = os.path.join(LOCAL, "export", "stl")
PREVIEW = os.path.join(LOCAL, "preview")
UP, UH, GH = PR.UP, PR.UH, -171.326109
ANG = [20, 25]
COL = {20: "#2b6cb0", 25: "#2f855a", 28: "#c05621", 30: "#805ad5"}

def surf(t, n=4):
    p=[t.reshape(-1,3)]
    for i in range(n+1):
        for j in range(n+1-i):
            a,b=i/n,j/n; p.append(t[:,0]*a+t[:,1]*b+t[:,2]*(1-a-b))
    return np.vstack(p)

def sil(t, step=2.0):
    V=surf(t); u,h=V@UH,V@UP-GH
    out=[]
    for uu in np.arange(u.min(), u.max()+step, step):
        m=(u>=uu-step)&(u<uu+step)
        if m.sum()>=3: out.append((uu,float(h[m].max())))
    return np.array(out)

def stats(t):
    V=t.reshape(-1,3); u,h=V@UH,V@UP-GH
    n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); mg=np.linalg.norm(n,axis=1); ok=mg>1e-12
    ar,nn,ctr=mg[ok]/2,n[ok]/mg[ok,None],t[ok].mean(1); ch=ctr@UP-GH
    gm=(ch<0.5)&((nn@UP)<-0.9)
    vol=abs(float(np.einsum("ij,ij->i",t[:,0],np.cross(t[:,1],t[:,2])).sum()/6))
    # 경사면 접촉 면적: 법선이 위를 향하고 h>10 인 면
    sm=(nn@UP>0.75)&(ch>10)
    return {"L":float(V[:,1].max()-V[:,1].min()),"vol":vol,
            "ground":float(ar[gm].sum()),"slope_area":float(ar[sm].sum()),
            "tip_u":float(u.min())}

def main():
    tri,st={},{}
    for a in ANG:
        p=os.path.join(STL,f"ERGO_HOUSING_W2_SLOPE{a}.stl")
        if os.path.exists(p):
            tri[a]=PR.read_stl(p); st[a]=stats(tri[a])
    if not tri: print("STL 없음"); return 2
    extra=[]
    for nm,c in (("STOCK_GIMBAL_IN_GRIP","#2e9e5b"),("ONEGRIP_IN_GRIP","#9aa7b4")):
        p=os.path.join(STL,nm+".stl")
        if os.path.exists(p): extra.append((PR.read_stl(p),c,1.0))
    allp=np.vstack([t.reshape(-1,3) for t in tri.values()]
                   +[e[0].reshape(-1,3) for e in extra])
    u,v,w=PR.frame(np.array([-1.0,0,0])); pu,pv=allp@u,allp@v
    for a in tri:
        fig,ax=plt.subplots(figsize=(13,7))
        PR.shade(ax,tri[a],u,v,w,"#5b7fa6",1.0)
        for t,c,al in extra: PR.shade(ax,t,u,v,w,c,al)
        ax.set_xlim(pu.min()-8,pu.max()+8); ax.set_ylim(pv.min()-8,pv.max()+8)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"단일 연속 경사 {a}deg — 전장 {st[a]['L']:.1f}mm  "
                     f"경사면 {st[a]['slope_area']:,.0f}mm2", fontsize=13)
        o=os.path.join(PREVIEW,f"SLOPE_{a}_SIDE.png")
        fig.savefig(o,dpi=110,bbox_inches="tight",facecolor="white"); plt.close(fig)
        print("  saved",os.path.relpath(o,LOCAL))
    fig,axes=plt.subplots(2,1,figsize=(15,13))
    for a in tri:
        s=sil(tri[a])
        axes[0].plot(s[:,0],s[:,1],lw=2.6,color=COL[a],
                     label=f"{a}deg  L={st[a]['L']:.0f}mm  경사면 {st[a]['slope_area']:,.0f}mm2")
    axes[0].axhline(0,color="k",lw=1.2); axes[0].set_aspect("equal")
    axes[0].set_xlim(-300,120); axes[0].set_ylim(-5,150); axes[0].grid(alpha=0.3)
    axes[0].legend(fontsize=10); axes[0].set_xlabel("u [mm] (왼쪽=앞)")
    axes[0].set_ylabel("지면 위 높이 [mm]")
    axes[0].set_title("SIDE 상단 실루엣 — 단일 연속 경사 4안 (턱 없음)", fontsize=14)
    for a in tri: PR.shade(axes[1],tri[a],u,v,w,COL[a],0.45)
    axes[1].set_xlim(pu.min()-8,pu.max()+8); axes[1].set_ylim(pv.min()-8,pv.max()+8)
    axes[1].set_aspect("equal"); axes[1].axis("off")
    axes[1].set_title("겹침 — 20(파랑) 25(초록) 28(주황) 30(보라)", fontsize=13)
    o=os.path.join(PREVIEW,"SLOPE_COMPARISON.png")
    fig.savefig(o,dpi=110,bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("  saved",os.path.relpath(o,LOCAL))
    print(f"\n{'경사':>5s} {'전장L':>9s} {'부피':>12s} {'접지':>10s} {'경사면적':>10s} {'팁u':>9s}")
    for a in sorted(st):
        s=st[a]
        print(f"{a:5d} {s['L']:9.1f} {s['vol']:12,.0f} {s['ground']:10,.0f}"
              f" {s['slope_area']:10,.0f} {s['tip_u']:9.1f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
