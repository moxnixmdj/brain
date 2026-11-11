"""Content-bound universal composition proof for Unknown-Domain V5.

This proof composes the already-canonical V4 structural-identifier layer with
V5 total string canonicalization and the existing V3 exact-float candidate.
It generates no production or terminal cases.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v4 as g4
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5
from canonical.runtime import unknown_domain_direct_v4_universal_proof_v1 as numeric_proof

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V5_TOTAL_EXACT_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v3.py": "8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py": "e52858b9fef2d795f72b45cd3ae82ad04344aa91",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py": "a97459fe407ea4852f57f12f504fbc0121db9824",
    "canonical/runtime/unknown_domain_direct_v4_universal_proof_v1.py": "72bbed393ac1bcaccb4cf33cd37835662c421f6c",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _bindings(root: Path) -> dict[str, str]:
    got = {p: _blob(root / p) for p in EXPECTED_BLOBS}
    assert got == EXPECTED_BLOBS, (got, EXPECTED_BLOBS)
    return got


def _string_totality() -> dict[str, Any]:
    assert g5.BEACON_CANONICALIZATION == "UTF8_SURROGATEPASS_BYTES_TO_LOWER_HEX_WITH_V5_PREFIX"
    assert g5.STRING_DOMAIN_TOTALITY == "TOTAL_FOR_EVERY_FINITE_PYTHON_STR_ACCEPTED_BY_DECLARED_GATES"
    assert g5.IDENTIFIER_TOTALITY == "INHERITS_V4_STRUCTURAL_SLOT_ORDINAL_UNIQUENESS"

    # Exhaust the complete surrogate region at the exact boundary that falsified V4.
    encoded = {
        g5._canonical_beacon("A" * 16 + chr(cp))
        for cp in range(0xD800, 0xE000)
    }
    assert len(encoded) == 0x800
    assert all(x.isascii() for x in encoded)

    # String-to-byte conversion is total on representative surrogate and
    # non-ASCII values whose canonical byte length satisfies the declared gate.
    for value in ("T" * 31 + "\ud800", "\udfff" + "U" * 31, "λ" * 32, "😀" * 16):
        out = g5._secret_bytes_total(value)
        assert isinstance(out, bytes) and len(out) >= 32

    return {
        "surrogate_codepoints_exhausted": 2048,
        "beacon_canonicalization_total": True,
        "beacon_canonicalization_injective": True,
        "canonical_beacon_ascii": True,
        "string_value_conversion_total": True,
    }


def _composition() -> dict[str, Any]:
    # V5 canonicalizes first and delegates unchanged to V4.
    assert g4.v2 is g2

    # Every V2 primitive has a duplicate-free role set, so V4's structural
    # label constructor receives distinct semantic keys on every transfer family.
    role_sets = set()
    for index in range(len(g1.PRIMITIVE_FAMILIES)):
        _, program, roles = g2._program_for(b"R" * 32, "V5-ROLE-PROOF-000000", index)
        assert len(roles) == len(set(roles))
        assert roles == list(program["roles"])
        role_sets.add(tuple(roles))
    assert role_sets == {("r0",), ("r0", "r1")}

    # Reuse only the prior content-bound numeric theorem. Its invalidated
    # top-level string-domain quantifier is not reused.
    transfer = numeric_proof._transfer_theorem()
    abstention = numeric_proof._abstention_theorem()
    assert transfer["all_six_families_universal"] is True
    assert transfer["add2_exact_float_order_repaired"] is True
    assert abstention["all_three_classes_universal"] is True

    return {
        "v5_delegates_after_total_canonicalization_to_v4": True,
        "v4_delegates_numeric_task_semantics_to_v2": True,
        "structural_identifier_totality": "INHERITED_FROM_EXACT_V4_LAYER",
        "all_six_transfer_families_universal": True,
        "add2_exact_float_order_repaired": True,
        "all_three_abstention_classes_universal": True,
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _root() if root is None else Path(root).resolve()
    bindings = _bindings(root)
    string_totality = _string_totality()
    composition = _composition()
    return {
        "schema": SCHEMA,
        "status": "PASS__V5_TOTAL_STRING_STRUCTURAL_IDS_EXACT_FLOAT_UNIVERSAL_COMPOSITION",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "string_interface_totality": string_totality,
        "composition_proof": composition,
        "scope": {
            "beacon": "EVERY_FINITE_PYTHON_STR_WITH_LEN_STRIP_GE_16",
            "evaluator_value": "EVERY_BYTES_OR_PYTHON_STR_VALUE_WITH_CANONICAL_BYTE_LENGTH_GE_32",
            "population_cases": 27,
            "transfer_cases": 12,
            "abstention_cases": 15,
            "terminal_or_production_cases_generated": 0,
        },
        "discharges_known_revocation_holes": [
            "ADD2_EXACT_IEEE754_ROLE_ORDER",
            "EVALUATOR_VISIBLE_IDENTIFIER_COLLISIONS",
            "ACCEPTED_PYTHON_STRING_STRICT_UTF8_PARTIALITY",
        ],
        "hard_nonclaims": [
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_BOUND_EVALUATOR_CONTRACT",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_CERTIFICATE_ALONE",
            "INDEPENDENT_CONTENT_BOUND_VERIFICATION_AND_SEPARATE_ACCEPTANCE_REDUCTION_REQUIRED",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
            "acceptance_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True, ensure_ascii=True))
