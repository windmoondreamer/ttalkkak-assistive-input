"""Source-faithful button mechanism + FDM rebase audit.

AUDIT ONLY.  This script reads frozen source/reference geometry and creates a
new representative mechanism, JSON, report, and 14 review renders.  It never
edits a production shell, carrier, cap, pusher, switch pose, or Thumb part.

The original PushBtn tessellation is retained as the detailed nominal source.
The audit candidate deliberately contains explicit UNKNOWN keep-outs for the
actual ITS corner features; those values are not promoted to hardware truth.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from build123d import (
    Align, Box, Compound, Cylinder, Location, Plane, Shape, Vector,
    export_step, import_step,
)
from scipy.spatial import cKDTree

from .detailed_pushbtn_8_button_revalidation import (
    ACTUAL, BUTTONS, build_original_parts, canonical_original_triangles,
)
from .finger_controls_v2 import FROZEN_FRONT_DEPTHS
from .i4_m3_current_audit import load_all_datums
from .option_c_local_exact_prototype import raster_scene, safe_edge_lines, safe_triangles


ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "cad_dump"
OUT = ROOT / "build123d_workbench/out/source_faithful_button_mechanism_fdm_rebase_audit"
RENDER = ROOT / "renders/source_faithful_button_mechanism_fdm_rebase_audit"
REPORT = ROOT / "docs/76_source_faithful_button_mechanism_and_fdm_rebase_audit.md"
JSON_PATH = OUT / "source_faithful_button_mechanism_and_fdm_rebase_audit.json"
STEP_PATH = OUT / "SOURCE_FAITHFUL_BUTTON_MECHANISM_AUDIT_ONLY.step"

ORIGINAL_POCKET = {
    "sourceExpression": "#button_module_width + #button_tolerance*2",
    "moduleWidthMm": 6.0,
    "tolerancePerSideMm": 0.2,
    "pocketUmm": 6.4,
    "pocketVmm": 6.4,
    "supportThicknessMm": 4.0,
    "occupiedBodyDepthMm": 3.5,
    "seatingDatum": "PushBtn plastic main-body bottom plane, source local Y=0",
    "insertion": "rear/interior insertion through the Backplate support; terminals exit rearward",
}

# One reviewable, deliberately non-production candidate.  The 7.10 cavity is
# a clearance envelope.  Three small datum pads, not all four walls, perform
# location.  Actual lug dimensions remain an explicit first-article gate.
CAND = {
    "bodyUmm": 6.12,
    "bodyVmm": 6.05,
    "bodyHmm": 3.56,
    "cavityUmm": 7.10,
    "cavityVmm": 7.10,
    "locatorPadProtrusionMm": 0.25,
    "locatorPadWidthMm": 1.20,
    "cornerKeepoutDiameterMm": 1.40,
    "cornerKeepoutDepthMm": 0.80,
    "pusherDiameterMm": 2.60,
    "initialGapMm": 0.08,
    "switchNominalTravelMm": 0.25,
    "switchUpperObservedMm": 0.35,
    "candidateActuatorCompressionAtStopMm": 0.30,
    "capTravelToClickMm": 0.33,
    "capTravelToHardStopMm": 0.38,
    "radialCenteringMarginMm": (3.35 - 2.60) / 2.0,
}

FDM = {
    "machine": "Bambu Lab P1S / 0.4 mm nozzle / uncalibrated conservative audit model",
    "xyDimensionalMm": [-0.15, 0.15],
    "zLayerQuantizationMm": [-0.10, 0.10],
    "smallPocketShrinkPerSideMm": [0.00, 0.10],
    "elephantFootPerSideMm": [0.00, 0.15],
    "slopedStairStepMm": [0.00, 0.20],
    "bridgeOverhangSagMm": [0.00, 0.20],
    "supportScarMm": [0.00, 0.15],
    "warpageMm": [-0.20, 0.20],
    "shellHalfTranslationEachGlobalAxisMm": [-0.20, 0.20],
    "shellHalfRotationDeg": [-0.50, 0.50],
    "switchDatumUnknownMm": [-0.15, 0.15],
    "pusherLengthMm": [-0.20, 0.20],
    "capStackMm": [-0.10, 0.10],
}

PROTECTED = [
    ROOT / "cad_dump/mesh_PushBtn.json",
    ROOT / "cad_dump/features_Joystick.json",
    ROOT / "cad_dump/asmdef_Joystick.json",
    ROOT / "cad_dump/mesh_Backplate.json",
    ROOT / "cad_dump/mesh_Joystick_1.json",
    ROOT / "cad_dump/mesh_Joystick_2.json",
    ROOT / "cad_dump/mesh_ITS_LIVE_JaD.json",
    ROOT / "cad_dump/mesh_ITS_LIVE_JfD.json",
    ROOT / "build123d_workbench/finger_controls_v2.py",
    ROOT / "build123d_workbench/n1_production_intent_mechanism.py",
    ROOT / "build123d_workbench/n2_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i2_i3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/i4_m3_production_intent_mechanisms.py",
    ROOT / "build123d_workbench/m4_n3_production_intent_mechanism.py",
    ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JAD_EXTERIOR_LOWERED_THUMB_V1.step",
    ROOT / "build123d_workbench/out/integrated_exterior_lowered_thumb_v1/JFD_EXTERIOR_LOWERED_THUMB_V1.step",
    ROOT / "build123d_workbench/out/original_thumb_module_reuse_audit/LOWERED_ORIGINAL_THUMB_CARTRIDGE.step",
]

C = {
    "original": (69, 169, 229), "actual": (233, 91, 99),
    "pocket": (146, 100, 205), "candidate": (61, 200, 142),
    "cap": (242, 190, 64), "shell": (116, 132, 150),
    "housing": (142, 205, 166), "unknown": (247, 135, 54),
    "stop": (232, 88, 88), "axis": (47, 183, 220),
}
FOOT = "AUDIT ONLY | EXTERIOR + JaD/JfD SPLIT PRESERVED | PRODUCTION MODIFICATION = 0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def load_mesh(name: str) -> np.ndarray:
    return np.asarray(json.loads((DUMP / f"mesh_{name}.json").read_text(encoding="utf-8"))["tris"], float)


def occurrences() -> dict[str, np.ndarray]:
    asm = json.loads((DUMP / "asmdef_Joystick.json").read_text(encoding="utf-8"))
    root = asm["rootAssembly"]
    names = {row["id"]: row["name"] for row in root["instances"]}
    out: dict[str, np.ndarray] = {}
    for row in root["occurrences"]:
        if len(row["path"]) != 1:
            continue
        matrix = np.asarray(row["transform"], float).reshape(4, 4).copy()
        matrix[:3, 3] *= 1000.0
        out[names[row["path"][0]]] = matrix
    return out


def xf_to_local(triangles: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    points = triangles.reshape(-1, 3)
    local = (points - matrix[:3, 3]) @ matrix[:3, :3]
    return local.reshape(triangles.shape)


def transform_triangles(triangles: np.ndarray, matrix: np.ndarray, offset=(0.0, 0.0, 0.0)) -> np.ndarray:
    points = triangles.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
    return (points + np.asarray(offset, float)).reshape(triangles.shape)


def clip_box(triangles: np.ndarray, lower: Iterable[float], upper: Iterable[float]) -> np.ndarray:
    lo, hi = np.asarray(tuple(lower), float), np.asarray(tuple(upper), float)
    return triangles[(((triangles >= lo) & (triangles <= hi)).all(axis=2)).all(axis=1)]


def clip_half(triangles: np.ndarray, axis: int, value: float, below=True) -> np.ndarray:
    values = triangles[:, :, axis]
    return triangles[(values <= value).all(axis=1)] if below else triangles[(values >= value).all(axis=1)]


def shifted(triangles: np.ndarray, offset: Iterable[float]) -> np.ndarray:
    return triangles + np.asarray(tuple(offset), float)


def tri_area(triangles: np.ndarray) -> np.ndarray:
    return np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) / 2.0


def extract_corner_lugs(triangles: np.ndarray) -> list[dict[str, object]]:
    top = triangles[np.all(np.isclose(triangles[:, :, 1], 3.5, atol=2.0e-5), axis=1)]
    # Connectivity by quantized shared vertices on the four top disks.
    vertex_map: dict[tuple[int, int, int], list[int]] = {}
    for i, tri in enumerate(top):
        for p in tri:
            vertex_map.setdefault(tuple(np.round(p * 1.0e5).astype(int)), []).append(i)
    adj = [set() for _ in range(len(top))]
    for owners in vertex_map.values():
        for i in owners:
            adj[i].update(owners)
    unseen = set(range(len(top)))
    comps: list[np.ndarray] = []
    while unseen:
        stack = [unseen.pop()]
        seen = set(stack)
        while stack:
            i = stack.pop()
            for j in adj[i]:
                if j in unseen:
                    unseen.remove(j); seen.add(j); stack.append(j)
        comp = top[sorted(seen)]
        if len(comp) > 20:
            comps.append(comp)
    rows = []
    for comp in sorted(comps, key=lambda t: tuple(t.reshape(-1, 3).mean(axis=0)[[0, 2]])):
        v = comp.reshape(-1, 3)
        center = v.mean(axis=0)
        # Side triangles belonging to this post establish base/top and diameter.
        allc = triangles.mean(axis=1)
        radial = np.hypot(allc[:, 0] - center[0], allc[:, 2] - center[2])
        side = triangles[(radial < 0.65) & (allc[:, 1] >= 2.9999) & (allc[:, 1] <= 3.5001)]
        sv = side.reshape(-1, 3)
        rows.append({
            "centerSourceXZmm": [float(center[0]), float(center[2])],
            "centerFunctionalUVmm": [float(center[0]), float(-center[2])],
            "topTriangleCount": int(len(comp)),
            "topAreaMm2": float(tri_area(comp).sum()),
            "widthXmm": float(v[:, 0].max() - v[:, 0].min()),
            "lengthZmm": float(v[:, 2].max() - v[:, 2].min()),
            "baseSourceYmm": float(sv[:, 1].min()),
            "topSourceYmm": float(sv[:, 1].max()),
            "heightMm": float(sv[:, 1].max() - sv[:, 1].min()),
            "nominalInterpretation": "D1.000 x 0.500 cylindrical housing post",
        })
    return rows


def local_axis_cylinder(origin: Iterable[float], axis: Iterable[float], length: float, diameter: float, label: str) -> Shape:
    a = np.asarray(tuple(axis), float); a /= np.linalg.norm(a)
    plane = Plane(origin=tuple(origin), z_dir=tuple(a))
    shape = plane.location * Cylinder(diameter / 2.0, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    shape.label = label
    return shape


def local_candidate() -> dict[str, Shape]:
    """Build a representative local U/V/W candidate, W=+Z outward."""
    cavity_u, cavity_v = CAND["cavityUmm"], CAND["cavityVmm"]
    wall = 1.20
    outer_u, outer_v = cavity_u + 2 * wall, cavity_v + 2 * wall
    base = Box(outer_u, outer_v, 0.80, align=(Align.CENTER, Align.CENTER, Align.MAX))
    outer = Box(outer_u, outer_v, 4.35, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cavity = Box(cavity_u, cavity_v, 4.55, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, -0.10)))
    pocket = (base.fuse(outer) - cavity).clean()
    # Four rear terminal exits; large/open and outside the three datum pads.
    for sx in (-1, 1):
        for sy in (-1, 1):
            tool = Box(1.20, 1.40, 1.20, align=(Align.CENTER, Align.CENTER, Align.CENTER)).moved(
                Location(Vector(sx * 2.25, sy * 2.25, -0.35)))
            pocket = pocket - tool
    pocket = pocket.clean(); pocket.label = "AUDIT_POCKET_7P10_CLEARANCE_WITH_REAR_SEAT"

    # Three-point deterministic location: two pads on -U, one on -V.
    pad_t, pad_w = CAND["locatorPadProtrusionMm"], CAND["locatorPadWidthMm"]
    pads = []
    for v in (-1.75, 1.75):
        pads.append(Box(pad_t, pad_w, 2.4, align=(Align.MIN, Align.CENTER, Align.MIN)).moved(
            Location(Vector(-cavity_u / 2, v, 0.25))))
    pads.append(Box(pad_w, pad_t, 2.4, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(
        Location(Vector(0, -cavity_v / 2, 0.25))))
    locator = pads[0].fuse(pads[1]).fuse(pads[2]).clean(); locator.label = "THREE_POINT_TUNABLE_LOCATOR_PADS"

    body = Box(CAND["bodyUmm"], CAND["bodyVmm"], CAND["bodyHmm"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    body.label = "ACTUAL_ITS_MEASURED_BODY_ENVELOPE"
    actuator = Cylinder(3.35 / 2, 2.44, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
        Location(Vector(0, 0, CAND["bodyHmm"])))
    actuator.label = "ACTUAL_ITS_MEASURED_ACTUATOR_ENVELOPE"
    lug_refs = []
    for u in (-2.25, 2.25):
        for v in (-2.25, 2.25):
            lug = Cylinder(CAND["cornerKeepoutDiameterMm"] / 2, CAND["cornerKeepoutDepthMm"],
                           align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
                Location(Vector(u, v, CAND["bodyHmm"])))
            lug.label = "ACTUAL_LUG_UNKNOWN_DIMENSION_KEEP_OUT"
            lug_refs.append(lug)
    lug_keepout = Compound(children=lug_refs, label="FOUR_ACTUAL_LUG_UNKNOWN_KEEP_OUTS")

    cap = Box(7.60, 7.60, 1.20, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 7.20)))
    cap.label = "FROZEN_EXTERIOR_CAP_PROXY"
    pusher = Cylinder(CAND["pusherDiameterMm"] / 2, 1.17,
                      align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.08)))
    pusher.label = "RECALCULATED_PUSHER_D2P60_GAP0P08"
    shoulder_outer = Box(6.50, 6.50, 0.30, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.70)))
    shoulder_inner = Cylinder(4.50 / 2, 0.50, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.60)))
    shoulder = (shoulder_outer - shoulder_inner).clean(); shoulder.label = "CAP_STRUCTURAL_SHOULDER"
    tail_outer = Cylinder(4.50 / 2, 0.35, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.90)))
    tail_inner = Cylinder(3.10 / 2, 0.55, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.80)))
    tail = (tail_outer - tail_inner).clean(); tail.label = "CAP_GUIDE_TAIL"
    cap_system = cap.fuse(pusher).fuse(shoulder).fuse(tail).clean(); cap_system.label = "AUDIT_CAP_PUSHER_SHOULDER"

    guide_outer = Box(8.60, 8.60, 1.05, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.10)))
    guide_bore = Cylinder(4.90 / 2, 1.30, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.00)))
    guide_cavity = Box(6.90, 6.90, 0.75, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.25)))
    guide = (guide_outer - guide_bore - guide_cavity).clean(); guide.label = "AUDIT_GUIDE_AND_STRUCTURAL_STOP"
    hard_stop = Box(6.9, 6.9, 0.10, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, 6.27)))
    hard_stop = (hard_stop - guide_bore).clean(); hard_stop.label = "PROVISIONAL_HARD_STOP_AT_CAP_TRAVEL_0P38"

    return {
        "pocket": pocket, "locator": locator, "body": body, "actuator": actuator,
        "lugKeepout": lug_keepout, "cap": cap_system, "pusher": pusher,
        "shoulder": shoulder, "guide": guide, "hardStop": hard_stop,
    }


def original_pocket_reconstruction() -> Shape:
    """Clean source-parameter reconstruction in raw PushBtn coordinates (+Y=W)."""
    outer = Box(8.80, 8.80, 4.00, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cavity = Box(6.40, 6.40, 4.20, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
        Location(Vector(0, 0, -0.10)))
    base = Box(8.80, 8.80, 0.80, align=(Align.CENTER, Align.CENTER, Align.MAX))
    pocket = base.fuse(outer) - cavity
    for sx in (-1, 1):
        for sy in (-1, 1):
            terminal = Box(1.25, 1.45, 1.20, align=(Align.CENTER, Align.CENTER, Align.CENTER)).moved(
                Location(Vector(sx * 2.25, sy * 2.25, -0.35)))
            pocket = pocket - terminal
    pocket = pocket.clean()
    # local Z becomes source +Y; local Y becomes source -Z.
    result = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)).location * pocket
    result.label = "ORIGINAL_6P40_BACKPLATE_POCKET_SOURCE_RECONSTRUCTION"
    return result


def at_state(shape: Shape, travel: float, label: str) -> Shape:
    moved = shape.moved(Location(Vector(0, 0, -travel))); moved.label = label
    return moved


def mesh_points(tris: np.ndarray) -> np.ndarray:
    return np.vstack((tris.reshape(-1, 3), tris.mean(axis=1)))


def housing_relation(backplate: np.ndarray, shell: np.ndarray) -> dict[str, object]:
    tree = cKDTree(mesh_points(shell))
    centers = backplate.mean(axis=1)
    distances = tree.query(centers, k=1, workers=1)[0]
    areas = tri_area(backplate)
    near = distances < 5.0
    near_area = float(areas[near].sum())
    unsupported = float(areas[(distances > 2.0) & near].sum())
    return {
        "method": "local/selected mesh centroid-to-shell samples; not a full-shell boolean",
        "minimumSampleGapMm": float(distances[near].min()),
        "maximumReportedLocalGapMm": float(distances[near].max()),
        "medianLocalGapMm": float(np.median(distances[near])),
        "contactAreaProxyLe0p10Mm2": float(areas[distances <= 0.10].sum()),
        "nearAreaLt5Mm2": near_area,
        "unsupportedAreaProxyGt2Lt5Mm2": unsupported,
        "unsupportedFractionOfNearArea": unsupported / near_area,
        "contactClass": "VARIABLE CLEARANCE / CAPTURED SEPARATE INSERT, NOT EXACT CONFORMAL",
    }


def source_shell_candidate_mesh(backplate: np.ndarray, shell: np.ndarray) -> np.ndarray:
    """Render-only shell-derived conformal band at controlled 0.30 mm clearance."""
    shell_centers = shell.mean(axis=1)
    bp_tree = cKDTree(mesh_points(backplate))
    distance, index = bp_tree.query(shell_centers, k=1, workers=1)
    selected = shell[(distance > 0.15) & (distance < 4.0)]
    centers = selected.mean(axis=1)
    _, nearest_index = bp_tree.query(centers, k=1, workers=1)
    nearest = mesh_points(backplate)[nearest_index]
    direction = nearest - centers
    norm = np.linalg.norm(direction, axis=1)
    direction = direction / np.maximum(norm[:, None], 1.0e-9)
    # Offset every selected shell triangle toward the interior by 0.30 mm.
    return selected + direction[:, None, :] * 0.30


def algorithm_audit() -> dict[str, object]:
    return {
        "currentSolver": [
            "approved external datum + shell opening",
            "choose_front_depths: carrier/body versus shell collision + 0.20 mm clearance",
            "switch body + terminal roots from selected front_depth",
            "carrier/pair bridge from selected front_depth",
            "build_cap last: boss/socket/contact adapts to already-selected switch depth",
            "production-intent scripts add D3 contact, guide, 0.350 cavity/hard stop, reaction support",
        ],
        "currentDefect": "cap/pusher/travel/seating tolerances are not simultaneous constraints; 0.350 is injected as architecture constant",
        "sourceFaithfulSolver": [
            "frozen exterior cap pose and W axis",
            "measured switch body + explicit corner-feature keep-out + measured seating datum",
            "controlled pocket locating surfaces + rear reaction + terminal/service exits",
            "actual rest/click/overtravel distribution",
            "pusher gap/length/tip and structural stop solved together",
            "shell/carrier clearance and split tolerance verified after the stack closes",
        ],
        "verdict": "REVISE — simultaneous source-faithful stack solver is mechanically correct",
    }


def per_button(datums: dict[str, object]) -> dict[str, object]:
    rows: dict[str, object] = {}
    for name in BUTTONS:
        d = datums[name]
        w = np.asarray(d.axis, float); w /= np.linalg.norm(w)
        u = np.asarray(d.switch_u, float); u /= np.linalg.norm(u)
        v = np.asarray(d.switch_v, float); v /= np.linalg.norm(v)
        angle_z = math.degrees(math.acos(float(np.clip(abs(w[2]), -1.0, 1.0))))
        centre = np.asarray(d.center, float)
        translation_projection = 0.20 * float(np.abs(w).sum())
        rotation_projection = abs(float(centre[0])) * math.tan(math.radians(0.50)) * math.sqrt(max(0.0, 1.0 - w[0] ** 2))
        split_w = translation_projection + rotation_projection
        if name in ("N1", "N2"):
            sensitivity = "HIGH"
        elif name in ("I3", "I4", "M3", "M4"):
            sensitivity = "MEDIUM"
        else:
            sensitivity = "LOW"
        # Conservative arithmetic (not RSS): all independent extremes align.
        base_w = 0.20 + 0.15 + 0.15 + 0.20 + 0.10
        total_w = base_w + split_w
        rest = [CAND["initialGapMm"] - total_w, CAND["initialGapMm"] + total_w]
        click = [rest[0] + 0.15, rest[1] + 0.35]
        stop = [CAND["capTravelToHardStopMm"] - (0.30 + split_w), CAND["capTravelToHardStopMm"] + (0.30 + split_w)]
        rows[name] = {
            "centerMm": list(map(float, centre)), "U": list(map(float, u)),
            "V": list(map(float, v)), "W": list(map(float, w)),
            "assemblyAxisVsGlobalZDeg": angle_z,
            "recommendedCarrierPrintAxisVsBuildZDeg": 0.0,
            "recommendedPocketWallVsBuildZDeg": 0.0,
            "recommendedPusherVsBuildZDeg": 0.0,
            "cornerLugAccommodation": "D1.40 x 0.80 audit keep-out; actual dimensions UNKNOWN",
            "pocket": "7.10 clearance cavity + 3 tunable locator pads + rear seating plane",
            "pusher": "D2.60 / 0.08 nominal initial gap / recalculated",
            "restGapRangeMm": rest, "clickPositionRangeMm": click,
            "hardStopCapTravelRangeMm": stop,
            "fdmU": {"locatingSideNominalMm": 0.24, "clearanceSideNominalMm": 0.49, "uncalibratedMinimumMm": -0.11},
            "fdmV": {"locatingSideNominalMm": 0.275, "clearanceSideNominalMm": 0.525, "uncalibratedMinimumMm": -0.075},
            "fdmWStackWorstPlusMinusMm": total_w,
            "shellSplitProjectedWMm": split_w,
            "shellSplitSensitivity": sensitivity,
            "worstCases": ["BIND/PRELOAD", "FAIL-TO-CLICK", "OVERTRAVEL"],
            "verdict": "AUDIT CANDIDATE ONLY / COUPON + ACTUAL METROLOGY REQUIRED",
        }
    return rows


def render_all(candidate: dict[str, Shape], original_tris: np.ndarray, lugs: list[dict[str, object]],
               datums: dict[str, object], bp: np.ndarray, shell_orig: np.ndarray,
               bp_low: np.ndarray, shell_cur: np.ndarray, conformal: np.ndarray) -> list[str]:
    RENDER.mkdir(parents=True, exist_ok=True)
    names: list[str] = []

    def render(filename: str, objects, title: str, subtitle: str, camera, fit=None, transparent=None, wires=None):
        path = RENDER / filename
        raster_scene(path, objects, title, subtitle, FOOT, camera_offset=camera,
                     fit_points=fit, transparent_objects=transparent or [], wireframes=wires or [])
        names.append(relative(path))

    section_tool = Box(100.0, 50.0, 100.0, align=(Align.CENTER, Align.MAX, Align.CENTER))

    def section_mesh(shape: Shape) -> np.ndarray:
        return safe_triangles((shape & section_tool).clean())

    # 1: three deliberately re-oriented copies in one review frame.
    a = shifted(original_tris, (-11, 0, 0))
    rot_x = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
    b = original_tris @ rot_x.T
    rot_z = np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], float)
    c = shifted(original_tris @ rot_z.T, (11, 0, 0))
    render("01_original_detailed_pushbtn_top_bottom_isometric.png",
           [(a, C["original"]), (b, C["original"]), (c, C["original"])],
           "1 / ORIGINAL DETAILED PUSHBTN — TOP / BOTTOM / ISOMETRIC",
           "3,530 facets | source +Y = actuation | copies re-oriented for one review panel",
           (34, -42, 28), np.vstack((a, b, c)).reshape(-1, 3))

    lug_region = original_tris[original_tris.mean(axis=1)[:, 1] > 2.85]
    render("02_original_corner_lug_closeup.png", [(lug_region, C["original"])],
           "2 / FOUR CORNER POSTS — EXACT SOURCE DETAIL",
           "centres (source X,Z) = (±2.25, ±2.25) | D1.000 x 0.500 | top Y=3.500",
           (12, -16, 11), lug_region.reshape(-1, 3))

    pocket_recon = original_pocket_reconstruction()
    pocket_crop = safe_triangles(pocket_recon)
    render("03_original_pushbtn_inside_original_pocket.png",
           [(pocket_crop, C["pocket"]), (original_tris, C["original"])],
           "3 / ORIGINAL PUSHBTN INSIDE ORIGINAL BACKPLATE POCKET",
           "source-feature reconstruction | 6.40 square opening | body-bottom seating datum",
           (22, -28, 18), None, [(pocket_crop, (*C["pocket"], 100))])

    source_section_tool = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)).location * section_tool
    pocket_section = safe_triangles((pocket_recon & source_section_tool).clean())
    render("04_corner_lug_pocket_section.png",
           [(pocket_section, C["pocket"]), (clip_half(original_tris, 2, 2.25), C["original"])],
           "4 / SECTION THROUGH CORNER POST + POCKET",
           "all four posts have positive 0.320–2.221 mm separation; no recess/contact/support seat",
           (20, -28, 3), None, [(pocket_section, (*C["pocket"], 100))])

    original_can = canonical_original_triangles(original_tris)
    actual_mesh = np.concatenate([safe_triangles(candidate["body"]), safe_triangles(candidate["actuator"])], axis=0)
    render("05_simplified_its_vs_original_overlay.png", [(original_can, C["original"])],
           "5 / ORIGINAL DETAILED VS CURRENT SIMPLIFIED ITS",
           "common body-bottom / W datum | red proxy omits the observed four corner features",
           (18, -23, 16), np.vstack((original_can.reshape(-1, 3), actual_mesh.reshape(-1, 3))),
           [(actual_mesh, (*C["actual"], 125))])

    current_outer = Box(8.8, 8.8, 4.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    current_cavity = Box(6.4, 6.4, 4.4, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Vector(0, 0, -0.1)))
    current_pocket = (current_outer - current_cavity).clean()
    cur_mesh = shifted(safe_triangles(current_pocket), (-6.5, 0, 0))
    cand_mesh = shifted(safe_triangles(candidate["pocket"]), (6.5, 0, 0))
    loc_mesh = shifted(safe_triangles(candidate["locator"]), (6.5, 0, 0))
    render("06_current_vs_source_faithful_pocket.png",
           [(cur_mesh, C["pocket"]), (cand_mesh, C["candidate"]), (loc_mesh, C["unknown"])],
           "6 / CURRENT RECTANGULAR POCKET VS SOURCE-FAITHFUL AUDIT POCKET",
           "left 6.40 all-wall clearance | right 7.10 clearance + three tunable locating pads + rear seat",
           (28, -34, 22), None)

    stack_objs = []
    for key, col in (("pocket", C["pocket"]), ("locator", C["unknown"]), ("body", C["actual"]),
                     ("actuator", C["actual"]), ("cap", C["cap"]), ("guide", C["candidate"]),
                     ("hardStop", C["stop"])):
        stack_objs.append((section_mesh(candidate[key]), col))
    render("07_actuation_stack_section.png", stack_objs,
           "7 / ACTUATION STACK — CAP → PUSHER → ACTUATOR → SEAT",
           "D2.60 pusher | 0.08 initial gap | body-bottom rear seat | 0.38 cap structural stop",
           (18, -26, 8), None)

    state_objs = []
    for i, (label, travel) in enumerate((('REST', 0.0), ('CLICK', 0.33), ('FULL', 0.38))):
        dx = (i - 1) * 12.0
        for key, col in (("pocket", C["pocket"]), ("body", C["actual"]), ("guide", C["candidate"])):
            state_objs.append((shifted(section_mesh(candidate[key]), (dx, 0, 0)), col))
        moving = at_state(candidate["cap"], travel, f"{label}_CAP")
        state_objs.append((shifted(section_mesh(moving), (dx, 0, 0)), C["cap"]))
    render("08_rest_click_full_sections.png", state_objs,
           "8 / REST / CLICK / FULL — PROVISIONAL STACK",
           "cap travel 0.000 / 0.330 / 0.380 | actuator compression 0 / 0.250 / 0.300",
           (38, -46, 18), None)

    def three_slabs(mesh: np.ndarray) -> np.ndarray:
        masks = [np.all(np.abs(mesh[:, :, 0] - position) <= 0.80, axis=1)
                 for position in (-10.0, 0.0, 10.0)]
        return mesh[np.logical_or.reduce(masks)]

    o_shell, o_bp = three_slabs(shell_orig), three_slabs(bp)
    render("09_original_thumb_inner_housing_shell_sections.png", [(o_shell, C["shell"]), (o_bp, C["housing"])],
           "9 / ORIGINAL THUMB — BACKPLATE / OUTER SHELL SECTIONS",
           "X=-10/0/+10 mm local slices | variable captured clearance, not exact coincident offset",
           (90, -120, 72), None, [(o_shell, (*C["shell"], 110))])

    c_shell, c_bp = three_slabs(shell_cur), three_slabs(bp_low)
    render("10_current_thumb_inner_housing_shell_sections.png", [(c_shell, C["shell"]), (c_bp, C["housing"])],
           "10 / CURRENT LOWERED THUMB — BACKPLATE / OUTER SHELL SECTIONS",
           "same X slices after rigid (0,+12.25,-21.00) lowering | larger variable unsupported gap",
           (90, -120, 72), None, [(c_shell, (*C["shell"], 110))])

    conformal_slab = three_slabs(conformal)
    render("11_proposed_conformal_inner_housing_section.png",
           [(c_shell, C["shell"]), (conformal_slab, C["candidate"]), (c_bp, C["housing"])],
           "11 / AUDIT-ONLY CONFORMAL INNER-HOUSING BAND",
           "green = frozen current shell-derived inward band, nominal 0.30 assembly clearance",
           (90, -120, 72), None, [(c_shell, (*C["shell"], 95)), (c_bp, (*C["housing"], 90))])

    axes = []
    fit = []
    for name in BUTTONS:
        d = datums[name]
        axis_shape = local_axis_cylinder(d.center, d.axis, 8.0, 0.65, f"{name}_W_AXIS")
        t = safe_triangles(axis_shape); axes.append((t, C["axis"])); fit.append(t.reshape(-1, 3))
    render("12_eight_button_local_axes.png", axes,
           "12 / EIGHT FROZEN BUTTON LOCAL W AXES",
           "N1 N2 I2 I3 I4 M3 M4 N3 | U/V frames retained in JSON/report",
           (85, -120, 85), np.vstack(fit))

    button_centers = np.array([datums[n].center for n in BUTTONS], float)
    lo, hi = button_centers.min(axis=0) - 12, button_centers.max(axis=0) + 12
    split_shell = clip_box(shell_cur, lo, hi)
    split_plane = Box(0.20, 90, 90, align=(Align.CENTER, Align.CENTER, Align.CENTER))
    split_mesh = safe_triangles(split_plane)
    render("13_shell_split_button_axis_relationship.png", axes + [(split_mesh, C["stop"])],
           "13 / JaD/JfD SPLIT + BUTTON AXIS RELATIONSHIP",
           "red X=0 split datum | N1/N2 high sensitivity | architecture preserved",
           (90, -130, 80), None, [(split_mesh, (*C["stop"], 80))])

    nominal = safe_triangles(candidate["body"])
    min_env = safe_triangles(Box(6.12 + 0.30, 6.05 + 0.30, 3.56 + 0.30,
                                 align=(Align.CENTER, Align.CENTER, Align.MIN)))
    pocket_mesh = safe_triangles(candidate["pocket"])
    render("14_fdm_worst_case_tolerance_visualization.png", [(pocket_mesh, C["pocket"]), (nominal, C["actual"])],
           "14 / FDM WORST-CASE — CAD ZERO-PENETRATION IS NOT A PASS",
           "orange = body/seat uncertainty envelope | locator-side min gaps become negative before calibration",
           (20, -28, 17), None, [(min_env, (*C["unknown"], 105))])
    return names


def report_text(data: dict[str, object]) -> str:
    lug = data["cornerLugs"]
    buttons = data["perButton"]
    table_rows = []
    for name in BUTTONS:
        r = buttons[name]
        w = ", ".join(f"{x:+.3f}" for x in r["W"])
        rg = r["restGapRangeMm"]
        table_rows.append(
            f"| {name} | `{w}` | D1.40×0.80 keep-out / actual UNKNOWN | 7.10 + 3 pads | "
            f"D2.60 / 0.08 gap | {rg[0]:+.3f}…{rg[1]:+.3f} | 0.25 nominal / UNKNOWN distribution | "
            f"0.38 provisional | 0.240 locate / −0.110 min | 0.275 locate / −0.075 min | "
            f"±{r['fdmWStackWorstPlusMinusMm']:.3f} | {r['shellSplitSensitivity']} | **COUPON HOLD** |"
        )
    feature_rows = [
        "| MAIN BODY X | 6.010 main / 6.310 skirt | 6.12 measured | NEAR-EQUIVALENT / actual controls |",
        "| MAIN BODY Y | 6.010 main / 6.310 skirt | 6.05 measured | NEAR-EQUIVALENT / actual controls |",
        "| BODY HEIGHT | 3.500 | 3.560 measured | NEAR-EQUIVALENT |",
        "| TOTAL HEIGHT | 5.000 body-bottom→tip | 6.000 measured | DIFFERENT |",
        "| ACTUATOR DIA | 3.500 | 3.350 measured | NEAR-EQUIVALENT |",
        "| ACTUATOR PROJECTION | 1.500 | 2.440 measured | DIFFERENT |",
        "| CORNER LUG COUNT | 4 exact | 4 visually observed by user | FEATURE EXISTS=YES |",
        "| CORNER LUG X/Y | U/V=(±2.250,±2.250) | UNKNOWN | UNKNOWN |",
        "| CORNER LUG SIZE | D1.000 nominal | UNKNOWN | UNKNOWN |",
        "| CORNER LUG HEIGHT | 0.500 | UNKNOWN | UNKNOWN |",
        "| TERMINAL ROOT | original detailed, 0.728×0.700 metal clue | 0.30×0.70 drawing / root physical UNKNOWN | DIFFERENT |",
        "| TERMINAL ENVELOPE | 7.566 outer span clue | 7.90 drawing nominal | DIFFERENT |",
    ]
    lug_rows = []
    for i, row in enumerate(lug, 1):
        lug_rows.append(
            f"| {i} | {row['centerSourceXZmm'][0]:+.3f}, {row['centerSourceXZmm'][1]:+.3f} | "
            f"{row['widthXmm']:.6f} | {row['lengthZmm']:.6f} | {row['heightMm']:.6f} | "
            f"{row['baseSourceYmm']:.6f} | {row['topSourceYmm']:.6f} | {data['lugPocketDistancesMm'][i-1]:.6f} |"
        )
    render_rows = "\n".join(f"- [{Path(p).name}](../{p})" for p in data["outputs"]["renders"])
    angle_rows = ", ".join(
        f"{name} {buttons[name]['assemblyAxisVsGlobalZDeg']:.3f}" for name in BUTTONS
    )
    return f"""# 76 — Source-faithful button mechanism and FDM rebase audit

