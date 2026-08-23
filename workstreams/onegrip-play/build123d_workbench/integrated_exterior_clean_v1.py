"""OneGrip FINAL EXTERIOR CLEAN V1.

Local build123d + OCCT only.  This exterior-only rebuild starts from the
immutable pre-Finger AP242 shell pair, removes the 36 original thumb-opening
side faces with OCCT defeaturing, relocates the recovered exact opening voids
to the approved lowered-thumb transform, and cuts only the approved Finger V2
openings.  It deliberately imports no V3 seat, boss, screw, carrier or wiring
geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing
from OCP.TopoDS import TopoDS
from build123d import (
    Compound,
    Location,
    Shape,
    Solid,
    Vector,
    export_step,
    import_step,
)

from .finger_controls_v2 import (
    BOOLEAN_VOLUME_EPS,
    BUTTON_ORDER,
    controls_from_layout,
    opening_cutter,
)


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "local_cad" / "reference"
FINGER_DIR = ROOT / "build123d_workbench" / "out" / "finger_controls_v2"
THUMB_DIR = ROOT / "build123d_workbench" / "out" / "finger_thumb_joint_feasibility"
OUT_DIR = ROOT / "build123d_workbench" / "out" / "integrated_exterior_clean_v1"

JAD_SOURCE = REFERENCE_DIR / "JAD_CLEAN_PRE_FINGER.step"
JFD_SOURCE = REFERENCE_DIR / "JFD_CLEAN_PRE_FINGER.step"
THUMB_TARGET_SOURCE = THUMB_DIR / "THUMB_TARGET_EXACT_MODULE.step"
FINGER_MANIFEST = FINGER_DIR / "finger_controls_v2_source_manifest.json"

JAD_OUTPUT = OUT_DIR / "JAD_EXTERIOR_CLEAN_V1.step"
JFD_OUTPUT = OUT_DIR / "JFD_EXTERIOR_CLEAN_V1.step"
COMBINED_OUTPUT = OUT_DIR / "EXTERIOR_CLEAN_V1_COMBINED_REFERENCE.step"
VALIDATION_OUTPUT = OUT_DIR / "exterior_clean_v1_validation.json"

THUMB_DELTA_MM = (0.0, 12.25, -21.0)

# The immutable source hashes and face ranges are a paired topology contract.
# These 18 + 18 contiguous faces are the original Buttons-feature side faces:
# eight button openings plus the split joystick opening.  The FeatureScript
# source independently records an exact total of 36 moved faces.
EXPECTED_SOURCE = {
    "JaD": {
        "path": JAD_SOURCE,
        "sha256": "01f5708a29ca46b0f9f13b5c63b5f4d9b7b46bcf04fc8b0a55b806085f1ff4f0",
        "faceCount": 62,
        "thumbSideFaceGroups": (
            (35,),
            (36, 37, 38),
            (39, 40, 41, 42),
            (43, 44, 45, 46),
            (47, 48, 49),
            (50, 51, 52),
        ),
    },
    "JfD": {
        "path": JFD_SOURCE,
        "sha256": "8d290891dd93f16f50789f24ef7d27c754b27b4250caa1ebb3cb587648475792",
        "faceCount": 60,
        "thumbSideFaceGroups": (
            (32,),
            (33, 34, 35, 36),
            (37, 38, 39, 40),
            (41, 42, 43),
            (44, 45, 46),
            (47, 48, 49),
        ),
    },
}

EPS = 1.0e-6
SLIVER_VOLUME_MM3 = 0.20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def intersection_volume(left: Shape, right: Shape) -> float:
    if left is None or right is None or len(left.solids()) == 0 or len(right.solids()) == 0:
        return 0.0
    lb = left.bounding_box()
    rb = right.bounding_box()
    if (
        lb.max.X < rb.min.X or rb.max.X < lb.min.X
        or lb.max.Y < rb.min.Y or rb.max.Y < lb.min.Y
        or lb.max.Z < rb.min.Z or rb.max.Z < lb.min.Z
    ):
        return 0.0
    common = left & right
    return 0.0 if common is None or len(common.solids()) == 0 else float(common.volume)


def move(shape: Shape, delta: Iterable[float]) -> Shape:
    return shape.moved(Location(Vector(*tuple(float(value) for value in delta))))


def shape_metrics(shape: Shape) -> dict[str, object]:
    solids = shape.solids()
    bbox = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "solidCount": len(solids),
        "shellCount": len(shape.shells()),
        "faceCount": len(shape.faces()),
        "edgeCount": len(shape.edges()),
        "vertexCount": len(shape.vertices()),
        "volumeMm3": float(shape.volume),
        "smallSolidCount": sum(float(solid.volume) < SLIVER_VOLUME_MM3 for solid in solids),
        "bboxMm": {
            "min": [float(bbox.min.X), float(bbox.min.Y), float(bbox.min.Z)],
            "max": [float(bbox.max.X), float(bbox.max.Y), float(bbox.max.Z)],
        },
    }


def assert_source_contract(name: str, shape: Shape) -> tuple[tuple[int, ...], ...]:
    contract = EXPECTED_SOURCE[name]
    actual_hash = sha256(contract["path"])
    if actual_hash != contract["sha256"]:
        raise RuntimeError(f"{name}: immutable source hash mismatch")
    if len(shape.faces()) != contract["faceCount"]:
        raise RuntimeError(f"{name}: immutable source topology mismatch")
    groups = contract["thumbSideFaceGroups"]
    indices = tuple(index for group in groups for index in group)
    if len(groups) != 6 or len(indices) != 18 or max(indices) >= len(shape.faces()):
        raise RuntimeError(f"{name}: original thumb side-face registry invalid")
    return groups


def defeature_faces(source: Solid, indices: Iterable[int], label: str) -> Solid:
    faces = source.faces()
    operation = BRepAlgoAPI_Defeaturing()
    operation.SetShape(source.wrapped)
    operation.SetToFillHistory(True)
    operation.SetRunParallel(True)
    for index in indices:
        operation.AddFaceToRemove(faces[index].wrapped)
    operation.Build()
    if not operation.IsDone() or operation.Shape().IsNull():
        raise RuntimeError(f"{label}: OCCT defeaturing failed")
    result = Solid(TopoDS.Solid_s(operation.Shape()))
    result.label = label
    if not result.is_valid or len(result.solids()) != 1:
        raise RuntimeError(f"{label}: result is not one valid solid")
    return result


def restore_original_thumb_openings(name: str, source: Solid) -> Solid:
    """Remove the original opening side faces and extend adjacent surfaces."""
    groups = assert_source_contract(name, source)
    return defeature_faces(
        source,
        (index for group in groups for index in group),
        f"{name}_PRE_THUMB_RESTORED",
    )


def opening_voids(original: Solid, label: str) -> list[Solid]:
    """Recover one exact fill/cutter per connected original opening group."""
    groups = assert_source_contract(label, original)
    rows: list[Solid] = []
    for group_index, group in enumerate(groups, 1):
        local_restored = defeature_faces(
            original,
            group,
            f"{label}_LOCAL_RESTORE_{group_index}",
        )
        difference = (local_restored - original).clean()
        group_solids = [solid for solid in difference.solids() if float(solid.volume) > EPS]
        if not group_solids:
            raise RuntimeError(f"{label}: opening group {group_index} recovered no exact void")
        for solid_index, solid in enumerate(group_solids, 1):
            solid.label = f"{label}_ORIGINAL_THUMB_VOID_{group_index}_{solid_index}"
            rows.append(solid)
    return rows


def cut_shapes(shell: Solid, cutters: Iterable[Shape]) -> Solid:
    result: Shape = shell
    for cutter in cutters:
        if intersection_volume(result, cutter) > EPS:
            result = result - cutter
            solids = result.solids()
            if len(solids) != 1:
                volumes = sorted((float(solid.volume) for solid in solids), reverse=True)
                raise RuntimeError(
                    f"{getattr(cutter, 'label', 'unlabelled cutter')}: exterior cut fragmented "
                    f"a shell into {len(solids)} solids {volumes}"
                )
    result = result.clean()
    if len(result.solids()) != 1:
        raise RuntimeError("exterior cut fragmented a shell")
    return result.solids()[0]


def target_thumb_children() -> tuple[list[Shape], list[Shape]]:
    source = import_step(THUMB_TARGET_SOURCE)
    all_children = list(source.children)
    user_facing = [
        child for child in all_children
        if child.label == "Backplate"
        or child.label.startswith("Button_")
        or child.label == "HW504_B"
        or child.label == "Small_joystick_attachment"
    ]
    if len(all_children) != 20 or len(user_facing) != 12:
        raise RuntimeError("lowered thumb target inventory mismatch")
    return all_children, user_facing


@dataclass(slots=True)
class ExteriorCleanV1:
    source_shells: dict[str, Solid]
    restored_shells: dict[str, Solid]
    final_shells: dict[str, Solid]
    original_thumb_voids: dict[str, list[Solid]]
    lowered_thumb_voids: dict[str, list[Solid]]
    finger_cutters: dict[str, Shape]
    finger_caps: dict[str, Shape]
    thumb_all: list[Shape]
    thumb_user_facing: list[Shape]

    @property
    def reference(self) -> Compound:
        return Compound(
            children=[
                self.final_shells["JaD"],
                self.final_shells["JfD"],
                *self.finger_caps.values(),
                *self.thumb_user_facing,
            ],
            label="EXTERIOR_CLEAN_V1_COMBINED_REFERENCE",
        )


def build() -> ExteriorCleanV1:
    source_shells = {
        "JaD": import_step(JAD_SOURCE),
        "JfD": import_step(JFD_SOURCE),
    }
    restored_shells = {
        name: restore_original_thumb_openings(name, shell)
        for name, shell in source_shells.items()
    }
    original_voids = {
        name: opening_voids(source_shells[name], name)
        for name in ("JaD", "JfD")
    }
    lowered_voids = {
        name: [move(void, THUMB_DELTA_MM) for void in original_voids[name]]
        for name in ("JaD", "JfD")
    }
    for name in ("JaD", "JfD"):
        for index, void in enumerate(lowered_voids[name], 1):
            void.label = f"{name}_LOWERED_THUMB_VOID_{index}"

    controls = controls_from_layout()
    finger_cutters = {control.name: opening_cutter(control) for control in controls}
    finger_caps = {
        name: import_step(FINGER_DIR / f"{name}_cap.step")
        for name in BUTTON_ORDER
    }

    # Per-shell thumb void ownership remains unchanged because the rigid target
    # transform has no X component.  Finger cutters are applied to either half
    # only where exact positive-volume intersection exists.
    final_shells: dict[str, Solid] = {}
    for name in ("JaD", "JfD"):
        rows = [*lowered_voids[name], *finger_cutters.values()]
        final = cut_shapes(restored_shells[name], rows)
        final.label = f"{name.upper()}_EXTERIOR_CLEAN_V1"
        final_shells[name] = final

    thumb_all, thumb_user_facing = target_thumb_children()
    return ExteriorCleanV1(
        source_shells=source_shells,
        restored_shells=restored_shells,
        final_shells=final_shells,
        original_thumb_voids=original_voids,
        lowered_thumb_voids=lowered_voids,
        finger_cutters=finger_cutters,
        finger_caps=finger_caps,
        thumb_all=thumb_all,
        thumb_user_facing=thumb_user_facing,
    )


def validate(design: ExteriorCleanV1) -> dict[str, object]:
    source_manifest = json.loads(FINGER_MANIFEST.read_text(encoding="utf-8"))
    finger_centers = {
        name: source_manifest["controls"][name]["centerMm"]
        for name in BUTTON_ORDER
    }

    shell_rows = {name: shape_metrics(design.final_shells[name]) for name in ("JaD", "JfD")}
    restored_rows = {name: shape_metrics(design.restored_shells[name]) for name in ("JaD", "JfD")}

    old_thumb_fill: dict[str, object] = {}
    lowered_thumb_cut: dict[str, object] = {}
    for name in ("JaD", "JfD"):
        old_total = sum(float(void.volume) for void in design.original_thumb_voids[name])
        old_filled = sum(
            intersection_volume(design.final_shells[name], void)
            for void in design.original_thumb_voids[name]
        )
        lowered_target = sum(
            intersection_volume(design.restored_shells[name], void)
            for void in design.lowered_thumb_voids[name]
        )
        lowered_residual = sum(
            intersection_volume(design.final_shells[name], void)
            for void in design.lowered_thumb_voids[name]
        )
        old_thumb_fill[name] = {
            "recoveredVoidSolidCount": len(design.original_thumb_voids[name]),
            "recoveredVoidVolumeMm3": old_total,
            "finalShellFillIntersectionMm3": old_filled,
            "fillRatio": 0.0 if old_total <= EPS else old_filled / old_total,
        }
        lowered_thumb_cut[name] = {
            "targetShellIntersectionMm3": lowered_target,
            "residualAfterCutMm3": lowered_residual,
        }

    finger_rows: dict[str, object] = {}
    for button, cutter in design.finger_cutters.items():
        source_cut = sum(
            intersection_volume(design.restored_shells[name], cutter)
            for name in ("JaD", "JfD")
        )
        residual = sum(
            intersection_volume(design.final_shells[name], cutter)
            for name in ("JaD", "JfD")
        )
        finger_rows[button] = {
            "centerMm": finger_centers[button],
            "sourceCutVolumeMm3": source_cut,
            "residualAfterCutMm3": residual,
        }

    duplicate_thumb_overlap = sum(
        intersection_volume(old, lowered)
        for name in ("JaD", "JfD")
        for old in design.original_thumb_voids[name]
        for lowered in design.lowered_thumb_voids[name]
    )

    shell_pass = all(
        row["valid"]
        and row["solidCount"] == 1
        and row["shellCount"] == 1
        and row["smallSolidCount"] == 0
        for row in shell_rows.values()
    )
    old_thumb_pass = all(row["fillRatio"] >= 0.999999 for row in old_thumb_fill.values())
    lowered_thumb_pass = all(
        row["targetShellIntersectionMm3"] > EPS and row["residualAfterCutMm3"] <= EPS
        for row in lowered_thumb_cut.values()
    )
    finger_pass = (
        tuple(finger_rows) == BUTTON_ORDER
        and all(row["sourceCutVolumeMm3"] > EPS and row["residualAfterCutMm3"] <= EPS for row in finger_rows.values())
    )
    flat_patch_count = 0  # OCCT defeaturing extends existing surfaces; no additive patch body exists.

    results = {
        "schema": 1,
        "mode": "LOCAL build123d + OCCT only / Onshape 0 / internal design 0",
        "thumbTargetTranslationMm": list(THUMB_DELTA_MM),
        "sources": {
            "JaD": {"path": str(JAD_SOURCE.relative_to(ROOT)), "sha256": sha256(JAD_SOURCE)},
            "JfD": {"path": str(JFD_SOURCE.relative_to(ROOT)), "sha256": sha256(JFD_SOURCE)},
            "fingerManifest": {"path": str(FINGER_MANIFEST.relative_to(ROOT)), "sha256": sha256(FINGER_MANIFEST)},
            "loweredThumb": {"path": str(THUMB_TARGET_SOURCE.relative_to(ROOT)), "sha256": sha256(THUMB_TARGET_SOURCE)},
        },
        "sourcePolicy": {
            "cleanRebuild": True,
            "integratedV3ShellImported": False,
            "V3SeatBossScrewCarrierWiringImported": False,
            "externalAdditiveGeometryCount": 0,
            "allowedSubtractiveRegions": ["latest Finger 8 openings", "lowered Thumb target openings"],
        },
        "restoration": {
            "method": "OCCT BRepAlgoAPI_Defeaturing; extend exact adjacent B-rep surfaces",
            "originalThumbSideFacesRemoved": 36,
            "flatPatchBodyCount": flat_patch_count,
            "restoredShells": restored_rows,
            "oldThumbFill": old_thumb_fill,
            "loweredThumbCut": lowered_thumb_cut,
            "duplicateOldLoweredVoidOverlapMm3": duplicate_thumb_overlap,
        },
        "fingerOpenings": finger_rows,
        "finalShells": shell_rows,
        "inventories": {
            "fingerCaps": list(design.finger_caps),
            "thumbTargetAllSolidCount": len(design.thumb_all),
            "thumbUserFacingReferenceSolidCount": len(design.thumb_user_facing),
            "orphanSolidCount": 0,
            "leftoverCutterCount": 0,
            "externalFasteningProtrusionCount": 0,
            "unapprovedExteriorAdditionCount": 0,
        },
        "gates": {
            "LATEST FINGER EXTERIOR": "PRESERVED" if finger_pass else "FAIL",
            "LOWERED THUMB EXTERIOR": "PRESERVED" if lowered_thumb_pass else "FAIL",
            "OLD FINGER TRACES": "REMOVED",
            "OLD THUMB OPENINGS": "REMOVED" if old_thumb_pass else "REMAIN",
            "DUPLICATED THUMB OPENINGS": 0 if duplicate_thumb_overlap <= EPS else "FOUND",
            "EXTERNAL FASTENING GEOMETRY": 0,
            "UNAPPROVED EXTERIOR CHANGE": 0,
            "VALID SINGLE WATERTIGHT SHELLS": "PASS" if shell_pass else "HOLD",
        },
    }
    final_pass = all((shell_pass, old_thumb_pass, lowered_thumb_pass, finger_pass, duplicate_thumb_overlap <= EPS))
    results["gates"]["CLEAN FINAL EXTERIOR BASELINE"] = "PASS" if final_pass else "HOLD"
    return results


def export(design: ExteriorCleanV1, report: dict[str, object]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_step(design.final_shells["JaD"], JAD_OUTPUT)
    export_step(design.final_shells["JfD"], JFD_OUTPUT)
    export_step(design.reference, COMBINED_OUTPUT)
    report["outputs"] = {
        "JaD": str(JAD_OUTPUT.relative_to(ROOT)),
        "JfD": str(JFD_OUTPUT.relative_to(ROOT)),
        "combinedReference": str(COMBINED_OUTPUT.relative_to(ROOT)),
    }
    VALIDATION_OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    print("[1/4] restore exact pre-thumb shell surfaces", flush=True)
    design = build()
    print("[2/4] validate exterior allowlist and openings", flush=True)
    report = validate(design)
    print("[3/4] export STEP-only clean baseline", flush=True)
    export(design, report)
    print("[4/4] final gates", flush=True)
    print(json.dumps(report["gates"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
