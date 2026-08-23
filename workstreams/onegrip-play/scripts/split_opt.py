import sys, json, math, os
sys.path.insert(0, os.path.dirname(__file__))
from axis_opt import *
import numpy as np
from scipy.optimize import minimize
FR=[frame(N0[i]) for i in range(4)]
def axf(i,p,q):
    u,v,z=FR[i]; a=z+p*u+q*v; return a/np.linalg.norm(a)
def dvf(p,q): return math.degrees(math.atan(math.hypot(p,q)))
def pocket_x(i,a,sign):
    c,A,h=obb(P[i],a,POCKET,SW+0.2,SW_FRONT)
    xs=[(c+A.T@(np.array([p,q,r],float)*h))[0] for p in(-1,1) for q in(-1,1) for r in(-1,1)]
    return max(xs) if sign>0 else min(xs)
def mnclr(x):
    B=[obb(P[i],axf(i,x[2*i],x[2*i+1]),SW,SW,SW_FRONT) for i in range(4)]
    m=1e9
    for i,j in KEY_PAIRS:
        hit,v=sat(B[i],B[j]); m=min(m,-v if hit else v)
    return m
def sok(x,w): return min(-w-pocket_x(2,axf(2,x[4],x[5]),+1), pocket_x(3,axf(3,x[6],x[7]),-1)-w)
def solve(tgt,wall,ntry=10,it=140):
    rng=np.random.default_rng(101); best=None
    for k in range(ntry):
        x0=np.zeros(8) if k==0 else rng.normal(0,0.22,8)
        y0=np.append(x0,[max(dvf(x0[2*i],x0[2*i+1]) for i in range(4))+3])
        cons=[{"type":"ineq","fun":lambda y: mnclr(y[:8])-tgt},
              {"type":"ineq","fun":lambda y: sok(y[:8],wall)}]
        for i in range(4):
            cons.append({"type":"ineq","fun":(lambda y,i=i: y[8]-dvf(y[2*i],y[2*i+1]))})
        r=minimize(lambda y:y[8],y0,method="SLSQP",constraints=cons,
                   bounds=[(-0.9,0.9)]*8+[(0,60)],options={"maxiter":it,"ftol":1e-9})
        x=r.x[:8]
        if mnclr(x)>=tgt-1e-6 and sok(x,wall)>=-1e-6:
            m=max(dvf(x[2*i],x[2*i+1]) for i in range(4))
            if best is None or m<best[0]-1e-4: best=(m,x.copy())
    if best is None: return None
    m,x=best
    cons=[{"type":"ineq","fun":lambda z: mnclr(z)-tgt},
          {"type":"ineq","fun":lambda z: sok(z,wall)},
          {"type":"ineq","fun":lambda z: m+0.03-max(dvf(z[2*i],z[2*i+1]) for i in range(4))}]
    r=minimize(lambda z: sum(dvf(z[2*i],z[2*i+1]) for i in range(4)),x,method="SLSQP",
               constraints=cons,bounds=[(-0.9,0.9)]*8,options={"maxiter":200,"ftol":1e-10})
    if mnclr(r.x)>=tgt-1e-6 and sok(r.x,wall)>=-1e-6: x=r.x
    return x
if __name__=="__main__":
    out={}
    for wall in (0.5,1.0,1.5,1.88):
        for tgt in (1.0,1.2):
            x=solve(tgt,wall)
            k=f"t{tgt}_w{wall}"
            if x is None:
                out[k]=None; print(k,"해 없음",flush=True); continue
            A=[axf(i,x[2*i],x[2*i+1]) for i in range(4)]
            ds=[dvf(x[2*i],x[2*i+1]) for i in range(4)]
            out[k]=dict(axes=[list(map(float,a)) for a in A], dev=ds,
                        maxdev=max(ds), clr=mnclr(x), i3x=pocket_x(2,A[2],1))
            print(f"{k}: maxdev {max(ds):.2f}  dev {[round(d,2) for d in ds]}  "
                  f"clr {mnclr(x):.3f}  I3x {pocket_x(2,A[2],1):.2f}",flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__),"..","cad_dump","axis_free_split.json"),"w"))
