"""Onshape read-only client for OneGrip Play.

원본 Joystick 문서는 public(ANONYMOUS_ACCESS)이라 인증 없이 GET이 가능하다.
단, 일부 엔드포인트(parts / bodydetails / massproperties / assemblies definition /
configuration / variables / versions)는 익명으로 401을 반환하므로 API 키가 필요하다.

키가 있으면 .env 또는 환경변수로 주입한다:
    ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY
키가 없으면 익명으로 동작한다.

이 모듈은 GET만 수행한다. 쓰기 메서드를 추가하지 말 것.
"""
import os
import requests

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path=None):
    """.env 를 os.environ 에 로드한다. 이미 설정된 환경변수는 덮어쓰지 않는다.

    값은 절대 출력하지 않는다.
    """
    path = path or os.path.join(_ROOT, ".env")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v and k not in os.environ:
                os.environ[k] = v
    return True


load_env()

BASE = os.environ.get("ONSHAPE_BASE_URL", "https://cad.onshape.com/api/v6")

# 원본 DIY Joystick CAD (읽기 전용 취급)
SOURCE = {
    "did": "143d2aa6a2cf1c2ed82be979",
    "wid": "f0ab4fb72b468eeb38cc7a63",
    "default_eid": "212ec93359aad06aa2bd2fad",
}

# 조회로 확인된 element id (2026-08-18 기준)
ELEMENTS = {
    "ps_Base": "2fae0d1a0124e696279efed6",
    "ps_Joystick": "212ec93359aad06aa2bd2fad",
    "ps_PushBtn": "7b9ddcd8027f0e95b934afc3",
    "ps_HW504_B": "c349d3fc572261fbfb95897f",
    "ps_Magnet": "bc18608af20c3b08c0ff7444",
    "ps_Hall_effect_sensor": "22b139a2653e397a94b9d9e1",
    "ps_625zz_bearing": "88241e40294795eaf2206863",
    "ps_ArduinoProMicro": "2a2504992e329ba63eccf9fc",
    "asm_Complete": "b844c9f23a7beb9d72779e4f",
    "asm_Base": "f28515c05753a2a56c83f653",
    "asm_Joystick": "14f545ef519ae3e58e12f61f",
    "asm_Bearing": "6fafe2b4bb803cc32e160661",
    "asm_Hall_effect_sensor": "2d9f69fcbaa034c7b028471c",
    "var_studio": "557f940136df10b235ef6ccd",
}


def session():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    ak, sk = os.environ.get("ONSHAPE_ACCESS_KEY"), os.environ.get("ONSHAPE_SECRET_KEY")
    if ak and sk:
        s.auth = (ak, sk)          # Onshape는 API 키의 basic auth를 허용한다
    return s


def get(path, params=None, s=None):
    """GET {BASE}/{path}. 401이면 인증이 필요한 엔드포인트다."""
    s = s or session()
    r = s.get(f"{BASE}/{path.lstrip('/')}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def dwe(kind, eid, sub="", did=None, wid=None):
    """part studio / assembly 경로 조립 헬퍼."""
    did = did or SOURCE["did"]
    wid = wid or SOURCE["wid"]
    tail = f"/{sub.lstrip('/')}" if sub else ""
    return f"{kind}/d/{did}/w/{wid}/e/{eid}{tail}"
