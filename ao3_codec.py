#!/usr/bin/env python3
"""
AO3 Transport-Core Reference Codec (v1.0.1)
Strict fail-closed pipeline: RFC 8785 JCS + RFC 4648 S5 Base64URL + SHA-256
Patch v1.0.1: whitespace rejection, alphabet guard, re-encode check, type guard.
Zero external dependencies. Spec: 23XXA03
"""

import base64
import hashlib
import json
import re
import sys

# Strict Base64URL alphabet — no padding, no whitespace
_B64URL_RE = re.compile(r'^[A-Za-z0-9_\-]+$')

# Allowed JSON value types — Python bool IS a subclass of int, so check bool first
_ALLOWED_TYPES = (str, bool, type(None), list)


def validate_payload(obj: dict) -> None:
    """
    Reject raw int/float values anywhere in the payload.
    Python bool is allowed (bool is subclass of int, so we check it first).
    Raises TypeError on violation.
    """
    if not isinstance(obj, dict):
        raise TypeError(f"Payload must be a dict, got {type(obj).__name__}")
    for k, v in obj.items():
        if not isinstance(k, str):
            raise TypeError(f"All keys must be str, got key {k!r}")
        if isinstance(v, bool):
            continue   # bool before int — allowed
        if isinstance(v, (int, float)):
            raise TypeError(
                f"Numeric types prohibited in AO3 payload. "
                f"Key {k!r} has value {v!r} ({type(v).__name__})"
            )
        if isinstance(v, list):
            for item in v:
                if isinstance(item, bool):
                    continue
                if isinstance(item, (int, float)):
                    raise TypeError(
                        f"Numeric types prohibited in list at key {k!r}"
                    )
        elif not isinstance(v, (str, type(None))):
            raise TypeError(
                f"Unsupported type {type(v).__name__} at key {k!r}"
            )


def canonicalize(obj: dict) -> bytes:
    """RFC 8785 JCS: sort_keys, compact separators, UTF-8, ensure_ascii=False."""
    validate_payload(obj)
    canonical_str = json.dumps(
        obj,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    )
    return canonical_str.encode('utf-8')


def encode_carrier(canonical_bytes: bytes) -> str:
    """RFC 4648 S5: unpadded Base64URL. '=' strictly prohibited in output."""
    return base64.urlsafe_b64encode(canonical_bytes).decode('ascii').rstrip('=')


def decode_carrier(carrier_str: str) -> bytes:
    """
    Decode unpadded Base64URL carrier.
    Fail-closed on:
      - any whitespace (no strip — reject outright)
      - padding character '='
      - characters outside Base64URL alphabet
      - malformed length (mod 4 == 1)
      - non-canonical re-encoding
    """
    # No silent strip — whitespace is a hard error
    if carrier_str != carrier_str.strip():
        raise ValueError(
            "Whitespace detected in carrier — injection rejected"
        )
    if '=' in carrier_str:
        raise ValueError(
            "Padding character '=' strictly prohibited in AO3 carrier"
        )
    if not _B64URL_RE.match(carrier_str):
        raise ValueError(
            "Carrier contains characters outside Base64URL alphabet [A-Za-z0-9_-]"
        )
    rem = len(carrier_str) % 4
    if rem == 1:
        raise ValueError("Malformed Base64URL carrier length (mod 4 == 1)")

    padding = '=' * ((4 - rem) % 4)
    decoded = base64.urlsafe_b64decode(carrier_str + padding)

    # Canonical re-encode check — decoded bytes must round-trip exactly
    re_encoded = base64.urlsafe_b64encode(decoded).decode('ascii').rstrip('=')
    if re_encoded != carrier_str:
        raise ValueError(
            "Carrier failed canonical re-encode check — non-canonical encoding rejected"
        )
    return decoded


def compute_digest(canonical_bytes: bytes) -> str:
    """SHA-256 hex digest over canonical UTF-8 bytes. NEVER hash the carrier."""
    return hashlib.sha256(canonical_bytes).hexdigest()


def build_envelope(payload_dict: dict) -> dict:
    """
    Canonical pipeline (order is the invariant):
      canonicalize -> compute_digest -> encode_carrier -> measure L -> emit
    """
    canonical_bytes = canonicalize(payload_dict)   # validate + serialize
    digest          = compute_digest(canonical_bytes)
    carrier         = encode_carrier(canonical_bytes)
    return {
        "H":       digest,
        "L":       len(carrier),
        "bytes":   len(canonical_bytes),
        "carrier": carrier
    }


def run_self_test() -> bool:
    """S4_PARITY_FIXTURE_001 + v1.0.1 guard tests."""
    all_pass = True

    # ── S4 parity fixture ────────────────────────────────────
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
    ok  = (env["H"] == expected_hash and
           env["L"] == expected_len  and
           env["bytes"] == expected_bytes)

    if ok:
        print("[+] S4 PARITY FIXTURE: PASS")
        print(f"    H={env['H']}")
        print(f"    L={env['L']}  bytes={env['bytes']}")
    else:
        print("[-] S4 PARITY FIXTURE: FAIL")
        all_pass = False

    # ── Whitespace rejection guard ───────────────────────────
    try:
        decode_carrier("eyJhbmNob3IiOiJBSlhfQ0FQVEFJTiJ9 ")  # trailing space
        print("[-] WHITESPACE GUARD: FAIL (should have raised)")
        all_pass = False
    except ValueError:
        print("[+] WHITESPACE GUARD: PASS")

    # ── Padding rejection guard ──────────────────────────────
    try:
        decode_carrier("eyJhbmNob3IiOiJBSlhfQ0FQVEFJTiJ9==")
        print("[-] PADDING GUARD: FAIL (should have raised)")
        all_pass = False
    except ValueError:
        print("[+] PADDING GUARD: PASS")

    # ── Alphabet guard ───────────────────────────────────────
    try:
        decode_carrier("eyJhbmNob3IiOiJBSlhfQ0FQVEFJTiJ9+/")
        print("[-] ALPHABET GUARD: FAIL (should have raised)")
        all_pass = False
    except ValueError:
        print("[+] ALPHABET GUARD: PASS")

    # ── Numeric type guard ───────────────────────────────────
    try:
        build_envelope({"key": 42})
        print("[-] INT TYPE GUARD: FAIL (should have raised)")
        all_pass = False
    except TypeError:
        print("[+] INT TYPE GUARD: PASS")

    # Bool is allowed (not a leakage)
    try:
        build_envelope({"flag": True})
        print("[+] BOOL ALLOWED: PASS")
    except TypeError:
        print("[-] BOOL ALLOWED: FAIL (bool should be permitted)")
        all_pass = False

    print()
    if all_pass:
        print("[+] STATUS: ALL GUARDS VERIFIED (v1.0.1 PASS)")
    else:
        print("[-] STATUS: ONE OR MORE GUARDS FAILED")
    return all_pass


if __name__ == "__main__":
    sys.exit(0 if run_self_test() else 1)
