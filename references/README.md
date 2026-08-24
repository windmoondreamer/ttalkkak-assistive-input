# Lalboard reference snapshots

The OneGrip CAD is original work. These directories are read-only upstream
checkouts retained only to make the Lalboard mechanism analysis reproducible.
They are intentionally ignored by the outer OneGrip repository; run
`fetch_lalboard_references.ps1` to recreate and verify them.

## Analysis baseline (source and its matching submodule)

| Local path | Official repository | Ref | Locked commit |
|---|---|---|---|
| `lalboard-v2.5.1/` | <https://github.com/JesusFreke/lalboard> | `v2.5.1` | `1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a` |
| `lalboard-v2.5.1/stls/` | <https://github.com/JesusFreke/lalboard_stls> | `v2.5.1` | `282d61ae3a4d06d4dba2590779023b716da62b45` |

The source tree at `1fb8e6b` records the `stls` gitlink as exactly `282d61a`.
This pair is therefore the reproducible v2.5.1 source/output baseline.

## Later official snapshots retained for comparison

| Local path | Official repository | Ref | Locked commit |
|---|---|---|---|
| `lalboard/` | <https://github.com/JesusFreke/lalboard> | `main` at inspection time | `eddf521062c8e6eb5e67b05d071c60f093652c0a` |
| `lalboard-stls-main/` | <https://github.com/JesusFreke/lalboard_stls> | `main` at inspection time | `cfd0534cea86e86224ba42f4a193078c626f1d7f` |

The retained source `main@eddf521` records its `stls` gitlink as exactly
`cfd0534`; the verification script checks this relation too.

`lalboard-stls-v2.5.1/` may also exist locally as a standalone copy of
`282d61a`; it is redundant with `lalboard-v2.5.1/stls/` and is not required.

The five geometry files used by the analysis have identical SHA-256 hashes at
`282d61a` and `cfd0534`; see `reference-lock.json`. No claim is made that every
file in those two output commits is identical.

## Verify/recreate

```powershell
powershell -ExecutionPolicy Bypass -File references/fetch_lalboard_references.ps1
```

The script never deletes or overwrites a directory. If an existing checkout is
at a different commit it stops and reports the mismatch.

## Licensing

The Lalboard source carries Apache License 2.0 notices and copyright notices
for Google LLC (2019 and, in individual files, 2020). The upstream source
snapshot has no separate `NOTICE` file. The output repository has no separate
license file, so this project treats those official generated artifacts as
object-form Lalboard material and accompanies any redistributed upstream
artifact with the parent source attribution and Apache-2.0 license.

OneGrip does not copy the upstream meshes or Python geometry into its CAD.
See [`../NOTICE-THIRD-PARTY.md`](../NOTICE-THIRD-PARTY.md) and
[`../THIRD_PARTY_LICENSES/lalboard-Apache-2.0.txt`](../THIRD_PARTY_LICENSES/lalboard-Apache-2.0.txt).
