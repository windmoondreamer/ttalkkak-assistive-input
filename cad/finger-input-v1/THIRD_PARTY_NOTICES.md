# Third-party references

## Lalboard

OneGrip Play's finger-module development reviewed the official Lalboard project:

- Source: <https://github.com/JesusFreke/lalboard>
- Upstream copyright: Copyright 2019–2020 Google LLC
- License: Apache License 2.0
- Inspected source commit: `1fb8e6bb635c71bbfc0d4a00655aeb42aec14f5a`
- Matching v2.5.1 output-submodule commit: `282d61ae3a4d06d4dba2590779023b716da62b45`
- Separately inspected later output commit: `cfd0534cea86e86224ba42f4a193078c626f1d7f`

The source and geometry in `cad/finger-input-v1/` are an original OneGrip
implementation. No Lalboard mesh or Python geometry was copied. Lalboard was
used to understand the independently moving center and direction keys, local
pivots, concave fingertip contact, anti-interference wells, and per-finger
adjustability. OneGrip removes the optical sensing, magnets, custom PCB, north
and south keys, and three-point magnetic mounts.

The exact analysis pair is kept separately under
`references/lalboard-v2.5.1/` and `references/lalboard-v2.5.1/stls/`. The
current-main comparison checkouts are `references/lalboard/` and
`references/lalboard-stls-main/`. These nested Git checkouts are ignored by the
outer project and are recreated and verified by
`references/fetch_lalboard_references.ps1`; exact commits and SHA-256 hashes are
recorded in `references/reference-lock.json`.

If upstream source or geometry is later copied or modified into a deliverable,
include the upstream Apache-2.0 license text, preserve its notices, and mark the
modified files. The project-level notice and license copy are
`NOTICE-THIRD-PARTY.md` and
`THIRD_PARTY_LICENSES/lalboard-Apache-2.0.txt`. See
`docs/lalboard_analysis.md` for the distribution checklist.
