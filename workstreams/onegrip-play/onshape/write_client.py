"""Onshape WRITE 클라이언트 — 승인된 사본 문서 1개로만 쓰기를 제한한다.

사용자 승인 대상 (2026-08-19):
    document  OneGrip_Play_V1   did = a21e64f36bc61df760d4587c
    workspace Main              wid = ef6a7b3ccc45186203e4d2ca
    owner     홍민 윤 (인증 계정과 동일, OWNER)

이 모듈의 모든 쓰기 함수는 did/wid 를 하드코딩된 값과 대조하고,
다르면 예외를 던져 요청 자체를 보내지 않는다.
Adam Simon 원본 문서(143d2aa6a2cf1c2ed82be979)로는 어떤 쓰기도 나갈 수 없다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from onshape.client import BASE, session  # noqa: E402

# ---- 승인된 WRITE 대상 (변경 금지) ----
DID = "a21e64f36bc61df760d4587c"
WID = "ef6a7b3ccc45186203e4d2ca"
EID_JOYSTICK = "425d9199b59cfb1efd9ddc35"     # Joystick Part Studio
EID_BASE = "df9a32f1f239bc71a732f5d3"
FORBIDDEN = {"143d2aa6a2cf1c2ed82be979"}      # Adam Simon 원본

PS = f"partstudios/d/{DID}/w/{WID}/e/{EID_JOYSTICK}"


def _guard(did, wid):
    if did in FORBIDDEN:
        raise RuntimeError(f"차단: 원본 문서로의 쓰기 시도 ({did})")
    if did != DID or wid != WID:
        raise RuntimeError(f"차단: 승인되지 않은 대상 did={did} wid={wid}")


def _url(path):
    return f"{BASE}/{path.lstrip('/')}"


def get(path, params=None):
    r = session().get(_url(path), params=params, timeout=300)
    r.raise_for_status()
    return r.json()


def ps_features(eid=EID_JOYSTICK):
    return get(f"partstudios/d/{DID}/w/{WID}/e/{eid}/features")


def post_feature(feature, eid=EID_JOYSTICK):
    """Part Studio 트리 최하단에 feature 를 append 한다."""
    _guard(DID, WID)
    cur = ps_features(eid)
    body = {
        "feature": feature,
        "serializationVersion": cur.get("serializationVersion"),
        "sourceMicroversion": cur.get("sourceMicroversion"),
        "rejectMicroversionSkew": False,
    }
    r = session().post(_url(f"partstudios/d/{DID}/w/{WID}/e/{eid}/features"),
                       json=body, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"POST feature 실패 {r.status_code}: {r.text[:600]}")
    return r.json()


def delete_feature(feature_id, eid=EID_JOYSTICK):
    """되돌리기용. 방금 추가한 신규 feature 만 지운다."""
    _guard(DID, WID)
    r = session().delete(
        _url(f"partstudios/d/{DID}/w/{WID}/e/{eid}/features/featureid/{feature_id}"),
        timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"DELETE feature 실패 {r.status_code}: {r.text[:400]}")
    return r.json()


def create_version(name, description=""):
    _guard(DID, WID)
    r = session().post(_url("documents/{}/versions".format(DID)),
                       json={"documentId": DID, "workspaceId": WID,
                             "name": name, "description": description},
                       timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"버전 생성 실패 {r.status_code}: {r.text[:400]}")
    return r.json()


def create_part_studio(name):
    """신규 Part Studio element 를 승인된 사본 안에 만든다.

    기존 element 는 건드리지 않는다. 하부 어댑터처럼 상체와 분리된 형상을
    만들 때 쓴다 (derive 없이 만들면 상체를 구조적으로 수정할 수 없다).
    """
    _guard(DID, WID)
    r = session().post(_url(f"partstudios/d/{DID}/w/{WID}"),
                       json={"name": name}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"Part Studio 생성 실패 {r.status_code}: {r.text[:400]}")
    return r.json()


def create_feature_studio(name):
    _guard(DID, WID)
    r = session().post(_url(f"featurestudios/d/{DID}/w/{WID}"),
                       json={"name": name}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"Feature Studio 생성 실패 {r.status_code}: {r.text[:400]}")
    return r.json()


def set_feature_studio_contents(eid, contents):
    _guard(DID, WID)
    r = session().post(_url(f"featurestudios/d/{DID}/w/{WID}/e/{eid}"),
                       json={"contents": contents}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"FS 내용 저장 실패 {r.status_code}: {r.text[:600]}")
    return r.json()


def feature_health(eid=EID_JOYSTICK):
    j = ps_features(eid)
    st = j.get("featureStates", {})
    bad = {k: v.get("featureStatus") for k, v in st.items()
           if v.get("featureStatus") not in ("OK", "INFO")}
    return {
        "count": len(j["features"]),
        "rollbackIndex": j.get("rollbackIndex"),
        "isComplete": j.get("isComplete"),
        "bad": bad,
        "microversion": j.get("sourceMicroversion"),
    }


# ---------- feature JSON 빌더 ----------

def qlist(pid, queries=None):
    return {"btType": "BTMParameterQueryList-148", "parameterId": pid,
            "queries": queries or []}


def enum(pid, name, value):
    return {"btType": "BTMParameterEnum-145", "parameterId": pid,
            "enumName": name, "value": value, "namespace": ""}


def qty(pid, expression):
    return {"btType": "BTMParameterQuantity-147", "parameterId": pid,
            "expression": expression}


def string(pid, value):
    return {"btType": "BTMParameterString-149", "parameterId": pid, "value": value}


def boolean(pid, value):
    return {"btType": "BTMParameterBoolean-144", "parameterId": pid, "value": value}


def _strip_ids(obj):
    """nodeId / featureId 를 제거해 Onshape 가 새로 발급하게 한다."""
    if isinstance(obj, dict):
        return {k: _strip_ids(v) for k, v in obj.items()
                if k not in ("nodeId", "featureId")}
    if isinstance(obj, list):
        return [_strip_ids(v) for v in obj]
    return obj


_VAR_TEMPLATE = None


def _var_template(eid=EID_JOYSTICK):
    """기존 assignVariable 피처를 템플릿으로 캐시한다 (파라미터 27개 전체 확보)."""
    global _VAR_TEMPLATE
    if _VAR_TEMPLATE is None:
        j = ps_features(eid)
        src = next(f for f in j["features"] if f["featureType"] == "assignVariable")
        _VAR_TEMPLATE = _strip_ids(src)
    return json.loads(json.dumps(_VAR_TEMPLATE))


def assign_variable(name, expression, var_type="LENGTH"):
    """assignVariable 피처 JSON. 기존 피처를 복제해 name/type/value 만 교체한다."""
    f = _var_template()
    f["name"] = f"#{name} = {expression}"
    f["suppressed"] = False
    type_field = {"LENGTH": "lengthValue", "ANGLE": "angleValue",
                  "NUMBER": "numberValue", "ANY": "anyValue"}[var_type]
    for p in f["parameters"]:
        pid = p.get("parameterId")
        if pid == "name":
            p["value"] = name
        elif pid == "variableType":
            p["value"] = var_type
        elif pid == "value" or pid == type_field:
            p["expression"] = expression
        elif pid in ("lengthValue", "angleValue", "numberValue", "anyValue"):
            p["expression"] = {"lengthValue": "0 mm", "angleValue": "0 deg",
                               "numberValue": "0", "anyValue": "0"}[pid]
        elif pid == "description":
            p["value"] = "OneGrip Play - finger button (신규)"
    return f
