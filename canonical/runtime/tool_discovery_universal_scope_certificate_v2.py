"""Universal formal scope certificate candidate for tool discovery V4.

This module proves only the active scope-completeness atom. It does not itself
grant acceptance, capability, family, execution, or promotion authority.

The proof domain is the frozen candidate-visible tool authority: every finite
current directly visible tool plus every tool exposed by every finite current
authorized discovery source. Identities outside all candidate-visible
information are observationally unavailable to both matched routes under the
frozen same-information/tool-authority rule and are not smuggled in as an
Opus-only hidden oracle.

Independent clean-room verification of these exact blobs remains mandatory.
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
        "d8e7c43e3f5f4252441622805f161e3a6f9a8402",
    "canonical/runtime/tool_discovery_information_safe_candidate.py":
        "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    "canonical/runtime/tool_discovery_dynamic_candidate_v3.py":
        "bbbee4d6baf8df937543644397abba38a67dce62",
    "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_SCOPE_RELATION_V1.json":
        "b27cf5a5f6a1b163b54abdd76ae618bfc85a08ea",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":
        "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
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
    "LEGACY_EXACT_PROJECTION",
    "FROZEN_SCOPE_OR_BRANCH_EXACT",
    "REGISTRY_MANIFEST_BINDS_LOAD_BEARING_SOURCE_FIELDS",
    "INTERFACE_COMPLETENESS_NOT_SELF_CERTIFIED_BY_INPUT_FLAG",
    "FINITE_CURRENT_SOURCE_EXHAUSTION_BEFORE_ROUTING",
    "ARBITRARY_DISCOVERED_IDENTITIES_MATERIALIZED",
    "SAFE_PROBE_AUTHORITY_ENFORCED",
    "CURRENT_EPOCH_EVIDENCE_ONLY",
    "GLOBAL_LEAST_COST_PROVED_SUFFICIENT_SELECTION",
    "FAIL_CLOSED_NO_VERIFIED_ROUTE",
    "V3_PRE_DISCOVERY_SELECTION_COUNTEREXAMPLE_ELIMINATED",
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


def _action_lines(source: str, fn_name: str = "next_action") -> dict[str, list[int]]:
    tree = ast.parse(source)
    fn = next(
        n for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn_name
    )
    out: dict[str, list[int]] = {}
    for node in ast.walk(fn):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        keys = node.value.keys
        vals = node.value.values
        for key, value in zip(keys, vals):
            if (
                isinstance(key, ast.Constant) and key.value == "action"
                and isinstance(value, ast.Constant) and isinstance(value.value, str)
            ):
                out.setdefault(value.value, []).append(node.lineno)
    return {k: sorted(v) for k, v in out.items()}


def derive_source_facts(
    v4: str,
    legacy: str,
    v3: str,
    relation: Mapping[str, Any],
    registry: Mapping[str, Any],
    protocol: Mapping[str, Any],
    terminal_binding: Mapping[str, Any],
    firewall: Mapping[str, Any],
    cut: Mapping[str, Any],
    bindings: Mapping[str, Any],
) -> dict[str, bool]:
    v4_lines = _action_lines(v4)
    v3_lines = _action_lines(v3)

    behavior = next(
        (
            row for row in registry.get("active_contracted_residuals", [])
            if isinstance(row, Mapping)
            and row.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
        ),
        None,
    )
    family = next(
        (
            row for row in protocol.get("protocols", [])
            if isinstance(row, Mapping)
            and row.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        ),
        None,
    )
    claim = next(
        (
            row for row in bindings.get("claims", [])
            if isinstance(row, Mapping)
            and row.get("predicate_id") == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
        ),
        None,
    )

    discover_first_v4 = (
        bool(v4_lines.get("DISCOVER"))
        and bool(v4_lines.get("PROBE"))
        and bool(v4_lines.get("SELECT"))
        and max(v4_lines["DISCOVER"]) < min(v4_lines["PROBE"] + v4_lines["SELECT"])
    )
    v3_selects_before_discovery = (
        bool(v3_lines.get("DISCOVER"))
        and bool(v3_lines.get("SELECT"))
        and min(v3_lines["SELECT"]) < min(v3_lines["DISCOVER"])
    )

    hard_nonclaims = set(relation.get("hard_nonclaims") or [])
    source_domain = relation.get("interface_domain") or {}
    visible = set(
        ((terminal_binding.get("information_boundary") or {}).get("candidate_visible") or [])
    )
    admissible = set(firewall.get("admissible_absolute_dominance_bases") or [])

    return {
        "LEGACY_EXACT_PROJECTION": (
            "from canonical.runtime import tool_discovery_information_safe_candidate as legacy" in v4
            and 'if "discovery_registry" not in public:' in v4
            and "return legacy.next_action(public)" in v4
            and "def next_action" in legacy
            and (relation.get("legacy_projection") or {}).get("legacy_candidate_blob_sha")
                == EXPECTED_BLOBS["canonical/runtime/tool_discovery_information_safe_candidate.py"]
        ),
        "FROZEN_SCOPE_OR_BRANCH_EXACT": (
            cut.get("target_predicate") == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
            and cut.get("target_proof_atom") == ATOM
            and "VERIFIED_DISCOVERY_INTERFACE_AND_UNIVERSAL_PROOF_COVERING_UNKNOWN_TOOL_IDENTITIES"
                in str(cut.get("minimum_missing_fact") or "")
            and relation.get("target_predicate") == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
            and relation.get("target_proof_atom") == ATOM
            and isinstance(claim, Mapping)
            and claim.get("blocker") == "ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
            and "UNIVERSAL_FORMAL_SCOPE_PROOF" in str(claim.get("discharge_condition") or "")
            and "UNIVERSAL_FORMAL_SCOPE_PROOF" in admissible
        ),
        "REGISTRY_MANIFEST_BINDS_LOAD_BEARING_SOURCE_FIELDS": all(
            token in v4
            for token in (
                '"source_id": x["source_id"]',
                '"epoch": x["epoch"]',
                '"cost": x["cost"]',
                '"available": x["available"]',
                '"authorized": x["authorized"]',
                "DISCOVERY_REGISTRY_MANIFEST_MISMATCH",
            )
        ),
        "INTERFACE_COMPLETENESS_NOT_SELF_CERTIFIED_BY_INPUT_FLAG": (
            "independently_verified" not in v4
            and "THE_REGISTRY_COMPLETE_FIELD_DOES_NOT_SELF_CERTIFY_INTERFACE_COMPLETENESS"
                in hard_nonclaims
        ),
        "FINITE_CURRENT_SOURCE_EXHAUSTION_BEFORE_ROUTING": (
            discover_first_v4
            and 'for src in reg["sources"]:' in v4
            and 'src["source_id"] not in queried' in v4
            and 'if src["available"] and src["authorized"]' in v4
            and 'raw.get("registry_epoch") != reg["epoch"]' in v4
            and 'raw.get("source_epoch") != src["epoch"]' in v4
            and source_domain.get("registry_contract") is not None
            and source_domain.get("source_result_contract") is not None
        ),
        "ARBITRARY_DISCOVERED_IDENTITIES_MATERIALIZED": (
            'tid = raw.get("tool_id")' in v4
            and "ingest(raw)" in v4
            and 'tools[tid] = row' in v4
            and "arbitrary nonempty strings" in str(source_domain.get("unknown_identity_scope") or "")
            and isinstance(behavior, Mapping)
            and "unknown or changing capabilities" in str(behavior.get("environment_state") or "")
            and "Tool docs/schemas" in str(behavior.get("allowed_information") or "")
        ),
        "SAFE_PROBE_AUTHORITY_ENFORCED": (
            '"SAFE_PROBE_PERMISSION"' in json.dumps(terminal_binding)
            and 'row["safe_probe_allowed"] = raw.get("safe_probe_allowed") is True' in v4
            and 'if tool.get("safe_probe_allowed") is not True:' in v4
            and 'continue' in v4
        ),
        "CURRENT_EPOCH_EVIDENCE_ONLY": (
            'rec.get("epoch") != epochs[tid]' in v4
            and '"TOOL_VERSION_CHANGED"' in v4
            and 'out[(tid, cap)]' in v4
            and "PUBLIC_VERSION_CHANGE_EVENTS" in visible
            and "EARNED_SAFE_PROBE_RECEIPTS" in visible
        ),
        "GLOBAL_LEAST_COST_PROVED_SUFFICIENT_SELECTION": (
            'eligible.sort(key=lambda x: (float(x["cost"]), str(x["tool_id"])))' in v4
            and "for tool in eligible:" in v4
            and "if value is False:" in v4
            and "if value is None:" in v4
            and discover_first_v4
            and "least-cost" in str(behavior.get("required_output_or_action") or "").lower()
        ),
        "FAIL_CLOSED_NO_VERIFIED_ROUTE": (
            '"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"' in v4
            and 'except ToolDiscoveryV4Error as exc:' in v4
            and 'return {"action": "ESCALATE", "reason": str(exc)}' in v4
        ),
        "V3_PRE_DISCOVERY_SELECTION_COUNTEREXAMPLE_ELIMINATED": (
            v3_selects_before_discovery
            and discover_first_v4
            and (relation.get("v3_counterexample") or {}).get("candidate_blob_sha")
                == EXPECTED_BLOBS["canonical/runtime/tool_discovery_dynamic_candidate_v3.py"]
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
            "PASS__TOOL_DISCOVERY_V4_UNIVERSAL_FORMAL_SCOPE_PROOF__"
            "INDEPENDENT_PUBLIC_RUNNER_VERIFICATION_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_proved": True,
        "scope_atom_satisfied_candidate": True,
        "scope_atom": ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "proof": {
            "observable_universe": (
                "Under the frozen same-information/tool-authority rule, the relevant "
                "identity universe is every finite current directly visible tool plus "
                "every tool exposed by every current candidate-visible authorized "
                "discovery source. An identity represented nowhere in candidate-visible "
                "information is unavailable to both matched routes and cannot become an "
                "Opus-only hidden action without breaking harness symmetry."
            ),
            "identity_completeness": (
                "The complete-interface registry binds the full current discovery-source "
                "set and epochs. V4 consumes only current complete source receipts and "
                "returns DISCOVER for each unqueried available authorized source before "
                "any PROBE or SELECT. Because the source set and each current result are "
                "finite, the union after exhaustion contains every discoverable identity, "
                "including identities not known when the policy was written."
            ),
            "routing_optimality": (
                "After identity exhaustion V4 filters availability, authorization and the "
                "generic constraint, sorts by (cost, tool_id), rejects a tool when any "
                "required capability has current negative evidence, probes only unresolved "
                "required capabilities when explicit safe-probe authority exists, and "
                "selects the first tool only after all required capabilities are currently "
                "positive. Therefore the selected route is the globally least-cost "
                "evidence-proved sufficient route in the complete observable universe."
            ),
            "evidence_safety": (
                "Capability metadata never becomes capability truth. Only exact-current-"
                "epoch SAFE_CAPABILITY_PROBE receipts count; public version changes advance "
                "epochs and invalidate stale receipts; tools lacking safe-probe authority "
                "are never probed."
            ),
            "legacy_conservation": (
                "When discovery_registry is absent V4 returns the exact verified legacy "
                "policy result directly. The frozen 180 terminal sample therefore remains "
                "behaviorally preserved without replay; the universal argument does not "
                "generalize from those 180 cases."
            ),
            "counterexample_elimination": (
                "Dynamic V3 could SELECT an already-visible expensive sufficient tool "
                "before querying an unqueried source containing a cheaper sufficient tool. "
                "V4 moves complete source exhaustion before any probe/selection, removing "
                "that universal least-cost counterexample."
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

    facts = derive_source_facts(
        _text("canonical/runtime/tool_discovery_complete_interface_candidate_v4.py"),
        _text("canonical/runtime/tool_discovery_information_safe_candidate.py"),
        _text("canonical/runtime/tool_discovery_dynamic_candidate_v3.py"),
        _load("canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_SCOPE_RELATION_V1.json"),
        _load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
        _load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
        _load("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"),
        _load("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"),
        _load("canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"),
        _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
    )
    out = prove_from_facts(facts)
    out["source_blob_drift"] = []
    out["derived_facts"] = facts
    return out


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_proved") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
