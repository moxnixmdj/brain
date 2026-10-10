"""R2 direct adequacy for normalized supervisory-finance single-UNLESS cases.

Exact family:
- one repository-local JSON case with an explicit Boolean exception_applies;
- one source string admitted by the certified single-UNLESS structural parser;
- select the applicable branch under that supplied fact;
- independently recompute the selection with a separate verifier implementation.

This is positive adequacy for the exact normalized contract only. It does not infer
the Boolean from reality and does not claim arbitrary finance-language closure.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_normalized_unless_branch_v1 as producer
from canonical.runtime import finance_normalized_unless_verify_v1 as verifier

SCHEMA = "PROJECT_BRAIN_R2_FINANCE_NORMALIZED_UNLESS_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::FINANCE_NORMALIZED_UNLESS_BRANCH_FAMILY_V1"
CAPABILITY_ID = "finance.normalized_unless.branch.stdlib"
VERIFIER_CAPABILITY_ID = "finance.normalized_unless.verify.stdlib"
POLICY_PREFIX = "R2_FINANCE_NORMALIZED_UNLESS_DIRECT::"
ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = re.compile(
    r"Using the normalized finance supervisory UNLESS case at "
    r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), select and independently "
    r"verify the applicable branch and save it to "
    r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
    re.IGNORECASE,
)


def _base(status: str, *, passed: bool) -> dict[str, Any]:
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


def _safe(root: Path, rel: str) -> Path:
    root = root.resolve()
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("PATH_INVALID")
    resolved = (root / p).resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return resolved


def _sha_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _raw_contract(goal: str) -> dict[str, Any]:
    contract = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["finance.normalized_unless.branch"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return contract


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED", passed=False), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {
            **_base("FAIL_CLOSED", passed=False),
            "reason": "TASK_ID_AND_GOAL_REQUIRED",
        }

    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE", passed=False), "matched": False}

    try:
        input_rel = match.group("input")
        output_rel = match.group("output")
        input_path = _safe(root, input_rel)
        output_path = _safe(root, output_rel)
        if input_path == output_path:
            raise ValueError("INPUT_OUTPUT_PATH_COLLISION")
        if not input_path.is_file():
            raise ValueError("FINANCE_CASE_INPUT_MISSING")

        case = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(case, dict) or case.get("schema") != producer.INPUT_SCHEMA:
            raise ValueError("FINANCE_CASE_SCHEMA_INVALID")
        if not isinstance(case.get("source_id"), str) or not str(case["source_id"]).strip():
            raise ValueError("FINANCE_CASE_SOURCE_ID_INVALID")
        if not isinstance(case.get("source_text"), str) or not str(case["source_text"]).strip():
            raise ValueError("FINANCE_CASE_SOURCE_TEXT_INVALID")
        if not isinstance(case.get("exception_applies"), bool):
            raise ValueError("FINANCE_CASE_EXCEPTION_APPLIES_INVALID")

        normalized = producer.compute(case)
        independent = verifier.verify(case, normalized)
        if independent.get("verified") is not True:
            raise ValueError("PREFLIGHT_INDEPENDENT_RECOMPUTATION_FAILED")

        contract = _raw_contract(goal)
        raw_ids = list(
            (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
        )
        if not raw_ids:
            raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")

        input_sha = _sha_file(input_path)
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "policy_id": POLICY_PREFIX + goal_sha + "::" + input_sha,
            "goal_sha256": goal_sha,
            "input_path": input_rel,
            "input_sha256": input_sha,
            "output_path": output_rel,
            "source_text_sha256": normalized["source_text_sha256"],
            "scope_id": normalized["scope_id"],
            "raw_task_contract_sha256": contract.get("task_contract_sha256"),
            "raw_acceptance_obligation_ids": raw_ids,
            "semantic_scope": (
                "EXACT_NORMALIZED_SUPERVISORY_FINANCE_SINGLE_UNLESS_WITH_EXPLICIT_"
                "TYPED_EXCEPTION_TRUTH_TO_INDEPENDENTLY_VERIFIED_BRANCH_SELECTION"
            ),
            "preflight_execution_authority": False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _restore(path: Path, existed: bool, original: bytes | None) -> None:
    if existed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original or b"")
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    input_path = _safe(root, str(pf["input_path"]))
    output_path = _safe(root, str(pf["output_path"]))
    existed = output_path.is_file()
    original = output_path.read_bytes() if existed else None

    try:
        before_sha = _sha_file(input_path)
        if before_sha != pf["input_sha256"]:
            raise RuntimeError("INPUT_DRIFT_BEFORE_EXECUTION")
        case = json.loads(input_path.read_text(encoding="utf-8"))

        produced = producer.compute(case)
        if produced.get("pass") is not True:
            raise RuntimeError("PRODUCER_DID_NOT_PASS")
        if produced.get("model_dependency_count") != 0:
            raise RuntimeError("PRODUCER_MODEL_DEPENDENCY_NONZERO")
        if _sha_file(input_path) != before_sha:
            raise RuntimeError("SOURCE_MUTATED_BY_PRODUCER")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(produced, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        result = json.loads(output_path.read_text(encoding="utf-8"))
        checked = verifier.verify(case, result)
        if checked.get("verified") is not True:
            raise RuntimeError(
                "INDEPENDENT_FINANCE_BRANCH_VERIFICATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )
        if checked.get("producer_independent") is not True:
            raise RuntimeError("VERIFIER_NOT_PRODUCER_INDEPENDENT")
        if checked.get("model_dependency_count") != 0:
            raise RuntimeError("VERIFIER_MODEL_DEPENDENCY_NONZERO")
        if _sha_file(input_path) != before_sha:
            raise RuntimeError("SOURCE_MUTATED_DURING_VERIFICATION")

        contract = _raw_contract(str(request["goal"]))
        accepted_ids = list(
            (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
        )
        if not accepted_ids or accepted_ids != pf["raw_acceptance_obligation_ids"]:
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")

        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "selected_policy_id": pf["policy_id"],
            "goal_sha256": pf["goal_sha256"],
            "input_path": pf["input_path"],
            "input_sha256": before_sha,
            "output_path": pf["output_path"],
            "output_sha256": _sha_file(output_path),
            "source_text_sha256": produced["source_text_sha256"],
            "scope_id": produced["scope_id"],
            "selected_branch": produced["selected_branch"],
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "producer_result": deepcopy(dict(produced)),
            "acceptance_receipt": deepcopy(dict(checked)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "source_immutability_verified": True,
            "authority_boundary": (
                "EXACT_NORMALIZED_SINGLE_UNLESS_FINANCE_CONTRACT_ONLY;"
                "EXCEPTION_APPLIES_IS_EXPLICIT_TYPED_INPUT_NOT_INFERRED_REALITY;"
                "NO_ARBITRARY_FINANCE_LANGUAGE_OR_OPEN_WORLD_GENERALIZATION"
            ),
        }
    except Exception as exc:
        _restore(output_path, existed, original)
        rollback = (
            output_path.is_file()
            and existed
            and output_path.read_bytes() == (original or b"")
        ) if existed else not output_path.exists()
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "goal_sha256": pf.get("goal_sha256"),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "rollback_complete": rollback,
            "reason": type(exc).__name__ + ":" + str(exc),
        }
