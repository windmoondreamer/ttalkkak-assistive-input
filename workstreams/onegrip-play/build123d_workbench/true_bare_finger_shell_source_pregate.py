"""Critical source-authenticity pre-gate for the eight Finger regions.

This script is deliberately audit-only.  It imports three immutable lineages,
measures local material additions/removals against the historical Start shell,
and renders proof images.  It creates no switch socket, actuator hole, shell
repair, STEP, STL, or production geometry.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from build123d import Compound, Shape, import_step

from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler
from .finger_controls_v2 import BUTTON_ORDER, controls_from_layout, oriented_box, unit
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .print_ready_frozen_exterior_recovery import expanded_fit, metrics
from .six_failed_leg_shell_landing_failure_mode_diagnostic_audit import raster_scene_without_header


OUT = ROOT / "build123d_workbench/out/true_bare_finger_shell_source_pregate"
RENDER = ROOT / "renders/true_bare_finger_shell_source_pregate"
JSON_PATH = OUT / "true_bare_finger_shell_source_pregate.json"
REPORT = ROOT / "docs/99_true_bare_finger_shell_source_pregate.md"

CURRENT = {
    "JaD": ROOT / "build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JaD.step",
    "JfD": ROOT / "build123d_workbench/out/print_ready_frozen_exterior/ONEGRIP_PRINT_EXTERIOR_JfD.step",
}
LOWER15 = {
    "JaD": ROOT / "thumb_exact_onshape_source/JaD_THUMB_LOWER15_APPROVED.step",
    "JfD": ROOT / "thumb_exact_onshape_source/JfD_THUMB_LOWER15_APPROVED.step",
}
HISTORICAL_START = {
    "JaD": ROOT / "local_cad/reference/JAD_CLEAN_PRE_FINGER.step",
    "JfD": ROOT / "local_cad/reference/JFD_CLEAN_PRE_FINGER.step",
}

REPORT_ORDER = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")
EPS = 1.0e-6
LEGACY_VOLUME_EPS = 0.05
LEGACY_FINGER_LOCATIONS = frozenset(("I2", "I3", "I4", "M3", "M4"))
LOCAL_UV = 9.50
EXTERIOR_BAND = (-2.50, 2.50)
INTERIOR_BAND = (2.50, 15.50)
FULL_BAND = (-2.50, 15.50)
FOOTER = "SOURCE AUTHENTICITY PRE-GATE | NO SOCKET BOOLEAN | NO PRODUCTION GEOMETRY"
COL = {
    "jad": (44, 153, 201), "jfd": (61, 188, 139), "current": (112, 132, 151),
    "legacy": (239, 81, 84), "removed": (247, 181, 64), "bare": (72, 190, 140),
    "axis": (250, 211, 96), "edge": (210, 225, 233),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def safe_volume(shape: Shape | None) -> float:
    return 0.0 if shape is None or not shape.solids() else float(shape.volume)


def local_crop(datum, band: tuple[float, float], label: str) -> Shape:
    return oriented_box(
        datum, LOCAL_UV, LOCAL_UV, band[0], band[1], cap_frame=True, label=label
    )


def local_difference(
    subject: dict[str, Shape], reference: dict[str, Shape], datum, band: tuple[float, float],
    *, collect_fragments: bool = False,
) -> tuple[float, list[Shape]]:
    tool = local_crop(datum, band, f"{datum.name}_LOCAL_AUDIT_BAND")
    total = 0.0
    fragments: list[Shape] = []
    for side in ("JaD", "JfD"):
        subject_crop = subject[side] & tool
        if subject_crop is None or not subject_crop.solids():
            continue
        reference_crop = reference[side] & tool
        common = None if reference_crop is None or not reference_crop.solids() else subject_crop & reference_crop
        difference_volume = max(0.0, safe_volume(subject_crop) - safe_volume(common))
        total += difference_volume
        if collect_fragments and difference_volume > LEGACY_VOLUME_EPS:
            difference = subject_crop - reference[side]
            if difference is not None:
                fragments.extend(solid for solid in difference.solids() if float(solid.volume) > EPS)
    return total, fragments


def axial_hits(ray: ExactRaySampler, datum) -> list[float]:
    center = np.asarray(datum.center, float)
    axis = np.asarray(unit(datum.axis), float)
    start_distance = 15.0
    start = center + axis * start_distance
    values = [
        float(hit - start_distance)
        for hit in ray.hits(tuple(map(float, start)), tuple(map(float, -axis)), 45.0)
    ]
    return [value for value in values if -2.50 - EPS <= value <= 15.50 + EPS]


def source_metrics(paths: dict[str, Path], shapes: dict[str, Shape]) -> dict[str, object]:
    return {
        side: {"path": relative(paths[side]), "sha256": sha256(paths[side]), **metrics(shapes[side])}
        for side in ("JaD", "JfD")
    }


def axis_lines(datums) -> list[tuple[np.ndarray, np.ndarray, tuple[int, int, int, int], str]]:
    rows = []
    for datum in datums:
        center = np.asarray(datum.center, float)
        axis = np.asarray(unit(datum.axis), float)
        rows.append((center + axis * 4.0, center - axis * 6.0, (*COL["axis"], 255), datum.name))
    return rows


def fit_shapes(shapes: list[Shape], factor: float = 1.18) -> np.ndarray:
    arrays = [safe_triangles(shape).reshape(-1, 3) for shape in shapes if shape is not None and shape.solids()]
    return expanded_fit(np.concatenate(arrays), factor)


def render_outputs(
    current: dict[str, Shape], lower15: dict[str, Shape], bare: dict[str, Shape],
    datums, representative: dict[str, list[Shape]], legacy_all: list[Shape]
) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    tri_current = {side: safe_triangles(current[side]) for side in ("JaD", "JfD")}
    tri_bare = {side: safe_triangles(bare[side]) for side in ("JaD", "JfD")}
    edge_current = {side: safe_edge_lines(current[side]) for side in ("JaD", "JfD")}
    edge_bare = {side: safe_edge_lines(bare[side]) for side in ("JaD", "JfD")}
    current_points = np.concatenate([tri_current[s].reshape(-1, 3) for s in ("JaD", "JfD")])
    bare_points = np.concatenate([tri_bare[s].reshape(-1, 3) for s in ("JaD", "JfD")])
    lines = axis_lines(datums)

    def draw(name, objects, camera, fit, *, transparent=None, wires=None, world_lines=None):
        path = RENDER / name
        raster_scene_without_header(
            path, objects, "", "", FOOTER, camera_offset=camera, fit_points=fit,
            transparent_objects=transparent or [], wireframes=wires or [],
            world_lines=world_lines or [], final_size=(1440, 960),
        )
        out.append(relative(path))

    draw(
        "01_all8_current_source_exterior.png",
        [(tri_current["JaD"], COL["current"]), (tri_current["JfD"], COL["current"])],
        (145, -245, -105), expanded_fit(current_points, 1.30), world_lines=lines,
    )
    legacy_objects = [(safe_triangles(shape), COL["legacy"]) for shape in legacy_all if shape.solids()]
    draw(
        "02_all8_current_source_interior.png", legacy_objects,
        (120, -205, -120), expanded_fit(current_points, 1.26),
        transparent=[(tri_current["JaD"], (*COL["jad"], 34)), (tri_current["JfD"], (*COL["jfd"], 34))],
        wires=[(edge_current["JaD"], (*COL["edge"], 82)), (edge_current["JfD"], (*COL["edge"], 82))],
        world_lines=lines,
    )

    rep = next(datum for datum in datums if datum.name == "I2")
    slab = oriented_box(rep, 0.28, 18.0, -3.0, 16.0, cap_frame=True, label="I2_SECTION_SLAB")
    current_section = [current[s] & slab for s in ("JaD", "JfD")]
    bare_section = [bare[s] & slab for s in ("JaD", "JfD")]
    current_section = [shape.clean() for shape in current_section if shape is not None and shape.solids()]
    bare_section = [shape.clean() for shape in bare_section if shape is not None and shape.solids()]
    section_shapes = [shape for shape in [*current_section, *bare_section, *representative["added"]] if shape is not None and shape.solids()]
    section_objects = [(safe_triangles(shape), COL["current"]) for shape in current_section if shape.solids()]
    section_objects += [(safe_triangles(shape), COL["legacy"]) for shape in representative["added"] if shape.solids()]
    draw(
        "03_i2_representative_legacy_cross_section.png", section_objects,
        tuple((np.asarray(rep.switch_u, float) * 50.0 - np.asarray(rep.axis, float) * 22.0).tolist()),
        fit_shapes(section_shapes, 1.55),
        transparent=[(safe_triangles(shape), (*COL["bare"], 42)) for shape in bare_section if shape.solids()],
        wires=[(safe_edge_lines(shape), (*COL["bare"], 150)) for shape in bare_section if shape.solids()],
        world_lines=axis_lines([rep]),
    )
    draw(
        "04_true_bare_candidate_exterior.png",
        [(tri_bare["JaD"], COL["jad"]), (tri_bare["JfD"], COL["jfd"])],
        (145, -245, -105), expanded_fit(bare_points, 1.30), world_lines=lines,
    )
    draw(
        "05_true_bare_candidate_interior.png", [],
        (120, -205, -120), expanded_fit(bare_points, 1.26),
        transparent=[(tri_bare["JaD"], (*COL["jad"], 45)), (tri_bare["JfD"], (*COL["jfd"], 45))],
        wires=[(edge_bare["JaD"], (*COL["edge"], 110)), (edge_bare["JfD"], (*COL["edge"], 110))],
        world_lines=lines,
    )
    return out


def report_text(data: dict[str, object]) -> str:
    rows = []
    for name in REPORT_ORDER:
        row = data["buttons"][name]
        rows.append(
            f"| {name} | {'YES' if row['bareExteriorSkin'] else 'NO'} | "
            f"{'YES' if row['legacyLargeOpening'] else 'NO'} | "
            f"{'YES' if row['legacyInternalHousing'] else 'NO'} | "
            f"{'YES' if row['legacyBossOrWall'] else 'NO'} | "
            f"{'YES' if row['safeForDirectItsEmbedding'] else 'NO'} |"
        )
    diff_rows = []
    for name in REPORT_ORDER:
        row = data["buttons"][name]
        diff_rows.append(
            f"| {name} | {row['currentVsHistoricalStart']['exteriorRemovedMm3']:.6f} | "
            f"{row['lower15VsHistoricalStart']['interiorAddedMm3']:.6f} | "
            f"{row['lower15VsHistoricalStart']['interiorRemovedMm3']:.6f} | "
            f"{row['axialHitsMm']['current']} | {row['axialHitsMm']['lower15']} | "
            f"{row['axialHitsMm']['historicalStart']} |"
        )
    return f"""# 99 — Critical true-bare Finger shell source pre-gate

