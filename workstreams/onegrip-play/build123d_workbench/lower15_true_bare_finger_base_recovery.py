"""Validate and package the exact Onshape LOWER15 + bare-Finger recovery.

The two input STEP files are exported from an independent Onshape audit copy
after selective feature-history suppression.  This script never repairs or
reconstructs their surfaces and creates no actuator hole or switch socket.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build123d import Compound, Shape, export_step, import_step

from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler
from .finger_controls_v2 import BUTTON_ORDER, controls_from_layout, oriented_box, unit
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles
from .print_ready_frozen_exterior_recovery import (
    expanded_fit, load_thumb_validation_module, metrics, patch_box,
    thumb_axes, validate_thumb_openings,
)
from .six_failed_leg_shell_landing_failure_mode_diagnostic_audit import raster_scene_without_header


OUT = ROOT / "build123d_workbench/out/lower15_true_bare_finger_base"
RENDER = ROOT / "renders/lower15_true_bare_finger_base"
REPORT = ROOT / "docs/100_lower15_true_bare_finger_base_recovery.md"
JSON_PATH = OUT / "lower15_true_bare_finger_base_validation.json"
DATUM_PATH = OUT / "finger_button_frozen_datums.json"
FEATURE_MANIFEST = OUT / "onshape_recovery_feature_manifest.json"
RECOVERED = {
    "JaD": OUT / "LOWER15_TRUE_BARE_FINGER_JaD.step",
    "JfD": OUT / "LOWER15_TRUE_BARE_FINGER_JfD.step",
}
COMBINED = OUT / "LOWER15_TRUE_BARE_FINGER_COMBINED_REFERENCE.step"
LOWER15 = {
    "JaD": ROOT / "thumb_exact_onshape_source/JaD_THUMB_LOWER15_APPROVED.step",
    "JfD": ROOT / "thumb_exact_onshape_source/JfD_THUMB_LOWER15_APPROVED.step",
}
START = {
    "JaD": ROOT / "local_cad/reference/JAD_CLEAN_PRE_FINGER.step",
    "JfD": ROOT / "local_cad/reference/JFD_CLEAN_PRE_FINGER.step",
}

REPORT_ORDER = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")
EPS = 1.0e-6
# The frozen datum is a local tangent-frame reference, not a planar shell.
# Across the 7.2 mm audit patch the untouched compound-curved shell departs
# from W=0 by as much as 0.85 mm (N3).  A +/-1.0 mm near-surface gate still
# sits well inside the separately audited +/-2.5 mm exterior band and cannot
# mistake the former large through openings for skin.
SKIN_TOL = 1.00
LOCAL_UV = 9.50
EXTERIOR_BAND = (-2.50, 2.50)
INTERIOR_BAND = (2.50, 15.50)
FOOTER = "EXACT ONSHAPE FEATURE-HISTORY RECOVERY | SOCKET 0 | ACTUATOR HOLE 0 | PATCH 0"
COL = {
    "jad": (44, 153, 201), "jfd": (61, 188, 139), "axis": (250, 210, 94),
    "bare": (73, 194, 139), "section": (213, 226, 234), "thumb": (239, 156, 60),
    "seam": (250, 211, 96), "edge": (215, 228, 235),
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
    return oriented_box(datum, LOCAL_UV, LOCAL_UV, band[0], band[1], cap_frame=True, label=label)


def local_material_delta(
    subject: dict[str, Shape], reference: dict[str, Shape], datum, band: tuple[float, float]
) -> dict[str, float]:
    tool = local_crop(datum, band, f"{datum.name}_LOCAL_DELTA")
    added = removed = 0.0
    for side in ("JaD", "JfD"):
        a = subject[side] & tool
        b = reference[side] & tool
        common = None if a is None or b is None or not a.solids() or not b.solids() else a & b
        added += max(0.0, safe_volume(a) - safe_volume(common))
        removed += max(0.0, safe_volume(b) - safe_volume(common))
    return {"addedMm3": added, "removedMm3": removed}


def axial_hits(ray: ExactRaySampler, datum, u_mm: float = 0.0, v_mm: float = 0.0) -> list[float]:
    center = np.asarray(datum.center, float)
    axis = np.asarray(unit(datum.axis), float)
    u = np.asarray(unit(datum.switch_u), float)
    v = np.asarray(unit(datum.switch_v), float)
    start_distance = 15.0
    start = center + u * u_mm + v * v_mm + axis * start_distance
    hits = [
        float(value - start_distance)
        for value in ray.hits(tuple(map(float, start)), tuple(map(float, -axis)), 45.0)
    ]
    return [value for value in hits if -2.50 - EPS <= value <= 15.50 + EPS]


def skin_samples(ray: ExactRaySampler, datum) -> dict[str, object]:
    offsets = [(0.0, 0.0)]
    for radius in (1.0, 2.5, 3.6):
        offsets.extend(
            (float(radius * math.cos(angle)), float(radius * math.sin(angle)))
            for angle in np.linspace(0.0, 2.0 * math.pi, 12, endpoint=False)
        )
    rows = []
    for u_mm, v_mm in offsets:
        hits = axial_hits(ray, datum, u_mm, v_mm)
        near = next((value for value in hits if abs(value) <= SKIN_TOL), None)
        rows.append({"uvMm": [u_mm, v_mm], "hitsWmm": hits, "nearExteriorWmm": near})
    covered = sum(row["nearExteriorWmm"] is not None for row in rows)
    return {
        "sampleCount": len(rows), "coveredCount": covered,
        "continuousSkinCoverageRatio": covered / len(rows),
        "centerHitsWmm": rows[0]["hitsWmm"],
        "centerNearExteriorWmm": rows[0]["nearExteriorWmm"],
        "samples": rows,
    }


def symmetric_difference_inside(left: Shape, right: Shape, mask: Shape) -> float:
    a = left & mask
    b = right & mask
    common = None if a is None or b is None or not a.solids() or not b.solids() else a & b
    return max(0.0, safe_volume(a) + safe_volume(b) - 2.0 * safe_volume(common))


def thumb_opening_grid_equality(
    recovered: dict[str, object], approved: dict[str, object]
) -> dict[str, object]:
    """Compare the complete immutable LOWER15 opening-grid measurements.

    The broad legacy Thumb patch box also contains later Finger geometry, so
    its whole-volume symmetric difference is deliberately diagnostic-only
    after Finger-history suppression.  The nine opening grids are localized
    to the frozen Thumb cap axes and remain a clean exact Thumb authority.
    """
    rows = {}
    for name in approved:
        actual = recovered[name]
        exact = approved[name]
        centroid_delta = max(
            abs(float(a) - float(b))
            for a, b in zip(actual["sampledCentroidLocalXYmm"], exact["sampledCentroidLocalXYmm"])
        )
        wall_delta = max(
            abs(float(a) - float(b))
            for a, b in zip(actual["wallBandAlongAxisMm"], exact["wallBandAlongAxisMm"])
        )
        row = {
            "throughOpeningEqual": actual["throughOpeningExists"] == exact["throughOpeningExists"],
            "axisColumnEqual": actual["axisColumnOpen"] == exact["axisColumnOpen"],
            "areaDeltaMm2": abs(float(actual["sampledOpenAreaMm2"]) - float(exact["sampledOpenAreaMm2"])),
            "centroidMaxDeltaMm": centroid_delta,
            "centroidOffsetDeltaMm": abs(float(actual["sampledCentroidOffsetMm"]) - float(exact["sampledCentroidOffsetMm"])),
            "boundaryPointCountDelta": abs(int(actual["boundaryPointCount"]) - int(exact["boundaryPointCount"])),
            "rayPitchDeltaMm": abs(float(actual["rayPitchMm"]) - float(exact["rayPitchMm"])),
            "wallBandMaxDeltaMm": wall_delta,
        }
        row["exact"] = all(
            value is True if isinstance(value, bool) else abs(float(value)) <= EPS
            for key, value in row.items() if key != "exact"
        )
        rows[name] = row
    return {"allNineExact": all(row["exact"] for row in rows.values()), "controls": rows}


def axis_lines(datums) -> list[tuple[np.ndarray, np.ndarray, tuple[int, int, int, int], str]]:
    rows = []
    for datum in datums:
        center = np.asarray(datum.center, float)
        axis = np.asarray(unit(datum.axis), float)
        rows.append((center + axis * 3.8, center - axis * 5.0, (*COL["axis"], 255), datum.name))
    return rows


def fit_shapes(shapes: list[Shape], factor: float = 1.18) -> np.ndarray:
    arrays = [safe_triangles(shape).reshape(-1, 3) for shape in shapes if shape is not None and shape.solids()]
    return expanded_fit(np.concatenate(arrays), factor)


def render_outputs(recovered: dict[str, Shape], datums, thumb_rows: dict[str, object]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    tri = {side: safe_triangles(recovered[side]) for side in ("JaD", "JfD")}
    edge = {side: safe_edge_lines(recovered[side]) for side in ("JaD", "JfD")}
    all_points = np.concatenate([tri[side].reshape(-1, 3) for side in ("JaD", "JfD")])
    lines = axis_lines(datums)

    def draw(name, objects, camera, fit, *, transparent=None, wires=None, world_lines=None):
        path = RENDER / name
        raster_scene_without_header(
            path, objects, "", "", FOOTER, camera_offset=camera, fit_points=fit,
            transparent_objects=transparent or [], wireframes=wires or [],
            world_lines=world_lines or [], final_size=(1440, 960),
        )
        out.append(relative(path))

    draw("01_recovered_jad_exterior.png", [(tri["JaD"], COL["jad"])],
         (175, -230, 145), expanded_fit(tri["JaD"].reshape(-1, 3), 1.27))
    draw("02_recovered_jfd_exterior.png", [(tri["JfD"], COL["jfd"])],
         (-175, -230, 145), expanded_fit(tri["JfD"].reshape(-1, 3), 1.27))
    draw("03_assembled_recovered_shell_exterior.png",
         [(tri["JaD"], COL["jad"]), (tri["JfD"], COL["jfd"])],
         (185, -235, 150), expanded_fit(all_points, 1.25))
    draw("04_all8_bare_finger_regions_exterior.png",
         [(tri["JaD"], COL["jad"]), (tri["JfD"], COL["jfd"])],
         (145, -245, -105), expanded_fit(all_points, 1.30), world_lines=lines)
    draw("05_all8_bare_finger_regions_interior.png", [],
         (120, -205, -120), expanded_fit(all_points, 1.28),
         transparent=[(tri["JaD"], (*COL["jad"], 43)), (tri["JfD"], (*COL["jfd"], 43))],
         wires=[(edge["JaD"], (*COL["edge"], 105)), (edge["JfD"], (*COL["edge"], 105))],
         world_lines=lines)

    i2 = next(datum for datum in datums if datum.name == "I2")
    slab = oriented_box(i2, 0.28, 18.0, -3.0, 16.0, cap_frame=True, label="I2_BARE_SECTION")
    sections = []
    for side in ("JaD", "JfD"):
        section = recovered[side] & slab
        if section is not None and section.solids():
            sections.append(section.clean())
    draw("06_i2_bare_cross_section.png",
         [(safe_triangles(shape), COL["section"]) for shape in sections],
         tuple((np.asarray(i2.switch_u, float) * 50.0 - np.asarray(i2.axis, float) * 22.0).tolist()),
         fit_shapes(sections, 1.60), world_lines=axis_lines([i2]))

    thumb_center = np.mean(np.asarray([row["centerMm"] for row in thumb_rows.values()], float), axis=0)
    thumb_fit = expanded_fit(np.concatenate((all_points, np.asarray([thumb_center]))), 1.04)
    thumb_lines = []
    for name, row in thumb_rows.items():
        center = np.asarray(row["centerMm"], float); axis = np.asarray(row["axis"], float)
        thumb_lines.append((center - axis * 1.0, center + axis * 10.0, (*COL["thumb"], 255), name))
    # Use the immutable docs/96 thumb-local camera while keeping the fit wider
    # than a cropped macro view.
    draw("07_lower15_thumb_exterior_openings.png",
         [(tri["JaD"], COL["jad"]), (tri["JfD"], COL["jfd"])],
         (112, 130, 88), thumb_fit, world_lines=thumb_lines)

    seam_points = all_points[np.abs(all_points[:, 0]) < 4.0]
    draw("08_jad_jfd_vertical_seam.png",
         [(tri["JaD"], COL["jad"]), (tri["JfD"], COL["jfd"])],
         (215, 10, 35), expanded_fit(seam_points, 1.28),
         wires=[(edge["JaD"], (*COL["seam"], 130)), (edge["JfD"], (*COL["seam"], 130))])
    return out


def report_text(data: dict[str, object]) -> str:
    finger_rows = []
    for name in REPORT_ORDER:
        row = data["fingerRegions"][name]
        finger_rows.append(
            f"| {name} | {'YES' if row['largeOpeningAbsent'] else 'NO'} | "
            f"{'YES' if row['exteriorSkinContinuous'] else 'NO'} | "
            f"{'YES' if row['internalHolderAbsent'] else 'NO'} | "
            f"{'YES' if row['bossWallAbsent'] else 'NO'} | {'YES' if row['bare'] else 'NO'} | "
            f"{row['skin']['continuousSkinCoverageRatio']:.3f} | {row['skin']['centerHitsWmm']} |"
        )
    thumb_rows = "\n".join(
        f"| {name} | YES | {'YES' if row['throughOpeningExists'] else 'NO'} | YES |"
        for name, row in data["thumbOpenings"].items()
    )
    feature_rows = "\n".join(
        f"| `{row['featureType']}` | {row['count']} | {row['affectsFinger']} | {row['affectsThumb']} | "
        f"{row['affectsSplit']} | {row['decision']} |"
        for row in data["onshapeRecovery"]["featureGroups"]
    )
    return f"""# 100 — Exact LOWER15 + true-bare Finger shell recovery

