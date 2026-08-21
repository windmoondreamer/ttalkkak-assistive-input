# 오른손 핸들 STL 출력판 결과

## Source

- document: `a21e64f36bc61df760d4587c`
- workspace: `RIGHT_HAND_MIRROR`
- workspaceId: `db3d780eca8b1efe55a0dadd`
- Part Studio: `Joystick`
- elementId: `425d9199b59cfb1efd9ddc35`
- configuration: `default`
- source solid count: `30`

Onshape export 조건:

- binary STL
- millimeter
- fine resolution
- unique parts as individual files
- hidden parts included

## Packing policy

프로젝트 기록의 Bambu Lab P1S를 기준으로 했다.

- physical bed: `256 × 256 mm`
- reserved edge margin: `8 mm`
- packed-cell gap: `10 mm`
- 실제 geometry 최소 edge margin: `13 mm`
- 실제 geometry 최소 part clearance: `10 mm`

PCA, 주요 CAD 면 normal, world axis 후보를 비교해 각 파트를 낮고 안정적인 방향으로 눕혔다. 후보 중 최대 bed-contact area의 20% 이상을 확보하는 방향만 사용해 단순 최소 높이만 선택하는 오류를 막았다.

## Result

- build plates: `1`
- parts on plate: `30`
- disconnected STL components: `30`
- added/removed parts: `0 / 0`
- plate triangle count: `165,612`
- combined STL size: `8,280,684 bytes`
- combined STL SHA-256: `9DF047B3E161A1F1E1FBC990F88FEE9ADFE325784553F4A68F5F15F4FAF3F6C4`
- plate geometry bbox:
  - min: `[13.000, 13.000, 0.000] mm`
  - max: `[237.103, 233.091, 38.759] mm`
- overlap: `0`
- bed-boundary violations: `0`
- minimum-clearance violations: `0`

## Deliverables

- `exports/right_hand_handle_parts/plates/OneGrip_RightHand_Handle_plate_01_of_01.stl`
- `exports/right_hand_handle_parts/plates/OneGrip_RightHand_Handle_plate_01_layout.png`
- `exports/right_hand_handle_parts/plates/layout_manifest.json`
- `exports/right_hand_handle_parts/OneGrip_RightHand_Handle_Parts.zip`
- `exports/right_hand_handle_parts/OneGrip_RightHand_Handle_PrintSet.zip`
- `exports/right_hand_handle_parts/individual_stl/` — 30 source STL files
- `scripts/pack_right_hand_handle_stl.py`

## Verdict

- `RIGHT-HAND HANDLE STL = READY`
- `PLATE COUNT = 1`
- `PACKING SAFETY = PASS`