CORNER LUG FUNCTION
= **F. SWITCH-HOUSING STAKING / MOLD-ASSEMBLY POSTS; NOT POCKET LOCATORS OR SEATING FEET**

CURRENT POCKET
= **INCOMPLETE — 6.40 source expression is real, but production FDM locating/actual-lug closure is not demonstrated**

SWITCH SEATING DATUM
= **PLASTIC MAIN-BODY BOTTOM / REAR PLANE (source PushBtn local Y=0), not corner-lug bottom**

CURRENT PUSHER LENGTH
= **RECOMPUTE**

CURRENT TRAVEL MODEL
= **PROVISIONAL**

ACTUATION SOLVER
= **REVISE**

THUMB INNER HOUSING
= **NON-CONFORMAL — LOCAL CONFORMAL REBASE RECOMMENDED**

FDM TOLERANCE
= **FAIL under uncalibrated conservative worst case; coupon/calibrated pads required**

SHELL SPLIT
= **PRESERVED**

EXTERIOR
= **PRESERVED**

PRODUCTION MODIFICATION
= **0**

> docs/75의 `BASELINE ARCHITECTURE REUSE = 100%`는 삭제하지 않았지만 현재부터
> **PROVISIONAL — SOURCE-DETAIL DEPENDENCY RECHECK REQUIRED**로 강등했다. 본 문서는 audit-only
> 후보와 review render만 만들며 production source를 수정하지 않는다.

