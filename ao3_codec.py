#!/usr/bin/env python3
"""
AO3 Transport-Core Reference Codec (v1.0)
Strict fail-closed pipeline: RFC 8785 JCS + RFC 4648 S5 Base64URL + SHA-256
Zero external dependencies.
Spec: 23XXA03 | Pipeline: AO3_1.0_7_STEP_FAIL_CLOSED
"""

import base64
import hashlib
import json
import sys


def canonicalize(obj) -> bytes:
    """RFC 8785 JCS: sort_keys=True, compact separators, UTF-8 output."""
    canonical_str = json.dumps(
        obj,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    )
    return canonical_str.encode('utf-8')


def encode_carrier(canonical_bytes: bytes) -> str:
    """RFC 4648 S5: unpadded Base64URL — '=' strictly prohibited."""
    return base64.urlsafe_b64encode(canonical_bytes).decode('ascii').rstrip('=')


def decode_carrier(carrier_str: str) -> bytes:
    """Decode unpadded Base64URL; reject padding and malformed lengths."""
    carrier_str = carrier_str.strip()
    if '=' in carrier_str:
        raise ValueError("Padding character '=' strictly prohibited in AO3 carrier")
    rem = len(carrier_str) % 4
    if rem == 1:
        raise ValueError("Malformed Base64URL carrier length")
    padding = '=' * ((4 - rem) % 4)
    return base64.urlsafe_b64decode(carrier_str + padding)


def compute_digest(canonical_bytes: bytes) -> str:
    """SHA-256 over canonical UTF-8 bytes. NEVER hash the carrier string."""
    return hashlib.sha256(canonical_bytes).hexdigest()


def build_envelope(payload_dict: dict) -> dict:
    """Canonical pipeline: canonicalize -> digest -> encode -> measure."""
    canonical_bytes = canonicalize(payload_dict)
    carrier         = encode_carrier(canonical_bytes)
    digest          = compute_digest(canonical_bytes)
    return {
        "H":       digest,
        "L":       len(carrier),
        "bytes":   len(canonical_bytes),
        "carrier": carrier
    }


def run_self_test() -> bool:
    """S4_PARITY_FIXTURE_001 — ratified across all active nodes."""
    fixture_payload = {
        "anchor": "AJX_CAPTAIN",
        "c3":     "NULL_UNWRITTEN",
        "clock":  "COLD_SHELF",
        "test":   "S4_PARITY_FIXTURE_001"
    }
    expected_hash  = "2f9a5916cbf1fe643b2e8718556d9bea01ab55ef81ba330ef52bb0d7d4a8894d"
    expected_len   = 131
    expected_bytes = 98

    env = build_envelope(fixture_payload)

    ok = (env["H"]     == expected_hash  and
          env["L"]     == expected_len   and
          env["bytes"] == expected_bytes)

    if ok:
        print("[+] STATUS: S4 PARITY VERIFIED (PASS)")
        print(f"    H={env['H']}")
        print(f"    L={env['L']}  bytes={env['bytes']}")
    else:
        print("[-] STATUS: S4 PARITY FAILED")
        print(f"    H got={env['H']} want={expected_hash}")
        print(f"    L got={env['L']} want={expected_len}")
        print(f"    bytes got={env['bytes']} want={expected_bytes}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run_self_test() else 1)
