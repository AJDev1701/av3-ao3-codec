# AV3 / AO3 Transport-Core Codec

**Authority:** Captain (`AJSX` / `AJDev1701`) | **Governance Spec:** `hexiq-gov/0.2.2` (`AGT001`) | **Classification:** `VERIFIED_SOURCE`

Deterministic byte-framing codec implementing the `AO3 Transport-Core Specification v1.0.2` for zero-drift, reproducible machine-to-machine data interchange. Features listed as deferred in `SPEC.md` (v1.1+) are not part of this release.

## Core Artifacts
- **`SPEC.md`:** Canonical `AO3 Transport-Core v1.0.2` framing specification.
- **`ao3_codec.py`:** Reference deterministic encoder/decoder implementation.
- **`SHA256MANIFEST.txt`:** SHA-256 digests of the committed files for local integrity verification.

## Build Provenance: `av3_testbench.exe`
- **What it is:** A prebuilt Windows x86-64 console test bench (89,080 bytes, SHA-256 `be17139c5952752a61f863640dd6a4b96feb1e5098feb62ada07f2ed062970b0`, listed in `SHA256MANIFEST.txt`). The same digest is recorded in the governance `LEDGER.md` (BLK-AV3-PHASE1, 2026-08-15).
- **Toolchain (`VERIFIED_SOURCE`, from strings embedded in the binary):** MinGW-w64 GCC 16.2.0, `-O2 -g`, `-march=x86-64`. Its debug information names `av3_vpu_testbench.cpp` as the source file.
- **Not verified:** The exact build command was not recorded, and the binary has not been checked as a reproducible build of the committed `reference/av3_vpu_testbench.cpp`. If you prefer not to run a prebuilt binary, build the test bench from that source file with your own C++ compiler.

## License & Support
- **Governance:** [`AJDev1701/universal-swarm-collaborative`](https://github.com/AJDev1701/universal-swarm-collaborative) (Inbound Gravity: Pull Requests Only)
- **License:** MIT License (`2026 Alex J. Dalhaus / HexiQ contributors`)
- **Support Open Research:** [Buy Me a Coffee (`ajdev1701`)](https://buymeacoffee.com/ajdev1701)