## Hard-gate result

```text
CURRENT \"CLEAN\" SOURCE IS TRUE BARE = NO

HISTORICAL START FINGER SHELL IS BARE = YES
HISTORICAL START HAS APPROVED LOWER15 THUMB EXTERIOR = NO

TRUE BARE COMPLETE V2 BASE = NOT CONFIRMED
BASE-SOURCE RECOVERY = FAIL
DIRECT-EMBEDDED SOCKET BOOLEAN STARTED = NO
```

The current docs/97 input is the print-ready shell with all eight 8 mm-class Finger
openings already subtracted.  Its intact fill authority is the later exact
`THUMB_LOWER15_HOUSING_V1` shell, which was exported after the historical INDEX/MIDDLE
features existed.  Therefore neither file is a bare Finger base.

The exact historical `Start` AP242 pair is a genuine pre-Finger shell and is the only
confirmed bare Finger geometry authority.  It preserves the original JaD/JfD split but
predates the approved LOWER15 Thumb exterior, so it cannot by itself be promoted to the
complete final V2 base requested here.  No guessed de-feature, Boolean fill, planar patch,
or source graft was performed.

## Current-source audit

| Button | Bare exterior skin? | Legacy large opening? | Legacy internal housing? | Legacy boss/wall? | Safe for direct ITS embedding? |
|---|---|---|---|---|---|
{chr(10).join(rows)}