## 1. Final verdict

**C. SOURCE-FAITHFUL BUTTON MECHANISM REBASE RECOMMENDED**

외형, 8개 중심/방향, maximum-lowered Thumb exterior, JaD/JfD split은 그대로 유지할 수 있다.
실패 지점은 exterior가 아니라 `actual lug metrology → controlled pocket locating → pusher gap/length
→ click/overtravel → structural stop → FDM/assembly tolerance` 내부 연쇄다.

별도 판정: **THUMB INNER HOUSING = LOCAL CONFORMAL REBASE**. 원본 Backplate도 별도 captured
insert이며 exact zero-offset conformal solid는 아니지만, lowering 후 shell-near area가 줄고 그중
2 mm 초과 unsupported 비율이 커졌다. frozen exterior에서 inward-derived controlled-clearance band를
audit render로 제시했다.

## 2. Four corner posts — exact extraction

원본 mesh의 source +Y가 press axis이고 transverse 축은 source X/Z다. 아래 X/Z를 기능 좌표 U/V로
읽을 때 V 부호만 반전된다. 네 top disk는 각각 126개 triangle, 면적 0.785073 mm²로 D1.000 원에
해당하며, side 포함 nominal 형상은 **D1.000 × 0.500 mm**다.

| lug | source X,Z centre mm | width X | length Z | height | base Y | top Y | exact gap to original Backplate mm |
|---:|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(lug_rows)}

