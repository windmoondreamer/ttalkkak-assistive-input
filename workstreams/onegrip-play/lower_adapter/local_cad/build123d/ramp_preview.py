"""램프 안 3D 프리뷰 + 실루엣 비교 (동일 카메라/스케일)."""
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
CASES = [("현재(227.6)", "ERGO_HOUSING_W2_PRINT_FINAL", "#a0aec0"),
         ("40deg(329.4)", "ERGO_HOUSING_W2_RAMP40", "#2f855a"),
         ("30deg(375.6)", "ERGO_HOUSING_W2_RAMP30", "#805ad5")]

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

def main():
    tri={}
    for lab,nm,col in CASES:
        p=os.path.join(STL, nm+".stl")
        if os.path.exists(p): tri[nm]=PR.read_stl(p)
    extra=[]
    for nm,col in (("STOCK_GIMBAL_IN_GRIP","#2e9e5b"),("ONEGRIP_IN_GRIP","#9aa7b4")):
        p=os.path.join(STL,nm+".stl")
        if os.path.exists(p): extra.append((PR.read_stl(p),col,1.0))
    allp=np.vstack([t.reshape(-1,3) for t in tri.values()]
                   +[e[0].reshape(-1,3) for e in extra])
    for view,wd in (("SIDE",np.array([-1.0,0,0])),
                    ("ISOMETRIC",np.array([-0.75,-0.62,0.23]))):
        u,v,w=PR.frame(wd); pu,pv=allp@u,allp@v
        for lab,nm,col in CASES[1:]:
            if nm not in tri: continue
            fig,ax=plt.subplots(figsize=(12,8))
            PR.shade(ax,tri[nm],u,v,w,"#5b7fa6",1.0)
            for t,c,a in extra: PR.shade(ax,t,u,v,w,c,a)
            ax.set_xlim(pu.min()-8,pu.max()+8); ax.set_ylim(pv.min()-8,pv.max()+8)
            ax.set_aspect("equal"); ax.axis("off")
            ax.set_title(f"OneGrip Play — {lab}  [{view}]", fontsize=13)
            o=os.path.join(PREVIEW,f"RAMP3D_{nm.split('_')[-1]}_{view}.png")
            fig.savefig(o,dpi=110,bbox_inches="tight",facecolor="white"); plt.close(fig)
            print("  saved", os.path.relpath(o,LOCAL))
    fig,axes=plt.subplots(1,2,figsize=(20,7))
    for lab,nm,col in CASES:
        if nm not in tri: continue
        s=sil(tri[nm]); axes[0].plot(s[:,0],s[:,1],lw=2.6,color=col,label=lab)
    axes[0].axhline(0,color="k",lw=1.2); axes[0].set_aspect("equal")
    axes[0].set_xlim(-250,110); axes[0].set_ylim(-5,150); axes[0].grid(alpha=0.3)
    axes[0].legend(fontsize=10); axes[0].set_xlabel("u [mm] (왼쪽=앞)")
    axes[0].set_ylabel("지면 위 높이 [mm]")
    axes[0].set_title("SIDE 상단 실루엣 — 실측 3D", fontsize=13)
    u,v,w=PR.frame(np.array([-1.0,0,0])); pu,pv=allp@u,allp@v
    for lab,nm,col in CASES[1:]:
        if nm in tri: PR.shade(axes[1],tri[nm],u,v,w,col,0.6)
    axes[1].set_xlim(pu.min()-8,pu.max()+8); axes[1].set_ylim(pv.min()-8,pv.max()+8)
    axes[1].set_aspect("equal"); axes[1].axis("off")
    axes[1].set_title("40deg(초록) vs 30deg(보라) 겹침", fontsize=13)
    o=os.path.join(PREVIEW,"RAMP3D_COMPARISON.png")
    fig.savefig(o,dpi=110,bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("  saved", os.path.relpath(o,LOCAL))
    return 0

if __name__ == "__main__":
    sys.exit(main())
