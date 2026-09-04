$ErrorActionPreference = "Stop"
Set-Location "D:\workspace\av3-ao3-codec"

# 1. ao3_codec.py — recursive validation + full 8-test suite
$codecSource = @'
#!/usr/bin/env python3
"""
AO3 Transport-Core Reference Codec (v1.0.2)
RFC 8785 JCS + RFC 4648 S5 Base64URL + SHA-256
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
    if rem == 1: raise ValueError("Invalid Base64URL carrier length")
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
    try: canonical_bytes = decode_carrier(carrier)
    except ValueError: return False
    return compute_digest(canonical_bytes) == declared_h

def run_self_test() -> bool:
    all_pass = True

    # 1. S4 positive parity fixture
    fixture  = {"anchor":"AJX_CAPTAIN","c3":"NULL_UNWRITTEN","clock":"COLD_SHELF","test":"S4_PARITY_FIXTURE_001"}
    target_h = "2f9a5916cbf1fe643b2e8718556d9bea01ab55ef81ba330ef52bb0d7d4a8894d"
    env = build_envelope(fixture)
    if not (env["bytes"]==98 and env["L"]==131 and env["H"]==target_h and verify_envelope(env)):
        print("FAIL: S4 parity"); all_pass = False
    else: print("[+] T1 S4_PARITY: PASS")

    # 2. Positive nested roundtrip (PPLX requirement)
    nested = {"directive":{"assigned":["CPLX","GRKX"],"enabled":True},"meta":None}
    nenv = build_envelope(nested)
    if not verify_envelope(nenv):
        print("FAIL: nested roundtrip"); all_pass = False
    else: print("[+] T2 NESTED_ROUNDTRIP: PASS")

    # 3. Negative: empty carrier (PPLX requirement)
    try:
        decode_carrier(""); print("FAIL: empty carrier accepted"); all_pass = False
    except ValueError: print("[+] T3 EMPTY_CARRIER: PASS")

    # 4. Negative: nested int
    try:
        build_envelope({"data":{"count":42}}); print("FAIL: nested int"); all_pass = False
    except TypeError: print("[+] T4 NESTED_INT: PASS")

    # 5. Negative: non-BMP key
    try:
        build_envelope({"key_\U0001F600":"val"}); print("FAIL: non-BMP"); all_pass = False
    except ValueError: print("[+] T5 NON_BMP_KEY: PASS")

    # 6. Negative: whitespace
    try:
        decode_carrier(" "+env["carrier"]); print("FAIL: whitespace"); all_pass = False
    except ValueError: print("[+] T6 WHITESPACE: PASS")

    # 7. Negative: padding
    try:
        decode_carrier(env["carrier"]+"="); print("FAIL: padding"); all_pass = False
    except ValueError: print("[+] T7 PADDING: PASS")

    # 8. Negative: bad alphabet
    try:
        decode_carrier(env["carrier"].replace("-","+")); print("FAIL: bad alphabet"); all_pass = False
    except ValueError: print("[+] T8 ALPHABET: PASS")

    print()
    if all_pass: print("AO3_V102_ALL_TESTS_PASS")
    else: print("FAIL: one or more tests failed")
    return all_pass

if __name__ == "__main__":
    sys.exit(0 if run_self_test() else 1)
'@
[System.IO.File]::WriteAllText("$PWD\ao3_codec.py", $codecSource, (New-Object System.Text.UTF8Encoding $False))
Write-Host "[1] ao3_codec.py written (UTF-8 No BOM)"

# 2. SPEC.md — explicit max_depth=8 with depth-0 root definition
$specSource = @'
# AO3 Transport-Core Specification (v1.0.2)
**Spec:** 23XXA03 | **Pipeline:** AO3_1.0_7_STEP_FAIL_CLOSED | **Patch:** v1.0.2

## 1. Scope and Execution Boundary

AO3 is a deterministic transport framing protocol for zero-drift M2M data interchange.

### 1.1 Invariant Constraints (v1.0 Gate)

- **Supported types:** str, bool, None, list, dict (recursive, ASCII-only keys)
- **Recursive depth:** max_depth=8. Root dict is depth 0. Depth 9 triggers fail-closed.
- **Excluded (deferred to v1.1+):**
  - int, float
  - Non-BMP Unicode keys (U+10000+)
  - Duplicate member names
  - NaN, Infinity, -Infinity

## 2. Canonicalization (RFC 8785 JCS)

- Keys sorted by UTF-16 code unit value
- Compact separators: , and :
- ensure_ascii=False -- literal UTF-8

## 3. Encoding (RFC 4648 Section 5)

- URL-safe Base64 alphabet (- and _)
- Padding = strictly prohibited
- Whitespace is a hard error
- Non-canonical re-encoding rejected by round-trip check
- Empty carrier string is a hard error

## 4. Hashing Invariant

  canonical_bytes = JCS_Serialize(payload_dict)
  H = SHA256(canonical_bytes)
  carrier = Base64URL_Unpadded(canonical_bytes)
  L = len(carrier)

Rule: H computed over canonical_bytes only. Never hash the carrier string.

## 5. S4 Parity Fixture (Ratified)

Fixture ID: S4_PARITY_FIXTURE_001

Payload (canonical form):
{"anchor":"AJX_CAPTAIN","c3":"NULL_UNWRITTEN","clock":"COLD_SHELF","test":"S4_PARITY_FIXTURE_001"}

Bytes : 98
L     : 131
H     : 2f9a5916cbf1fe643b2e8718556d9bea01ab55ef81ba330ef52bb0d7d4a8894d

## 6. Test Matrix (8 assertions, all required for release gate)

T1  S4_PARITY_FIXTURE_001 positive match
T2  Nested object build + verify roundtrip
T3  Empty carrier rejection
T4  Nested int rejection
T5  Non-BMP key rejection
T6  Whitespace in carrier rejection
T7  Padding in carrier rejection
T8  Non-Base64URL character rejection

## 7. Patch Notes

v1.0.2: recursive validate_payload (max_depth=8), 8-test suite, empty carrier guard,
        deterministic manifest (hash  file, UTF-8 No BOM, lowercase hashes),
        SPEC max_depth formally documented.

*Spec 23XXA03 | AO3 v1.0.2 | Universal Swarm Collaborative*
'@
[System.IO.File]::WriteAllText("$PWD\SPEC.md", $specSource, (New-Object System.Text.UTF8Encoding $False))
Write-Host "[2] SPEC.md written (UTF-8 No BOM)"

# 3. stage_repo.ps1 — deterministic hash  file format, UTF-8 No BOM, lowercase
$stageScript = @'
$ErrorActionPreference = "Stop"
Set-Location "D:\workspace\av3-ao3-codec"
Write-Host "[*] Running codec self-test..."
python ao3_codec.py
if ($LASTEXITCODE -ne 0) { Write-Error "Codec test failed"; exit 1 }
Write-Host "[*] Generating deterministic SHA-256 manifest..."
$files = @("SPEC.md","ao3_codec.py","stage_repo.ps1")
$lines = foreach ($f in $files) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLowerInvariant()
    "$h  $f"
}
$utf8NoBom = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllLines("$PWD\SHA256MANIFEST.txt", $lines, $utf8NoBom)
Write-Host "[+] SHA256MANIFEST.txt written (UTF-8 No BOM, relative paths, lowercase hashes)"
'@
[System.IO.File]::WriteAllText("$PWD\stage_repo.ps1", $stageScript, (New-Object System.Text.UTF8Encoding $False))
Write-Host "[3] stage_repo.ps1 written (UTF-8 No BOM)"

# 4. Run self-test + generate manifest
Write-Host ""
python ao3_codec.py
if ($LASTEXITCODE -ne 0) { Write-Error "Self-test FAILED. Aborting."; exit 1 }

Write-Host ""
Write-Host "[*] Generating manifest..."
$files = @("SPEC.md","ao3_codec.py","stage_repo.ps1")
$lines = foreach ($f in $files) {
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLowerInvariant()
    "$h  $f"
}
$utf8NoBom = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllLines("$PWD\SHA256MANIFEST.txt", $lines, $utf8NoBom)
Write-Host "[+] Manifest:"
Get-Content SHA256MANIFEST.txt

# 5. Commit and push
git add SPEC.md ao3_codec.py stage_repo.ps1 SHA256MANIFEST.txt
git commit -m "feat(ao3): v1.0.2 final -- 8-test suite, recursive validator, deterministic manifest, no-BOM"
git push origin main
Write-Host ""
Write-Host "COMMIT_SHA: $(git rev-parse HEAD)"