- count/symmetry: **4 / two-axis symmetric at ±2.250 mm**
- plastic relation: main housing top Y=3.000에서 시작해 Y=3.500까지 돌출한다.
- terminal relation: terminals는 Y<0 rear side에 있고 posts는 Y=3.0…3.5 front side라 기능면이 반대다.
- original pocket contact: selected exact OCCT pair에서 common volume 0, 네 gap 모두 양수다.
- 기능 판정: A/B/C/D가 아니다. **스위치 케이스 자체 staking/mold-assembly post(F)**가 가장
  일관된다. 실제 ITS에서도 존재는 YES이나 정밀 치수는 UNKNOWN이다.

## 3. Original pocket and seating reconstruction

| item | result |
|---|---|
| pocket U/V | **6.400 × 6.400 mm**, source expression `6.0 + 2×0.2` |
| source support thickness | **4.000 mm** |
| occupied body cavity depth | **3.500 mm** nominal PushBtn housing |
| corner-lug recess | **none found**; open/front headspace accommodates the posts |
| bottom/rear seating plane | **PushBtn plastic body bottom Y=0** |
| side locating | 6.40 square Backplate walls, nominal 0.195/side around 6.010 main body |
| skirt fit | 6.310 skirt leaves **0.045 mm/side**, CAD-fit but not FDM production clearance |
| rear reaction | Backplate seating ring/plane around terminal exits |
| insertion | interior/rear insertion; actuator toward cap/shell, terminals rearward |
| terminal exits | four rear openings/reliefs; not corner-post seats |

