"""Fail-closed scope-proof compiler for the owned exhaustive Tool Discovery route.

This checker binds the exact frozen target, reproduces the Dynamic V3 counterexample,
and verifies that the replacement route has the structural premises used by the
universal proof certificate. It grants no acceptance credit by itself.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_owned_exhaustive_v1 as owned
from canonical.runtime.tool_universe_gateway_v1 import (
    ToolUniverseGateway,
    prove_identity_completeness,
)

ROOT = Path(__file__).resolve().parents[2]
TARGET_ATOM = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_"
    "OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)
EXPECTED = {
    "canonical/runtime/tool_discovery_dynamic_candidate_v3.py": "bbbee4d6baf8df937543644397abba38a67dce62",
    "canonical/runtime/tool_discovery_dynamic_candidate_v4.py": "394cbc2e3092ef0bb870ccad9b092343275ca73e",
    "canonical/runtime/tool_universe_gateway_v1.py": "fd27f6f49e6a1ca6d47dc053f229c30492380b70",
    "canonical/runtime/tool_discovery_owned_exhaustive_v1.py": "b496803c3e32cffc22b4e679a5730223a8de9cd0",
    "canonical/tests/test_tool_discovery_dynamic_v4.py": "23f0add178ca0c731d15e0645ee9b8841317efee",
    "canonical/tests/test_tool_universe_gateway_v1.py": "cb4e0728c6bdf444a58e19bd1f854fbe2b6efc61",
    "canonical/tests/test_tool_discovery_owned_exhaustive_v1.py": "a64051324497c6489e9310dbc4d2fc94a64d1482",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json": "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json": "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json": "48ba33998e73b8eec2731be51a7ec78077ed0d4a",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "7885a827b1483bfb38315c1f492848f7e4680285",
}


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _find(obj: Any, key: str, value: str) -> Mapping[str, Any] | None:
    if isinstance(obj, Mapping):
        if obj.get(key) == value:
            return obj
        for child in obj.values():
            found = _find(child, key, value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for child in obj:
            found = _find(child, key, value)
            if found is not None:
                return found
    return None


def _entry(tid: str, cost: float) -> dict[str, Any]:
    return {
        "tool_id": tid,
        "available": True,
        "authorized": True,
        "cost": cost,
        "constraints": {},
    }


def evaluate() -> dict[str, Any]:
    drift = [path for path, sha in EXPECTED.items() if _blob_sha(path) != sha]
    if drift:
        return {
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT__ZERO_CREDIT",
            "source_blob_drift": drift,
            "universal_scope_proof_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    protocol = _load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    registry = _load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
    cut = _load("canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json")
    bindings = _load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
    family = _find(protocol, "family", "TOOL_DISCOVERY_SELECTION_AND_LEARNING") or {}
    behavior = _find(registry, "behavior_id", "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001") or {}
    target = _find(bindings, "predicate_id", "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR") or {}

    semantic = {
        "unknown_tool_discovery_required":
            "unknown tool discovery" in list(family.get("task_dimensions") or []),
        "discover_if_needed_required":
            "Discover candidate tools if needed" in str(behavior.get("required_output_or_action") or ""),
        "unknown_changing_scope_preserved":
            "Unknown/changing tool ecosystem to verified usable route" == behavior.get("scope"),
        "success_route_atom_still_open":
            target.get("state") == "EXTERNAL_BLOCKED",
        "scope_completeness_is_blocker":
            target.get("blocker_class") == "SCOPE_COMPLETENESS",
        "formalism_cut_targets_same_atom":
            cut.get("target_proof_atom") == TARGET_ATOM,
    }

    # Reproduce the load-bearing V3 falsifier: a known expensive route is selected
    # while an unqueried source can expose a cheaper sufficient identity.
    v3_public = {
        "required_capabilities": ["CAP_A"],
        "visible_tools": [dict(_entry("EXPENSIVE", 10), epoch=0)],
        "discovery_sources": [{"source_id": "S0", "cost": 0.1, "available": True}],
        "discovery_receipts": [],
        "prior_probe_receipts": [{
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "EXPENSIVE",
            "capability": "CAP_A",
            "epoch": 0,
            "supported": True,
        }],
        "version_events": [],
    }
    v3_action = v3.next_action(v3_public)
    v3_counterexample = (
        v3_action == {"action": "SELECT", "tool_id": "EXPENSIVE"}
        and not v3_public["discovery_receipts"]
    )

    gateway = ToolUniverseGateway([_entry("EXPENSIVE", 10), _entry("CHEAP", 1)])
    state = owned.new_episode(gateway, required_capabilities=["CAP_A"])
    repaired_first = owned.next_action(gateway, state)
    identity = prove_identity_completeness(gateway)

    v4_source = (ROOT / "canonical/runtime/tool_discovery_dynamic_candidate_v4.py").read_text(encoding="utf-8")
    gateway_source = (ROOT / "canonical/runtime/tool_universe_gateway_v1.py").read_text(encoding="utf-8")
    wrapper_source = (ROOT / "canonical/runtime/tool_discovery_owned_exhaustive_v1.py").read_text(encoding="utf-8")
    structural = {
        "v4_discovery_precedes_catalog":
            v4_source.find("if sources:") < v4_source.find("tools, conflict = _catalog(public)"),
        "v4_global_cost_order":
            'admissible.sort(' in v4_source and 'float(t.get("cost", 0.0))' in v4_source,
        "v4_select_requires_no_unknown":
            'if unknown:' in v4_source and 'return {"action": "SELECT", "tool_id": tid}' in v4_source,
        "gateway_discovery_exact_registry":
            '[self._registry[tid].public_metadata() for tid in sorted(self._registry)]' in gateway_source,
        "gateway_rejects_unregistered":
            'raise GatewayError("UNREGISTERED_TOOL_ID")' in gateway_source,
        "gateway_epoch_advances":
            "self._epoch += 1" in gateway_source,
        "wrapper_epoch_fail_closed":
            "episode_epoch != gateway.epoch" in wrapper_source,
        "wrapper_uses_only_gateway_discovery_source":
            '"discovery_sources": [gateway.discovery_source()]' in wrapper_source,
    }

    passed = (
        all(semantic.values())
        and v3_counterexample
        and repaired_first.get("action") == "DISCOVER"
        and identity.get("status") == "PASS__OWNED_IDENTITY_SCOPE_COMPLETE"
        and identity.get("every_invocable_discoverable") is True
        and all(structural.values())
    )

    return {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_OWNED_EXHAUSTIVE_SCOPE_PROOF_COMPILER_V1",
        "status": (
            "PASS__OWNED_EXHAUSTIVE_UNIVERSAL_SCOPE_PROOF_CANDIDATE__"
            "INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT"
            if passed else
            "FAIL_CLOSED__PROOF_PRECONDITION_FAILED__ZERO_CREDIT"
        ),
        "source_blob_drift": [],
        "semantic_preconditions": semantic,
        "v3_global_optimality_counterexample_reproduced": v3_counterexample,
        "v3_counterexample_action": v3_action,
        "replacement_first_action": repaired_first,
        "owned_identity_scope": identity,
        "structural_preconditions": structural,
        "universal_scope_proof_candidate": passed,
        "universal_argument": {
            "L1_owned_identity_completeness":
                "For every finite gateway registry R, gate_invoke accepts only IDs in R and discover enumerates exactly R; therefore every invocable identity is discoverable.",
            "L2_discovery_before_selection":
                "The wrapper exposes only the gateway source and V4 returns DISCOVER while that available source is unqueried, so no PROBE or SELECT precedes complete identity enumeration.",
            "L3_finite_probe_progress":
                "After discovery, the candidate considers a finite sorted tool set and finite required-capability set; each successful PROBE resolves one previously unknown pair.",
            "L4_global_least_cost":
                "Tools are traversed in nondecreasing cost/id order; every earlier eligible tool must be disproved before a later tool can be selected, so the first selected sufficient route is globally least-cost in R.",
            "L5_no_unsupported_selection":
                "SELECT is emitted only after every required capability has current positive evidence; hidden capability truth is never read directly.",
            "L6_epoch_soundness":
                "Registry replacement increments the owned epoch; the wrapper refuses stale episodes before discovery/probe/selection reuse.",
            "L7_unknown_changing_tool_support":
                "A new tool becomes invocable only by entering a new registry epoch; the next episode discovers that changed registry before selection.",
        },
        "minimum_missing_fact_if_independently_verified":
            TARGET_ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "target_preserved": True,
        "terminal_results_replayed": 0,
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
    return 0 if out["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
