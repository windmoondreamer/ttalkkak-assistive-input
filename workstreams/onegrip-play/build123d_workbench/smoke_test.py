"""Dependency, geometry, source-file and STEP round-trip smoke test."""

from __future__ import annotations

import json
from math import isclose

import build123d
from build123d import import_step

from .export_baseline import OUT_DIR, export_all
from .model import build_all_carriers
from .source_of_truth import ONSHAPE_VERSION_ID, REFERENCE_MESHES


EXPECTED_COMPONENTS = {
    "JfD_RWID_carrier_extension": 10,
    "JaD_RZKD_carrier_extension": 3,
}


def main() -> None:
    assert build123d.__version__ == "0.11.1"
    assert ONSHAPE_VERSION_ID == "f51e9d9a868db9ef0fcd4b06"
    for name, path in REFERENCE_MESHES.items():
        assert path.is_file(), f"Missing reference mesh: {name}: {path}"

    manifest = export_all()
    for model in build_all_carriers():
        expected = EXPECTED_COMPONENTS[model.name]
        assert len(model.components) == expected
        assert len(model.compound.solids()) == expected
        assert model.compound.is_valid
        assert all(component.is_valid for component in model.components.values())
        assert all(component.volume > 0.0 for component in model.components.values())

        step_path = OUT_DIR / f"{model.name}.step"
        stl_path = OUT_DIR / f"{model.name}.stl"
        assert step_path.stat().st_size > 1_000
        assert stl_path.stat().st_size > 1_000
        round_trip = import_step(step_path)
        assert round_trip.is_valid
        assert len(round_trip.solids()) == expected
        assert isclose(round_trip.volume, model.volume, rel_tol=1e-9, abs_tol=1e-6)

    persisted = json.loads((OUT_DIR / "baseline_manifest.json").read_text("utf-8"))
    assert persisted["onshape_source"]["version_id"] == ONSHAPE_VERSION_ID
    assert persisted["models"].keys() == manifest["models"].keys()
    print(
        "PASS: build123d 0.11.1; 13 carrier solids; "
        "STEP/STL export and STEP round-trip verified"
    )


if __name__ == "__main__":
    main()
