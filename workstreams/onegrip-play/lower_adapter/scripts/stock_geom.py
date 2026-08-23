"""스톡 짐벌 — 전 부품 중립 복원 형상 캐시 (GET only).

Onshape `Complete` assembly 스냅샷은 **편향 상태**다 (Pitch 5.6062 deg / Roll 0.452 deg).
카트리지 설계는 중립 기준이어야 하므로 프레임별로 되돌린다.

프레임 분류는 이름이 아니라 **Base 대비 상대 회전각**으로 한다
(`Spring_holder` 는 이름과 달리 이동부다).

  GRIP 프레임 (기준)  : Joystick_*, Pitch, Spring_holder, Magnet(피치측)
  ROLL 프레임         : Roll, 롤축 베어링/나사
  BASE 프레임 (고정)  : Base, Roll_holder, Roll_holder_2, Spacer, 고정 나사/센서

중립화: 각 프레임의 강체 회전을 피벗 중심으로 역회전시킨다.
"""
import io
import json
import os
import sys

import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from onshape.client import BASE, session                     # noqa: E402
from onshape import write_client as wc                      # noqa: E402

OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
ASM = os.path.join(OUT, "asm_stock_full.json")
CACHE = os.path.join(OUT, "stock_full.npz")

# 사본(OneGrip_Play_V1) 의 element id — 원본 id 와 다르다
ASM_COMPLETE = "d0f87c9cb6d605a481820aa1"

SEAT_Z = -67.878507
SOCKET_XY = (0.0, 27.269160)
PIVOT = np.array([0.0, 27.275842424215217, -114.86085362847555])


def _get(url, params=None):
    r = session().get(url, params=params, timeout=300)
    r.raise_for_status()
    return r.json()


def fetch_assembly(force=False):
    if os.path.exists(ASM) and not force:
        return json.load(io.open(ASM, encoding="utf-8"))
    a = _get(f"{BASE}/assemblies/d/{wc.DID}/w/{wc.WID}/e/{ASM_COMPLETE}",
             params=[("includeNonSolids", "false")])
    inst = {}
    for node in [a["rootAssembly"]] + a.get("subAssemblies", []):
        for i in node.get("instances", []):
            inst[i["id"]] = i
    occ = []
    for o in a["rootAssembly"].get("occurrences", []):
        leaf = inst.get(o["path"][-1])
        if leaf is None or leaf.get("type") != "Part":
            continue
        occ.append({"name": leaf["name"], "elementId": leaf["elementId"],
                    "partId": leaf["partId"], "documentId": leaf["documentId"],
                    "microversion": leaf.get("documentMicroversion"),
                    "versionId": leaf.get("documentVersion"),
                    "T": o["transform"]})
    # Onshape instance name 은 "Roll <1>" 처럼 인스턴스 번호가 붙어 있다
    for o in occ:
        o["base"] = re.sub(r"\s*<\d+>\s*$", "", o["name"])
    # 동명 인스턴스 구분
    seen = {}
    for o in occ:
        n = o["name"]
        seen[n] = seen.get(n, 0) + 1
        o["key"] = n if seen[n] == 1 else f"{n}#{seen[n]}"
    json.dump(occ, io.open(ASM, "w", encoding="utf-8"), indent=1)
    return occ


# 메시를 받을 부품 (SMD 저항/캐패시터 등 미세 부품은 제외)
KEEP = re.compile(
    r"^(Base|Roll_holder|Roll_holder_2|Spacer|Roll|Pitch|Spring_holder"
    r"|Joystick_1|Joystick_2|Backplate|Small_joystick_attachment|HW504_B"
    r"|Hex socket head cap screw M[35]"
    r"|Outer_racing|Inner_racing"
    r"|Part [1-4]"                      # Hall_effect_sensor 어셈블리 부품
    r"|Magnet"
    r"|micro board|micro usb shell|micro usb internal|atmega32U4"
    r"|MICRO_stackable header 12)")


