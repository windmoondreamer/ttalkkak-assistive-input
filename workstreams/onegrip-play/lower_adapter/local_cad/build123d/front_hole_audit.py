"""정면 실루엣의 '구멍' 정량 — 렌더 대신 래스터 + flood fill.

전 부품 삼각형을 시선 평면에 투영해 채운 뒤, 테두리에서 flood fill 한다.
채워지지 않은 빈칸 = 모델에 둘러싸인 진짜 구멍(뚫려 보이는 곳).
"""
from __future__ import annotations
import os, sys, math
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import preview_render as PR
matplotlib.rcParams["font.family"]="Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"]=False
LOCAL=os.path.dirname(HERE); STL=os.path.join(LOCAL,"export","stl"); PREVIEW=os.path.join(LOCAL,"preview")
import sys as _s
BASE=_s.argv[1] if len(_s.argv)>1 else "ERGO_HOUSING_25_WRAP_W134"
PARTS=[BASE,"BOTTOM_CARRIER_FINAL","STOCK_GIMBAL_IN_GRIP","ONEGRIP_IN_GRIP"]
UP,UH=PR.UP,PR.UH
T=np.vstack([PR.read_stl(os.path.join(STL,n+".stl")) for n in PARTS if os.path.exists(os.path.join(STL,n+".stl"))])

def silhouette(wd, px=800):
    u,v,w=PR.frame(np.array(wd,dtype=float))
    P=np.stack([T.reshape(-1,3)@u, T.reshape(-1,3)@v],1).reshape(-1,3,2)
    lo=P.reshape(-1,2).min(0)-2; hi=P.reshape(-1,2).max(0)+2
    fig=plt.figure(figsize=(px/100.0, px/100.0*(hi[1]-lo[1])/(hi[0]-lo[0])), dpi=100)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(lo[0],hi[0]); ax.set_ylim(lo[1],hi[1]); ax.axis("off")
    ax.add_collection(PolyCollection(P,facecolors="k",edgecolors="k",linewidths=0.35))
    fig.canvas.draw()
    buf=np.asarray(fig.canvas.buffer_rgba())[:,:,:3]
    plt.close(fig)
    occ=buf.sum(2)<600                       # 검정 = 재료
    mmpp=(hi[0]-lo[0])/occ.shape[1]
    return occ, mmpp

def holes(occ):
    """테두리에서 flood fill -> 도달 못 한 빈칸이 둘러싸인 구멍.

    (y,x) 튜플 스택은 1.4M 셀에서 MemoryError 를 낸다 (실측).
    y*W+x 정수 인코딩 + numpy bool 배열로 바꾼다.
    """
    H, W = occ.shape
    free = (~occ).ravel()
    seen = np.zeros(free.size, dtype=bool)
    st = []
    top = np.arange(0, W); bot = np.arange((H - 1) * W, H * W)
    left = np.arange(0, H * W, W); right = left + (W - 1)
    for idx in (top, bot, left, right):
        k = idx[free[idx] & ~seen[idx]]
        seen[k] = True
        st.extend(k.tolist())
    while st:
        i = st.pop()
        y, x = divmod(i, W)
        if x > 0 and free[i - 1] and not seen[i - 1]:
            seen[i - 1] = True; st.append(i - 1)
        if x < W - 1 and free[i + 1] and not seen[i + 1]:
            seen[i + 1] = True; st.append(i + 1)
        if y > 0 and free[i - W] and not seen[i - W]:
            seen[i - W] = True; st.append(i - W)
        if y < H - 1 and free[i + W] and not seen[i + W]:
            seen[i + W] = True; st.append(i + W)
    return (free & ~seen).reshape(H, W)


def label_sizes(mask):
    """연결 성분 목록 -> (셀수, xmin, xmax, ymin, ymax). 정수 인코딩 스택."""
    H, W = mask.shape
    m = mask.ravel()
    lab = np.zeros(m.size, dtype=bool)
    out = []
    for start in np.nonzero(m & ~lab)[0]:
        if lab[start]:
            continue
        st = [int(start)]; lab[start] = True; cells = []
        while st:
            i = st.pop(); cells.append(i)
            y, x = divmod(i, W)
            for j, ok in ((i - 1, x > 0), (i + 1, x < W - 1),
                          (i - W, y > 0), (i + W, y < H - 1)):
                if ok and m[j] and not lab[j]:
                    lab[j] = True; st.append(j)
        c = np.array(cells); ys, xs = c // W, c % W
        out.append((len(c), int(xs.min()), int(xs.max()),
                    int(ys.min()), int(ys.max())))
    out.sort(reverse=True)
    return out


def main():
    views=[("앞 0도",UH),("앞 부각10도",UH*0.985+UP*0.174),("앞 부각20도",UH*0.940+UP*0.342),
           ("앞 부각30도",UH*0.866+UP*0.5),("반대쪽 0도",-UH),("측면 0도",np.array([-1.0,0,0]))]
    print("정면 실루엣에 둘러싸인 구멍 (뚫려 보이는 면적)")
    for nm,wd in views:
        occ,mmpp=silhouette(wd)
        hm=holes(occ)
        tot=hm.sum()*mmpp*mmpp
        parts=label_sizes(hm)[:3]
        s=" / ".join("%.1fmm2 (%.0fx%.0f)"%(n*mmpp*mmpp,(x1-x0+1)*mmpp,(y1-y0+1)*mmpp) for n,x0,x1,y0,y1 in parts) or "없음"
        print("  %-10s 총 %8.1f mm2   상위: %s"%(nm,tot,s))
    return 0

if __name__=="__main__":
    sys.exit(main())
