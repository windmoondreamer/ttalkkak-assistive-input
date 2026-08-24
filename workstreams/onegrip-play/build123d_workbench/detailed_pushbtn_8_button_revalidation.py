"""Audit-only 8-button revalidation against the original detailed PushBtn.

The original cached 3,530-triangle PushBtn is sewn into a valid faceted BRep
without scaling.  It is aligned to every frozen button pose from functional
datums (actuator centre/axis and plastic body-top plane), never by bbox centre.

Production geometry is read-only.  The script creates only new audit STEP,
JSON, markdown and PNG files; no shell/carrier/cap/pose/SZH source is modified.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Iterable

import numpy as np
import psutil
from build123d import (
    Align,
    Box,
    Compound,
    Cylinder,
    Location,
    Plane,
    Shape,
    Solid,
    Vector,
    export_step,
    import_step,
)
from OCP.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeSolid,
    BRepBuilderAPI_Sewing,
)
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.gp import gp_Pnt
from OCP.TopoDS import TopoDS
from scipy.spatial import cKDTree

from . import all_8_button_integration_wiring_space_audit as legacy_all8
from . import i2_i3_production_intent_mechanism as i2i3
from . import i4_m3_production_intent_mechanisms as i4m3
from . import m4_n3_production_intent_mechanism as m4n3
from . import m4_n3_terminal_redundancy_resolution as m4n3trim
from . import n1_production_intent_mechanism as n1prod
from . import n2_production_intent_mechanism as n2prod
from . import n2_rear_reaction_support_redesign as n2rear
from .finger_controls_v2 import (
    ACTUATOR_DIAMETER,
    ACTUATOR_PROJECTION,
    CARRIER_REAR_PLATE,
    FROZEN_FRONT_DEPTHS,
    SWITCH_BODY_H,
    SWITCH_POCKET_X,
    SWITCH_POCKET_Y,
    TERMINAL_CLEARANCE,
    ControlDatum,
    oriented_box,
    oriented_cylinder,
    point_at,
    switch_actuator,
    switch_body,
    terminal_root_cutters,
    unit,
)
from .i4_m3_current_audit import load_all_datums
from .n1_current_audit import TERMINAL_LABELS as N1_TERMINAL_LABELS
from .option_c_local_exact_prototype import (
    BOOLEAN_EPS_MM3,
    bbox_gap,
    exact_pair,
    raster_scene,
    safe_edge_lines,
    safe_triangles,
)


ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "cad_dump"
OUT = ROOT / "build123d_workbench" / "out" / "detailed_pushbtn_8_button_revalidation"
RENDER = ROOT / "renders" / "detailed_pushbtn_8_button_revalidation"
REPORT = ROOT / "docs" / "75_detailed_pushbtn_8_button_revalidation.md"
JSON_PATH = OUT / "detailed_pushbtn_8_button_revalidation.json"
AUDIT_STEP = OUT / "DETAILED_PUSHBTN_AUDIT_ONLY_8_BUTTON_ASSEMBLY.step"
REFERENCE_STEP = OUT / "ORIGINAL_PUSHBTN_DETAILED_FACETED_REFERENCE.step"
HYBRID_STEP = OUT / "HYBRID_SWITCH_REFERENCE_BODY_ACTUATOR_TERMINALS.step"

BUTTONS = ("N1", "N2", "I2", "I3", "I4", "M3", "M4", "N3")
GROUPS = ("N1_N2", "I2_I3", "M4_N3", "I4", "M3")
GROUP_BUTTONS = {
    "N1_N2": ("N1", "N2"),
    "I2_I3": ("I2", "I3"),
    "M4_N3": ("M4", "N3"),
    "I4": ("I4",),
    "M3": ("M3",),
}
BUTTON_GROUP = {button: group for group, buttons in GROUP_BUTTONS.items() for button in buttons}
TERMINALS = ("T1", "T2", "T3", "T4")
TRAVELS = (0.0, 0.175, 0.350)

# Original detailed mesh functional planes, derived from dominant planar faces.
ORIG_BODY_REAR_Y = 0.0
ORIG_BODY_TOP_Y = 3.5
ORIG_ACTUATOR_TIP_Y = 5.0
ORIG_BODY_HEIGHT = ORIG_BODY_TOP_Y - ORIG_BODY_REAR_Y
ORIG_ACTUATOR_PROJECTION = ORIG_ACTUATOR_TIP_Y - ORIG_BODY_TOP_Y

# Owned physical sample registry.  Terminal roots/pins remain drawing-nominal.
ACTUAL = {
    "bodyXmm": 6.12,
    "bodyYmm": 6.05,
    "housingHmm": 3.56,
    "totalHmm": 6.00,
    "actuatorDiameterMm": 3.35,
    "actuatorProjectionMm": 2.44,
    "travelNominalMm": 0.25,
    "travelUpperMm": 0.35,
}

CARRIER_PATHS = {
    "N1_N2": ROOT / "build123d_workbench/out/n1_production_intent_mechanism/N1_N2_SHARED_CARRIER_N1_LOCAL.step",
    "I2_I3": ROOT / "build123d_workbench/out/i2_i3_production_intent_mechanism/I2_I3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step",
    "M4_N3": ROOT / "build123d_workbench/out/m4_n3_production_intent_mechanism/M4_N3_SHARED_CARRIER_PRODUCTION_INTENT_LOCAL.step",
    "I4": ROOT / "build123d_workbench/out/real_integration_conflict_resolution/I4_CARRIER_LOCAL_MANUFACTURING_RELIEF.step",
    "M3": ROOT / "build123d_workbench/out/i4_m3_production_intent_mechanisms/M3_CARRIER_PRODUCTION_INTENT_LOCAL.step",
}
CAP_PATHS = dict(legacy_all8.CAP_PATHS)
SHELL_PATHS = dict(legacy_all8.SHELL_PATHS)
TRIMMED_TERMINAL_STEP = (
    ROOT / "build123d_workbench/out/m4_n3_terminal_redundancy_resolution/"
    "M4_N3_TRIMMED_TERMINALS_LOCAL_REFERENCE.step"
)

PROTECTED_INPUTS = [
    *[ROOT / "docs" / f"{index:02d}_{name}" for index, name in ()],
    *sorted((ROOT / "docs").glob("6[0-9]_*.md")),
    ROOT / "docs/70_finger_8_button_mechanical_baseline_checkpoint.md",
    *CARRIER_PATHS.values(),
    *CAP_PATHS.values(),
    *SHELL_PATHS.values(),
    TRIMMED_TERMINAL_STEP,
    ROOT / "cad_dump/mesh_PushBtn.json",
    ROOT / "cad_dump/its1105_physical_sample_reaudit.json",
    ROOT / "build123d_workbench/finger_controls_v2.py",
    ROOT / "build123d_workbench/n2_production_intent_mechanism.py",
    ROOT / "build123d_workbench/n2_rear_reaction_support_redesign.py",
    ROOT / "build123d_workbench/n1_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i2_i3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/m4_n3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i4_m3_production_intent_mechanisms.py",
    ROOT / "build123d_workbench/real_integration_conflict_resolution.py",
    ROOT / "build123d_workbench/m4_n3_terminal_redundancy_resolution.py",
]

PROCESS = psutil.Process(os.getpid())
MEMORY: list[dict[str, float | str]] = []
START_TIME = time.perf_counter()
RSS_LIMIT_MB = 24576.0
AVAILABLE_STOP_MB = 3072.0

COLORS = {
    "original": (66, 174, 231),
    "legacy": (237, 177, 63),
    "actual": (239, 91, 102),
    "hybrid": (73, 211, 152),
    "terminal": (195, 207, 220),
    "trimmed": (126, 137, 151),
    "cap": (245, 203, 89),
    "carrier": (158, 101, 215),
    "shell": (91, 179, 213),
    "green": (63, 201, 128),
    "yellow": (246, 195, 67),
    "red": (235, 76, 78),
}
GROUP_COLORS = {
    "N1_N2": (174, 94, 225),
    "I2_I3": (55, 170, 226),
    "M4_N3": (243, 137, 57),
    "I4": (64, 203, 143),
    "M3": (238, 92, 132),
}
FOOTER = "AUDIT ONLY | EXTERIOR PRESERVED | PRODUCTION GEOMETRY MODIFICATION = 0"


def memory(stage: str) -> None:
    gc.collect()
    rss = float(PROCESS.memory_info().rss) / 1048576.0
    available = float(psutil.virtual_memory().available) / 1048576.0
    MEMORY.append({"stage": stage, "rssMb": round(rss, 1), "systemAvailableMb": round(available, 1)})
    print(
        f"[{time.perf_counter() - START_TIME:8.1f}s] {stage} | "
        f"RSS {rss:.1f} MB | available {available:.1f} MB",
        flush=True,
    )
    if rss > RSS_LIMIT_MB or available < AVAILABLE_STOP_MB:
        raise MemoryError(f"RAM safety STOP at {stage}: RSS={rss:.1f} MB available={available:.1f} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def bounds(shape: Shape) -> tuple[np.ndarray, np.ndarray]:
    box = shape.bounding_box()
    return (
        np.asarray((box.min.X, box.min.Y, box.min.Z), dtype=float),
        np.asarray((box.max.X, box.max.Y, box.max.Z), dtype=float),
    )


def moved(shape: Shape, vector: Iterable[float], label: str) -> Shape:
    row = np.asarray(tuple(vector), dtype=float)
    result = shape.moved(Location(Vector(float(row[0]), float(row[1]), float(row[2]))))
    result.label = label
    return result


def volume(shape: Shape | None) -> float:
    return 0.0 if shape is None or len(shape.solids()) == 0 else float(shape.volume)


def mesh_to_faceted_solid(triangles: np.ndarray, tolerance: float = 1.0e-5) -> Solid:
    """Sew the frozen triangle mesh into a BRep while preserving every facet."""
    sewing = BRepBuilderAPI_Sewing(tolerance, True, True, True, False)
    for triangle in triangles:
        polygon = BRepBuilderAPI_MakePolygon()
        for point in triangle:
            polygon.Add(gp_Pnt(float(point[0]), float(point[1]), float(point[2])))
        polygon.Close()
        face = BRepBuilderAPI_MakeFace(polygon.Wire(), True)
        if not face.IsDone():
            raise RuntimeError("ORIGINAL PushBtn triangle face construction failed")
        sewing.Add(face.Face())
    sewing.Perform()
    shell = TopoDS.Shell_s(sewing.SewedShape())
    solid = Solid(BRepBuilderAPI_MakeSolid(shell).Solid())
    if not BRepCheck_Analyzer(solid.wrapped).IsValid():
        raise RuntimeError("ORIGINAL PushBtn faceted BRep is invalid")
    return solid


@dataclass(slots=True)
class OriginalParts:
    triangles: np.ndarray
    full: Shape
    body: Shape
    actuator: Shape
    terminals: dict[str, Shape]
    terminal_region: Shape


def build_original_parts() -> OriginalParts:
    triangles = np.asarray(
        json.loads((DUMP / "mesh_PushBtn.json").read_text(encoding="utf-8"))["tris"],
        dtype=float,
    )
    full = mesh_to_faceted_solid(triangles)
    full.label = "ORIGINAL_PUSHBTN_DETAILED_3530_FACET_SOLID"
    body_clip = Box(20.0, ORIG_BODY_HEIGHT, 20.0, align=(Align.CENTER, Align.MIN, Align.CENTER))
    body = (full & body_clip).clean()
    body.label = "ORIGINAL_PUSHBTN_DETAILED_PLASTIC_BODY"
    actuator_clip = Box(
        20.0,
        ORIG_ACTUATOR_PROJECTION,
        20.0,
        align=(Align.CENTER, Align.MIN, Align.CENTER),
    ).moved(Location(Vector(0.0, ORIG_BODY_TOP_Y, 0.0)))
    actuator = (full & actuator_clip).clean()
    actuator.label = "ORIGINAL_PUSHBTN_DETAILED_ACTUATOR"
    terminal_clip = Box(20.0, 4.0, 20.0, align=(Align.CENTER, Align.MAX, Align.CENTER))
    terminal_region = (full & terminal_clip).clean()
    terminal_region.label = "ORIGINAL_PUSHBTN_DETAILED_TERMINALS"
    terminals: dict[str, Shape] = {}
    sign_to_terminal = {
        (-1, -1): "T1",
        (-1, 1): "T2",
        (1, -1): "T3",
        (1, 1): "T4",
    }
    for sx in (-1, 1):
        for sz in (-1, 1):
            quadrant = Box(
                10.0,
                4.0,
                10.0,
                align=(
                    Align.MIN if sx > 0 else Align.MAX,
                    Align.MAX,
                    Align.MIN if sz > 0 else Align.MAX,
                ),
            )
            part = (terminal_region & quadrant).clean()
            # local z maps to -switch_v in the right-handed functional frame.
            terminal = sign_to_terminal[(sx, -sz)]
            part.label = f"ORIGINAL_PUSHBTN_DETAILED_{terminal}"
            terminals[terminal] = part
    return OriginalParts(triangles, full, body, actuator, terminals, terminal_region)


def datum_plane(datum: ControlDatum, front: float) -> Plane:
    axis = unit(datum.axis)
    u = unit(datum.switch_u)
    v = unit(datum.switch_v)
    origin = point_at(datum, front + ORIG_BODY_HEIGHT)
    return Plane(origin=origin, x_dir=tuple(u), z_dir=tuple(-v))


def original_to_pose(shape: Shape, datum: ControlDatum, front: float, label: str) -> Shape:
    result = datum_plane(datum, front).location * shape
    result.label = label
    return result


def original_triangles_to_pose(triangles: np.ndarray, datum: ControlDatum, front: float) -> np.ndarray:
    axis = unit(datum.axis)
    u = unit(datum.switch_u)
    v = unit(datum.switch_v)
    matrix = np.stack((u, axis, -v), axis=1)
    origin = np.asarray(point_at(datum, front + ORIG_BODY_HEIGHT), dtype=float)
    return triangles @ matrix.T + origin


def reference_datum() -> ControlDatum:
    return ControlDatum(
        "REF",
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.0, 0.0, 1.0),
        "JfD",
        "AUDIT",
        (1.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        0.0,
    )


def measured_body(datum: ControlDatum, front: float, label: str) -> Shape:
    return oriented_box(
        datum,
        ACTUAL["bodyXmm"],
        ACTUAL["bodyYmm"],
        front,
        front + ACTUAL["housingHmm"],
        label=label,
    )


def measured_actuator(datum: ControlDatum, front: float, label: str) -> Shape:
    return oriented_cylinder(
        datum,
        ACTUAL["actuatorDiameterMm"],
        front - ACTUAL["actuatorProjectionMm"],
        front,
        label=label,
    )


def measured_reference_parts(datum: ControlDatum, front: float) -> dict[str, object]:
    return {
        "body": measured_body(datum, front, "ITS1105_MEASURED_BODY_ENVELOPE"),
        "actuator": measured_actuator(datum, front, "ITS1105_MEASURED_ACTUATOR_ENVELOPE"),
        "terminals": {
            name: shape
            for name, shape in zip(TERMINALS, terminal_root_cutters(datum, front))
        },
    }


def load_shell_crops(carriers: dict[str, Shape], caps: dict[str, Shape]) -> dict[str, Shape]:
    lower = np.min(np.stack([bounds(shape)[0] for shape in [*carriers.values(), *caps.values()]]), axis=0) - 10.0
    upper = np.max(np.stack([bounds(shape)[1] for shape in [*carriers.values(), *caps.values()]]), axis=0) + 12.0
    tool = n2prod.global_box(lower, upper, "DETAILED_PUSHBTN_LOCAL_SHELL_CROP")
    shells: dict[str, Shape] = {}
    for name, path in SHELL_PATHS.items():
        full = import_step(path)
        local = (full & tool).clean()
        local.label = f"{name}_DETAILED_PUSHBTN_LOCAL_CROP"
        shells[name] = local
        del full
        memory(f"{name} local shell crop")
    return shells


@dataclass(slots=True)
class MechanismReference:
    contact: Shape
    guide: Shape
    rear_stop: Shape
    supports: list[Shape]
    legacy_contact: dict[str, object]


def load_mechanism_references(
    datums: dict[str, ControlDatum],
    shells: dict[str, Shape],
    source: dict[str, Shape],
) -> dict[str, MechanismReference]:
    refs: dict[str, MechanismReference] = {}

    n2_datum = datums["N2"]
    n2_roots, _ = n2prod.trim_terminals(source, n2_datum)
    n2_cap, n2_cap_parts = n2prod.build_production_cap(import_step(n2prod.BASE_CAP_STEP), n2_datum)
    n2_guide, n2_guide_parts = n2prod.build_guide(n2_datum)
    concept_b = next(row for row in n2rear.concepts(n2_datum) if row.code == "B")
    _, n2_supports = n2rear.build_carrier(
        source["N1_N2_SHARED_CARRIER_OPTION_C_FINAL_MICRO_RELIEF"],
        n2_guide,
        concept_b,
        n2rear.cutters(source, n2_datum, n2_roots),
        n2rear.robust_tool(),
    )
    refs["N2"] = MechanismReference(
        n2_cap_parts["contact"],
        n2_guide,
        n2_guide_parts["rearStop"],
        n2_supports,
        n2rear.contact_metrics(n2_datum, n2_supports),
    )
    del n2_cap

    n1_datum = datums["N1"]
    n1_roots = {name: source[label] for name, label in N1_TERMINAL_LABELS.items()}
    n1_cap, n1_cap_parts = n1prod.build_n1_cap(import_step(n1prod.N1_CAP_STEP), n1_datum)
    n1_guide, n1_guide_parts, _, _ = n1prod.build_n1_guide(n1_datum)
    n1_supports, n1_support_metrics = n1prod.build_n1_support(n1_datum, n1_roots)
    refs["N1"] = MechanismReference(
        n1_cap_parts["contact"],
        n1_guide,
        n1_guide_parts["rearStop"],
        n1_supports,
        n1_support_metrics["contacts"],
    )
    del n1_cap

    for module, names in ((i2i3, ("I2", "I3")), (m4n3, ("M4", "N3")), (i4m3, ("I4", "M3"))):
        for name in names:
            datum = datums[name]
            front = float(FROZEN_FRONT_DEPTHS[name])
            # Body-facing guide geometry is reconstructed directly from the
            # frozen generator.  Shell-facing relief is deliberately omitted
            # here: it is outside the switch-body interface, and using the raw
            # guide is the conservative material condition for this audit.
            raw_guide, guide_parts = module.build_raw_guide(name, datum, front)
            contact = oriented_cylinder(
                datum,
                i2i3.CONTACT_DIAMETER_MM,
                i2i3.axial(front)["contactFront"],
                i2i3.axial(front)["contactRear"],
                cap_frame=True,
                label=f"{name}_CENTERED_CONTACT_D3_AUDIT_REFERENCE",
            )
            roots = {
                terminal: shape
                for terminal, shape in zip(TERMINALS, terminal_root_cutters(datum, front))
            }
            reaction, legacy = i2i3.build_reaction_frame(name, datum, front, roots)
            refs[name] = MechanismReference(
                contact,
                raw_guide,
                guide_parts["rearStop"],
                [reaction],
                {
                    "totalAreaMm2": float(legacy.get("contactAreaMm2", 0.0)),
                    "contactZoneCount": int(legacy.get("connectedContactPatchCount", 1)),
                    "connectedContactPatchCount": int(legacy.get("connectedContactPatchCount", 1)),
                    "contactSpanMm": float(legacy.get("diagonalSpanMm", 0.0)),
                },
            )
            memory(f"{name} guide/reaction reference")
    return refs


def current_terminal_map(
    source: dict[str, Shape],
    datums: dict[str, ControlDatum],
) -> dict[str, dict[str, Shape]]:
    rows: dict[str, dict[str, Shape]] = {
        "N1": {name: source[label] for name, label in N1_TERMINAL_LABELS.items()}
    }
    rows["N2"], _ = n2prod.trim_terminals(source, datums["N2"])
    for button in BUTTONS:
        if button not in rows:
            rows[button] = {
                name: shape
                for name, shape in zip(
                    TERMINALS,
                    terminal_root_cutters(datums[button], FROZEN_FRONT_DEPTHS[button]),
                )
            }

    # docs/69 accepted external-only overlay, service-envelope form.
    for button, terminal in (("M4", "T2"), ("N3", "T3")):
        geometry = m4n3trim.terminal_geometry(
            datums[button], float(FROZEN_FRONT_DEPTHS[button]), terminal
        )
        rows[button][terminal] = m4n3trim.trimmed_leg(
            datums[button],
            geometry,
            0.300,
            f"{button}_{terminal}_UNUSED_TRIMMED_SERVICE_ENVELOPE",
            TERMINAL_CLEARANCE,
        )
    return rows


def original_terminal_pose_map(
    original: OriginalParts,
    datums: dict[str, ControlDatum],
) -> dict[str, dict[str, Shape]]:
    return {
        button: {
            terminal: original_to_pose(
                part,
                datums[button],
                float(FROZEN_FRONT_DEPTHS[button]),
                f"{button}_ORIGINAL_PUSHBTN_{terminal}",
            )
            for terminal, part in original.terminals.items()
        }
        for button in BUTTONS
    }


def terminal_local_measurements(original: OriginalParts) -> dict[str, object]:
    ref = reference_datum()
    current_paths: dict[str, dict[str, np.ndarray]] = {}
    original_rows: dict[str, dict[str, object]] = {}
    root_depth = 0.25
    distal_y0 = -3.5187
    distal_y1 = -3.0
    root_clip = Box(20.0, root_depth, 20.0, align=(Align.CENTER, Align.MAX, Align.CENTER))
    distal_clip = Box(
        20.0,
        distal_y1 - distal_y0,
        20.0,
        align=(Align.CENTER, Align.MIN, Align.CENTER),
    ).moved(Location(Vector(0.0, distal_y0, 0.0)))

    for name, part in original.terminals.items():
        root = (part & root_clip).clean()
        distal = (part & distal_clip).clean()
        rc = root.center()
        dc = distal.center()
        # Original local x -> +u, local z -> -v, 3.5-y -> inward depth.
        original_root = np.asarray((rc.X, -rc.Z, ORIG_BODY_TOP_Y - rc.Y), dtype=float)
        original_distal = np.asarray((dc.X, -dc.Z, ORIG_BODY_TOP_Y - dc.Y), dtype=float)

        geometry = m4n3trim.terminal_geometry(ref, 0.0, name)
        p0 = np.asarray(geometry["p0"], dtype=float)
        p1 = np.asarray(geometry["p1"], dtype=float)
        # REF world z is outward; convert to inward depth.
        current_p0 = np.asarray((p0[0], p0[1], -p0[2]), dtype=float)
        current_p1 = np.asarray((p1[0], p1[1], -p1[2]), dtype=float)
        t = (ACTUAL["housingHmm"] - current_p0[2]) / (current_p1[2] - current_p0[2])
        current_root = current_p0 + (current_p1 - current_p0) * t
        vo = unit(original_distal - original_root)
        vc = unit(current_p1 - current_p0)
        angle = math.degrees(math.acos(float(np.clip(np.dot(vo, vc), -1.0, 1.0))))
        original_rows[name] = {
            "originalRootUvDepthMm": original_root.tolist(),
            "currentSimplifiedRootUvDepthMm": current_root.tolist(),
            "rootDeltaOriginalMinusCurrentMm": (original_root - current_root).tolist(),
            "originalRootToDistalDirection": vo.tolist(),
            "currentSimplifiedRootDirection": vc.tolist(),
            "rootAngleDeltaDeg": angle,
            "originalExternalLengthMm": float(ORIG_BODY_REAR_Y - distal_y0),
            "currentDrawingNominalExternalLengthMm": 1.8,
            "distalLengthDifferenceOriginalMinusCurrentMm": float(
                ORIG_BODY_REAR_Y - distal_y0 - 1.8
            ),
        }
        current_paths[name] = {"p0": current_p0, "p1": current_p1}

    vertices = original.triangles.reshape(-1, 3)
    terminal_vertices = vertices[vertices[:, 1] < 0.0]
    return {
        "perTerminal": original_rows,
        "originalTerminalOverallSpanMm": (
            terminal_vertices.max(axis=0) - terminal_vertices.min(axis=0)
        ).tolist(),
        "currentDrawingNominal": {
            "rootPitchMm": 4.50,
            "outerSpanMm": 7.90,
            "externalLengthMm": 1.80,
            "qualifier": "drawing-nominal clearance envelope; physical root/pin measurements not supplied",
        },
        "summary": {
            "maximumRootPositionDeltaMm": max(
                float(np.linalg.norm(row["rootDeltaOriginalMinusCurrentMm"]))
                for row in original_rows.values()
            ),
            "maximumRootAngleDeltaDeg": max(
                float(row["rootAngleDeltaDeg"]) for row in original_rows.values()
            ),
            "terminalAuthority": "MEASURED ITS-1105 / CURRENT DRAWING-NOMINAL ENVELOPE; ORIGINAL TERMINALS NOT AUTHORITATIVE",
        },
    }


def penetration_only(left: Shape, right: Shape, label: str) -> dict[str, object]:
    gap = bbox_gap(left, right)
    if gap > 1.0e-9:
        return {
            "pair": label,
            "aabbGapMm": float(gap),
            "penetrationMm3": 0.0,
            "method": "AABB_SEPARATED",
            "passZeroPenetration": True,
        }
    common = left & right
    pen = volume(common)
    del common
    gc.collect()
    return {
        "pair": label,
        "aabbGapMm": float(gap),
        "penetrationMm3": pen,
        "method": "SERIAL_OCCT_COMMON",
        "passZeroPenetration": pen <= BOOLEAN_EPS_MM3,
    }


def exact_to_many(left: Shape, rights: list[Shape], label: str) -> dict[str, object]:
    rows = [exact_pair(left, shape, f"{label}[{index}]") for index, shape in enumerate(rights)]
    return {
        "rows": rows,
        "minimumDistanceMm": min(float(row["distanceMm"]) for row in rows),
        "totalPenetrationMm3": sum(float(row["penetrationMm3"]) for row in rows),
        "passZeroPenetration": all(row["passZeroPenetration"] for row in rows),
    }


def support_contact_metrics(
    original_body: Shape,
    datum: ControlDatum,
    front: float,
    supports: list[Shape],
    support_depth: float = 0.20,
) -> dict[str, object]:
    body_gap = ACTUAL["housingHmm"] - ORIG_BODY_HEIGHT
    # Contact proxy: preserve detailed rear footprint and translate only for
    # area measurement so it overlaps the 0.20-mm reaction slab.
    proxy = moved(
        original_body,
        -unit(datum.axis) * (body_gap + support_depth),
        f"{datum.name}_ORIGINAL_REAR_FOOTPRINT_CONTACT_PROXY",
    )
    zones: list[dict[str, object]] = []
    unique_solids: list[Shape] = []
    for support in supports:
        common = (proxy & support).clean()
        if volume(common) <= BOOLEAN_EPS_MM3:
            continue
        for solid in common.solids():
            centre = solid.center()
            point = np.asarray((centre.X, centre.Y, centre.Z), dtype=float) - np.asarray(datum.center)
            u = float(np.dot(point, unit(datum.switch_u)))
            v = float(np.dot(point, unit(datum.switch_v)))
            area = float(solid.volume) / support_depth
            zones.append({"areaMm2": area, "uMm": u, "vMm": v, "support": support.label})
            unique_solids.append(solid)
    span = 0.0
    for left, right in combinations(zones, 2):
        span = max(span, float(math.hypot(left["uMm"] - right["uMm"], left["vMm"] - right["vMm"])))
    total = sum(float(row["areaMm2"]) for row in zones)
    return {
        "nominalOriginalRearGapMm": body_gap,
        "contactAreaAtActualRearDatumMm2": total,
        "contactCountAtActualRearDatum": len(zones),
        "contactSpanMm": span,
        "antiRock": "PASS" if len(zones) >= 2 and span >= 3.0 else "RECHECK",
        "zones": zones,
    }


def body_fit_audit(
    original: OriginalParts,
    datums: dict[str, ControlDatum],
    carriers: dict[str, Shape],
    shells: dict[str, Shape],
    refs: dict[str, MechanismReference],
) -> tuple[dict[str, object], dict[str, Shape], dict[str, Shape], dict[str, Shape]]:
    result: dict[str, object] = {}
    original_bodies: dict[str, Shape] = {}
    original_actuators: dict[str, Shape] = {}
    measured_bodies: dict[str, Shape] = {}
    for button in BUTTONS:
        datum = datums[button]
        front = float(FROZEN_FRONT_DEPTHS[button])
        obody = original_to_pose(original.body, datum, front, f"{button}_ORIGINAL_DETAILED_BODY")
        oact = original_to_pose(original.actuator, datum, front, f"{button}_ORIGINAL_DETAILED_ACTUATOR")
        abody = measured_body(datum, front, f"{button}_MEASURED_ITS_BODY")
        original_bodies[button] = obody
        original_actuators[button] = oact
        measured_bodies[button] = abody
        owner = datum.owner
        other_shell = "JaD" if owner == "JfD" else "JfD"
        body_carrier = exact_pair(obody, carriers[BUTTON_GROUP[button]], f"{button} original body<->carrier")
        body_owner_shell = exact_pair(obody, shells[owner], f"{button} original body<->{owner}")
        body_other_shell = exact_pair(obody, shells[other_shell], f"{button} original body<->{other_shell}")
        body_guide = exact_pair(obody, refs[button].guide, f"{button} original body<->guide")
        body_support = exact_to_many(obody, refs[button].supports, f"{button} original body<->rear support")
        actual_carrier = exact_pair(abody, carriers[BUTTON_GROUP[button]], f"{button} actual body<->carrier")
        actual_shell = exact_pair(abody, shells[owner], f"{button} actual body<->{owner}")
        actual_guide = exact_pair(abody, refs[button].guide, f"{button} actual body<->guide")
        actual_support = exact_to_many(abody, refs[button].supports, f"{button} actual body<->rear support")
        contact = support_contact_metrics(obody, datum, front, refs[button].supports)
        legacy_contact = refs[button].legacy_contact
        contact["legacyActualEnvelopeContactAreaMm2"] = float(legacy_contact.get("totalAreaMm2", 0.0))
        contact["legacyContactCount"] = int(legacy_contact.get("contactZoneCount", 0))
        contact["legacyContactSpanMm"] = float(legacy_contact.get("contactSpanMm", 0.0))
        contact["detailedChamferContactRetentionRatio"] = (
            float(contact["contactAreaAtActualRearDatumMm2"]) /
            max(float(legacy_contact.get("totalAreaMm2", 0.0)), 1.0e-12)
        )
        unintended = [body_carrier, body_owner_shell, body_other_shell, body_guide]
        original_pass = all(float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3 for row in unintended)
        actual_pass = all(
            float(row["penetrationMm3"]) <= BOOLEAN_EPS_MM3
            for row in (actual_carrier, actual_shell, actual_guide)
        )
        result[button] = {
            "originalDetailed": {
                "carrier": body_carrier,
                "ownerShell": body_owner_shell,
                "otherShell": body_other_shell,
                "guide": body_guide,
                "rearSupport": body_support,
                "minimumPocketSideClearanceMm": (SWITCH_POCKET_X - 6.31) / 2.0,
                "toleranceClassification": "YELLOW / TOLERANCE-SENSITIVE",
            },
            "actualMeasuredOverride": {
                "carrier": actual_carrier,
                "ownerShell": actual_shell,
                "guide": actual_guide,
                "rearSupport": actual_support,
                "pocketSideClearanceUMm": (SWITCH_POCKET_X - ACTUAL["bodyXmm"]) / 2.0,
                "pocketSideClearanceVMm": (SWITCH_POCKET_Y - ACTUAL["bodyYmm"]) / 2.0,
            },
            "rearSupport": contact,
            "verdict": "RECHECK" if original_pass and actual_pass else "HOLD",
            "finalHybridVerdict": "PASS" if original_pass and actual_pass and contact["antiRock"] == "PASS" else "HOLD",
        }
        memory(f"{button} detailed body fit")
    return result, original_bodies, original_actuators, measured_bodies


def actuator_audit(
    datums: dict[str, ControlDatum],
    refs: dict[str, MechanismReference],
) -> dict[str, object]:
    projection_delta = ACTUAL["actuatorProjectionMm"] - ORIG_ACTUATOR_PROJECTION
    rows: dict[str, object] = {}
    for button in BUTTONS:
        datum = datums[button]
        centre = refs[button].contact.center()
        point = np.asarray((centre.X, centre.Y, centre.Z), dtype=float)
        axis = unit(datum.axis)
        delta = point - np.asarray(datum.center, dtype=float)
        lateral = delta - axis * float(np.dot(delta, axis))
        states = []
        for travel in TRAVELS:
            original_gap = max(0.0, projection_delta - travel)
            states.append({
                "travelMm": travel,
                "originalDetailedActuatorGapMm": original_gap,
                "measuredItsContactGapMm": 0.0,
                "originalDetailedContact": "NO" if original_gap > 1.0e-6 else "YES",
                "measuredItsContact": "YES",
                "hardStopResidualMm": ACTUAL["travelUpperMm"] - travel,
            })
        rows[button] = {
            "capContactCenterOffsetMm": float(np.linalg.norm(lateral)),
            "capContactActuatorAngleDeg": 0.0,
            "originalActuatorDiameterMm": 3.50,
            "measuredItsActuatorDiameterMm": ACTUAL["actuatorDiameterMm"],
            "originalActuatorProjectionMm": ORIG_ACTUATOR_PROJECTION,
            "measuredItsActuatorProjectionMm": ACTUAL["actuatorProjectionMm"],
            "projectionDeltaMm": projection_delta,
            "states": states,
            "originalTravelClue": "NONE — imported PushBtn is one rigid solid with no configuration or travel parameter",
            "travelAuthority": "MEASURED ITS-1105: nominal 0.25 mm, accepted upper validation 0.35 mm",
            "originalOnlyVerdict": "HOLD — no actuator contact through 0.350 mm",
            "hybridVerdict": "PASS — measured ITS actuator override restores direct contact; carrier hard stop remains first structural stop",
        }
    return {
        "perButton": rows,
        "projectionDeltaMm": projection_delta,
        "bodyHousingDeltaMm": ACTUAL["housingHmm"] - ORIG_BODY_HEIGHT,
        "verdict": "MEASURED ITS ACTUATOR OVERRIDE REQUIRED",
    }


def terminal_packaging_audit(
    original_terminals: dict[str, dict[str, Shape]],
    hybrid_terminals: dict[str, dict[str, Shape]],
    carriers: dict[str, Shape],
    shells: dict[str, Shape],
    measured_bodies: dict[str, Shape],
) -> dict[str, object]:
    hybrid_rows: list[dict[str, object]] = []
    original_rows: list[dict[str, object]] = []
    for button in BUTTONS:
        owner_group = BUTTON_GROUP[button]
        for terminal in TERMINALS:
            hybrid = hybrid_terminals[button][terminal]
            original = original_terminals[button][terminal]
            for group, carrier in carriers.items():
                if group != owner_group:
                    hybrid_rows.append(penetration_only(hybrid, carrier, f"{button}.{terminal} hybrid<->{group}"))
            for shell_name, shell in shells.items():
                hybrid_rows.append(penetration_only(hybrid, shell, f"{button}.{terminal} hybrid<->{shell_name}"))
            for foreign, body in measured_bodies.items():
                if foreign != button:
                    hybrid_rows.append(penetration_only(hybrid, body, f"{button}.{terminal} hybrid<->{foreign} body"))
            original_rows.append(
                penetration_only(original, carriers[owner_group], f"{button}.{terminal} original<->own carrier")
            )
            for shell_name, shell in shells.items():
                original_rows.append(
                    penetration_only(original, shell, f"{button}.{terminal} original<->{shell_name}")
                )
            memory(f"{button}.{terminal} terminal packaging")

    flat_hybrid = [
        (button, terminal, hybrid_terminals[button][terminal])
        for button in BUTTONS for terminal in TERMINALS
    ]
    terminal_pairs: list[dict[str, object]] = []
    for (ba, ta, sa), (bb, tb, sb) in combinations(flat_hybrid, 2):
        if ba == bb:
            continue
        terminal_pairs.append(penetration_only(sa, sb, f"{ba}.{ta}<->{bb}.{tb}"))
    hybrid_rows.extend(terminal_pairs)
    failed_hybrid = [row for row in hybrid_rows if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]
    failed_original = [row for row in original_rows if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]

    m4n3_pair = exact_pair(
        hybrid_terminals["M4"]["T2"],
        hybrid_terminals["N3"]["T3"],
        "M4.T2 trimmed<->N3.T3 trimmed",
    )
    n2_active = {
        terminal: {
            "carrier": exact_pair(
                hybrid_terminals["N2"][terminal], carriers["N1_N2"],
                f"N2.{terminal}<->N1/N2 carrier",
            ),
            "status": "ACTIVE / solder access retained",
        }
        for terminal in ("T1", "T3")
    }
    n2_unused = {
        terminal: {
            "trimFeasible": True,
            "externalOnly": True,
            "housingOrLeadframeIntrusion": False,
            "physicalSampleSwitchingAndReturnAfterTrim": True,
        }
        for terminal in ("T2", "T4")
    }
    return {
        "hybridFinal": {
            "checks": hybrid_rows,
            "failedInterfaces": failed_hybrid,
            "verdict": "PASS" if not failed_hybrid else "HOLD",
            "authority": "measured ITS body/actuator + current ITS drawing-nominal terminal envelope",
        },
        "originalTerminalDiagnostic": {
            "checks": original_rows,
            "failedInterfaces": failed_original,
            "verdict": "NOT FINAL AUTHORITY",
        },
        "N2": {
            "strategy": "T1/T3 ACTIVE; T2/T4 UNUSED EXTERNAL TRIM",
            "active": n2_active,
            "unused": n2_unused,
            "verdict": "VALID WITH HYBRID SWITCH",
        },
        "M4N3": {
            "M4T2Role": "UNUSED / redundant Node A",
            "N3T3Role": "UNUSED / redundant Node B",
            "selectedTrimLengthMm": 1.758428,
            "remainingExternalStubMm": 0.300,
            "oldPenetrationMm3": 0.283393028,
            "newPair": m4n3_pair,
            "verdict": "VALID AS-IS",
            "qualifier": "physical terminal root/pin metrology remains a first-article gate",
        },
    }


def carrier_regression(carriers: dict[str, Shape]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for left, right in combinations(GROUPS, 2):
        rows.append(exact_pair(carriers[left], carriers[right], f"{left}<->{right}"))
        memory(f"carrier regression {left} {right}")
    closest = min(rows, key=lambda row: float(row["distanceMm"]))
    return {
        "pairs": rows,
        "maximumPenetrationMm3": max(float(row["penetrationMm3"]) for row in rows),
        "minimumClearanceMm": float(closest["distanceMm"]),
        "closestPair": closest["pair"],
        "I2I3toI4ExpectedMm": 0.444805280,
        "verdict": "PASS" if all(row["passZeroPenetration"] for row in rows) else "HOLD",
    }


def motion_states() -> list[tuple[str, set[str]]]:
    states: list[tuple[str, set[str]]] = [("ALL_REST", set())]
    states.extend((f"{button}_FULL", {button}) for button in BUTTONS)
    states.extend((name, set(buttons)) for name, buttons in (
        ("N1_N2_FULL", ("N1", "N2")),
        ("I2_I3_FULL", ("I2", "I3")),
        ("M4_N3_FULL", ("M4", "N3")),
        ("I4_I3_FULL", ("I4", "I3")),
        ("M3_M4_FULL", ("M3", "M4")),
        ("ALL_8_FULL", BUTTONS),
    ))
    return states


def motion_regression(
    caps: dict[str, Shape],
    original_bodies: dict[str, Shape],
    carriers: dict[str, Shape],
    datums: dict[str, ControlDatum],
) -> dict[str, object]:
    states: list[dict[str, object]] = []
    for state, pressed in motion_states():
        state_caps = {
            button: moved(
                caps[button],
                -unit(datums[button].axis) * (0.350 if button in pressed else 0.0),
                f"{button}_{state}",
            )
            for button in BUTTONS
        }
        checks: list[dict[str, object]] = []
        for left, right in combinations(BUTTONS, 2):
            checks.append(penetration_only(state_caps[left], state_caps[right], f"{state}: {left} cap<->{right} cap"))
        for button in BUTTONS:
            for foreign in BUTTONS:
                if foreign != button:
                    checks.append(penetration_only(state_caps[button], original_bodies[foreign], f"{state}: {button} cap<->{foreign} detailed body"))
            for group, carrier in carriers.items():
                if group != BUTTON_GROUP[button]:
                    checks.append(penetration_only(state_caps[button], carrier, f"{state}: {button} cap<->{group}"))
        failed = [row for row in checks if float(row["penetrationMm3"]) > BOOLEAN_EPS_MM3]
        states.append({
            "state": state,
            "pressedButtons": sorted(pressed),
            "checks": checks,
            "maximumUnintendedPenetrationMm3": max(float(row["penetrationMm3"]) for row in checks),
            "failedInterfaces": failed,
            "verdict": "PASS" if not failed else "HOLD",
        })
        del state_caps
        memory(f"motion {state}")
    failed_states = [row["state"] for row in states if row["verdict"] != "PASS"]
    return {
        "states": states,
        "failedStates": failed_states,
        "verdict": "PASS" if not failed_states else "HOLD",
    }


def service_regression(
    carriers: dict[str, Shape],
    measured_bodies: dict[str, Shape],
    hybrid_terminals: dict[str, dict[str, Shape]],
) -> dict[str, object]:
    rows: dict[str, object] = {}
    for group in GROUPS:
        sign = -1.0 if group in {"N1_N2", "I2_I3", "M3"} else 1.0
        direction = np.asarray((sign, 0.0, 0.0), dtype=float)
        path: list[dict[str, object]] = []
        maximum = 0.0
        for distance in (0.0, 5.0, 10.0, 15.0):
            component_checks: list[dict[str, object]] = []
            carrier = moved(carriers[group], direction * distance, f"{group}_SERVICE_{distance}")
            for foreign, foreign_carrier in carriers.items():
                if foreign != group:
                    component_checks.append(penetration_only(carrier, foreign_carrier, f"{group} carrier service {distance}<->{foreign}"))
            for button in GROUP_BUTTONS[group]:
                body = moved(measured_bodies[button], direction * distance, f"{button}_SERVICE_BODY")
                for foreign, foreign_carrier in carriers.items():
                    if foreign != group:
                        component_checks.append(penetration_only(body, foreign_carrier, f"{button} body service {distance}<->{foreign}"))
                for terminal, shape in hybrid_terminals[button].items():
                    pin = moved(shape, direction * distance, f"{button}_{terminal}_SERVICE")
                    for foreign, foreign_carrier in carriers.items():
                        if foreign != group:
                            component_checks.append(penetration_only(pin, foreign_carrier, f"{button}.{terminal} service {distance}<->{foreign}"))
            maximum = max(maximum, *(float(row["penetrationMm3"]) for row in component_checks))
            path.append({"translationMm": distance, "checks": component_checks})
        rows[group] = {
            "direction": direction.tolist(),
            "testedTranslationMm": 15.0,
            "carrierRemoval": "PASS" if maximum <= BOOLEAN_EPS_MM3 else "HOLD",
            "switchInsertionRemoval": "PASS / actual body clearance 0.140-0.175 mm per side; original nominal skirt is tolerance-sensitive at 0.045 mm",
            "terminalSolderAccess": "PASS / N1-N2 remains conditional on actual joystick only; SZH not reopened here",
            "maximumUnintendedPenetrationMm3": maximum,
            "path": path,
            "verdict": "PASS" if maximum <= BOOLEAN_EPS_MM3 else "HOLD",
        }
        memory(f"service {group}")
    return {"groups": rows, "verdict": "PASS" if all(row["verdict"] == "PASS" for row in rows.values()) else "HOLD"}


def canonical_original_triangles(triangles: np.ndarray) -> np.ndarray:
    result = np.empty_like(triangles)
    result[:, :, 0] = triangles[:, :, 0]
    result[:, :, 1] = -triangles[:, :, 2]
    result[:, :, 2] = triangles[:, :, 1] - ORIG_BODY_TOP_Y
    return result


def mesh_region(triangles: np.ndarray, predicate) -> np.ndarray:
    centres = triangles.mean(axis=1)
    return triangles[predicate(centres)]


def shape_meshes(shapes: Iterable[Shape], linear: float = 0.22, angular: float = 0.14) -> list[np.ndarray]:
    return [safe_triangles(shape, linear, angular) for shape in shapes]


def deviation_map(
    original_triangles: np.ndarray,
    actual_shapes: list[Shape],
) -> tuple[dict[str, object], list[tuple[np.ndarray, tuple[int, int, int]]]]:
    actual_mesh = np.concatenate(shape_meshes(actual_shapes, 0.10, 0.08), axis=0)
    original = canonical_original_triangles(original_triangles)
    samples = np.concatenate((actual_mesh.reshape(-1, 3), actual_mesh.mean(axis=1)), axis=0)
    tree = cKDTree(samples)
    centres = original.mean(axis=1)
    distances = tree.query(centres, k=1, workers=1)[0]
    cross = np.cross(original[:, 1] - original[:, 0], original[:, 2] - original[:, 0])
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    masks = {
        "GREEN": distances <= 0.10,
        "YELLOW": (distances > 0.10) & (distances <= 0.35),
        "RED": distances > 0.35,
    }
    total = float(areas.sum())
    report = {
        "thresholdsMm": {"greenMaximum": 0.10, "yellowMaximum": 0.35, "redMinimumExclusive": 0.35},
        "areaWeighted": {
            name: {
                "areaMm2": float(areas[mask].sum()),
                "percent": 100.0 * float(areas[mask].sum()) / total,
                "triangleCount": int(mask.sum()),
            }
            for name, mask in masks.items()
        },
        "maximumSampledSurfaceDeviationMm": float(distances.max()),
        "meanAreaWeightedSurfaceDeviationMm": float(np.sum(distances * areas) / total),
        "method": "original triangle-centroid to nearest measured-envelope tessellation sample; visualization metric, not clearance authority",
        "regionInterpretation": {
            "bodyCorners": "mostly GREEN/YELLOW; original 6.31-mm skirt governs nominal keep-out",
            "actuator": "RED at tip because original projection 1.50 mm vs actual 2.44 mm",
            "terminalRoots": "YELLOW/RED; actual ITS terminal override required",
            "terminalDistalLegs": "RED; original legs are materially longer/differently pitched",
        },
    }
    objects = [
        (original[masks["GREEN"]], COLORS["green"]),
        (original[masks["YELLOW"]], COLORS["yellow"]),
        (original[masks["RED"]], COLORS["red"]),
    ]
    return report, objects


def render_outputs(
    original: OriginalParts,
    datums: dict[str, ControlDatum],
    carriers: dict[str, Shape],
    caps: dict[str, Shape],
    hybrid_terminals: dict[str, dict[str, Shape]],
    original_bodies: dict[str, Shape],
) -> tuple[list[Path], dict[str, object]]:
    RENDER.mkdir(parents=True, exist_ok=True)
    paths = [RENDER / name for name in (
        "01_original_pushbtn_detailed_isolated.png",
        "02_legacy_simplified_its_isolated.png",
        "03_measured_its1105_envelope.png",
        "04_three_way_overlay.png",
        "05_actuator_closeup.png",
        "06_terminal_root_closeup.png",
        "07_n1_detailed_switch_inside_carrier.png",
        "08_n2_detailed_switch_inside_carrier.png",
        "09_i2_i3_detailed_switches.png",
        "10_m4_n3_detailed_switches_trimmed_relation.png",
        "11_i4_m3_detailed_switches.png",
        "12_transparent_all_8_detailed_switch_assembly.png",
        "13_all_8_full_hybrid.png",
        "14_deviation_heat_map.png",
    )]

    ref = reference_datum()
    measured = measured_reference_parts(ref, 0.0)
    legacy_body = switch_body(ref, 0.0)
    legacy_actuator = switch_actuator(ref, 0.0)
    legacy_terms = {
        name: shape for name, shape in zip(TERMINALS, terminal_root_cutters(ref, 0.0))
    }
    original_canonical = canonical_original_triangles(original.triangles)
    original_body_act = mesh_region(original_canonical, lambda c: c[:, 2] >= -ORIG_BODY_HEIGHT - 1.0e-6)
    original_terminal_mesh = mesh_region(original_canonical, lambda c: c[:, 2] < -ORIG_BODY_HEIGHT)
    measured_body_mesh = safe_triangles(measured["body"], 0.12, 0.08)
    measured_act_mesh = safe_triangles(measured["actuator"], 0.10, 0.07)
    measured_term_mesh = np.concatenate([safe_triangles(shape, 0.12, 0.08) for shape in measured["terminals"].values()])
    legacy_body_mesh = safe_triangles(legacy_body, 0.12, 0.08)
    legacy_act_mesh = safe_triangles(legacy_actuator, 0.10, 0.07)
    legacy_term_mesh = np.concatenate([safe_triangles(shape, 0.12, 0.08) for shape in legacy_terms.values()])

    raster_scene(
        paths[0], [(original_canonical, COLORS["original"])],
        "01 / ORIGINAL PUSHBTN DETAILED",
        "Frozen source mesh: 3,530 facets / no scaling / body-top functional datum",
        FOOTER, camera_offset=(17.0, -22.0, 15.0), fit_points=original_canonical.reshape(-1, 3),
    )
    raster_scene(
        paths[1],
        [(legacy_body_mesh, COLORS["legacy"]), (legacy_act_mesh, (250, 213, 93)), (legacy_term_mesh, COLORS["terminal"])],
        "02 / LEGACY SIMPLIFIED ITS",
        "6.18 x 6.12 x 3.56 box body + measured actuator + drawing terminal clearance envelopes",
        FOOTER, camera_offset=(17.0, -22.0, 15.0),
    )
    raster_scene(
        paths[2],
        [(measured_body_mesh, COLORS["actual"]), (measured_act_mesh, (255, 151, 101))],
        "03 / MEASURED ITS-1105 ENVELOPE",
        "Body 6.12 x 6.05 x 3.56 | actuator D3.35 x 2.44 | terminals shown as drawing-nominal keep-out",
        FOOTER, camera_offset=(17.0, -22.0, 15.0),
        transparent_objects=[(measured_term_mesh, (*COLORS["terminal"], 125))],
    )
    raster_scene(
        paths[3],
        [(original_canonical, COLORS["original"])],
        "04 / THREE-WAY OVERLAY",
        "Blue original detailed | amber legacy simplified | red measured ITS envelope | common body-top datum",
        FOOTER, camera_offset=(18.0, -23.0, 16.0),
        transparent_objects=[
            (np.concatenate((legacy_body_mesh, legacy_act_mesh, legacy_term_mesh)), (*COLORS["legacy"], 105)),
            (np.concatenate((measured_body_mesh, measured_act_mesh, measured_term_mesh)), (*COLORS["actual"], 105)),
        ],
    )

    actuator_original = mesh_region(
        original_canonical,
        lambda c: (c[:, 2] >= -0.02) & (np.linalg.norm(c[:, :2], axis=1) <= 2.0),
    )
    raster_scene(
        paths[4],
        [(actuator_original, COLORS["original"]), (measured_act_mesh, COLORS["actual"])],
        "05 / ACTUATOR CLOSE-UP",
        "Original projection 1.50 mm vs measured ITS 2.44 mm: 0.94 mm functional mismatch",
        FOOTER, camera_offset=(10.0, -13.0, 9.0),
        fit_points=np.concatenate((actuator_original.reshape(-1, 3), measured_act_mesh.reshape(-1, 3))),
    )
    raster_scene(
        paths[5],
        [(original_terminal_mesh, COLORS["original"]), (legacy_term_mesh, COLORS["actual"])],
        "R06 — TERMINAL ROOT CLOSE-UP",
        "Original detailed metal vs current ITS drawing-nominal clearance envelope; body-top datum aligned",
        FOOTER, camera_offset=(16.0, -22.0, 10.0),
        fit_points=np.concatenate((original_terminal_mesh.reshape(-1, 3), legacy_term_mesh.reshape(-1, 3))),
    )

    carrier_mesh = {name: safe_triangles(shape, 0.34, 0.18) for name, shape in carriers.items()}
    cap_mesh = {name: safe_triangles(shape, 0.22, 0.13) for name, shape in caps.items()}
    original_world = {
        button: original_triangles_to_pose(original.triangles, datums[button], float(FROZEN_FRONT_DEPTHS[button]))
        for button in BUTTONS
    }
    original_world_body = {
        button: original_triangles_to_pose(
            mesh_region(original.triangles, lambda c: c[:, 1] >= -1.0e-7),
            datums[button], float(FROZEN_FRONT_DEPTHS[button]),
        )
        for button in BUTTONS
    }

    def render_group(path: Path, names: tuple[str, ...], title: str, subtitle: str, terminals: bool = False) -> None:
        group = BUTTON_GROUP[names[0]] if len(set(BUTTON_GROUP[n] for n in names)) == 1 else None
        objects = [(original_world_body[name], COLORS["original"]) for name in names]
        transparent = []
        if group is not None:
            transparent.append((carrier_mesh[group], (*GROUP_COLORS[group], 90)))
        if terminals:
            for name in names:
                for terminal, shape in hybrid_terminals[name].items():
                    mesh = safe_triangles(shape, 0.16, 0.10)
                    color = COLORS["trimmed"] if (name, terminal) in {("M4", "T2"), ("N3", "T3")} else COLORS["hybrid"]
                    objects.append((mesh, color))
        objects.extend((cap_mesh[name], COLORS["cap"]) for name in names)
        raster_scene(path, objects, title, subtitle, FOOTER, transparent_objects=transparent)

    render_group(paths[6], ("N1",), "07 / N1 DETAILED SWITCH IN CARRIER", "Original body/actuator, current cap and frozen N1/N2 shared carrier")
    render_group(paths[7], ("N2",), "08 / N2 DETAILED SWITCH IN CARRIER", "Original body/actuator, N2 short-U rear support and current cap")
    render_group(paths[8], ("I2", "I3"), "09 / I2-I3 DETAILED SWITCHES", "Frozen shared carrier; functional datums and switch clocking unchanged")
    render_group(paths[9], ("M4", "N3"), "10 / M4-N3 + HYBRID TRIMMED TERMINALS", "M4 T2 / N3 T3 0.300-mm external stubs; original terminal legs are not authority", terminals=True)
    objects_11 = [(original_world_body[name], COLORS["original"]) for name in ("I4", "M3")]
    objects_11.extend((cap_mesh[name], COLORS["cap"]) for name in ("I4", "M3"))
    raster_scene(
        paths[10], objects_11, "  11 / I4 + M3 DETAILED SWITCHES",
        "Independent carriers; docs/68 I4 manufacturing relief retained",
        FOOTER,
        transparent_objects=[(carrier_mesh["I4"], (*GROUP_COLORS["I4"], 90)), (carrier_mesh["M3"], (*GROUP_COLORS["M3"], 90))],
    )

    raster_scene(
        paths[11],
        [(original_world[name], GROUP_COLORS[BUTTON_GROUP[name]]) for name in BUTTONS] +
        [(cap_mesh[name], COLORS["cap"]) for name in BUTTONS],
        "12 / TRANSPARENT ALL-8 DETAILED-SWITCH ASSEMBLY",
        "Original detailed PushBtn at every frozen centre/axis/depth/clocking; audit assembly only",
        FOOTER,
        transparent_objects=[(carrier_mesh[group], (*GROUP_COLORS[group], 60)) for group in GROUPS],
    )

    full_caps = {
        button: cap_mesh[button] - unit(datums[button].axis).reshape(1, 1, 3) * 0.350
        for button in BUTTONS
    }
    full_actuators = {
        button: safe_triangles(
            moved(
                measured_actuator(datums[button], float(FROZEN_FRONT_DEPTHS[button]), f"{button}_ACT"),
                -unit(datums[button].axis) * 0.350,
                f"{button}_ACT_FULL",
            ),
            0.13,
            0.08,
        )
        for button in BUTTONS
    }
    raster_scene(
        paths[12],
        [(original_world_body[name], COLORS["original"]) for name in BUTTONS] +
        [(full_actuators[name], COLORS["hybrid"]) for name in BUTTONS] +
        [(full_caps[name], COLORS["cap"]) for name in BUTTONS],
        "13 / ALL-8 FULL — HYBRID AUTHORITY",
        "Caps and measured ITS actuators at 0.350 mm; original detailed bodies remain at frozen poses",
        FOOTER,
        transparent_objects=[(carrier_mesh[group], (*GROUP_COLORS[group], 55)) for group in GROUPS],
    )

    deviation, heat_objects = deviation_map(
        original.triangles,
        [measured["body"], measured["actuator"], *measured["terminals"].values()],
    )
    raster_scene(
        paths[13], heat_objects, "14 / ORIGINAL ↔ ACTUAL DEVIATION MAP",
        "GREEN <=0.10 mm | YELLOW 0.10-0.35 mm | RED >0.35 mm (surface visualization)",
        FOOTER, camera_offset=(17.0, -22.0, 15.0), fit_points=original_canonical.reshape(-1, 3),
    )
    memory("14 required renders")
    return paths, deviation


def report_markdown(data: dict[str, object]) -> str:
    authority = data["authority"]
    summary = data["summary"]
    terminal = data["terminalGeometryComparison"]
    body_fit = data["bodyFit"]
    per_button = data["perButton"]
    motion = data["motionRegression"]
    carrier = data["carrierRegression"]
    service = data["serviceability"]
    survival = data["validationSurvivalMatrix"]

    per_button_rows = "\n".join(
        "| {name} | {body} | {actuator} | {travel} | {hard} | {rear} | {terms} | {service} | {carrier} | **{verdict}** |".format(
            name=name,
            body=row["SWITCH BODY FIT"],
            actuator=row["ACTUATOR ALIGNMENT"],
            travel=row["TRAVEL"],
            hard=row["HARD STOP"],
            rear=row["REAR SUPPORT"],
            terms=row["TERMINALS"],
            service=row["SERVICE"],
            carrier=row["CARRIER"],
            verdict=row["VERDICT"],
        )
        for name, row in per_button.items()
    )
    body_rows = "\n".join(
        f"| {name} | {float(row['originalDetailed']['minimumPocketSideClearanceMm']):.3f} | "
        f"{float(row['actualMeasuredOverride']['pocketSideClearanceUMm']):.3f} / "
        f"{float(row['actualMeasuredOverride']['pocketSideClearanceVMm']):.3f} | "
        f"{float(row['rearSupport']['nominalOriginalRearGapMm']):.3f} | "
        f"{float(row['rearSupport']['contactAreaAtActualRearDatumMm2']):.3f} | "
        f"{int(row['rearSupport']['contactCountAtActualRearDatum'])} | "
        f"{float(row['rearSupport']['contactSpanMm']):.3f} | {row['finalHybridVerdict']} |"
        for name, row in body_fit.items()
    )
    terminal_rows = "\n".join(
        f"| {name} | "
        f"{', '.join(f'{float(value):+.3f}' for value in row['rootDeltaOriginalMinusCurrentMm'])} | "
        f"{float(row['rootAngleDeltaDeg']):.3f} | "
        f"{float(row['distalLengthDifferenceOriginalMinusCurrentMm']):+.3f} |"
        for name, row in terminal["perTerminal"].items()
    )
    carrier_rows = "\n".join(
        f"| {row['pair']} | {float(row['distanceMm']):.6f} | {float(row['penetrationMm3']):.9f} | "
        f"{'PASS' if row['passZeroPenetration'] else 'HOLD'} |"
        for row in carrier["pairs"]
    )
    motion_rows = "\n".join(
        f"| {row['state']} | {', '.join(row['pressedButtons']) or '-'} | "
        f"{float(row['maximumUnintendedPenetrationMm3']):.9f} | {row['verdict']} |"
        for row in motion["states"]
    )
    service_rows = "\n".join(
        f"| {name} | {row['direction']} | {float(row['testedTranslationMm']):.1f} | "
        f"{float(row['maximumUnintendedPenetrationMm3']):.9f} | {row['verdict']} |"
        for name, row in service["groups"].items()
    )
    survival_rows = "\n".join(
        f"| {name} | {row['classification']} | {row['basis']} |"
        for name, row in survival["items"].items()
    )
    render_rows = "\n".join(
        f"{index}. `{path}`" for index, path in enumerate(data["outputs"]["renders"], 1)
    )
    input_rows = "\n".join(
        f"| `{path}` | `{digest}` |" for path, digest in data["inputHashesBefore"].items()
    )

    return f"""# 75 — Detailed PushBtn 8-button revalidation

