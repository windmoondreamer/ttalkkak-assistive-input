"""컨포멀 하우징 빌드를 FeatureScript **평가 엔드포인트**에서 단계별로 실행해
어느 연산이 실패하는지 찾는다.

`GET /features` 가 429 일 때 유일하게 남는 진단 경로다.
평가 엔드포인트는 형상을 저장하지 않으므로 CAD WRITE 가 아니다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from onshape.client import BASE, session            # noqa: E402
from onshape import write_client as wc              # noqa: E402

OUT = os.path.join(ROOT, "lower_adapter", "cad_dump")
FS = os.path.join(ROOT, "lower_adapter", "cad", "OneGrip_Conformal.fs")


def prelude():
    """생성 FS 에서 상수 + 헬퍼 함수만 뽑는다 (feature 정의 제외)."""
    src = io.open(FS, encoding="utf-8").read()
    head = src[:src.index("// ---------- 피처 ----------")]
    head = head.replace("FeatureScript 2878;\n", "")
    # 평가 엔드포인트는 이미 std 를 import 한 상태이고 import 문을 허용하지 않는다
    head = re.sub(r"^import\(.*$", "", head, flags=re.M)
    # 평가 스크립트는 최상위 export 를 허용하지 않는다
    head = head.replace("export enum", "enum").replace("export const", "const")
    return head


BODY = r"""
function trace(context is Context, id is Id)
{
    print("== outer bands ==\n");
    mkRound(context, id + "o0", OUTER[0], 10 * millimeter,
        OUTER_Z[0] * millimeter, OUTER_Z[1] * millimeter);
    const hs = qBodyType(qCreatedBy(id + "o0" + "a", EntityType.BODY), BodyType.SOLID);
    print("  o0 bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");
    for (var i = 1; i < size(OUTER); i += 1)
    {
        const bid = id + ("o" ~ i);
        mkRound(context, bid, OUTER[i], 10 * millimeter,
            OUTER_Z[i] * millimeter, OUTER_Z[i + 1] * millimeter);
        join(context, bid + "j", hs, bid + "a");
        print("  o" ~ i ~ " bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");
    }
    print("== tail outer ==\n");
    mkRound(context, id + "to", TAIL_OUT, 8 * millimeter,
        TAIL_OUT_Z[0] * millimeter, TAIL_OUT_Z[1] * millimeter);
    join(context, id + "toj", hs, id + "to" + "a");
    print("  bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");

    print("== skirts ==\n");
    mkRound(context, id + "sk", SKIRT, 10 * millimeter,
        (GROUND_ZMIN - 20) * millimeter, CAR_TOP * millimeter);
    join(context, id + "skj", hs, id + "sk" + "a");
    print("  main skirt bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");
    mkRound(context, id + "tsk", TAIL_SKIRT, 8 * millimeter,
        (GROUND_ZMIN - 20) * millimeter, TAIL_OUT_Z[0] * millimeter);
    join(context, id + "tskj", hs, id + "tsk" + "a");
    print("  tail skirt bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");

    print("== ground cut ==\n");
    halfSpace(context, id + "g", N_GROUND, D_GROUND * millimeter);
    cut(context, id + "gc", hs, id + "g" + "ex");
    print("  bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");

    print("== knee cut ==\n");
    const kth = 34 * degree;
    const ky = 18 * millimeter;
    const yv = vector(0.0, 1.0, 0.0);
    const uu = normalize(yv - dot(yv, N_GROUND) * N_GROUND);
    const nk = -sin(kth) * uu + cos(kth) * N_GROUND;
    const zk = (D_GROUND * millimeter - N_GROUND[1] * ky) / N_GROUND[2];
    const dk = dot(vector(0 * millimeter, ky, zk), nk);
    print("  nk=" ~ toString(nk) ~ " dk=" ~ toString(dk) ~ "\n");
    halfSpace(context, id + "k", nk, dk);
    cut(context, id + "kc", hs, id + "k" + "ex");
    print("  bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");

    print("== cavity ==\n");
    for (var i = 0; i < size(CAV); i += 1)
    {
        const cid = id + ("c" ~ i);
        mkRound(context, cid, CAV[i], 6 * millimeter,
            CAV_Z[i] * millimeter, CAV_Z[i + 1] * millimeter);
        cut(context, cid + "c", hs, cid + "a");
        print("  cav" ~ i ~ " bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");
    }
    mkRound(context, id + "tc", TAIL_CAV, 5 * millimeter,
        TAIL_CAV_Z[0] * millimeter, TAIL_CAV_Z[1] * millimeter);
    cut(context, id + "tcc", hs, id + "tc" + "a");
    print("  tail cav bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");

    print("== carrier opening ==\n");
    mkRound(context, id + "co", CAR_OPEN, 8 * millimeter,
        (GROUND_ZMIN - 30) * millimeter, CAR_TOP * millimeter);
    cut(context, id + "coc", hs, id + "co" + "a");
    print("  bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");
    mkRound(context, id + "tco", TAIL_CAR_OPEN, 6 * millimeter,
        (GROUND_ZMIN - 30) * millimeter, TAIL_CAV_Z[0] * millimeter);
    cut(context, id + "tcoc", hs, id + "tco" + "a");
    print("  bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");

    print("== usb port ==\n");
    mkBox(context, id + "usb",
        vector(USB_CX * millimeter, (TAIL_CAV[3] - 150) * millimeter),
        vector(USB_W * millimeter, 300 * millimeter), USB_Z0 * millimeter,
        USB_Z1 * millimeter);
    cut(context, id + "usbc", hs, id + "usb");
    print("  bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");

    print("== inserts ==\n");
    for (var s = 0; s < size(SCREWS); s += 1)
    {
        const iid = id + ("ins" ~ s);
        const px = SCREWS[s][0] * millimeter;
        const py = SCREWS[s][1] * millimeter;
        fCylinder(context, iid, {
                    "topCenter" : vector(px, py, (CAR_TOP + INSERT_L) * millimeter),
                    "bottomCenter" : vector(px, py, (CAR_TOP - 1) * millimeter),
                    "radius" : INSERT_D / 2 * millimeter
                });
        cut(context, iid + "c", hs, iid);
        print("  ins" ~ s ~ " ok\n");
    }
    print("DONE bodies=" ~ size(evaluateQuery(context, hs)) ~ "\n");
}

function(context is Context, queries is map)
{
    trace(context, newId() + "T");
    return 1;
}
"""


def main():
    T = json.load(io.open(os.path.join(OUT, "conformal_target.json"), encoding="utf-8"))
    script = prelude() + BODY
    r = session().post(
        f"{BASE}/partstudios/d/{wc.DID}/w/{wc.WID}/e/{T['ps_eid']}/featurescript",
        json={"script": script, "queries": {}}, timeout=600)
    print("HTTP", r.status_code)
    j = r.json() if r.status_code == 200 else None
    if j is None:
        print(r.text[:2000])
        return
    print("---- console ----")
    print(j.get("console", "")[:6000])
    for n in j.get("notices", [])[:20]:
        print("NOTICE", n.get("level"), n.get("message"))


if __name__ == "__main__":
    main()
