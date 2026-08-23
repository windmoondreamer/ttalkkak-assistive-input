"""스톡 짐벌 자체의 기계적 한계 각도 측정 (읽기 전용).

FIXED(Base/Roll_holder/Roll_holder_2/Spacer) 대비 MOVING(Roll/Pitch/Spring_holder)
을 피벗 둘레로 돌려 처음 닿는 각도를 찾는다. 형상 쓰기 0건.
"""
from __future__ import annotations
import os, sys, math
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import parameters as P, geometry_utils as G
import build123d as bd
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.BRepTools import BRepTools

LOCAL=os.path.dirname(HERE)
STEP=os.path.join(LOCAL,"reference","ONEGRIP_LOWER_ASSEMBLY_REFERENCE.step")
FIXED={"Base","Roll_holder","Roll_holder_2","Spacer"}
MOVING={"Roll","Pitch","Spring_holder"}

def load_named():
    doc=TDocStd_Document(TCollection_ExtendedString("d"))
    r=STEPCAFControl_Reader(); r.SetNameMode(True)
    r.ReadFile(STEP); r.Transfer(doc)
    st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    seq=TDF_LabelSequence(); st.GetFreeShapes(seq)
    out={}
    def walk(lab, loc):
        nm=TDataStd_Name(); got=lab.FindAttribute(TDataStd_Name.GetID_s(), nm)
        name=nm.Get().ToExtString() if got else ""
        l2=TopLoc_Location(st.GetLocation_s(lab).Transformation()) if st.IsReference_s(lab) else TopLoc_Location()
        cur=loc.Multiplied(l2) if st.IsReference_s(lab) else loc
        if st.IsReference_s(lab):
            ref=lab.__class__()
            from OCP.TDF import TDF_Label
            ref=TDF_Label()
            st.GetReferredShape_s(lab, ref)
            walk(ref, cur)
            return
        if st.IsSimpleShape_s(lab):
            sh=st.GetShape_s(lab)
            if sh is not None and not sh.IsNull():
                out.setdefault(str(name),[]).append(sh.Moved(cur))
        ch=TDF_LabelSequence(); st.GetComponents_s(lab, ch)
        for i in range(1, ch.Length()+1): walk(ch.Value(i), cur)
    for i in range(1, seq.Length()+1):
        walk(seq.Value(i), TopLoc_Location())
    return out

def pts_of(shapes, tol=0.5):
    T=[]
    for sh in shapes:
        s=bd.Shape(sh)
        try:
            BRepTools.Clean_s(s.wrapped)
            f=os.path.join(P.EXPORT_STL,"_s.stl"); bd.export_stl(s,f,tolerance=tol,angular_tolerance=0.5)
            T.append(G.read_stl_tris(f)); os.remove(f)
        except Exception as e:
            print("   skip:",e)
    return np.vstack(T) if T else None

def main():
    named=load_named()
    keys=sorted(named.keys())
    print("STEP 안 이름 %d종"%len(keys))
    hit=[k for k in keys if k.split(" ")[0] in FIXED|MOVING]
    print("관심 부품:", hit)
    F=[]; M=[]
    for k,v in named.items():
        base=k.split(" ")[0]
        if base in FIXED: F+=v
        elif base in MOVING: M+=v
    print("FIXED shape %d / MOVING shape %d"%(len(F),len(M)))
    if not F or not M:
        print("이름 매칭 실패 - 중단"); return 1
    TF=pts_of(F); TM=pts_of(M)
    print("FIXED 삼각형 %d / MOVING 삼각형 %d"%(len(TF),len(TM)))
    # 어셈블리 -> 그립 프레임
    import json
    A=json.load(open(os.path.join(LOCAL,"reports","01_reference_alignment.json"),encoding="utf-8"))
    T=A["T_assembly_to_grip"]; R=np.array(T["R"]); t=np.array(T["t"])
    f=lambda X:(X.reshape(-1,3)@R.T+t).reshape(-1,3,3)
    TF=f(TF); TM=f(TM)
    DECK=-61.878507; PIV=np.array([0.0,27.269160,DECK-52.9823])
    print("그립 프레임 FIXED bbox ",TF.reshape(-1,3).min(0).round(2),TF.reshape(-1,3).max(0).round(2))
    print("             MOVING bbox",TM.reshape(-1,3).min(0).round(2),TM.reshape(-1,3).max(0).round(2))
    S=TM.mean(1)                      # 이동부 삼각형 중심
    rng=np.random.default_rng(0)
    if len(S)>6000: S=S[rng.choice(len(S),6000,replace=False)]
    def rot(ax,deg):
        r=math.radians(deg); c,sn=math.cos(r),math.sin(r)
        M2=np.array([[1,0,0],[0,c,-sn],[0,sn,c]]) if ax=="X" else np.array([[c,0,sn],[0,1,0],[-sn,0,c]])
        return (S-PIV)@M2.T+PIV
    print("")
    print("스톡 짐벌 자체 한계 — 이동부가 고정부와 처음 닿는 각도")
    print("  축 방향   0도   5    8   10   12   14   15   16   18   20")
    for ax in ("X","Y"):
        for sg in (+1,-1):
            row=[]; first=None
            for deg in (0,5,8,10,12,14,15,16,18,20):
                n=int(G.mesh_inside(TF,rot(ax,sg*deg)).sum())
                row.append("%4d"%n)
                if deg>0 and n>0 and first is None: first=deg
            print("  %s %+d   %s   -> 처음 접촉 %s"%(ax,sg," ".join(row),("%d도"%first) if first else ">20도"))
    return 0

if __name__=="__main__":
    sys.exit(main())