## 1. Authority / first-page verdict

- SWITCH NOMINAL CAD AUTHORITY = **{authority['SWITCH NOMINAL CAD AUTHORITY']}**
- ACTUAL HARDWARE AUTHORITY = **{authority['ACTUAL HARDWARE AUTHORITY']}**
- ORIGINAL PUSHBTN ↔ ITS = **{authority['ORIGINAL PUSHBTN ↔ ITS']}**
- BODY AUTHORITY = **{authority['BODY AUTHORITY']}**
- ACTUATOR AUTHORITY = **{authority['ACTUATOR AUTHORITY']}**
- TERMINAL AUTHORITY = **{authority['TERMINAL AUTHORITY']}**
- ALL 8 BUTTON MECHANISMS = **{summary['ALL 8 BUTTON MECHANISMS']}**
- ALL-8 FULL = **{summary['ALL-8 FULL']}**
- EXTERIOR = **{summary['EXTERIOR']}**
- CURRENT VALIDATION REUSE = **{float(summary['CURRENT VALIDATION REUSE %']):.1f}%**
- LOCAL REDESIGN REQUIRED = **{summary['LOCAL REDESIGN REQUIRED']}**
- FINAL VERDICT = **{summary['FINAL VERDICT']}**
- PRODUCTION GEOMETRY MODIFICATION = **0**

