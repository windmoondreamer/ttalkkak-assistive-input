# Third-party references

## Lalboard

The OneGrip Play finger-input design process reviewed the official Lalboard
project by JesusFreke:

- Source: <https://github.com/JesusFreke/lalboard>
- Official generated outputs: <https://github.com/JesusFreke/lalboard_stls>
- Copyright notices: Google LLC, 2019 and 2020
- License: Apache License 2.0

The reproducible analysis baseline is source commit
`1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a` (`v2.5.1`) together with the
exact output-submodule commit it records,
`282d61ae3a4d06d4dba2590779023b716da62b45` (`v2.5.1`). Output commit
`cfd0534cea86e86224ba42f4a193078c626f1d7f` was also inspected; the five
geometry artifacts used in the analysis are byte-identical at those two output
commits. Exact hashes and local checkout instructions are in
[`references/reference-lock.json`](references/reference-lock.json) and
[`references/README.md`](references/README.md).

OneGrip's CAD, source, and exported geometry are original and do not contain
copied Lalboard meshes or Python geometry. Lalboard was a design reference for
independent center/direction motion pairs, local pivots, concave fingertip
contacts, interference wells, and per-finger adjustment. This attribution is
provided for technical traceability; it does not imply endorsement by Google
or the Lalboard project.

If an upstream Lalboard source or geometry file is redistributed or modified,
include the Apache License 2.0 text, retain applicable copyright and attribution
notices, and mark modified files. A copy of the license is at
[`THIRD_PARTY_LICENSES/lalboard-Apache-2.0.txt`](THIRD_PARTY_LICENSES/lalboard-Apache-2.0.txt).

