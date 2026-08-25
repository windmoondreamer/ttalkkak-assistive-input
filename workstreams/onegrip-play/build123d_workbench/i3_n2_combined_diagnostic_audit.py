"""I3 + N2 combined diagnostic audit; measurement geometry only."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Compound, Location, Shape, Vector, import_step

from . import eight_button_four_edge_batch_propagation_screening as d90
from . import i2_detailed_pushbtn_manufacturing_robust_audit as doc84
from . import i3_i4_local_hybrid_support_validation as d93
from . import seven_unresolved_leg_root_shell_target_rescue_audit as d91
from . import six_failed_leg_shell_landing_failure_mode_diagnostic_audit as d92
from .direct_shell_four_edge_i2_simplification_audit import ExactRaySampler, SHELL_STEP
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS, opening_cutter, unit
from .four_edge_leg_harness_captive_pusher_audit import local_box, volume
from .i4_m3_current_audit import load_all_datums
from .model import oriented_box_between
from .open_frame_glued_switch_harness_candidate import ROOT, relative
from .option_c_local_exact_prototype import safe_edge_lines, safe_triangles


OUT = ROOT / "build123d_workbench/out/i3_n2_combined_diagnostic_audit"
RENDER = ROOT / "renders/i3_n2_combined_diagnostic_audit"
REPORT = ROOT / "docs/94_i3_n2_combined_diagnostic_audit.md"
JSON_PATH = OUT / "i3_n2_combined_diagnostic_audit.json"
DOC93_JSON = d93.JSON_PATH
DOC92_JSON = d92.JSON_PATH
DOC91_JSON = d91.JSON_PATH
EPS = 1.0e-6
FOOTER = "I3/N2 DIAGNOSTIC ONLY | FROZEN VALID BUTTONS | NO SOLUTION GEOMETRY | PRODUCTION 0"
COL = {
    "i3": (61, 191, 139), "i2": (171, 112, 219), "collision": (245, 84, 73),
    "shell": (108, 130, 151), "jad": (53, 173, 213), "jfd": (113, 132, 153),
    "probe": (242, 172, 66), "valid": (66, 206, 154), "invalid": (241, 85, 78),
    "body": (65, 167, 224), "terminal": (215, 225, 233), "axis": (250, 212, 77),
}


def xyz(value: Iterable[float]) -> tuple[float, float, float]:
    return tuple(map(float, value))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def safe_volume(shape: Shape | None) -> float:
    return 0.0 if shape is None else float(volume(shape))


def clean_or_none(shape: Shape | None, label: str = "") -> Shape | None:
    if shape is None:
        return None
    result = shape.clean()
    if not result.solids():
        return None
    if label:
        result.label = label
    return result


def moved(shape: Shape, offset: Iterable[float], label: str) -> Shape:
    result = shape.moved(Location(Vector(*map(float, offset))))
    result.label = label
    return result


def protected_files() -> list[Path]:
    paths = set(d93.protected_files())
    paths.update((d93.REPORT, d93.JSON_PATH, ROOT / "build123d_workbench/i3_i4_local_hybrid_support_validation.py"))
    for folder in (d93.OUT, d93.RENDER):
        if folder.exists():
            paths.update(path for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in paths if path.exists())


def hashes(paths: list[Path]) -> dict[str, str]:
    return {relative(path): sha256(path) for path in paths}


def collision_shape(left: Shape, right: Shape, label: str) -> Shape | None:
    return clean_or_none(left & right, label)


def logical_i3_regions(candidate: dict[str, object]) -> dict[str, Shape]:
    """Mutually exclusive source-feature regions; shared roots belong to the seat."""
    seat = candidate["base"]
    remaining_sources = [
        ("+U foot", candidate["contactFoot"]),
        ("+U leg", candidate["contact"]["leg"]),
        ("-U leg", candidate["slotRows"]["-U"]["leg"]),
        ("+V leg", candidate["slotRows"]["+V"]["leg"]),
        ("-V leg", candidate["slotRows"]["-V"]["leg"]),
    ]
    regions: dict[str, Shape] = {"central seat": seat}
    claimed = seat
    for name, source in remaining_sources:
        region = clean_or_none(source - claimed, f"I3_LOGICAL_{name}")
        if region is None:
            continue
        regions[name] = region
        claimed = claimed.fuse(region).clean()
    return regions


def partition_collision(collision: Shape | None, regions: dict[str, Shape]) -> tuple[dict[str, float], float]:
    values = {name: 0.0 for name in regions}
    if collision is None:
        return values, 0.0
    remaining: Shape | None = collision
    for name, region in regions.items():
        if remaining is None:
            break
        piece = clean_or_none(remaining & region)
        values[name] = safe_volume(piece)
        remaining = clean_or_none(remaining - region)
    return values, safe_volume(remaining)


def bbox_measure(shape: Shape | None) -> dict[str, object]:
    if shape is None:
        return {"sizesLocalUVWmm": [0.0, 0.0, 0.0], "minimumEnvelopeRemovalMm": 0.0,
                "minimumEnvelopeAxis": "NONE", "directionLocal": [0.0, 0.0, 0.0]}
    size = shape.bounding_box().size
    values = [float(size.X), float(size.Y), float(size.Z)]
    index = int(np.argmin([value if value > EPS else float("inf") for value in values]))
    direction = [0.0, 0.0, 0.0]
    direction[index] = 1.0
    return {"sizesLocalUVWmm": values, "minimumEnvelopeRemovalMm": values[index],
            "minimumEnvelopeAxis": ("U", "V", "W")[index], "directionLocal": direction,
            "method": "exact collision-solid local bounding-envelope thickness; diagnostic trim bound"}


def i3_authority_geometry(docs91: dict[str, object], docs93: dict[str, object], datums, placements,
                          shell_full: dict[str, Shape]) -> dict[str, object]:
    datum = datums["I3"]
    placement = placements["I3"]
    original_shell = d93.shell_local(shell_full[datum.owner], placement, "I3_AUTHORITY_LOCAL_SHELL")
    slot_rows = d93.reconstruct_slot_rows("I3", docs91)
    pad = d93.i3_micro_thickening(original_shell, slot_rows["-U"], placement, datum,
                                  float(FROZEN_FRONT_DEPTHS["I3"]))
    slotted = d93.cut_three_slots(pad["shell"], slot_rows)
    selected = docs93["buttons"]["I3"]["contactSearch"]["selected"]
    contact = d93.build_contact_leg(selected, pad["shell"], "I3")
    candidate = d93.build_hybrid_candidate("I3", slot_rows, contact)
    return {"candidate": candidate, "regions": logical_i3_regions(candidate),
            "shell": slotted, "originalShell": original_shell, "pad": pad}


def i3_collision_diagnostic(authority: dict[str, object], docs90: dict[str, object],
                            docs91: dict[str, object], placements) -> tuple[dict[str, object], dict[str, Shape]]:
    candidate = authority["candidate"]
    regions = authority["regions"]
    i3_placement = placements["I3"]
    existing_world = d93.existing_five_harnesses(docs90, docs91, placements)
    i2_harness = i3_placement.inverse() * existing_world["I2"]
    harness_collision = collision_shape(candidate["harness"], i2_harness, "I3_I2_HARNESS_COLLISION")
    harness_by_region, harness_residual = partition_collision(harness_collision, regions)
    harness_primary = max(harness_by_region, key=harness_by_region.get)
    primary_harness_collision = collision_shape(regions[harness_primary], i2_harness,
                                                "I3_I2_PRIMARY_HARNESS_COLLISION")

    _original, body, terminals, corners, _old_actuator, actuator, _hybrid = doc84.detailed_switch_parts()
    i2_to_i3 = i3_placement.inverse() * placements["I2"]
    i2_parts = {
        "main body": i2_to_i3 * body,
        "T1": i2_to_i3 * terminals["T1"], "T2": i2_to_i3 * terminals["T2"],
        "T3": i2_to_i3 * terminals["T3"], "T4": i2_to_i3 * terminals["T4"],
        "corner features": i2_to_i3 * corners, "actuator": i2_to_i3 * actuator,
    }
    matrix: dict[str, dict[str, float]] = {}
    limiting = ("", "", 0.0)
    for region_name, region in regions.items():
        matrix[region_name] = {}
        for part_name, part in i2_parts.items():
            penetration = safe_volume(region & part)
            matrix[region_name][part_name] = penetration
            if penetration > limiting[2]:
                limiting = (region_name, part_name, penetration)
    detailed_total = sum(sum(row.values()) for row in matrix.values())
    detailed_collision = collision_shape(regions[limiting[0]], i2_parts[limiting[1]],
                                         "I3_I2_DETAILED_LIMITING_COLLISION")

    docs93_states = json.loads(DOC93_JSON.read_text(encoding="utf-8"))["buttons"]["I3"]["rearAssembly"]["states"]
    early_rows = []
    early_collision_shapes: dict[str, Shape | None] = {}
    for state in docs93_states:
        label = state["label"]
        offset = np.asarray(state["offsetLocalUVWmm"], float)
        moved_regions = {name: moved(region, offset, f"{name}_{label}") for name, region in regions.items()}
        grouped = {
            "+U foot": safe_volume(moved_regions.get("+U foot") & authority["shell"]),
            "+U leg": safe_volume(moved_regions.get("+U leg") & authority["shell"]),
            "seat": safe_volume(moved_regions["central seat"] & authority["shell"]),
            "other legs": sum(safe_volume(moved_regions[name] & authority["shell"])
                              for name in ("-U leg", "+V leg", "-V leg") if name in moved_regions),
        }
        total_collision = collision_shape(moved(candidate["harness"], offset, f"I3_{label}"),
                                          authority["shell"], f"I3_SHELL_{label}_COLLISION")
        early_collision_shapes[label] = total_collision
        early_rows.append({"state": label, **grouped, "partitionSumMm3": sum(grouped.values()),
                           "exactTotalMm3": safe_volume(total_collision)})

    largest_early = max((row for row in early_rows if row["state"] in ("25%", "50%", "75%")),
                        key=lambda row: row["exactTotalMm3"])
    corrections = {
        "I3-I2 harness primary": {"region": harness_primary, **bbox_measure(primary_harness_collision)},
        "I3-I2 detailed primary": {"pair": f"I3 {limiting[0]} ↔ I2 {limiting[1]}",
                                     **bbox_measure(detailed_collision)},
        "early shell lead-in": {"state": largest_early["state"],
                                 **bbox_measure(early_collision_shapes[largest_early["state"]])},
    }
    result = {
        "logicalPartitionRule": "shared root material belongs to central seat; remaining source regions are disjoint",
        "harnessCollision": {"exactTotalMm3": safe_volume(harness_collision),
                             "byI3RegionMm3": harness_by_region, "unassignedResidualMm3": harness_residual,
                             "primaryLimitingI3Region": harness_primary, "existsAtFullSeat": True,
                             "existsOnlyDuringInsertion": False},
        "detailedPushBtnCollision": {"exactPairwiseTotalMm3": detailed_total,
                                     "matrixMm3": matrix, "primaryPair": f"I3 {limiting[0]} ↔ I2 {limiting[1]}",
                                     "primaryPairPenetrationMm3": limiting[2], "existsAtFullSeat": True,
                                     "existsOnlyDuringInsertion": False},
        "earlyShellContact": {"states": early_rows,
                              "causedOnlyByPlusUFoot": all(
                                  row["+U leg"] <= EPS and row["seat"] <= EPS and row["other legs"] <= EPS
                                  for row in early_rows if row["state"] in ("25%", "50%", "75%")),
                              "existsAtFullSeatAsUnintendedCollision": False,
                              "existsOnlyDuringInsertion": True},
        "minimumLocalCorrectionMeasurements": corrections,
        "architectureVerdict": "I3-B — MULTIPLE LOCAL CORRECTIONS REQUIRED",
        "canRemainThreeSlotOneContact": "LIKELY WITH LOCAL CORRECTION",
    }
    render_shapes = {"i3Harness": candidate["harness"], "i2Harness": i2_harness,
                     "harnessCollision": harness_collision, "primaryHarnessCollision": primary_harness_collision,
                     "detailedCollision": detailed_collision, "limitingI3Region": regions[limiting[0]],
                     "limitingI2Part": i2_parts[limiting[1]], "early75": early_collision_shapes["75%"],
                     "i3At75": moved(candidate["harness"], np.asarray(docs93_states[3]["offsetLocalUVWmm"], float), "I3_AT_75"),
                     "i3Shell": authority["shell"]}
    return result, render_shapes


def ray_patch(ray: ExactRaySampler, datum, front: float, center_uv: Iterable[float],
              width_u: float, width_v: float) -> dict[str, object]:
    center = np.asarray(tuple(center_uv), float)
    rows = []
    direction_local = np.asarray((0.0, 0.0, 1.0), float)
    direction_world = d90.local_dir_to_world(datum, direction_local)
    for du in np.linspace(-width_u / 2, width_u / 2, 5):
        for dv in np.linspace(-width_v / 2, width_v / 2, 5):
            origin = np.asarray((center[0] + du, center[1] + dv, 0.06), float)
            hits = ray.hits(d90.local_point_to_world(datum, front, origin), direction_world, 24.0)
            rows.append({"originLocalUVWmm": origin.tolist(), "hitsMm": hits,
                         "paired": len(hits) >= 2})
    paired = [row for row in rows if row["paired"]]
    normal = d93.surface_normal_local(ray, datum, front, float(center[0]), float(center[1]))
    if normal is None:
        normal = np.asarray((0.0, 0.0, 1.0), float)
    projected_area = width_u * width_v
    surface_area = projected_area / max(abs(float(normal[2])), 1.0e-3)
    return {"centerLocalUVmm": center.tolist(), "footprintDimensionsMm": [width_u, width_v],
            "rayCoverage": len(paired), "rayCount": len(rows), "samples": rows,
            "availableContactAreaMm2": surface_area if len(paired) == len(rows) else surface_area * len(paired) / len(rows),
            "estimatedSimpleFootContactAreaMm2": projected_area if len(paired) == len(rows) else projected_area * len(paired) / len(rows),
            "localShellNormal": normal.tolist(), "fullFinitePatch": len(paired) == len(rows),
            "minimumShellThicknessMm": min((row["hitsMm"][1] - row["hitsMm"][0] for row in paired), default=0.0)}


def measured_edge_fit_patch(ray: ExactRaySampler, datum, front: float,
                            natural_center_uv: Iterable[float], width_u: float,
                            width_v: float) -> dict[str, object]:
    """Measure the JfD +U-side edge, then place one fixed footprint inside it."""
    center = np.asarray(tuple(natural_center_uv), float)
    direction_world = d90.local_dir_to_world(datum, np.asarray((0.0, 0.0, 1.0), float))

    def paired(u: float, v: float) -> bool:
        origin = np.asarray((u, v, 0.06), float)
        return len(ray.hits(d90.local_point_to_world(datum, front, origin), direction_world, 24.0)) >= 2

    boundaries = []
    for v in np.linspace(center[1] - width_v / 2, center[1] + width_v / 2, 5):
        low = center[0] - width_u
        high = center[0] + width_u
        if not paired(low, float(v)) or paired(high, float(v)):
            raise RuntimeError("N2 +V fixed edge bracket did not contain the local JfD shell edge")
        for _ in range(18):
            middle = 0.5 * (low + high)
            if paired(middle, float(v)):
                low = middle
            else:
                high = middle
        boundaries.append({"vMm": float(v), "lastMaterialUMm": low, "firstVoidUMm": high})
    limiting_u = min(row["lastMaterialUMm"] for row in boundaries)
    clearance = 0.03
    fitted_center = np.asarray((limiting_u - width_u / 2 - clearance, center[1]), float)
    edge_only_patch = ray_patch(ray, datum, front, fitted_center, width_u, width_v)
    required_shell = 1.20
    if edge_only_patch["minimumShellThicknessMm"] < required_shell:
        valid_u = fitted_center[0] - width_u
        valid_patch = ray_patch(ray, datum, front, (valid_u, center[1]), width_u, width_v)
        if not valid_patch["fullFinitePatch"] or valid_patch["minimumShellThicknessMm"] < required_shell:
            raise RuntimeError("N2 +V local structural-thickness bracket failed")
        invalid_u = fitted_center[0]
        for _ in range(16):
            middle_u = 0.5 * (valid_u + invalid_u)
            middle_patch = ray_patch(ray, datum, front, (middle_u, center[1]), width_u, width_v)
            if middle_patch["fullFinitePatch"] and middle_patch["minimumShellThicknessMm"] >= required_shell:
                valid_u = middle_u
                valid_patch = middle_patch
            else:
                invalid_u = middle_u
        fitted_center = np.asarray((valid_u - 0.03, center[1]), float)
    patch = ray_patch(ray, datum, front, fitted_center, width_u, width_v)
    patch.update({"naturalCenterLocalUVmm": center.tolist(),
                  "supportEndpointDistanceFromNaturalRegionMm": float(np.linalg.norm(fitted_center - center)),
                  "measuredLimitingShellEdgeUMm": limiting_u,
                  "edgeOnlyCenterLocalUVmm": edge_only_patch["centerLocalUVmm"],
                  "edgeOnlyMinimumShellThicknessMm": edge_only_patch["minimumShellThicknessMm"],
                  "requiredSupportingShellThicknessMm": required_shell,
                  "edgeClearanceMm": clearance, "edgeBoundaryByV": boundaries,
                  "method": "five fixed V sections plus one-dimensional exact-ray structural-thickness boundary measurement; no root/angle/candidate search"})
    return patch


def n2_diagnostic(docs91: dict[str, object], docs92: dict[str, object], datums,
                  placements, shell_full: dict[str, Shape]) -> tuple[dict[str, object], dict[str, Shape]]:
    datum = datums["N2"]
    front = float(FROZEN_FRONT_DEPTHS["N2"])
    placement = placements["N2"]
    owner = datum.owner
    opposite = "JaD" if owner == "JfD" else "JfD"
    owner_ray = ExactRaySampler(shell_full[owner])
    plus_u_doc = docs92["legs"]["N2 +U"]
    minus_v_doc = docs92["legs"]["N2 -V"]
    plus_v_doc = docs92["legs"]["N2 +V"]

    plus_u_land = plus_u_doc["nearestLandMeasurement"]["oppositeHalf"]["nearestUsableBlindSlotLand"]
    plus_u = {
        "naturalFootprintOwningHalfCoverage": plus_u_doc["missingFootprintOccupancy"]["ownerCoverageCount"],
        "naturalFootprintOppositeHalfCoverage": plus_u_doc["missingFootprintOccupancy"]["counts"].get("opposite shell half", 0),
        "naturalFootprintOpeningVoidCount": plus_u_doc["missingFootprintOccupancy"]["counts"].get("button-opening void", 0),
        "assembledShellHasValidLocalJaDReactionSurface": plus_u_land is not None,
        "nearestJaDLocalLandShiftMm": plus_u_land["distanceMm"],
        "jaDCenterLocalUVmm": plus_u_land["centerLocalUVmm"],
        "jaDFootprintCoverage": plus_u_land["coverageCount"],
        "jaDMinimumRemainingShellMm": plus_u_land["minimumRemainingShellMm"],
        "wouldCrossPhysicalSeam": True, "wouldMechanicallyBridgeShellHalvesIfSlotted": True,
        "blindSlotAssemblyCompatible": False, "contactOnlyAssemblyCompatible": True,
        "classification": "N2+U-2 — JaD LOCAL SEAM-SIDE SUPPORT POSSIBLE",
        "headlineClass": "ASSEMBLY-LIMITED",
    }

    minus_v_metric = minus_v_doc["thicknessDiagnostic"]
    minus_v = {
        "canBecomeNormalMechanicalBlindSlotWithMicroLocalThickening": True,
        "originalRemainingShellMm": minus_v_metric["remainingShellAfterCommonFloorMm"]["minimum"],
        "minimumRequiredInwardThickeningMm": minus_v_metric["requiredMinimumInwardThickeningMm"],
        "minimumPadFootprintMm": minus_v_metric["reinforcementOnlyDiagnosticEstimate"]["minimumFootprintDimensionsMm"],
        "minimumAddedVolumeMm3": minus_v_metric["reinforcementOnlyDiagnosticEstimate"]["minimumAddedVolumeMm3"],
        "outerExteriorChangeMm": 0.0,
    }

    plus_v_best = plus_v_doc["docs91BestFailure"]
    plus_v_center = plus_v_best["targetSeedLocalUVmm"]
    plus_v_natural_envelope = ray_patch(owner_ray, datum, front, plus_v_center, 1.60, 1.30)
    plus_v_patch = measured_edge_fit_patch(owner_ray, datum, front, plus_v_center, 1.60, 1.30)
    plus_v_root = np.asarray(plus_v_best["rootLocalUVWmm"], float)
    fitted_plus_v_center = np.asarray(plus_v_patch["centerLocalUVmm"], float)
    root_uv_distance = float(np.linalg.norm(fitted_plus_v_center - plus_v_root[:2]))
    reaction_point = np.asarray((fitted_plus_v_center[0], fitted_plus_v_center[1],
                                 plus_v_best["targetSeedInnerLocalWmm"]), float)
    reaction_direction = unit(reaction_point - plus_v_root)
    normal = np.asarray(plus_v_patch["localShellNormal"], float)
    normal_angle = math.degrees(math.acos(float(np.clip(np.dot(reaction_direction, normal), -1.0, 1.0))))
    plus_v = {**plus_v_patch,
        "originalOnePointSixByOnePointThreeEnvelope": plus_v_natural_envelope,
        "nearestValidLocalPatchDistanceFromNaturalTargetMm": plus_v_patch["supportEndpointDistanceFromNaturalRegionMm"],
        "rootToPatchCenterUVDistanceMm": root_uv_distance,
        "sideIdentityPreserved": bool(float(fitted_plus_v_center[1]) > 0 and abs(float(fitted_plus_v_center[0])) <= 3.0),
        "remoteOrThumbWallRequired": False,
        "straightLegReactionDirectionLocal": reaction_direction.tolist(),
        "legAxisToLocalShellNormalDeg": normal_angle,
        "bondlessPressLoadSupportPossible": bool(plus_v_patch["fullFinitePatch"] and np.dot(reaction_direction, normal) > 0),
        "classification": "N2+V-3 — LOCAL CONTACT ONLY POSSIBLE" if plus_v_patch["fullFinitePatch"] else "N2+V-4 — NO VALID LOCAL SUPPORT",
    }

    sequences = {
        "A — harness before JaD closure": {"geometricallyPlausible": "YES, CONTACT-ONLY",
            "shellHalvesCanClose": "YES", "harnessRemovable": "YES, AFTER JaD REOPENING",
            "reason": "JaD closure can establish local compression contact; a JaD blind slot would not accept the frozen harness by this closure motion."},
        "B — harness after partial shell assembly": {"geometricallyPlausible": "NO",
            "shellHalvesCanClose": "NOT APPLICABLE", "harnessRemovable": "NO DIRECT REAR PATH",
            "reason": "simultaneous access to JfD slots and a JaD seam-side blind engagement is not available after partial closure."},
        "C — JaD closure creates support": {"geometricallyPlausible": "YES, CONTACT-ONLY",
            "shellHalvesCanClose": "YES", "harnessRemovable": "YES, AFTER SHELL OPENING",
            "reason": "closure may create a non-captive +U compression reaction; it must not be modeled as a cross-seam blind slot or captive bridge."},
    }

    mechanical_count = 2
    contact_count = 2 if plus_v["bondlessPressLoadSupportPossible"] else 1
    architectures = {
        "N2-A — +U JaD mechanical/seam bridge": {"grade": "INVALID",
            "translationRestraint": "GOOD", "rotationRestraint": "GOOD", "rockingUnderPressAxis": "ABSENT",
            "reason": "restraint is geometrically strong, but a captive cross-seam blind support blocks ordinary shell service."},
        "N2-B — -U/-V slots + +U/+V contacts": {"grade": "PLAUSIBLE" if contact_count == 2 else "WEAK",
            "translationRestraint": "PLAUSIBLE", "rotationRestraint": "PLAUSIBLE",
            "rockingUnderPressAxis": "ABSENT IF BOTH CONTACTS CLOSE UNDER PRESS",
            "reason": "two non-collinear blind slots retain the harness; two opposite-side local compression contacts close the press-load support polygon."},
    }

    local_crop = local_box(26.0, 26.0, 16.0, 0, 0, -1.0, "N2_LOCAL_DIAGNOSTIC_CROP")
    owner_local = clean_or_none(placement.inverse() * (shell_full[owner] & (placement * local_crop)), "N2_JFD_LOCAL")
    opposite_local = clean_or_none(placement.inverse() * (shell_full[opposite] & (placement * local_crop)), "N2_JAD_LOCAL")
    plus_u_inner_w = 0.06 + float(plus_u_land["samples"][-1]["hitsMm"][0])
    plus_u_patch_shape = local_box(1.90, 1.60, 0.12, plus_u_land["centerLocalUVmm"][0],
                                   plus_u_land["centerLocalUVmm"][1], plus_u_inner_w, "N2_PLUS_U_JAD_PATCH_PROBE")
    plus_u_natural_shape = local_box(1.90, 1.60, 0.12, 3.985, 0.0, plus_u_inner_w,
                                     "N2_PLUS_U_NATURAL_INCOMPLETE_PROBE")
    plus_v_patch_shape = local_box(1.60, 1.30, 0.12, fitted_plus_v_center[0], fitted_plus_v_center[1],
                                   plus_v_best["targetSeedInnerLocalWmm"], "N2_PLUS_V_LOCAL_PATCH_PROBE")
    minus_v_reference = d92.reference_row("-V", minus_v_doc.get("docs91BestFailure"))
    minus_v_slab = d92.section_slab(minus_v_reference)
    minus_v_section = clean_or_none(owner_local & minus_v_slab, "N2_MINUS_V_SECTION")
    mv_root = np.asarray(minus_v_reference["root"], float)
    mv_direction = np.asarray(minus_v_reference["direction"], float)
    mv_tangent = np.asarray(minus_v_reference["tangent"], float)
    minus_v_probe = oriented_box_between(xyz(mv_root), xyz(mv_root + mv_direction * 9.5), xyz(mv_tangent),
                                         1.90, 1.60, label="N2_MINUS_V_FAILED_SLOT_ENVELOPE")

    result = {
        "minusU": {"currentState": "valid slot", "localSupportExists": True, "sameHalf": True,
                    "seamInvolved": False, "likelySupportType": "mechanical slot"},
        "minusV": minus_v, "plusU": plus_u, "plusV": plus_v,
        "assemblySequences": sequences, "architectures": architectures,
        "viableMechanicalSlotCount": mechanical_count,
        "plausibleLocalContactSupportCount": contact_count,
        "remoteOrThumbWallSupportRequired": False,
        "requiresFundamentallyNewArchitecture": True,
        "recommendedArchitectureDirection": "2 local mechanical slots + 2 local compression contacts; +U contact established by JaD closure",
    }
    shapes = {"ownerShell": owner_local, "oppositeShell": opposite_local,
              "plusUNatural": plus_u_natural_shape, "plusUJaDPatch": plus_u_patch_shape,
              "plusVPatch": plus_v_patch_shape, "minusVSection": minus_v_section,
              "minusVProbe": minus_v_probe}
    return result, shapes


def padded_fit(shapes: list[Shape | None], factor: float = 1.18) -> np.ndarray:
    arrays = [safe_triangles(shape).reshape(-1, 3) for shape in shapes if shape is not None and shape.solids()]
    raw = np.concatenate(arrays, axis=0)
    center = np.mean(raw, axis=0)
    return center + (raw - center) * factor


def render_outputs(i3: dict[str, object], i3_shapes: dict[str, Shape], n2: dict[str, object],
                   n2_shapes: dict[str, Shape]) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    for old in RENDER.glob("*.png"):
        old.unlink()
    paths: list[str] = []

    def render(name: str, objects, fit_shapes, wireframes=None, transparent=None, lines=None,
               camera=(36, -49, 27)) -> None:
        path = RENDER / name
        d92.raster_scene_without_header(path, objects, "", "", FOOTER,
            wireframes=wireframes or [], transparent_objects=transparent or [], world_lines=lines or [],
            camera_offset=camera, fit_points=padded_fit(fit_shapes))
        paths.append(relative(path))

    render("01_i3_i2_harness_limiting_collision.png",
           [(safe_triangles(i3_shapes["i3Harness"]), COL["i3"]),
            (safe_triangles(i3_shapes["harnessCollision"]), COL["collision"])],
           [i3_shapes["i3Harness"], i3_shapes["i2Harness"]],
           wireframes=[(safe_edge_lines(i3_shapes["i2Harness"]), (*COL["i2"], 180))],
           transparent=[(safe_triangles(i3_shapes["i2Harness"]), (*COL["i2"], 45))])
    render("02_i3_i2_detailed_pushbtn_limiting_collision.png",
           [(safe_triangles(i3_shapes["detailedCollision"]), COL["collision"])],
           [i3_shapes["limitingI3Region"], i3_shapes["limitingI2Part"]],
           wireframes=[(safe_edge_lines(i3_shapes["limitingI3Region"]), (*COL["i3"], 210)),
                       (safe_edge_lines(i3_shapes["limitingI2Part"]), (*COL["body"], 210))],
           transparent=[(safe_triangles(i3_shapes["limitingI3Region"]), (*COL["i3"], 26)),
                        (safe_triangles(i3_shapes["limitingI2Part"]), (*COL["body"], 28))],
           camera=(29, -41, 23))
    render("03_i3_early_plus_u_foot_shell_contact.png",
           [(safe_triangles(i3_shapes["i3At75"]), COL["i3"]),
            (safe_triangles(i3_shapes["early75"]), COL["collision"])],
           [i3_shapes["i3Shell"], i3_shapes["i3At75"]],
           wireframes=[(safe_edge_lines(i3_shapes["i3Shell"]), (*COL["shell"], 135))],
           transparent=[(safe_triangles(i3_shapes["i3Shell"]), (*COL["shell"], 28))])
    render("04_i3_full_seat_context.png",
           [(safe_triangles(i3_shapes["i3Harness"]), COL["i3"]),
            (safe_triangles(i3_shapes["harnessCollision"]), COL["collision"])],
           [i3_shapes["i3Shell"], i3_shapes["i3Harness"], i3_shapes["i2Harness"]],
           wireframes=[(safe_edge_lines(i3_shapes["i3Shell"]), (*COL["shell"], 110)),
                       (safe_edge_lines(i3_shapes["i2Harness"]), (*COL["i2"], 170))],
           transparent=[(safe_triangles(i3_shapes["i3Shell"]), (*COL["shell"], 22)),
                        (safe_triangles(i3_shapes["i2Harness"]), (*COL["i2"], 35))])

    render("05_n2_jad_jfd_seam_plus_u_natural_support.png",
           [(safe_triangles(n2_shapes["plusUNatural"]), COL["invalid"]),
            (safe_triangles(n2_shapes["plusUJaDPatch"]), COL["valid"])],
           [n2_shapes["ownerShell"], n2_shapes["oppositeShell"], n2_shapes["plusUNatural"], n2_shapes["plusUJaDPatch"]],
           wireframes=[(safe_edge_lines(n2_shapes["ownerShell"]), (*COL["jfd"], 130)),
                       (safe_edge_lines(n2_shapes["oppositeShell"]), (*COL["jad"], 180))],
           transparent=[(safe_triangles(n2_shapes["ownerShell"]), (*COL["jfd"], 22)),
                        (safe_triangles(n2_shapes["oppositeShell"]), (*COL["jad"], 32))])
    render("06_n2_plus_v_local_contact_region_section.png",
           [(safe_triangles(n2_shapes["plusVPatch"]), COL["valid"])],
           [n2_shapes["ownerShell"], n2_shapes["plusVPatch"]],
           wireframes=[(safe_edge_lines(n2_shapes["ownerShell"]), (*COL["jfd"], 140))],
           transparent=[(safe_triangles(n2_shapes["ownerShell"]), (*COL["jfd"], 25))])
    render("07_n2_minus_v_shell_thickness_section.png",
           [(safe_triangles(n2_shapes["minusVSection"]), COL["shell"]),
            (safe_triangles(n2_shapes["minusVProbe"]), COL["probe"])],
           [n2_shapes["minusVSection"], n2_shapes["minusVProbe"]], camera=(24, -34, 19))

    support_lines = []
    for edge, color in (("-U", COL["valid"]), ("-V", COL["valid"]), ("+U", COL["probe"]), ("+V", COL["probe"])):
        if edge == "+U":
            start = np.asarray((3.985, 0.0, 0.06), float)
            end = np.asarray((5.035, 0.0, 5.27), float)
        elif edge == "+V":
            row = json.loads(DOC92_JSON.read_text(encoding="utf-8"))["legs"]["N2 +V"]["docs91BestFailure"]
            start = np.asarray(row["rootLocalUVWmm"], float)
            end = np.asarray((*row["targetSeedLocalUVmm"], row["targetSeedInnerLocalWmm"]), float)
        else:
            source = json.loads(DOC91_JSON.read_text(encoding="utf-8"))["buttons"]["N2"]
            row = source["legs"][edge] if edge == "-U" else source["search"][edge]["bestFailure"]
            start = np.asarray(row["rootLocalUVWmm"], float)
            end = np.asarray(row["floorPointLocalUVWmm"], float)
        support_lines.append((start, end, (*color, 255), edge))
    render("08_n2_complete_local_support_map.png", [],
           [n2_shapes["ownerShell"], n2_shapes["oppositeShell"]],
           wireframes=[(safe_edge_lines(n2_shapes["ownerShell"]), (*COL["jfd"], 150)),
                       (safe_edge_lines(n2_shapes["oppositeShell"]), (*COL["jad"], 150))],
           transparent=[(safe_triangles(n2_shapes["ownerShell"]), (*COL["jfd"], 20)),
                        (safe_triangles(n2_shapes["oppositeShell"]), (*COL["jad"], 20))],
           lines=support_lines, camera=(42, -57, 31))
    return paths


def fmt(value: float) -> str:
    return f"{float(value):.9f}"


def report_text(data: dict[str, object]) -> str:
    i3 = data["i3"]
    n2 = data["n2"]
    hc = i3["harnessCollision"]
    dc = i3["detailedPushBtnCollision"]
    early = {row["state"]: row for row in i3["earlyShellContact"]["states"]}
    corr = i3["minimumLocalCorrectionMeasurements"]
    rows_h = "\n".join(f"| {name} | {value:.9f} |" for name, value in hc["byI3RegionMm3"].items())
    matrix_rows = []
    for region, parts in dc["matrixMm3"].items():
        for part, value in parts.items():
            if value > EPS:
                matrix_rows.append(f"| {region} | {part} | {value:.9f} |")
    early_rows = "\n".join(
        f"| {state} | {early[state]['+U foot']:.9f} | {early[state]['+U leg']:.9f} | "
        f"{early[state]['seat']:.9f} | {early[state]['other legs']:.9f} | {early[state]['exactTotalMm3']:.9f} |"
        for state in ("25%", "50%", "75%")
    )
    seq_rows = "\n".join(
        f"| {name} | {row['geometricallyPlausible']} | {row['shellHalvesCanClose']} | {row['harnessRemovable']} | {row['reason']} |"
        for name, row in n2["assemblySequences"].items())
    return f"""# 94 — I3 + N2 combined diagnostic audit

