"""A+C 데모 렌더 — 기준 vs A+C 비교, 무게추 베이 표시."""
from __future__ import annotations
import os, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import preview_render as PR
matplotlib.rcParams["font.family"]="Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"]=False
LOCAL=os.path.dirname(HERE); STL=os.path.join(LOCAL,"export","stl")
PREVIEW=os.path.join(LOCAL,"preview")
UP,UH,GH=PR.UP,PR.UH,-171.326109

def main():
    base=PR.read_stl(os.path.join(STL,"ERGO_HOUSING_W2_SLOPE20_A.stl"))
    ac=PR.read_stl(os.path.join(STL,"ERGO_HOUSING_W2_SLOPE25_A.stl"))
    bay=None
    extra=[]
    for nm,c in (("STOCK_GIMBAL_IN_GRIP","#2e9e5b"),("ONEGRIP_IN_GRIP","#9aa7b4")):
        p=os.path.join(STL,nm+".stl")
        if os.path.exists(p): extra.append((PR.read_stl(p),c,1.0))
    allp=np.vstack([ac.reshape(-1,3)]+[e[0].reshape(-1,3) for e in extra])
    u,v,w=PR.frame(np.array([-1.0,0,0])); pu,pv=allp@u,allp@v
    def gline(ax):
        ax.plot([pu.min()-20,pu.max()+20],
                [(np.array([0,0,0])@UP), (np.array([0,0,0])@UP)], lw=0)
    # 1) A+C 단독
    for nm,tris,title,withbay in (
        ("FINAL_25A_SIDE", ac, "25deg + 후방 발 (무게추 없음)", True),
        ("FINAL_20A_SIDE", base, "20deg + 후방 발 (무게추 없음)", False)):
        fig,ax=plt.subplots(figsize=(14,7))
        PR.shade(ax,tris,u,v,w,"#5b7fa6",1.0)
        for t,c,a in extra: PR.shade(ax,t,u,v,w,c,a)

        ax.set_xlim(pu.min()-10,pu.max()+10); ax.set_ylim(pv.min()-10,pv.max()+10)
        ax.set_aspect("equal"); ax.axis("off"); ax.set_title(title,fontsize=13)
        o=os.path.join(PREVIEW,nm+".png")
        fig.savefig(o,dpi=110,bbox_inches="tight",facecolor="white"); plt.close(fig)
        print("  saved",os.path.relpath(o,LOCAL))
    # 2) 겹침 비교
    fig,ax=plt.subplots(figsize=(15,7))
    PR.shade(ax,base,u,v,w,"#a0aec0",0.55)
    PR.shade(ax,ac,u,v,w,"#2b6cb0",0.55)
    ax.set_xlim(pu.min()-10,pu.max()+10); ax.set_ylim(pv.min()-10,pv.max()+10)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("회색=20deg   파랑=25deg   (둘 다 후방 발 적용)",fontsize=13)
    o=os.path.join(PREVIEW,"FINAL_A_COMPARISON.png")
    fig.savefig(o,dpi=110,bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("  saved",os.path.relpath(o,LOCAL))
    # 3) ISO
    u2,v2,w2=PR.frame(np.array([-0.75,-0.62,0.23]))
    p2u,p2v=allp@u2,allp@v2
    fig,ax=plt.subplots(figsize=(12,9))
    PR.shade(ax,ac,u2,v2,w2,"#5b7fa6",1.0)
    for t,c,a in extra: PR.shade(ax,t,u2,v2,w2,c,a)
    ax.set_xlim(p2u.min()-10,p2u.max()+10); ax.set_ylim(p2v.min()-10,p2v.max()+10)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("25deg + 후방 발 [ISOMETRIC]",fontsize=13)
    o=os.path.join(PREVIEW,"FINAL_25A_ISOMETRIC.png")
    fig.savefig(o,dpi=110,bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("  saved",os.path.relpath(o,LOCAL))
    return 0

if __name__=="__main__":
    sys.exit(main())