따라서 corner posts 때문에 body가 0.5 mm 뜨는 구조가 아니다. pusher 기준은 `body bottom →
housing top → actuator projection` 연쇄다. 다만 actual ITS의 body-bottom/foot 형상 실측이 없으므로
production pocket depth는 아직 잠그지 않는다.

## 4. Original PushBtn ↔ actual ITS feature map

| feature | ORIGINAL | ACTUAL ITS | STATUS |
|---|---:|---:|---|
{chr(10).join(feature_rows)}

Actual lug packaging rule은 **FEATURE EXISTS=YES / dimensions=UNKNOWN / first-article gate**다.
원본 D1×0.5를 실물 치수로 복사하지 않았다.

## 5. Audit-only pocket candidate

대표 local U/V/W 후보는 **7.10 × 7.10 clearance cavity**, rear body-bottom seat, terminal exits,
그리고 세 개의 교체/튜닝 가능한 datum pad를 쓴다. 모든 벽을 억지 끼움으로 만들지 않고
`−U 두 점 + −V 한 점`만 locating, 반대 벽은 clearance로 분리했다.

- actual body nominal gap before pads: U 0.490 / V 0.525 mm per side
- locating side after 0.25 pad: U **0.240** / V **0.275 mm**
- corner feature: D1.40 × 0.80 **UNKNOWN keep-out**, printed contact 없음
- pusher: **D2.60**, actuator radial centering margin **0.375 mm**
- nominal initial gap: **0.080 mm**; zero-preload를 의도하지만 FDM worst case는 아직 닫히지 않는다.
- removal: front/open insertion and rear terminal access; all-round press fit 없음

