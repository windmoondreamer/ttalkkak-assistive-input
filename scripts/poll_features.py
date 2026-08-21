"""/features GET rate limit 이 풀릴 때까지 폴링해 feature states 를 저장한다 (READ ONLY)."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from onshape.client import BASE, session, load_env
from onshape import write_client as wc

load_env()
D = f"{wc.DID}/w/{wc.WID}/e/{wc.EID_JOYSTICK}"
OUT = os.path.join(os.path.dirname(__file__), "..", "cad_dump", "features_final.json")
deadline = time.time() + 7800
while time.time() < deadline:
    s = session()
    r = s.get(f"{BASE}/partstudios/d/{D}/features", params={"noSketchGeometry": "true"}, timeout=300)
    if r.status_code == 200:
        j = r.json()
        with open(OUT, "w") as f:
            json.dump(j, f)
        st = j.get("featureStates", {})
        from collections import Counter
        c = Counter(v.get("featureStatus") for v in st.values())
        print(f"SUCCESS  feature {len(j.get('features',[]))}개  상태 {dict(c)}", flush=True)
        print(f"  rollbackIndex={j.get('rollbackIndex')} isComplete={j.get('isComplete')}", flush=True)
        sys.exit(0)
    ra = r.headers.get("Retry-After")
    print(f"429  Retry-After={ra}  ({time.strftime('%H:%M:%S')})", flush=True)
    time.sleep(240)
print("TIMEOUT: rate limit 해제 안 됨", flush=True)
sys.exit(1)
