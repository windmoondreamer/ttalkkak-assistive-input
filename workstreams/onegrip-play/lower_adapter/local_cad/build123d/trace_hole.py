"""관통 구멍 터널 추적 — 광선이 실제로 어디를 지나가는지 3D 로 찍는다."""
from __future__ import annotations
import os, sys, struct
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
LOCAL=os.path.dirname(HERE); STL=os.path.join(LOCAL,"export","stl")
UP=np.array([0.0,0.3420201433256687,0.9396926207859084])
UH=np.array([0.0,0.9396926207859084,-0.3420201433256687])

def read_stl(p):
    with open(p,'rb') as f:
        h=f.read(5); f.seek(0)
        if h==b'solid':
            v=[l.split()[1:4] for l in f if l.split() and l.split()[0]==b'vertex']
            return np.array(v,dtype=float).reshape(-1,3,3)
        f.seek(80); n=struct.unpack('<I',f.read(4))[0]
        t=np.empty((n,3,3))
        for i in range(n):
            d=struct.unpack('<12fH',f.read(50)); t[i]=np.array(d[3:12]).reshape(3,3)
        return t

T=read_stl(os.path.join(STL,"ERGO_HOUSING_25_WRAP_W134.stl"))
v0,v1,v2=T[:,0],T[:,1],T[:,2]; e1,e2=v1-v0,v2-v0

def nhits(orig,d):
    p=np.cross(d,e2); det=(e1*p).sum(1); m=np.abs(det)>1e-9
    inv=np.zeros(len(T)); inv[m]=1.0/det[m]
    t0=orig-v0; u=(t0*p).sum(1)*inv
    q=np.cross(t0,e1); vv=(d*q).sum(1)*inv; tt=(e2*q).sum(1)*inv
    ok=m&(u>=0)&(vv>=0)&(u+vv<=1)&(tt>0)
    return int(ok.sum())

def frame(wd):
    w=np.array(wd,float); w/=np.linalg.norm(w)
    up=UP if abs(w@UP)<0.95 else np.array([1.0,0,0])
    u=np.cross(up,w); u/=np.linalg.norm(u); v=np.cross(w,u)
    return u,v,w

def scan(wd,lab,step=0.6):
    u,v,w=frame(wd)
    P=T.reshape(-1,3)
    su,sv=P@u,P@v
    us=np.arange(su.min(),su.max(),step); vs=np.arange(sv.min(),sv.max(),step)
    ctr=T.mean(1); cw=(ctr@w).min()-60
    hit=np.zeros((len(vs),len(us)),bool)
    for i,vv in enumerate(vs):
        for j,uu in enumerate(us):
            o=u*uu+v*vv+w*cw
            hit[i,j]=nhits(o,w)>0
    free=~hit; seen=np.zeros_like(free); st=[]
    Hh,Ww=free.shape
    for x in range(Ww):
        for y in (0,Hh-1):
            if free[y,x] and not seen[y,x]: st.append((y,x)); seen[y,x]=True
    for y in range(Hh):
        for x in (0,Ww-1):
            if free[y,x] and not seen[y,x]: st.append((y,x)); seen[y,x]=True
    while st:
        y,x=st.pop()
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<Hh and 0<=nx<Ww and free[ny,nx] and not seen[ny,nx]:
                seen[ny,nx]=True; st.append((ny,nx))
    hole=free&~seen
    print("\n[%s] 관통 구멍 셀 %d개  면적 %.1f mm2"%(lab,hole.sum(),hole.sum()*step*step))
    if not hole.any(): return
    ys,xs=np.nonzero(hole)
    # 각 구멍 광선에서 가장 가까운 삼각형 정점 찾기 -> 터널 위치
    loc=[]
    for y,x in list(zip(ys,xs))[::max(1,len(ys)//60)]:
        o=u*us[x]+v*vs[y]+w*cw
        d=P-o; t=d@w; perp=d-np.outer(t,w)
        r=np.linalg.norm(perp,axis=1)
        k=np.argsort(r)[:4]
        loc.extend(P[k])
    loc=np.array(loc)
    print("  터널 주변 재료 최근접점")
    print("    X %7.2f ~ %7.2f    Y %8.2f ~ %8.2f    Z %8.2f ~ %8.2f"
          %(loc[:,0].min(),loc[:,0].max(),loc[:,1].min(),loc[:,1].max(),loc[:,2].min(),loc[:,2].max()))
    for s,lb in ((+1,"X>0"),(-1,"X<0")):
        q=loc[np.sign(loc[:,0])==s]
        if len(q): print("    %s : X %.2f~%.2f  Y %.2f~%.2f  Z %.2f~%.2f"
                         %(lb,q[:,0].min(),q[:,0].max(),q[:,1].min(),q[:,1].max(),q[:,2].min(),q[:,2].max()))

for lab,wd in (("앞 부각40도",UH*0.766+UP*0.643),("앞 부각30도",UH*0.866+UP*0.5)):
    scan(wd,lab)