이 후보는 actual lug/body coupon에 맞춰 pad thickness와 keep-out을 재규격화하기 위한 review geometry다.

## 6. Pusher / travel / hard-stop re-derivation

| state | cap travel | pusher–actuator | actuator compression | structural-stop gap |
|---|---:|---|---:|---:|
| REST | 0.000 | 0.080 gap | 0.000 | 0.380 |
| CLICK (nominal inference) | 0.330 | contact | 0.250 | 0.050 |
| FULL audit stop | 0.380 | contact | 0.300 | 0.000 |

`0.350 mm`는 actual sample 기록의 upper observation/validation bound일 뿐 pre-travel/click/post-travel
분해가 없다. 후보는 0.30 compression에서 printed shoulder가 하중을 받도록 보였지만 이것도
**PROVISIONAL**이다. production hard stop은 실물 force–travel 또는 최소 REST/CLICK/BOTTOM-OUT
실측 전 확정할 수 없다.

## 7. Solver dependency audit

현재:

```text
shell/body clearance
→ choose_front_depths()
→ switch/body/terminal pose
→ carrier + pair bridge
→ build_cap() adapts last
→ later mechanism scripts inject D3 pusher + 0.350 guide/hard stop + support
```

권고:

```text
frozen exterior cap pose + W
+ actual body/lug seating datum
+ actual travel distribution
+ controlled pocket/rear reaction
+ pusher gap/length/tip
+ structural stop
→ simultaneous stack closure
→ shell/carrier/split/FDM clearance verification
```

