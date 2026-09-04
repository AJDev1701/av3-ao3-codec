# AO3 Transport-Core Specification (v1.0.2)
**Spec:** 23XXA03 | **Pipeline:** AO3_1.0_7_STEP_FAIL_CLOSED | **Patch:** v1.0.2

---

## 1. Scope and Execution Boundary

AO3 is a deterministic transport framing protocol for zero-drift M2M data interchange.

### 1.1 Invariant Constraints

- **Supported types:** str, bool, None, list, dict (recursive, ASCII keys only)
- **Recursive depth:** bounded at max_depth=8
- **Excluded (deferred to v1.1+):** int, float, non-BMP keys (U+10000+),
  duplicate member names, NaN/Infinity

---

## 2. Canonicalization (RFC 8785 JCS)

- Keys sorted by UTF-16 code unit value
- Compact separators: `,` and `:`
- ensure_ascii=False -- literal UTF-8, no \uXXXX escapes

---

## 3. Encoding (RFC 4648 Section 5)

- URL-safe Base64 alphabet (`-` and `_`)
- Padding `=` strictly prohibited in carrier
- Whitespace in carrier is a hard error
- Non-canonical re-encoding rejected by round-trip check

---

## 4. Hashing Invariant

```
canonical_bytes = JCS_Serialize(payload_dict)
H = SHA256(canonical_bytes)
carrier = Base64URL_Unpadded(canonical_bytes)
L = len(carrier)
```

Rule: H is computed over canonical_bytes only. Never hash the carrier string.

---

## 5. S4 Parity Fixture (Ratified)

Fixture ID: S4_PARITY_FIXTURE_001

Payload:
{"anchor":"AJX_CAPTAIN","c3":"NULL_UNWRITTEN","clock":"COLD_SHELF","test":"S4_PARITY_FIXTURE_001"}

Bytes : 98
L     : 131
H     : 2f9a5916cbf1fe643b2e8718556d9bea01ab55ef81ba330ef52bb0d7d4a8894d

---

## 6. v1.0.2 Patch Notes

- validate_payload(): recursive traversal replacing flat-dict-only check
- max_depth=8 guard prevents unbounded nesting
- Non-BMP key rejection added (ord(c) > 0xFFFF)
- Negative test suite: nested int, non-BMP key, whitespace, padding, bad alphabet
- stage_repo.ps1: relative leaf paths in SHA256MANIFEST.txt (no D:\workspace\... paths)
- SPEC.md: nested scope formally documented in S1.1

---

*Spec 23XXA03 | AO3 v1.0.2 | Universal Swarm Collaborative*