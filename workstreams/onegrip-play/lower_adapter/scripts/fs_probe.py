"""FeatureScript 런타임 오류 진단기.

Onshape 는 feature 상태를 ERROR 로만 알려주고 메시지를 주지 않는다.
이 스크립트는 같은 코드를 /featurescript 평가 엔드포인트에서 돌려 실제 예외 메시지를 얻는다.

    python lower_adapter/scripts/fs_probe.py "<expr>"

`<expr>` 는 익명 함수 본문. 상수/헬퍼는 OneGrip_LowerAdapter.fs 에서 그대로 가져온다.
GET/POST 모두 평가용이며 Part Studio 형상을 바꾸지 않는다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from onshape.client import BASE, session          # noqa: E402
from onshape import write_client as wc            # noqa: E402

FS_PATH = os.path.join(ROOT, "lower_adapter", "cad", "OneGrip_LowerAdapter.fs")
TARGET = os.path.join(ROOT, "lower_adapter", "cad_dump", "adapter_target.json")


MARK_UTIL = "//  유틸"
MARK_FEAT = "//  피처"


def split_source():
    """(top-level 함수들, 상수 블록) 으로 나눈다.

    /featurescript 평가 엔드포인트는 top-level 에서 `function` 만 받는다.
    `const` / `enum` / `export` 는 거부하므로 상수는 익명 함수 안으로 넣는다.
    """
    src = io.open(FS_PATH, encoding="utf-8").read()
    src = "\n".join(src.split("\n")[2:])            # FeatureScript 헤더 + import 제거
    head, rest = src.split(MARK_UTIL, 1)
    utils = rest.split(MARK_FEAT, 1)[0]
    a = head.find("export enum AdpStage")
    if a >= 0:
        b = head.find("\n}\n", a)
        head = head[:a] + head[b + 3:]
    consts = "\n".join(l for l in head.split("\n") if not l.lstrip().startswith("//"))
    utils = utils.split("=====\n", 1)[-1]
    return utils, consts


def run(expr):
    t = json.load(io.open(TARGET, encoding="utf-8"))
    utils, consts = split_source()
    script = (utils + "\nfunction(context is Context, queries) {\n"
              + consts + "\n" + expr + "\n}\n")
    r = session().post(
        f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{t['ps_eid']}/featurescript",
        json={"script": script}, timeout=300)
    j = r.json()
    notices = j.get("notices", [])
    if notices:
        for n in notices:
            st = (n.get("stackTrace") or [{}])
            loc = st[0] if st else {}
            print("[%s] line %s col %s" % (n.get("type"), loc.get("line"), loc.get("column")))
            print("   ", n.get("message"))
            for fr in st[1:4]:
                print("    at line", fr.get("line"))
        return False
    print("OK  result =", json.dumps(j.get("result"))[:300])
    for c in j.get("console", "").split("\n")[:20]:
        if c.strip():
            print("   |", c)
    return True


if __name__ == "__main__":
    run(sys.argv[1])