def _tris(j):
    """tessellatedfaces 응답 -> (N,3,3) 삼각형 (m).

    Onshape 응답 스키마가 두 가지다:
      (구) 최상위가 body 리스트, vertices 가 [x, y, z]
      (신) BTExportTessellatedFacesResponse-898, body 는 j["bodies"],
           vertices 가 {"x":..,"y":..,"z":..}
    둘 다 받는다.
    """
    bodies = j if isinstance(j, list) else (j.get("bodies") or [])
    tris = []
    for body in bodies:
        for f in body.get("faces", []):
            for facet in f.get("facets", []):
                v = facet.get("vertices") or []
                if len(v) != 3:
                    continue
                if isinstance(v[0], dict):
                    tris.append([[p["x"], p["y"], p["z"]] for p in v])
                else:
                    tris.append(v)
    return np.array(tris, dtype=float)


def fetch_mesh(o):
    """part tessellation (부품 로컬 좌표, mm).

    외부 표준부품 문서(나사)는 `/m/` `/v/` 경로가 빈 응답을 돌려주므로 메시를 못 받는다.
    -> 나사는 transform 만 쓰고 치수는 ISO 4762 규격으로 모델링한다.
    """
    if o["documentId"] != wc.DID:
        raise LookupError("external standard-content doc: no mesh")
    url = f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{o['elementId']}/tessellatedfaces"
    j = _get(url, params=[("partId", o["partId"]), ("angleTolerance", "0.09"),
                          ("chordTolerance", "0.00012")])
    t = _tris(j)
    if len(t) == 0:
        raise LookupError("empty tessellation")
    return t * 1000.0


# 프레임 귀속 — 이름 기반 명시 분류.
# `rot_angle(Rb.T @ R)` 로는 분류할 수 없다: 그 값은 편향이 아니라
# 부품 자체 로컬 방향까지 포함한 절대 방향차다 (마그넷이 110 deg 로 나오는 이유).
# 구조적 귀속은 원본 어셈블리 구성으로 확정한다.
FRAME_OF = {
    # 고정부 — 카트리지가 여기에 물린다
    "Base": "BASE", "Roll_holder": "BASE", "Roll_holder_2": "BASE", "Spacer": "BASE",
    # 롤 프레임
    "Roll": "ROLL",
    # 피치(=그립) 프레임
    "Pitch": "GRIP", "Spring_holder": "GRIP",
}
GRIP_PREFIX = ("Joystick_", "Button_", "PushBtn", "HW504_B", "Backplate",
               "Small_joystick_attachment", "micro", "atmega", "MICRO_", "Part ",
               "SOD ", "Magnet")


def classify(base):
    if base in FRAME_OF:
        return FRAME_OF[base]
    if base.startswith(GRIP_PREFIX):
        return "GRIP"
    return "UNKNOWN"          # 베어링 / 나사 등 — 개별 판정


def rot_angle(R):
    return np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)))


