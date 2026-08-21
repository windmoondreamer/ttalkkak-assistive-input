"""원본 Joystick 문서의 구조를 cad_dump/ 로 덤프한다 (읽기 전용).

    python scripts/dump_structure.py

익명 접근으로 가능한 것: document 정보, element 목록, part studio feature tree, assembly BOM.
401이 나는 항목은 API 키 설정 후 다시 실행하면 채워진다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import ELEMENTS, SOURCE, dwe, session  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "cad_dump")


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)


def main():
    s = session()
    did, wid = SOURCE["did"], SOURCE["wid"]

    def grab(label, path, params=None):
        r = s.get(f"https://cad.onshape.com/api/v6/{path}", params=params, timeout=60)
        print(f"{r.status_code}  {label}")
        return r.json() if r.status_code == 200 else None

    doc = grab("document", f"documents/{did}")
    if doc:
        save("document.json", doc)
    els = grab("elements", f"documents/d/{did}/w/{wid}/elements")
    if els:
        save("elements.json", els)

    for key, eid in ELEMENTS.items():
        if key.startswith("ps_"):
            j = grab(f"features {key}", dwe("partstudios", eid, "features"))
            if j:
                save(f"features_{key[3:]}.json", j)
        elif key.startswith("asm_"):
            j = grab(f"bom {key}", dwe("assemblies", eid, "bom"),
                     {"indented": "true", "multiLevel": "true"})
            if j:
                save(f"bom_{key[4:]}.json", j)


if __name__ == "__main__":
    main()
