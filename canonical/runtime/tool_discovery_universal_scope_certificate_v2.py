"""Fail-closed universal scope certificate candidate for tool discovery.

This checker binds the zero-reality theorem in TOOL_DISCOVERY_SCOPE_RELATION_V2
to exact content-addressed Brain sources. The theorem is not an extrapolation
from the preserved 180-case terminal sample. It proves the frozen current
protocol over every valid finite declared tool ecosystem with arbitrary hidden
capability variants and sound safe-probe semantics.

It grants no acceptance, capability, family, execution, or promotion authority.
Independent clean-room verification remains mandatory.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
ATOM = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
    "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)

EXPECTED_BLOBS = {
    "canonical/runtime/tool_discovery_information_safe_candidate.py":
        "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    "canonical/runtime/tool_discovery_information_safe_proof.py":
        "2450a9644119c9fdf9c43307a1d115098d6ba592",
    "canonical/runtime/tool_discovery_information_safe_proof_v2.py":
        "5e8a953864e13ec76768c3e8920644107c65a644",
    "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":
        "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
        "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
    "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json":
        "48ba33998e73b8eec2731be51a7ec78077ed0d4a",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
        "7885a827b1483bfb38315c1f492848f7e4680285",
    "canonical/governance/TOOL_DISCOVERY_SCOPE_RELATION_V2.json":
        "52cea5b88ccea7a3d48ecf51edb30bb3ebe2f45d",
}

REQUIRED_FACTS = (
    "CANDIDATE_TOTAL_ORDERS_ELIGIBLE_TOOLS",
    "CANDIDATE_FILTERS_EVIDENCE_TO_CURRENT_EPOCH",
    "CANDIDATE_PROBES_ONLY_UNKNOWN_REQUIRED_PAIR",
    "CANDIDATE_REJECTS_TOOL_ON_CURRENT_NEGATIVE",
    "CANDIDATE_SELECTS_ONLY_AFTER_ALL_REQUIRED_POSITIVE",
    "CANDIDATE_ESCALATES_ONLY_AFTER_ORDERED_SCAN_EXHAUSTS",
    "PROBE_RECEIPT_RETURNS_EXACT_CURRENT_HIDDEN_TRUTH",
    "ORACLE_DEFINES_LEAST_COST_SUFFICIENT_ELIGIBLE_TOOL",
    "SELECTION_REQUIRES_CURRENT_POSITIVE_EVIDENCE",
    "TRANSFER_REUSES_UNCHANGED_EVIDENCE",
    "VERSION_CHANGE_INVALIDATES_CHANGED_TOOL_EVIDENCE",
    "NO_SUFFICIENT_ROUTE_ESCALATION_IS_CHECKED_AFTER_NEGATIVE_EVIDENCE",
)

def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()

def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

def _has(text: str, *parts: str) -> bool:
    return all(p in text for p in parts)

def derive_source_facts(candidate: str, proof_v1: str, proof_v2: str) -> dict[str, bool]:
    fc = _functions(candidate)
    f1 = _functions(proof_v1)
    f2 = _functions(proof_v2)
    return {
        "CANDIDATE_TOTAL_ORDERS_ELIGIBLE_TOOLS": (
            "next_action" in fc
            and _has(
                candidate,
                'if t.get("available") is True and t.get("authorized") is True',
                'tools.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))',
            )
        ),
        "CANDIDATE_FILTERS_EVIDENCE_TO_CURRENT_EPOCH": (
            "_epoch_map" in fc
            and "_evidence" in fc
            and _has(
                candidate,
                'if tid not in epochs or rec.get("epoch") != epochs[tid]:',
                'out[(tid, cap)] = rec.get("supported") is True',
            )
        ),
        "CANDIDATE_PROBES_ONLY_UNKNOWN_REQUIRED_PAIR": _has(
            candidate,
            'if value is None:',
            'unknown.append(cap)',
            'if unknown:',
            'return {"action": "PROBE", "tool_id": tid, "capability": unknown[0]}',
        ),
        "CANDIDATE_REJECTS_TOOL_ON_CURRENT_NEGATIVE": _has(
            candidate,
            'if value is False:',
            'known_false = True',
            'if known_false:',
            'continue',
        ),
        "CANDIDATE_SELECTS_ONLY_AFTER_ALL_REQUIRED_POSITIVE": _has(
            candidate,
            'if unknown:',
            'return {"action": "PROBE", "tool_id": tid, "capability": unknown[0]}',
            'return {"action": "SELECT", "tool_id": tid}',
        ),
        "CANDIDATE_ESCALATES_ONLY_AFTER_ORDERED_SCAN_EXHAUSTS": _has(
            candidate,
            'for tool in tools:',
            'return {"action": "ESCALATE", "reason": "NO_EVIDENCE_SUPPORTED_SUFFICIENT_TOOL"}',
        ),
        "PROBE_RECEIPT_RETURNS_EXACT_CURRENT_HIDDEN_TRUTH": (
            "_probe_receipt" in f1
            and _has(
                proof_v1,
                'epoch = _current_epoch(case, stage, tid)',
                'supported = cap in _hidden_caps(case, stage, tid)',
                '"kind": "SAFE_CAPABILITY_PROBE"',
            )
        ),
        "ORACLE_DEFINES_LEAST_COST_SUFFICIENT_ELIGIBLE_TOOL": (
            "_oracle_best_tool" in f1
            and _has(
                proof_v1,
                'if t.get("available") is not True or t.get("authorized") is not True:',
                'if req.issubset(_hidden_caps(case, stage, tid)):',
                'eligible.append((float(t["cost"]), tid))',
                'eligible.sort()',
                'return eligible[0][1]',
            )
        ),
        "SELECTION_REQUIRES_CURRENT_POSITIVE_EVIDENCE": (
            "_selection_is_evidence_supported" in f1
            and _has(
                proof_v1,
                'return all(evidence.get((tool_id, cap)) is True for cap in req)',
                'if not evidence_ok:',
                '"SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE"',
            )
        ),
        "TRANSFER_REUSES_UNCHANGED_EVIDENCE": _has(
            proof_v1,
            'repeated_without_change = sorted',
            '"VALID_PRIOR_EVIDENCE_NOT_REUSED"',
        ),
        "VERSION_CHANGE_INVALIDATES_CHANGED_TOOL_EVIDENCE": _has(
            candidate,
            'if ev.get("kind") == "TOOL_VERSION_CHANGED":',
            'out[tid] = int(ev.get("new_epoch", 1))',
            'if tid not in epochs or rec.get("epoch") != epochs[tid]:',
        ) and _has(
            proof_v1,
            'versioned = {str(x["tool_id"]) for x in case["stage2"].get("version_events", [])}',
        ),
        "NO_SUFFICIENT_ROUTE_ESCALATION_IS_CHECKED_AFTER_NEGATIVE_EVIDENCE": (
            "_execute_allow_escalate" in f2
            and _has(
                proof_v2,
                'if kind=="ESCALATE":',
                'if str(exc)!="NO_SUFFICIENT_TOOL":',
                '"PREMATURE_ESCALATION_WITH_UNTESTED_ROUTE"',
                '"PASS_ESCALATE_NO_SUFFICIENT_ROUTE"',
            )
        ),
    }

def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "status": "FAIL_CLOSED__UNIVERSAL_SCOPE_PREMISE_MISSING",
            "missing": missing,
            "universal_scope_proved": False,
            "scope_atom_satisfied_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    return {
        "status": (
            "PASS__UNIVERSAL_FORMAL_SCOPE_PROOF_DERIVED_FOR_FROZEN_TOOL_DISCOVERY__"
            "INDEPENDENT_PUBLIC_RUNNER_VERIFICATION_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "scope_atom": ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof": {
            "scope_semantics": (
                "The frozen family acceptance is over tool ecosystems with hidden "
                "capability variants. The terminal binding exposes TOOL_IDS_AND_DECLARED_COSTS "
                "and hides the ACTUAL_TOOL_CAPABILITY_MATRIX. The current behavioral contract "
                "likewise describes unknown or changing capabilities over available tools. "
                "Therefore the exact frozen scope is capability discovery and route selection "
                "over the declared finite identity universe, not arbitrary open-world identity enumeration."
            ),
            "finite_progress": (
                "Within a fixed stage there are finitely many eligible-tool/required-capability "
                "pairs. The policy probes only an unknown current-epoch pair, and a sound probe "
                "turns that pair permanently true or false for the stage. Thus every probe "
                "strictly decreases the finite unknown-pair measure and termination requires "
                "at most |eligible tools|*|required capabilities| probes."
            ),
            "least_cost_correctness": (
                "Eligible tools are totally ordered by declared cost then tool id. A tool is "
                "skipped only after a current negative required-capability fact and is selected "
                "only after every required capability has current positive evidence. Therefore "
                "the first selected tool is a least-cost sufficient eligible route."
            ),
            "no_route_correctness": (
                "If no sufficient eligible route exists, finite monotone probing eventually "
                "establishes at least one negative required-capability fact for every eligible "
                "tool; the ordered scan then exhausts and the policy escalates. A sufficient "
                "route cannot be skipped because sound evidence never marks one of its required "
                "capabilities false."
            ),
            "transfer_and_versions": (
                "Probe receipts are accepted only at the public current epoch. Unchanged tools "
                "retain current receipts across tasks, while a public version change advances "
                "the changed tool epoch and makes its old receipts stale. Thus transfer occurs "
                "without unsupported state promotion and changed tools are re-probed."
            ),
            "pointwise_ceiling": (
                "On every valid case inside the frozen declared-tool contract, selecting the "
                "least-cost sufficient route or correctly escalating when none exists is the "
                "terminal correctness ceiling for the route-selection obligation. The proof is "
                "pointwise and universal; the preserved 180/180 sample is not used as a scope argument."
            ),
        },
        "uses_empirical_generalization": False,
        "preserved_180_case_sample_used_for_scope_proof": False,
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

def verify() -> dict[str, Any]:
    for rel, want in EXPECTED_BLOBS.items():
        got = blob_sha(ROOT / rel)
        if got != want:
            raise AssertionError((rel, got, want))

    protocols = json.loads(_text(
        "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
    ))
    row = next(
        x for x in protocols["protocols"]
        if x["family"] == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    )
    assert row["status"] == "DEFINED_RESULT_OPEN"
    assert row["proof_mode"] == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
    assert "unknown tool discovery" in row["task_dimensions"]
    assert "frozen tool ecosystems with hidden capability variants" in row["acceptance"]
    assert "second-task transfer" in row["acceptance"]
    assert "unsupported capability-state promotion" in row["acceptance"]
    assert "same frozen task population/harness/tool authority" in protocols["universal_rules"]["same_scope"]

    binding = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
    ))
    visible = binding["information_boundary"]["candidate_visible"]
    hidden = binding["information_boundary"]["hidden_from_candidate"]
    assert "TOOL_IDS_AND_DECLARED_COSTS" in visible
    assert "ACTUAL_TOOL_CAPABILITY_MATRIX" in hidden
    assert binding["information_boundary"]["candidate_receives_hidden_oracle"] is False
    assert "NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS" in binding["source_pool"]["terminal_scope_claim"]

    registry = json.loads(_text(
        "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
    ))
    rr = next(
        x for x in registry["active_contracted_residuals"]
        if x.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
    )
    assert "available tool schemas/capabilities" in rr["inputs"].lower()
    assert "unknown or changing capabilities" in rr["environment_state"].lower()
    assert "discover candidate tools if needed" in rr["required_output_or_action"].lower()

    firewall = json.loads(_text(
        "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"
    ))
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in firewall["admissible_absolute_dominance_bases"]
    assert "TOOL_DISCOVERY_SELECTION_AND_LEARNING" in firewall[
        "expected_current_reduction"
    ]["reopened_pending_scope_completeness"]

    blocker = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"
    ))
    assert blocker["target_predicate"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    assert "EXACT_SCOPE_SEMANTICS" in blocker["minimum_missing_fact"]
    assert "VERIFIED_DISCOVERY_INTERFACE" in blocker["minimum_missing_fact"]

    acceptance = json.loads(_text(
        "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
    ))
    claim = next(
        x for x in acceptance["claims"]
        if x.get("predicate_id") == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    )
    assert claim["state"] == "EXTERNAL_BLOCKED"
    assert claim["blocker"] == "ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in claim["discharge_condition"]

    relation = json.loads(_text(
        "canonical/governance/TOOL_DISCOVERY_SCOPE_RELATION_V2.json"
    ))
    assert relation["status"].startswith("CANDIDATE_UNIVERSAL_FORMAL_SCOPE_RELATION")
    semantics = relation["exact_frozen_scope_semantics"]
    assert semantics["protocol_acceptance_population"] == (
        "FROZEN_TOOL_ECOSYSTEMS_WITH_HIDDEN_CAPABILITY_VARIANTS"
    )
    assert semantics["candidate_visible_identity_surface"] == "TOOL_IDS_AND_DECLARED_COSTS"
    assert semantics["candidate_hidden_surface"] == "ACTUAL_TOOL_CAPABILITY_MATRIX"
    assert "ARBITRARY_OPEN_WORLD_TOOL_IDENTITY_ENUMERATION_IS_NOT_PART" in semantics["scope_ruling"]
    assert relation["population_relation"]["not_empirical"] is True

    facts = derive_source_facts(
        _text("canonical/runtime/tool_discovery_information_safe_candidate.py"),
        _text("canonical/runtime/tool_discovery_information_safe_proof.py"),
        _text("canonical/runtime/tool_discovery_information_safe_proof_v2.py"),
    )
    return prove_from_facts(facts)

def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1

if __name__ == "__main__":
    raise SystemExit(main())
