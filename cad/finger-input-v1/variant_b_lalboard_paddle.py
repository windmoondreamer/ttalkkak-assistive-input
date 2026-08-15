"""Export selected Variant B (original OneGrip geometry)."""

from finger_module_common import PRESETS, VARIANTS, assembly_parts_variant_b, compound, export_bundle


if __name__ == "__main__":
    shape = compound(assembly_parts_variant_b(PRESETS["middle"], include_switches=False).values())
    export_bundle(shape, VARIANTS / "variant_b_lalboard_paddle")
