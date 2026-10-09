"""Direct R2 adequacy route for authoritative normalized Finance source packages."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import evidence_decision_synthesis as producer
from canonical.runtime.finance_normalized_direct_acceptance_v1 import (
    DOCUMENT,
    PACKAGE_SCHEMA,
    SOURCE_MODES,
    SUPERVISORY,
    verify as verify_acceptance,
)
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA = "PROJECT_BRAIN_R2_FINANCE_NORMALIZED_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::AUTHORITATIVE_NORMALIZED_FINANCE_DECISION_V1"
POLICY_PREFIX = "R2_FINANCE_NORMALIZED_DIRECT::"
ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = re.compile(
    r"From the authoritative normalized finance package at "
    r"(?P<input>canonical/[A-Za-z0-9_.-/]+.json), synthesize and independently "
    r"verify the finance decision and save it to "
    r"(?P<output>canonical/[A-Za-z0-9_.-/]+.json).?",
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
    out = (root / p).resolve()
    if out == root or root not in out.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return out


def _sha_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _raw_contract(goal: str) -> dict[str, Any]:
    contract = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["finance.normalized.decision"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return contract


def _basic_package_check(package: Any) -> tuple[str, str]:
    if not isinstance(package, Mapping) or package.get("schema") != PACKAGE_SCHEMA:
        raise ValueError("FINANCE_PACKAGE_SCHEMA_INVALID")
    leaf = str(package.get("leaf_id") or "")
    if leaf not in {SUPERVISORY, DOCUMENT}:
        raise ValueError("FINANCE_LEAF_INVALID")
    if package.get("source_mode") != SOURCE_MODES[leaf]:
        raise ValueError("FINANCE_SOURCE_MODE_INVALID")
    source_id = str(package.get("source_id") or "").strip()
    if not source_id:
        raise ValueError("FINANCE_SOURCE_ID_REQUIRED")
    problem = package.get("decision_problem")
    if not isinstance(problem, Mapping) or problem.get("schema") != producer.SCHEMA:
        raise ValueError("FINANCE_DECISION_PROBLEM_SCHEMA_INVALID")
    return leaf, source_id


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
            raise ValueError("FINANCE_PACKAGE_MISSING")
        package = json.loads(input_path.read_text(encoding="utf-8"))
        leaf, source_id = _basic_package_check(package)
        contract = _raw_contract(goal)
        raw_ids = list(
            (contract.get("acceptance_contract") or {}).get(
                "required_obligation_ids"
            )
            or []
        )
        if not raw_ids:
            raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        input_sha = _sha_file(input_path)
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "policy_id": POLICY_PREFIX + goal_sha + "::" + input_sha,
            "goal_sha256": goal_sha,
            "input_path": input_rel,
            "input_sha256": input_sha,
            "output_path": output_rel,
            "leaf_id": leaf,
            "source_id": source_id,
            "source_mode": package.get("source_mode"),
            "raw_task_contract_sha256": contract.get("task_contract_sha256"),
            "raw_acceptance_obligation_ids": raw_ids,
            "semantic_scope": (
                "AUTHORITATIVE_NORMALIZED_FINANCE_SOURCE_UNIVERSE_TO_"
                "INDEPENDENTLY_VERIFIED_TYPED_DECISION"
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
        package = json.loads(input_path.read_text(encoding="utf-8"))
        _basic_package_check(package)
        result = producer.synthesize(dict(package["decision_problem"]))
        if result.get("model_dependency_count") != 0:
            raise RuntimeError("PRODUCER_MODEL_DEPENDENCY_NONZERO")
        if _sha_file(input_path) != before_sha:
            raise RuntimeError("SOURCE_MUTATED_BY_PRODUCER")

        acceptance = verify_acceptance(package, result)
        if acceptance.get("pass") is not True:
            raise RuntimeError(
                "INDEPENDENT_FINANCE_ACCEPTANCE_FAILED:"
                + "|".join(acceptance.get("errors") or [])
            )
        if _sha_file(input_path) != before_sha:
            raise RuntimeError("SOURCE_MUTATED_DURING_ACCEPTANCE")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if not output_path.is_file():
            raise RuntimeError("OUTPUT_MISSING")

        contract = _raw_contract(str(request["goal"]))
        accepted_ids = list(
            (contract.get("acceptance_contract") or {}).get(
                "required_obligation_ids"
            )
            or []
        )
        if (
            not accepted_ids
            or accepted_ids != pf["raw_acceptance_obligation_ids"]
        ):
            raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
        return {
            **_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED", passed=True),
            "matched": True,
            "route_id": ROUTE_ID,
            "selected_policy_id": pf["policy_id"],
            "goal_sha256": pf["goal_sha256"],
            "input_path": pf["input_path"],
            "input_sha256": before_sha,
            "output_path": pf["output_path"],
            "output_sha256": _sha_file(output_path),
            "leaf_id": pf["leaf_id"],
            "source_mode": pf["source_mode"],
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "decision_result": deepcopy(dict(result)),
            "acceptance_receipt": deepcopy(dict(acceptance)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "source_immutability_verified": True,
            "raw_prose_semantic_extraction_claimed": False,
            "authority_boundary": (
                "AUTHORITATIVE_NORMALIZED_FINANCE_PACKAGES_ONLY__"
                "NO_ARBITRARY_RAW_FINANCE_LANGUAGE_GENERALIZATION"
            ),
        }
    except Exception as exc:
        _restore(output_path, existed, original)
        rollback = (
            output_path.is_file()
            and existed
            and output_path.read_bytes() == (original or b"")
            if existed
            else not output_path.exists()
        )
        return {
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "goal_sha256": pf.get("goal_sha256"),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "rollback_complete": rollback,
            "reason": type(exc).__name__ + ":" + str(exc),
        }