def build(force=False):
    if os.path.exists(CACHE) and not force:
        z = np.load(CACHE, allow_pickle=True)
        return {k: z[k] for k in z.files}

    occ = fetch_assembly(force)
    Tg = np.array(next(o for o in occ if o["base"] == "Joystick_1")["T"],
                  dtype=float).reshape(4, 4)
    Rg, tg = Tg[:3, :3], Tg[:3, 3] * 1000.0

    def to_grip(T):
        T = np.array(T, dtype=float).reshape(4, 4).copy()
        T[:3, 3] *= 1000.0
        R = Rg.T @ T[:3, :3]
        t = Rg.T @ (T[:3, 3] - tg)
        return R, t

    Rb, tb = to_grip(next(o for o in occ if o["base"] == "Base")["T"])
    ROLL_KEY = next(o["key"] for o in occ if o["base"] == "Roll")

    # 프레임별 중립화 회전 (그립 프레임에서 Base 를 정렬시키는 회전)
    C_base = Rb.T          # base 로컬 -> 중립.  전체 회전으로는 아래 N_base 를 쓴다
    N_base = Rb.T          # placeholder, 아래에서 실제 계산

    out, meta = {}, {}
    # 1) 각 occurrence 의 그립프레임 회전 R 을 구해 Base 대비 상대각으로 분류
    frames = {}
    for o in occ:
        R, t = to_grip(o["T"])
        frames[o["key"]] = (R, t)
        meta[o["key"]] = {"rel_deg": float(rot_angle(Rb.T @ R)),
                          "name": o["name"], "base": o["base"],
                          "partId": o["partId"], "elementId": o["elementId"]}

    # 2) 중립화: Base 프레임을 그립 프레임에 정렬시키는 회전 Nb (피벗 중심)
    #    Base 의 +Z 가 그립 +Z 와 평행해지고, Base 의 +X 가 그립 -X 와 평행해지도록.
    #    실제로는 Rb 를 가장 가까운 축정렬 회전으로 스냅한다.
    S = np.zeros((3, 3))
    for c in range(3):
        v = Rb[:, c]
        k = int(np.argmax(np.abs(v)))
        S[k, c] = np.sign(v[k])
    assert abs(np.linalg.det(S) - 1.0) < 1e-9, np.linalg.det(S)
    Nb = S @ Rb.T                                   # Base 프레임 중립화 회전

    # ROLL 프레임 중립화: Roll 의 상대각만큼
    Rr, _ = frames[ROLL_KEY]
    Sr = np.zeros((3, 3))
    for c in range(3):
        v = Rr[:, c]
        k = int(np.argmax(np.abs(v)))
        Sr[k, c] = np.sign(v[k])
    Nr = Sr @ Rr.T

    N_of = {"BASE": Nb, "ROLL": Nr, "GRIP": np.eye(3)}

    for o in occ:
        k = o["key"]
        fr = classify(o["base"])
        meta[k]["frame"] = fr
        if not KEEP.match(o["base"]):
            continue
        try:
            tri = fetch_mesh(o)
        except Exception as e:                       # noqa: BLE001
            print(f"  mesh 실패 {k}: {type(e).__name__} {str(e)[:100]}")
            continue
        R, t = frames[k]
        P = tri.reshape(-1, 3) @ R.T + t             # 그립좌표 (편향 상태 그대로 저장)
        out[k] = P.reshape(-1, 3, 3).astype(np.float32)
        print(f"  {k:<44s} {fr:<8s} tri={len(tri):6d}")

    # 나사/외부부품 transform (중립 좌표) 별도 저장
    hw = {}
    for o in occ:
        if not o["base"].startswith("Hex socket head cap screw"):
            continue
        R, t = frames[o["key"]]
        hw[o["key"]] = {"base": o["base"], "frame": classify(o["base"]),
                        "origin_deflected": t.tolist(),
                        "axis_deflected": R[:, 2].tolist(),
                        "x_deflected": R[:, 0].tolist()}
    json.dump(hw, io.open(os.path.join(OUT, "stock_hardware.json"), "w",
                          encoding="utf-8"), indent=1, ensure_ascii=False)

    np.savez_compressed(CACHE, **out)
    json.dump({"PIVOT": PIVOT.tolist(),
               "N": {k: v.tolist() for k, v in N_of.items()}},
              io.open(os.path.join(OUT, "stock_frames.json"), "w", encoding="utf-8"),
              indent=1)
    json.dump(meta, io.open(os.path.join(OUT, "stock_full_meta.json"), "w",
                            encoding="utf-8"), indent=1, ensure_ascii=False)
    return out


def load(neutral=True, frame_map=None):
    """캐시를 읽는다. 기본은 **중립 복원** 상태.

    캐시 자체는 편향 상태(그립좌표)로 저장돼 있고, 프레임 귀속을 바꿔도
    재다운로드 없이 다시 중립화할 수 있다.
    """
    z = np.load(CACHE, allow_pickle=True)
    d = {k: z[k].astype(np.float64) for k in z.files}
    if not neutral:
        return d
    fr = json.load(io.open(os.path.join(OUT, "stock_frames.json"), encoding="utf-8"))
    N_of = {k: np.array(v) for k, v in fr["N"].items()}
    piv = np.array(fr["PIVOT"])
    m = meta()
    out = {}
    for k, P in d.items():
        f = (frame_map or {}).get(k) or m.get(k, {}).get("frame", "GRIP")
        N = N_of.get(f, np.eye(3))
        Q = (P.reshape(-1, 3) - piv) @ N.T + piv
        out[k] = Q.reshape(-1, 3, 3)
    return out


def meta():
    return json.load(io.open(os.path.join(OUT, "stock_full_meta.json"), encoding="utf-8"))


if __name__ == "__main__":
    build(force="--force" in sys.argv)
