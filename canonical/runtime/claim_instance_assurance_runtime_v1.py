"""Live frozen-claim assurance runtime.

This composes the existing claim-instance assurance binder with the UVCK V2
assurance closure compiler. It closes all four assurance gates only for one
exact frozen claim whose canonical evidence adapter proves semantic/execution
closure and claim-scoped adversarial closure.

It does not grant global domain closure, acceptance authority, execution
authority, terminal authority, or terminal credit.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as closure
from canonical.runtime import claim_instance_assurance_binder_v1 as binder

SCHEMA = "PROJECT_BRAIN_CLAIM_INSTANCE_ASSURANCE_RUNTIME_V1"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_MISSION_PATH = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"


def _base(status: str, *, passed: bool, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "closure_scope": "FROZEN_CLAIM_INSTANCE_ONLY",
        "global_domain_closure": False,
        "global_open_world_closure": False,
        "global_mission_completion_derivable": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", passed=False, reason=reason, **extra)


def _current_mission_blob_sha(repo_root: str | Path) -> str:
    root = Path(repo_root).resolve(strict=True)
    path = (root / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json").resolve(strict=True)
    path.relative_to(root)
    return binder.git_blob_sha(path.read_bytes())


def _assurance_graph(bound: Mapping[str, Any]) -> dict[str, Any]:
    claim_id = str(bound.get("claim_id") or "").strip()
    if not claim_id:
        raise ValueError("BOUND_CLAIM_ID_REQUIRED")
    return {
        "schema": closure.GRAPH_SCHEMA,
        "root_ids": ["claim:" + claim_id],
        "nodes": [
            {
                "id": "claim:" + claim_id,
                "type": "CLAIM",
                "status": "SUPPORTED",
                "depends_on": ["evidence:claim-instance-binder"],
                "defeated_by": [],
            },
            {
                "id": "evidence:claim-instance-binder",
                "type": "EVIDENCE",
                "status": "SUPPORTED",
                "authoritative_leaf": True,
                "source_schema": bound.get("schema"),
                "source_status": bound.get("status"),
            },
        ],
    }


def evaluate(
    bundle: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        return _fail("BUNDLE_NOT_OBJECT")

    try:
        mission_sha = _current_mission_blob_sha(repo_root)
    except Exception as exc:
        return _fail("CURRENT_MISSION_BINDING_UNAVAILABLE:" + type(exc).__name__ + ":" + str(exc))

    bound = binder.evaluate(
        bundle,
        current_mission_blob_sha=mission_sha,
        repo_root=repo_root,
    )
    if bound.get("pass") is not True:
        return _base(
            "OPEN__CLAIM_INSTANCE_ASSURANCE_NOT_CLOSED"
            if bound.get("status") != "FAIL_CLOSED"
            else "FAIL_CLOSED",
            passed=False,
            reason=bound.get("reason"),
            binder_result=deepcopy(dict(bound)),
            current_mission_blob_sha=mission_sha,
        )

    if (
        bound.get("domain_semantic_closure") is not True
        or bound.get("domain_execution_closure") is not True
        or bound.get("claim_scoped_adversarial_closure") is not True
        or bound.get("closure_scope") != "FROZEN_CLAIM_INSTANCE_ONLY"
    ):
        return _fail(
            "BOUND_CLAIM_ASSURANCE_PREMISES_INCOMPLETE",
            binder_result=deepcopy(dict(bound)),
            current_mission_blob_sha=mission_sha,
        )

    graph = _assurance_graph(bound)
    structural = closure.evaluate(graph)
    gates = deepcopy(dict(structural.get("closure_gates") or {}))
    if (
        structural.get("existing_kernel_expressive") is not True
        or gates.get("representation_closure") is not True
        or gates.get("proof_closure") is not True
    ):
        return _fail(
            "ASSURANCE_STRUCTURAL_CLOSURE_NOT_PROVED",
            binder_result=deepcopy(dict(bound)),
            structural_result=deepcopy(dict(structural)),
            current_mission_blob_sha=mission_sha,
        )

    gates["execution_closure"] = True
    gates["adversarial_closure"] = True

    return _base(
        "PASS__FROZEN_CLAIM_INSTANCE_ASSURANCE_CLOSED",
        passed=True,
        claim_id=bound.get("claim_id"),
        claim_kind=bound.get("claim_kind"),
        required_root_ids=deepcopy(bound.get("required_root_ids") or []),
        covered_root_ids=deepcopy(bound.get("covered_root_ids") or []),
        assurance_gates=gates,
        representation_closure=True,
        proof_closure=True,
        execution_closure=True,
        adversarial_closure=True,
        binder_result=deepcopy(dict(bound)),
        structural_result=deepcopy(dict(structural)),
        current_mission_blob_sha=mission_sha,
        rule=(
            "ALL_FOUR_GATES_CLOSE_ONLY_FOR_EXACT_CURRENT_MISSION_BOUND_CLAIM_INSTANCE__"
            "BINDER_EVIDENCE_IS_CONTENT_ADDRESSED_AND_ADAPTER_VERIFIED__"
            "NO_GLOBAL_DOMAIN_OR_MISSION_PROMOTION"
        ),
    )


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    bundle = args.get("bundle")
    return evaluate(bundle, repo_root=args.get("repo_root") or ROOT)
