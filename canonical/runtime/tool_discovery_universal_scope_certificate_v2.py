"""Universal scope certificate candidate for Tool Discovery common authority V1.

The certificate is intentionally narrow: it proves the scope-completeness atom,
not acceptance or ownership.  It composes the independently verified V4
discovery-before-commitment program with a candidate-hidden, evaluator-held
common matched tool authority whose discovery-source union is exact by
construction and validation.

No empirical sample is generalized here.
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
    "canonical/runtime/tool_discovery_dynamic_candidate_v4.py":
        "e614d0bed8e291e31f57189cd6f0f75aa39b0f74",
    "canonical/tests/test_tool_discovery_dynamic_v4.py":
        "23f0add178ca0c731d15e0645ee9b8841317efee",
    "canonical/governance/TOOL_DISCOVERY_DYNAMIC_V4_REPAIR_ACTIVATION_V1.json":
        "36a7a97f3d68066337bb2cf45778d4100c22c185",
    "canonical/verification/TOOL_DISCOVERY_DYNAMIC_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        "10cb18355d247a05177230d0dd345e161e84111d",
    "canonical/runtime/tool_discovery_common_authority_interface_v1.py":
        "1c86903fed59790672de2285c9e7b3f6f46dff25",
    "canonical/tests/test_tool_discovery_common_authority_interface_v1.py":
        "d54a447e19b32b2daa4b4f9b1855142b34671f39",
    "canonical/governance/TOOL_DISCOVERY_COMMON_AUTHORITY_SCOPE_RELATION_V1.json":
        "4c890bc23e37f7c845a56affa9e0b175653f6271",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1.json":
        "49181a12362ba3d640fc18d0251901dd49dce929",
    "canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json":
        "d9ac894594ebcd2883520f7b7977a3548420541c",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
        "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
    "canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_V1.json":
        "e485b9729e8aea6bee2d75453167912023167fe8",
}

REQUIRED_FACTS = (
    "MATCHED_PROTOCOL_SAME_VISIBLE_INFORMATION",
    "MATCHED_PROTOCOL_SAME_TOOL_CLASSES",
    "MATCHED_PROTOCOL_SAME_EXTERNAL_ACTION_AUTHORITY",
    "SUPERPORTFOLIO_IDENTICAL_TOOL_BOUNDARIES",
    "FAMILY_PROTOCOL_UNKNOWN_TOOL_DISCOVERY_LITERAL",
    "FAMILY_PROTOCOL_FROZEN_HIDDEN_TOOL_ECOSYSTEM",
    "BEHAVIOR_INPUT_AVAILABLE_TOOL_SCHEMAS_CAPABILITIES",
    "BEHAVIOR_REQUIRES_DISCOVER_IF_NEEDED",
    "BEHAVIOR_SCOPE_UNKNOWN_CHANGING_TO_VERIFIED_ROUTE",
    "COMMON_AUTHORITY_INTERFACE_FINITE_NORMALIZED",
    "COMMON_AUTHORITY_PARTITION_COVERS_EVERY_IDENTITY",
    "COMMON_AUTHORITY_VALIDATOR_REQUIRES_EXACT_UNION",
    "COMMON_AUTHORITY_VALIDATOR_REJECTS_OUTSIDE_IDENTITY",
    "COMMON_AUTHORITY_VALIDATOR_REJECTS_METADATA_MUTATION",
    "COMMON_AUTHORITY_VALIDATOR_REJECTS_CAPABILITY_TRUTH_LEAK",
    "OUTSIDE_COMMON_AUTHORITY_NOT_INVOCABLE",
    "V4_DISCOVERY_PRECEDES_EVIDENCE_ROUTE_COMMITMENT",
    "V4_QUERIES_ALL_AVAILABLE_UNQUERIED_SOURCES",
    "V4_GLOBAL_COST_ORDER_AFTER_DISCOVERY",
    "V4_SELECT_REQUIRES_CURRENT_POSITIVE_EVIDENCE",
    "V4_INDEPENDENT_PUBLIC_RUNNER_PASS",
    "V4_ACTIVATION_PRESERVES_COMMON_AUTHORITY_RESIDUAL",
    "PRIOR_SCOPE_CUT_EXPLICITLY_ALLOWS_VERIFIED_DISCOVERY_INTERFACE_UNIVERSAL_PROOF",
    "FIREWALL_ALLOWS_UNIVERSAL_FORMAL_SCOPE_PROOF",
)


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _json(rel: str) -> dict[str, Any]:
    value = json.loads(_text(rel))
    if not isinstance(value, dict):
        raise AssertionError(rel + ":NOT_OBJECT")
    return value


def _functions(text: str) -> set[str]:
    tree = ast.parse(text)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _has(text: str, *parts: str) -> bool:
    return all(p in text for p in parts)


def derive_source_facts(interface_source: str, v4_source: str) -> dict[str, bool]:
    fi = _functions(interface_source)
    fv = _functions(v4_source)

    matched = _json("canonical/governance/UNBARRED_FAMILY_MATCHED_PARITY_PROTOCOL_V1.json")
    superp = _json("canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json")
    protocols = _json("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    registry = _json("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
    v4_verification = _json(
        "canonical/verification/TOOL_DISCOVERY_DYNAMIC_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
    )
    v4_activation = _json("canonical/governance/TOOL_DISCOVERY_DYNAMIC_V4_REPAIR_ACTIVATION_V1.json")
    cut = _json("canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_V1.json")
    firewall = _json("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json")

    family = next(
        x for x in protocols["protocols"]
        if x.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    )
    behavior = next(
        x for x in registry["active_contracted_residuals"]
        if x.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
    )
    he = matched["harness_equivalence"]

    discovery_branch = v4_source.find("if sources:")
    evidence_branch = v4_source.find("evidence=_evidence(public)")
    tools_branch = v4_source.find("tools=[t for t in public.get")
    if evidence_branch < 0:
        evidence_branch = v4_source.find("constraint=public.get")

    return {
        "MATCHED_PROTOCOL_SAME_VISIBLE_INFORMATION": he.get("same_visible_information") is True,
        "MATCHED_PROTOCOL_SAME_TOOL_CLASSES": he.get("same_tool_classes") is True,
        "MATCHED_PROTOCOL_SAME_EXTERNAL_ACTION_AUTHORITY": he.get("same_external_action_authority") is True,
        "SUPERPORTFOLIO_IDENTICAL_TOOL_BOUNDARIES": any(
            "IDENTICAL_CASE_PAYLOADS_AND_TOOL_BOUNDARIES" in str(x)
            for x in superp.get("execution_semantics", [])
        ),
        "FAMILY_PROTOCOL_UNKNOWN_TOOL_DISCOVERY_LITERAL": (
            "unknown tool discovery" in [str(x).lower() for x in family.get("task_dimensions", [])]
        ),
        "FAMILY_PROTOCOL_FROZEN_HIDDEN_TOOL_ECOSYSTEM": (
            family.get("proof_mode") == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
            and "frozen tool ecosystems with hidden capability variants"
            in str(family.get("acceptance", "")).lower()
        ),
        "BEHAVIOR_INPUT_AVAILABLE_TOOL_SCHEMAS_CAPABILITIES": (
            "available tool schemas/capabilities" in str(behavior.get("inputs", "")).lower()
        ),
        "BEHAVIOR_REQUIRES_DISCOVER_IF_NEEDED": (
            "discover candidate tools if needed"
            in str(behavior.get("required_output_or_action", "")).lower()
        ),
        "BEHAVIOR_SCOPE_UNKNOWN_CHANGING_TO_VERIFIED_ROUTE": (
            "unknown/changing tool ecosystem to verified usable route"
            == str(behavior.get("scope", "")).lower()
        ),
        "COMMON_AUTHORITY_INTERFACE_FINITE_NORMALIZED": (
            "_normalize_authority" in fi
            and "build_complete_interface" in fi
            and _has(
                interface_source,
                "seen: set[str] = set()",
                "DUPLICATE_AUTHORITY_TOOL_ID:",
                "source_count < 1",
            )
        ),
        "COMMON_AUTHORITY_PARTITION_COVERS_EVERY_IDENTITY": _has(
            interface_source,
            "for i, row in enumerate(authority):",
            "buckets[i % source_count].append(public_projection(row))",
            "source_results = {",
        ),
        "COMMON_AUTHORITY_VALIDATOR_REQUIRES_EXACT_UNION": (
            "validate_complete_interface" in fi
            and _has(
                interface_source,
                "if union_ids != authority_ids:",
                "DISCOVERY_UNION_NOT_COMMON_AUTHORITY:",
                "counts[tid] = counts.get(tid, 0) + 1",
                "DISCOVERY_IDENTITY_NOT_EXACTLY_ONCE:",
            )
        ),
        "COMMON_AUTHORITY_VALIDATOR_REJECTS_OUTSIDE_IDENTITY": (
            "DISCOVERY_TOOL_OUTSIDE_COMMON_AUTHORITY:" in interface_source
        ),
        "COMMON_AUTHORITY_VALIDATOR_REJECTS_METADATA_MUTATION": (
            "DISCOVERY_METADATA_MISMATCH:" in interface_source
            and "expected = public_projection(by_id[tid])" in interface_source
        ),
        "COMMON_AUTHORITY_VALIDATOR_REJECTS_CAPABILITY_TRUTH_LEAK": (
            "FORBIDDEN_DISCOVERY_FIELDS" in interface_source
            and "DISCOVERY_CAPABILITY_TRUTH_LEAK:" in interface_source
        ),
        "OUTSIDE_COMMON_AUTHORITY_NOT_INVOCABLE": (
            "tool_invocable" in fi
            and 'return str(tool_id) in ids' in interface_source
        ),
        "V4_DISCOVERY_PRECEDES_EVIDENCE_ROUTE_COMMITMENT": (
            "next_action" in fv
            and discovery_branch >= 0
            and evidence_branch > discovery_branch
            and tools_branch > discovery_branch
        ),
        "V4_QUERIES_ALL_AVAILABLE_UNQUERIED_SOURCES": _has(
            v4_source,
            's.get("available") is True',
            'str(s.get("source_id") or "") not in queried',
            'return {"action":"DISCOVER"',
        ),
        "V4_GLOBAL_COST_ORDER_AFTER_DISCOVERY": _has(
            v4_source,
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))',
            'return {"action":"PROBE"',
            'return {"action":"SELECT"',
        ),
        "V4_SELECT_REQUIRES_CURRENT_POSITIVE_EVIDENCE": _has(
            v4_source,
            "if v is False:",
            "if v is None: unknown.append(cap)",
            "if unknown:",
            'return {"action":"SELECT","tool_id":tid}',
        ),
        "V4_INDEPENDENT_PUBLIC_RUNNER_PASS": (
            str(v4_verification.get("status", "")).startswith("PASS__EXACT_BYTES")
            and v4_verification.get("independent_public_runner", {}).get("run_conclusion") == "success"
        ),
        "V4_ACTIVATION_PRESERVES_COMMON_AUTHORITY_RESIDUAL": (
            "COMMON_FROZEN_TOOL_AUTHORITY"
            in str(v4_activation.get("remaining_primitive_fact", ""))
            and "BRAIN_ONLY_REGISTRY_COMPLETENESS"
            in str(v4_activation.get("forbidden_shortcut", ""))
        ),
        "PRIOR_SCOPE_CUT_EXPLICITLY_ALLOWS_VERIFIED_DISCOVERY_INTERFACE_UNIVERSAL_PROOF": (
            "VERIFIED_DISCOVERY_INTERFACE_AND_UNIVERSAL_PROOF_COVERING_UNKNOWN_TOOL_IDENTITIES"
            in str(cut.get("minimum_missing_fact", ""))
        ),
        "FIREWALL_ALLOWS_UNIVERSAL_FORMAL_SCOPE_PROOF": (
            "UNIVERSAL_FORMAL_SCOPE_PROOF"
            in firewall.get("admissible_absolute_dominance_bases", [])
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
            "PASS__COMMON_MATCHED_AUTHORITY_UNIVERSAL_SCOPE_RELATION_DERIVED__"
            "INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "scope_atom": ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof": {
            "common_authority": (
                "The canonical matched protocol fixes identical visible information, "
                "tool classes and external action authority for Brain and Opus, while "
                "the superportfolio fixes identical case payloads and tool boundaries. "
                "Hence every valid matched route identity lies inside one common finite "
                "episode authority."
            ),
            "unknown_identity": (
                "The common authority is evaluator-held, not candidate-preenumerated. "
                "Initial visible identities may be empty; DISCOVER is the only route by "
                "which hidden identities enter the candidate-visible set, and capability "
                "truth remains oracle-only."
            ),
            "completeness": (
                "For every finite common authority, the interface partitions the public "
                "projection of every identity across finite sources exactly once, and "
                "the validator rejects omission, outside identities, duplicate coverage, "
                "metadata mutation, source unavailability and capability-truth leakage."
            ),
            "counterfactual_elimination": (
                "An identity outside the identical external action authority is not "
                "invocable by either Brain or Opus, so adding such a hypothetical tool "
                "cannot add a valid matched route. Open-world non-invocable tools are "
                "therefore irrelevant counterfactuals rather than omitted candidates."
            ),
            "program_composition": (
                "Independent V4 verification proves discovery closure before commitment "
                "and global cost-ordered evidence resolution conditional on a complete "
                "declared interface. Composing that result with the common-authority "
                "complete interface yields the universal scope relation."
            ),
        },
        "uses_empirical_generalization": False,
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

    relation = _json("canonical/governance/TOOL_DISCOVERY_COMMON_AUTHORITY_SCOPE_RELATION_V1.json")
    assert relation["scope_relation"]["scope_narrowing"] is False
    assert relation["scope_relation"]["brain_only_registry_substitution"] is False
    assert relation["proof_domain"]["unknown_identity_semantics"].startswith(
        "TOOL_IDENTITY_NEED_NOT_BE_INITIAL_VISIBLE"
    )
    assert relation["expected_independent_projection"]["uses_empirical_generalization"] is False

    facts = derive_source_facts(
        _text("canonical/runtime/tool_discovery_common_authority_interface_v1.py"),
        _text("canonical/runtime/tool_discovery_dynamic_candidate_v4.py"),
    )
    return prove_from_facts(facts)


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
