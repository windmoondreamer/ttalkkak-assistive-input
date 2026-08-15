"""Export the functional middle-finger Variant C comparator and states."""

from finger_module_common import PRESETS, VARIANTS, export_bundle
from functional_comparators import build_functional_comparators


if __name__ == "__main__":
    variant = build_functional_comparators(PRESETS["middle"])["variant_c"]
    export_bundle(variant["state_assemblies"]["neutral"], VARIANTS / "variant_c_rocker")
    for state, shape in variant["state_assemblies"].items():
        export_bundle(shape, VARIANTS / f"variant_c_{state}_assembly")