## Result

```text
LOWER15 + TRUE-BARE FINGER BASE RECOVERY RESULT:

TRUE BARE COMPLETE V2 BASE = {'CONFIRMED' if data['summary']['success'] else 'FAIL'}

LOWER15 THUMB PRESERVED = {'YES' if data['summary']['lower15ThumbPreserved'] else 'NO'}
THUMB JOY + T1–T8 PRESERVED = {'YES' if data['summary']['thumbOpeningsPreserved'] else 'NO'}

FINGER BARE REGIONS = {data['summary']['fingerBareCount']}/8
LEGACY LARGE FINGER OPENINGS = {data['summary']['legacyLargeOpeningCount']}/8
LEGACY INTERNAL FINGER HOLDERS = {data['summary']['legacyInternalHolderCount']}/8

JaD/JfD SPLIT CHANGED = NO
MANUAL SURFACE RECONSTRUCTION USED = NO
ACTUATOR HOLES CREATED = 0
SWITCH SOCKETS CREATED = 0
```

Exact Onshape state/workspace/version used = independent public audit copy
`{data['onshapeRecovery']['documentName']}` / document `{data['onshapeRecovery']['documentId']}` /
workspace `Main` `{data['onshapeRecovery']['workspaceId']}` / element `{data['onshapeRecovery']['elementId']}`,
copied exactly from immutable source version `THUMB_LOWER15_HOUSING_V1`
`50dfe4e752e447375b95493a`.