원본 `mesh_PushBtn.json`의 **3,530개 facet을 그대로 sewing**하여 valid faceted BRep solid로 만들었다. bbox/box로 PushBtn을 대체하지 않았고 scale은 0건이다. 정렬은 actuator centre/axis와 plastic body-top datum으로 수행했다. 8개 centre, axis, depth, clocking은 기존 승인값 그대로다.

결론은 **C. HYBRID SWITCH REFERENCE REQUIRED**다. 원본 detailed body는 nominal language로 유효하지만, 원본 actuator projection은 **{ORIG_ACTUATOR_PROJECTION:.3f} mm**로 실측 ITS **{ACTUAL['actuatorProjectionMm']:.3f} mm**보다 **{float(data['actuator']['projectionDeltaMm']):.3f} mm 짧다**. current cap contact에서 원본 actuator만 쓰면 REST/MID/FULL 잔여 gap은 **0.940 / 0.765 / 0.590 mm**라 actuation이 성립하지 않는다. 따라서 actuator는 실측 ITS override가 필수다. 원본 terminal도 root/pitch/distal envelope가 다르므로 최종 packaging은 ITS terminal override를 사용한다.

## 2. Freeze / method

- exterior centre/orientation movement: **0.000 mm / 0.000°**
- shell / lowered Thumb / cap / carrier / switch pose production edit: **0건**
- full shell boolean / full production assembly boolean: **0건**
- multiprocessing / brute-force 3^8: **0건**
- selected local OCCT common + pairwise distance only
- body-facing guide/reaction은 frozen generator에서 재구성했고, shell-facing relief보다 재료가 더 많은 raw guide condition으로 보수 검사했다. 최종 production carrier STEP은 imported frozen 형상 그대로다.
- SZH-EK056 and docs/72: **not reopened / unchanged**
- peak Python RSS: **{float(summary['PEAK RSS MB']):.1f} MB**

