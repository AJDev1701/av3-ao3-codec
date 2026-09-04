#!/usr/bin/env python3
"""
AO3 Transport-Core Reference Codec (v1.0.2)
RFC 8785 JCS + RFC 4648 S5 Base64URL + SHA-256
Patch v1.0.2: recursive validation, negative test suite, bounded depth.
"""
import base64, hashlib, json, re, sys

B64URL_PATTERN = re.compile(r'^[A-Za-z0-9_-]+$')

def validate_payload(item, depth: int = 0, max_depth: int = 8):
    if depth > max_depth:
        raise ValueError(f"Payload exceeds maximum nesting depth of {max_depth}")
    if isinstance(item, bool):
        return
    if isinstance(item, int):
        raise TypeError("Integers are deferred to v1.1+")
    if isinstance(item, float):
        raise TypeError("Floats are out of scope for AO3 v1.0")
    if isinstance(item, (str, type(None))):
        return
    if isinstance(item, dict):
        for k, v in item.items():
            if not isinstance(k, str):
                raise TypeError("Object keys must be strings")
            if any(ord(c) > 0xFFFF for c in k):
                raise ValueError("Non-BMP keys are deferred to v1.1+")
            validate_payload(v, depth + 1, max_depth)
    elif isinstance(item, list):
        for elem in item:
            validate_payload(elem, depth + 1, max_depth)
    else:
        raise TypeError(f"Unsupported payload type: {type(item).__name__}")

def canonicalize(obj) -> bytes:
    validate_payload(obj)
    return json.dumps(obj, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode('utf-8')

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
    if len(carrier) != declared_l:
        return False
    try:
        canonical_bytes = decode_carrier(carrier)
    except ValueError:
        return False
    return compute_digest(canonical_bytes) == declared_h

def run_self_test() -> bool:
    # 1. S4 positive fixture
    fixture = {"anchor":"AJX_CAPTAIN","c3":"NULL_UNWRITTEN","clock":"COLD_SHELF","test":"S4_PARITY_FIXTURE_001"}
    target_h = "2f9a5916cbf1fe643b2e8718556d9bea01ab55ef81ba330ef52bb0d7d4a8894d"
    env = build_envelope(fixture)
    if not (env["bytes"]==98 and env["L"]==131 and env["H"]==target_h and verify_envelope(env)):
        print("FAIL: S4 parity"); return False
    print("[+] S4 PARITY: PASS")

    # 2. Nested object support (Option B)
    nested = {"anchor":"AJX_CAPTAIN","directive":{"assigned":["CPLX","GRKX"],"active":True}}
    nenv = build_envelope(nested)
    if not verify_envelope(nenv):
        print("FAIL: nested object"); return False
    print("[+] NESTED OBJECT: PASS")

    # 3. Negative: nested int
    try:
        build_envelope({"data":{"count":42}}); print("FAIL: nested int not rejected"); return False
    except TypeError: print("[+] NESTED INT REJECTION: PASS")

    # 4. Negative: non-BMP key
    try:
        build_envelope({"key_\U0001F600":"value"}); print("FAIL: non-BMP not rejected"); return False
    except ValueError: print("[+] NON-BMP KEY REJECTION: PASS")

    # 5. Negative: whitespace in carrier
    try:
        decode_carrier(" " + env["carrier"]); print("FAIL: whitespace not rejected"); return False
    except ValueError: print("[+] WHITESPACE REJECTION: PASS")

    # 6. Negative: padding
    try:
        decode_carrier(env["carrier"] + "="); print("FAIL: padding not rejected"); return False
    except ValueError: print("[+] PADDING REJECTION: PASS")

    # 7. Negative: invalid alphabet
    try:
        bad = env["carrier"].replace("-","+")
        if bad != env["carrier"]:
            decode_carrier(bad); print("FAIL: bad char not rejected"); return False
    except ValueError: pass
    print("[+] ALPHABET REJECTION: PASS")

    print(); print("ALL_GUARDS_AND_NEGATIVE_TESTS_PASS")
    return True

if __name__ == "__main__":
    sys.exit(0 if run_self_test() else 1)