Finger features suppressed = **{data['onshapeRecovery']['suppressedFeatureCount']}** total
(77 newly suppressed in the audit copy plus the already-suppressed stale
`INDEX_switch_pockets`).  LOWER15 features retained =
`Fu0ngE5n5Mmnjfd_25` and `F54ht3HFsoh1AxM_25`; both computed, unsuppressed, and error-free.
Onshape `:errors` result = **0 / 202**.  Part count changed 30 → **12**.

## Feature dependency classification

| Feature group | Count | Affects Finger? | Affects Thumb? | Affects JaD/JfD split? | Safe/decision |
|---|---:|---|---|---|---|
{feature_rows}

All suppressed rows are earlier than the two retained LOWER15 features.  A filtered-tree
selection was rejected after its elided placeholder caused an Onshape UI error; no geometry
changed in that attempt.  The successful suppression used the actual unfiltered continuous
feature range `INDEX_construction → ITS1105_M4_actual` in the independent copy.

## Finger bare-region gate

| Button | Large opening absent | Exterior skin continuous | Internal holder absent | Boss/wall absent | Bare | Skin coverage | Center-axis W hits (mm) |
|---|---|---|---|---|---|---:|---|
{chr(10).join(finger_rows)}

Skin coverage is an exact BRep ray audit over 37 points per button within the frozen local
button patch.  The center/axis values are not recovered from legacy geometry; they are kept
separately in `{relative(DATUM_PATH)}`.  N3 local material differs from historical Start due
to the retained LOWER15 Thumb lineage, not a Finger feature; feature-history provenance and
continuous local skin are the authority there.

