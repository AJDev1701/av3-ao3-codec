# AO3 Transport-Core -- Reference Specification v1.0.1
**Spec:** 23XXA03 | **Pipeline:** AO3_1.0_7_STEP_FAIL_CLOSED
**Repo:** AJDev1701/av3-ao3-codec | **Patch:** v1.0.1 (2026-09-03)

---

## 1. Purpose

AO3 Transport-Core defines a deterministic, zero-dependency serialization and
integrity envelope for machine-to-machine payload exchange within the Universal
Swarm Collaborative. It guarantees canonical byte-exact reproducibility across
all nodes regardless of runtime environment.

---

## 2. Pipeline (7-Step Fail-Closed)

```
Step 1  Construct payload dict (ASCII strings, null, bool, arrays only)
Step 2  Canonicalize via RFC 8785 JCS -> UTF-8 bytes
Step 3  Compute H = SHA-256(canonical_bytes)
Step 4  Encode carrier = Base64URL(canonical_bytes), strip padding
Step 5  Measure L = len(carrier)
Step 6  Emit envelope {H, L, bytes, carrier}
Step 7  Verify: decode carrier -> re-canonicalize -> re-hash -> assert H match
```

**Invariant:** H is always computed over canonical UTF-8 bytes.
Never hash the Base64URL carrier string directly.

---

## 3. Canonicalization (RFC 8785 JCS)

- Keys sorted lexicographically by UTF-16 code unit value
- Compact separators: `","` and `":"`
- `ensure_ascii=False` -- literal UTF-8, no `\uXXXX` escapes
- Current scope: ASCII strings, null, bool, arrays
- Deferred: IEEE 754 floats, non-BMP keys (U+10000+)

---

## 4. Encoding (RFC 4648 Section 5)

- URL-safe Base64 alphabet (`-` and `_` replacing `+` and `/`)
- Padding character `=` **strictly prohibited** in emitted carrier
- Malformed carrier length (mod 4 == 1) is a hard error
- Whitespace in carrier is a hard error (no silent strip)
- Characters outside `[A-Za-z0-9_-]` are a hard error
- Non-canonical re-encoding (decoded bytes do not round-trip) is a hard error

---

## 5. S4 Parity Fixture (Ratified)

```
Payload : {"anchor":"AJX_CAPTAIN","c3":"NULL_UNWRITTEN",
            "clock":"COLD_SHELF","test":"S4_PARITY_FIXTURE_001"}
Bytes   : 98
L       : 131
H       : 2f9a5916cbf1fe643b2e8718556d9bea01ab55ef81ba330ef52bb0d7d4a8894d
```

All nodes must pass this fixture before any push is authorized.

---

## 6. Scope Boundaries

| Allowed          | Deferred                  |
|------------------|---------------------------|
| ASCII strings    | Non-BMP Unicode keys      |
| null, bool       | IEEE 754 floats           |
| Arrays of above  | Nested objects beyond depth 2 |
| dict (payload root) | Raw int/float values   |

**Type guard:** Python `bool` is a subclass of `int`. The validator checks
`bool` before `int` to allow `True`/`False` while rejecting raw integers.

---

## 7. Root Cause -- Ghost Object Eliminated

Previous Step 5 failures (WC-0710P, WC-1925A, WC-1110P) traced to hashing
an internal draft object at T-1 containing uncommitted template markers.

Fix: H is computed immediately after `canonicalize()`, before any further
string operations. `build_envelope()` enforces this order structurally.

---

## 8. v1.0.1 Patch Notes

- `decode_carrier`: whitespace now rejected outright (no silent `.strip()`)
- `decode_carrier`: strict `[A-Za-z0-9_-]` alphabet regex enforcement added
- `decode_carrier`: canonical re-encode round-trip check added
- `validate_payload`: added -- rejects raw int/float, allows bool and str
- SPEC.md: Unicode mojibake corrected; all arrows rendered as ASCII `->` or `--`
- SPEC.md: Section 4 heading corrected (`A5` -> `Section 5`)

---

*Spec 23XXA03 | AO3 v1.0.1 | Universal Swarm Collaborative*