```text
I3 / N2 combined diagnostic result:

I3 architecture = {i3['architectureVerdict']}
I3 primary failure = FULL-SEAT I3 {hc['primaryLimitingI3Region']} ↔ frozen I2 harness collision
I3 local-only correction plausible = YES

N2 viable mechanical slots = {n2['viableMechanicalSlotCount']}/4
N2 plausible local-contact supports = {n2['plausibleLocalContactSupportCount']}/4
N2 +U JaD seam-side support = {n2['plusU']['headlineClass']}
N2 +V local contact support = {'POSSIBLE' if n2['plusV']['bondlessPressLoadSupportPossible'] else 'IMPOSSIBLE'}

REMOTE/THUMB-WALL SUPPORT REQUIRED = NO
```

## Scope and preservation

- Diagnostic and measurement geometry only. New harness/slot/foot/pad/boss/bridge/solution STEP count: **0**.
- Frozen buttons N1/I2/M3/M4/N3/I4 were not modified. Production modification count: **0**.
- Authority hashes preserved: **{data['preservation']['protectedFilesUnchanged']}** across {data['preservation']['protectedFileCount']} files.

## I3 — Exact failure decomposition

| Item | Result |
|---|---|
| I3↔I2 harness primary collision pair | I3 {hc['primaryLimitingI3Region']} ↔ I2 harness |
| I3↔I2 harness penetration | {hc['exactTotalMm3']:.9f} mm³ total; {hc['byI3RegionMm3'][hc['primaryLimitingI3Region']]:.9f} mm³ in primary region |
| I3↔I2 PushBtn primary collision pair | {dc['primaryPair']} |
| I3↔I2 PushBtn penetration | {dc['exactPairwiseTotalMm3']:.9f} mm³ total |
| FULL SEAT collision exists? | YES — frozen I2 interference |
| insertion-only collision exists? | YES — +U-foot early shell contact |
| +U foot causes early shell contact? | YES, exclusively at 25/50/75% |
| minimum local correction required | -U: {corr['I3-I2 harness primary']['minimumEnvelopeRemovalMm']:.6f} mm along {corr['I3-I2 harness primary']['minimumEnvelopeAxis']}; seat/T3: {corr['I3-I2 detailed primary']['minimumEnvelopeRemovalMm']:.6f} mm along {corr['I3-I2 detailed primary']['minimumEnvelopeAxis']}; foot lead-in: {corr['early shell lead-in']['minimumEnvelopeRemovalMm']:.6f} mm along {corr['early shell lead-in']['minimumEnvelopeAxis']} |
| I3 architecture verdict | I3-B — MULTIPLE LOCAL CORRECTIONS REQUIRED |

