"""Zero-reality P1 V7 direct-surface transport gate.

This gate intentionally separates:
1. independently verified V7 mechanism correctness on its verified envelope, from
2. proof that the three frozen direct surfaces actually transport the new
   load-bearing failure_semantics distinction required by V7.

A missing transport binding is a fail-closed result, not a capability failure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_V7_DIRECT_SURFACE_SCOPE_TRANSPORT_VERDICT_V1"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
ROUTE = "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF"

BINDING = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
MANIFEST = "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"
DIRECT_ROUTES = "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json"
FOUR_CONTRACTS = "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json"
V6_FALSIFICATION = "canonical/verification/P1_V6_DERIVED_ONLY_SCOPE_FALSIFICATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V7_VERIFICATION = "canonical/verification/P1_V7_CURRENT_MAIN_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V7_ENVELOPE = "canonical/governance/P1_TYPED_CAUSAL_INTERVENTION_ENVELOPE_V7.json"
TERMINAL_WAVE = "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"

EXPECTED_SURFACES = {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
REQUIRED_SEMANTICS = {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _git_blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _contains_literal(value: Any, literal: str) -> bool:
    if isinstance(value, str):
        return literal in value
    if isinstance(value, Mapping):
        return any(_contains_literal(k, literal) or _contains_literal(v, literal) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_literal(x, literal) for x in value)
    return False


def _surface_rows(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for tier in ("T0", "T2"):
        rows = (((manifest.get("portfolios") or {}).get(tier) or {}).get("surfaces") or [])
        for row in rows:
            if isinstance(row, Mapping) and ROUTE in (row.get("proof_routes") or []):
                out[f"{tier}/{row.get('id')}::{ROUTE}"] = row
    return out


def _p1_receipt(wave: Mapping[str, Any], tier: str) -> Mapping[str, Any] | None:
    rows = (((wave.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts") or {}).get(tier, [])
    hits = [x for x in rows if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR]
    return hits[0] if len(hits) == 1 else None


def evaluate(
    binding: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    routes: Mapping[str, Any] | None = None,
    contracts: Mapping[str, Any] | None = None,
    v6: Mapping[str, Any] | None = None,
    v7: Mapping[str, Any] | None = None,
    envelope: Mapping[str, Any] | None = None,
    wave: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    binding = dict(binding or _load(BINDING))
    manifest = dict(manifest or _load(MANIFEST))
    routes = dict(routes or _load(DIRECT_ROUTES))
    contracts = dict(contracts or _load(FOUR_CONTRACTS))
    v6 = dict(v6 or _load(V6_FALSIFICATION))
    v7 = dict(v7 or _load(V7_VERIFICATION))
    envelope = dict(envelope or _load(V7_ENVELOPE))
    wave = dict(wave or _load(TERMINAL_WAVE))

    errors: list[str] = []

    if binding.get("behavior_id") != BEHAVIOR:
        errors.append("P1_BEHAVIOR_DRIFT")
    if set(binding.get("direct_surface_bindings") or []) != EXPECTED_SURFACES:
        errors.append("P1_DIRECT_SURFACE_BINDING_DRIFT")

    surfaces = _surface_rows(manifest)
    if set(surfaces) != EXPECTED_SURFACES:
        errors.append("MANIFEST_P1_SURFACE_SET_DRIFT")

    obligations = [
        x for x in (contracts.get("obligations") or [])
        if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR
    ]
    if len(obligations) != 1:
        errors.append("FROZEN_P1_CONTRACT_OBLIGATION_COUNT")

    direct_routes = [
        x for x in (routes.get("routes") or [])
        if isinstance(x, Mapping) and BEHAVIOR in (x.get("covers") or [])
    ]
    if len(direct_routes) != 1:
        errors.append("DIRECT_P1_ROUTE_COUNT")
    elif direct_routes[0].get("id") != "DIRECT_TRAJECTORY_CAUSAL_CONTRACT_SUITE":
        errors.append("DIRECT_P1_ROUTE_ID_DRIFT")

    if not str(v6.get("status") or "").startswith(
        "INDEPENDENT_PUBLIC_RUNNER_PASS__V6_TERMINAL_SCOPE_TRANSPORT_FALSIFIED"
    ):
        errors.append("V6_DERIVED_ONLY_FALSIFICATION_NOT_INDEPENDENT_PASS")
    if "V6_MUST_NOT_BE_USED_AS_EXACT_OR_SUPERSET_TERMINAL_P1_SCOPE_CARRIER" not in set(v6.get("verified_consequence") or []):
        errors.append("V6_FALSIFICATION_CONSEQUENCE_MISSING")

    if not str(v7.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_CURRENT_MAIN_V7_BYTES"):
        errors.append("V7_EXACT_BYTES_NOT_INDEPENDENT_PASS")
    exact = v7.get("exact_brain_blobs") if isinstance(v7.get("exact_brain_blobs"), Mapping) else {}
    for path in (
        "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
        "canonical/tests/test_trajectory_failure_typed_ir_v7.py",
        V7_ENVELOPE,
    ):
        if exact.get(path) != _git_blob_sha(path):
            errors.append("V7_EXACT_BLOB_DRIFT:" + path)

    hardening = set(envelope.get("hardening") or [])
    required_hardening = {
        "FAILURE_SEMANTICS_IS_PARSED_VALIDATED_AND_LOAD_BEARING",
        "DERIVED_UPSTREAM_FAILURES_NEVER_BECOME_DIRECT_REPAIR_ROOTS",
        "ALL_DIRECT_CONTRACT_FAILURES_ON_TERMINAL_CAUSAL_SLICE_REMAIN_REPAIR_RELEVANT",
    }
    if not required_hardening <= hardening:
        errors.append("V7_FAILURE_SEMANTICS_HARDENING_DRIFT")

    terminal: dict[str, Any] = {}
    for tier in ("T0", "T2"):
        row = _p1_receipt(wave, tier)
        if row is None:
            errors.append("TERMINAL_P1_RECEIPT_MISSING:" + tier)
            continue
        terminal[tier] = dict(row)
        for key in ("load_bearing", "direct_instrumentation_pass", "parent_terminal_acceptance_pass"):
            if row.get(key) is not True:
                errors.append(f"TERMINAL_P1_RECEIPT_FAIL:{tier}:{key}")
        for key in ("case_replaced", "tuning_replay", "result_to_runtime_feedback"):
            if row.get(key) is not False:
                errors.append(f"TERMINAL_P1_RECEIPT_CONTAMINATED:{tier}:{key}")

    # Critical zero-reality transport question:
    # do the frozen surface-authority objects themselves carry the distinction
    # that V7 now requires? Do NOT inspect the V7 envelope here.
    surface_transport_sources = {
        BINDING: binding,
        MANIFEST: manifest,
        DIRECT_ROUTES: routes,
        FOUR_CONTRACTS: contracts,
    }
    semantics_presence = {
        rel: {semantic: _contains_literal(obj, semantic) for semantic in sorted(REQUIRED_SEMANTICS)}
        for rel, obj in surface_transport_sources.items()
    }
    failure_semantics_field_present = {
        rel: _contains_literal(obj, "failure_semantics")
        for rel, obj in surface_transport_sources.items()
    }
    transport_explicit = (
        any(failure_semantics_field_present.values())
        and all(any(row[s] for row in semantics_presence.values()) for s in REQUIRED_SEMANTICS)
    )

    errors = sorted(set(errors))
    if errors:
        status = "FAIL_CLOSED__SOURCE_OR_VERIFICATION_DRIFT__ZERO_CREDIT"
        classification = "INVALID_INPUT_OR_AUTHORITY_DRIFT"
    elif not transport_explicit:
        status = "FAIL_CLOSED__V7_DIRECT_SURFACE_FAILURE_SEMANTICS_TRANSPORT_NOT_PROVED__ZERO_CREDIT"
        classification = "FORMAL_INPUT_BINDING_RESIDUAL"
    else:
        status = "PASS__V7_DIRECT_SURFACE_FAILURE_SEMANTICS_TRANSPORT_EXPLICIT__ZERO_CREDIT"
        classification = "TRANSPORT_PRECONDITION_PROVED"

    relation = "SUPERSET_PRECONDITION_PROVED" if transport_explicit and not errors else "NOT_PROVED"
    claims = [
        {
            "claim_id": "P1_V7_SCOPE_TRANSPORT::" + surface.split("::", 1)[0].replace("/", "::"),
            "direct_surface": surface,
            "relation": relation,
            "private_benchmark_population_scope_claimed": False,
        }
        for surface in sorted(surfaces)
    ]

    return {
        "schema": SCHEMA,
        "status": status,
        "pass": bool(transport_explicit and not errors),
        "classification": classification,
        "errors": errors,
        "behavior_id": BEHAVIOR,
        "surface_count": len(surfaces),
        "surfaces": sorted(surfaces),
        "claim_bound_relations": claims,
        "v6_derived_only_scope_transport_falsified": not any(
            x.startswith("V6_") for x in errors
        ),
        "v7_exact_mechanism_independently_verified": not any(
            x.startswith("V7_") for x in errors
        ),
        "load_bearing_failure_semantics": sorted(REQUIRED_SEMANTICS),
        "surface_transport_sources": {
            rel: {
                "failure_semantics_field_present": failure_semantics_field_present[rel],
                "semantic_literals_present": semantics_presence[rel],
            }
            for rel in sorted(surface_transport_sources)
        },
        "failure_semantics_transport_explicit": transport_explicit,
        "missing_transport_fact": (
            None if transport_explicit else
            "EXPLICIT_FROZEN_SURFACE_TO_V7_FAILURE_SEMANTICS_MAPPING_OR_PROOF_PRESERVING_ADAPTER"
        ),
        "terminal_receipts_preserved": {
            "T0": terminal.get("T0", {}).get("case_id"),
            "T2": terminal.get("T2", {}).get("case_id"),
            "terminal_results_replayed": 0,
        },
        "quarantine_lift_eligible": False,
        "next": (
            "INDEPENDENTLY_VERIFY_THIS_ZERO_REALITY_VERDICT__"
            "IF_FAIL_CLOSED_REPRODUCES__SYNTHESIZE_MINIMUM_PROOF_PRESERVING_FAILURE_SEMANTICS_ADAPTER__"
            "NO_TERMINAL_REPLAY"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    # Both a proved transport and a classified fail-closed residual are valid
    # executions of this diagnostic gate. Authority drift is not.
    return 1 if out["classification"] == "INVALID_INPUT_OR_AUTHORITY_DRIFT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
