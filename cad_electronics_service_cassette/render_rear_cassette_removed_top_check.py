"""Top-view confirmation that the red-X rear cassette is absent in V2."""

from pathlib import Path

import bpy


HERE = Path(__file__).resolve().parent
MODEL = HERE / "export" / "ONEGRIP_STOCK_SPRING_BASE_CASSETTE_BODY_INTEGRATED_V4.stl"
OUTPUT = HERE / "rear_removed_flat_deck_top_check.png"


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=str(MODEL))
    part = bpy.context.selected_objects[0]
    part.name = "V4_RED_X_REMOVED_AND_RED_CIRCLE_DECK_FLAT"

    green = bpy.data.materials.new("Printed green")
    green.diffuse_color = (0.055, 0.52, 0.23, 1.0)
    part.data.materials.append(green)

    bpy.ops.object.camera_add(location=(0.0, 25.0, 230.0))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 170.0
    camera.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Top check world")
    scene.world.color = (0.055, 0.065, 0.075)
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUTPUT)
    bpy.ops.render.render(write_still=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