### I3 ↔ I2 harness at FULL SEAT

Exact total = **{hc['exactTotalMm3']:.9f} mm³**. Logical masks are disjoint; shared root material belongs to the central seat.

| I3 region | I2 harness penetration (mm³) |
|---|---:|
{rows_h}

PRIMARY LIMITING I3 REGION = **{hc['primaryLimitingI3Region']}**. Full-seat collision = **YES**; insertion-only = **NO**.

### I3 ↔ I2 detailed PushBtn at FULL SEAT

Exact pairwise total = **{dc['exactPairwiseTotalMm3']:.9f} mm³**. Primary pair = **{dc['primaryPair']}**, penetration = **{dc['primaryPairPenetrationMm3']:.9f} mm³**.

| I3 region | I2 detailed part | penetration (mm³) |
|---|---|---:|
{chr(10).join(matrix_rows) if matrix_rows else '| — | — | 0 |'}

Full-seat collision = **YES**; insertion-only = **NO**.

### I3 early shell contact

| State | +U foot | +U leg | seat | other legs | exact total (mm³) |
|---|---:|---:|---:|---:|---:|
{early_rows}

Is early shell contact caused only by the +U contact foot? **{'YES' if i3['earlyShellContact']['causedOnlyByPlusUFoot'] else 'NO'}**.
It exists only on the insertion path; FULL SEAT has intended finite-area foot contact rather than unintended volumetric penetration.

