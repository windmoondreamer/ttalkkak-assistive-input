"""±15도 모션 포락선 밴드 생성 + 절삭 안전성 실측 (읽기 전용).

기존 conformal_envelope.json(±10도) 과 **같은 밴드 형식**으로 만든다.
형상 재구성이 아니라 keep-out 용이다.
합성 회전은 캐시된 ±10도 자세를 0.0012mm 오차로 재현함을 확인했다.
"""
from __future__ import annotations
import os, sys, json, math, struct
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import parameters as P
LOCAL=os.path.dirname(HERE)
ADAPTER=os.path.dirname(LOCAL)
DECK=-61.878507
PIV=np.array([0.0,27.269160,DECK-52.9823])
MOV=("Joystick_1","Joystick_2","HW504_B","Small_joystick_attachment","Backplate",
     "Magnet","Pitch","Roll","Spring_holder","Inner_racing","Outer_racing","Part ")

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

def neutral_moving():
    d=np.load(os.path.join(ADAPTER,"cad_dump","motion_configs_gripfix.npz"))
    ks=[k for k in d.keys() if k.split("|")[0]=="neutral"
        and any(k.split("|")[1].startswith(g) for g in MOV)]
    return np.vstack([d[k] for k in ks])

def R(ax,deg):
    t=math.radians(deg); c,s=math.cos(t),math.sin(t)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]]) if ax=="X" else np.array([[c,0,s],[0,1,0],[-s,0,c]])

def hull(pts):
    """monotone chain convex hull (scipy 없이)."""
    P=sorted(set(map(tuple,np.round(np.asarray(pts,dtype=float),3))))
    if len(P)<3: return P
    def half(Q):
        st=[]
        for q in Q:
            while len(st)>=2:
                (ax,ay),(bx,by)=st[-2],st[-1]
                if (bx-ax)*(q[1]-ay)-(by-ay)*(q[0]-ax)<=0: st.pop()
                else: break
            st.append(q)
        return st
    lo=half(P); up=half(P[::-1])
    return lo[:-1]+up[:-1]


def grow(H,clr,nd=16):
    """볼록껍질을 clr 만큼 바깥으로 (Minkowski 근사)."""
    A=np.array(H); out=[]
    for i in range(nd):
        a=2*math.pi*i/nd
        out.append(A+np.array([clr*math.cos(a),clr*math.sin(a)]))
    return hull(np.vstack(out))



NPOLY = 32
CY_AX = 27.269160

def radial_poly(H, n=NPOLY, cx=0.0, cy=CY_AX):
    """볼록껍질을 중심 (cx,cy) 기준 n등분 반경 다각형으로 바꾼다.

    loft 하려면 밴드마다 **정점 수가 같아야** 한다. 볼록이므로 반경 재표본이
    형상을 보존한다.

    광선 c+t*d 와 변 p0+u*e 의 교차는
        t = cross(w,e)/cross(d,e),  u = cross(w,d)/cross(d,e),  w = p0-c
    이다. u 부호를 뒤집어 쓰면 엉뚱한 변을 골라 자기교차 다각형이 나오고
    OCC 가 `TopoDS::Face` 타입 오류를 낸다 (실측).
    """
    A = np.asarray(H, dtype=float)
    c = np.array([float(cx), float(cy)])
    if not point_in_hull(c, A):
        c = A.mean(axis=0)
    p0 = A
    p1 = np.roll(A, -1, axis=0)
    e = p1 - p0
    w = p0 - c
    out = []
    for k in range(n):
        ang = 2 * math.pi * k / n
        d = np.array([math.cos(ang), math.sin(ang)])
        den = d[0] * e[:, 1] - d[1] * e[:, 0]          # cross(d,e)
        ok = np.abs(den) > 1e-12
        t = np.full(len(A), -1.0)
        u = np.full(len(A), -1.0)
        t[ok] = (w[ok, 0] * e[ok, 1] - w[ok, 1] * e[ok, 0]) / den[ok]
        u[ok] = (w[ok, 0] * d[1] - w[ok, 1] * d[0]) / den[ok]
        good = ok & (t > 0) & (u >= -1e-9) & (u <= 1 + 1e-9)
        r = float(t[good].max()) if good.any() else float(np.linalg.norm(A - c, axis=1).max())
        out.append([float(c[0] + d[0] * r), float(c[1] + d[1] * r)])
    return out


def point_in_hull(c, A):
    m = len(A)
    for i in range(m):
        p0 = A[i]; p1 = A[(i + 1) % m]
        if (p1[0] - p0[0]) * (c[1] - p0[1]) - (p1[1] - p0[1]) * (c[0] - p0[0]) < -1e-9:
            return False
    return True


def swept(N,amax,nphi=24):
    """(구) 반각 amax 원뿔. **부족하다** — 아래 square_poses 를 쓴다."""
    out=[N]
    for i in range(nphi):
        ph=2*math.pi*i/nphi
        M=R("X",amax*math.cos(ph))@R("Y",amax*math.sin(ph))
        out.append((N-PIV)@M.T+PIV)
    return np.vstack(out)

def square_poses(amax,n=9):
    """스톡 짐벌은 Roll/Pitch 독립 2축 카르단이다.

    도달 집합은 반각 amax 원뿔이 아니라 **정사각형** |roll|<=amax & |pitch|<=amax 다.
    코너 (amax,amax) 의 합성 편향은 acos(cos^2 amax) = 21.06deg (amax=15) 로
    원뿔 밖이다. 원뿔로 포락선을 만들면 코너 자세에서 간섭이 남는다 (실측).
    """
    g=np.linspace(-amax,amax,n)
    out=[]
    for r in g:
        for pt in g:
            out.append((float(r),float(pt)))
    return out

