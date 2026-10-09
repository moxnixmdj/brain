"""R2 direct adequacy for task-role-bound cross-document Finance UNLESS."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_task_role_raw_fact_unless_branch_v1 as producer
from canonical.runtime import finance_task_role_raw_fact_unless_verify_v1 as verifier

SCHEMA = "PROJECT_BRAIN_R2_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::FINANCE_TASK_ROLE_RAW_FACT_UNLESS_FAMILY_V1"
CAPABILITY_ID = "finance.task_role_raw_fact_unless.branch.stdlib"
VERIFIER_CAPABILITY_ID = "finance.task_role_raw_fact_unless.verify.stdlib"
POLICY_PREFIX = "R2_FINANCE_TASK_ROLE_RAW_FACT_UNLESS::"
ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = re.compile(
    r"Using the task-role cross-document finance UNLESS case at "
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
    q = (root / p).resolve()
    if q == root or root not in q.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return q


def _sha_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _contract(goal: str) -> dict[str, Any]:
    out = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["finance.task_role_raw_fact_unless.branch"],
    )
    if out.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return out


def _case_source_paths(case: Mapping[str, Any]) -> tuple[str, str]:
    task = case.get("task_record")
    roles = task.get("source_roles") if isinstance(task, Mapping) else None
    if not isinstance(roles, Mapping):
        raise ValueError("SOURCE_ROLES_REQUIRED")
    policy = roles.get("policy_source_path")
    facts = roles.get("fact_source_path")
    if not isinstance(policy, str) or not isinstance(facts, str):
        raise ValueError("SOURCE_ROLE_PATHS_INVALID")
    return policy.strip().replace("\\", "/"), facts.strip().replace("\\", "/")


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
        return {**_base("FAIL_CLOSED", passed=False), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE", passed=False), "matched": False}

    try:
        inp = match.group("input")
        outp = match.group("output")
        ip = _safe(root, inp)
        op = _safe(root, outp)
        if ip == op:
            raise ValueError("INPUT_OUTPUT_PATH_COLLISION")
        if not ip.is_file():
            raise ValueError("CROSS_DOCUMENT_CASE_INPUT_MISSING")
        case = json.loads(ip.read_text(encoding="utf-8"))
        if not isinstance(case, dict) or case.get("schema") != producer.INPUT_SCHEMA:
            raise ValueError("CROSS_DOCUMENT_CASE_SCHEMA_INVALID")

        produced = producer.compute(case, repo_root=root)
        checked = verifier.verify(case, produced, repo_root=root)
        if checked.get("verified") is not True:
            raise ValueError(
                "PREFLIGHT_INDEPENDENT_RECOMPUTATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )

        policy_rel, fact_rel = _case_source_paths(case)
        pp = _safe(root, policy_rel)
        fp = _safe(root, fact_rel)
        contract = _contract(goal)
        raw_ids = list(
            (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
        )
        if not raw_ids:
            raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        case_sha = _sha_file(ip)
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED", passed=False),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "policy_id": (
                POLICY_PREFIX
                + goal_sha
                + "::"
                + case_sha
                + "::"
                + produced["source_set_sha256"]
            ),
            "goal_sha256": goal_sha,
            "input_path": inp,
            "input_sha256": case_sha,
            "policy_source_path": policy_rel,
            "policy_source_sha256": _sha_file(pp),
            "fact_source_path": fact_rel,
            "fact_source_sha256": _sha_file(fp),
            "output_path": outp,
            "source_set_sha256": produced["source_set_sha256"],
            "typed_context_sha256": produced["typed_context_sha256"],
            "raw_task_contract_sha256": contract.get("task_contract_sha256"),
            "raw_acceptance_obligation_ids": raw_ids,
            "semantic_scope": (
                "EXPLICIT_TASK_ROLE_BOUND_DECLARED_POLICY_SOURCE_PLUS_RAW_TYPED_FACT_SOURCE_"
                "WITH_EXPLICIT_TERM_TO_FIELD_UNLESS"
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

    ip = _safe(root, str(pf["input_path"]))
    pp = _safe(root, str(pf["policy_source_path"]))
    fp = _safe(root, str(pf["fact_source_path"]))
    op = _safe(root, str(pf["output_path"]))
    existed = op.is_file()
    original = op.read_bytes() if existed else None

    try:
        before = {
            "case": _sha_file(ip),
            "policy": _sha_file(pp),
            "facts": _sha_file(fp),
        }
        if before != {
            "case": pf["input_sha256"],
            "policy": pf["policy_source_sha256"],
            "facts": pf["fact_source_sha256"],
        }:
            raise RuntimeError("SOURCE_DRIFT_BEFORE_EXECUTION")

        case = json.loads(ip.read_text(encoding="utf-8"))
        produced = producer.compute(case, repo_root=root)
        if produced.get("pass") is not True or produced.get("model_dependency_count") != 0:
            raise RuntimeError("PRODUCER_AUTHORITY_INVALID")

        after_producer = {
            "case": _sha_file(ip),
            "policy": _sha_file(pp),
            "facts": _sha_file(fp),
        }
        if after_producer != before:
            raise RuntimeError("SOURCE_MUTATED_BY_PRODUCER")

        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(
            json.dumps(produced, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        observed = json.loads(op.read_text(encoding="utf-8"))
        checked = verifier.verify(case, observed, repo_root=root)
        if checked.get("verified") is not True:
            raise RuntimeError(
                "INDEPENDENT_CROSS_DOCUMENT_VERIFICATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )
        if checked.get("producer_independent") is not True or checked.get("model_dependency_count") != 0:
            raise RuntimeError("VERIFIER_AUTHORITY_INVALID")
        if {
            "case": _sha_file(ip),
            "policy": _sha_file(pp),
            "facts": _sha_file(fp),
        } != before:
            raise RuntimeError("SOURCE_MUTATED_DURING_VERIFICATION")

        contract = _contract(str(request["goal"]))
        ids = list(
            (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
        )
        if not ids or ids != pf["raw_acceptance_obligation_ids"]:
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
            "input_sha256": before["case"],
            "policy_source_path": pf["policy_source_path"],
            "policy_source_sha256": before["policy"],
            "fact_source_path": pf["fact_source_path"],
            "fact_source_sha256": before["facts"],
            "output_path": pf["output_path"],
            "output_sha256": _sha_file(op),
            "source_set_sha256": produced["source_set_sha256"],
            "typed_context_sha256": produced["typed_context_sha256"],
            "defined_term": produced["defined_term"],
            "field_name": produced["field_name"],
            "operator": produced["operator"],
            "literal": produced["literal"],
            "condition_holds": produced["condition_holds"],
            "selected_branch": produced["selected_branch"],
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": ids,
            "raw_acceptance_obligation_count": len(ids),
            "producer_result": deepcopy(dict(produced)),
            "acceptance_receipt": deepcopy(dict(checked)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "source_immutability_verified": True,
            "authority_boundary": (
                "TASK_RECORD_EXPLICITLY_DESIGNATES_TWO_DECLARED_SOURCE_PATHS_AS_POLICY_AND_FACT;"
                "RAW_FACT_BYTES_ARE_TYPED_AND_BOUND;NO_IMPLICIT_SOURCE_ROLE_DISCOVERY;"
                "NO_GENERAL_CROSS_DOCUMENT_BINDING_SYNONYMY_ONTOLOGY_OR_EXTERNAL_WORLD_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(op, existed, original)
        rollback = (
            op.is_file() and existed and op.read_bytes() == (original or b"")
        ) if existed else not op.exists()
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