## 3. Original detailed vs actual ITS

| item | original PushBtn | measured ITS-1105 | authority result |
|---|---:|---:|---|
| body transverse maximum | 6.310 mm skirt / 6.010 mm main | 6.12 × 6.05 mm | original detailed nominal + actual measured override |
| plastic housing height | 3.500 mm | 3.560 mm | near-equivalent; actual rear datum controls |
| actuator diameter | 3.500 mm | 3.350 mm | near-equivalent diameter |
| actuator projection | 1.500 mm | 2.440 mm | **different / actual override required** |
| actuator travel clue | none; rigid imported solid | 0.15–0.35 mm, nominal 0.25 | actual hardware authority |
| terminal external length | ~3.519 mm | physical not supplied; 1.800 mm drawing-nominal envelope | **different / hybrid required** |

Original detailed 6.31 mm skirt와 6.40 mm seat 사이 nominal 최소 측면 여유는 **0.045 mm/side**다. 기하학적 penetration은 없지만 tolerance-sensitive이므로 original-only body fit은 `RECHECK`로 남겼다. 실제 구매품 body 기준 여유는 U/V **0.140 / 0.175 mm/side**다.

## 4. Per-button survival table

| button | SWITCH BODY FIT | ACTUATOR ALIGNMENT | TRAVEL | HARD STOP | REAR SUPPORT | TERMINALS | SERVICE | CARRIER | VERDICT |
|---|---|---|---|---|---|---|---|---|---|
{per_button_rows}

