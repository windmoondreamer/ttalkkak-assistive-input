"""Render the actual moving spring plate from the stock-gimbal STEP."""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
PARTS = HERE / "stock_gimbal_named_parts"
PREVIEW = HERE / "stock_gimbal_spring_plate_identification.png"


def material(name: str, rgba: tuple[float, float, float, float]):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def import_stl(filename: str, name: str, mat):
    bpy.ops.wm.stl_import(filepath=str(PARTS / filename))
    obj = bpy.context.selected_objects[0]
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    fixed = material("Fixed stock base", (0.72, 0.74, 0.78, 1.0))
    moving = material("Actual moving spring plate", (0.95, 0.24, 0.06, 1.0))
    pitch_mat = material("Pitch attachment", (0.18, 0.20, 0.24, 1.0))

    import_stl("Base.stl", "FIXED_BASE_WITH_FOUR_SPRING_HOOKS", fixed)
    import_stl("Spring_holder.stl", "MOVING_SPRING_PLATE", moving)
    import_stl("Pitch.stl", "HANDLE_PITCH_ATTACHMENT", pitch_mat)

    # Thin guide lines make the four spring load paths legible without
    # pretending to model the team's exact physical coil spring.
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
    spring_mat = material("Spring load path", (0.07, 0.09, 0.12, 1.0))
    for index, (start, end) in enumerate(zip(base_points, moving_points, strict=True), 1):
        curve = bpy.data.curves.new(f"SPRING_PATH_{index}", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = 0.75
        curve.bevel_resolution = 3
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*start, 1.0)
        spline.points[1].co = (*end, 1.0)
        obj = bpy.data.objects.new(f"SPRING_PATH_{index}", curve)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(spring_mat)

    bpy.ops.object.light_add(type="AREA", location=(-120, -140, 190))
    key = bpy.context.object
    key.data.energy = 1300
    key.data.size = 110
    point_at(key, (0, 27, 5))
    bpy.ops.object.light_add(type="AREA", location=(140, 90, 130))
    fill = bpy.context.object
    fill.data.energy = 800
    fill.data.size = 100
    point_at(fill, (0, 27, 5))

    bpy.ops.object.camera_add(location=(150, -185, 170))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 190
    point_at(camera, (0, 35, 5))
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
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW)
    bpy.ops.render.render(write_still=True)
    print(PREVIEW)


if __name__ == "__main__":
    main()
