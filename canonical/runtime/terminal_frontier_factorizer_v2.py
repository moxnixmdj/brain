from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import terminal_frontier_factorizer_v1 as v1

DELETED_NON_NECESSARY = "COMPOSITION_COMPONENT_SCOPED_PROOFS"

ATOMIC = tuple(x for x in v1.ATOMIC if x != DELETED_NON_NECESSARY)
META = v1.META
TARGET_TUPLE_ATOMS = set(v1.TARGET_TUPLE_ATOMS)
EXTERNAL_RESULT_ATOMS = set(v1.EXTERNAL_RESULT_ATOMS)
UNIVERSAL_SCOPE_ATOMS = set(v1.UNIVERSAL_SCOPE_ATOMS) - {DELETED_NON_NECESSARY}
QUOTIENT_META = set(v1.QUOTIENT_META)


class FactorizationV2Error(RuntimeError):
    pass


def _registry_predicate(repo_root: Path, predicate_id: str) -> dict:
    path = repo_root / "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [x for x in data.get("predicates", []) if x.get("id") == predicate_id]
    if len(rows) != 1:
        raise FactorizationV2Error("PREDICATE_REGISTRY_BINDING_INVALID")
    return rows[0]


def contraction_preconditions(repo_root: Path | None = None) -> dict:
    root = repo_root or Path(__file__).resolve().parents[2]
    if DELETED_NON_NECESSARY not in v1.ATOMIC:
        raise FactorizationV2Error("DELETED_PREDICATE_NOT_IN_V1_OPEN_ATOMIC")
    if DELETED_NON_NECESSARY not in v1.UNIVERSAL_SCOPE_ATOMS:
        raise FactorizationV2Error("DELETED_PREDICATE_NOT_IN_V1_SCOPE_INTERFACE")
    if DELETED_NON_NECESSARY in v1.TARGET_TUPLE_ATOMS:
        raise FactorizationV2Error("DEPENDENCY_PREDICATE_UNEXPECTEDLY_SCORE_BEARING")
    row = _registry_predicate(root, DELETED_NON_NECESSARY)
    if row.get("family") != "MULTI_CAPABILITY_COMPOSITION":
        raise FactorizationV2Error("DEPENDENCY_FAMILY_DRIFT")
    if row.get("kind") != "DEPENDENCY_PROOF":
        raise FactorizationV2Error("DEPENDENCY_KIND_DRIFT")
    return {
        "historical_registry_predicate_preserved": True,
        "historical_kind": row["kind"],
        "historical_family": row["family"],
        "deleted_from_terminal_necessity_only": True,
    }


def factorize(repo_root: Path | None = None) -> dict:
    pre = contraction_preconditions(repo_root)
    obligations = list(ATOMIC) + list(META)
    req: dict[str, list[str]] = {o: [] for o in obligations}

    for o in TARGET_TUPLE_ATOMS:
        if o in req:
            req[o].append("TARGET_TUPLE_BINDING")
    for o in EXTERNAL_RESULT_ATOMS:
        if o in req:
            req[o].append("EXTERNAL_RESULT_OR_ACCESS")
    for o in UNIVERSAL_SCOPE_ATOMS:
        if o in req:
            req[o].append("UNIVERSAL_SCOPE_AND_COMPOSITION")
    for o in QUOTIENT_META:
        req[o].append("BEHAVIORAL_QUOTIENT_AND_TRANSFER")
    req["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"].extend([
        "EXTERNAL_RESULT_OR_ACCESS",
        "UNIVERSAL_SCOPE_AND_COMPOSITION",
    ])

    missing = sorted(o for o, interfaces in req.items() if not interfaces)
    if missing:
        raise FactorizationV2Error("UNMAPPED_OBLIGATIONS:" + ",".join(missing))

    expected = (set(v1.ATOMIC) | set(v1.META)) - {DELETED_NON_NECESSARY}
    if set(obligations) != expected:
        raise FactorizationV2Error("NONLOSSLESS_CONTRACTION")

    interfaces: dict[str, list[str]] = {}
    for obligation, names in req.items():
        for name in names:
            interfaces.setdefault(name, []).append(obligation)

    for preserved in (
        "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
        "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
    ):
        if preserved not in req or "UNIVERSAL_SCOPE_AND_COMPOSITION" not in req[preserved]:
            raise FactorizationV2Error("COMPOSITION_PRESERVATION_FAILED:" + preserved)

    return {
        "status": "PASS__31_OF_31_TERMINALLY_NECESSARY_OPEN_TRUTH_OBLIGATIONS_PRESERVED__ONE_REDUNDANT_DEPENDENCY_PREDICATE_DELETED__ZERO_CREDIT",
        "open_atomic_count": len(ATOMIC),
        "meta_count": len(META),
        "truth_obligation_count": len(obligations),
        "historical_v1_truth_obligation_count": len(v1.ATOMIC) + len(v1.META),
        "interface_count": len(interfaces),
        "interfaces": {k: sorted(v) for k, v in sorted(interfaces.items())},
        "obligation_interfaces": {k: sorted(v) for k, v in sorted(req.items())},
        "deleted_non_necessary_obligations": [DELETED_NON_NECESSARY],
        "truth_obligations_deleted": 1,
        "truth_obligations_closed": 0,
        "preconditions": pre,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(factorize(), indent=2, sort_keys=True))
