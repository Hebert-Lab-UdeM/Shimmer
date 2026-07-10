# Shimmer

Unified acquisition code for the Shimmer family of wireless biosignal devices.

This repository holds two generations of acquisition code, separated by device
family and project era:

| Folder            | Device  | Era   | Description                                       |
| ----------------- | ------- | ----- | ------------------------------------------------- |
| `Shimmer3-2022/`  | Shimmer3 | 2022+ | Legacy Shimmer3 acquisition code (Realterm-based). |
| `Shimmer3R-2026/` | Shimmer3R | 2026+ | Active acquisition code for the STM32U5A5 / CYW20820 platform. |

The `2022` stamp on the legacy folder refers to the project lineage (Shimmer3
adoption at the Hebert Lab), not the last-modified date of any file.

## Per-folder layout

Both `Shimmer3-2022/matlab/` and `Shimmer3R-2026/matlab/` use the same
sub-folder shape:

```
matlab/
  StreamShimmer*.m       top-level acquisition script
  shimmer_bridge.m       bridge layer (legacy only)
  data/                  runtime dataset captures (gitignored contents)
  examples/              worked-example scripts
  params/                config-time parameter objects
  reference/             archived historical scripts (legacy only)
  requirements/          third-party installers (legacy only — Realterm)
  resources/
    docs/                PDF user guides and instrument manuals
    libs/                Java JAR runtime libraries
    helpers/             supporting .m files
    Sampling Rate Table.txt
```

`Shimmer3R-2026/python/` is the placeholder for the Python implementation
phases described in `specs/shimmer3r-gsr-ppg-streaming/prd.md` (Phase 2:
pyshimmer, Phase 3: bleak). The legacy folder does not include a `python/`
subfolder because the legacy code is MATLAB-only.

## Excluded artefacts

The following materials are intentionally **not** tracked in this repository:

- `vibration_bridge.m` and `Pulse_Vibreur_Stress_Calorique.m` — vestibular
  stimulation code, not Shimmer acquisition.
- Per-session runtime logs (`log_files/*.log`, top-level `shimmer_*.log`).
- Raw serial captures (`realtermBuffer/*.dat`).
- The 471 MB LSL-recorded dataset `subj-B_789.xdf`.
- Per-development error logs in `examples/`.

## Lab Streaming Layer (LSL) Setup

Both MATLAB implementations bundle the LSL MATLAB bindings directly:

- **Shimmer3-2022**: `matlab/LSL/`
- **Shimmer3R-2026**: `matlab/LSL/`

The bindings are copied from https://github.com/labstreaminglayer/liblsl-Matlab

To update LSL:
```bash
cd Shimmer3-2022/matlab/LSL
git pull
```