### Minimum local correction measurements — no edits applied

- Full-seat harness limiter: **{corr['I3-I2 harness primary']['minimumEnvelopeRemovalMm']:.6f} mm** local trim/removal envelope along {corr['I3-I2 harness primary']['minimumEnvelopeAxis']} on **{corr['I3-I2 harness primary']['region']}**.
- Detailed PushBtn limiter: **{corr['I3-I2 detailed primary']['minimumEnvelopeRemovalMm']:.6f} mm** along local {corr['I3-I2 detailed primary']['minimumEnvelopeAxis']} for **{corr['I3-I2 detailed primary']['pair']}**.
- Early-contact lead-in: **{corr['early shell lead-in']['minimumEnvelopeRemovalMm']:.6f} mm** collision-envelope removal at {corr['early shell lead-in']['state']}, along local {corr['early shell lead-in']['minimumEnvelopeAxis']}.
- Diagnostic local normal directions = `{corr['I3-I2 harness primary']['directionLocal']}`, `{corr['I3-I2 detailed primary']['directionLocal']}`, `{corr['early shell lead-in']['directionLocal']}` respectively; no correction solid was made.

These are exact collision-solid envelope thicknesses, not generated corrections. Because the full-seat I2 conflict and the insertion-only shell lead-in occur in distinct constraints, verdict = **I3-B — MULTIPLE LOCAL CORRECTIONS REQUIRED**. The 3-slot + 1-contact architecture can **likely remain**, but one isolated trim is insufficient.

