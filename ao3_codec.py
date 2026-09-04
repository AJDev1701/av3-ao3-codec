#!/usr/bin/env python3
"""
AO3 Transport-Core Reference Codec (v1.0.2)
RFC 8785 JCS + RFC 4648 S5 Base64URL + SHA-256
Patch v1.0.2: recursive validation, 8-test suite, no-BOM output.
"""
import base64, hashlib, json, re, sys

B64URL_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')

def validate_payload(item, depth: int = 0, max_depth: int = 8):
    if depth > max_depth:
        raise ValueError(f"Payload exceeds maximum nesting depth of {max_depth}")
    if isinstance(item, bool): return
    if isinstance(item, int):   raise TypeError("Integers deferred to v1.1+")
    if isinstance(item, float): raise TypeError("Floats out of scope for AO3 v1.0")
    if isinstance(item, (str, type(None))): return
    if isinstance(item, dict):
        for k, v in item.items():
            if not isinstance(k, str): raise TypeError("Keys must be strings")
            if any(ord(c) > 0xFFFF for c in k): raise ValueError("Non-BMP keys deferred to v1.1+")
            validate_payload(v, depth + 1, max_depth)
    elif isinstance(item, list):
        for elem in item: validate_payload(elem, depth + 1, max_depth)
    else:
        raise TypeError(f"Unsupported type: {type(item).__name__}")

def canonicalize(obj) -> bytes:
    validate_payload(obj)
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

def encode_carrier(canonical_bytes: bytes) -> str:
    return base64.urlsafe_b64encode(canonical_bytes).decode('ascii').rstrip('=')

def decode_carrier(carrier_str: str) -> bytes:
    if not isinstance(carrier_str, str) or not carrier_str:
        raise ValueError("Carrier must be a non-empty string")
    if carrier_str != carrier_str.strip():
        raise ValueError("Whitespace prohibited in carrier")
    if '=' in carrier_str:
        raise ValueError("'=' padding prohibited in AO3 carrier")
    if not B64URL_PATTERN.match(carrier_str):
        raise ValueError("Invalid Base64URL character detected")
    rem = len(carrier_str) % 4
    if rem == 1:
        raise ValueError("Invalid Base64URL carrier length")
    padding = '=' * ((4 - rem) % 4)
    decoded = base64.urlsafe_b64decode(carrier_str + padding)
    if encode_carrier(decoded) != carrier_str:
        raise ValueError("Non-canonical Base64URL encoding")
    return decoded

def compute_digest(canonical_bytes: bytes) -> str:
    return hashlib.sha256(canonical_bytes).hexdigest()

def build_envelope(payload_dict: dict) -> dict:
    canonical_bytes = canonicalize(payload_dict)
    carrier = encode_carrier(canonical_bytes)
    digest  = compute_digest(canonical_bytes)
    return {"H": digest, "L": len(carrier), "bytes": len(canonical_bytes), "carrier": carrier}

def verify_envelope(envelope: dict) -> bool:
    carrier    = envelope.get("carrier", "")
    declared_h = envelope.get("H", "")
    declared_l = envelope.get("L", -1)
    if len(carrier) != declared_l: return False
    try:
        canonical_bytes = decode_carrier(carrier)
    except ValueError:
        return False
    return compute_digest(canonical_bytes) == declared_h

def run_self_test() -> bool:
    all_pass = True

    # T1: S4 positive parity fixture
    fixture  = {"anchor": "AJX_CAPTAIN", "c3": "NULL_UNWRITTEN",
                "clock": "COLD_SHELF", "test": "S4_PARITY_FIXTURE_001"}
    target_h = "2f9a5916cbf1fe643b2e8718556d9bea01ab55ef81ba330ef52bb0d7d4a8894d"
    env = build_envelope(fixture)
    if env["bytes"]==98 and env["L"]==131 and env["H"]==target_h and verify_envelope(env):
        print("[+] T1 S4_PARITY: PASS")
    else:
        print("[-] T1 S4_PARITY: FAIL"); all_pass = False

    # T2: Positive nested roundtrip (PPLX requirement)
    nested = {"directive": {"assigned": ["CPLX", "GRKX"], "enabled": True}, "meta": None}
    nenv = build_envelope(nested)
    if verify_envelope(nenv):
        print("[+] T2 NESTED_ROUNDTRIP: PASS")
    else:
        print("[-] T2 NESTED_ROUNDTRIP: FAIL"); all_pass = False

    # T3: Negative — empty carrier (PPLX requirement)
    try:
        decode_carrier("")
        print("[-] T3 EMPTY_CARRIER: FAIL"); all_pass = False
    except ValueError:
        print("[+] T3 EMPTY_CARRIER: PASS")

    # T4: Negative — nested int
    try:
        build_envelope({"data": {"count": 42}})
        print("[-] T4 NESTED_INT: FAIL"); all_pass = False
    except TypeError:
        print("[+] T4 NESTED_INT: PASS")

    # T5: Negative — non-BMP key
    try:
        build_envelope({"key_\U0001F600": "val"})
        print("[-] T5 NON_BMP_KEY: FAIL"); all_pass = False
    except ValueError:
        print("[+] T5 NON_BMP_KEY: PASS")

    # T6: Negative — whitespace in carrier
    try:
        decode_carrier(" " + env["carrier"])
        print("[-] T6 WHITESPACE: FAIL"); all_pass = False
    except ValueError:
        print("[+] T6 WHITESPACE: PASS")

    # T7: Negative — padding character
    try:
        decode_carrier(env["carrier"] + "=")
        print("[-] T7 PADDING: FAIL"); all_pass = False
    except ValueError:
        print("[+] T7 PADDING: PASS")

    # T8: Negative — invalid Base64URL alphabet ('+' is standard b64 but not URL-safe)
    # Use a hardcoded string containing '+' — guaranteed to trigger alphabet guard
    try:
        decode_carrier("eyJhbmNob3IiOiJBSlhfQ0FQVEFJTiIs+mMzIjoiTlVMTF9VTldSSVRURU4i")
        print("[-] T8 ALPHABET: FAIL"); all_pass = False
    except ValueError:
        print("[+] T8 ALPHABET: PASS")

    print()
    if all_pass:
        print("AO3_V102_ALL_TESTS_PASS")
    else:
        print("FAIL: one or more tests failed")
    return all_pass

if __name__ == "__main__":
    sys.exit(0 if run_self_test() else 1)
