"""R2 direct adequacy for bounded finance semantic hypothesis-product control V1."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_semantic_hypothesis_product_v1 as producer
from canonical.runtime import finance_semantic_hypothesis_product_verify_v1 as verifier

SCHEMA = "PROJECT_BRAIN_R2_FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_V1"
CAPABILITY_ID = "finance.semantic.hypothesis_product.stdlib"
VERIFIER_CAPABILITY_ID = "finance.semantic.hypothesis_product.verify.stdlib"
ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = re.compile(
    r"Using the bounded finance semantic hypothesis product case at "
    r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), compute and independently "
    r"verify the decision-relevant joint semantic ambiguity control and save it to "
    r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
    re.I,
)


def _base(status: str, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "matched": False,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _safe(root: str | Path, rel: str) -> Path:
    root = Path(root).resolve()
    path = Path(str(rel))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("PATH_INVALID")
    target = (root / path).resolve()
    if target == root or root not in target.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return target


def _contract(goal: str) -> Mapping[str, Any]:
    out = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["finance.semantic.hypothesis.product.control"],
    )
    if out.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return out


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    goal = str(request.get("goal") or "").strip()
    task_id = str(request.get("task_id") or "").strip()
    if not goal or not task_id:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}
    try:
        input_path = match.group("input")
        output_path = match.group("output")
        source = _safe(root, input_path)
        target = _safe(root, output_path)
        if source == target or not source.is_file():
            raise ValueError("INPUT_INVALID")
        raw = source.read_bytes()
        case = json.loads(raw.decode("utf-8"))
        produced = producer.compute(case)
        checked = verifier.verify(case, produced)
        if checked.get("verified") is not True:
            raise ValueError(
                "PREFLIGHT_RECOMPUTATION_FAILED:"
                + str(checked.get("reason") or "")
            )
        contract = _contract(goal)
        ids = list(
            (contract.get("acceptance_contract") or {}).get(
                "required_obligation_ids"
            )
            or []
        )
        if not ids:
            raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        input_sha = sha256(raw).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "policy_id": (
                "R2_FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT::"
                + goal_sha
                + "::"
                + input_sha
            ),
            "goal_sha256": goal_sha,
            "input_path": input_path,
            "input_sha256": input_sha,
            "output_path": output_path,
            "raw_acceptance_obligation_ids": ids,
            "semantic_scope": (
                "DECLARED_COMPLETE_FINANCE_SEMANTIC_DIMENSIONS__EXPLICIT_"
                "CARTESIAN_COMPLETENESS__COMPLETE_FACTORIZED_TERMINAL_SIGNATURES__"
                "DIMENSION_LOCAL_COMPLETE_OBSERVATION_MAPS"
            ),
            "preflight_execution_authority": False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    source = _safe(root, pf["input_path"])
    target = _safe(root, pf["output_path"])
    existed = target.is_file()
    old = target.read_bytes() if existed else None
    try:
        before = source.read_bytes()
        if sha256(before).hexdigest() != pf["input_sha256"]:
            raise RuntimeError("INPUT_DRIFT")
        case = json.loads(before.decode("utf-8"))
        produced = producer.compute(case)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(produced, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        checked = verifier.verify(
            case, json.loads(target.read_text(encoding="utf-8"))
        )
        if (
            checked.get("verified") is not True
            or checked.get("producer_independent") is not True
        ):
            raise RuntimeError("INDEPENDENT_VERIFICATION_FAILED")
        if source.read_bytes() != before:
            raise RuntimeError("SOURCE_MUTATED")
        ids = list(
            (_contract(str(request["goal"])).get("acceptance_contract") or {}).get(
                "required_obligation_ids"
            )
            or []
        )
        if ids != pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", True),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "selected_policy_id": pf["policy_id"],
            "goal_sha256": pf["goal_sha256"],
            "input_path": pf["input_path"],
            "input_sha256": pf["input_sha256"],
            "output_path": pf["output_path"],
            "output_sha256": sha256(target.read_bytes()).hexdigest(),
            "joint_world_count": produced["joint_world_count"],
            "decision_action": produced["decision"].get("action"),
            "decision_status": produced["decision"].get("status"),
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": ids,
            "raw_acceptance_obligation_count": len(ids),
            "acceptance_receipt": deepcopy(dict(checked)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "source_immutability_verified": True,
            "authority_boundary": (
                "ADEQUACY_IS_PROVED_ONLY_FOR_CORRECT_JOINT_AMBIGUITY_CONTROL_"
                "UNDER_THE_EXPLICIT_COMPLETE_PRODUCT_AND_FACTORIZATION_PREMISES__"
                "NO_COMPONENT_SEMANTIC_TRUTH_IS_INFERRED"
            ),
        }
    except Exception as exc:
        if existed:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(old or b"")
        else:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        rollback = (
            target.is_file() and existed and target.read_bytes() == (old or b"")
            if existed
            else not target.exists()
        )
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "rollback_complete": rollback,
            "reason": type(exc).__name__ + ":" + str(exc),
        }