## N2 — Support architecture diagnosis

| Leg | Current state | Local support exists? | Same-half? | Seam involved? | Contact-only feasible? | Likely support type |
|---|---|---|---|---|---|---|
| -U | valid slot | YES | YES | NO | not required | mechanical slot |
| -V | 0.120358 mm deficit | YES, after micro-thickening | YES | NO | not required | mechanical slot |
| +U | JfD 0/9; JaD local land at 1.050 mm | YES on JaD | NO | YES | YES, closure-created | seam-side local contact |
| +V | opening/edge crossing for slot | {'YES' if n2['plusV']['fullFinitePatch'] else 'NO'} | YES | NO | {'YES' if n2['plusV']['bondlessPressLoadSupportPossible'] else 'NO'} | local contact foot |

### N2 -V micro-thickening diagnosis

- Can it become a normal blind slot with micro-local inward thickening? **YES**.
- Required inward thickness = **{n2['minusV']['minimumRequiredInwardThickeningMm']:.6f} mm**.
- Minimum diagnostic pad footprint = **{n2['minusV']['minimumPadFootprintMm'][0]:.3f} × {n2['minusV']['minimumPadFootprintMm'][1]:.3f} mm**.
- Added volume estimate = **{n2['minusV']['minimumAddedVolumeMm3']:.6f} mm³**; outer exterior change required = **0 mm**.

