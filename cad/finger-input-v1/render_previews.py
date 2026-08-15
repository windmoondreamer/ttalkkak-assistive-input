"""Blender 5.x product-render pipeline for the OneGrip finger input CAD.

Run from the repository root (or any directory) with::

    blender --background --python cad/finger-input-v1/render_previews.py

Optional arguments after ``--``::

    --resolution 720 --samples 48
    --only variant_a_01_front final_01_four_finger_array

The script intentionally contains no dimensions or fabricated labels in-frame.
Neutral, pressed-state, exploded-part, and integration geometry all comes from
the checked-in STL exports.  The render manifest records the SHA-256 digest and
nanosecond-resolution modification time of every input used by a run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
RENDERS = ROOT / "renders"
PRINTABLE = ROOT / "printable"
VARIANTS_DIR = ROOT / "variants"
INTEGRATION = ROOT / "integration"
RENDER_GEOMETRY = RENDERS / "geometry_cache"
BUILD_MANIFEST = ROOT / "build_manifest.json"
BUILD_DATA = json.loads(BUILD_MANIFEST.read_text(encoding="utf-8"))
GRIP_M = (
    ROOT.parent
    / "grip-size-prototypes"
    / "putty_cast_v7_support_free"
    / "ergonomic_putty_grip_support_free_M.stl"
)


def manifest_stl(keys, fallback: Path) -> Path:
    """Resolve a generated STL path from the build manifest when available."""
    value = BUILD_DATA
    try:
        for key in keys:
            value = value[key]
        relative = Path(value["stl"])
        return ROOT / relative
    except (KeyError, TypeError):
        # State/attached-rail entries appear only after the new generator has
        # completed.  The deterministic export name remains a safe preflight
        # target while CAD regeneration is in progress.
        return fallback

VARIANTS = {
    "a": {
        "slug": "direct_switch",
        "states": {
            state: RENDER_GEOMETRY / f"variant_a_{state}_visualization_only.stl"
            for state in ("neutral", "left", "center", "right")
        },
        "exploded": {
            name: VARIANTS_DIR / f"variant_a_{name}.stl"
            for name in (
                "shell", "bottom_cover", "left_plunger", "center_plunger",
                "right_plunger", "stop_shim_0p20_coarse_fdm",
            )
        },
        "color": (0.045, 0.30, 0.32, 1.0),
    },
    "b": {
        "slug": "lalboard_paddle",
        "states": {
            state: RENDER_GEOMETRY / f"variant_b_{state}_visualization_only.stl"
            for state in ("neutral", "left", "center", "right")
        },
        "exploded": {
            name: manifest_stl(
                ("presets", "middle", "files", name),
                PRINTABLE / f"middle_{name}.stl",
            )
            for name in (
                "cartridge", "bottom_cover", "left_key", "left_follower",
                "center_key", "right_key", "right_follower", "left_tpu_pad",
                "center_tpu_pad", "right_tpu_pad",
            )
        },
        "color": (0.045, 0.20, 0.46, 1.0),
    },
    "c": {
        "slug": "rocker",
        "states": {
            state: RENDER_GEOMETRY / f"variant_c_{state}_visualization_only.stl"
            for state in ("neutral", "left", "center", "right")
        },
        "exploded": {
            name: VARIANTS_DIR / f"variant_c_{name}.stl"
            for name in (
                "shell", "bottom_cover", "shared_rocker", "left_follower",
                "center_follower", "right_follower", "stop_shim_0p20_coarse_fdm",
            )
        },
        "color": (0.56, 0.16, 0.06, 1.0),
    },
}

MIDDLE_LAYOUT = BUILD_DATA["presets"]["middle"]["layout"]
SWITCH_SPEC = BUILD_DATA["switch"]
SWITCH_POSITIONS = {
    state: tuple(float(value) for value in MIDDLE_LAYOUT[f"{state}_switch"])
    for state in ("left", "center", "right")
}
MIDDLE_SURROGATE = INTEGRATION / "middle_finger_surrogate.stl"
ATTACHED_ARRAY = manifest_stl(
    ("__render_cache_not_in_manifest__",),
    RENDER_GEOMETRY / "four_finger_array_with_attached_rail_visualization_only.stl",
)


def cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--resolution", type=int, default=720)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--only", nargs="*", default=[])
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


ARGS = cli_args()
RENDERS.mkdir(parents=True, exist_ok=True)
RENDERED: list[dict[str, object]] = []
USED_INPUTS: set[Path] = {BUILD_MANIFEST.resolve(), Path(__file__).resolve()}
SCENE_INPUTS: set[Path] = set()
INPUT_RECORD_CACHE: dict[tuple[str, int, int], dict[str, object]] = {}
SOURCE_SNAPSHOT: dict[Path, tuple[int, int]] = {}


def should_render(stem: str) -> bool:
    if not ARGS.only:
        return True
    return stem in ARGS.only or any(stem.startswith(prefix) for prefix in ARGS.only)


def source_label(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.parents[1]).as_posix()
    except ValueError:
        return resolved.as_posix()


def input_record(path: Path) -> dict[str, object]:
    resolved = path.resolve()
    stat = resolved.stat()
    cache_key = (str(resolved), stat.st_size, stat.st_mtime_ns)
    cached = INPUT_RECORD_CACHE.get(cache_key)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    record = {
        "path": source_label(resolved),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": digest.hexdigest(),
    }
    INPUT_RECORD_CACHE[cache_key] = record
    return record


def required_sources() -> list[Path]:
    paths = {
        BUILD_MANIFEST.resolve(),
        Path(__file__).resolve(),
        GRIP_M.resolve(),
        MIDDLE_SURROGATE.resolve(),
    }
    paths.update(
        path.resolve()
        for info in VARIANTS.values()
        for group in (info["states"], info["exploded"])
        for path in group.values()
    )
    paths.update(
        path.resolve()
        for path in (
            RENDER_GEOMETRY / "four_finger_array_visualization_only.stl",
            RENDER_GEOMETRY / "four_finger_array_with_surrogates_visualization_only.stl",
            ATTACHED_ARRAY,
        )
    )
    return sorted(paths, key=source_label)


def preflight_sources() -> dict[Path, tuple[int, int]]:
    missing = [source_label(path) for path in required_sources() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Render preflight failed; regenerate CAD before rendering. Missing:\n  "
            + "\n  ".join(missing)
        )
    return {
        path: (path.stat().st_size, path.stat().st_mtime_ns)
        for path in required_sources()
    }


def verify_source_snapshot(snapshot: dict[Path, tuple[int, int]]) -> None:
    changed = [
        source_label(path)
        for path, original in snapshot.items()
        if not path.exists() or (path.stat().st_size, path.stat().st_mtime_ns) != original
    ]
    if changed:
        raise RuntimeError(
            "CAD inputs changed during rendering; discard this run and rerender after freeze:\n  "
            + "\n  ".join(changed)
        )


def material(name: str, rgba, metallic=0.0, roughness=0.42):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


MAT = {
    "skin": material("Soft fingertip surrogate", (0.90, 0.43, 0.25, 1), roughness=0.58),
    "contact": material("Active contact", (1.0, 0.15, 0.055, 1), metallic=0.05, roughness=0.28),
    "switch": material("Switch housing", (0.055, 0.065, 0.085, 1), roughness=0.31),
    "button": material("Switch actuator", (0.86, 0.89, 0.93, 1), metallic=0.22, roughness=0.24),
    "metal": material("Hardware", (0.32, 0.39, 0.47, 1), metallic=0.72, roughness=0.22),
    "grip": material("Grip M", (0.17, 0.19, 0.23, 1), roughness=0.64),
    "array": material("Four finger array", (0.025, 0.27, 0.42, 1), roughness=0.37),
    "floor": material("Studio floor", (0.82, 0.84, 0.87, 1), roughness=0.72),
    "neutral": material("Neutral CAD", (0.19, 0.23, 0.29, 1), roughness=0.46),
}
for key, info in VARIANTS.items():
    MAT[f"variant_{key}"] = material(f"Variant {key.upper()}", info["color"], roughness=0.38)


def clear_scene():
    SCENE_INPUTS.clear()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection" and collection.users == 0:
            bpy.data.collections.remove(collection)


def configure_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = ARGS.resolution
    scene.render.resolution_y = ARGS.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_percentage = 100
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.filepath = ""
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filter_size = 1.25
    scene.render.use_file_extension = True
    scene.render.image_settings.compression = 18
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = ARGS.samples
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.22, 0.25, 0.29, 1)
    bg.inputs["Strength"].default_value = 0.62


def import_stl(path: Path, name: str, mat, location=(0, 0, 0)):
    if not path.exists():
        raise FileNotFoundError(path)
    before = set(bpy.context.scene.objects)
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(path))
    else:
        bpy.ops.import_mesh.stl(filepath=str(path))
    created = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not created:
        raise RuntimeError(f"STL import created no object: {path}")
    obj = created[0]
    obj.name = name
    obj.location = location
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    resolved = path.resolve()
    USED_INPUTS.add(resolved)
    SCENE_INPUTS.add(resolved)
    return obj


def rounded_box(name, location, scale, mat, bevel=1.2):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = obj.modifiers.new("Soft edge", "BEVEL")
    mod.width = min(bevel, min(scale) * 0.22)
    mod.segments = 5
    obj.data.materials.append(mat)
    return obj


def cylinder(name, location, radius, depth, mat, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new("Edge bevel", "BEVEL")
    bevel.width = min(radius * 0.14, 0.4)
    bevel.segments = 3
    return obj


def bounds(objects):
    pts = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "FONT"}:
            continue
        pts.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not pts:
        return Vector((-1, -1, -1)), Vector((1, 1, 1))
    return (
        Vector(tuple(min(p[i] for p in pts) for i in range(3))),
        Vector(tuple(max(p[i] for p in pts) for i in range(3))),
    )


def add_switch(location, index=0, active=False):
    x, y, z = location
    width = float(SWITCH_SPEC["width"])
    depth = float(SWITCH_SPEC["depth"])
    body_height = float(SWITCH_SPEC["body_height"])
    total_height = float(SWITCH_SPEC["total_height"])
    terminal_pitch = float(SWITCH_SPEC["terminal_pitch"])
    terminal_radius = float(SWITCH_SPEC["terminal_diameter"]) / 2
    terminal_length = float(SWITCH_SPEC["terminal_length"])
    cap_height = total_height - body_height
    cap_width = min(width, depth) * 0.55
    housing = rounded_box(
        f"Switch {index + 1} housing",
        (x, y, z + body_height / 2),
        (width, depth, body_height),
        MAT["switch"],
        0.6,
    )
    actuator_mat = MAT["contact"] if active else MAT["button"]
    actuator = rounded_box(
        f"Switch {index + 1} actuator",
        (x, y, z + body_height + cap_height / 2),
        (cap_width, cap_width, cap_height),
        actuator_mat,
        min(0.25, cap_height * 0.3),
    )
    pins = [
        cylinder(
            f"Switch {index + 1} terminal",
            (x + sx, y, z - terminal_length / 2),
            terminal_radius,
            terminal_length,
            MAT["metal"],
        )
        for sx in (-terminal_pitch / 2, terminal_pitch / 2)
    ]
    return [housing, actuator, *pins]


def add_studio(objects, floor=True):
    mn, mx = bounds(objects)
    center = (mn + mx) * 0.5
    size = max(70.0, (mx - mn).length * 1.35)
    if floor:
        bpy.ops.mesh.primitive_plane_add(size=size, location=(center.x, center.y, mn.z - 0.28))
        plane = bpy.context.object
        plane.name = "Studio floor"
        plane.data.materials.append(MAT["floor"])
    light_specs = [
        # CAD geometry is authored in millimetres while Blender lights use a
        # metre-oriented inverse-square model, hence the deliberately high power.
        ("Key", (center.x - size * 0.38, center.y - size * 0.34, mx.z + size * 0.55), 145000, size * 0.33),
        ("Fill", (center.x + size * 0.42, center.y - size * 0.18, center.z + size * 0.28), 85000, size * 0.28),
        ("Rim", (center.x + size * 0.12, center.y + size * 0.45, mx.z + size * 0.42), 125000, size * 0.24),
    ]
    for name, loc, power, area_size in light_specs:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.shape = "DISK"
        data.size = area_size
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        direction = center - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera_for(objects, direction=(1.4, -1.7, 1.25), up=(0, 0, 1), margin=1.26, perspective=False):
    mn, mx = bounds(objects)
    center = (mn + mx) * 0.5
    corners = [
        Vector((x, y, z))
        for x in (mn.x, mx.x)
        for y in (mn.y, mx.y)
        for z in (mn.z, mx.z)
    ]
    view_dir = Vector(direction).normalized()  # target -> camera
    look = -view_dir
    up_vec = Vector(up).normalized()
    if abs(look.dot(up_vec)) > 0.96:
        up_vec = Vector((0, 1, 0))
    right = look.cross(up_vec).normalized()
    screen_up = right.cross(look).normalized()
    w = max((p - center).dot(right) for p in corners) - min((p - center).dot(right) for p in corners)
    h = max((p - center).dot(screen_up) for p in corners) - min((p - center).dot(screen_up) for p in corners)
    extent = max(w, h, 1.0)
    data = bpy.data.cameras.new("Product camera")
    cam = bpy.data.objects.new("Product camera", data)
    bpy.context.collection.objects.link(cam)
    distance = max((mx - mn).length * 2.1, 55.0)
    cam.location = center + view_dir * distance
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    if perspective:
        data.type = "PERSP"
        data.lens = 58
    else:
        data.type = "ORTHO"
        data.ortho_scale = extent * margin
    data.dof.use_dof = False
    bpy.context.scene.camera = cam
    return cam


def render(stem: str, category: str, description: str):
    if not should_render(stem):
        return
    if SOURCE_SNAPSHOT:
        verify_source_snapshot(SOURCE_SNAPSHOT)
    path = RENDERS / f"{stem}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if SOURCE_SNAPSHOT:
        verify_source_snapshot(SOURCE_SNAPSHOT)
    RENDERED.append(
        {
            "file": path.name,
            "category": category,
            "description": description,
            "geometry_inputs": [source_label(item) for item in sorted(SCENE_INPUTS, key=source_label)],
        }
    )
    print(f"[OneGrip render] {path.name}")


def variant_base(key, state="neutral"):
    info = VARIANTS[key]
    obj = import_stl(
        info["states"][state],
        f"Variant {key.upper()} — {info['slug']} — {state}",
        MAT[f"variant_{key}"],
    )
    return obj


def render_variant_standard(key, view, direction, up=(0, 0, 1)):
    number = {"front": "01", "side": "02", "top": "03"}[view]
    stem = f"variant_{key}_{number}_{view}"
    if not should_render(stem):
        return
    clear_scene(); configure_scene()
    obj = variant_base(key)
    objects = [obj]
    add_studio(objects)
    camera_for(objects, direction=direction, up=up, margin=1.25)
    render(
        stem,
        f"variant_{key}",
        f"{view} view of the visualization-only neutral-state {VARIANTS[key]['slug']} mesh; STEP/3MF is authoritative",
    )


def render_fingertip(key):
    stem = f"variant_{key}_04_fingertip_surrogate"
    if not should_render(stem): return
    clear_scene(); configure_scene()
    obj = variant_base(key)
    finger = import_stl(MIDDLE_SURROGATE, "Exported middle-finger surrogate", MAT["skin"])
    objects = [obj, finger]
    add_studio(objects)
    camera_for(objects, direction=(1.45, -1.75, 1.0), margin=1.28, perspective=False)
    render(stem, f"variant_{key}", "Middle-finger surrogate aligned to the visualization-only neutral assembly mesh")


def exploded_material(key, part_name):
    if "tpu" in part_name:
        return MAT["skin"]
    if "follower" in part_name:
        return MAT["metal"]
    if "shim" in part_name:
        return MAT["contact"]
    if any(token in part_name for token in ("key", "plunger", "rocker")):
        return MAT["button"]
    return MAT[f"variant_{key}"]


def exploded_offset(part_name):
    if part_name == "bottom_cover":
        return Vector((0, 0, -8.0))
    if "tpu" in part_name:
        return Vector((0, 0, 34.0))
    if "follower" in part_name:
        return Vector((0, 0, 11.0))
    if any(token in part_name for token in ("key", "plunger", "rocker")):
        return Vector((0, 0, 23.0))
    if "shim" in part_name:
        return Vector((0, 22.0, 13.0))
    return Vector((0, 0, 0))


def render_exploded(key):
    stem = f"variant_{key}_05_exploded"
    if not should_render(stem): return
    clear_scene(); configure_scene()
    objects = []
    for part_name, path in VARIANTS[key]["exploded"].items():
        obj = import_stl(
            path,
            f"Variant {key.upper()} separated part — {part_name}",
            exploded_material(key, part_name),
        )
        obj.location += exploded_offset(part_name)
        objects.append(obj)
    add_studio(objects)
    camera_for(objects, direction=(1.55, -1.8, 1.15), margin=1.22)
    render(stem, f"variant_{key}", "Exploded view assembled exclusively from exported separated-part STLs")


def render_switches(key):
    stem = f"variant_{key}_06_switches"
    if not should_render(stem): return
    clear_scene(); configure_scene()
    USED_INPUTS.add(BUILD_MANIFEST.resolve())
    SCENE_INPUTS.add(BUILD_MANIFEST.resolve())
    objects = []
    for i, state in enumerate(("left", "center", "right")):
        x, y = SWITCH_POSITIONS[state]
        objects += add_switch((x, y, 0), i, active=False)
    add_studio(objects)
    camera_for(objects, direction=(1.35, -1.65, 1.25), margin=1.3)
    render(stem, f"variant_{key}", "Panasonic switch references at exact middle-preset manifest coordinates")


def render_state(key, state, number):
    stem = f"variant_{key}_{number:02d}_state_{state}"
    if not should_render(stem): return
    clear_scene(); configure_scene()
    obj = variant_base(key, state)
    objects = [obj]
    add_studio(objects)
    camera_for(objects, direction=(1.25, -1.65, 1.0), margin=1.22)
    render(
        stem,
        f"variant_{key}",
        f"Visualization-only {state.upper()} kinematic assembly mesh with CAD-authored key, follower, and switch travel",
    )


def render_array():
    stem = "final_01_four_finger_array"
    if should_render(stem):
        clear_scene(); configure_scene()
        obj = import_stl(RENDER_GEOMETRY / "four_finger_array_visualization_only.stl", "Four finger array", MAT["array"])
        objects = [obj]
        add_studio(objects)
        camera_for(objects, direction=(1.25, -1.6, 1.15), margin=1.2)
        render(stem, "integration", "Four-finger array from the visualization-only assembly STL; STEP/3MF is authoritative")

    stem = "final_02_four_finger_array_with_surrogates"
    if should_render(stem):
        clear_scene(); configure_scene()
        obj = import_stl(RENDER_GEOMETRY / "four_finger_array_with_surrogates_visualization_only.stl", "Four finger array with surrogates", MAT["array"])
        objects = [obj]
        add_studio(objects)
        camera_for(objects, direction=(1.25, -1.6, 1.08), margin=1.2)
        render(stem, "integration", "Visualization-only four-finger array STL with aligned surrogate geometry")


def render_grip_integration():
    stem = "final_03_grip_m_integration_preview"
    if not should_render(stem): return
    clear_scene(); configure_scene()
    grip = import_stl(GRIP_M, "Existing ergonomic putty grip — M", MAT["grip"])
    array = import_stl(
        ATTACHED_ARRAY,
        "Four-finger array with attached vertical rail",
        MAT["array"],
    )
    # The CAD export already shares the M-grip coordinate system: modules are
    # on global -X, their heights/depths are preset-specific, and the carrier
    # rail intentionally enters the grip-side mounting envelope.  Do not
    # center, floor, rotate, or add a cosmetic separation here.
    objects = [grip, array]
    add_studio(objects)
    camera_for(objects, direction=(-1.5, -1.9, 1.05), margin=1.18, perspective=False)
    render(
        stem,
        "integration",
        "Native-coordinate four-finger array and attached carrier rail against the existing M grip STL",
    )
    blend_path = RENDERS / "onegrip_finger_input_grip_m_integration.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    RENDERED.append(
        {
            "file": blend_path.name,
            "category": "integration",
            "description": "Editable Blender 5 native-coordinate attached-rail integration scene",
            "geometry_inputs": [source_label(item) for item in sorted(SCENE_INPUTS, key=source_label)],
        }
    )


def write_manifest():
    expected = []
    for key in VARIANTS:
        expected.extend(
            f"variant_{key}_{i:02d}_{suffix}.png"
            for i, suffix in enumerate(
                (
                    "front", "side", "top", "fingertip_surrogate", "exploded", "switches",
                    "state_left", "state_center", "state_right",
                ),
                start=1,
            )
        )
    expected.extend(
        (
            "final_01_four_finger_array.png",
            "final_02_four_finger_array_with_surrogates.png",
            "final_03_grip_m_integration_preview.png",
            "onegrip_finger_input_grip_m_integration.blend",
        )
    )
    input_files = [input_record(path) for path in sorted(USED_INPUTS, key=source_label)]
    if SOURCE_SNAPSHOT:
        verify_source_snapshot(SOURCE_SNAPSHOT)
    manifest = {
        "schema": "onegrip-render-preview-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "resolution_px": [ARGS.resolution, ARGS.resolution],
        "engine": "BLENDER_EEVEE",
        "source_geometry": "Generated visualization-only STL cache; authoritative assemblies are STEP/3MF and render script does not alter core CAD",
        "motion_state_note": (
            "LEFT/CENTER/RIGHT images use visualization-only kinematic meshes with real key, follower, "
            "and switch travel. No conceptual state cue geometry is added."
        ),
        "exploded_view_note": "Exploded images use the actual exported separated printable-part STLs.",
        "switch_layout": {
            "preset": "middle",
            "coordinates_mm": {name: list(coords) for name, coords in SWITCH_POSITIONS.items()},
            "source": source_label(BUILD_MANIFEST),
        },
        "integration_note": (
            "Grip integration imports the visualization-only attached-rail mesh and the existing M grip "
            "at their native coordinates with no render-time placement transform."
        ),
        "input_files": input_files,
        "expected_outputs": expected,
        "outputs_written_this_run": RENDERED,
        "missing_outputs": [name for name in expected if not (RENDERS / name).exists()],
    }
    with open(RENDERS / "render_manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


def main():
    global SOURCE_SNAPSHOT
    SOURCE_SNAPSHOT = preflight_sources()
    for key in VARIANTS:
        render_variant_standard(key, "front", (0, -1, 0))
        render_variant_standard(key, "side", (1, 0, 0))
        render_variant_standard(key, "top", (0, 0, 1), up=(0, 1, 0))
        render_fingertip(key)
        render_exploded(key)
        render_switches(key)
        render_state(key, "left", 7)
        render_state(key, "center", 8)
        render_state(key, "right", 9)
    render_array()
    render_grip_integration()
    verify_source_snapshot(SOURCE_SNAPSHOT)
    write_manifest()
    print(f"[OneGrip render] completed {len(RENDERED)} outputs in {RENDERS}")


if __name__ == "__main__":
    main()
