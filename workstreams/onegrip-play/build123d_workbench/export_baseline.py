"""Export the local OneGrip build123d baseline to STEP, STL and JSON."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build123d
from build123d import Shape, export_step, export_stl

from .model import CarrierModel, back_node, build_all_carriers
from .source_of_truth import (
    CAP_EXPOSURE,
    CAP_OPENING,
    CAP_SIZE,
    HOLDER_FRONT_TRIM,
    INDEX,
    MIDDLE,
    MIDDLE_POCKET,
    ONSHAPE_URL,
    ONSHAPE_VERSION_ID,
    ONSHAPE_VERSION_NAME,
    REFERENCE_MESHES,
)


OUT_DIR = Path(__file__).resolve().parent / "out"


def _vector(vector: Any) -> list[float]:
    return [float(vector.X), float(vector.Y), float(vector.Z)]


def _shape_metrics(shape: Shape) -> dict[str, Any]:
    bbox = shape.bounding_box()
    return {
        "valid": bool(shape.is_valid),
        "volume_mm3": float(shape.volume),
        "solid_count": len(shape.solids()),
        "bbox_mm": {"min": _vector(bbox.min), "max": _vector(bbox.max)},
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model_manifest(model: CarrierModel) -> dict[str, Any]:
    return {
        "retainer_owner": model.retainer_name,
        "compound": _shape_metrics(model.compound),
        "component_volume_sum_mm3": model.volume,
        "components": {
            name: _shape_metrics(shape) for name, shape in model.components.items()
        },
    }


def export_all(out_dir: Path = OUT_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    models = build_all_carriers()
    for model in models:
        export_step(model.compound, out_dir / f"{model.name}.step")
        export_stl(
            model.compound,
            out_dir / f"{model.name}.stl",
            tolerance=0.03,
            angular_tolerance=0.08,
        )

    references: dict[str, Any] = {}
    for name, path in REFERENCE_MESHES.items():
        references[name] = {
            "path": str(path.relative_to(path.parents[2])
                        if name.endswith("shell") else path.relative_to(path.parents[3])),
            "absolute_path": str(path),
            "exists": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
            "sha256": _sha256(path) if path.is_file() else None,
            "role": "mesh reference only; not treated as editable B-rep",
        }

    manifest = {
        "schema": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "units": "mm",
        "build123d_version": build123d.__version__,
        "onshape_source": {
            "version_name": ONSHAPE_VERSION_NAME,
            "version_id": ONSHAPE_VERSION_ID,
            "url": ONSHAPE_URL,
        },
        "button_datums": {
            button.name: {
                "center_mm": button.center,
                "axis": button.axis,
                "shell_normal": button.normal,
                "back_node_mm": back_node(button),
            }
            for button in (*INDEX, *MIDDLE)
        },
        "external_language": {
            "middle_pocket_mm": MIDDLE_POCKET,
            "cap_opening_mm": CAP_OPENING,
            "cap_size_mm": CAP_SIZE,
            "cap_exposure_mm": CAP_EXPOSURE,
            "holder_front_trim_mm": HOLDER_FRONT_TRIM,
        },
        "models": {model.name: _model_manifest(model) for model in models},
        "reference_meshes": references,
    }
    manifest_path = out_dir / "baseline_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    manifest = export_all()
    print(f"build123d {manifest['build123d_version']}")
    print(f"source {manifest['onshape_source']['version_name']} "
          f"{manifest['onshape_source']['version_id']}")
    for name, data in manifest["models"].items():
        print(
            f"{name}: {data['compound']['solid_count']} solids, "
            f"{data['component_volume_sum_mm3']:.6f} mm^3"
        )
    print(f"exports {OUT_DIR}")


if __name__ == "__main__":
    main()
