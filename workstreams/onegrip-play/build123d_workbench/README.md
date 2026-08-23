# OneGrip build123d workbench

This isolated workbench carries the verified `FINGER_SIMPLIFIED_CARRIER_V1`
coordinates into a local, scriptable build123d baseline.

## Bootstrap

From the repository root in PowerShell:

```powershell
.\scripts\setup_build123d.ps1
```

## Rebuild exports

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.export_baseline
```

## Validate

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.smoke_test
```

## MIDDLE redesign

Build the exact OCC parts, run the local collision/assembly gates, and export
STEP/STL:

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.validate_middle_redesign
```

Create the six visual-QC images and the print-oriented six-part plate:

```powershell
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.render_middle_redesign
.\.venv-build123d\Scripts\python.exe -m build123d_workbench.prepare_middle_print_stl
```

The MIDDLE redesign is defined in `middle_redesign.py`; its manufacturing
parameters are grouped at the top of that module. It contains no Onshape
client code, and running these commands performs zero CAD writes.

Generated STEP/STL files and a JSON manifest are written to `out/` and are
intentionally ignored by Git. The exact Onshape source meshes remain in their
existing `exports/` directories and are never modified by this workbench.

The Python package is named `build123d_workbench` deliberately; a local module
named `build123d` would shadow the installed dependency.
