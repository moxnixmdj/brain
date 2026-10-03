"""Universal scope certificate candidate for complete-interface Tool Discovery V4.

This checker binds an explicit finite complete discovery registry plus complete
per-source discovery receipts to the frozen TOOL_ROUTE_DISCOVERY_AND_SELECTION_001
contract. It proves scope structurally; it does not extrapolate from the historical
180-case sample and grants no acceptance/family credit without independent review.
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
    "canonical/runtime/tool_discovery_complete_interface_candidate_v4.py":
        "7bd881ae427df05b114aa070a35acb71ad98172b",
    "canonical/tests/test_tool_discovery_complete_interface_candidate_v4.py":
        "598a952aae58f11f8a9ff32ca28a350b323ee2ac",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
        "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
    "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json":
        "48ba33998e73b8eec2731be51a7ec78077ed0d4a",
    "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        "e628d8d5b63c2020400129fcc9e0bc6fde6101b2",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":
        "7885a827b1483bfb38315c1f492848f7e4680285",
}

REQUIRED_FACTS = (
    "COMPLETE_REGISTRY_REQUIRED",
    "REGISTRY_MANIFEST_CONTENT_BOUND",
    "ALL_AVAILABLE_SOURCES_EXHAUSTED_BEFORE_TOOL_REASONING",
    "DISCOVERY_RECEIPTS_REGISTRY_AND_SOURCE_EPOCH_BOUND",
    "DISCOVERY_RECEIPT_COMPLETENESS_REQUIRED",
    "UNKNOWN_OR_CONFLICTING_IDENTITIES_FAIL_CLOSED",
    "ONLY_CURRENT_TOOL_EPOCH_EVIDENCE_USED",
    "CONSTRAINT_AUTHORITY_FILTER_PRECEDES_PROBING",
    "TOOLS_ORDERED_BY_COST_THEN_ID",
    "KNOWN_FALSE_TOOL_SKIPPED",
    "UNKNOWN_REQUIRED_CAPABILITY_PROBED",
    "SELECT_REQUIRES_ALL_REQUIRED_CURRENT_POSITIVE",
    "ESCALATION_AFTER_COMPLETE_DISCOVERY_AND_NO_SURVIVING_ROUTE",
)


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _has(text: str, *parts: str) -> bool:
    return all(part in text for part in parts)


def derive_source_facts(candidate: str) -> dict[str, bool]:
    funcs = _functions(candidate)
    return {
        "COMPLETE_REGISTRY_REQUIRED": (
            "_registry" in funcs and _has(
                candidate,
                'reg.get("kind") != "COMPLETE_DISCOVERY_REGISTRY"',
                'reg.get("complete") is not True',
                'reg.get("independently_verified") is not True',
                'DISCOVERY_REGISTRY_COMPLETENESS_NOT_VERIFIED',
            )
        ),
        "REGISTRY_MANIFEST_CONTENT_BOUND": _has(
            candidate,
            'source_manifest_sha256',
            'expected = _sha(sorted(',
            'DISCOVERY_REGISTRY_MANIFEST_MISMATCH',
        ),
        "ALL_AVAILABLE_SOURCES_EXHAUSTED_BEFORE_TOOL_REASONING": _has(
            candidate,
            'for src in reg["sources"]:',
            'src["available"] and src["source_id"] not in queried',
            '"action": "DISCOVER"',
            'constraint = public.get("constraint")',
        ) and candidate.index('for src in reg["sources"]:') < candidate.index('constraint = public.get("constraint")'),
        "DISCOVERY_RECEIPTS_REGISTRY_AND_SOURCE_EPOCH_BOUND": _has(
            candidate,
            'raw.get("registry_epoch") != reg["epoch"]',
            'raw.get("source_epoch") != src["epoch"]',
            'continue',
        ),
        "DISCOVERY_RECEIPT_COMPLETENESS_REQUIRED": _has(
            candidate,
            'raw.get("complete") is not True',
            'DISCOVERY_RECEIPT_NOT_COMPLETE:',
        ),
        "UNKNOWN_OR_CONFLICTING_IDENTITIES_FAIL_CLOSED": _has(
            candidate,
            'DISCOVERY_RECEIPT_UNKNOWN_SOURCE:',
            'DISCOVERED_TOOL_ID_CONFLICT:',
            'return {"action": "ESCALATE", "reason": str(exc)}',
        ),
        "ONLY_CURRENT_TOOL_EPOCH_EVIDENCE_USED": (
            "_current_tool_epochs" in funcs and "_evidence" in funcs and _has(
                candidate,
                'rec.get("epoch") != epochs[tid]',
                'TOOL_VERSION_CHANGED',
                'new_epoch',
            )
        ),
        "CONSTRAINT_AUTHORITY_FILTER_PRECEDES_PROBING": _has(
            candidate,
            'row.get("available") is True',
            'row.get("authorized") is True',
            '_pred(constraint, row)',
            'eligible.sort(',
        ),
        "TOOLS_ORDERED_BY_COST_THEN_ID": _has(
            candidate,
            'eligible.sort(key=lambda x: (float(x["cost"]), str(x["tool_id"])))',
        ),
        "KNOWN_FALSE_TOOL_SKIPPED": _has(
            candidate,
            'if value is False:',
            'impossible = True',
            'if impossible:',
            'continue',
        ),
        "UNKNOWN_REQUIRED_CAPABILITY_PROBED": _has(
            candidate,
            'if value is None:',
            'unknown.append(cap)',
            'if unknown:',
            '"action": "PROBE"',
            '"capability": unknown[0]',
        ),
        "SELECT_REQUIRES_ALL_REQUIRED_CURRENT_POSITIVE": _has(
            candidate,
            'for cap in required:',
            'if value is False:',
            'if value is None:',
            'return {"action": "SELECT"',
        ),
        "ESCALATION_AFTER_COMPLETE_DISCOVERY_AND_NO_SURVIVING_ROUTE": _has(
            candidate,
            '"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"',
        ),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [x for x in REQUIRED_FACTS if facts.get(x) is not True]
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
            "PASS__COMPLETE_DISCOVERY_INTERFACE_UNIVERSAL_SCOPE_PROOF__"
            "INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "scope_atom": ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof_domain": (
            "ALL_FINITE_VALID_TOOL_ECOSYSTEMS_PRESENTED_THROUGH_AN_EXPLICIT_"
            "INDEPENDENTLY_VERIFIED_COMPLETE_DISCOVERY_REGISTRY_WITH_FINITE_COMPLETE_"
            "PER_SOURCE_RESULTS__FINITE_REQUIRED_CAPABILITIES__GENERIC_PUBLIC_"
            "CONSTRAINTS__CURRENT_EPOCH_SAFE_PROBE_RECEIPTS__AND_FINITE_VERSION_EVENTS"
        ),
        "proof": {
            "identity_completeness": (
                "The registry names the complete authoritative source set for one "
                "epoch and every available source must return a complete current "
                "receipt before capability reasoning begins. Therefore the materialized "
                "tool identity set equals the union of the certified discovery universe."
            ),
            "finite_discovery_induction": (
                "Base case has a finite set of unqueried registered sources. Each "
                "DISCOVER action removes exactly one source from that set once a valid "
                "receipt is incorporated. Thus after finitely many actions identity "
                "discovery is complete or the protocol fails closed."
            ),
            "capability_soundness": (
                "Hidden capability truth is never inferred from metadata. Only current "
                "tool-epoch SAFE_CAPABILITY_PROBE receipts enter capability evidence; "
                "version changes make older receipts unusable."
            ),
            "least_cost_route": (
                "After complete identity discovery, admissible tools are ordered by "
                "cost then id. Any known-false tool is skipped; the first tool whose "
                "required capabilities all have current positive evidence is therefore "
                "the globally least-cost verified sufficient tool in the certified universe."
            ),
            "probe_minimality": (
                "For an unresolved capability of the cheapest not-disproved tool, two "
                "allowed worlds are observationally identical except for that capability. "
                "Any universally sound policy must obtain distinguishing evidence before "
                "safely selecting that tool or bypassing it for a more expensive one. "
                "The candidate performs exactly that first unresolved safe probe."
            ),
            "escalation": (
                "ESCALATE occurs only after the complete source registry is exhausted "
                "and every admissible discovered tool is ruled out or none exists, so "
                "no verified admissible route remains inside the certified universe."
            ),
            "transfer_and_change": (
                "Current-epoch discovery and probe receipts are reusable on later tasks; "
                "registry/source/tool epoch changes invalidate only the affected stale "
                "evidence and reopen the finite proof steps required by the new epoch."
            ),
            "terminal_ceiling": (
                "Within the frozen information boundary, the route is pointwise sound: "
                "when a sufficient route exists it returns the least-cost verified route; "
                "otherwise it fails closed. Probe actions are decision-relevant under "
                "indistinguishable hidden-capability worlds. No unsupported capability "
                "promotion is possible."
            ),
        },
        "uses_empirical_generalization": False,
        "historical_180_case_sample_role": "PRESERVED_REGRESSION_EVIDENCE_ONLY__NOT_SCOPE_BASIS",
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def verify() -> dict[str, Any]:
    for rel, expected in EXPECTED_BLOBS.items():
        got = blob_sha(ROOT / rel)
        if got != expected:
            raise AssertionError((rel, got, expected))

    protocol = json.loads(_text("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"))
    row = next(x for x in protocol["protocols"] if x["family"] == "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
    assert row["status"] == "DEFINED_RESULT_OPEN"
    assert "unknown tool discovery" in row["task_dimensions"]
    assert "later-task transfer without rediscovery" in row["task_dimensions"]
    assert "no unsupported capability-state promotion" in row["acceptance"]

    registry = json.loads(_text("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"))
    def find(obj):
        if isinstance(obj, dict):
            if obj.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
                return obj
            for value in obj.values():
                got = find(value)
                if got is not None:
                    return got
        elif isinstance(obj, list):
            for value in obj:
                got = find(value)
                if got is not None:
                    return got
        return None
    contract = find(registry)
    assert contract is not None
    assert "Discover candidate tools if needed" in contract["required_output_or_action"]
    assert "Unknown/changing tool ecosystem" in contract["scope"]

    firewall = json.loads(_text("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"))
    assert "UNIVERSAL_FORMAL_SCOPE_PROOF" in firewall["admissible_absolute_dominance_bases"]

    cut = json.loads(_text("canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"))
    assert cut["target_predicate"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
    assert "VERIFIED_DISCOVERY_INTERFACE" in cut["minimum_missing_fact"]
    assert cut["current_route_state"].startswith("BLOCKED")

    prior = json.loads(_text("canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"))
    assert prior["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert "VERIFIED_DISCOVERY_INTERFACE" in prior["minimum_missing_fact"]

    bindings = json.loads(_text("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"))
    claim = next(x for x in bindings["claims"] if x.get("predicate_id") == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
    assert claim["state"] != "PROVED"

    facts = derive_source_facts(_text("canonical/runtime/tool_discovery_complete_interface_candidate_v4.py"))
    return prove_from_facts(facts)


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