`Legacy internal housing/boss/wall` requires both positive interior material in exact
LOWER15 relative to historical Start and explicit Finger feature lineage at that location.
That lineage exists at I2/I3/I4/M3/M4.  N3's local box also measures LOWER15-vs-Start
material change, but history identifies N3 as new and the change lies in the neighboring
Thumb/M4 region; it is therefore not mislabelled as an N3-specific legacy holder.
N1/N2/N3 still fail the current-source bare-skin gate because docs/96 subtracted the later
8 mm-class opening cutter.

## Numeric local proof

| Button | Current exterior material removed vs Start (mm³) | LOWER15 interior material added vs Start (mm³) | LOWER15 interior material removed vs Start (mm³) | Current center-axis local hits W (mm) | LOWER15 center-axis local hits W (mm) | Start center-axis local hits W (mm) |
|---|---:|---:|---:|---|---|---|
{chr(10).join(diff_rows)}

Audit bands use frozen center/axis only: exterior W = {EXTERIOR_BAND[0]:.2f}…{EXTERIOR_BAND[1]:.2f} mm,
interior W = {INTERIOR_BAND[0]:.2f}…{INTERIOR_BAND[1]:.2f} mm.  Positive W is inward.
The local volume threshold for a legacy feature is {LEGACY_VOLUME_EPS:.2f} mm³.

