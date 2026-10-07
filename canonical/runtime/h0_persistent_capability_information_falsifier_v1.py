from __future__ import annotations

from hashlib import sha256
from typing import Any


def _bits(payload: bytes) -> int:
    return 8 * len(payload)


def representation_laundering_counterexample() -> dict[str, Any]:
    """Show that a learned-byte label can change while capability information does not."""
    capability_state = b"target-policy:if-x-then-a-else-b"
    learned_container = capability_state
    source_constant = b'POLICY = ' + repr(capability_state).encode("ascii")

    return {
        "semantic_payload_sha256": sha256(capability_state).hexdigest(),
        "learned_representation_declared_learned_bytes": len(learned_container),
        "source_constant_declared_learned_bytes": 0,
        "source_constant_total_bits": _bits(source_constant),
        "capability_information_preserved": capability_state in source_constant,
        "declared_learned_byte_count_changed": len(learned_container) != 0,
        "learned_byte_metric_representation_invariant": False,
    }


def repaired_accounting_contract() -> dict[str, Any]:
    return {
        "quantity": "PERSISTENT_CAPABILITY_INFORMATION",
        "counts": [
            "MODEL_OR_WEIGHT_BYTES",
            "SOURCE_CONSTANTS",
            "LOOKUP_TABLES",
            "HANDWRITTEN_RULES",
            "TARGET_SPECIFIC_PROGRAMS",
            "VERIFIED_CAPABILITY_LIBRARY_ENTRIES",
            "SEARCH_HEURISTICS_WHEN_CAUSALLY_NECESSARY",
        ],
        "excludes_only_by_declared_boundary": [
            "FIXED_UNIVERSAL_INTERPRETER",
            "JIT_DECLARATIVE_KNOWLEDGE",
            "NON_LOAD_BEARING_METADATA",
        ],
        "external_capability_laundering_forbidden": True,
        "resource_semantics_load_bearing": True,
    }


def compile_h0_falsification() -> dict[str, Any]:
    witness = representation_laundering_counterexample()
    if not witness["capability_information_preserved"]:
        return {"status": "FAIL_CLOSED", "reason": "NO_REENCODING_WITNESS"}
    if witness["learned_byte_metric_representation_invariant"]:
        return {"status": "FAIL_CLOSED", "reason": "EXPECTED_METRIC_NONINVARIANCE"}
    return {
        "status": "PASS__ZERO_LEARNED_BYTE_METRIC_FALSIFIED_AS_LOAD_BEARING_QUANTITY",
        "learned_byte_metric_falsified": True,
        "h0_zero_learned_not_decidable_from_that_metric": True,
        "repaired_hypothesis": "H0_ZERO_INCREMENTAL_PERSISTENT_CAPABILITY_INFORMATION",
        "next_falsifier": "F_TARGET_RELEVANT_IRREDUCIBLE_CAPABILITY_INFORMATION",
        "terminal_credit": False,
    }
