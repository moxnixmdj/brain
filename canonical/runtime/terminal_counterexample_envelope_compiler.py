#!/usr/bin/env python3
"""Terminal counterexample + verified-envelope compiler.

Purpose
-------
Reduce a behavioral proof problem to the smallest unresolved proof basis without
spending fresh terminal evidence.

This compiler is deliberately non-authoritative about capability truth. It only
propagates *already verified* envelopes, verified failures, and verified
implication receipts. Unknowns remain unknown.

Key guarantees
--------------
* Fail closed on malformed or contradictory evidence.
* Never convert simulation/prediction into proof.
* Exact implication closure over the declared finite implication universe.
* Exact minimum residual basis when <= 20 unknown dimensions; otherwise returns
  a conservative all-unknown basis and marks it non-exact.
* Emits counterexample obligations for only the irreducible residual basis.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_TERMINAL_COUNTEREXAMPLE_ENVELOPE_COMPILER_V1"

AUTHORITATIVE_PROOF_KINDS = {
    "FORMAL_PROOF",
    "THEORETICAL_CEILING",
    "EXHAUSTIVE_FINITE_VERIFICATION",
    "INDEPENDENT_VERIFIED_BOUNDED_ENVELOPE",
    "INDEPENDENT_VERIFIED_SCOPE_EQUIVALENT_PROTOCOL",
}

MAX_EXACT_BASIS_DIMENSIONS = 20


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _strings(value: Any, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{name} must be {'a non-empty' if not allow_empty else 'a'} list")
    if not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError(f"{name} contains invalid entries")
    vals = [x.strip() for x in value]
    if len(vals) != len(set(vals)):
        raise ValueError(f"{name} contains duplicates")
    return vals


def _closure(seed: set[str], implications: list[tuple[frozenset[str], frozenset[str], str]]) -> set[str]:
    out = set(seed)
    changed = True
    while changed:
        changed = False
        for antecedent, consequent, _receipt in implications:
            if antecedent <= out and not consequent <= out:
                out.update(consequent)
                changed = True
    return out


def _exact_minimum_seed(
    universe: set[str],
    implications: list[tuple[frozenset[str], frozenset[str], str]],
) -> tuple[list[str], bool]:
    """Return a smallest seed subset whose implication closure covers universe.

    Exact only for <= MAX_EXACT_BASIS_DIMENSIONS. For larger universes we
    conservatively return all unresolved dimensions.
    """
    ordered = sorted(universe)
    if not ordered:
        return [], True
    if len(ordered) > MAX_EXACT_BASIS_DIMENSIONS:
        return ordered, False

    for size in range(len(ordered) + 1):
        for combo in itertools.combinations(ordered, size):
            if universe <= _closure(set(combo), implications):
                return list(combo), True
    return ordered, True


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        contract_id = _string(data.get("contract_id"), "contract_id")
        required = set(_strings(data.get("required_dimensions"), "required_dimensions"))
    except ValueError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "terminal_credit_delta": 0,
            "fresh_terminal_evidence_consumed": 0,
        }

    proved_direct: set[str] = set()
    envelope_receipts: dict[str, list[str]] = {}
    envelopes = data.get("verified_envelopes")
    if not isinstance(envelopes, list):
        errors.append("VERIFIED_ENVELOPES_MUST_BE_LIST")
        envelopes = []

    for idx, env in enumerate(envelopes):
        if not isinstance(env, dict):
            errors.append(f"ENVELOPE_{idx}_INVALID")
            continue
        try:
            env_id = _string(env.get("id"), f"verified_envelopes[{idx}].id")
            covers = set(_strings(env.get("covers"), f"verified_envelopes[{idx}].covers"))
            receipt = _string(env.get("receipt"), f"verified_envelopes[{idx}].receipt")
            proof_kind = _string(env.get("proof_kind"), f"verified_envelopes[{idx}].proof_kind")
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if env.get("authority_verified") is not True:
            errors.append(f"ENVELOPE_NOT_VERIFIED:{env_id}")
            continue
        if proof_kind not in AUTHORITATIVE_PROOF_KINDS:
            errors.append(f"NONAUTHORITATIVE_PROOF_KIND:{env_id}:{proof_kind}")
            continue

        outside = covers - required
        if outside:
            errors.append(f"ENVELOPE_COVERS_UNDECLARED_DIMENSIONS:{env_id}:" + ",".join(sorted(outside)))
            continue

        proved_direct.update(covers)
        for dim in covers:
            envelope_receipts.setdefault(dim, []).append(receipt)

    failed: set[str] = set()
    failure_receipts: dict[str, list[str]] = {}
    failures = data.get("verified_failures")
    if failures is None:
        failures = []
    if not isinstance(failures, list):
        errors.append("VERIFIED_FAILURES_MUST_BE_LIST")
        failures = []

    for idx, item in enumerate(failures):
        if not isinstance(item, dict):
            errors.append(f"FAILURE_{idx}_INVALID")
            continue
        try:
            dims = set(_strings(item.get("dimensions"), f"verified_failures[{idx}].dimensions"))
            receipt = _string(item.get("receipt"), f"verified_failures[{idx}].receipt")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if item.get("authority_verified") is not True:
            errors.append(f"FAILURE_NOT_VERIFIED:{idx}")
            continue
        outside = dims - required
        if outside:
            errors.append("FAILURE_COVERS_UNDECLARED_DIMENSIONS:" + ",".join(sorted(outside)))
            continue
        failed.update(dims)
        for dim in dims:
            failure_receipts.setdefault(dim, []).append(receipt)

    implications: list[tuple[frozenset[str], frozenset[str], str]] = []
    raw_implications = data.get("verified_implications")
    if raw_implications is None:
        raw_implications = []
    if not isinstance(raw_implications, list):
        errors.append("VERIFIED_IMPLICATIONS_MUST_BE_LIST")
        raw_implications = []

    seen_implications: set[tuple[frozenset[str], frozenset[str]]] = set()
    for idx, item in enumerate(raw_implications):
        if not isinstance(item, dict):
            errors.append(f"IMPLICATION_{idx}_INVALID")
            continue
        try:
            antecedent = frozenset(_strings(item.get("if_proved"), f"verified_implications[{idx}].if_proved"))
            consequent = frozenset(_strings(item.get("then_proved"), f"verified_implications[{idx}].then_proved"))
            receipt = _string(item.get("receipt"), f"verified_implications[{idx}].receipt")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if item.get("authority_verified") is not True:
            errors.append(f"IMPLICATION_NOT_VERIFIED:{idx}")
            continue
        outside = (set(antecedent) | set(consequent)) - required
        if outside:
            errors.append("IMPLICATION_REFERENCES_UNDECLARED_DIMENSIONS:" + ",".join(sorted(outside)))
            continue
        if antecedent & consequent:
            consequent = frozenset(set(consequent) - set(antecedent))
        if not consequent:
            warnings.append(f"IMPLICATION_{idx}_NO_NEW_CONSEQUENCE")
            continue
        key = (antecedent, consequent)
        if key in seen_implications:
            warnings.append(f"IMPLICATION_{idx}_DUPLICATE")
            continue
        seen_implications.add(key)
        implications.append((antecedent, consequent, receipt))

    if errors:
        return {
            "schema": SCHEMA,
            "contract_id": contract_id,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "warnings": sorted(set(warnings)),
            "terminal_credit_delta": 0,
            "fresh_terminal_evidence_consumed": 0,
        }

    proved = _closure(proved_direct, implications)
    contradiction = sorted(proved & failed)
    if contradiction:
        return {
            "schema": SCHEMA,
            "contract_id": contract_id,
            "status": "FAIL_CLOSED_CONTRADICTORY_VERIFIED_EVIDENCE",
            "contradictory_dimensions": contradiction,
            "proved_dimensions": sorted(proved),
            "failed_dimensions": sorted(failed),
            "errors": ["VERIFIED_PASS_AND_FAIL_OVERLAP"],
            "warnings": sorted(set(warnings)),
            "terminal_credit_delta": 0,
            "fresh_terminal_evidence_consumed": 0,
        }

    unknown = required - proved - failed

    unresolved_implications = []
    for antecedent, consequent, receipt in implications:
        if antecedent <= unknown and consequent <= unknown:
            unresolved_implications.append((antecedent, consequent, receipt))

    basis, basis_exact = _exact_minimum_seed(unknown, unresolved_implications)

    counterexample_obligations = [
        {
            "dimension": dim,
            "query": f"FIND_WITNESS_WITHIN_DECLARED_SCOPE_WHERE_{dim}_FAILS",
            "promotion_rule": (
                "A_WITNESS_IS_A_VERIFIED_FAILURE; ABSENCE_OF_A_WITNESS_IS_NOT_PROOF "
                "UNLESS_THE_SEARCH_IS_FORMALLY_COMPLETE_OR_EXHAUSTIVE"
            ),
        }
        for dim in basis
    ]

    if failed:
        status = "VERIFIED_COUNTEREXAMPLE_PRESENT"
    elif not unknown:
        status = "DECLARED_CONTRACT_DIMENSIONS_COVERED_BY_VERIFIED_EVIDENCE"
    else:
        status = "PARTIAL_VERIFIED_ENVELOPE__RESIDUAL_UNKNOWN"

    result = {
        "schema": SCHEMA,
        "contract_id": contract_id,
        "status": status,
        "required_dimensions": sorted(required),
        "proved_dimensions_direct": sorted(proved_direct),
        "proved_dimensions_after_implication_closure": sorted(proved),
        "failed_dimensions": sorted(failed),
        "unknown_dimensions": sorted(unknown),
        "minimum_residual_proof_basis": basis,
        "minimum_residual_proof_basis_exact": basis_exact,
        "counterexample_obligations": counterexample_obligations,
        "verified_implication_count": len(implications),
        "proved_dimension_receipts": {k: sorted(set(v)) for k, v in sorted(envelope_receipts.items())},
        "failure_dimension_receipts": {k: sorted(set(v)) for k, v in sorted(failure_receipts.items())},
        "warnings": sorted(set(warnings)),
        "terminal_credit_delta": 0,
        "fresh_terminal_evidence_consumed": 0,
        "authority_rule": (
            "THIS_COMPILER_PROPAGATES_ONLY_PREVERIFIED_ENVELOPES_FAILURES_AND_IMPLICATIONS; "
            "IT_DOES_NOT_TURN_PREDICTION_SIMULATION_OR_SEARCH_FAILURE_INTO_CAPABILITY_PROOF"
        ),
    }

    assert set(result["proved_dimensions_after_implication_closure"]) \
        | set(result["failed_dimensions"]) \
        | set(result["unknown_dimensions"]) == required
    assert not (set(result["proved_dimensions_after_implication_closure"]) & set(result["failed_dimensions"]))
    assert not (set(result["proved_dimensions_after_implication_closure"]) & set(result["unknown_dimensions"]))
    assert not (set(result["failed_dimensions"]) & set(result["unknown_dimensions"]))
    return result


def self_test() -> None:
    data = {
        "contract_id": "DEMO",
        "required_dimensions": ["A", "B", "C", "D", "E", "F"],
        "verified_envelopes": [
            {
                "id": "ENV1",
                "covers": ["A", "B"],
                "receipt": "receipt://env1",
                "proof_kind": "INDEPENDENT_VERIFIED_BOUNDED_ENVELOPE",
                "authority_verified": True,
            }
        ],
        "verified_failures": [],
        "verified_implications": [
            {
                "if_proved": ["B"],
                "then_proved": ["C"],
                "receipt": "receipt://b-implies-c",
                "authority_verified": True,
            },
            {
                "if_proved": ["D"],
                "then_proved": ["E", "F"],
                "receipt": "receipt://d-implies-ef",
                "authority_verified": True,
            },
        ],
    }
    out = evaluate(data)
    assert out["status"] == "PARTIAL_VERIFIED_ENVELOPE__RESIDUAL_UNKNOWN"
    assert out["proved_dimensions_after_implication_closure"] == ["A", "B", "C"]
    assert out["unknown_dimensions"] == ["D", "E", "F"]
    assert out["minimum_residual_proof_basis"] == ["D"]
    assert out["minimum_residual_proof_basis_exact"] is True
    assert len(out["counterexample_obligations"]) == 1

    fail = dict(data)
    fail["verified_failures"] = [{
        "dimensions": ["A"],
        "receipt": "receipt://fail-a",
        "authority_verified": True,
    }]
    out2 = evaluate(fail)
    assert out2["status"] == "FAIL_CLOSED_CONTRADICTORY_VERIFIED_EVIDENCE"

    bad = dict(data)
    bad["verified_envelopes"] = [{
        "id": "BAD",
        "covers": ["A"],
        "receipt": "receipt://bad",
        "proof_kind": "SIMULATION_PREDICTION",
        "authority_verified": True,
    }]
    out3 = evaluate(bad)
    assert out3["status"] == "FAIL_CLOSED"
    assert any(x.startswith("NONAUTHORITATIVE_PROOF_KIND") for x in out3["errors"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        print(json.dumps({"schema": SCHEMA, "status": "SELF_TEST_PASS"}, sort_keys=True))
        return 0

    if args.input is None:
        ap.error("input required unless --self-test")

    data = json.loads(args.input.read_text(encoding="utf-8"))
    out = evaluate(data)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not out["status"].startswith("FAIL_CLOSED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