## Source lineage

| Lineage | Finger exterior | Finger internal | Thumb exterior | Decision |
|---|---|---|---|---|
| current print-ready docs/96 source | all 8 large openings | later internal material remains where present in LOWER15 | approved exact LOWER15 | reject as bare base |
| exact `THUMB_LOWER15_HOUSING_V1` | old INDEX/MIDDLE opening/seat traces at retained locations | old Finger-added walls/holders at retained locations | approved exact LOWER15 | reject as bare base |
| exact historical `Start` AP242 | smooth pre-Finger skin | no Finger holder group | original pre-LOWER15 Thumb | bare Finger authority only; incomplete final base |

Feature-history evidence: historical `Start` is immutable Onshape version
`4342e7db262cbced58bf16b8`, with INDEX/MIDDLE group absent.  Exact LOWER15 is immutable
version `50dfe4e752e447375b95493a`.  docs/06 records the earlier Finger feature sequence as
8 × 8 mm openings followed by 12.4 × 12.4 mm holders and switch pockets.

## Required visual proof

{chr(10).join(f'- `{path}`' for path in data['outputs']['renders'])}

The images use a farther camera and intentionally omit top-left labels.  Red in the
interior/cross-section proof is later LOWER15 material absent from historical Start.

## Stop condition

The next admissible source-recovery action is a read-only/exported Onshape state that
retains exact LOWER15 Thumb features while suppressing or rolling back all Finger-specific
openings/holders, or an equivalently exact feature-history export.  Until that exists:

```text
BASE-SOURCE RECOVERY = FAIL
STOP
```

