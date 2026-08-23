"""Exterior-first OneGrip mockup with the maximum-lowered Thumb cluster.

This branch starts from FINAL EXTERIOR CLEAN V1, keeps the frozen Finger V2
openings/caps, and applies only the user-facing opening envelopes for the
original Thumb controls at the approved (0,+12.25,-21.00) mm transform.

No Backplate, PushBtn, HW504 mechanism, carrier, seat, wire, boss, screw or
fastening geometry is exported.  Internal collisions and assembly feasibility
are deliberately deferred until the user approves the exterior.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from build123d import Compound, Shape, Solid, export_step, import_step

from .finger_controls_v2 import BOOLEAN_VOLUME_EPS, BUTTON_ORDER
from .finger_thumb_integrated_v3 import (
    THUMB_OPENING_CLEARANCE,
    thumb_user_side_service_box,
)
from .integrated_exterior_clean_v1 import (
    THUMB_DELTA_MM,
    THUMB_TARGET_SOURCE,
    build as build_clean,
    cut_shapes,
    intersection_volume,
    shape_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
FINGER_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "integrated_exterior_lowered_thumb_v1"

JAD_OUTPUT = OUT_DIR / "JAD_EXTERIOR_LOWERED_THUMB_V1.step"
JFD_OUTPUT = OUT_DIR / "JFD_EXTERIOR_LOWERED_THUMB_V1.step"
COMBINED_OUTPUT = OUT_DIR / "EXTERIOR_LOWERED_THUMB_V1_COMBINED_REFERENCE.step"
VALIDATION_OUTPUT = OUT_DIR / "exterior_lowered_thumb_v1_validation.json"

LOWER15_JAD_MESH = (
    ROOT / "exports" / "thumb_lower15_housing_mockup"
    / "OneGrip_lower15_housing_Joystick_1_JaD.stl"
)
LOWER15_JFD_MESH = (
    ROOT / "exports" / "thumb_lower15_housing_mockup"
    / "OneGrip_lower15_housing_Joystick_2_JfD.stl"
)

EXTERNAL_THUMB_LABELS = (
    "Button_wide_1",
    "Button_side_1",
    "Button_corner_1",
    "Button_corner_2",
    "Button_side_2",
    "Button_wide_2",
    "Button_middle_1",
    "Button_middle_2",
    "Small_joystick_attachment",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_external_thumb() -> dict[str, Shape]:
    source = import_step(THUMB_TARGET_SOURCE)
    rows = {
        child.label: child
        for child in source.children
        if child.label in EXTERNAL_THUMB_LABELS
    }
    if tuple(name for name in EXTERNAL_THUMB_LABELS if name in rows) != EXTERNAL_THUMB_LABELS:
        missing = [name for name in EXTERNAL_THUMB_LABELS if name not in rows]
        raise RuntimeError(f"maximum-lowered exterior Thumb inventory mismatch: {missing}")
    if len(rows) != 9:
        raise RuntimeError("maximum-lowered exterior Thumb must contain exactly 9 controls")
    return rows


def build_opening_tools(external_thumb: dict[str, Shape]) -> dict[str, Shape]:
    rows: dict[str, Shape] = {}
    for name in EXTERNAL_THUMB_LABELS:
        tool = thumb_user_side_service_box(
            external_thumb[name],
            THUMB_OPENING_CLEARANCE,
            f"{name}_EXTERIOR_ONLY_OPENING_TOOL",
        )
        rows[name] = tool
    return rows


@dataclass(slots=True)
class ExteriorLoweredThumbV1:
    clean: object
    shells: dict[str, Solid]
    finger_caps: dict[str, Shape]
    thumb_controls: dict[str, Shape]
    thumb_opening_tools: dict[str, Shape]

    @property
    def reference(self) -> Compound:
        return Compound(
            children=[
                self.shells["JaD"],
                self.shells["JfD"],
                *self.finger_caps.values(),
                *self.thumb_controls.values(),
            ],
            label="EXTERIOR_LOWERED_THUMB_V1_COMBINED_REFERENCE",
        )


def build() -> ExteriorLoweredThumbV1:
    clean = build_clean()
    thumb_controls = load_external_thumb()
    opening_tools = build_opening_tools(thumb_controls)

    shells: dict[str, Solid] = {}
    for side in ("JaD", "JfD"):
        shell = cut_shapes(clean.final_shells[side], opening_tools.values())
        shell.label = f"{side.upper()}_EXTERIOR_LOWERED_THUMB_V1"
        shells[side] = shell

    finger_caps = {
        name: import_step(FINGER_DIR / f"{name}_cap.step")
        for name in BUTTON_ORDER
    }
    return ExteriorLoweredThumbV1(
        clean=clean,
        shells=shells,
        finger_caps=finger_caps,
        thumb_controls=thumb_controls,
        thumb_opening_tools=opening_tools,
    )


def validate(design: ExteriorLoweredThumbV1) -> dict[str, object]:
    shell_metrics = {side: shape_metrics(design.shells[side]) for side in ("JaD", "JfD")}

    thumb_openings: dict[str, object] = {}
    for name, tool in design.thumb_opening_tools.items():
        source_by_side = {
            side: intersection_volume(design.clean.final_shells[side], tool)
            for side in ("JaD", "JfD")
        }
        residual_by_side = {
            side: intersection_volume(design.shells[side], tool)
            for side in ("JaD", "JfD")
        }
        thumb_openings[name] = {
            "sourceShellIntersectionMm3": source_by_side,
            "totalSourceShellIntersectionMm3": sum(source_by_side.values()),
            "residualAfterCutMm3": residual_by_side,
            "totalResidualAfterCutMm3": sum(residual_by_side.values()),
            "clearanceMm": THUMB_OPENING_CLEARANCE,
        }

    finger_openings: dict[str, object] = {}
    for name, tool in design.clean.finger_cutters.items():
        residual = sum(
            intersection_volume(design.shells[side], tool)
            for side in ("JaD", "JfD")
        )
        finger_openings[name] = {"residualAfterThumbExteriorCutMm3": residual}

    old_thumb_fill: dict[str, object] = {}
    for side in ("JaD", "JfD"):
        original_total = sum(
            float(void.volume) for void in design.clean.original_thumb_voids[side]
        )
        protected_total = 0.0
        protected_filled = 0.0
        for void in design.clean.original_thumb_voids[side]:
            protected: Shape = void
            for tool in design.thumb_opening_tools.values():
                if intersection_volume(protected, tool) > BOOLEAN_VOLUME_EPS:
                    protected = (protected - tool).clean()
            if len(protected.solids()) == 0:
                continue
            protected_total += float(protected.volume)
            protected_filled += intersection_volume(design.shells[side], protected)
        old_thumb_fill[side] = {
            "recoveredOriginalVoidVolumeMm3": original_total,
            "overlapAuthorizedByNewLoweredOpeningsMm3": original_total - protected_total,
            "oldPositionOutsideNewOpeningMm3": protected_total,
            "finalShellFillOutsideNewOpeningMm3": protected_filled,
            "fillRatioOutsideNewOpening": (
                0.0
                if protected_total <= BOOLEAN_VOLUME_EPS
                else protected_filled / protected_total
            ),
        }

    shells_pass = all(
        row["valid"]
        and row["solidCount"] == 1
        and row["shellCount"] == 1
        and row["smallSolidCount"] == 0
        for row in shell_metrics.values()
    )
    thumb_pass = (
        len(thumb_openings) == 9
        and all(
            row["totalSourceShellIntersectionMm3"] > BOOLEAN_VOLUME_EPS
            and row["totalResidualAfterCutMm3"] <= BOOLEAN_VOLUME_EPS
            for row in thumb_openings.values()
        )
    )
    finger_pass = (
        tuple(finger_openings) == BUTTON_ORDER
        and all(
            row["residualAfterThumbExteriorCutMm3"] <= BOOLEAN_VOLUME_EPS
            for row in finger_openings.values()
        )
    )
    old_thumb_pass = all(
        row["fillRatioOutsideNewOpening"] >= 0.999999
        for row in old_thumb_fill.values()
    )

    report: dict[str, object] = {
        "schema": 1,
        "mode": "EXTERIOR FIRST / LOCAL build123d + OCCT / Onshape 0",
        "scope": "clean shell + latest Finger 8 + maximum-lowered Thumb exterior only",
        "thumbTargetTranslationMm": list(THUMB_DELTA_MM),
        "sources": {
            "cleanExteriorBuilder": "build123d_workbench/integrated_exterior_clean_v1.py",
            "targetThumbExactModule": {
                "path": str(THUMB_TARGET_SOURCE.relative_to(ROOT)),
                "sha256": sha256(THUMB_TARGET_SOURCE),
            },
            "lower15HousingVisualReference": {
                "JaD": {"path": str(LOWER15_JAD_MESH.relative_to(ROOT)), "sha256": sha256(LOWER15_JAD_MESH)},
                "JfD": {"path": str(LOWER15_JFD_MESH.relative_to(ROOT)), "sha256": sha256(LOWER15_JFD_MESH)},
                "booleanSource": False,
                "reason": "historical exterior position/silhouette reference only; STL is not exact B-rep",
            },
        },
        "constructionPolicy": {
            "shellStartingPoint": "FINAL EXTERIOR CLEAN V1 exact shell pair",
            "thumbOpeningMethod": "9 localized user-side opening envelopes, 0.80 mm clearance",
            "originalThumbControlRelativeGeometryChanged": False,
            "shellAdditiveGeometryCount": 0,
            "throughReliefCount": 0,
            "backplateExported": False,
            "pushButtonBodiesExported": False,
            "HW504MechanismExported": False,
            "internalCarrierSeatWireFasteningExported": False,
            "externalThumbControlCount": len(design.thumb_controls),
            "fingerCapCount": len(design.finger_caps),
        },
        "shells": shell_metrics,
        "thumbOpenings": thumb_openings,
        "fingerOpenings": finger_openings,
        "originalThumbOpeningFill": old_thumb_fill,
        "deferredInternalReview": [
            "Thumb Backplate seating",
            "HW504 mechanism clearance",
            "PushBtn actuation and travel",
            "Finger/Thumb internal interference",
            "carrier and assembly path",
            "wiring path",
            "internal fastening",
        ],
        "gates": {
            "LATEST FINGER 8 EXTERIOR": "PRESERVED" if finger_pass else "FAIL",
            "MAXIMUM-LOWERED THUMB EXTERIOR": "APPLIED" if thumb_pass else "FAIL",
            "OLD THUMB OPENINGS": "REMOVED" if old_thumb_pass else "REMAIN",
            "THUMB MECHANISM THROUGH CUTTER": 0,
            "EXTERNAL FASTENING GEOMETRY": 0,
            "VALID SINGLE WATERTIGHT SHELLS": "PASS" if shells_pass else "HOLD",
            "INTERNAL DESIGN": "DEFERRED / NOT A BLOCKER FOR THIS EXTERIOR REVIEW",
        },
    }
    exterior_ready = shells_pass and thumb_pass and finger_pass and old_thumb_pass
    report["gates"]["EXTERIOR REVIEW MOCKUP"] = "READY" if exterior_ready else "HOLD"
    report["gates"]["PRODUCTION / PRINT APPROVAL"] = "NOT EVALUATED"
    return report


def export(design: ExteriorLoweredThumbV1, report: dict[str, object]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_step(design.shells["JaD"], JAD_OUTPUT)
    export_step(design.shells["JfD"], JFD_OUTPUT)
    export_step(design.reference, COMBINED_OUTPUT)
    report["outputs"] = {
        "JaD": str(JAD_OUTPUT.relative_to(ROOT)),
        "JfD": str(JFD_OUTPUT.relative_to(ROOT)),
        "combinedReference": str(COMBINED_OUTPUT.relative_to(ROOT)),
    }
    VALIDATION_OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    print("[1/4] build FINAL EXTERIOR CLEAN V1 source", flush=True)
    design = build()
    print("[2/4] validate exterior-only lowered Thumb openings", flush=True)
    report = validate(design)
    print("[3/4] export STEP-only exterior review set", flush=True)
    export(design, report)
    print("[4/4] exterior gates", flush=True)
    print(json.dumps(report["gates"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
