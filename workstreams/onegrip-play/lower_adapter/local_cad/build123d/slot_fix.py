"""정면에서 보이는 '틈'의 정체와 해소안 — 덱 립 단면 비교. 측정/작도만."""
from __future__ import annotations
import os, sys, math
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
matplotlib.rcParams["font.family"]="Malgun Gothic"; matplotlib.rcParams["axes.unicode_minus"]=False
LOCAL=os.path.dirname(HERE); PREVIEW=os.path.join(LOCAL,"preview")
DECK=0.0
# X 방향 반폭 (mm), dz 는 덱 기준
sweep={0:74.01/2,-1:76.24/2,-2:76.76/2,-3:77.51/2,-4:79.64/2,-5:84.73/2,-6:87.79/2,-7:90.68/2,-8:92.45/2}
FLANGE=77.52/2; OPEN_NOW=92.90/2
LIP_TOP=max(FLANGE+0.8, sweep[0]+1.5)
fig,axes=plt.subplots(1,2,figsize=(13.5,6.4),sharey=True)
for ax,mode in zip(axes,("now","fix")):
    zs=sorted(sweep.keys(),reverse=True)
    if mode=="now":
        wall=[(z,OPEN_NOW) for z in zs]; title="현재 — 개구부 92.9 곧은 벽"
    else:
        wall=[(z,max(LIP_TOP, sweep[z]+1.5)) for z in zs]; title="수정안 — 립 상단 %.1f, 아래로 벌어짐"%(LIP_TOP*2)
    W=np.array(wall)
    for s in (+1,-1):
        ax.fill_betweenx(W[:,0], s*W[:,1], s*(W[:,1]+14), color="#5b7fa6", alpha=.85, lw=0)
        ax.plot(s*W[:,1],W[:,0],color="#2c3e50",lw=1.6)
    ax.add_patch(plt.Rectangle((-FLANGE,-6.0),2*FLANGE,3.0,fc="#e67e22",alpha=.9,ec="#b9651a"))
    ax.text(0,-4.6,"그립 치마 77.5",ha="center",va="center",fontsize=9,color="white",weight="bold")
    ax.add_patch(plt.Rectangle((-50.71/2,-3.0),50.71,9.0,fc="#95a5a6",alpha=.8,ec="#7f8c8d"))
    ax.text(0,2.5,"그립",ha="center",fontsize=10,color="white",weight="bold")
    sw=np.array([[z,sweep[z]] for z in zs])
    for s in (+1,-1): ax.plot(s*sw[:,1],sw[:,0],":",color="#c0392b",lw=1.3)
    g=(W[W[:,0]==-3][0][1] if mode=="fix" else OPEN_NOW)-FLANGE
    top=(LIP_TOP if mode=="fix" else OPEN_NOW)-FLANGE
    ax.annotate("",xy=(FLANGE,-4.5),xytext=((LIP_TOP if mode=="fix" else OPEN_NOW),-4.5),
                arrowprops=dict(arrowstyle="<->",color="#8e44ad",lw=1.8))
    ax.text((FLANGE+(LIP_TOP if mode=="fix" else OPEN_NOW))/2,-9.0,
            "보이는 틈\n%.2f mm"%top,ha="center",fontsize=11,color="#8e44ad",weight="bold")
    ax.axhline(0,color="#2c3e50",lw=1.0,ls="-")
    ax.set_title(title,fontsize=12); ax.set_xlim(-72,72); ax.set_ylim(-9.5,9.5)
    ax.set_xlabel("X (mm)"); ax.grid(alpha=.2)
axes[0].set_ylabel("덱 기준 높이 (mm)")
axes[0].plot([],[],":",color="#c0392b",label="±10도 스윕 포락선"); axes[0].legend(loc="lower right",fontsize=9)
fig.suptitle("정면에서 보이는 틈 — 개구부를 치마까지 좁히면 사라진다",fontsize=13)
p=os.path.join(PREVIEW,"SLOT_FIX.png"); fig.savefig(p,dpi=115,bbox_inches="tight",facecolor="white")
print("saved",os.path.relpath(p,LOCAL))
print("립 상단 반폭 %.2f -> 지름 %.2f mm,  치마 대비 틈 %.2f mm/side"%(LIP_TOP,LIP_TOP*2,LIP_TOP-FLANGE))
