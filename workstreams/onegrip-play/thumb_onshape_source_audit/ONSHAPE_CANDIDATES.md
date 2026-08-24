# ONSHAPE CANDIDATES

## Candidate A — exact saved version (selected)

| Field | Value |
|---|---|
| Document | `OneGrip_Play_V1` |
| DID | `a21e64f36bc61df760d4587c` |
| Version | `THUMB_LOWER15_HOUSING_V1` |
| VID | `50dfe4e752e447375b95493a` |
| Element / Part Studio | `Joystick` / `425d9199b59cfb1efd9ddc35` |
| Shell parts | `Joystick_1 / JaD`, `Joystick_2 / JfD` |
| Configuration | `default` |
| Transform | `(0,+12.25,-21.00) mm` |
| Outer skin | match |
| Openings | `JOY + T1–T8` present |
| Geometry | native exact solid B-rep, two shell halves inside a 30-solid Part Studio |
| Exact export | Parasolid and STEP offered per individual shell part |

Decision: **MOST LIKELY APPROVED SOURCE; authority proven.** The version is
immutable, its description matches the approved transform and inventory, and
the approved visual STL is directly traced to its `JaD/JfD` source state.

## Candidate B — current Main workspace

| Field | Value |
|---|---|
| Workspace | `Main` / `ef6a7b3ccc45186203e4d2ca` |
| Element | `Joystick` / `425d9199b59cfb1efd9ddc35` |
| Current inventory | 203 features / 22 parts |
| Geometry | later editable descendant |

Decision: **not the immutable authority.** The current workspace has later
Finger/carrier changes. It may retain the same shell topology, but the saved
LOWER15 version is the safer exact source.

## Candidate C — local LOWER15 STL pair

| Field | Value |
|---|---|
| Parts | `JaD`, `JfD` |
| Geometry | watertight tessellation only |
| Openings | approved `JOY + T1–T8` visible/measurable |
| Use | approved visual patch input and evidence |

Decision: **derived evidence, not exact authority.** Earlier audits correctly
classified these local files as mesh-only, but incorrectly stopped one level
too low in the lineage. Their upstream Onshape version is exact.

## Candidate D — reconstructed local exact STEP pair

| Field | Value |
|---|---|
| Files | `JAD_EXTERIOR_LOWERED_THUMB_V1.step`, `JFD_EXTERIOR_LOWERED_THUMB_V1.step` |
| Outer skin | near-match |
| Opening match | failed: T1/T3/JOY over-cut; T2/T4/T6/T7/T8 missing or partial |
| Geometry | exact local reconstruction, but not source-faithful opening topology |

Decision: **rejected as approved source.** Exact file format does not make the
reconstructed topology authoritative.

## Candidate E — `THUMB_LOWER15_PREWRITE`

Decision: **rejected.** It is the rollback checkpoint before the additional
lower-15 housing write and therefore cannot contain the final approved opening
position.