`choose_front_depths` 자체의 shell-clearance 역할은 남길 수 있지만 최상위 solver가 될 수 없다.
`build_cap`, guide, pusher, hard stop, rear support와 pair bridge는 공통 stack result를 소비해야 한다.
production generator는 이번 작업에서 수정하지 않았다.

## 8. U/V/W, print orientation, FDM model

별도 carrier의 권장 출력 자세는 rear plate on bed라 pocket/pusher W가 build Z와 **0°**이고 pocket
walls도 build Z에 평행하다. 아래 global-Z 각도는 조립 자세를 보여 주며, 실제 인쇄에서는 각
carrier를 local frame으로 재배향해야 한다.

사용한 uncalibrated conservative 범위(mm): XY ±0.15, Z quantization ±0.10, small-pocket shrink
0…0.10/side, elephant foot 0…0.15/side, slope 0…0.20, bridge sag 0…0.20, support scar
0…0.15, warpage ±0.20, shell-half translation global axis별 ±0.20, rotation ±0.50°.

선형 worst-case 합산에서는 candidate locating-side minimum도 U −0.110 / V −0.075 mm가 되어
**BIND/PRELOAD** 가능성이 남는다. W stack도 모든 버튼에서 rest preload, fail-to-click,
overtravel을 동시에 배제하지 못한다. 그러므로 CAD `0.000 penetration`은 PASS가 아니다.

## 9. Per-button virtual propagation

| button | SWITCH LOCAL W | CORNER-LUG ACCOMMODATION | POCKET | PUSHER / REST GAP | REST GAP RANGE | TRAVEL | HARD STOP | FDM U | FDM V | FDM W STACK | SHELL-SPLIT | VERDICT |
|---|---|---|---|---|---:|---|---|---|---|---:|---|---|
{chr(10).join(table_rows)}

Assembly global Z에 대한 W 각도(deg): {angle_rows}.

N1/N2는 seam/shared-carrier capture 때문에 HIGH, I3/I4/M3/M4는 MEDIUM, I2/N3는 LOW로
분류했다. 이것은 split 제거 권고가 아니며 screw/joint seating variation을 W에 투영한 것이다.

## 10. Thumb inner-housing relation

| metric | ORIGINAL | CURRENT LOWERED |
|---|---:|---:|
| minimum sampled local gap | {data['thumbHousing']['original']['minimumSampleGapMm']:.3f} | {data['thumbHousing']['currentLowered']['minimumSampleGapMm']:.3f} |
| median local gap (<5 mm region) | {data['thumbHousing']['original']['medianLocalGapMm']:.3f} | {data['thumbHousing']['currentLowered']['medianLocalGapMm']:.3f} |
| max reported local gap | {data['thumbHousing']['original']['maximumReportedLocalGapMm']:.3f} | {data['thumbHousing']['currentLowered']['maximumReportedLocalGapMm']:.3f} |
| contact proxy ≤0.10 mm² | {data['thumbHousing']['original']['contactAreaProxyLe0p10Mm2']:.3f} | {data['thumbHousing']['currentLowered']['contactAreaProxyLe0p10Mm2']:.3f} |
| near-shell area proxy <5 mm² | {data['thumbHousing']['original']['nearAreaLt5Mm2']:.3f} | {data['thumbHousing']['currentLowered']['nearAreaLt5Mm2']:.3f} |
| unsupported proxy 2…5 mm² | {data['thumbHousing']['original']['unsupportedAreaProxyGt2Lt5Mm2']:.3f} | {data['thumbHousing']['currentLowered']['unsupportedAreaProxyGt2Lt5Mm2']:.3f} |
| unsupported fraction of near area | {100.0 * data['thumbHousing']['original']['unsupportedFractionOfNearArea']:.1f}% | {100.0 * data['thumbHousing']['currentLowered']['unsupportedFractionOfNearArea']:.1f}% |

방법은 full boolean이 아니라 X=−10/0/+10 sections와 local centroid-to-shell samples다. 원본도
Backplate라는 별도 부품이며 exact fused/conformal zero-gap은 아니다. 그러나 lowering 후 near-shell
area가 줄고 median gap 및 unsupported fraction이 커졌다. 후보는 **frozen current shell의 local inner-facing tessellation에서
inward 0.30 mm로 유도한 render-only band**다. production에서는 mesh offset이 아니라 frozen BRep
local surface의 controlled offset/loft와 fastening datum으로 다시 만들어야 한다.

## 11. Load path / design-principle comparison

`USER FORCE → CAP → D2.60 PUSHER → ACTUATOR → SWITCH BODY → BODY-BOTTOM SEAT
→ POCKET/LOCATOR PADS → INNER HOUSING → SHELL`.

| function | comparison |
|---|---|
| switch locating | **HYBRID RECOMMENDED** — original seat principle + actual body metrology |
| corner-lug support | **ORIGINAL PRINCIPLE** — no printed load contact; keep-out only |
| pocket | **HYBRID RECOMMENDED** — source datum + FDM three-point pads |
| actuator contact / pusher | **CURRENT CONCEPT BETTER, DIMENSION RECOMPUTE** |
| guide / retention | **CURRENT BETTER** |
| hard stop | **CURRENT PRINCIPLE BETTER, 0.350 VALUE PROVISIONAL** |
| rear support | **HYBRID RECOMMENDED** — broad body seat, terminal-safe exits |
| inner housing / shell transfer | **LOCAL CONFORMAL REBASE** |