def band_hull_union(N,zs,poses,clr=1.5,maxv=28,merge=1,smear_down=4):
    """자세별로 밴드 2D 볼록껍질을 구해 합집합의 껍질을 취한다.

    전 자세 점군을 통째로 쌓으면 자세 x 72만점이라 못 든다. 자세마다 껍질만
    남기면 값이 같으면서 훨씬 가볍다.

    merge: 이웃 밴드까지 합친다. 이산 자세 격자 사이 각도에서 점이 다른 Z
    밴드로 넘어가 껍질 밖으로 삐져나오는 것을 막는다 (실측: 45도 방위에서
    15도는 통과인데 13.53도가 접촉하는 비단조가 나왔다).
    """
    dz=zs[1]-zs[0]
    acc={i:[] for i in range(len(zs))}
    for k,(r,pt) in enumerate(poses):
        M=R("X",r)@R("Y",pt)
        Q=(N-PIV)@M.T+PIV
        for i,z in enumerate(zs):
            s=Q[(Q[:,2]>=z)&(Q[:,2]<z+dz)]
            if len(s)<3: continue
            H=hull(s[:,:2])
            if len(H)>=3: acc[i].extend(H)
        if (k+1)%25==0: print("   자세 %d/%d"%(k+1,len(poses)))
    out=[]
    for i,z in enumerate(zs):
        # smear_down: 위 밴드의 (더 큰) 껍질을 아래로 번지게 한다.
        # 밴드가 아래로 갈수록 좁아지므로 절삭면에 가로 계단이 생기고, 그
        # 계단이 코어 선반 한가운데 떨어지면 박판이 남는다 (실측: Y 60~70,
        # Z -90~-89 에 10mm 선반 중 1.02mm 잔류, 73.5 x 9.0mm).
        pool=[]
        for j in range(max(0,i-merge), min(len(zs), i+smear_down+1)):
            pool.extend(acc[j])
        if len(pool)<3: out.append(None); continue
        H=hull(np.array(pool))
        G2=grow(H,clr)
        out.append(radial_poly(G2))
    return out


def bands(P3,zs,clr=1.5):
    out=[]
    dz=zs[1]-zs[0]
    for z in zs:
        s=P3[(P3[:,2]>=z)&(P3[:,2]<z+dz)]
        if len(s)<8: out.append(None); continue
        out.append([float(s[:,0].min()-clr),float(s[:,0].max()+clr),
                    float(s[:,1].min()-clr),float(s[:,1].max()+clr),int(len(s))])
    return out

def main():
    N=neutral_moving()
    print("이동부 점 %d"%len(N))
    zs=[float(z) for z in np.arange(-153.0,-59.9,1.0)]
    zs_=zs
    poses=square_poses(15.0,n=13)
    print("정사각형 자세 %d개 (roll x pitch, -15~+15, 2.5도 간격)"%len(poses))
    PG=band_hull_union(N,zs_,poses,clr=1.5)
    nv=[len(q) for q in PG if q]
    print("다각형 밴드 %d개, 정점 %d~%d"%(len(nv),min(nv),max(nv)))
    S15=swept(N,15.0)
    E10=bands(swept(N,10.0),zs); E15=bands(S15,zs)
    J={"zs":zs,"rects15":E15,"rects10":E10,"polys15":PG,"clearance":1.5,"amax":15.0,
       "basis":"square |roll|<=15 & |pitch|<=15 (13x13 grid, band-merge +-1, radial 32-gon)",
       "note":"합성 회전(±10도 재현오차 0.0012mm) 기반. 원뿔이 아니라 정사각형 도달집합."}
    op=os.path.join(ADAPTER,"cad_dump","motion_envelope15.json")
    json.dump(J,open(op,"w",encoding="utf-8"),ensure_ascii=False)
    print("저장:",os.path.relpath(op,LOCAL))
    # V3 외피 대비 남는 살
    T=read_stl(os.path.join(LOCAL,"export","stl","ERGO_HOUSING_25_WRAP_FINAL_V3.stl"))
    V=T.reshape(-1,3)
    print("\n밴드별 ±15도 요구 vs V3 외곽 (남는 살, mm)")
    print("     Z     ±10 X범위        ±15 X범위       V3 외곽X    살(X)   ±15 Ymax  V3 Ymax  살(Y)")
    worst=(1e9,None)
    for i,z in enumerate(zs):
        a,b=E10[i],E15[i]
        if b is None: continue
        m=np.abs(V[:,2]-(z+0.5))<0.8
        if m.sum()<20: continue
        ox=V[m][:,0].max(); oy=V[m][:,1].max()
        wx=ox-b[1]; wy=oy-b[3]
        if int(z)%8==0:
            print("  %+7.1f  %6.1f~%5.1f   %6.1f~%5.1f   %7.1f  %6.2f   %6.1f  %6.1f  %6.2f"
                  %(z,a[0] if a else 0,a[1] if a else 0,b[0],b[1],ox,wx,b[3],oy,wy))
        for w,lab in ((wx,"X"),(wy,"Y")):
            if w<worst[0]: worst=(w,(z,lab))
    print("\n최소 남는 살 %.2f mm  @ Z %+.1f (%s 방향)"%(worst[0],worst[1][0],worst[1][1]))
    return 0

if __name__=="__main__":
    sys.exit(main())
