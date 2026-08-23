"""실루엣 구멍의 3D 위치 특정.

여러 시선에서 실루엣 래스터 -> 테두리 flood fill -> 둘러싸인 빈칸(=관통 구멍).
그 픽셀을 광선으로 되쏘아, 광선에 가장 가까운 모델 삼각형들의 좌표를 보고한다.
"""
from __future__ import annotations
import os, sys
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import preview_render as PR
LOCAL=os.path.dirname(HERE); STL=os.path.join(LOCAL,"export","stl")
UP,UH=PR.UP,PR.UH
BASE=sys.argv[1] if len(sys.argv)>1 else "ERGO_HOUSING_25_WRAP_W134"
H=PR.read_stl(os.path.join(STL,BASE+".stl"))

def silhouette(T,wd,px=1200):
    u,v,w=PR.frame(np.array(wd,dtype=float))
    P=np.stack([T.reshape(-1,3)@u,T.reshape(-1,3)@v],1).reshape(-1,3,2)
    lo=P.reshape(-1,2).min(0)-2; hi=P.reshape(-1,2).max(0)+2
    fig=plt.figure(figsize=(px/100.0,px/100.0*(hi[1]-lo[1])/(hi[0]-lo[0])),dpi=100)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(lo[0],hi[0]); ax.set_ylim(lo[1],hi[1]); ax.axis("off")
    ax.add_collection(PolyCollection(P,facecolors="k",edgecolors="k",linewidths=0.35))
    fig.canvas.draw(); buf=np.asarray(fig.canvas.buffer_rgba())[:,:,:3]; plt.close(fig)
    occ=buf.sum(2)<600
    return occ,lo,hi,u,v,w

def enclosed(occ):
    Hh,Ww=occ.shape; free=~occ; seen=np.zeros_like(free); st=[]
    for x in range(Ww):
        for y in (0,Hh-1):
            if free[y,x]: st.append((y,x)); seen[y,x]=True
    for y in range(Hh):
        for x in (0,Ww-1):
            if free[y,x] and not seen[y,x]: st.append((y,x)); seen[y,x]=True
    while st:
        y,x=st.pop()
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<Hh and 0<=nx<Ww and free[ny,nx] and not seen[ny,nx]:
                seen[ny,nx]=True; st.append((ny,nx))
    return free & ~seen

def comps(mask):
    Hh,Ww=mask.shape; lab=np.zeros((Hh,Ww),int); cur=0; out=[]
    for y in range(Hh):
        for x in range(Ww):
            if mask[y,x] and lab[y,x]==0:
                cur+=1; st=[(y,x)]; lab[y,x]=cur; pts=[]
                while st:
                    a,b=st.pop(); pts.append((a,b))
                    for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                        ny,nx=a+dy,b+dx
                        if 0<=ny<Hh and 0<=nx<Ww and mask[ny,nx] and lab[ny,nx]==0:
                            lab[ny,nx]=cur; st.append((ny,nx))
                out.append(pts)
    out.sort(key=len,reverse=True); return out

C=H.mean(1)
def report(wd,lab):
    occ,lo,hi,u,v,w=silhouette(H,wd)
    hm=enclosed(occ); cs=comps(hm)
    mmpp=(hi[0]-lo[0])/occ.shape[1]
    print("\n[%s]  구멍 성분 %d개"%(lab,len(cs)))
    for pts in cs[:4]:
        area=len(pts)*mmpp*mmpp
        if area<1.0: continue
        ys=np.array([p[0] for p in pts]); xs=np.array([p[1] for p in pts])
        su=lo[0]+(xs+0.5)*mmpp
        sv=hi[1]-(ys+0.5)*mmpp
        # 이 픽셀들의 광선에 가까운 삼각형 찾기
        cu=C@u; cv=C@v
        near=[]
        for a,b in zip(su[::max(1,len(su)//40)],sv[::max(1,len(sv)//40)]):
            dd=np.hypot(cu-a,cv-b)
            k=np.argsort(dd)[:6]
            near.extend(C[k][dd[k]<2.5])
        if not near: continue
        near=np.array(near)
        print("  면적 %6.1f mm2  화면 %5.1f x %5.1f mm"%(area,su.max()-su.min(),sv.max()-sv.min()))
        print("    주변 재료 좌표  X %7.2f~%7.2f  Y %8.2f~%8.2f  Z %8.2f~%8.2f"
              %(near[:,0].min(),near[:,0].max(),near[:,1].min(),near[:,1].max(),near[:,2].min(),near[:,2].max()))
        print("    중심 (%.2f, %.2f, %.2f)"%tuple(near.mean(0)))

for lab,wd in (("앞 부각30도",UH*0.866+UP*0.5),("앞 부각20도",UH*0.940+UP*0.342),
               ("앞 부각40도",UH*0.766+UP*0.643),("뒤 부각30도",-UH*0.866+UP*0.5),
               ("측면 부각30도",np.array([-0.866,0,0])+UP*0.5)):
    report(wd,lab)