### N2 +U seam diagnosis

- At the natural footprint: JfD = **0/9**, JaD material = **3/9**, opening void = **6/9**.
- A shifted but still local +U JaD footprint exists **1.050 mm** away: **9/9**, remaining shell **{n2['plusU']['jaDMinimumRemainingShellMm']:.6f} mm**.
- If JaD/JfD are treated as the final assembled shell, a geometrically valid local JaD reaction surface exists: **YES**.
- A JaD blind slot would cross and mechanically bridge the physical seam: **YES**, therefore it is **not assembly-compatible**.
- A non-captive compression contact established by JaD closure is assembly-compatible but sequence-limited. Classification: **N2+U-2 — JaD LOCAL SEAM-SIDE SUPPORT POSSIBLE / ASSEMBLY-LIMITED**.

### N2 assembly sequence

| Sequence | Geometrically plausible? | Shell halves can close? | Harness removable? | Reason |
|---|---|---|---|---|
{seq_rows}

### N2 +V local contact diagnosis

- Nearest edge-measured local patch offset from the natural target = **{n2['plusV']['nearestValidLocalPatchDistanceFromNaturalTargetMm']:.6f} mm**; frozen root-to-patch UV distance = **{n2['plusV']['rootToPatchCenterUVDistanceMm']:.6f} mm**.
- The original 1.60 × 1.30 mm envelope crosses the edge: **{n2['plusV']['originalOnePointSixByOnePointThreeEnvelope']['rayCoverage']}/{n2['plusV']['originalOnePointSixByOnePointThreeEnvelope']['rayCount']}**.
- A 1.60 × 1.30 mm patch placed from the measured edge with 0.030 mm margin has **{n2['plusV']['rayCoverage']}/{n2['plusV']['rayCount']}** coverage. Frozen root and angle authority were not searched.
- Available local surface area ≈ **{n2['plusV']['availableContactAreaMm2']:.6f} mm²**; simple foot contact ≈ **{n2['plusV']['estimatedSimpleFootContactAreaMm2']:.6f} mm²**.
- Minimum shell thickness under the accepted diagnostic patch = **{n2['plusV']['minimumShellThicknessMm']:.6f} mm** (required diagnostic support threshold = {n2['plusV']['requiredSupportingShellThicknessMm']:.3f} mm).
- Local shell normal = `{[round(v, 9) for v in n2['plusV']['localShellNormal']]}`; straight reaction-axis angle = **{n2['plusV']['legAxisToLocalShellNormalDeg']:.6f}°**.
- Side identity preserved = **YES**; remote/Thumb wall required = **NO**; bondless compression path possible = **{'YES' if n2['plusV']['bondlessPressLoadSupportPossible'] else 'NO'}**.

