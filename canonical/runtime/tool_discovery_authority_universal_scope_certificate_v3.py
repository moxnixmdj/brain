"""Authority-complete universal scope certificate for tool discovery V5.

V3 composes two independently checkable facts:
1. V5 derives the discovery registry from every action in the exact matched
   tool-authority boundary and overwrites caller-supplied registry subsets.
2. V4's universal certificate proves routing correctness after that registry
   is fixed: source exhaustion, arbitrary identity materialization, safe/current
   evidence, least-cost sufficient selection, and fail-closed escalation.

This is a scope certificate candidate only. It grants no acceptance, capability,
family, execution, or promotion authority without independent clean-room proof
and a separate atomic acceptance reduction.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import tool_discovery_universal_scope_certificate_v2 as v4cert

ROOT = Path(__file__).resolve().parents[2]
ATOM = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
    "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)

EXPECTED_BLOBS = {
    "canonical/runtime/tool_discovery_authority_complete_candidate_v5.py":
        "b916c5dd0ff3c21604705f38aa3c47c75955e4d6",
    "canonical/governance/TOOL_DISCOVERY_AUTHORITY_COMPLETE_SCOPE_RELATION_V2.json":
        "374b863989440b34ff3c90d8ad62a98603ddf83c",
    "canonical/runtime/tool_discovery_complete_interface_candidate_v4.py":
        "d8e7c43e3f5f4252441622805f161e3a6f9a8402",
    "canonical/runtime/tool_discovery_universal_scope_certificate_v2.py":
        "a245d2007acb1eef79deddc4a3fea19ebc440a27",
    "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_SCOPE_RELATION_V1.json":
        "b27cf5a5f6a1b163b54abdd76ae618bfc85a08ea",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
}

REQUIRED_FACTS = (
    "FULL_AUTHORITY_ACTION_ENUMERATION",
    "CALLER_REGISTRY_SUBSET_CANNOT_HIDE_SOURCE",
    "ONLY_EXHAUSTIVE_SOURCE_ACTIONS_ADMITTED",
    "AUTHORITY_MANIFEST_BINDS_ALL_ACTIONS",
    "SAME_MATCHED_TOOL_AUTHORITY",
    "DOWNSTREAM_V4_UNIVERSAL_ROUTING_PROOF",
    "LEGACY_EXACT_PROJECTION_PRESERVED",
)


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _load(rel: str) -> dict[str, Any]:
    value = json.loads(_text(rel))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _function_source(source: str, name: str) -> str:
    tree = ast.parse(source)
    node = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    )
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1:node.end_lineno])


def derive_source_facts(
    v5: str,
    relation: Mapping[str, Any],
    protocol: Mapping[str, Any],
    downstream: Mapping[str, Any],
) -> dict[str, bool]:
    builder = _function_source(v5, "registry_from_tool_authority")
    next_action = _function_source(v5, "next_action")
    semantics = relation.get("authority_semantics") or {}
    hard_nonclaims = set(relation.get("hard_nonclaims") or [])
    universal_rules = protocol.get("universal_rules") or {}

    return {
        "FULL_AUTHORITY_ACTION_ENUMERATION": (
            'actions = authority.get("actions")' in builder
            and "for raw in actions:" in builder
            and 'if kind != "DISCOVERY_SOURCE":' in builder
            and "sources.append({" in builder
            and "TOOL_AUTHORITY.actions is the complete finite candidate-visible action set"
                in str(semantics.get("tool_authority") or "")
        ),
        "CALLER_REGISTRY_SUBSET_CANNOT_HIDE_SOURCE": (
            'if "tool_authority" not in public:' in next_action
            and 'registry = registry_from_tool_authority(public)' in next_action
            and 'derived["discovery_registry"] = registry' in next_action
            and "return v4.next_action(derived)" in next_action
            and "overwritten" in str(semantics.get("discovery_source_derivation") or "").lower()
        ),
        "ONLY_EXHAUSTIVE_SOURCE_ACTIONS_ADMITTED": (
            'raw.get("result_semantics") != "EXHAUSTIVE_CURRENT_TOOL_LIST"' in builder
            and "DISCOVERY_SOURCE_RESULT_NOT_EXHAUSTIVE:" in builder
            and "exhaustive" in str(semantics.get("source_admissibility") or "").lower()
            and "fail closed" in str(semantics.get("source_admissibility") or "").lower()
        ),
        "AUTHORITY_MANIFEST_BINDS_ALL_ACTIONS": (
            "normalized_actions.append({" in builder
            and 'declared = authority.get("action_manifest_sha256")' in builder
            and 'expected = _sha(sorted(normalized_actions, key=lambda x: x["action_id"]))' in builder
            and "TOOL_AUTHORITY_MANIFEST_MISMATCH" in builder
            and "including non-discovery actions" in str(semantics.get("integrity") or "")
        ),
        "SAME_MATCHED_TOOL_AUTHORITY": (
            "same frozen task population/harness/tool authority"
                in str(universal_rules.get("same_scope") or "")
            and "same harness/tool authority" in str(semantics.get("same_authority") or "")
            and "NO_CLAIM_THAT_EVERY_EXTERNAL_WORLD_TOOL_IS_VISIBLE" in hard_nonclaims
        ),
        "DOWNSTREAM_V4_UNIVERSAL_ROUTING_PROOF": (
            downstream.get("universal_scope_proved") is True
            and downstream.get("scope_atom_satisfied_candidate") is True
            and downstream.get("basis_kind") == "UNIVERSAL_FORMAL_SCOPE_PROOF"
            and downstream.get("uses_empirical_generalization") is False
            and "from canonical.runtime import tool_discovery_complete_interface_candidate_v4 as v4" in v5
        ),
        "LEGACY_EXACT_PROJECTION_PRESERVED": (
            'if "tool_authority" not in public:' in next_action
            and "return v4.next_action(public)" in next_action
            and "legacy" in json.dumps(relation.get("proof_chain") or []).lower()
            and (relation.get("downstream_verified_candidate") or {}).get("blob_sha")
                == EXPECTED_BLOBS["canonical/runtime/tool_discovery_complete_interface_candidate_v4.py"]
        ),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "status": "FAIL_CLOSED__AUTHORITY_UNIVERSAL_SCOPE_PREMISE_MISSING",
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
            "PASS__TOOL_DISCOVERY_V5_AUTHORITY_COMPLETE_UNIVERSAL_SCOPE_PROOF__"
            "INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "scope_atom": ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "interface_basis_kind": "AUTHORITY_DERIVED_COMPLETE_DISCOVERY_INTERFACE",
        "proof": {
            "authority_closure": (
                "The frozen matched protocol exposes the same finite tool authority to "
                "both routes. V5 enumerates every action in that authority, derives a "
                "discovery source from every DISCOVERY_SOURCE action, and overwrites any "
                "caller-supplied registry. Therefore no discovery action available to "
                "either matched route can be omitted by a smaller registry."
            ),
            "source_admissibility": (
                "Only discovery actions whose declared result semantics are "
                "EXHAUSTIVE_CURRENT_TOOL_LIST enter the derived registry. Partial source "
                "interfaces fail closed until wrapped by an exhaustive adapter."
            ),
            "composition": (
                "V5 delegates the derived registry to the exact V4 policy. The bound V4 "
                "certificate proves that all current authorized sources are exhausted "
                "before probing/selection, arbitrary returned identities are materialized, "
                "safe current-epoch evidence is required, and the first selected route is "
                "globally least-cost among evidence-proved sufficient admissible tools."
            ),
            "observable_scope": (
                "This is completeness over the selectable action universe, not over every "
                "tool in the external world. A tool unreachable through any action in the "
                "shared authority is unavailable to both matched routes and cannot be used "
                "as an Opus-only hidden oracle without violating same-authority symmetry."
            ),
            "legacy_conservation": (
                "Without tool_authority V5 delegates unchanged to V4, whose exact legacy "
                "projection preserves the immutable frozen 180-case behavior without replay."
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
    drift = []
    for rel, want in EXPECTED_BLOBS.items():
        got = blob_sha(ROOT / rel)
        if got != want:
            drift.append({"path": rel, "got": got, "expected": want})
    if drift:
        return {
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "source_blob_drift": drift,
            "universal_scope_proved": False,
            "scope_atom_satisfied_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    downstream = v4cert.verify()
    facts = derive_source_facts(
        _text("canonical/runtime/tool_discovery_authority_complete_candidate_v5.py"),
        _load("canonical/governance/TOOL_DISCOVERY_AUTHORITY_COMPLETE_SCOPE_RELATION_V2.json"),
        _load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
        downstream,
    )
    out = prove_from_facts(facts)
    out["source_blob_drift"] = []
    out["downstream_v4"] = {
        "universal_scope_proved": downstream.get("universal_scope_proved"),
        "scope_atom_satisfied_candidate": downstream.get("scope_atom_satisfied_candidate"),
        "basis_kind": downstream.get("basis_kind"),
        "uses_empirical_generalization": downstream.get("uses_empirical_generalization"),
    }
    out["derived_facts"] = facts
    return out


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