Candidate에서 lug point-contact, body cantilever와 all-wall press fit은 제거했지만, uncalibrated FDM
worst case가 locator pads와 W stack을 닫지 못하므로 production PASS는 아니다.

## 12. Required renders

{render_rows}

## 13. Priority next step — production apply 전

1. **반드시 변경 검토:** pocket locating을 all-wall 6.40 clearance에서 datum-pad/clearance-surface
   구조로 rebase하고 pusher/hard-stop을 실측 travel stack으로 재계산한다.
2. **그대로 살릴 수 있음:** approved exterior, 8 center/axis, cap 외부 7.60/8.00 language,
   JaD/JfD split, current separate guide/structural-stop 원리.
3. **실측 필수:** actual lug U/V/D/H/base, main/skirt maximum, body-bottom seating flatness,
   actuator REST/CLICK/BOTTOM-OUT, terminal root/exit.
4. **coupon 필수:** 6.70/6.90/7.10 cavity와 0.15/0.25/0.35 locator pads, elephant-foot 방향,
   D2.4/2.6/2.8 pusher, 0.05/0.08/0.12 gap, assembly 반복성.
5. **production apply 전 render:** chosen measured ITS exact model in N1/N2 seam, all 8 local sections,
   Thumb BRep conformal insert/fastener sections, tolerance-min/max motion overlay.

## 14. Outputs / freeze / STOP

- audit STEP: `{data['outputs']['step']}`
- audit JSON: `{data['outputs']['json']}`
- report: `{data['outputs']['report']}`
- protected production inputs preserved: **{data['protectedInputsPreserved']}**
- production geometry modification: **0**

**STOP.** 사용자 render review/승인 전 production pocket, carrier, cap, pusher, shell, Thumb에 적용하지 않는다.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    before = {relative(p): sha256(p) for p in PROTECTED if p.exists()}

    original_tris = load_mesh("PushBtn")
    lugs = extract_corner_lugs(original_tris)
    if len(lugs) != 4:
        raise RuntimeError(f"Expected four original corner posts, found {len(lugs)}")

    candidate = local_candidate()
    original = build_original_parts()
    original_canonical = Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)).location * original.full
    original_canonical.label = "ORIGINAL_PUSHBTN_EXACT_DETAIL_BODY_BOTTOM_W0"
    assembly = Compound(children=[
        original_canonical,
        candidate["pocket"], candidate["locator"], candidate["body"],
        candidate["actuator"], candidate["lugKeepout"], candidate["cap"],
        candidate["guide"], candidate["hardStop"],
    ], label="SOURCE_FAITHFUL_BUTTON_MECHANISM_AUDIT_ONLY")
    export_step(assembly, STEP_PATH)

    datums = {name: datum for name, datum in load_all_datums().items() if name in BUTTONS}
    bp = load_mesh("Backplate")
    shell_orig = np.vstack((load_mesh("Joystick_1"), load_mesh("Joystick_2")))
    bp_low = bp + np.array([0.0, 12.25, -21.0])
    shell_cur = np.vstack((load_mesh("ITS_LIVE_JaD"), load_mesh("ITS_LIVE_JfD")))
    thumb_original = housing_relation(bp, shell_orig)
    thumb_current = housing_relation(bp_low, shell_cur)
    conformal = source_shell_candidate_mesh(bp_low, shell_cur)

    # Selected exact results already established against original Backplate in
    # the representative PushBtn<4> pose; preserve order sorted by X then Z.
    lug_distances = [0.3203669231, 0.4075434014, 2.2207743730, 0.4763209919]
    rows = per_button(datums)
    pngs = render_all(candidate, original_tris, lugs, datums, bp, shell_orig, bp_low, shell_cur, conformal)

    data: dict[str, object] = {
        "schema": "onegrip.source_faithful_button_mechanism_and_fdm_rebase_audit.v1",
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "AUDIT ONLY / SERIAL / LOCAL CROPS + SELECTED PAIRS / NO FULL SHELL BOOLEAN",
        "statusCorrection": "docs/75 BASELINE ARCHITECTURE REUSE=100% downgraded to PROVISIONAL — SOURCE-DETAIL DEPENDENCY RECHECK REQUIRED",
        "authority": {
            "nominal": "ORIGINAL ONEGRIP DETAILED PUSHBTN",
            "hardware": "ACTUAL PURCHASED ITS-1105 MEASUREMENTS",
            "architecture": "ORIGINAL SURROUNDING BACKPLATE/POCKET + CURRENT SEPARATE GUIDE/HARD-STOP PRINCIPLE",
            "legacy": "CURRENT SIMPLIFIED ITS PROXY",
        },
        "freeze": {"exterior": "PRESERVED", "buttonCentersOrientations": "PRESERVED",
                   "loweredThumbExterior": "PRESERVED", "JaDJfDSplit": "PRESERVED",
                   "productionGeometryModificationCount": 0},
        "cornerLugs": lugs,
        "lugPocketDistancesMm": lug_distances,
        "lugFunction": "F / switch-housing staking or mold-assembly posts; no original pocket contact",
        "actualLugFeature": {"exists": True, "source": "user visual observation", "dimensions": "UNKNOWN", "gate": "FIRST ARTICLE METROLOGY"},
        "originalPocket": ORIGINAL_POCKET,
        "candidate": CAND,
        "travelAuthority": {"original": "UNKNOWN / rigid CAD only", "actualNominalMm": 0.25,
                            "actualUpperObservedMm": 0.35, "current0p350": "PROVISIONAL",
                            "candidateHardStop": "0.38 cap travel / 0.30 actuator compression / PROVISIONAL"},
        "algorithm": algorithm_audit(),
        "fdmModel": FDM,
        "perButton": rows,
        "thumbHousing": {"original": thumb_original, "currentLowered": thumb_current,
                         "candidate": "frozen exterior local inner-facing surface-derived 0.30 mm render band",
                         "verdict": "LOCAL CONFORMAL REBASE"},
        "finalVerdict": "C / SOURCE-FAITHFUL BUTTON MECHANISM REBASE RECOMMENDED",
        "thumbVerdict": "LOCAL CONFORMAL REBASE",
        "outputs": {"step": relative(STEP_PATH), "json": relative(JSON_PATH),
                    "report": relative(REPORT), "renders": pngs},
    }
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    after = {relative(p): sha256(p) for p in PROTECTED if p.exists()}
    data["inputHashesBefore"] = before
    data["inputHashesAfter"] = after
    data["protectedInputsPreserved"] = before == after
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT.write_text(report_text(data), encoding="utf-8")
    print(json.dumps({
        "verdict": data["finalVerdict"], "thumb": data["thumbVerdict"],
        "lugCount": len(lugs), "renders": len(pngs),
        "protectedInputsPreserved": data["protectedInputsPreserved"],
        "step": relative(STEP_PATH), "json": relative(JSON_PATH), "report": relative(REPORT),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
