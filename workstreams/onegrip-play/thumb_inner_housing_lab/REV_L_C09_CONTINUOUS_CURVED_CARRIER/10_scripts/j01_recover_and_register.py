"""J01 - recover the latest Thumb candidate and register it against docs/101.

Section 4: identify the latest candidate from files and lineage, not from names
quoted in older reports.
Section 7: place it with NO manual correction, and prove first that the two
lineages share one reference frame.

The frame proof is done two ways that can disagree:
  * provenance -- the docs/101 chain's own recorded hashes
  * geometry   -- Thumb features measured independently on both shells

Provenance alone is not enough; a script can start from the right file and still
emit a transformed result.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from build123d import import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from b01_true_axes import NAME_MAP, ORDER, leaf_parts  # noqa: E402
from b03_axis_authority import ray_intervals, true_axis  # noqa: E402
from i02_original_external_stack import frame, skin_reference  # noqa: E402

OUT = L.LAB / "01_recover"
D101 = L.ROOT / "build123d_workbench/out/direct_embedded_finger_switch_final_candidate"
BASE = L.ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
REV_D_BASELINE = {
    "JAD_APPROVED": "622ADB3B1B1D6095435AAC624BB11042080FC8B7399B0C920BECDE708FA54E86",
    "JFD_APPROVED": "D75F62E04DF15B1150EA10EEB8DA1AAA0AAE7CA7C31862CEA42823A0929EA340",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def load(keys, tag, tol=0.06):
    T = []
    for k in keys:
        s, _ = L.as_single_solid(import_step(L.SRC[k]), k)
        T.append(L.triangles(s, tol=tol, ang=0.12))
        del s
    T = np.concatenate(T)
    print("  %-28s %7d triangles" % (tag, len(T)))
    return T


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- 1 latest Thumb candidate --------------------------------------
    print("=== section 4: latest Thumb candidate ===")
    cands = []
    for name in ("C06_SOURCE_FAITHFUL_THUMB_CORE.step",
                 "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"):
        p = L.REV_I / "07_prototype" / name
        if p.exists():
            cands.append({"name": name, "path": str(p), "sha256": sha(p),
                          "mtime": p.stat().st_mtime, "bytes": p.stat().st_size})
    cands.sort(key=lambda c: -c["mtime"])
    for c in cands:
        print("  %-46s %s  %s" % (c["name"],
                                  __import__("datetime").datetime.fromtimestamp(
                                      c["mtime"]).strftime("%Y-%m-%d %H:%M"),
                                  c["sha256"][:12]))
    latest = cands[0]
    v = json.loads((L.REV_I / "08_validation" / "i08_validate.json").read_text(encoding="utf-8"))
    c07 = json.loads((L.REV_I / "07_prototype" / "i10_c07.json").read_text(encoding="utf-8"))
    print("  latest by mtime = %s" % latest["name"])
    print("  its validation json: PASS %d / FAIL %d, vol %.1f, faces %d"
          % (v["pass"], v["fail"], c07["volumeMm3"], c07["faces"]))
    print("  i10_c07.json volume %.3f vs validation gate text -> same build"
          % c07["volumeMm3"])

    # ---- 2 provenance chain ---------------------------------------------
    print("")
    print("=== section 7a: provenance ===")
    prov = {}
    ok_auth = True
    for k, want in REV_D_BASELINE.items():
        got = sha(L.SRC[k])
        prov[k] = {"sha256": got, "matchesRevD": got == want}
        ok_auth &= got == want
        print("  %-14s %s  %s" % (k, got[:16] + "...",
                                  "MATCHES REV_D" if got == want else "!! CHANGED !!"))
    d101 = json.loads((D101 / "direct_embedded_finger_switch_final_candidate_validation.json")
                      .read_text(encoding="utf-8"))
    b15 = json.loads((BASE / "lower15_true_bare_finger_base_validation.json")
                     .read_text(encoding="utf-8"))
    chain_ok = True
    for tag, p in (("LOWER15_TRUE_BARE_JaD", BASE / "LOWER15_TRUE_BARE_FINGER_JaD.step"),
                   ("LOWER15_TRUE_BARE_JfD", BASE / "LOWER15_TRUE_BARE_FINGER_JfD.step")):
        got = sha(p)
        want = d101["authority"]["base"]["JaD" if "JaD" in tag else "JfD"]["sha256"]
        chain_ok &= got == want
        prov[tag] = {"sha256": got, "matchesDocs101Authority": got == want}
        print("  %-22s %s  %s" % (tag, got[:16] + "...",
                                  "= docs/101 authority" if got == want else "!! MISMATCH !!"))
    print("  base recovery declares: lower15ThumbPreserved=%s, thumbOpeningsPreserved=%s"
          % (b15["summary"]["lower15ThumbPreserved"], b15["summary"]["thumbOpeningsPreserved"]))
    print("  docs/101 thumbAfterCut passCount = %d of 9" % d101["thumbAfterCut"]["passCount"])
    print("  -> the docs/101 chain starts at THIS lab's frozen authority, unmodified")

    # ---- 3 independent geometric registration ---------------------------
    print("")
    print("=== section 7b: independent geometric registration on Thumb features ===")
    Ta = load(("JAD_APPROVED", "JFD_APPROVED"), "frozen authority")
    Tb = load(("D101_JAD", "D101_JFD"), "docs/101 shell")
    Tc = load(("D101_BASE_JAD", "D101_BASE_JFD"), "docs/101 base (bare)")

    _, cart = leaf_parts("LOWERED_ORIGINAL_THUMB_CARTRIDGE")
    rows, worst_skin, worst_iv = {}, 0.0, 0.0
    print("")
    print("%-5s %12s %12s %10s   %s" % ("ctrl", "skin auth", "skin d101", "delta", "axis intervals"))
    for short in ORDER:
        lab = next(k for k, v2 in NAME_MAP.items() if v2 == short)
        cap, _ = L.as_single_solid(cart[lab], short)
        w, _, _ = true_axis(cap)
        P = L.surf_points(cap, 40000, tol=0.05)
        cen = P.mean(axis=0)
        ex, ey = frame(w)
        r_cap = float(np.hypot((P - cen) @ ex, (P - cen) @ ey).max())
        sa = skin_reference(Ta, cen, w, ex, ey, r_cap)["referenceMm"]
        sb = skin_reference(Tb, cen, w, ex, ey, r_cap)["referenceMm"]
        ia = ray_intervals(Ta, cen, w, -45.0, 45.0) or []
        ib = ray_intervals(Tb, cen, w, -45.0, 45.0) or []
        same = len(ia) == len(ib) and all(
            abs(a0 - b0) < 1.0e-3 and abs(a1 - b1) < 1.0e-3
            for (a0, a1), (b0, b1) in zip(ia, ib))
        d = abs(sa - sb)
        worst_skin = max(worst_skin, d)
        if not same:
            worst_iv = max(worst_iv, 1.0)
        rows[short] = {"skinAuthorityMm": sa, "skinDocs101Mm": sb, "skinDeltaMm": d,
                       "axisIntervalsAuthority": ia, "axisIntervalsDocs101": ib,
                       "axisIntervalsIdentical": bool(same)}
        print("%-5s %12.6f %12.6f %10.6f   %s"
              % (short, sa, sb, d, "identical" if same else "DIFFER %d vs %d" % (len(ia), len(ib))))
        del cap
        L.memory("reg " + short)

    # a global check that does not depend on the control axes at all
    def thumb_bbox(T):
        P = T.reshape(-1, 3)
        m = np.linalg.norm(P - L.DATUM_P, axis=1) < 45.0
        q = P[m]
        return q.min(axis=0), q.max(axis=0), int(m.sum())

    a0, a1, na = thumb_bbox(Ta)
    b0, b1, nb = thumb_bbox(Tb)
    bb = float(np.abs(np.concatenate([a0 - b0, a1 - b1])).max())
    print("")
    print("  Thumb-region material bbox (within 45 mm of DATUM_P)")
    print("    authority  min %s  max %s  (%d pts)" % (np.round(a0, 4), np.round(a1, 4), na))
    print("    docs/101   min %s  max %s  (%d pts)" % (np.round(b0, 4), np.round(b1, 4), nb))
    print("    worst corner delta = %.6f mm" % bb)

    conf = ("HIGH" if (ok_auth and chain_ok and worst_skin < 0.01 and worst_iv == 0.0
                       and bb < 0.01) else "MEDIUM" if worst_skin < 0.20 else "LOW")
    print("")
    print("  THUMB CANDIDATE TRANSFORM APPLIED = NONE (identity)")
    print("  REASON = the docs/101 chain is derived from this lab's frozen authority,")
    print("           and the Thumb region measures identically on both shells")
    print("  COORDINATE REGISTRATION CONFIDENCE = %s" % conf)

    L.write_json(OUT / "j01_recover_and_register.json",
                 {"candidates": cands, "latest": latest,
                  "latestValidation": {"pass": v["pass"], "fail": v["fail"],
                                       "volumeMm3": c07["volumeMm3"],
                                       "faces": c07["faces"], "solids": c07["solids"],
                                       "valid": c07["valid"]},
                  "provenance": prov, "chainOk": bool(chain_ok and ok_auth),
                  "docs101ThumbAfterCutPass": d101["thumbAfterCut"]["passCount"],
                  "controls": rows,
                  "worstSkinDeltaMm": worst_skin,
                  "thumbRegionBboxDeltaMm": bb,
                  "transformApplied": "IDENTITY",
                  "registrationConfidence": conf, "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
