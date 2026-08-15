"""Export the functional middle-finger Variant A comparator and states."""

from finger_module_common import PRESETS, VARIANTS, export_bundle
from functional_comparators import build_functional_comparators


if __name__ == "__main__":
    variant = build_functional_comparators(PRESETS["middle"])["variant_a"]
    export_bundle(variant["state_assemblies"]["neutral"], VARIANTS / "variant_a_direct_switch")
    for state, shape in variant["state_assemblies"].items():
        export_bundle(shape, VARIANTS / f"variant_a_{state}_assembly")
