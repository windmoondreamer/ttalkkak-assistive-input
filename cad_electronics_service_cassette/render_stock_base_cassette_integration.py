"""Preview the cassette attached to the actual four-spring stock Base."""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
OUT = HERE / "export"
PARTS = HERE / "stock_gimbal_named_parts"
PREVIEW = HERE / "stock_base_cassette_integration_preview_v4.png"

INTEGRATED = OUT / "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_BODY_INTEGRATED_V4.stl"
LID = OUT / "ONEGRIP_ELECTRONICS_SERVICE_CASSETTE_LID_V4.stl"
BODY_CENTER_Y = -46.864
BASE_BOTTOM_Z = -28.099601
BODY_H = 12.0
LID_GAP = 0.20
EXPLODED_GAP = 7.0


def material(name: str, rgba: tuple[float, float, float, float]):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def import_stl(path: Path, name: str, mat):
    bpy.ops.wm.stl_import(filepath=str(path))
    obj = bpy.context.selected_objects[0]
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_spring_path(start, end, index, mat):
    curve = bpy.data.curves.new(f"SPRING_{index}", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.9
    curve.bevel_resolution = 4
    spline = curve.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (*start, 1.0)
    spline.points[1].co = (*end, 1.0)
    obj = bpy.data.objects.new(f"SPRING_{index}", curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    white = material("Fixed Base + cassette", (0.80, 0.83, 0.87, 1.0))
    black = material("Moving gimbal", (0.065, 0.075, 0.095, 1.0))
    orange = material("Removable lid", (0.95, 0.25, 0.055, 1.0))
    steel = material("Spring path", (0.22, 0.25, 0.30, 1.0))

    import_stl(INTEGRATED, "FIXED_BASE_AND_CASSETTE_ONE_SOLID", white)
    import_stl(PARTS / "Spring_holder.stl", "MOVING_SPRING_HOLDER", black)
    import_stl(PARTS / "Pitch.stl", "PITCH_AND_HANDLE_POST", black)
    lid = import_stl(LID, "REMOVABLE_LID_EXPLODED", orange)
    lid.location = (
        0.0,
        BODY_CENTER_Y,
        BASE_BOTTOM_Z + BODY_H + LID_GAP + EXPLODED_GAP,
    )

    base_points = [
        (-38.868, -15.273, -12.0),
        (38.868, -15.273, -12.0),
        (-38.868, 68.545, -12.0),
        (38.868, 68.545, -12.0),
    ]
    moving_points = [
        (-28.0, -3.0, 34.0),
        (28.0, -3.0, 34.0),
        (-28.0, 57.0, 34.0),
        (28.0, 57.0, 34.0),
    ]
    for index, (start, end) in enumerate(zip(base_points, moving_points, strict=True), 1):
        add_spring_path(start, end, index, steel)

    bpy.ops.object.light_add(type="AREA", location=(-130, -170, 190))
    key = bpy.context.object
    key.data.energy = 1400
    key.data.size = 120
    point_at(key, (0, 15, 0))
    bpy.ops.object.light_add(type="AREA", location=(160, 60, 130))
    fill = bpy.context.object
    fill.data.energy = 850
    fill.data.size = 100
    point_at(fill, (0, 15, 0))

    bpy.ops.object.camera_add(location=(165, -225, 175))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 215
    point_at(camera, (0, 20, 0))
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.curvature_ridge_factor = 1.8
    scene.display.shading.curvature_valley_factor = 1.2
    scene.world.color = (0.04, 0.045, 0.055)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1300
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW)
    bpy.ops.render.render(write_still=True)
    print(PREVIEW)


if __name__ == "__main__":
    main()
