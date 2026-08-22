"""OneGrip Play — 로컬 build123d 파이프라인 한 번에 실행 (§24, §25).

    .venv-build123d/Scripts/python lower_adapter/local_cad/build.py

순서:  import -> align -> build -> verify -> preview
Onshape API 호출 0건.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "build123d")

STEPS = [
    ("레퍼런스 임포트 / 왕복", "import_reference.py"),
    ("좌표계 정합",            "align_reference.py"),
    ("인체공학 외피 생성",      "ergo_shell.py"),
    ("조립 프리뷰",            "assembly_preview.py"),
    ("로컬 검증",              "verify_geometry.py"),
    ("프리뷰 렌더",            "preview_render.py"),
]


def main():
    only = sys.argv[1:] or None
    rc = 0
    for label, script in STEPS:
        if only and not any(o in script for o in only):
            continue
        print("\n" + "#" * 78)
        print(f"# {label}   ({script})")
        print("#" * 78)
        r = subprocess.run([sys.executable, os.path.join(B, script)])
        if r.returncode != 0:
            print(f"\n[{script}] 종료 코드 {r.returncode}")
            rc = r.returncode
            if r.returncode >= 2:      # 레퍼런스 없음 등 치명적
                break
    return rc


if __name__ == "__main__":
    sys.exit(main())