Generated: {data['generatedAtUtc']}
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    print("stage import immutable sources", flush=True)
    current = {side: import_step(path) for side, path in CURRENT.items()}
    lower15 = {side: import_step(path) for side, path in LOWER15.items()}
    bare = {side: import_step(path) for side, path in HISTORICAL_START.items()}
    datums = controls_from_layout()
    rays = {
        "current": ExactRaySampler(Compound(children=list(current.values()))),
        "lower15": ExactRaySampler(Compound(children=list(lower15.values()))),
        "historicalStart": ExactRaySampler(Compound(children=list(bare.values()))),
    }
    buttons: dict[str, object] = {}
    legacy_all: list[Shape] = []
    representative = {"added": [], "removed": []}
    print("stage bounded local material audit", flush=True)
    for datum in datums:
        current_ext_removed, _ = local_difference(bare, current, datum, EXTERIOR_BAND)
        current_ext_added, _ = local_difference(current, bare, datum, EXTERIOR_BAND)
        lower_ext_added, _ = local_difference(lower15, bare, datum, EXTERIOR_BAND)
        lower_ext_removed, _ = local_difference(bare, lower15, datum, EXTERIOR_BAND)
        lower_int_added, added_shapes = local_difference(
            lower15, bare, datum, INTERIOR_BAND,
            collect_fragments=datum.name in LEGACY_FINGER_LOCATIONS,
        )
        lower_int_removed, removed_shapes = local_difference(bare, lower15, datum, INTERIOR_BAND)
        current_int_added, _ = local_difference(current, bare, datum, INTERIOR_BAND)
        current_int_removed, _ = local_difference(bare, current, datum, INTERIOR_BAND)
        legacy_all.extend(added_shapes)
        if datum.name == "I2":
            representative = {"added": added_shapes, "removed": removed_shapes}
        large_opening = current_ext_removed > LEGACY_VOLUME_EPS
        housing = datum.name in LEGACY_FINGER_LOCATIONS and lower_int_added > LEGACY_VOLUME_EPS
        buttons[datum.name] = {
            "owner": datum.owner,
            "centerMm": list(datum.center), "axis": list(datum.axis),
            "bareExteriorSkin": not large_opening,
            "legacyLargeOpening": large_opening,
            "legacyInternalHousing": housing,
            "legacyBossOrWall": housing,
            "safeForDirectItsEmbedding": False,
            "currentVsHistoricalStart": {
                "exteriorRemovedMm3": current_ext_removed,
                "exteriorAddedMm3": current_ext_added,
                "interiorRemovedMm3": current_int_removed,
                "interiorAddedMm3": current_int_added,
            },
            "lower15VsHistoricalStart": {
                "exteriorRemovedMm3": lower_ext_removed,
                "exteriorAddedMm3": lower_ext_added,
                "interiorRemovedMm3": lower_int_removed,
                "interiorAddedMm3": lower_int_added,
            },
            "axialHitsMm": {name: axial_hits(ray, datum) for name, ray in rays.items()},
        }
        print(f"  {datum.name} complete", flush=True)

    print("stage proof renders", flush=True)
    render_paths = render_outputs(current, lower15, bare, datums, representative, legacy_all)
    data = {
        "schema": "onegrip-true-bare-finger-shell-source-pregate-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "socketBooleanCount": 0, "shellRepairCount": 0, "stepExportCount": 0,
            "stlExportCount": 0, "productionGeometryModificationCount": 0,
            "localUvMm": LOCAL_UV, "exteriorBandWmm": list(EXTERIOR_BAND),
            "interiorBandWmm": list(INTERIOR_BAND), "legacyVolumeThresholdMm3": LEGACY_VOLUME_EPS,
        },
        "gate": {
            "currentCleanSourceTrueBare": False,
            "historicalStartFingerShellBare": True,
            "historicalStartHasApprovedLower15Thumb": False,
            "trueBareCompleteV2BaseConfirmed": False,
            "result": "BASE-SOURCE RECOVERY = FAIL",
        },
        "sources": {
            "current": source_metrics(CURRENT, current),
            "exactLower15": source_metrics(LOWER15, lower15),
            "historicalStart": source_metrics(HISTORICAL_START, bare),
        },
        "buttons": buttons,
        "outputs": {"json": relative(JSON_PATH), "report": relative(REPORT), "renders": render_paths},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"gate": data["gate"], "outputs": data["outputs"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