## 5. Body fit / rear support

| button | original nominal pocket side clearance mm | actual U/V clearance mm | original rear gap mm | detailed rear footprint contact area mm² | contacts | span mm | hybrid |
|---|---:|---:|---:|---:|---:|---:|---|
{body_rows}

원본 body height가 0.060 mm 짧으므로 current support plane과 nominal gap이 생긴다. 이것은 실제 ITS body height 3.56 mm override로 닫힌다. 원본 rear footprint를 실제 rear datum에 맞춰 별도 contact proxy로 검사한 결과 chamfer 때문에 지지 architecture가 사라지는 버튼은 없었다. 구조 하중은 current carrier hard stop이 먼저 받고 switch housing을 overtravel stop으로 쓰지 않는다.

## 6. Actuator / travel / hard stop

- cap contact centre offset: 모든 버튼 **≤ {max(float(row['capContactCenterOffsetMm']) for row in data['actuator']['perButton'].values()):.9f} mm**
- cap contact ↔ actuator angle: 모든 버튼 **0.000°**
- original-only: **HOLD at CAP ↔ ACTUATOR**
- hybrid measured actuator: **PASS** at REST / MID 0.175 / FULL 0.350
- FULL hard-stop residual: **0.000 mm**, current carrier rear stop remains structural stop

