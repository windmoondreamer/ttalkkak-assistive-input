"""25deg + wrap skirt 최종 프리뷰 7종. 동일 카메라/스케일."""
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
UP,UH=PR.UP,PR.UH
VIEWS={"SIDE":np.array([-1.0,0,0]), "ISOMETRIC":np.array([-0.75,-0.62,0.23]),
       "TOP":-UP, "FRONT":-UH, "REAR":UH, "BOTTOM":UP}

def main():
    house=PR.read_stl(os.path.join(STL,"ERGO_HOUSING_25_WRAP_W134.stl"))
    print(f"FINAL 삼각형 {len(house):,}")
    sets=[(house,"#5b7fa6",1.0)]
    for nm,c in (("BOTTOM_CARRIER_FINAL","#2b6cb0"),
                 ("STOCK_GIMBAL_IN_GRIP","#2e9e5b"),
                 ("ONEGRIP_IN_GRIP","#9aa7b4")):
        p=os.path.join(STL,nm+".stl")
        if os.path.exists(p): sets.append((PR.read_stl(p),c,1.0)); print("  +",nm)
    allp=np.vstack([s[0].reshape(-1,3) for s in sets])
    def draw(name,wd,title,section=None):
        u,v,w=PR.frame(wd)
        fig,ax=plt.subplots(figsize=(11,10))
        for tris,col,al in sets:
            t=tris
            if section is not None:
                ax_i,val,keep_neg=section
                # 삼각형 **중심**으로 자르면 절단면을 걸친 삼각형이 뾰족하게
                # 튀어나온다. 세 정점이 모두 한쪽인 것만 남긴다.
                vx=t[:,:,ax_i]
                t=t[(vx<val).all(1)] if keep_neg else t[(vx>val).all(1)]
            if len(t): PR.shade(ax,t,u,v,w,col,al)
        pu,pv=allp@u,allp@v
        ax.set_xlim(pu.min()-8,pu.max()+8); ax.set_ylim(pv.min()-8,pv.max()+8)
        ax.set_aspect("equal"); ax.axis("off"); ax.set_title(title,fontsize=13)
        p=os.path.join(PREVIEW,name+".png")
        fig.savefig(p,dpi=115,bbox_inches="tight",facecolor="white"); plt.close(fig)
        print("  saved",os.path.relpath(p,LOCAL))
    for k,wd in VIEWS.items():
        draw(f"W134_{k}",wd,f"OneGrip Play — 25deg + WRAP + 팔받침 133.6mm  [{k}]")
    draw("W134_CUTAWAY",np.array([-0.75,-0.62,0.23]),
         "CUTAWAY (X<0 제거) — 스톡짐벌(초록)/캐리어(진파랑)/코어+25deg 팔받침+스커트(파랑)",
         section=(0,0.0,False))
    return 0

if __name__=="__main__":
    sys.exit(main())
