# Revision log

## V1 — 2026-08-13

- Created three CAD-level mechanisms for direct switches, independent paddles,
  and a shared rocker.
- Selected independent paddles for P0; kept direct switches as the schedule
  fallback and excluded the shared rocker from V1.
- Replaced the preliminary pivoting center key with a two-post straight guide
  after checking the official Lalboard mechanism.
- Moved the two guide posts outside the 6.2mm center-switch envelope.
- Added a 0.62mm shell stop gap: 0.50mm maximum pretravel + 0.12mm controlled
  travel after click.
- Increased PETG side pivot holes to Ø2.4mm for Ø2.0mm shafts.
- Reduced center anti-loss cross holes to Ø1.1mm for Ø1.0mm pins, leaving at
  least 0.85mm nominal wall in the 2.8mm guide post.
- Added separate index, middle, ring, and pinky contact widths and lever ratios.
- Added screw-fastened bottom covers, rear wire channels, strain-relief exit,
  replaceable TPU pads, adjustable mount plates, ±8° wedges, P0 fixture, finger
  surrogates, and M-grip integration preview.
- Replaced the original long side-key actuator with a short rotary cam and an
  independent vertical follower, so the EVQ switch receives axial load only.
- Added full-travel retention clearance, switch-terminal relief, cable grooves,
  measured 0.1/0.2/0.3mm U-shims, true 16mm depth slots, and near-±8° wedges.
- Made Variant A and Variant C functional comparators rather than disconnected
  concept solids; all three mechanisms now have exported neutral/L/C/R states.
- Added the four-cartridge carrier rail and its actual module-hole interface.
- Restricted STL to individual printable parts. Multi-solid assemblies are
  distributed as STEP/3MF; flattened STL files live only in the explicitly
  non-authoritative `renders/geometry_cache/` preview cache.
- Added exact B-rep mechanism/interface validation, welded 2-manifold STL/3MF
  audits, provenance hashes, real-state Blender renders, and reproducible
  Lalboard source/output locks plus Apache-2.0 attribution.
