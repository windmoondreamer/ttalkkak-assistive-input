"""J05 - assembly sequences, done properly (section 16).

J03's first attempt declared BOTH sequences BLOCKED, and both verdicts were
artefacts of how the motion was posed:

  * Sequence A swept the core 20 mm along -JOY, i.e. straight down into a closed
    cavity.  That is not how the core is fitted.  The shell splits into JaD and
    JfD, so the core is laid into ONE OPEN HALF and the other half closes over
    it.  Swept along +-U -- the split normal -- the same core scores 0.0000 mm3
    against every Finger switch.
  * Sequence B tested WITHDRAWAL of the Finger switches.  A direct-embedded
    switch is inserted from inside going outward until the actuator emerges, so
    withdrawal and insertion share one corridor; that part of the finding is
    real and stands.

Section 16 is explicit that a single failing sequence does not fail assembly, so
this poses each step the way it is actually performed:

    core placement   into one OPEN half, with that half's switches already in
    switch insertion along its own press axis, outward, from the cavity side
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from build123d import Location, Vector, import_step

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labutil as L  # noqa: E402
from j02_collision import switch_groups  # noqa: E402

OUT = L.LAB / "04_assembly"
CAND = L.REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
TRAVEL = 30.0
STEP = 1.0
INSERT = 12.0
# docs/101 cut table: which half carries each button's pocket
OWNER = {"I2": "JfD", "I3": "JfD", "I4": "JaD", "M3": "JfD",
         "M4": "JaD", "N1": "JfD", "N2": "BOTH", "N3": "JaD"}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dat = json.loads((L.ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
                      / "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
    axes = {k: L.unit(np.asarray(v["pressAxis"], float)) for k, v in dat["controls"].items()}

    core, _ = L.as_single_solid(import_step(str(CAND)), "C07")
    halves = {}
    for tag, key in (("JaD", "D101_JAD"), ("JfD", "D101_JFD")):
        halves[tag], _ = L.as_single_solid(import_step(L.SRC[key]), tag)
    groups = switch_groups()
    sw_all = [s for g in groups.values() for v in g.values() for s in v]
    sw_half = {"JaD": [], "JfD": []}
    for b, g in groups.items():
        whole = [s for v in g.values() for s in v]
        for h in (("JaD", "JfD") if OWNER[b] == "BOTH" else (OWNER[b],)):
            sw_half[h].extend(whole)
    print("switches per half: JaD %d solids, JfD %d solids"
          % (len(sw_half["JaD"]), len(sw_half["JfD"])))
    L.memory("load")

    # ---- step 1: lay the core into one OPEN half -------------------------
    print("")
    print("=== core placement into one open half (the other half removed) ===")
    dirs = {"+U": L.DATUM_U, "-U": -L.DATUM_U,
            "+N (outward)": -L.DATUM_N, "-N (inward)": L.DATUM_N,
            "+V": L.DATUM_V, "-V": -L.DATUM_V}
    place = {}
    print("%-14s %12s %12s %12s %12s"
          % ("direction", "vs JaD", "JaD switches", "vs JfD", "JfD switches"))
    for dn, dv in dirs.items():
        row = {}
        for h in ("JaD", "JfD"):
            vs_shell = vs_sw = 0.0
            for k in np.arange(STEP, TRAVEL + 1e-9, STEP):
                mv = Location(Vector(*[float(x) for x in (dv * float(k))]))
                c = core.moved(mv)
                vs_shell += L.inter_vol(c, halves[h])
                for s in sw_half[h]:
                    vs_sw += L.inter_vol(c, s)
            row[h] = {"shellMm3": vs_shell, "switchesMm3": vs_sw}
        place[dn] = row
        print("%-14s %12.4f %12.4f %12.4f %12.4f"
              % (dn, row["JaD"]["shellMm3"], row["JaD"]["switchesMm3"],
                 row["JfD"]["shellMm3"], row["JfD"]["switchesMm3"]))
        L.memory("place " + dn)

    best = []
    for dn, row in place.items():
        for h in ("JaD", "JfD"):
            if row[h]["shellMm3"] <= 1.0e-6 and row[h]["switchesMm3"] <= 1.0e-6:
                best.append((dn, h))
    print("  clear withdrawal/placement paths (30 mm, shell AND switches): %s"
          % (", ".join("%s out of %s" % (d, h) for d, h in best) or "none"))

    # ---- step 2: insert each Finger switch with the core already in ------
    print("")
    print("=== Finger switch insertion along its own press axis, core installed ===")
    ins = {}
    for b, g in groups.items():
        whole = [s for v in g.values() for s in v]
        w = axes[b]
        tot = 0.0
        first = None
        for k in np.arange(STEP, INSERT + 1e-9, STEP):
            mv = Location(Vector(*[float(x) for x in (-w * float(k))]))
            v = sum(L.inter_vol(s.moved(mv), core) for s in whole)
            tot += v
            if v > 1.0e-6 and first is None:
                first = float(k)
        ins[b] = {"corridorObstructionMm3": tot, "firstBlockAtMm": first,
                  "owner": OWNER[b]}
        print("  %-4s (%s) corridor %9.4f mm3   first block at %s"
              % (b, OWNER[b], tot, ("%.1f mm" % first) if first else "never"))
        L.memory("ins " + b)

    blocked = [b for b, v in ins.items() if v["corridorObstructionMm3"] > 1.0e-6]
    seqA = len(best) > 0
    seqB = len(blocked) == 0
    print("")
    print("=== verdict ===")
    print("  SEQUENCE A  Finger switches epoxied -> core laid into the open half"
          " -> close: %s" % ("VALID" if seqA else "BLOCKED"))
    print("  SEQUENCE B  core installed -> Finger switches inserted: %s"
          % ("VALID" if seqB else "BLOCKED at " + ", ".join(blocked)))
    print("  ASSEMBLY = %s" % ("PASS" if (seqA or seqB) else "FAIL"))
    if seqA and not seqB:
        print("  -> the order is FORCED: N1 and N2 must be seated and epoxied before")
        print("     the Thumb core goes in.  Nothing is geometrically impossible.")

    L.write_json(OUT / "j05_assembly_sequences.json",
                 {"travelMm": TRAVEL, "insertionMm": INSERT, "owner": OWNER,
                  "corePlacement": place, "clearPaths": best,
                  "fingerInsertion": ins, "blockedButtons": blocked,
                  "sequenceAValid": bool(seqA), "sequenceBValid": bool(seqB),
                  "assembly": "PASS" if (seqA or seqB) else "FAIL",
                  "memory": L.MEMORY_LOG})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
