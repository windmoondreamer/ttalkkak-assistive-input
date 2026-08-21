"""인증 상태 확인 + 이전 401 항목 재조회 (READ ONLY).

GET 요청만 수행한다. POST/PUT/DELETE 를 절대 사용하지 않는다.
API 키 값은 어떤 경우에도 출력하지 않는다.

    python scripts/check_auth.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import BASE, ELEMENTS, SOURCE, session  # noqa: E402

D, W = SOURCE["did"], SOURCE["wid"]
PS = ELEMENTS["ps_Base"]
PS_J = ELEMENTS["ps_Joystick"]
ASM = ELEMENTS["asm_Complete"]
VAR = ELEMENTS["var_studio"]

# (라벨, 경로, 익명 접근 시 결과)
PROBES = [
    ("documents/{did}",            f"documents/{D}", 200),
    ("elements",                   f"documents/d/{D}/w/{W}/elements", 200),
    ("partstudio features (Base)", f"partstudios/d/{D}/w/{W}/e/{PS}/features", 200),
    ("assembly bom (Complete)",    f"assemblies/d/{D}/w/{W}/e/{ASM}/bom", 200),
    ("parts (Base)",               f"parts/d/{D}/w/{W}/e/{PS}", 401),
    ("parts (Joystick)",           f"parts/d/{D}/w/{W}/e/{PS_J}", 401),
    ("bodydetails (Base)",         f"partstudios/d/{D}/w/{W}/e/{PS}/bodydetails", 401),
    ("bodydetails (Joystick)",     f"partstudios/d/{D}/w/{W}/e/{PS_J}/bodydetails", 401),
    ("massproperties (Base)",      f"partstudios/d/{D}/w/{W}/e/{PS}/massproperties", 401),
    ("massproperties (Joystick)",  f"partstudios/d/{D}/w/{W}/e/{PS_J}/massproperties", 401),
    ("configuration (Joystick)",   f"partstudios/d/{D}/w/{W}/e/{PS_J}/configuration", 401),
    ("assembly definition",        f"assemblies/d/{D}/w/{W}/e/{ASM}", 401),
    ("variables (Variable Studio)", f"variables/d/{D}/w/{W}/e/{VAR}/variables", 401),
    ("versions",                   f"documents/d/{D}/versions", 401),
]


def main():
    s = session()
    authed = bool(s.auth)
    print("=" * 78)
    print("ONSHAPE READ-ONLY 인증 확인   (GET 전용)")
    print("=" * 78)
    print(f"  base url        : {BASE}")
    print(f"  ACCESS_KEY      : {'설정됨' if os.environ.get('ONSHAPE_ACCESS_KEY') else '없음'}")
    print(f"  SECRET_KEY      : {'설정됨' if os.environ.get('ONSHAPE_SECRET_KEY') else '없음'}")
    print(f"  auth 적용 여부  : {'YES (basic auth)' if authed else 'NO (익명)'}")

    # 인증 자체 확인: 내 사용자 세션 조회
    r = s.get(f"{BASE}/users/sessioninfo", timeout=30)
    print(f"\n  GET /users/sessioninfo -> HTTP {r.status_code}")
    if r.status_code == 200:
        j = r.json()
        print(f"    인증 주체 : {j.get('name')} ({j.get('email')})")
        print(f"    상태      : 인증 성공")
    else:
        print(f"    상태      : 인증 실패 — 키를 확인하세요")

    print(f"\n{'-'*78}")
    print(f"  {'endpoint':<30} {'익명':>6} {'인증':>6}   {'판정':<12} note")
    print(f"{'-'*78}")
    newly, still = [], []
    for label, path, anon in PROBES:
        try:
            r = s.get(f"{BASE}/{path}", timeout=60)
            code = r.status_code
            note = ""
            if code == 200:
                note = f"{len(r.content)//1024} KB"
        except Exception as ex:
            code, note = "ERR", str(ex)[:40]
        if anon == 401 and code == 200:
            verdict = "NEW OK"
            newly.append(label)
        elif anon == 401 and code != 200:
            verdict = "여전히 불가"
            still.append((label, code))
        elif code == 200:
            verdict = "유지"
        else:
            verdict = "회귀"
        print(f"  {label:<30} {anon:>6} {code:>6}   {verdict:<12} {note}")

    print(f"\n{'-'*78}")
    print(f"  새로 열린 항목 : {len(newly)} / {sum(1 for p in PROBES if p[2]==401)}")
    for n in newly:
        print(f"      + {n}")
    if still:
        print(f"  여전히 불가    : {len(still)}")
        for n, c in still:
            print(f"      - {n}  (HTTP {c})")


if __name__ == "__main__":
    main()
