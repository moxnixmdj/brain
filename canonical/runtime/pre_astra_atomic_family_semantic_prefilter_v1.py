from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PRE_ASTRA_ATOMIC_FAMILY_SEMANTIC_PREFILTER_VERIFIER_V1"

PREFILTER = "canonical/governance/PRE_ASTRA_ATOMIC_FAMILY_SEMANTIC_PREFILTER_20261006_V1.json"
REGISTRY = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVIDENCE = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
TUPLES = "canonical/governance/OPUS55_SCORE_TARGET_TUPLE_BINDINGS_20261005_V1.json"
V7 = "canonical/governance/V7_CAPABILITY_EVALUATOR_CERTIFICATION_TRICHOTOMY_20261006_V1.json"
MINCUT = "canonical/governance/PRE_ASTRA_TARGET_INFORMATION_MINCUT_THEOREM_20261006_V1.json"
PACKET_V2 = "canonical/governance/ASTRA_SCARCE_ACCESS_TARGET_SEMANTICS_CLASSIFICATION_PACKET_20261006_V2.json"

EXPECTED = {
    REGISTRY: "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    EVIDENCE: "a3fd20e58fdbd9b86278b7de0c245de3063dce27",
    TUPLES: "9bbd45f066ab94fa3f5110b9cc5efcd4118d1367",
    V7: "dce8d6838de486862d205436ed96cda6376e28ba",
    MINCUT: "6622a34c2de805523ac2c87808c13fb6cba1f3fe",
    PACKET_V2: "2d2062ecccd37aa745f836bdae059836f50fa84e",
}

EXPECTED_KIND_COUNTS = {
    "PUBLIC_FIXED_BAR": 14,
    "MATCHED_NONINFERIORITY": 4,
    "MATCHED_SCOPE_AUDIT": 4,
    "DIRECT_SCOPE_AUDIT": 1,
    "DEPENDENCY_PROOF": 1,
}


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text())
    if not isinstance(value, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return value


def _proved_ids(evidence: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("predicate_id"))
        for row in evidence.get("claims") or []
        if isinstance(row, Mapping)
        and str(row.get("state") or "").startswith("PROVED")
    }


def evaluate() -> dict[str, Any]:
    errors: list[str] = []

    for path, expected in EXPECTED.items():
        actual = blob(path)
        if actual != expected:
            errors.append(f"SOURCE_BLOB_DRIFT:{path}:{actual}")

    pre = load(PREFILTER)
    reg = load(REGISTRY)
    ev = load(EVIDENCE)
    tuples = load(TUPLES)
    v7 = load(V7)

    proved = _proved_ids(ev)
    unresolved = [
        row for row in reg.get("predicates") or []
        if isinstance(row, Mapping) and row.get("id") not in proved
    ]
    unresolved_ids = {str(row.get("id")) for row in unresolved}

    frontier = pre.get("current_atomic_frontier") or {}
    declared_ids: set[str] = set()
    kind_counts: dict[str, int] = {}
    for kind in EXPECTED_KIND_COUNTS:
        row = frontier.get(kind)
        if not isinstance(row, Mapping):
            errors.append("PREFILTER_KIND_MISSING:" + kind)
            continue
        ids = set(map(str, row.get("predicates") or []))
        declared_ids |= ids
        kind_counts[kind] = len(ids)
        if row.get("count") != len(ids):
            errors.append("PREFILTER_KIND_COUNT_SELF_MISMATCH:" + kind)

    if declared_ids != unresolved_ids:
        errors.append("PREFILTER_ATOMIC_SET_MISMATCH")

    actual_kind_counts: dict[str, int] = {}
    for row in unresolved:
        kind = str(row.get("kind"))
        actual_kind_counts[kind] = actual_kind_counts.get(kind, 0) + 1

    if actual_kind_counts != EXPECTED_KIND_COUNTS:
        errors.append("REGISTRY_KIND_PARTITION_DRIFT")
    if kind_counts != EXPECTED_KIND_COUNTS:
        errors.append("PREFILTER_KIND_PARTITION_DRIFT")
    if frontier.get("total_unresolved_atomic") != 24:
        errors.append("PREFILTER_TOTAL_NOT_24")

    fixed = set(map(
        str,
        ((frontier.get("PUBLIC_FIXED_BAR") or {}).get("predicates") or [])
    ))
    tuple_ids = {
        str(row.get("predicate_id") or row.get("id"))
        for row in tuples.get("bindings") or []
        if isinstance(row, Mapping)
    }
    if fixed != tuple_ids:
        errors.append("FIXED_BAR_TARGET_TUPLE_SET_MISMATCH")

    derived_families: dict[str, set[str]] = {}
    for row in unresolved:
        family = str(row.get("family"))
        derived_families.setdefault(family, set()).add(str(row.get("id")))

    declared_families_raw = (
        (pre.get("family_semantic_frontier") or {}).get("families") or {}
    )
    declared_families = {
        str(family): set(map(str, ids))
        for family, ids in declared_families_raw.items()
    }
    if declared_families != derived_families:
        errors.append("FAMILY_ATOMIC_MAPPING_MISMATCH")
    if len(derived_families) != 14:
        errors.append("FAMILY_COUNT_NOT_14")

    routes = v7.get("routes") or {}
    for route in (
        "E_EXPLICIT_COMPLETE",
        "M_HIDDEN_RESTRICTED_MONOTONE",
        "U_ARBITRARY_OR_UNCLASSIFIED_HIDDEN",
    ):
        if route not in routes:
            errors.append("V7_ROUTE_MISSING:" + route)

    fam = pre.get("family_semantic_frontier") or {}
    if fam.get("default_route_status") != (
        "UNRESOLVED_FOR_FAMILY_WIDE_E_OR_M__RETAIN_U_UNLESS_SEPARATE_PROOF_EXISTS"
    ):
        errors.append("FAMILY_DEFAULT_ROUTE_OVERCLAIM")
    if fam.get("proved_family_level_M_receipts_bound_by_this_authority_set") != 0:
        errors.append("UNSUPPORTED_FAMILY_M_CREDIT")

    firewall = pre.get("semantic_level_firewall") or {}
    if "SEPARATE_PROOF" not in str(firewall.get("family_wide_E") or ""):
        errors.append("FAMILY_E_FIREWALL_WEAK")
    if "SEPARATE_PROOF" not in str(firewall.get("family_wide_M") or ""):
        errors.append("FAMILY_M_FIREWALL_WEAK")

    accounting = pre.get("accounting") or {}
    if accounting.get("astra_access_consumed") != 0:
        errors.append("ASTRA_ACCESS_ACCOUNTING_OVERCLAIM")
    for key in (
        "terminal_credit_delta",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key) != 0:
            errors.append("NONZERO_CREDIT:" + key)

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__24_ATOMIC_CONTRACTS_SEPARATED_FROM_14_FAMILY_SEMANTIC_QUESTIONS__ZERO_ASTRA_ACCESS__ZERO_CREDIT"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(errors),
        "unresolved_atomic_count": 24 if ok else None,
        "family_count": 14 if ok else None,
        "kind_counts": EXPECTED_KIND_COUNTS if ok else {},
        "fixed_bar_target_tuple_count": 14 if ok else None,
        "family_E_or_M_credit": 0,
        "astra_access_consumed": 0,
        "terminal_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
