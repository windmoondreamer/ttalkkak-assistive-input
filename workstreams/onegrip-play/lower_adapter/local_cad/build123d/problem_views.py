"""내가 문제라고 보는 곳 표시 — 덱 개구부와 그립 치마 사이 틈.

전 부품 **전역 깊이 정렬** 렌더 (부품별로 그리면 뒤 부품이 덧칠된다).
카메라는 팔받침 쪽(-Y). 화면축: x = -X, y = p·UP.
"""
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
DECK=-61.878507; CY=27.269160
PARTS=[("ERGO_HOUSING_25_WRAP_FINAL_V3","#5b7fa6"),("BOTTOM_CARRIER_FINAL","#2b6cb0"),
       ("STOCK_GIMBAL_IN_GRIP","#2e9e5b"),("ONEGRIP_IN_GRIP","#9aa7b4")]

def scene(wd):
    u,v,w=PR.frame(np.array(wd,float))
    T=[];C=[]
    for nm,col in PARTS:
        p=os.path.join(STL,nm+".stl")
        if not os.path.exists(p): continue
        t=PR.read_stl(p); T.append(t); C.append(np.repeat([matplotlib.colors.to_rgb(col)],len(t),axis=0))
    T=np.vstack(T); C=np.vstack(C)
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); nn=n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
    k=(nn@w)<0; T,C,nn=T[k],C[k],nn[k]
    o=np.argsort(-(T.mean(1)@w)); T,C,nn=T[o],C[o],nn[o]
    L=np.array([0.4,-0.6,0.7]); L/=np.linalg.norm(L)
    sh=np.clip(0.35+0.65*np.abs(nn@L),0,1)
    poly=np.stack([T.reshape(-1,3)@u,T.reshape(-1,3)@v],1).reshape(-1,3,2)
    return poly,np.clip(C*sh[:,None],0,1)

def main():
    poly,cols=scene(UH)
    sx=lambda x:-x
    sy=lambda p:float(np.array(p)@UP)
    yc=sy((0,CY,DECK))
    for tag,(hw,hh) in (("WIDE",(78,62)),("ZOOM",(52,34))):
        fig,ax=plt.subplots(figsize=(10.5,8))
        ax.add_collection(PolyCollection(poly,facecolors=cols,edgecolors="none",linewidths=0))
        ax.set_xlim(-hw,hw); ax.set_ylim(yc-hh*0.45,yc+hh*0.85)
        ax.set_aspect("equal"); ax.axis("off")
        # 틈 표시: 개구부 가장자리(46.4) <-> 치마 가장자리(38.76)
        ygap=yc-2.0
        for s in (+1,-1):
            ax.annotate("",xy=(sx(s*46.4),ygap),xytext=(sx(s*38.76),ygap),
                        arrowprops=dict(arrowstyle="<->",color="#d62828",lw=2.2))
        ax.text(0,ygap-6.5,"이 틈이 사방 7.7~8.7 mm  ← 내가 문제라고 보는 곳",
                ha="center",fontsize=12,color="#d62828",weight="bold")
        ax.plot([sx(46.4),sx(46.4)],[ygap-1.5,ygap+9],color="#d62828",lw=1.0,ls=":")
        ax.plot([sx(-46.4),sx(-46.4)],[ygap-1.5,ygap+9],color="#d62828",lw=1.0,ls=":")
        ax.plot([sx(38.76),sx(38.76)],[ygap-1.5,ygap+9],color="#f77f00",lw=1.0,ls=":")
        ax.plot([sx(-38.76),sx(-38.76)],[ygap-1.5,ygap+9],color="#f77f00",lw=1.0,ls=":")
        ax.text(sx(46.4),ygap+10,"덱 구멍 가장자리\n92.9",ha="center",fontsize=9,color="#d62828")
        ax.text(sx(-38.76),ygap+10,"그립 치마\n77.5",ha="center",fontsize=9,color="#b35c00")
        ax.set_title("팔받침 쪽에서 본 그립 밑동  [%s]"%tag,fontsize=13)
        p=os.path.join(PREVIEW,"PROBLEM_%s.png"%tag)
        fig.savefig(p,dpi=120,bbox_inches="tight",facecolor="white"); plt.close(fig)
        print("  saved",os.path.relpath(p,LOCAL))
    # 위에서 본 3안 비교
    fig,ax=plt.subplots(figsize=(8.6,8.6))
    from matplotlib.patches import Rectangle,FancyBboxPatch
    def rect(w,h,c,lab,ls="-",lw=2.4):
        ax.add_patch(Rectangle((-w/2,CY-h/2),w,h,fill=False,ec=c,lw=lw,ls=ls,label=lab))
    rect(77.52,72.44,"#f77f00","그립 치마 77.5 x 72.4 (통과해야 함)","-",3.0)
    rect(92.90,89.80,"#d62828","그대로  92.9 x 89.8   틈 7.7mm","--")
    rect(84.0,79.0,"#2a9d8f","중간(권장) 84 x 79   틈 3.2mm")
    rect(79.12,74.04,"#264653","최대  79.1 x 74.0   틈 0.8mm")
    ax.set_xlim(-60,60); ax.set_ylim(CY-60,CY+60); ax.set_aspect("equal"); ax.grid(alpha=.25)
    ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")
    ax.set_title("위에서 본 3안 — 구멍을 줄일수록 틈도 정비 여유도 같이 줄어든다",fontsize=12)
    ax.legend(loc="upper left",fontsize=9,framealpha=.95)
    p=os.path.join(PREVIEW,"PROBLEM_OPTIONS.png")
    fig.savefig(p,dpi=120,bbox_inches="tight",facecolor="white"); plt.close(fig)
    print("  saved",os.path.relpath(p,LOCAL))
    return 0

if __name__=="__main__":
    sys.exit(main())