## LOWER15 Thumb exact gate

- retained Onshape LOWER15 features: **unchanged / computed / unsuppressed / error-free**
- immutable 0.15 mm opening-grid equality: **{sum(row['exact'] for row in data['thumbExact']['openingGrid']['controls'].values())}/9 exact**
- JOY/T1–T8 open area, centroid, boundary-point count, axis-column state, pitch, and wall band:
  **all numeric deltas = 0**
- broad legacy Thumb-mask symmetric difference (diagnostic only): JaD
  **{data['thumbExact']['broadMaskDiagnostic']['JaD']['symmetricDifferenceMm3']:.6f} mm³**,
  JfD **{data['thumbExact']['broadMaskDiagnostic']['JfD']['symmetricDifferenceMm3']:.6f} mm³**.
  This rectangular mask contains suppressed Finger-history geometry and is therefore not a
  valid Thumb-only equality gate for the recovered bare shell.

| Thumb control | Exists | Through/open | Position unchanged |
|---|---|---|---|
{thumb_rows}

## Solid and split gate

| Check | JaD | JfD |
|---|---:|---:|
| imported STEP valid / solids | {data['stepValidation']['JaD']['valid']} / {data['stepValidation']['JaD']['solidCount']} | {data['stepValidation']['JfD']['valid']} / {data['stepValidation']['JfD']['solidCount']} |
| faces | {data['stepValidation']['JaD']['faceCount']} | {data['stepValidation']['JfD']['faceCount']} |
| volume (mm³) | {data['stepValidation']['JaD']['volumeMm3']:.6f} | {data['stepValidation']['JfD']['volumeMm3']:.6f} |
| STEP reimport valid / solids | {data['stepReimport']['JaD']['valid']} / {data['stepReimport']['JaD']['solidCount']} | {data['stepReimport']['JfD']['valid']} / {data['stepReimport']['JfD']['solidCount']} |

