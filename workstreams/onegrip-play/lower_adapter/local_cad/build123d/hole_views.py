"""정면 '구멍' 실체 확인 — 전 부품 **전역 깊이 정렬** 렌더.

기존 w134_preview 는 부품별로 그려서 나중 부품이 하우징 위에 덮어 그려졌다
(정면에서 짐벌이 비쳐 보이던 원인). 여기서는 삼각형을 전부 합친 뒤 한 번만
정렬한다.
"""
from __future__ import annotations
import os, sys
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import preview_render as PR
matplotlib.rcParams["font.family"]="Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"]=False
LOCAL=os.path.dirname(HERE); STL=os.path.join(LOCAL,"export","stl")
PREVIEW=os.path.join(LOCAL,"preview")

PARTS=[("ERGO_HOUSING_25_WRAP_W134","#5b7fa6"),
       ("BOTTOM_CARRIER_FINAL","#2b6cb0"),
       ("STOCK_GIMBAL_IN_GRIP","#2e9e5b"),
       ("ONEGRIP_IN_GRIP","#9aa7b4")]

def draw(name, wdir, title, parts=None):
    u,v,w = PR.frame(np.array(wdir,dtype=float))
    T=[]; Cc=[]
    for nm,col in (parts or PARTS):
        p=os.path.join(STL,nm+".stl")
        if not os.path.exists(p): continue
        t=PR.read_stl(p)
        T.append(t); Cc.append(np.repeat([matplotlib.colors.to_rgb(col)],len(t),axis=0))
    T=np.vstack(T); Cc=np.vstack(Cc)
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0])
    nn=n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
    keep=(nn@w)<0
    T,Cc,nn=T[keep],Cc[keep],nn[keep]
    o=np.argsort(-(T.mean(1)@w))                 # 전역 정렬 (핵심)
    T,Cc,nn=T[o],Cc[o],nn[o]
    L=np.array([0.4,-0.6,0.7]); L/=np.linalg.norm(L)
    sh=np.clip(0.35+0.65*np.abs(nn@L),0,1)
    cols=np.clip(Cc*sh[:,None],0,1)
    poly=np.stack([T.reshape(-1,3)@u, T.reshape(-1,3)@v],1).reshape(-1,3,2)
    fig,ax=plt.subplots(figsize=(10,10))
    ax.add_collection(PolyCollection(poly,facecolors=cols,edgecolors="none",linewidths=0))
    pu,pv=poly[:,:,0].ravel(),poly[:,:,1].ravel()
    ax.set_xlim(pu.min()-8,pu.max()+8); ax.set_ylim(pv.min()-8,pv.max()+8)
    ax.set_aspect("equal"); ax.axis("off"); ax.set_title(title,fontsize=13)
    p=os.path.join(PREVIEW,name+".png")
    fig.savefig(p,dpi=115,bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("  saved",os.path.relpath(p,LOCAL))

def main():
    UP,UH=PR.UP,PR.UH
    # 팔받침은 -u 쪽. 그쪽에 카메라를 두고 뒤(+u)를 보는 것이 "앞에서 뒤쪽" 이다.
    draw("VIEW_ARMSIDE",   UH, "팔받침 쪽에서 뒤를 봄 (앞 -> 뒤)")
    draw("VIEW_ARMSIDE_U15", UH*0.966+UP*0.259, "팔받침 쪽 부각 15도")
    draw("VIEW_ARMSIDE_U30", UH*0.866+UP*0.500, "팔받침 쪽 부각 30도")
    draw("VIEW_BACKSIDE", -UH, "반대쪽에서 봄 (뒤 -> 앞)  ※ 앞서 보여준 것")
    return 0

if __name__=="__main__":
    sys.exit(main())