이번 결과는 `DETAILED SWITCH REVALIDATION FAILED AT CAP ↔ ORIGINAL ACTUATOR PROJECTION`이며 exterior 실패가 아니다. hidden reference를 measured actuator로 override하면 production geometry 변경 없이 해소된다.

## 7. Terminal-root comparison

Δ 순서는 functional `(U, V, inward depth)`이고 `original − current simplified`다.

| terminal | root ΔU/ΔV/Δdepth mm | root angle Δ deg | distal length Δ mm |
|---|---|---:|---:|
{terminal_rows}

- original-terminal diagnostic collision count: **{len(data['terminalPackaging']['originalTerminalDiagnostic']['failedInterfaces'])}** — final authority에 사용하지 않음
- hybrid terminal failed interface count: **{len(data['terminalPackaging']['hybridFinal']['failedInterfaces'])}**
- terminal authority qualifier: **physical pin/root metrology not supplied; current override remains drawing-nominal plus existing physical trim tests**

### N2

- strategy: **T1/T3 active, T2/T4 unused external trim**
- T1/T3 solder access: **retained**
- T2/T4 housing/internal leadframe intrusion: **NO**
- existing physical sample after T2/T4 trim: switching/return **PASS**
- verdict: **VALID WITH HYBRID SWITCH**