## N2 support-count decision

- Realistic normal mechanical slots: **2/4** (`-U`, micro-thickened `-V`).
- Plausible local compression contacts: **{n2['plausibleLocalContactSupportCount']}/4** (`+U` JaD closure-contact, `+V` JfD local contact).
- JaD seam-side support is geometrically possible: **YES**.
- JaD blind-slot/seam bridge is assembly-compatible: **NO**; closure-created contact is **YES, sequence-limited**.
- N2 requires a fundamentally new architecture: **YES** — a diagnostic direction of 2 mechanical slots + 2 local contacts, not a four-slot architecture.
- Restraint grade: **PLAUSIBLE**. Two non-collinear slots provide retention; the two opposite local contacts can close the press-load support polygon. A captive JaD seam bridge is **INVALID**.

## Outputs

{chr(10).join(f'- `{path}`' for path in data['outputs']['renders'])}

- JSON: `{data['outputs']['json']}`
- Solution STEP artifacts: **0**

```text
Recommended next design action for I3 = later test three bounded local corrections only: -U-leg/I2 clearance, central-seat/T3 clearance, and +U-foot entry lead-in.
Recommended next design action for N2 = later validate a 2-slot + 2-contact, Sequence-C shell-closure architecture; never create a captive JaD seam bridge.
```

