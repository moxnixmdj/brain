"""R2 direct adequacy route for bounded finance candidate terminal signatures V1."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_candidate_policy_terminal_signatures_v1 as producer
from canonical.runtime import finance_candidate_policy_terminal_signatures_verify_v1 as verifier

SCHEMA = "PROJECT_BRAIN_R2_FINANCE_CANDIDATE_POLICY_TERMINAL_SIGNATURES_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::FINANCE_CANDIDATE_POLICY_TERMINAL_SIGNATURES_V1"
CAPABILITY_ID = "finance.candidate_policy.terminal_signatures.stdlib"
VERIFIER_CAPABILITY_ID = "finance.candidate_policy.terminal_signatures.verify.stdlib"
ROOT = Path(__file__).resolve().parents[2]
GRAMMAR = re.compile(
    r"Using the bounded finance candidate policy worldset at "
    r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), derive and independently "
    r"verify complete candidate terminal signatures and save them to "
    r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
    re.IGNORECASE,
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
        "verification_authority_mutated": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _safe(root: str | Path, rel: str) -> Path:
    root = Path(root).resolve()
    p = Path(str(rel))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("PATH_INVALID")
    q = (root / p).resolve()
    if q == root or root not in q.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return q


def _contract(goal: str) -> Mapping[str, Any]:
    out = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["finance.candidate_policy.terminal_signatures"],
    )
    if out.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    return out


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    m = GRAMMAR.fullmatch(goal)
    if m is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    try:
        input_rel = m.group("input")
        output_rel = m.group("output")
        input_path = _safe(root, input_rel)
        output_path = _safe(root, output_rel)
        if input_path == output_path or not input_path.is_file():
            raise ValueError("INPUT_INVALID")

        before = input_path.read_bytes()
        case = json.loads(before.decode("utf-8"))
        produced = producer.compute(case)
        checked = verifier.verify(case, produced)
        if checked.get("verified") is not True:
            raise ValueError("PREFLIGHT_INDEPENDENT_RECOMPUTATION_FAILED")

        contract = _contract(goal)
        ids = list(
            (contract.get("acceptance_contract") or {}).get("required_obligation_ids")
            or []
        )
        if not ids:
            raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")

        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        input_sha = sha256(before).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "policy_id": "R2_FINANCE_CANDIDATE_TERMINAL_SIGNATURES::" + goal_sha + "::" + input_sha,
            "goal_sha256": goal_sha,
            "input_path": input_rel,
            "input_sha256": input_sha,
            "output_path": output_rel,
            "raw_acceptance_obligation_ids": ids,
            "candidate_count": produced["candidate_count"],
            "policy_family": produced["policy_family"],
            "semantic_scope": (
                "EXACT_DECLARED_FINITE_CANDIDATE_SET__EXPLICIT_CANDIDATE_BOOLEAN_FACTS__"
                "EXACT_BOUNDED_NORMALIZED_IF_OR_UNLESS_POLICY_REPLAY__"
                "COMPLETE_TERMINAL_SIGNATURES_RELATIVE_TO_DECLARED_CANDIDATE_SET"
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

    input_path = _safe(root, pf["input_path"])
    output_path = _safe(root, pf["output_path"])
    existed = output_path.is_file()
    old = output_path.read_bytes() if existed else None

    try:
        before = input_path.read_bytes()
        if sha256(before).hexdigest() != pf["input_sha256"]:
            raise RuntimeError("INPUT_DRIFT")
        case = json.loads(before.decode("utf-8"))
        produced = producer.compute(case)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(produced, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        reread = json.loads(output_path.read_text(encoding="utf-8"))
        checked = verifier.verify(case, reread)
        if checked.get("verified") is not True or checked.get("producer_independent") is not True:
            raise RuntimeError("INDEPENDENT_VERIFICATION_FAILED")
        if input_path.read_bytes() != before:
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
            "output_sha256": sha256(output_path.read_bytes()).hexdigest(),
            "candidate_count": reread["candidate_count"],
            "terminal_equivalence_class_count": reread["terminal_equivalence_class_count"],
            "all_candidates_terminally_equivalent": reread["all_candidates_terminally_equivalent"],
            "policy_family": reread["policy_family"],
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
                "DIRECT_ADEQUACY_PROVES_COMPLETE_TERMINAL_SIGNATURE_DERIVATION_ONLY_"
                "RELATIVE_TO_THE_EXACT_DECLARED_CANDIDATE_SET_AND_EXPLICIT_CANDIDATE_"
                "BOOLEAN_FACTS__IT_DOES_NOT_PROVE_CANDIDATE_SET_SEMANTIC_COMPLETENESS_"
                "OR_INFER_CANDIDATE_FACT_TRUTH_OR_GENERAL_FINANCE_SEMANTICS"
            ),
        }
    except Exception as exc:
        if existed:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(old or b"")
        else:
            try:
                output_path.unlink()
            except FileNotFoundError:
                pass
        rollback = (
            output_path.is_file() and existed and output_path.read_bytes() == (old or b"")
            if existed
            else not output_path.exists()
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
