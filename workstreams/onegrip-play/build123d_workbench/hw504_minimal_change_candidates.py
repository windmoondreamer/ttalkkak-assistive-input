"""Analysis-only HW504 minimal-change candidates for the frozen OneGrip exterior.

The source STEP contains no named HW504 subcomponents or assembly mates.  This
module therefore separates *observed geometry* (exact cylinders, axes,
intersections and volumes) from *geometry-based functional inference*.  It
creates local comparison B-reps only.  No production shell, Finger geometry or
source reference is overwritten.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector, export_step, import_step

from .finger_controls_v2 import exact_distance
from .original_thumb_module_reuse_audit import (
    EPS,
    bbox_gap,
    bbox_row,
    center,
    intersection,
    load_current_shells,
    load_finger_references,
    load_target_parts,
    sha256,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build123d_workbench" / "out" / "hw504_minimal_change_candidates"
REPORT_OUTPUT = OUT_DIR / "hw504_minimal_change_candidates.json"

JAD_SOURCE = (
    ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
    / "JAD_EXTERIOR_LOWERED_THUMB_V1.step"
)
JFD_SOURCE = (
    ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"
    / "JFD_EXTERIOR_LOWERED_THUMB_V1.step"
)
FINGER_SOURCE = (
    ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
    / "FINGER_V2_ASSEMBLY_REFERENCE.step"
)
THUMB_SOURCE = (
    ROOT / "build123d_workbench" / "out" / "finger_thumb_joint_feasibility"
    / "THUMB_TARGET_EXACT_MODULE.step"
)

# Exact cylindrical-face evidence from the lowered HW504 occurrence.  The three
# mutually orthogonal directions intersect the neutral shaft line.  Keeping
# their line, direction and radii fixed is the kinematic freeze used here.
DATUM_P = np.asarray((-0.21604013507035, -23.14907664213591, 40.49617911468703), dtype=float)
DATUM_N = np.asarray((-0.000181853768751, -0.598493368976127, -0.801127739015953), dtype=float)
DATUM_U = np.asarray((0.999999460340440, 0.000710605462944, -0.000757864568375), dtype=float)
DATUM_V = np.cross(DATUM_N, DATUM_U)
DATUM_V /= np.linalg.norm(DATUM_V)
DATUM_N /= np.linalg.norm(DATUM_N)
DATUM_U /= np.linalg.norm(DATUM_U)

# Exact observed maximum cylindrical contact radii, plus a deliberately small
# 0.30 mm analysis guard.  This is a protected-datum envelope, not a claim that
# every enclosed voxel is a bearing.
DATUM_SPECS = {
    "NEUTRAL_STICK_AXIS_N": {"axis": DATUM_N, "radiusMm": 3.50, "guardMm": 0.30, "lengthMm": 34.0},
    "PIVOT_AXIS_U": {"axis": DATUM_U, "radiusMm": 4.50, "guardMm": 0.30, "lengthMm": 36.0},
    "PIVOT_AXIS_V": {"axis": DATUM_V, "radiusMm": 2.50, "guardMm": 0.30, "lengthMm": 36.0},
}

# Backplate local plane established from exact source surface/vertex alignment.
BACKPLATE_ORIGIN = np.asarray((-0.23581763, -4.41709540, 24.99272364), dtype=float)
BACKPLATE_U = np.asarray((1.0, 0.0, 0.0), dtype=float)
BACKPLATE_N = np.asarray((0.00017647, 0.60270162, 0.79796662), dtype=float)
BACKPLATE_N /= np.linalg.norm(BACKPLATE_N)
BACKPLATE_V = np.cross(BACKPLATE_N, BACKPLATE_U)
BACKPLATE_V /= np.linalg.norm(BACKPLATE_V)

EXPORT_NAMES = {
    "HW504_FUNCTIONAL_DATUM_REFERENCE.step",
    "CURRENT_HW504_COLLISION_MAP.step",
    "CANDIDATE_A_SHELL_RELIEF_ONLY.step",
    "CANDIDATE_B_SHELL_RELIEF_PLUS_NONFUNCTIONAL_TRIM.step",
    "CANDIDATE_C_MINIMAL_SUPPORT_REDESIGN.step",
    "BACKPLATE_INTERNAL_SPLIT_ADAPTER_PROPOSAL.step",
    "FULL_COMPARISON_REFERENCE.step",
}


def xyz(row: Iterable[float]) -> tuple[float, float, float]:
    return tuple(float(value) for value in row)


def label_copy(shape: Shape, label: str) -> Shape:
    result = shape.moved(shape.location)
    result.label = label
    return result


def axis_cylinder(point: np.ndarray, axis: np.ndarray, radius: float, length: float, label: str) -> Shape:
    axis = axis / np.linalg.norm(axis)
    hint = DATUM_U
    if abs(float(np.dot(axis, hint))) > 0.95:
        hint = DATUM_V
    x_dir = hint - axis * float(np.dot(axis, hint))
    x_dir /= np.linalg.norm(x_dir)
    plane = Plane(origin=xyz(point), x_dir=xyz(x_dir), z_dir=xyz(axis))
    result = plane.location * Cylinder(
        float(radius),
        float(length),
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def plane_box(
    center_row: np.ndarray,
    u: np.ndarray,
    normal: np.ndarray,
    width_u: float,
    width_v: float,
    depth_n: float,
    label: str,
) -> Shape:
    plane = Plane(origin=xyz(center_row), x_dir=xyz(u), z_dir=xyz(normal))
    result = plane.location * Box(
        float(width_u), float(width_v), float(depth_n),
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
    result.label = label
    return result


def fuse_all(shapes: list[Shape], label: str) -> Shape:
    if not shapes:
        raise ValueError(f"Cannot fuse empty shape list for {label}")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    result.label = label
    return result


def common_shapes(left: Shape, targets: dict[str, Shape], prefix: str) -> tuple[list[Shape], list[dict[str, object]]]:
    solids: list[Shape] = []
    rows: list[dict[str, object]] = []
    for target_name, target in targets.items():
        volume, common = intersection(left, target, f"{prefix}__{target_name}")
        if common is None or volume <= EPS:
            continue
        solids.append(common)
        rows.append(
            {
                "target": target_name,
                "penetrationVolumeMm3": volume,
                "centroidMm": center(common).tolist(),
                "bboxMm": bbox_row(common),
            }
        )
    return solids, rows


def shape_volume(shape: Shape | None) -> float:
    return 0.0 if shape is None else float(shape.volume)


def common_volume(left: Shape, right: Shape) -> float:
    return intersection(left, right)[0]


def remaining_collision(shape: Shape, targets: dict[str, Shape]) -> dict[str, object]:
    rows = []
    total = 0.0
    for name, target in targets.items():
        volume = common_volume(shape, target)
        if volume > EPS:
            rows.append({"target": name, "penetrationVolumeMm3": volume})
            total += volume
    clearance = 0.0 if rows else min(exact_distance(shape, target) for target in targets.values())
    return {
        "penetrationVolumeMm3": total,
        "minimumClearanceMm": clearance,
        "intersectingPairCount": len(rows),
        "collisions": rows,
    }


def build_datum_reference() -> tuple[dict[str, Shape], Shape, dict[str, object]]:
    datums: dict[str, Shape] = {}
    rows: dict[str, object] = {}
    for name, spec in DATUM_SPECS.items():
        exact = axis_cylinder(
            DATUM_P, np.asarray(spec["axis"]), float(spec["radiusMm"]), float(spec["lengthMm"]),
            f"{name}__EXACT_OBSERVED_RADIUS",
        )
        guard = axis_cylinder(
            DATUM_P, np.asarray(spec["axis"]), float(spec["radiusMm"] + spec["guardMm"]),
            float(spec["lengthMm"]), f"{name}__PROTECTED_GUARD",
        )
        datums[f"{name}__EXACT"] = exact
        datums[f"{name}__GUARD"] = guard
        rows[name] = {
            "pointMm": DATUM_P.tolist(),
            "direction": np.asarray(spec["axis"]).tolist(),
            "observedMaximumContactRadiusMm": spec["radiusMm"],
            "analysisGuardMm": spec["guardMm"],
            "protectedEnvelopeLengthMm": spec["lengthMm"],
            "source": "exact coaxial cylindrical-face extraction from imported HW504 solids",
        }
    envelope = fuse_all([shape for name, shape in datums.items() if name.endswith("__GUARD")], "HW504_PROTECTED_DATUM_ENVELOPE")
    return datums, envelope, rows


def build_split_backplate_adapter(backplate: Shape, protected: Shape) -> tuple[Shape, Shape, dict[str, object]]:
    """Planar split adapter concept behind the exact Backplate.

    The adapter is intentionally a separate, internal, no-undercut frame.  It
    has a broad planar locating face, one asymmetric anti-rotation key and a
    center opening.  It does not add any exterior boss, tube or flange.
    """
    center_row = BACKPLATE_ORIGIN + BACKPLATE_V * -8.0 + BACKPLATE_N * -10.15
    outer = plane_box(center_row, BACKPLATE_U, BACKPLATE_N, 42.0, 64.0, 2.40, "ADAPTER_OUTER")
    inner = plane_box(center_row, BACKPLATE_U, BACKPLATE_N, 33.0, 52.0, 3.20, "ADAPTER_CENTER_OPENING")
    frame = outer - inner

    # Asymmetric internal key: anti-rotation without an external cylindrical boss.
    key_center = center_row + BACKPLATE_U * 15.6 + BACKPLATE_V * 24.8 + BACKPLATE_N * 1.5
    key = plane_box(key_center, BACKPLATE_U, BACKPLATE_N, 5.2, 8.0, 5.4, "ADAPTER_ANTI_ROTATION_KEY")
    adapter = frame.fuse(key)

    # Preserve cartridge and kinematic service volumes; the exact Backplate is
    # the only intended locating contact in this conceptual proposal.
    adapter = adapter - protected
    adapter = adapter.clean()
    adapter.label = "BACKPLATE_INTERNAL_SPLIT_ADAPTER_FULL"

    # Split at the immutable X=0 shell seam for removal/service.  Oversized
    # halfspaces make the split deterministic and printable on a planar face.
    positive = Box(80.0, 140.0, 140.0, align=(Align.MIN, Align.CENTER, Align.CENTER)).moved(Location(
        # Default box begins at X=0; translate Y/Z only to cover this workspace.
        Vector(0.0, -10.0, 25.0)
    ))
    negative = Box(80.0, 140.0, 140.0, align=(Align.MAX, Align.CENTER, Align.CENTER)).moved(Location(
        Vector(0.0, -10.0, 25.0)
    ))
    jad = (adapter & positive).clean()
    jfd = (adapter & negative).clean()
    jad.label = "JAD_INTERNAL_BACKPLATE_ADAPTER_HALF"
    jfd.label = "JFD_INTERNAL_BACKPLATE_ADAPTER_HALF"

    metrics = {
        "architecture": "ORIGINAL BACKPLATE + NEW INTERNAL SHELL-SIDE SPLIT ADAPTER",
        "backplateGeometryChanged": False,
        "adapterLocation": "negative-normal/rear side of exact Backplate; internal comparison reference only",
        "locating": "42 x 64 mm nominal planar split frame with center service opening",
        "antiRotation": "single asymmetric 5.2 x 8.0 mm rectangular internal key",
        "service": "two halves split at X=0; straight pull with no modeled undercut",
        "fdm": {
            "minimumNominalWallMm": 2.40,
            "planarPrintFace": True,
            "externalBossTubeFlangeCount": 0,
        },
        "volumeMm3": float(jad.volume + jfd.volume),
        "backplatePenetrationMm3": common_volume(adapter, backplate),
        "protectedDatumPenetrationMm3": common_volume(adapter, protected),
        "status": "CONCEPT FEASIBLE; shell attachment/capture fastener requires a later approved stage",
    }
    return jad, jfd, metrics


def export_compound(path: Path, children: list[Shape], label: str) -> None:
    rows = []
    for index, shape in enumerate(children, 1):
        copy = shape.moved(shape.location)
        if not copy.label:
            copy.label = f"{label}_{index}"
        rows.append(copy)
    export_step(Compound(children=rows, label=label), path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parts = load_target_parts()
    by_name = {part.name: part.shape for part in parts}
    hw_a = by_name["THUMB_JOYSTICK_HW504_COMPONENT_1"]
    hw_b = by_name["THUMB_JOYSTICK_HW504_COMPONENT_2"]
    backplate = by_name["THUMB_BACKPLATE"]
    shells = load_current_shells()
    finger_switches, finger_carriers = load_finger_references()
    n_targets = {
        "FINGER_SWITCH_N1": finger_switches["N1"],
        "FINGER_SWITCH_N2": finger_switches["N2"],
        "FINGER_CARRIER_N1_N2_SHARED": finger_carriers["N1_N2_SHARED_CARRIER"],
    }
    shell_targets = {f"SHELL_{name}": shape for name, shape in shells.items()}
    all_obstacles = {**shell_targets, **n_targets}

    datums, protected, datum_rows = build_datum_reference()

    # Exact current collision decomposition.
    collision_debug: list[Shape] = []
    collision_rows: dict[str, list[dict[str, object]]] = {}
    conflict_tools: dict[str, Shape] = {}
    conflict_sets: dict[str, list[Shape]] = {}
    for label, hw in (("HW504_A", hw_a), ("HW504_B", hw_b)):
        commons, rows = common_shapes(hw, all_obstacles, f"CURRENT_COLLISION__{label}")
        for row, common in zip(rows, commons):
            protected_v = common_volume(common, protected)
            row.update(
                {
                    "protectedDatumOverlapMm3": protected_v,
                    "nonProtectedOverlapMm3": max(0.0, float(row["penetrationVolumeMm3"]) - protected_v),
                    "functionalClassification": (
                        "PROTECTED_DATUM_OVERLAP" if protected_v > EPS else "OUTSIDE_PROTECTED_DATUM_ENVELOPE"
                    ),
                    "shellInternalReliefFeasibility": (
                        "EXACT CUT POSSIBLE; exterior-boundary preservation not proven"
                        if str(row["target"]).startswith("SHELL_")
                        else "NOT APPLICABLE"
                    ),
                    "localHwTrimFeasibility": (
                        "NONFUNCTIONAL-ONLY TRIM INSUFFICIENT" if protected_v > EPS else "LOCAL TRIM CANDIDATE"
                    ),
                }
            )
        collision_rows[label] = rows
        if commons:
            conflict_sets[label] = commons
            conflict_tools[label] = fuse_all(commons, f"{label}_ALL_EXACT_CONFLICT_TOOL")
            collision_debug.extend(commons)

    # Candidate A: exact source HW and Backplate; shell boolean only.  This is
    # deliberately not accepted merely because the boolean removes overlap:
    # external-boundary preservation of the exact review shells must be proven.
    shell_a = {
        name: (shape - backplate - hw_a - hw_b).clean()
        for name, shape in shells.items()
    }

    # Candidate B: candidate-A shell plus only the conflict portion lying
    # outside the protected datum envelope removed from each HW solid.
    b_hw: dict[str, Shape] = {}
    b_removed: dict[str, float] = {}
    for label, hw in (("HW504_A", hw_a), ("HW504_B", hw_b)):
        candidate = hw
        for common in conflict_sets[label]:
            outside_protected = common - protected
            if outside_protected is not None and len(outside_protected.solids()) > 0 and float(outside_protected.volume) > EPS:
                candidate = candidate - outside_protected
        candidate = candidate.clean()
        candidate.label = f"CANDIDATE_B_{label}_NONFUNCTIONAL_TRIM"
        b_hw[label] = candidate
        b_removed[label] = max(0.0, float(hw.volume - candidate.volume))

    # Candidate C: remove all exact conflict material, then add a new planar
    # rear support bridge outside the N1/N2 collision box.  The center/axis/
    # radii are unchanged reference datums.  This is a support reform proposal,
    # not a production-ready recreation of the imported mechanism.
    c_hw: dict[str, Shape] = {}
    c_removed: dict[str, float] = {}
    for label, hw in (("HW504_A", hw_a), ("HW504_B", hw_b)):
        candidate = hw
        for common in conflict_sets[label]:
            candidate = candidate - common
        candidate = candidate.clean()
        candidate.label = f"CANDIDATE_C_{label}_CONFLICT_REMOVED_CORE"
        c_hw[label] = candidate
        c_removed[label] = max(0.0, float(hw.volume - candidate.volume))

    bridge_center = DATUM_P + DATUM_N * 10.2 + DATUM_V * 9.0
    bridge_outer = plane_box(bridge_center, DATUM_U, DATUM_N, 27.0, 13.0, 3.2, "C_SUPPORT_BRIDGE_OUTER")
    bridge_inner = plane_box(bridge_center, DATUM_U, DATUM_N, 19.0, 6.5, 4.0, "C_SUPPORT_BRIDGE_OPENING")
    bridge = (bridge_outer - bridge_inner - protected)
    for obstacle in all_obstacles.values():
        bridge = bridge - obstacle
    bridge = bridge.clean()
    bridge.label = "CANDIDATE_C_NEW_PLANAR_SUPPORT_BRIDGE"

    adapter_jad, adapter_jfd, adapter_metrics = build_split_backplate_adapter(backplate, protected)

    # Candidate metrics against immutable Finger and shell references.
    candidate_rows: dict[str, object] = {}
    candidate_specs = {
        "A": {"hw": {"HW504_A": hw_a, "HW504_B": hw_b}, "shell": shell_a, "added": []},
        "B": {"hw": b_hw, "shell": shell_a, "added": []},
        "C": {"hw": c_hw, "shell": shells, "added": [bridge]},
    }
    original_hw_volume = float(hw_a.volume + hw_b.volume)
    original_protected_volume = common_volume(hw_a, protected) + common_volume(hw_b, protected)
    for name, spec in candidate_specs.items():
        hw_shapes = list(spec["hw"].values())
        analysis_shapes = [*hw_shapes, *spec["added"]]
        analysis_compound = Compound(children=analysis_shapes)
        shell_test_targets = {f"SHELL_{key}": value for key, value in spec["shell"].items()}
        finger_result = remaining_collision(analysis_compound, n_targets)
        shell_result = remaining_collision(analysis_compound, shell_test_targets)
        candidate_protected_volume = sum(common_volume(shape, protected) for shape in hw_shapes)
        protected_loss = max(0.0, original_protected_volume - candidate_protected_volume)
        removed = max(0.0, original_hw_volume - sum(float(shape.volume) for shape in hw_shapes))
        added = sum(float(shape.volume) for shape in spec["added"])
        candidate_rows[name] = {
            "description": {
                "A": "shell internal relief only; all 20 original parts exact",
                "B": "shell relief plus HW material trim outside protected datum envelope",
                "C": "all exact conflict material removed plus new planar support bridge; original kinematic datums retained as references",
            }[name],
            "exactOriginalPartsRetainedCount": 20 if name == "A" else 18,
            "exactOriginalPartsRetainedRatioPercent": 100.0 if name == "A" else 90.0,
            "backplateExactAsIs": True,
            "fingerModificationCount": 0,
            "exteriorModificationCount": 0,
            "hwRemovedVolumeMm3": removed,
            "hwAddedVolumeMm3": added,
            "protectedDatumMaterialLossMm3": protected_loss,
            "fingerClearance": finger_result,
            "shellClearance": shell_result,
            "minimumNominalNewWallMm": 3.2 if name == "C" else None,
            "assemblyServicePath": {
                "A": "unchanged original HW insertion; relief boundary has zero nominal clearance",
                "B": "unchanged original HW insertion; trimmed surfaces need finishing/validation",
                "C": "planar rear bridge is seam-loadable; actual bearing retention sequence is not validated",
            }[name],
            "fdmFeasibility": {
                "A": "shell relief exact-zero-clearance and external-boundary risk: FAIL",
                "B": "trim is manufacturable but protected collision remains if reported above: CONDITIONAL",
                "C": "new bridge is planar/no-under-cut, but recreated support strength and bearing capture require validation",
            }[name],
            "kinematicGeometryChange": (
                "0 at source-part level" if name == "A" else
                ("0 only where protected envelope is untouched" if protected_loss <= EPS else "NONZERO")
            ),
        }

    # Explicit component decomposition, keeping observation separate from inference.
    decomposition = {
        "HW504_A": {
            "sourceExactSolidVolumeMm3": float(hw_a.volume),
            "bboxMm": bbox_row(hw_a),
            "observedGeometry": "1104 faces; dense fixed-body/board/support bulk with N/U/V cylindrical collars and holes",
            "inferredRole": "primarily fixed sensor/PCB/housing/support body",
            "motionClass": "FIXED BODY inference; imported STEP contains no mates",
            "protected": ["N/U/V axis lines", "coaxial collars/holes", "mutual HW504 interface", "original mounting-hole datums"],
            "structuralBulk": "large rectangular/irregular body surrounding the three-axis collar cluster",
            "mountingGeometry": "outer tabs/holes and lower body regions; exact semantic ownership unknown",
            "removableNonfunctionalRegionRule": "only exact conflict material outside the protected-datum envelope; strength is not implied",
            "disposition": "KEEP for A; TRIM-CANDIDATE for B; SUPPORT-REDESIGN for C",
        },
        "HW504_B": {
            "sourceExactSolidVolumeMm3": float(hw_b.volume),
            "bboxMm": bbox_row(hw_b),
            "observedGeometry": "78 faces; compact tri-axis cylindrical gimbal/stem body touching the Small joystick attachment",
            "inferredRole": "moving gimbal/stick-side body and bearing/contact counterpart",
            "motionClass": "MOVING BODY inference; imported STEP contains no mates",
            "protected": ["neutral shaft axis/r3.5 surface", "U r4.5/r4.25 coaxial faces", "V r2.5/r1.5 coaxial faces", "attachment interface"],
            "structuralBulk": "compact material between the intersecting N/U/V cylinders",
            "mountingGeometry": "pivot journals/contact cylinders; should not be treated as sacrificial mounting tabs",
            "removableNonfunctionalRegionRule": "none assumed unless exact conflict lies wholly outside protected-datum envelope",
            "disposition": "KEEP for A; KEEP/limited TRIM for B; SUPPORT-REDESIGN only as last approved option",
        },
    }

    exports: dict[str, Path] = {
        "HW504_FUNCTIONAL_DATUM_REFERENCE.step": OUT_DIR / "HW504_FUNCTIONAL_DATUM_REFERENCE.step",
        "CURRENT_HW504_COLLISION_MAP.step": OUT_DIR / "CURRENT_HW504_COLLISION_MAP.step",
        "CANDIDATE_A_SHELL_RELIEF_ONLY.step": OUT_DIR / "CANDIDATE_A_SHELL_RELIEF_ONLY.step",
        "CANDIDATE_B_SHELL_RELIEF_PLUS_NONFUNCTIONAL_TRIM.step": OUT_DIR / "CANDIDATE_B_SHELL_RELIEF_PLUS_NONFUNCTIONAL_TRIM.step",
        "CANDIDATE_C_MINIMAL_SUPPORT_REDESIGN.step": OUT_DIR / "CANDIDATE_C_MINIMAL_SUPPORT_REDESIGN.step",
        "BACKPLATE_INTERNAL_SPLIT_ADAPTER_PROPOSAL.step": OUT_DIR / "BACKPLATE_INTERNAL_SPLIT_ADAPTER_PROPOSAL.step",
        "FULL_COMPARISON_REFERENCE.step": OUT_DIR / "FULL_COMPARISON_REFERENCE.step",
    }
    # The shell-heavy references are immutable for this study and expensive to
    # serialise.  Reuse an existing export after the first exact build.  B/C are
    # intentionally lightweight component prototypes; their shell/Finger test
    # references and exact metrics remain in JSON instead of duplicating the
    # multi-megabyte frozen shell in every STEP.
    immutable_exports = (
        ("HW504_FUNCTIONAL_DATUM_REFERENCE.step", [hw_a, hw_b, *datums.values()], "HW504_FUNCTIONAL_DATUM_REFERENCE"),
        ("CURRENT_HW504_COLLISION_MAP.step", [hw_a, hw_b, *n_targets.values(), *shells.values(), *collision_debug], "CURRENT_HW504_COLLISION_MAP"),
        ("CANDIDATE_A_SHELL_RELIEF_ONLY.step", [*shell_a.values(), hw_a, hw_b, backplate], "CANDIDATE_A_SHELL_RELIEF_ONLY"),
        ("BACKPLATE_INTERNAL_SPLIT_ADAPTER_PROPOSAL.step", [backplate, adapter_jad, adapter_jfd], "BACKPLATE_INTERNAL_SPLIT_ADAPTER_PROPOSAL"),
        ("FULL_COMPARISON_REFERENCE.step", [*by_name.values(), *shells.values(), *n_targets.values(), adapter_jad, adapter_jfd, *datums.values()], "HW504_MINIMAL_CHANGE_FULL_COMPARISON_REFERENCE"),
    )
    for name, children, label in immutable_exports:
        if not exports[name].exists():
            export_compound(exports[name], children, label)
    export_compound(
        exports["CANDIDATE_B_SHELL_RELIEF_PLUS_NONFUNCTIONAL_TRIM.step"],
        [*b_hw.values(), backplate, *datums.values()],
        "CANDIDATE_B_LIGHTWEIGHT_HW_TRIM_PROTOTYPE__USES_CANDIDATE_A_SHELL_REFERENCE",
    )
    export_compound(
        exports["CANDIDATE_C_MINIMAL_SUPPORT_REDESIGN.step"],
        [*c_hw.values(), bridge, backplate, *datums.values()],
        "CANDIDATE_C_LIGHTWEIGHT_SUPPORT_REFORM_PROTOTYPE__USES_FROZEN_SHELL_REFERENCES",
    )

    source_hashes = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in (JAD_SOURCE, JFD_SOURCE, FINGER_SOURCE, THUMB_SOURCE)
    }
    report = {
        "schema": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL OCCT EXACT B-REP / ANALYSIS PROTOTYPES ONLY / PRODUCTION WRITE 0 / Onshape 0",
        "hardFreeze": {
            "latestFinger8": True,
            "maximumLoweredThumbExterior": True,
            "joystickOpening": True,
            "thumbButtonPositions": True,
            "gripExterior": True,
            "fingerGeometryModificationCount": 0,
            "productionExteriorModificationCount": 0,
            "sourceOriginalPartOverwriteCount": 0,
        },
        "sourceSha256": source_hashes,
        "semanticLimit": "HW504 is an imported fused STEP occurrence without named subcomponents or mates; roles are geometry-based inference and are not BOM/vendor confirmation.",
        "functionalDatumFreeze": datum_rows,
        "kinematicFreeze": {
            "joystickCenterChangeMm": 0.0,
            "neutralAxisAngularChangeDeg": 0.0,
            "pivotAxisUAngularChangeDeg": 0.0,
            "pivotAxisVAngularChangeDeg": 0.0,
            "rangeChange": "NOT MODELED; no source motion mates exist",
            "actuatorStickGeometryChange": 0,
            "buttonRelativeGeometryChangeMm": 0.0,
            "bearingContactDatumChangeMm": 0.0,
            "travelGeometryChange": 0,
        },
        "functionalDecomposition": decomposition,
        "collisionDecomposition": collision_rows,
        "priorityOrderApplied": [
            "1 shell internal relief analysis",
            "2 HW nonfunctional-only trim",
            "3 shell-side Backplate adapter",
            "4 HW support reform",
            "5 functional mechanism change forbidden without separate approval",
        ],
        "candidates": candidate_rows,
        "prototypeComposition": {
            "A": "modified comparison shell halves + exact HW A/B + exact Backplate",
            "B": "lightweight modified HW A/B + exact Backplate + datum references; uses Candidate-A shell STEP",
            "C": "lightweight modified HW A/B + new bridge + exact Backplate + datum references; frozen shells are referenced, not duplicated",
        },
        "backplateAdapter": adapter_metrics,
        "decision": {
            "preferredCandidate": "PENDING exact result gate",
            "reason": "Populated after exact collision/protected-datum metrics are evaluated.",
        },
        "finalFields": {
            "HW504_A": "PENDING",
            "HW504_B": "PENDING",
            "BACKPLATE": "AS-IS",
            "NEW_INTERNAL_ADAPTER": "YES - analysis proposal only",
            "KINEMATICS": "0 datum change; range not dynamically validated",
            "EXACT_ORIGINAL_PARTS_RETAINED": "PENDING candidate selection",
            "ORIGINAL_REUSE_RATIO": "PENDING candidate selection",
            "FINGER_MODIFICATION": "0 / NOT REQUIRED BY POLICY; unresolved collision may remain",
            "EXTERIOR_MODIFICATION": "0 / REQUIRED TO REMAIN 0",
        },
        "outputs": {},
        "stop": "STOP AFTER COMPARISON; DO NOT APPLY TO PRODUCTION CAD",
    }

    # Deterministic gate.  A cannot be selected because the earlier exact shell
    # relief is not proven internal-only.  B is accepted only if it clears both
    # obstacle groups without protected material loss.  Otherwise C remains a
    # study, not an approval, if it also loses protected material or collides.
    b = report["candidates"]["B"]
    c = report["candidates"]["C"]
    if (
        b["protectedDatumMaterialLossMm3"] <= EPS
        and b["fingerClearance"]["penetrationVolumeMm3"] <= EPS
        and b["shellClearance"]["penetrationVolumeMm3"] <= EPS
    ):
        report["decision"] = {"preferredCandidate": "B", "reason": "clears exact shell/Finger obstacles with protected datum loss 0"}
    elif (
        c["protectedDatumMaterialLossMm3"] <= EPS
        and c["fingerClearance"]["penetrationVolumeMm3"] <= EPS
        and c["shellClearance"]["penetrationVolumeMm3"] <= EPS
    ):
        report["decision"] = {"preferredCandidate": "C", "reason": "B leaves protected conflict; C clears exact obstacles with protected datum loss 0"}
    else:
        report["decision"] = {
            "preferredCandidate": "NONE APPROVED",
            "reason": "no candidate simultaneously proves zero protected-datum loss, zero frozen-Finger penetration and zero shell penetration while preserving exterior",
        }

    selected = report["decision"]["preferredCandidate"]
    if selected in ("B", "C"):
        report["finalFields"].update(
            {
                "HW504_A": "TRIM" if selected == "B" else "REDESIGN SUPPORT",
                "HW504_B": "TRIM" if selected == "B" else "REDESIGN SUPPORT",
                "EXACT_ORIGINAL_PARTS_RETAINED": "18 / 20",
                "ORIGINAL_REUSE_RATIO": "90.0 % exact-part geometry; functional datum reuse separately preserved",
            }
        )
    else:
        report["finalFields"].update(
            {
                "HW504_A": "KEEP pending approved collision solution",
                "HW504_B": "KEEP pending approved collision solution",
                "EXACT_ORIGINAL_PARTS_RETAINED": "20 / 20 in frozen source; no production candidate approved",
                "ORIGINAL_REUSE_RATIO": "100.0 % in source reference / 0 approved collision-free implementation",
            }
        )

    report["outputs"] = {
        name: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
        for name, path in exports.items()
    }
    REPORT_OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_OUTPUT.relative_to(ROOT)), "decision": report["decision"], "candidates": candidate_rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
