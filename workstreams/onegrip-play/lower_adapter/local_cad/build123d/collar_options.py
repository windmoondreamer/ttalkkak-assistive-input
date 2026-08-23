"""A/B collar 제약 설명도 — 위에서 본 윤곽 비교 + 옆 단면.

측정만 한다. 형상 쓰기 0건.
"""
from __future__ import annotations
import os, sys, math
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
matplotlib.rcParams["font.family"]="Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"]=False
LOCAL=os.path.dirname(HERE); PREVIEW=os.path.join(LOCAL,"preview")
DECK=-61.878507; C=np.array([0.0,27.269160]); NA=144
d=np.load(os.path.join(LOCAL,"..","cad_dump","motion_configs_gripfix.npz"))
GRIP=("Joystick_1","Joystick_2","HW504_B","Small_joystick_attachment","Backplate","Magnet","Pitch")
def sel(c=None):
    ks=[k for k in d.keys() if any(k.split("|")[1].startswith(g) for g in GRIP)
        and (c is None or k.split("|")[0]==c)]
    return np.vstack([d[k] for k in ks])
U,N=sel(),sel("neutral")
ANG=np.arange(NA)*2*math.pi/NA
def prof(p):
    """각도별 최대반경. 빈 bin 은 원형 보간하고, tessellation 톱니는
    ±2 bin 이동최대로 눌러 실제 포락선에 맞춘다."""
    v=p[:,:2]-C; r=np.hypot(v[:,0],v[:,1]); a=np.arctan2(v[:,1],v[:,0])%(2*math.pi)
    i=np.clip((a/(2*math.pi)*NA).astype(int),0,NA-1)
    o=np.full(NA,np.nan)
    for k in range(NA):
        s=r[i==k]
        if s.size: o[k]=s.max()
    m=~np.isnan(o)
    if m.sum()<3: return np.nan_to_num(o)
    idx=np.arange(NA)
    o=np.interp(idx, idx[m], o[m], period=NA)
    w=np.stack([np.roll(o,k) for k in (-2,-1,0,1,2)])
    return w.max(axis=0)
def slab(p,z,t=0.75): return p[(p[:,2]>z-t)&(p[:,2]<z+t)]
def poly(r):
    return np.column_stack([C[0]+np.cos(ANG)*r, C[1]+np.sin(ANG)*r])
def close(P): return np.vstack([P,P[:1]])

zs=np.arange(-9.0,26.01,0.5); Pn={z:prof(slab(N,DECK+z)) for z in zs}
DZ=10.0
ps=prof(slab(U,DECK+DZ))
pe=np.max(np.stack([Pn[z] for z in zs if z<=DZ+1e-9]),axis=0)
rA=np.maximum(ps+1.5, pe+0.8); rB=ps+1.5
grip=prof(slab(N,DECK+DZ)); flange=prof(slab(N,DECK-6.0,1.0)); sweep=prof(slab(U,DECK))

fig,ax=plt.subplots(figsize=(9.2,9.2))
def L(r,c,lab,lw=2.0,ls="-"):
    P=close(poly(r)); ax.plot(P[:,0],P[:,1],ls,color=c,lw=lw,label=lab)
# 현재 개구부 (실측 92.9 x 89.8, 라운드 사각)
from matplotlib.patches import FancyBboxPatch
ax.add_patch(plt.Rectangle((-46.4,-18.4),92.9,89.8,fill=False,ec="#c0392b",lw=2.4,ls="--",
                           label="현재 개구부 92.9 x 89.8"))
L(flange,"#e67e22","그립 착좌 플랜지 77.5 x 72.4  ← A 의 한계",2.2)
L(rA,"#2980b9","A 고정식 collar 79.3 x 77.5",2.4)
L(rB,"#27ae60","B 분리형 링 65.0 x 66.2",2.4)
L(sweep,"#7f8c8d","덱에서 ±10도 스윕 74.9 x 71.4",1.4,":")
L(grip,"#34495e","그립 (덱+10mm, 중립)",1.6)
ax.plot([C[0]],[C[1]],"k+",ms=10)
ax.set_aspect("equal"); ax.grid(alpha=.25)
ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")
ax.set_title("위에서 본 개구부 — 무엇이 각 안의 한계를 정하는가  (덱 위 10mm 기준)",fontsize=12)
ax.legend(loc="upper left",fontsize=9,framealpha=.95)
p=os.path.join(PREVIEW,"COLLAR_AB_TOP.png")
fig.savefig(p,dpi=115,bbox_inches="tight",facecolor="white"); plt.close(fig)
print("saved",os.path.relpath(p,LOCAL))

# ---- 옆 단면 (X=0, Y-Z) : 왜 A 가 플랜지에 막히는가
fig,ax=plt.subplots(figsize=(10.0,7.6))
m=np.abs(N[:,0])<3.0
ax.plot(N[m][:,1],N[m][:,2],".",ms=1.0,color="#95a5a6",label="그립 (중립) 단면")
fl=slab(N,DECK-6.0,1.2)
ax.plot([fl[:,1].min(),fl[:,1].max()],[DECK-6.0,DECK-6.0],color="#e67e22",lw=5,solid_capstyle="butt",
        label="착좌 플랜지 77.5 x 72.4  ← 위로 빠져나가야 한다")
ax.axhline(DECK,color="#2c3e50",lw=1.6)
ax.text(-58,DECK+1.5,"덱 평면",fontsize=10,color="#2c3e50")
for r,c,lab in ((rA,"#2980b9","A 고정식 collar (내경 79.3)"),(rB,"#27ae60","B 분리형 링 (내경 65.0)")):
    y1=C[1]+r[0]; y2=C[1]-r[NA//2]
    ax.add_patch(plt.Rectangle((y1,DECK),5.0,DZ,fc=c,alpha=.6,ec=c))
    ax.add_patch(plt.Rectangle((y2-5.0,DECK),5.0,DZ,fc=c,alpha=.6,ec=c,label=lab))
ax.plot([C[1]],[DECK-52.9823],"kx",ms=10)
ax.text(C[1]+3,DECK-53.5,"짐벌 피벗 (덱 아래 52.98mm)",fontsize=9)
for s2 in (+1,-1):
    a=math.radians(10)*s2
    ax.plot([C[1],C[1]+52.9823*math.sin(a)],[DECK-52.9823,DECK],color="#c0392b",lw=1.1,ls=":")
ax.annotate("+-10도 기울이면 덱에서 옆으로 9.20mm 이 여유는 어떤 설계로도 못 없앤다",

            xy=(C[1]+9.2,DECK), xytext=(C[1]-62,DECK-32), fontsize=9.5, color="#c0392b",
            arrowprops=dict(arrowstyle="->",color="#c0392b",lw=1.0))
ax.set_xlim(-62,118); ax.set_ylim(DECK-62,DECK+30)
ax.set_aspect("equal"); ax.grid(alpha=.25)
ax.set_xlabel("Y (mm)"); ax.set_ylabel("Z (mm)")
ax.set_title("옆 단면 — A 의 한계는 플랜지, B 의 한계는 모션",fontsize=12)
ax.legend(loc="upper right",fontsize=9,framealpha=.95)
p=os.path.join(PREVIEW,"COLLAR_AB_SECTION.png")
fig.savefig(p,dpi=115,bbox_inches="tight",facecolor="white"); plt.close(fig)
print("saved",os.path.relpath(p,LOCAL))
