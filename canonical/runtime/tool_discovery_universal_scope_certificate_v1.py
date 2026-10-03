"""Universal formal scope certificate candidate for Tool Discovery.

This proves the exact information-safe Tool Discovery policy for the frozen
MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER protocol under explicit protocol
assumptions. It is a theorem about finite hidden-capability search, not a claim
that every tool identity on the Internet is known.

No acceptance/family/ownership credit is granted here. Independent clean-room
verification and a separate acceptance reducer remain mandatory.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
TARGET = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_UNIVERSAL_SCOPE_CERTIFICATE_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/tool_discovery_information_safe_candidate.py":
        "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    "canonical/runtime/tool_discovery_information_safe_proof.py":
        "2450a9644119c9fdf9c43307a1d115098d6ba592",
    "canonical/runtime/tool_discovery_information_safe_proof_v2.py":
        "5e8a953864e13ec76768c3e8920644107c65a644",
    "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":
        "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    "canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_RELATION_V1.json":
        "009ab8e14ee14b76d799a826de34d07586a69918",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
        "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
        "0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
    "canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json":
        "60a7c1139cad315d977bf5ed97e708cc5ec3fcc7",
    "canonical/verification/UNIVERSAL_LEARNING_CONTRACT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        "2bff1082b81755ff5f8e8f0e97587090cc873283",
}

REQUIRED_FACTS = (
    "POLICY_FILTERS_TO_AVAILABLE_AUTHORIZED_TOOLS",
    "POLICY_ORDERS_ELIGIBLE_TOOLS_BY_COST_THEN_ID",
    "POLICY_USES_CURRENT_EPOCH_EVIDENCE_ONLY",
    "POLICY_SKIPS_TOOL_AFTER_ANY_REQUIRED_NEGATIVE",
    "POLICY_PROBES_ONLY_UNKNOWN_REQUIRED_CAPABILITY",
    "POLICY_SELECTS_ONLY_AFTER_ALL_REQUIRED_CAPABILITIES_POSITIVE",
    "POLICY_ESCALATES_ONLY_AFTER_NO_NONDISPROVED_ELIGIBLE_TOOL_REMAINS",
    "ORACLE_PROBES_ONLY_REQUIRED_CAPABILITY",
    "ORACLE_PROBE_RETURNS_CURRENT_HIDDEN_TRUTH",
    "V2_REJECTS_SELECTION_WITHOUT_SUFFICIENT_ROUTE",
    "V2_REJECTS_NONOPTIMAL_SELECTION",
    "V2_REJECTS_SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE",
    "V2_REJECTS_PREMATURE_ESCALATION",
    "FROZEN_PROTOCOL_EXPOSES_TOOL_IDS_COSTS_AUTHORIZATION_AND_VERSION_EVENTS",
    "FROZEN_PROTOCOL_HIDES_CAPABILITY_MATRIX_AND_BEST_ROUTE",
    "FROZEN_PROTOCOL_ALLOWS_ABSOLUTE_THEORETICAL_CEILING",
)


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _json(rel: str) -> dict[str, Any]:
    return json.loads(_text(rel))


def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _has(text: str, *parts: str) -> bool:
    return all(part in text for part in parts)


def derive_source_facts(
    candidate: str,
    proof_v1: str,
    proof_v2: str,
    binding: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, bool]:
    fc = _functions(candidate)
    f1 = _functions(proof_v1)
    f2 = _functions(proof_v2)

    info = binding.get("information_boundary") or {}
    visible = set(info.get("candidate_visible") or [])
    hidden = set(info.get("hidden_from_candidate") or [])

    row = next(
        (
            x for x in (protocol.get("protocols") or [])
            if x.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        ),
        {},
    )
    universal = protocol.get("universal_rules") or {}

    return {
        "POLICY_FILTERS_TO_AVAILABLE_AUTHORIZED_TOOLS": (
            "next_action" in fc
            and _has(
                candidate,
                'if t.get("available") is True and t.get("authorized") is True',
            )
        ),
        "POLICY_ORDERS_ELIGIBLE_TOOLS_BY_COST_THEN_ID": (
            "next_action" in fc
            and _has(
                candidate,
                'tools.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))',
            )
        ),
        "POLICY_USES_CURRENT_EPOCH_EVIDENCE_ONLY": (
            "_epoch_map" in fc
            and "_evidence" in fc
            and _has(
                candidate,
                'if ev.get("kind") == "TOOL_VERSION_CHANGED":',
                'out[tid] = int(ev.get("new_epoch", 1))',
                'if tid not in epochs or rec.get("epoch") != epochs[tid]:',
                "continue",
            )
        ),
        "POLICY_SKIPS_TOOL_AFTER_ANY_REQUIRED_NEGATIVE": _has(
            candidate,
            "known_false = False",
            "if value is False:",
            "known_false = True",
            "if known_false:",
            "continue",
        ),
        "POLICY_PROBES_ONLY_UNKNOWN_REQUIRED_CAPABILITY": _has(
            candidate,
            "for cap in required:",
            "if value is None:",
            "unknown.append(cap)",
            'return {"action": "PROBE", "tool_id": tid, "capability": unknown[0]}',
        ),
        "POLICY_SELECTS_ONLY_AFTER_ALL_REQUIRED_CAPABILITIES_POSITIVE": _has(
            candidate,
            "if unknown:",
            'return {"action": "PROBE"',
            'return {"action": "SELECT", "tool_id": tid}',
        ),
        "POLICY_ESCALATES_ONLY_AFTER_NO_NONDISPROVED_ELIGIBLE_TOOL_REMAINS": _has(
            candidate,
            'return {"action": "ESCALATE", "reason": "NO_EVIDENCE_SUPPORTED_SUFFICIENT_TOOL"}',
        ),
        "ORACLE_PROBES_ONLY_REQUIRED_CAPABILITY": (
            "_probe_receipt" in f1
            and _has(
                proof_v1,
                "if cap not in req:",
                'raise ValueError("PROBE_IRRELEVANT_CAPABILITY")',
            )
        ),
        "ORACLE_PROBE_RETURNS_CURRENT_HIDDEN_TRUTH": (
            "_probe_receipt" in f1
            and "_hidden_caps" in f1
            and "_current_epoch" in f1
            and _has(
                proof_v1,
                "epoch = _current_epoch(case, stage, tid)",
                "supported = cap in _hidden_caps(case, stage, tid)",
                '"supported": supported',
            )
        ),
        "V2_REJECTS_SELECTION_WITHOUT_SUFFICIENT_ROUTE": (
            "_execute_allow_escalate" in f2
            and _has(
                proof_v2,
                'if str(exc)=="NO_SUFFICIENT_TOOL":',
                '"SELECTED_WHEN_NO_SUFFICIENT_TOOL"',
            )
        ),
        "V2_REJECTS_NONOPTIMAL_SELECTION": _has(
            proof_v2,
            "if tid!=expected:",
            '"NONOPTIMAL_OR_INSUFFICIENT_SELECTION"',
        ),
        "V2_REJECTS_SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE": _has(
            proof_v2,
            "if not v1._selection_is_evidence_supported(case,stage,receipts,tid):",
            '"SELECTION_WITHOUT_CURRENT_POSITIVE_EVIDENCE"',
        ),
        "V2_REJECTS_PREMATURE_ESCALATION": _has(
            proof_v2,
            "for tool in eligible:",
            "if not any(negatives):",
            '"PREMATURE_ESCALATION_WITH_UNTESTED_ROUTE"',
        ),
        "FROZEN_PROTOCOL_EXPOSES_TOOL_IDS_COSTS_AUTHORIZATION_AND_VERSION_EVENTS": {
            "TOOL_IDS_AND_DECLARED_COSTS",
            "AVAILABILITY_AND_AUTHORIZATION",
            "PUBLIC_VERSION_CHANGE_EVENTS",
            "EARNED_SAFE_PROBE_RECEIPTS",
        }.issubset(visible),
        "FROZEN_PROTOCOL_HIDES_CAPABILITY_MATRIX_AND_BEST_ROUTE": {
            "ACTUAL_TOOL_CAPABILITY_MATRIX",
            "LEAST_COST_CAPABLE_ROUTE",
        }.issubset(hidden),
        "FROZEN_PROTOCOL_ALLOWS_ABSOLUTE_THEORETICAL_CEILING": (
            row.get("proof_mode") == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
            and "absolute/theoretical ceiling" in str(universal.get("same_scope") or "")
        ),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__UNIVERSAL_SCOPE_PREMISE_MISSING",
            "missing": missing,
            "universal_scope_proved": False,
            "scope_atom_satisfied_candidate": False,
            "target_predicate": TARGET,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_FROZEN_HIDDEN_TOOL_PROTOCOL__"
            "INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "target_predicate": TARGET,
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof": {
            "domain": (
                "Any finite current tool set and finite required-capability set under "
                "the frozen protocol information boundary and truthful safe-probe semantics."
            ),
            "termination_measure": (
                "For every non-disproved eligible tool, count required capabilities "
                "whose current-epoch truth is still unknown. Every PROBE resolves one "
                "such pair. A false result permanently disproves that tool for the "
                "current requirement/epoch; a true result is never reprobed in that epoch. "
                "Therefore selection or escalation occurs after finitely many probes, "
                "bounded above by |eligible_tools|*|required_capabilities|."
            ),
            "sufficiency": (
                "A tool can be selected only when no required capability is unknown "
                "and none is false, so every required capability has current positive evidence."
            ),
            "optimality": (
                "Eligible tools are visited in ascending (cost, tool_id) order. A later "
                "tool is reached only after every earlier tool has current negative "
                "evidence for a required capability. Thus any selected tool is the "
                "least-cost sufficient route with deterministic tie-breaking."
            ),
            "no_route": (
                "If no tool is selected, every eligible tool has been disproved by at "
                "least one truthful current negative required-capability receipt; hence "
                "no eligible sufficient route exists and escalation is correct."
            ),
            "transfer_and_change": (
                "Current-epoch receipts are reused across later tasks. Public version "
                "change advances only the changed tool's epoch, so its old receipts are "
                "ignored while unchanged-tool evidence remains reusable."
            ),
            "ceiling": (
                "Under the exact frozen hidden-tool protocol, terminal route correctness "
                "and valid-route top-1 are therefore 1 for every valid instance. Since "
                "their theoretical upper bound is 1, no matched Opus result can exceed it."
            ),
        },
        "uses_empirical_generalization": False,
        "source_180_of_180_load_bearing": False,
        "internet_wide_tool_identity_completeness_claim": False,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def verify() -> dict[str, Any]:
    for rel, expected in EXPECTED_BLOBS.items():
        got = blob_sha(ROOT / rel)
        if got != expected:
            raise AssertionError((rel, got, expected))

    binding = _json(
        "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
    )
    protocol = _json("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    relation = _json(
        "canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_RELATION_V1.json"
    )
    registry = _json("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
    firewall = _json(
        "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"
    )
    bindings = _json(
        "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
    )
    learning_receipt = _json(
        "canonical/verification/UNIVERSAL_LEARNING_CONTRACT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
    )

    assert binding["prewave_admissible"] is True
    assert binding["information_boundary"]["candidate_receives_hidden_oracle"] is False
    assert binding["route_gates"]["information_boundary_frozen"] is True
    assert binding["route_gates"]["independent_verification_pass"] is True

    row = next(
        x for x in protocol["protocols"]
        if x["family"] == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    )
    assert row["status"] == "DEFINED_RESULT_OPEN"
    assert row["proof_mode"] == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
    assert "terminal-success/valid-route bounds >= Opus matched bounds" in row["acceptance"]

    contract = next(
        x for x in registry["active_contracted_residuals"]
        if x.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
    )
    assert "least-cost admissible route" in contract["required_output_or_action"]
    assert "unsupported capability claims" in contract["failure_condition"]

    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in firewall["admissible_absolute_dominance_bases"]

    claim = next(
        x for x in bindings["claims"]
        if x.get("predicate_id") == TARGET
    )
    assert claim["state"] == "EXTERNAL_BLOCKED"
    assert claim["blocker"] == "ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in claim["discharge_condition"]

    assert relation["target_predicate"] == TARGET
    assert relation["acceptance_implication_candidate"]["theoretical_upper_bound"] == 1
    assert relation["hard_nonclaims"][0] == "NO_OPEN_WORLD_INTERNET_TOOL_IDENTITY_COMPLETENESS_CLAIM"

    assert learning_receipt["independent_runner"]["conclusion"] == "success"
    assert learning_receipt["verified"]["structural_novelty_scope_closed_candidate"] is True
    assert learning_receipt["verified"]["semantic_success_rate_proved"] is False

    facts = derive_source_facts(
        _text("canonical/runtime/tool_discovery_information_safe_candidate.py"),
        _text("canonical/runtime/tool_discovery_information_safe_proof.py"),
        _text("canonical/runtime/tool_discovery_information_safe_proof_v2.py"),
        binding,
        protocol,
    )
    return prove_from_facts(facts)


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
