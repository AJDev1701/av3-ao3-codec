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