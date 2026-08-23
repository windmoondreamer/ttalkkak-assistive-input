"""벽 목업 렌더 — 전역 깊이 정렬, 팔받침 쪽(앞)에서 본 비교."""
from __future__ import annotations
import os, sys
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import preview_render as PR
matplotlib.rcParams["font.family"]="Malgun Gothic"; matplotlib.rcParams["axes.unicode_minus"]=False
LOCAL=os.path.dirname(HERE); STL=os.path.join(LOCAL,"export","stl"); PREVIEW=os.path.join(LOCAL,"preview")
UP,UH=PR.UP,PR.UH
BASE=[("ERGO_HOUSING_25_WRAP_W134","#5b7fa6"),("BOTTOM_CARRIER_FINAL","#2b6cb0"),
      ("STOCK_GIMBAL_IN_GRIP","#2e9e5b"),("ONEGRIP_IN_GRIP","#9aa7b4")]

def draw(name,wdir,title,parts):
    u,v,w=PR.frame(np.array(wdir,dtype=float))
    T=[];Cc=[]
    for nm,col in parts:
        p=os.path.join(STL,nm+".stl")
        if not os.path.exists(p): print("   없음",nm); continue
        t=PR.read_stl(p); T.append(t); Cc.append(np.repeat([matplotlib.colors.to_rgb(col)],len(t),axis=0))
    T=np.vstack(T); Cc=np.vstack(Cc)
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); nn=n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
    k=(nn@w)<0; T,Cc,nn=T[k],Cc[k],nn[k]
    o=np.argsort(-(T.mean(1)@w)); T,Cc,nn=T[o],Cc[o],nn[o]
    L=np.array([0.4,-0.6,0.7]); L/=np.linalg.norm(L)
    sh=np.clip(0.35+0.65*np.abs(nn@L),0,1)
    poly=np.stack([T.reshape(-1,3)@u,T.reshape(-1,3)@v],1).reshape(-1,3,2)
    fig,ax=plt.subplots(figsize=(9,9))
    ax.add_collection(PolyCollection(poly,facecolors=np.clip(Cc*sh[:,None],0,1),edgecolors="none",linewidths=0))
    pu,pv=poly[:,:,0].ravel(),poly[:,:,1].ravel()
    ax.set_xlim(pu.min()-8,pu.max()+8); ax.set_ylim(pv.min()-8,pv.max()+8)
    ax.set_aspect("equal"); ax.axis("off"); ax.set_title(title,fontsize=12)
    p=os.path.join(PREVIEW,name+".png")
    fig.savefig(p,dpi=115,bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("  saved",os.path.relpath(p,LOCAL))

def main():
    # 카메라는 -w 쪽. 팔받침(-Y) + 위(UP) 에서 보려면 w = UH*a - UP*b - X*c
    ISO=UH*0.70-UP*0.45-np.array([0.55,0.0,0.0])
    for tag,extra,lab in (("NONE",None,"현재 — 치마 밑 틈이 보인다"),
                          ("H10",("MOCK_WALL_H10","#e0a34a"),"벽 10mm — 바깥면을 위로 연장"),
                          ("H14",("MOCK_WALL_H14","#e0a34a"),"벽 14mm — 바깥면을 위로 연장")):
        parts=BASE+([extra] if extra else [])
        draw("WALL_%s_FRONT"%tag, UH, lab+"  [앞에서 뒤로]", parts)
        draw("WALL_%s_ISO"%tag, ISO, lab+"  [ISO]", parts)
    return 0

if __name__=="__main__":
    sys.exit(main())
