"""The one canonical-JSON form, in one place.

WHY THIS EXISTS

`json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False).encode("utf-8")` was written out by hand in **58 modules** of this
tree, with byte-identical bodies. It is the hashing key for every receipt, every
certificate and every proof atom in the repository.

That is not merely duplication. A digest key is a *contract between producers*: two
modules that canonicalise differently produce different hashes for the same fact, and
the mismatch only shows up as a failed verification much later. Eight of the 58 had
already drifted into different bodies before this module existed.

BEST PART IS NO PART

No new behaviour, no new options, no configurable separator. One function, one body,
identical to the 58 it replaces. Modules that called a local `_canon` keep working:
their local definition is replaced by an import of this one, so every call site is
unchanged and the byte-for-byte semantics are preserved.

`canonical_sha256` is provided because 27 of those same files also wrote `_sha` by
hand; it is the same function composed with sha256, not a second convention.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "PROJECT_BRAIN_CANONICAL_FORM_V1"


def canonical_bytes(value: Any) -> bytes:
    """The canonical UTF-8 encoding of a JSON-representable value.

    Sorted keys, no insignificant whitespace, UTF-8 preserved, NaN refused.
    This is the exact body that was duplicated in 58 modules.
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Hex sha256 of :func:`canonical_bytes`."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


# Short name for modules that used `_canon` at 124 call sites.
_canon = canonical_bytes