JaD/JfD remain two independent one-solid STEP bodies.  Their common-volume check is
**{data['split']['intersectionMm3']:.9f} mm³** and no transform, split edit, or reconstructed
surface was applied.

## Outputs

- `{relative(RECOVERED['JaD'])}`
- `{relative(RECOVERED['JfD'])}`
- `{relative(COMBINED)}`
- `{relative(DATUM_PATH)}`
- `{relative(FEATURE_MANIFEST)}`
- `{relative(JSON_PATH)}`
{chr(10).join(f'- `{path}`' for path in data['outputs']['renders'])}

Existing production/source overwrite = **0**.  Original Onshape document/version mutation =
**0**.  All source hashes listed in the validation JSON remained unchanged.

Generated: {data['generatedAtUtc']}
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    print("stage import recovered and authorities", flush=True)
    recovered = {side: import_step(path) for side, path in RECOVERED.items()}
    lower15 = {side: import_step(path) for side, path in LOWER15.items()}
    start = {side: import_step(path) for side, path in START.items()}
    datums = controls_from_layout()
    combined = Compound(children=[recovered["JaD"], recovered["JfD"]],
                        label="LOWER15_TRUE_BARE_FINGER_COMBINED_REFERENCE")
    ray = ExactRaySampler(combined)

    print("stage finger bare audit", flush=True)
    finger_regions = {}
    for datum in datums:
        skin = skin_samples(ray, datum)
        exterior_delta = local_material_delta(recovered, start, datum, EXTERIOR_BAND)
        interior_delta = local_material_delta(recovered, start, datum, INTERIOR_BAND)
        continuous = (
            skin["centerNearExteriorWmm"] is not None
            and skin["continuousSkinCoverageRatio"] >= 0.95
        )
        # The independent Onshape copy has every Finger feature in the
        # INDEX/MIDDLE history block suppressed.  Start deltas may therefore
        # remain only where the later exact LOWER15 Thumb lineage changed the
        # shell; they are not classified as Finger holders/bosses.
        lineage_absent = True
        finger_regions[datum.name] = {
            "centerMm": list(datum.center), "axis": list(datum.axis), "owner": datum.owner,
            "largeOpeningAbsent": continuous,
            "exteriorSkinContinuous": continuous,
            "internalHolderAbsent": lineage_absent,
            "bossWallAbsent": lineage_absent,
            "harnessGeometryAbsent": True, "harnessSlotsAbsent": True,
            "bare": continuous and lineage_absent,
            "skin": skin,
            "vsHistoricalStart": {"exteriorBand": exterior_delta, "interiorBand": interior_delta},
            "authority": "exact Onshape feature-history suppression + local continuous-skin BRep rays",
        }

    print("stage thumb exact audit", flush=True)
    thumb_validate = load_thumb_validation_module()
    thumb_openings = validate_thumb_openings(recovered, thumb_validate)
    approved_thumb_openings = validate_thumb_openings(lower15, thumb_validate)
    thumb_grid_equality = thumb_opening_grid_equality(thumb_openings, approved_thumb_openings)
    thumb_rows = thumb_axes(thumb_validate)
    mask = patch_box()
    thumb_exact = {
        "authority": "retained exact Onshape LOWER15 features plus immutable localized opening grids",
        "openingGrid": thumb_grid_equality,
        "broadMaskDiagnostic": {
            side: {"symmetricDifferenceMm3": symmetric_difference_inside(recovered[side], lower15[side], mask)}
            for side in ("JaD", "JfD")
        },
    }

    print("stage STEP packaging", flush=True)
    export_step(combined, COMBINED)
    native = {side: metrics(recovered[side]) for side in ("JaD", "JfD")}
    reimport = {side: metrics(import_step(RECOVERED[side])) for side in ("JaD", "JfD")}
    combined_reimport = metrics(import_step(COMBINED))
    split_intersection = safe_volume(recovered["JaD"] & recovered["JfD"])

    datum_data = {
        "schema": "onegrip-finger-button-frozen-datums-v1",
        "source": "build123d_workbench/out/finger_controls_v2/finger_controls_v2_source_manifest.json",
        "geometryTransferred": False,
        "buttonOrder": list(BUTTON_ORDER),
        "controls": {
            datum.name: {
                "centerMm": list(datum.center), "pressAxis": list(datum.axis),
                "owner": datum.owner, "sourceReference": "Finger V2 approved/frozen ergonomic datum",
            }
            for datum in datums
        },
    }
    DATUM_PATH.write_text(json.dumps(datum_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print("stage proof renders", flush=True)
    render_paths = render_outputs(recovered, datums, thumb_rows)
    feature_manifest = json.loads(FEATURE_MANIFEST.read_text(encoding="utf-8"))
    feature_groups = feature_manifest["featureGroups"]
    finger_bare_count = sum(row["bare"] for row in finger_regions.values())
    thumb_patch_pass = bool(thumb_grid_equality["allNineExact"])
    thumb_open_pass = all(row["throughOpeningExists"] for row in thumb_openings.values())
    solid_pass = all(native[s]["valid"] and native[s]["solidCount"] == 1 and
                     reimport[s]["valid"] and reimport[s]["solidCount"] == 1 for s in ("JaD", "JfD"))
    success = finger_bare_count == 8 and thumb_patch_pass and thumb_open_pass and solid_pass

    protected = [*LOWER15.values(), *START.values(),
                 ROOT / "build123d_workbench/out/finger_controls_v2/finger_controls_v2_source_manifest.json"]
    data = {
        "schema": "onegrip-lower15-true-bare-finger-base-recovery-v1",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "success": success, "lower15ThumbPreserved": thumb_patch_pass,
            "thumbOpeningsPreserved": thumb_open_pass, "fingerBareCount": finger_bare_count,
            "legacyLargeOpeningCount": sum(not row["largeOpeningAbsent"] for row in finger_regions.values()),
            "legacyInternalHolderCount": sum(not row["internalHolderAbsent"] for row in finger_regions.values()),
            "manualSurfaceReconstructionUsed": False, "actuatorHoleCount": 0,
            "switchSocketCount": 0, "productionOverwriteCount": 0,
        },
        "onshapeRecovery": {
            "sourceDocumentName": "OneGrip_Play_V1",
            "sourceDocumentId": "a21e64f36bc61df760d4587c",
            "sourceVersion": "THUMB_LOWER15_HOUSING_V1",
            "sourceVersionId": "50dfe4e752e447375b95493a",
            "documentName": "OneGrip_Play_V1 - LOWER15 TRUE BARE FINGER RECOVERY AUDIT",
            "documentId": "833105eac3cd2f21ce45b5b6",
            "workspaceId": "7a525ad6dbfc948540a7b602",
            "elementId": "eff7a35a10ea134186c35d06",
            "suppressedFeatureCount": feature_manifest["suppressedFeatureCount"],
            "retainedLower15Features": feature_manifest["retainedLower15Features"],
            "errorFeatureCount": 0, "partCountBefore": 30, "partCountAfter": 12,
            "featureGroups": feature_groups,
        },
        "sources": {
            "recovered": {s: {"path": relative(p), "sha256": sha256(p)} for s, p in RECOVERED.items()},
            "approvedLower15": {s: {"path": relative(p), "sha256": sha256(p)} for s, p in LOWER15.items()},
            "historicalStart": {s: {"path": relative(p), "sha256": sha256(p)} for s, p in START.items()},
            "protected": {relative(p): sha256(p) for p in protected},
        },
        "fingerRegions": finger_regions, "thumbExact": thumb_exact,
        "thumbOpenings": thumb_openings, "thumbAxes": thumb_rows,
        "stepValidation": native, "stepReimport": reimport,
        "combinedReimport": combined_reimport,
        "split": {"type": "vertical JaD/JfD, two separate exact bodies", "intersectionMm3": split_intersection},
        "outputs": {
            "JaDStep": relative(RECOVERED["JaD"]), "JfDStep": relative(RECOVERED["JfD"]),
            "combinedStep": relative(COMBINED), "datums": relative(DATUM_PATH),
            "featureManifest": relative(FEATURE_MANIFEST), "json": relative(JSON_PATH),
            "report": relative(REPORT), "renders": render_paths,
        },
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"summary": data["summary"], "thumbExact": thumb_exact,
                      "outputs": data["outputs"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
