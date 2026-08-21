"""Transient GET-like FeatureScript diagnostics for M3 support connectivity."""
from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_i4_retainer as api  # noqa: E402
from eval_live_collision import flat  # noqa: E402


SCRIPT = r'''
function(context is Context, queries is map)
{
    const id = makeId("FgrLCfymF2ioZvN_23");
    const jfd = qContainsPoint(qAllSolidBodies(), vector(-4.8872, 0, -35) * millimeter);
    const jad = qContainsPoint(qAllSolidBodies(), vector(4.8859, 0, -35) * millimeter);
    const ring = qCreatedBy(id + "ring", EntityType.BODY);
    const beamN = qCreatedBy(id + "beam-1", EntityType.BODY);
    const beamP = qCreatedBy(id + "beam1", EntityType.BODY);
    return {
        "ringCount" : size(evaluateQuery(context, ring)),
        "beamNCount" : size(evaluateQuery(context, beamN)),
        "beamPCount" : size(evaluateQuery(context, beamP)),
        "ringJfD" : evDistance(context, { "side0" : ring, "side1" : jfd }),
        "ringJaD" : evDistance(context, { "side0" : ring, "side1" : jad }),
        "ringBeamN" : evDistance(context, { "side0" : ring, "side1" : beamN }),
        "ringBeamP" : evDistance(context, { "side0" : ring, "side1" : beamP })
        , "ringJfDCollision" : evCollision(context, { "tools" : ring, "targets" : jfd })
        , "beamNJfDCollision" : evCollision(context, { "tools" : beamN, "targets" : jfd })
    };
}
'''


def main():
    output = api.request(
        "POST", f"partstudios/d/{api.DID}/w/{api.WID}/e/{api.EID}/featurescript",
        {"script": SCRIPT},
    )
    decoded = flat(output.get("result")) if output.get("result") is not None else output
    print(json.dumps(decoded, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