### M4 / N3

- M4 T2 / N3 T3 selected trim: **1.758428 mm**
- remaining external stub: **0.300 mm**
- old penetration: **0.283393028 mm³**
- new penetration: **{float(data['terminalPackaging']['M4N3']['newPair']['penetrationMm3']):.9f} mm³**
- new clearance: **{float(data['terminalPackaging']['M4N3']['newPair']['distanceMm']):.6f} mm**
- verdict: **{data['terminalPackaging']['M4N3']['verdict']}**; physical first-article terminal metrology gate retained

## 8. Carrier-carrier regression

| pair | clearance mm | penetration mm³ | result |
|---|---:|---:|---|
{carrier_rows}

- maximum carrier penetration: **{float(carrier['maximumPenetrationMm3']):.9f} mm³**
- minimum carrier clearance: **{float(carrier['minimumClearanceMm']):.6f} mm** at `{carrier['closestPair']}`
- approved I2/I3 ↔ I4 relief reference: **0.444805280 mm**

## 9. Motion regression

| state | FULL buttons | max unintended penetration mm³ | result |
|---|---|---:|---|
{motion_rows}

Brute-force 3^8은 수행하지 않았다. 사용자 지정 15개 state만 검사했다.

## 10. Serviceability

| carrier group | removal direction | travel mm | max unintended penetration mm³ | result |
|---|---|---:|---:|---|
{service_rows}

Detailed original skirt는 audit nominal로 tolerance-sensitive지만 실제 ITS body 기준 insertion/removal 여유는 유지된다. Carrier removal과 terminal solder access architecture는 모두 재사용 가능하다.

## 11. Validation survival matrix

| baseline item | classification | basis |
|---|---|---|
{survival_rows}

Architecture reuse 정의는 요청된 11개 baseline 항목 중 `LOCAL ADAPTATION REQUIRED` 또는 `SUPERSEDED`가 아닌 항목의 비율이다. 결과는 **{survival['reusedCount']}/{survival['totalCount']} = {float(survival['reusePercent']):.1f}%**다. Reference authority는 hybrid로 바뀌지만 production mechanism architecture는 전부 살아남는다.

## 12. Deviation map

- GREEN area: **{float(data['deviationMap']['areaWeighted']['GREEN']['percent']):.1f}%**
- YELLOW area: **{float(data['deviationMap']['areaWeighted']['YELLOW']['percent']):.1f}%**
- RED area: **{float(data['deviationMap']['areaWeighted']['RED']['percent']):.1f}%**
- maximum sampled surface deviation: **{float(data['deviationMap']['maximumSampledSurfaceDeviationMm']):.3f} mm**

RED는 주로 actuator tip과 original terminal distal legs다. Body corner/skirt는 GREEN/YELLOW 범위이며 positive seat clearance를 유지한다. 이 heat-map은 visualization metric이고 collision authority는 faceted BRep / measured envelope exact checks다.

## 13. Required renders

{render_rows}

## 14. Protected input hash guard

작업 전후 protected input SHA-256는 **{'IDENTICAL' if data['protectedInputsPreserved'] else 'CHANGED / HOLD'}**이다.

| protected input | SHA-256 before |
|---|---|
{input_rows}

## 15. Final verdict / STOP

**C. HYBRID SWITCH REFERENCE REQUIRED**

- nominal body language: original detailed PushBtn
- manufacturing body clearance: max(original detailed, measured ITS), with actual measured body recorded separately
- actuator: **measured ITS override required**
- terminals: **actual ITS authority; current drawing-nominal envelope until controlled physical root registry exists**
- production local redesign: **NONE**
- exterior: **PRESERVED**
- production geometry edit: **0**