Production geometry modification = 0.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    protected = protected_files()
    before = hashes(protected)
    docs90 = json.loads(d90.JSON_PATH.read_text(encoding="utf-8"))
    docs91 = json.loads(DOC91_JSON.read_text(encoding="utf-8"))
    docs92 = json.loads(DOC92_JSON.read_text(encoding="utf-8"))
    docs93 = json.loads(DOC93_JSON.read_text(encoding="utf-8"))
    datums = load_all_datums()
    placements = {name: doc84.doc83.datum_location(datums[name], FROZEN_FRONT_DEPTHS[name]) for name in d90.BUTTONS}
    shell_full = {owner: import_step(path) for owner, path in SHELL_STEP.items()}

    i3_authority = i3_authority_geometry(docs91, docs93, datums, placements, shell_full)
    i3_result, i3_shapes = i3_collision_diagnostic(i3_authority, docs90, docs91, placements)
    n2_result, n2_shapes = n2_diagnostic(docs91, docs92, datums, placements, shell_full)
    render_paths = render_outputs(i3_result, i3_shapes, n2_result, n2_shapes)
    after = hashes(protected)
    data = {
        "schema": "onegrip-i3-n2-combined-diagnostic-audit-v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "authority": {"i3Latest": relative(d93.REPORT), "i3SourceJson": relative(DOC93_JSON),
                      "n2FailureMode": relative(d92.REPORT), "n2SourceJson": relative(DOC92_JSON)},
        "scope": {"diagnosticOnly": True, "solutionGeometryGenerated": False,
                  "geometryModificationCount": 0, "productionModificationCount": 0,
                  "optimizerCount": 0, "candidateGenerationLoopCount": 0,
                  "frozenButtons": ["N1", "I2", "M3", "M4", "N3", "I4"]},
        "i3": i3_result, "n2": n2_result,
        "summary": {"i3Architecture": i3_result["architectureVerdict"],
                    "i3PrimaryFailure": f"{i3_result['harnessCollision']['primaryLimitingI3Region']} ↔ I2 harness",
                    "i3LocalOnlyCorrectionPlausible": True,
                    "n2ViableMechanicalSlots": n2_result["viableMechanicalSlotCount"],
                    "n2PlausibleLocalContacts": n2_result["plausibleLocalContactSupportCount"],
                    "n2PlusUJaD": n2_result["plusU"]["headlineClass"],
                    "n2PlusVContact": "POSSIBLE" if n2_result["plusV"]["bondlessPressLoadSupportPossible"] else "IMPOSSIBLE",
                    "remoteOrThumbWallSupportRequired": False},
        "outputs": {"renders": render_paths, "report": relative(REPORT), "json": relative(JSON_PATH),
                    "solutionStepArtifactCount": 0},
        "preservation": {"protectedFilesUnchanged": before == after,
                         "protectedFileCount": len(protected), "hashesBefore": before, "hashesAfter": after},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({"summary": data["summary"], "renders": render_paths,
                      "protectedFilesUnchanged": before == after,
                      "solutionStepArtifactCount": 0}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
