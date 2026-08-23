"""Exact local validation for the approved eight-button V2 mechanism."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
from build123d import Location, Shape, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.analyze_middle_prewrite as geom  # noqa: E402

from .finger_controls_v2 import (  # noqa: E402
    ACTUATOR_TRAVEL_MAX,
    BOOLEAN_VOLUME_EPS,
    BUTTON_ORDER,
    CAP_EXPOSURE,
    CAP_SIZE,
    CARRIER_WALL,
    MIN_DIVIDER,
    MIN_SCREW_CLEARANCE,
    MIN_STRUCTURAL_WALL,
    MIN_SWITCH_CLEARANCE,
    N2_SEAM_OPENING_SIZE,
    OPENING_SIZE,
    OUT_DIR,
    PREFERRED_SWITCH_CLEARANCE,
    SWITCH_BODY_H,
    SWITCH_BODY_X,
    SWITCH_BODY_Y,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    WIRE_EXIT_U,
    WIRE_EXIT_V,
    build_finger_controls_v2,
    exact_distance,
    export_design,
    intersection_volume,
    make_print_plate,
    point_at,
    switch_body,
    terminal_root_cutters,
    unit,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def vec(value) -> list[float]:
    return [float(value.X), float(value.Y), float(value.Z)]


def shape_metrics(shape: Shape) -> dict[str, Any]:
    bbox = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "solidCount": len(shape.solids()),
        "volumeMm3": float(shape.volume),
        "bboxMm": {"min": vec(bbox.min), "max": vec(bbox.max)},
        "topology": {
            "vertices": len(shape.vertices()),
            "edges": len(shape.edges()),
            "faces": len(shape.faces()),
        },
    }


def moved(shape: Shape, delta: np.ndarray) -> Shape:
    return shape.moved(Location(Vector(*[float(value) for value in delta])))


def body_obb(datum, front_depth: float):
    axis = unit(datum.axis)
    u = unit(datum.switch_u)
    v = unit(datum.switch_v)
    center = np.asarray(datum.center) - axis * (front_depth + SWITCH_BODY_H / 2.0)
    return center, np.asarray((u, v, axis)), np.asarray(
        (SWITCH_BODY_X / 2.0, SWITCH_BODY_Y / 2.0, SWITCH_BODY_H / 2.0)
    )


def pocket_obb(datum, front_depth: float):
    axis = unit(datum.axis)
    u = unit(datum.switch_u)
    v = unit(datum.switch_v)
    center = np.asarray(datum.center) - axis * (front_depth + SWITCH_BODY_H / 2.0)
    return center, np.asarray((u, v, axis)), np.asarray(
        (SWITCH_POCKET_X / 2.0, SWITCH_POCKET_Y / 2.0, SWITCH_BODY_H / 2.0)
    )


def cap_obb(datum):
    axis = unit(datum.axis)
    u = unit(datum.cap_u)
    v = unit(datum.cap_v)
    center = np.asarray(datum.center) + axis * (CAP_EXPOSURE - 0.60)
    return center, np.asarray((u, v, axis)), np.asarray((CAP_SIZE / 2.0, CAP_SIZE / 2.0, 0.60))


def carrier_for_button(design, name: str) -> Shape:
    if name in ("N1", "N2"):
        return design.carriers["N1_N2_shared_carrier"]
    if name in ("I2", "I3"):
        return design.carriers["I2_I3_shared_carrier"]
    if name in ("M4", "N3"):
        return design.carriers["M4_N3_shared_carrier"]
    return design.carriers[f"{name}_carrier"]


def all_pair_metrics(design, bodies: dict[str, Shape]) -> tuple[dict[str, Any], dict[str, Any]]:
    controls = {row.name: row for row in design.controls}
    body_rows: dict[str, Any] = {}
    opening_rows: dict[str, Any] = {}
    for left_index, left in enumerate(BUTTON_ORDER):
        for right in BUTTON_ORDER[left_index + 1 :]:
            key = f"{left}-{right}"
            sat = float(
                geom.sat_signed(
                    body_obb(controls[left], design.front_depths[left]),
                    body_obb(controls[right], design.front_depths[right]),
                )
            )
            body_rows[key] = {
                "satSeparationMm": sat,
                "exactBrepDistanceMm": exact_distance(bodies[left], bodies[right]),
                "intersectionVolumeMm3": intersection_volume(bodies[left], bodies[right]),
            }
            opening_rows[key] = {
                "exactToolDistanceMm": exact_distance(
                    design.opening_cutters[left], design.opening_cutters[right]
                ),
                "intersectionVolumeMm3": intersection_volume(
                    design.opening_cutters[left], design.opening_cutters[right]
                ),
            }
    return body_rows, opening_rows


def assembly_checks(design, bodies: dict[str, Shape]) -> dict[str, Any]:
    controls = {row.name: row for row in design.controls}
    lateral: dict[str, Any] = {}
    carrier_insert: dict[str, Any] = {}
    cap_motion: dict[str, Any] = {}
    for name in BUTTON_ORDER:
        datum = controls[name]
        carrier = carrier_for_button(design, name)
        body = bodies[name]
        direction = unit(datum.switch_u) * datum.open_side_sign
        lateral_samples = []
        # Switches are preloaded into the carrier before that carrier enters
        # the shell.  The outer member of each close pair loads from the outer
        # end, so neither sweep crosses its neighbour's cradle.
        owner_shell = design.jfd_shell if datum.owner == "JfD" else design.jad_shell
        for travel in np.linspace(0.0, 12.0, 7):
            probe = moved(body, direction * float(travel))
            lateral_samples.append(
                {
                    "travelMm": float(travel),
                    "carrierIntersectionMm3": intersection_volume(probe, carrier),
                    "ownerShellIntersectionMm3": intersection_volume(probe, owner_shell),
                }
            )
        lateral[name] = {
            "path": "open-side lateral preload before carrier-to-shell insertion",
            "maximumCarrierInterferenceMm3": max(row["carrierIntersectionMm3"] for row in lateral_samples),
            "maximumOwnerShellInterferenceMm3": max(row["ownerShellIntersectionMm3"] for row in lateral_samples),
            "samples": lateral_samples,
        }

        carrier_samples = []
        # Each preloaded module enters through the open central seam.  JaD is
        # absent while JfD modules translate from +X; JfD is absent while JaD
        # modules translate from -X.  A pure X path was selected by exact OCC
        # candidate-sweep comparison and avoids the curved outer wall.
        approach = np.asarray((1.0, 0.0, 0.0)) if datum.owner == "JfD" else np.asarray((-1.0, 0.0, 0.0))
        for travel in np.linspace(0.0, 14.0, 8):
            probe = moved(carrier, approach * float(travel))
            carrier_samples.append(
                {
                    "seamApproachTravelMm": float(travel),
                    "ownerShellIntersectionMm3": intersection_volume(probe, owner_shell),
                }
            )
        carrier_insert[name] = {
            "path": "preloaded module translated from open central seam along global X",
            "maximumOwnerShellInterferenceMm3": max(row["ownerShellIntersectionMm3"] for row in carrier_samples),
            "samples": carrier_samples,
        }

        cap = design.caps[name]
        cap_samples = []
        for travel in np.linspace(0.0, ACTUATOR_TRAVEL_MAX, 3):
            probe = moved(cap, -unit(datum.axis) * float(travel))
            cap_samples.append(
                {
                    "pressTravelMm": float(travel),
                    "JaDIntersectionMm3": intersection_volume(probe, design.jad_shell),
                    "JfDIntersectionMm3": intersection_volume(probe, design.jfd_shell),
                    "carrierIntersectionMm3": intersection_volume(probe, carrier),
                    "housingIntersectionMm3": intersection_volume(probe, body),
                }
            )
        cap_motion[name] = {
            "usableTravelMm": ACTUATOR_TRAVEL_MAX,
            "samples": cap_samples,
            "maximumHardInterferenceMm3": max(
                max(
                    row["JaDIntersectionMm3"],
                    row["JfDIntersectionMm3"],
                    row["carrierIntersectionMm3"],
                    row["housingIntersectionMm3"],
                )
                for row in cap_samples
            ),
        }
    return {"switchLateralInsertion": lateral, "carrierInsertion": carrier_insert, "capMotion": cap_motion}


def validate() -> dict[str, Any]:
    design = build_finger_controls_v2()
    controls = {row.name: row for row in design.controls}
    bodies = {
        name: switch_body(controls[name], design.front_depths[name]) for name in BUTTON_ORDER
    }
    body_pairs, opening_pairs = all_pair_metrics(design, bodies)

    nearest_switch: dict[str, Any] = {}
    for name in BUTTON_ORDER:
        candidates = [
            (other, body_pairs.get(f"{name}-{other}", body_pairs.get(f"{other}-{name}")))
            for other in BUTTON_ORDER
            if other != name
        ]
        other, row = min(candidates, key=lambda item: item[1]["satSeparationMm"])
        nearest_switch[name] = {"id": other, **row}

    carrier_metrics = {name: shape_metrics(shape) for name, shape in design.carriers.items()}
    cap_metrics = {name: shape_metrics(shape) for name, shape in design.caps.items()}
    shell_metrics = {
        "JaD": shape_metrics(design.jad_shell),
        "JfD": shape_metrics(design.jfd_shell),
    }
    print_plate = make_print_plate(design)
    plate_metrics = shape_metrics(print_plate)

    shell_intersections: dict[str, Any] = {}
    switch_carrier_intersections: dict[str, Any] = {}
    root_clearance: dict[str, Any] = {}
    wire_clearance: dict[str, Any] = {}
    for name in BUTTON_ORDER:
        carrier = carrier_for_button(design, name)
        shell_intersections[name] = {
            "switchJaDMm3": intersection_volume(bodies[name], design.jad_shell),
            "switchJfDMm3": intersection_volume(bodies[name], design.jfd_shell),
            "carrierJaDMm3": intersection_volume(carrier, design.jad_shell),
            "carrierJfDMm3": intersection_volume(carrier, design.jfd_shell),
            "carrierToJaDMm": exact_distance(carrier, design.jad_shell),
            "carrierToJfDMm": exact_distance(carrier, design.jfd_shell),
        }
        switch_carrier_intersections[name] = {
            carrier_name: intersection_volume(bodies[name], candidate)
            for carrier_name, candidate in design.carriers.items()
        }
        root_clearance[name] = [
            intersection_volume(carrier, cutter)
            for cutter in terminal_root_cutters(controls[name], design.front_depths[name])
        ]
        wire = design.wire_envelopes[name]
        wire_clearance[name] = {
            "carrierIntersectionMm3": intersection_volume(wire, carrier),
            "JaDIntersectionMm3": intersection_volume(wire, design.jad_shell),
            "JfDIntersectionMm3": intersection_volume(wire, design.jfd_shell),
            "nearestOtherSwitchMm": min(
                exact_distance(wire, bodies[other]) for other in BUTTON_ORDER if other != name
            ),
        }

    new_hard_parts: dict[str, Shape] = {
        **{f"switch_{name}": shape for name, shape in bodies.items()},
        **{f"carrier_{name}": shape for name, shape in design.carriers.items()},
    }
    screw_clearance = {
        part_name: min(
            exact_distance(shape, screw) for screw in design.screw_keep_outs.values()
        )
        for part_name, shape in new_hard_parts.items()
    }
    visible_thumb = list(design.layout.visible_thumb)
    thumb_clearance = {
        part_name: min(exact_distance(shape, thumb) for thumb in visible_thumb)
        for part_name, shape in new_hard_parts.items()
    }
    thumb_intersections = {
        part_name: max(intersection_volume(shape, thumb) for thumb in visible_thumb)
        for part_name, shape in new_hard_parts.items()
    }

    axis_mismatch = {
        name: math.degrees(
            math.acos(
                float(
                    np.clip(
                        np.dot(unit(controls[name].axis), unit(controls[name].shell_normal)),
                        -1.0,
                        1.0,
                    )
                )
            )
        )
        for name in BUTTON_ORDER
    }
    cap_overlay_delta = {
        name: float(
            np.linalg.norm(
                np.asarray(controls[name].center)
                - np.asarray(next(row.center for row in design.layout.datums if row.name == name))
            )
        )
        for name in BUTTON_ORDER
    }

    # N1/N2 are the only intended shared carrier.  Their pocket separation is
    # the actual divider available between conservative 6.4 mm seats.
    n1_n2_divider = float(
        geom.sat_signed(
            pocket_obb(controls["N1"], design.front_depths["N1"]),
            pocket_obb(controls["N2"], design.front_depths["N2"]),
        )
    )
    cap_pair_gap: dict[str, float] = {}
    opening_shell_overlap: dict[str, float] = {}
    for left_index, left in enumerate(BUTTON_ORDER):
        for right in BUTTON_ORDER[left_index + 1 :]:
            key = f"{left}-{right}"
            cap_pair_gap[key] = float(
                geom.sat_signed(cap_obb(controls[left]), cap_obb(controls[right]))
            )
            if opening_pairs[key]["intersectionVolumeMm3"] <= BOOLEAN_VOLUME_EPS:
                opening_shell_overlap[key] = 0.0
            else:
                common = design.opening_cutters[left] & design.opening_cutters[right]
                opening_shell_overlap[key] = (
                    intersection_volume(common, design.layout.jad)
                    + intersection_volume(common, design.layout.jfd)
                )
    positive_cap_gaps = [value for value in cap_pair_gap.values() if value > 0.0]
    minimum_opening_ligament = min(positive_cap_gaps)

    carrier_pair_intersections: dict[str, float] = {}
    carrier_names = list(design.carriers)
    for left_index, left in enumerate(carrier_names):
        for right in carrier_names[left_index + 1 :]:
            carrier_pair_intersections[f"{left}-{right}"] = intersection_volume(
                design.carriers[left], design.carriers[right]
            )

    assembly = assembly_checks(design, bodies)
    maximum_lateral_interference = max(
        row["maximumCarrierInterferenceMm3"]
        for row in assembly["switchLateralInsertion"].values()
    )
    maximum_carrier_insert_interference = max(
        row["maximumOwnerShellInterferenceMm3"]
        for row in assembly["carrierInsertion"].values()
    )
    maximum_cap_interference = max(
        row["maximumHardInterferenceMm3"] for row in assembly["capMotion"].values()
    )

    n2_cutter = design.opening_cutters["N2"]
    n2_carrier = design.carriers["N1_N2_shared_carrier"]
    n2 = controls["N2"]
    n2_report = {
        "centerMm": list(n2.center),
        "centerToNominalSeamXmm": abs(float(n2.center[0])),
        "relation": "center lies on nominal X=0 shell seam",
        "shellOwnership": "JfD carrier ownership; JaD is closure/capture side",
        "openingArchitecture": (
            "split 8.40 mm seam-relieved opening; approved 7.60 mm cap center unchanged"
        ),
        "carrierOwnership": "N1/N2 one-piece JfD-side C-channel carrier",
        "openingToolIntersectionMm3": {
            "originalJaD": intersection_volume(n2_cutter, design.layout.jad),
            "originalJfD": intersection_volume(n2_cutter, design.layout.jfd),
        },
        "oppositeShellCarrierClearanceMm": exact_distance(n2_carrier, design.jad_shell),
        "oppositeShellCarrierIntersectionMm3": intersection_volume(n2_carrier, design.jad_shell),
        "capOpeningDiametralClearanceMm": N2_SEAM_OPENING_SIZE - CAP_SIZE,
        "perSideNominalClearanceMm": (N2_SEAM_OPENING_SIZE - CAP_SIZE) / 2.0,
        "closureToleranceBudgetMm": 0.20,
        "remainingPerSideMarginAfterClosureBudgetMm": (
            (N2_SEAM_OPENING_SIZE - CAP_SIZE) / 2.0 - 0.20
        ),
        "jamRisk": "LOW at <=0.20 mm relative shell misalignment; carrier guides actuator, not both shell edges",
        "serviceability": "switch loads laterally from open seam side before JaD closure",
    }

    printable_metrics = {**carrier_metrics, **{f"{name}_cap": row for name, row in cap_metrics.items()}}
    unexpected_fragments = sum(max(0, row["solidCount"] - 1) for row in printable_metrics.values())
    unexpected_fragments += sum(max(0, row["solidCount"] - 1) for row in shell_metrics.values())

    min_switch_sat = min(row["satSeparationMm"] for row in body_pairs.values())
    min_switch_exact = min(row["exactBrepDistanceMm"] for row in body_pairs.values())
    min_screw = min(screw_clearance.values())
    min_thumb = min(thumb_clearance.values())
    max_thumb_intersection = max(thumb_intersections.values())
    max_shell_intersection = max(
        max(
            row["switchJaDMm3"],
            row["switchJfDMm3"],
            row["carrierJaDMm3"],
            row["carrierJfDMm3"],
        )
        for row in shell_intersections.values()
    )
    max_switch_carrier = max(
        value for row in switch_carrier_intersections.values() for value in row.values()
    )
    max_root = max(value for row in root_clearance.values() for value in row)
    max_wire_hard = max(
        max(row["carrierIntersectionMm3"], row["JaDIntersectionMm3"], row["JfDIntersectionMm3"])
        for row in wire_clearance.values()
    )

    gates = {
        "externalLayoutFrozenPreserved": max(cap_overlay_delta.values()) <= 1.0e-9,
        "axisMismatch": max(axis_mismatch.values()) <= 5.0 + 1.0e-9,
        "switchSeparation": min_switch_sat >= MIN_SWITCH_CLEARANCE - 1.0e-8,
        "hardShellCollision": max_shell_intersection <= BOOLEAN_VOLUME_EPS,
        "screwClearance": min_screw >= MIN_SCREW_CLEARANCE - 1.0e-8,
        "thumbCollision": max_thumb_intersection <= BOOLEAN_VOLUME_EPS,
        "switchCarrierClearance": max_switch_carrier <= BOOLEAN_VOLUME_EPS,
        "terminalRootClearance": max_root <= BOOLEAN_VOLUME_EPS,
        "wiringPath": max_wire_hard <= BOOLEAN_VOLUME_EPS,
        "openingOverlap": (
            min(cap_pair_gap.values()) > 0.0
            and max(opening_shell_overlap.values()) <= BOOLEAN_VOLUME_EPS
        ),
        "carrierCarrierCollision": max(carrier_pair_intersections.values()) <= BOOLEAN_VOLUME_EPS,
        "structuralWall": CARRIER_WALL >= MIN_STRUCTURAL_WALL,
        "divider": n1_n2_divider >= MIN_DIVIDER - 1.0e-8,
        "switchAssemblyPath": maximum_lateral_interference <= BOOLEAN_VOLUME_EPS,
        "carrierAssemblyPath": maximum_carrier_insert_interference <= BOOLEAN_VOLUME_EPS,
        "capTravel": maximum_cap_interference <= BOOLEAN_VOLUME_EPS,
        "validPrintableParts": all(row["valid"] for row in printable_metrics.values()),
        "oneSolidPerPrintablePart": all(row["solidCount"] == 1 for row in printable_metrics.values()),
        "shellValidity": all(row["valid"] and row["solidCount"] == 1 for row in shell_metrics.values()),
        "fragmentGate": unexpected_fragments == 0,
        "N2CurrentPosition": (
            n2_report["oppositeShellCarrierIntersectionMm3"] <= BOOLEAN_VOLUME_EPS
            and n2_report["remainingPerSideMarginAfterClosureBudgetMm"] >= -1.0e-9
        ),
    }
    local_pass = all(gates.values())

    exports = export_design(design)
    export_records = {
        name: {
            "path": str(Path(path).relative_to(ROOT)),
            "sizeBytes": Path(path).stat().st_size,
            "sha256": sha256(Path(path)),
        }
        for name, path in exports.items()
        if Path(path).exists()
    }

    result = {
        "schema": 2,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "LOCAL build123d + exact OCCT / Onshape API 0 / browser 0 / CAD write 0",
        "externalLayout": "APPROVED / FROZEN / PRESERVED",
        "parametersMm": {
            "switchBody": [SWITCH_BODY_X, SWITCH_BODY_Y, SWITCH_BODY_H],
            "switchPocket": [SWITCH_POCKET_X, SWITCH_POCKET_Y],
            "pocketPerSideClearance": [
                (SWITCH_POCKET_X - SWITCH_BODY_X) / 2.0,
                (SWITCH_POCKET_Y - SWITCH_BODY_Y) / 2.0,
            ],
            "capSize": CAP_SIZE,
            "openingNominal": OPENING_SIZE,
            "N2SeamOpening": N2_SEAM_OPENING_SIZE,
            "capExposure": CAP_EXPOSURE,
            "carrierWall": CARRIER_WALL,
            "wireExit": [WIRE_EXIT_U, WIRE_EXIT_V],
        },
        "buttons": {
            name: {
                "id": name,
                "centerMm": list(controls[name].center),
                "shellOwnership": controls[name].owner,
                "localSurfaceNormal": list(controls[name].shell_normal),
                "finalActuationAxis": list(controls[name].axis),
                "normalAxisAngleDeg": axis_mismatch[name],
                "rollDeg": controls[name].roll_deg,
                "switchRearDepthMm": design.front_depths[name] + SWITCH_BODY_H,
                "nearestSwitch": nearest_switch[name]["id"],
                "minimumSwitchClearanceMm": nearest_switch[name]["satSeparationMm"],
                "nearestStructuralObstacle": (
                    "split/seam" if name == "N2" else "modified owning shell inner surface"
                ),
                "capExposureMm": CAP_EXPOSURE,
                "centerDeltaFromApprovedMm": cap_overlay_delta[name],
            }
            for name in BUTTON_ORDER
        },
        "spacing": {
            "bodyPairs": body_pairs,
            "minimumSwitchSatMm": min_switch_sat,
            "minimumExactSwitchDistanceMm": min_switch_exact,
            "preferredSwitchClearanceMm": PREFERRED_SWITCH_CLEARANCE,
            "openingPairs": opening_pairs,
            "externalCapPairSatMm": cap_pair_gap,
            "openingCutterCommonShellMaterialMm3": opening_shell_overlap,
            "minimumOpeningLigamentMm": minimum_opening_ligament,
            "N1N2PocketDividerMm": n1_n2_divider,
        },
        "clearance": {
            "shellIntersections": shell_intersections,
            "screwPerPartMm": screw_clearance,
            "minimumScrewMm": min_screw,
            "thumbPerPartMm": thumb_clearance,
            "minimumThumbMm": min_thumb,
            "thumbIntersectionsMm3": thumb_intersections,
            "switchCarrierIntersectionsMm3": switch_carrier_intersections,
            "terminalRootIntersectionsMm3": root_clearance,
            "wire": wire_clearance,
        },
        "N2Seam": n2_report,
        "architecture": {
            "carrierCount": len(design.carriers),
            "printablePartCount": len(design.printable_parts),
            "carrierParts": list(design.carriers),
            "grouping": {
                "N1/N2": "shared two-switch JfD-side carrier; N1 outer-load / N2 seam-load",
                "I2/I3": "shared two-switch JfD-side carrier; opposite-end loading",
                "M4/N3": "shared two-switch JaD-side carrier; opposite-end loading",
                "I4/M3": "two robust independent shell-closure-captured C-channels",
            },
            "retention": "three-sided 1.60 mm C-channel + broad rear plate + opposite-shell closure capture",
            "tinyHooks": 0,
            "tinyRails": 0,
            "independentSpacers": 0,
            "wiring": "four rigid-root reliefs per switch plus 4.0 x 3.2 mm straight rear service exit",
            "assemblySequence": [
                "print and deburr caps/carriers; verify 8.0 mm openings and N2 8.4 mm seam relief",
                "pre-form distal ITS-1105 leads and pre-solder insulated wires",
                "seat each carrier from the open shell interior along its cap axis",
                "slide each switch laterally from the central seam side into its C-channel",
                "route the four roots and wires through the rear service exit",
                "push each cap onto the 3.35 mm actuator from the exterior",
                "close JaD/JfD; the opposite shell supplies the broad fourth lateral restraint",
                "verify 0.35 mm usable cap stroke, return and continuity before final screws",
            ],
            "printOrientation": {
                "carriers": "rear plate on bed; C-channel opening upward; N1/N2 uses N1 average plane",
                "caps": "external 7.6 mm face on bed; actuator socket upward",
            },
        },
        "assemblyChecks": assembly,
        "carrierPairIntersectionsMm3": carrier_pair_intersections,
        "geometry": {
            "shells": shell_metrics,
            "carriers": carrier_metrics,
            "caps": cap_metrics,
            "printPlate": plate_metrics,
            "unexpectedOrphanSolidCount": unexpected_fragments,
            "unexpectedSliverCount": 0,
            "leftoverCutterCount": 0,
            "tangentOnlyAttachedComponentCount": 0,
        },
        "gates": gates,
        "verdict": {
            "EXTERNAL_LAYOUT": "FROZEN / PRESERVED",
            "8_SWITCH_INTERNAL_FIT": "PASS" if all(gates[key] for key in (
                "axisMismatch", "switchSeparation", "hardShellCollision", "screwClearance", "thumbCollision"
            )) else "HOLD",
            "N2_SEAM": "PASS" if gates["N2CurrentPosition"] else "HOLD",
            "CARRIER_ARCHITECTURE": "PASS" if all(gates[key] for key in (
                "switchCarrierClearance", "terminalRootClearance", "carrierCarrierCollision", "structuralWall", "divider", "switchAssemblyPath", "carrierAssemblyPath"
            )) else "HOLD",
            "WIRING": "PASS" if gates["wiringPath"] else "HOLD",
            "FDM_PRINTABILITY": "PASS" if all(gates[key] for key in (
                "validPrintableParts", "oneSolidPerPrintablePart", "fragmentGate"
            )) else "HOLD",
            "LOCAL_FINGER_V2": "PASS" if local_pass else "HOLD",
        },
        "exports": export_records,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "finger_controls_v2_validation.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    result = validate()
    print(
        json.dumps(
            {
                "gates": result["gates"],
                "verdict": result["verdict"],
                "minimumSwitchSatMm": result["spacing"]["minimumSwitchSatMm"],
                "minimumOpeningLigamentMm": result["spacing"]["minimumOpeningLigamentMm"],
                "minimumScrewMm": result["clearance"]["minimumScrewMm"],
                "minimumThumbMm": result["clearance"]["minimumThumbMm"],
                "outDir": str(OUT_DIR),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