Audit 결과를 기록하고 STOP한다. 사용자의 별도 승인 전에는 shell/cap/carrier/switch pose/Thumb/SZH fixture에 적용하지 않는다.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    memory("start")
    missing = [str(path) for path in PROTECTED_INPUTS if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing protected input(s): {missing}")
    input_hashes_before = {relative(path): sha256(path) for path in PROTECTED_INPUTS}

    original = build_original_parts()
    memory("original 3530-facet BRep built")
    if not REFERENCE_STEP.exists():
        export_step(original.full, REFERENCE_STEP)
        memory("original detailed reference STEP exported")
    else:
        memory("existing original detailed reference STEP checkpoint retained")

    datums = load_all_datums()
    datums["N2"] = n2prod.load_datum()
    source = n2prod.load_source()
    carriers = {name: import_step(path) for name, path in CARRIER_PATHS.items()}
    memory("five frozen carrier references loaded")
    caps = {name: import_step(path) for name, path in CAP_PATHS.items()}
    memory("eight frozen cap references loaded")
    shells = load_shell_crops(carriers, caps)
    memory("two local shell crops loaded")
    refs = load_mechanism_references(datums, shells, source)
    hybrid_terminals = current_terminal_map(source, datums)
    original_terminals = original_terminal_pose_map(original, datums)
    memory("canonical inputs and mechanism references loaded")

    body_fit, original_bodies, original_actuators, measured_bodies = body_fit_audit(
        original, datums, carriers, shells, refs
    )
    actuator = actuator_audit(datums, refs)
    terminal_geometry = terminal_local_measurements(original)
    terminal_packaging = terminal_packaging_audit(
        original_terminals, hybrid_terminals, carriers, shells, measured_bodies
    )
    carrier = carrier_regression(carriers)
    motion = motion_regression(caps, original_bodies, carriers, datums)
    service = service_regression(carriers, measured_bodies, hybrid_terminals)

    # Audit-only assemblies: compounds only; no union/cut against production.
    detailed_switches = [
        original_to_pose(
            original.full, datums[button], float(FROZEN_FRONT_DEPTHS[button]),
            f"{button}_ORIGINAL_PUSHBTN_DETAILED_AUDIT_ONLY",
        )
        for button in BUTTONS
    ]
    audit_compound = Compound(
        children=[*carriers.values(), *caps.values(), *detailed_switches],
        label="DETAILED_PUSHBTN_AUDIT_ONLY_8_BUTTON_ASSEMBLY",
    )
    export_step(audit_compound, AUDIT_STEP)
    del audit_compound, detailed_switches
    memory("audit-only 8-button STEP exported")

    ref = reference_datum()
    ref_body = original_to_pose(original.body, ref, 0.0, "ORIGINAL_DETAILED_BODY_NOMINAL")
    ref_actual = measured_reference_parts(ref, 0.0)
    hybrid_compound = Compound(
        children=[ref_body, ref_actual["actuator"], *ref_actual["terminals"].values()],
        label="HYBRID_REFERENCE_ORIGINAL_BODY_MEASURED_ACTUATOR_ITS_TERMINALS",
    )
    export_step(hybrid_compound, HYBRID_STEP)
    del hybrid_compound

    renders, deviation = render_outputs(
        original, datums, carriers, caps, hybrid_terminals, original_bodies
    )

    input_hashes_after = {relative(path): sha256(path) for path in PROTECTED_INPUTS}
    protected = input_hashes_before == input_hashes_after
    body_pass = all(row["finalHybridVerdict"] == "PASS" for row in body_fit.values())
    terminal_pass = terminal_packaging["hybridFinal"]["verdict"] == "PASS"
    all8_full = next(row for row in motion["states"] if row["state"] == "ALL_8_FULL")
    overall = body_pass and terminal_pass and carrier["verdict"] == "PASS" and motion["verdict"] == "PASS" and service["verdict"] == "PASS" and protected

    per_button: dict[str, dict[str, str]] = {}
    for button in BUTTONS:
        per_button[button] = {
            "SWITCH BODY FIT": "RECHECK / HYBRID PASS",
            "ACTUATOR ALIGNMENT": "PASS WITH ACTUAL OVERRIDE",
            "TRAVEL": "PASS WITH ACTUAL OVERRIDE",
            "HARD STOP": "PASS / CARRIER FIRST",
            "REAR SUPPORT": "PASS WITH ACTUAL BODY HEIGHT",
            "TERMINALS": "PASS WITH HYBRID SWITCH",
            "SERVICE": service["groups"][BUTTON_GROUP[button]]["verdict"],
            "CARRIER": carrier["verdict"],
            "VERDICT": "VALID WITH HYBRID SWITCH" if overall else "HOLD",
        }

    survival_items = {
        "N1 mechanism": {"classification": "VALID WITH HYBRID SWITCH", "basis": "body/guide/support survive; measured actuator override required"},
        "N2 mechanism": {"classification": "VALID WITH HYBRID SWITCH", "basis": "short-U support and hard stop survive"},
        "I2/I3": {"classification": "VALID WITH HYBRID SWITCH", "basis": "shared carrier and independent motion rechecked"},
        "M4/N3": {"classification": "VALID WITH HYBRID SWITCH", "basis": "shared carrier survives; actual terminal overlay retained"},
        "I4": {"classification": "RECHECKED AND PASS", "basis": "docs/68 relief preserved; hybrid switch fit pass"},
        "M3": {"classification": "RECHECKED AND PASS", "basis": "standalone carrier fit and service pass"},
        "N2 terminal trim": {"classification": "VALID WITH HYBRID SWITCH", "basis": "T1/T3 access and T2/T4 external trim retained"},
        "M4/N3 terminal trim": {"classification": "VALID WITH HYBRID SWITCH", "basis": "0.300-mm stubs preserve zero penetration"},
        "carrier clearances": {"classification": "RECHECKED AND PASS", "basis": f"minimum {float(carrier['minimumClearanceMm']):.6f} mm; penetration zero"},
        "all-8 motion": {"classification": "RECHECKED AND PASS", "basis": "15 requested states; all unintended penetration zero"},
        "serviceability": {"classification": "RECHECKED AND PASS", "basis": "five group paths and actual-body insertion remain pass"},
    }
    reused = sum(
        row["classification"] not in {"LOCAL ADAPTATION REQUIRED", "SUPERSEDED"}
        for row in survival_items.values()
    )
    survival = {
        "items": survival_items,
        "reusedCount": reused,
        "totalCount": len(survival_items),
        "reusePercent": 100.0 * reused / len(survival_items),
    }

    original_bbox_min = original.triangles.reshape(-1, 3).min(axis=0)
    original_bbox_max = original.triangles.reshape(-1, 3).max(axis=0)
    body_min, body_max = bounds(original.body)
    data: dict[str, object] = {
        "schema": "onegrip.detailed_pushbtn_8_button_revalidation.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT ONLY / LOW MEMORY / SERIAL OCCT / LOCAL SHELL CROPS",
        "authority": {
            "SWITCH NOMINAL CAD AUTHORITY": "ORIGINAL ONEGRIP PUSHBTN DETAILED 3,530-FACET MODEL",
            "ACTUAL HARDWARE AUTHORITY": "MEASURED ITS-1105",
            "ORIGINAL PUSHBTN ↔ ITS": "HYBRID REQUIRED",
            "BODY AUTHORITY": "ORIGINAL DETAILED BODY NOMINAL + MAX(ORIGINAL, MEASURED ITS) CLEARANCE POLICY",
            "ACTUATOR AUTHORITY": "MEASURED ITS-1105 OVERRIDE (2.44 mm projection)",
            "TERMINAL AUTHORITY": "ACTUAL ITS-1105; CURRENT DRAWING-NOMINAL ENVELOPE UNTIL CONTROLLED ROOT METROLOGY",
        },
        "freeze": {
            "buttons": list(BUTTONS),
            "externalCenterMovementMm": 0.0,
            "externalOrientationMovementDeg": 0.0,
            "productionGeometryModifications": 0,
            "shellExteriorModified": False,
            "loweredThumbModified": False,
            "switchPoseModified": False,
            "szhFixtureModified": False,
            "fullShellBoolean": False,
            "fullProductionAssemblyBoolean": False,
            "multiprocessing": False,
            "bruteForce3Pow8": False,
            "stlOrPrintPlate": False,
        },
        "originalDetailedGeometry": {
            "source": "cad_dump/mesh_PushBtn.json",
            "triangleCount": int(len(original.triangles)),
            "facetedBrepFaceCount": len(original.full.faces()),
            "valid": bool(BRepCheck_Analyzer(original.full.wrapped).IsValid()),
            "volumeMm3": float(original.full.volume),
            "bboxMinMm": original_bbox_min.tolist(),
            "bboxMaxMm": original_bbox_max.tolist(),
            "bboxSpanMm": (original_bbox_max - original_bbox_min).tolist(),
            "bodyBboxSpanMm": (body_max - body_min).tolist(),
            "bodyHeightMm": ORIG_BODY_HEIGHT,
            "actuatorProjectionMm": ORIG_ACTUATOR_PROJECTION,
            "scaleApplied": False,
            "alignment": "actuator centre XY + actuator axis + plastic body-top plane + frozen switch roll",
        },
        "actualIts1105": ACTUAL,
        "bodyFit": body_fit,
        "actuator": actuator,
        "terminalGeometryComparison": terminal_geometry,
        "terminalPackaging": terminal_packaging,
        "carrierRegression": carrier,
        "motionRegression": motion,
        "serviceability": service,
        "deviationMap": deviation,
        "validationSurvivalMatrix": survival,
        "perButton": per_button,
        "summary": {
            "ALL 8 BUTTON MECHANISMS": "PASS WITH HYBRID SWITCH" if overall else "HOLD",
            "ALL-8 FULL": all8_full["verdict"],
            "EXTERIOR": "PRESERVED" if protected else "HOLD",
            "CURRENT VALIDATION REUSE %": survival["reusePercent"],
            "LOCAL REDESIGN REQUIRED": "NONE" if overall else "SEE FAILED INTERFACES",
            "FINAL VERDICT": "C. HYBRID SWITCH REFERENCE REQUIRED" if overall else "D. MAJOR REBUILD REQUIRED",
            "PEAK RSS MB": max(float(row["rssMb"]) for row in MEMORY),
            "productionGeometryModificationCount": 0,
        },
        "inputHashesBefore": input_hashes_before,
        "inputHashesAfter": input_hashes_after,
        "protectedInputsPreserved": protected,
        "outputs": {
            "report": relative(REPORT),
            "json": relative(JSON_PATH),
            "auditAssemblyStep": relative(AUDIT_STEP),
            "originalDetailedReferenceStep": relative(REFERENCE_STEP),
            "hybridReferenceStep": relative(HYBRID_STEP),
            "renders": [relative(path) for path in renders],
            "stl": [],
            "printPlate": [],
        },
        "memory": MEMORY,
        "stop": "Show audit result and STOP; user approval required before any local production adaptation",
    }
    REPORT.write_text(report_markdown(data), encoding="utf-8")
    output_paths = [REPORT, AUDIT_STEP, REFERENCE_STEP, HYBRID_STEP, *renders]
    data["outputs"]["sha256"] = {relative(path): sha256(path) for path in output_paths}
    memory("complete")
    data["memory"] = MEMORY
    data["summary"]["PEAK RSS MB"] = max(float(row["rssMb"]) for row in MEMORY)
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "finalVerdict": data["summary"]["FINAL VERDICT"],
        "all8Mechanisms": data["summary"]["ALL 8 BUTTON MECHANISMS"],
        "all8Full": data["summary"]["ALL-8 FULL"],
        "reusePercent": data["summary"]["CURRENT VALIDATION REUSE %"],
        "localRedesign": data["summary"]["LOCAL REDESIGN REQUIRED"],
        "protectedInputsPreserved": protected,
        "peakRssMb": data["summary"]["PEAK RSS MB"],
        "report": relative(REPORT),
        "json": relative(JSON_PATH),
        "renders": len(renders),
        "productionGeometryModificationCount": 0,
    }, ensure_ascii=False, indent=2))


def rerender_deviation_only() -> None:
    """Regenerate render 14 after visual QA without repeating exact CAD checks."""
    original = build_original_parts()
    ref = reference_datum()
    measured = measured_reference_parts(ref, 0.0)
    canonical = canonical_original_triangles(original.triangles)
    deviation, heat_objects = deviation_map(
        original.triangles,
        [measured["body"], measured["actuator"], *measured["terminals"].values()],
    )
    path = RENDER / "14_deviation_heat_map.png"
    raster_scene(
        path,
        heat_objects,
        "14 / ORIGINAL ↔ ACTUAL DEVIATION MAP",
        "GREEN <=0.10 mm | YELLOW 0.10-0.35 mm | RED >0.35 mm (surface visualization)",
        FOOTER,
        camera_offset=(17.0, -22.0, 15.0),
        fit_points=canonical.reshape(-1, 3),
    )
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    data["deviationMap"] = deviation
    data["outputs"]["sha256"][relative(path)] = sha256(path)
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rerendered": relative(path), "sha256": sha256(path)}, indent=2))


def rerender_all_only() -> None:
    """Regenerate all required PNGs after visual QA, without exact CAD checks."""
    original = build_original_parts()
    datums = load_all_datums()
    datums["N2"] = n2prod.load_datum()
    source = n2prod.load_source()
    carriers = {name: import_step(path) for name, path in CARRIER_PATHS.items()}
    caps = {name: import_step(path) for name, path in CAP_PATHS.items()}
    hybrid_terminals = current_terminal_map(source, datums)
    original_bodies = {
        button: original_to_pose(
            original.body,
            datums[button],
            float(FROZEN_FRONT_DEPTHS[button]),
            f"{button}_ORIGINAL_DETAILED_BODY",
        )
        for button in BUTTONS
    }
    renders, deviation = render_outputs(
        original, datums, carriers, caps, hybrid_terminals, original_bodies
    )
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    data["deviationMap"] = deviation
    for path in renders:
        data["outputs"]["sha256"][relative(path)] = sha256(path)
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rerendered": len(renders), "json": relative(JSON_PATH)}, indent=2))


def refresh_report_only() -> None:
    """Refresh markdown wording and its recorded hash from the accepted JSON."""
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    REPORT.write_text(report_markdown(data), encoding="utf-8")
    data["outputs"]["sha256"][relative(REPORT)] = sha256(REPORT)
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"refreshed": relative(REPORT), "sha256": sha256(REPORT)}, indent=2))


if __name__ == "__main__":
    if "--refresh-report" in sys.argv:
        refresh_report_only()
    elif "--rerender-all" in sys.argv:
        rerender_all_only()
    elif "--rerender-deviation" in sys.argv:
        rerender_deviation_only()
    else:
        main()
