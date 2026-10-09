"""R2 direct adequacy for source-defined raw-fact finance UNLESS cases.

The raw goal binds one task-local case file and one output path. The case must
contain:
- finance policy source bytes with proof-carrying structural source coverage,
- an explicit source declaration mapping the human condition term to one field,
- raw strict JSON fact bytes containing that field.

The producer and a separate producer-independent verifier must converge before
the output transaction commits. Implicit synonymy, ontology, sector conventions,
cross-document identity, and external-world factual truth remain outside scope.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import finance_defined_term_raw_fact_unless_branch_v1 as producer
from canonical.runtime import finance_defined_term_raw_fact_unless_verify_v1 as verifier

SCHEMA = "PROJECT_BRAIN_R2_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_FAMILY_V1"
CAPABILITY_ID = "finance.defined_term_raw_fact.unless.stdlib"
VERIFIER_CAPABILITY_ID = "finance.defined_term_raw_fact.unless.verify.stdlib"
POLICY_PREFIX = "R2_FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_DIRECT::"
ROOT = Path(__file__).resolve().parents[2]
_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR = re.compile(
    r"^Using the source-defined raw-fact finance UNLESS case at "
    r"(?P<input>" + _PATH + r"\.json), select and independently verify the "
    r"applicable branch and save it to (?P<output>" + _PATH + r"\.json)\.?$",
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
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _safe(root: Path, rel: str) -> Path:
    root = root.resolve()
    p = Path(str(rel))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("PATH_INVALID")
    out = (root / p).resolve()
    if out == root or root not in out.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return out


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _raw_contract(goal: str) -> dict[str, Any]:
    contract = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=["finance.defined_term_raw_fact.unless"],
    )
    if contract.get("pass") is not True:
        raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
    ids = list(
        (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
    )
    if not ids:
        raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
    return contract


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}

    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    try:
        input_rel = match.group("input")
        output_rel = match.group("output")
        input_path = _safe(root, input_rel)
        output_path = _safe(root, output_rel)
        if input_path == output_path:
            raise ValueError("INPUT_OUTPUT_PATH_COLLISION")
        if not input_path.is_file():
            raise ValueError("FINANCE_DEFINED_TERM_CASE_MISSING")

        case = json.loads(input_path.read_text(encoding="utf-8"))
        produced = producer.compute(case)
        checked = verifier.verify(case, produced)
        if checked.get("verified") is not True:
            raise ValueError(
                "PREFLIGHT_INDEPENDENT_VERIFICATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )

        contract = _raw_contract(goal)
        raw_ids = list(contract["acceptance_contract"]["required_obligation_ids"])
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        input_sha = _sha(input_path)
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": goal_sha,
            "policy_id": POLICY_PREFIX + goal_sha + "::" + input_sha,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "input_path": input_rel,
            "input_sha256": input_sha,
            "output_path": output_rel,
            "policy_source_id": produced.get("policy_source_id"),
            "policy_source_text_sha256": produced.get("policy_source_text_sha256"),
            "fact_source_id": produced.get("fact_source_id"),
            "fact_source_sha256": produced.get("fact_source_sha256"),
            "typed_context_sha256": produced.get("typed_context_sha256"),
            "defined_term": produced.get("defined_term"),
            "field_name": produced.get("field_name"),
            "condition_atom_id": produced.get("condition_atom_id"),
            "selected_branch": produced.get("selected_branch"),
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "raw_acceptance_obligation_ids": raw_ids,
            "semantic_scope": (
                "TASK_BOUND_FINANCE_POLICY_SOURCE_WITH_PROOF_CARRYING_STRUCTURAL_COVERAGE__"
                "EXPLICIT_DEFINED_TERM_TO_ONE_TYPED_FIELD__STRICT_RAW_FACT_JSON__"
                "CONTROLLED_SINGLE_UNLESS"
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
        if _sha(input_path) != pf["input_sha256"]:
            raise RuntimeError("INPUT_DRIFT_BEFORE_EXECUTION")
        case = json.loads(input_path.read_text(encoding="utf-8"))

        produced = producer.compute(case)
        if (
            produced.get("pass") is not True
            or produced.get("model_dependency_count") != 0
            or produced.get("external_world_truth_claimed") is not False
            or produced.get("implicit_semantic_inference_claimed") is not False
        ):
            raise RuntimeError("FINANCE_DEFINED_TERM_PRODUCER_BOUNDARY_INVALID")
        if _sha(input_path) != pf["input_sha256"]:
            raise RuntimeError("INPUT_MUTATED_BY_PRODUCER")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(produced, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        stored = json.loads(output_path.read_text(encoding="utf-8"))
        checked = verifier.verify(case, stored)
        if checked.get("verified") is not True:
            raise RuntimeError(
                "INDEPENDENT_FINANCE_DEFINED_TERM_VERIFICATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )
        if checked.get("producer_independent") is not True:
            raise RuntimeError("VERIFIER_NOT_PRODUCER_INDEPENDENT")
        if checked.get("producer_module_imported") is not False:
            raise RuntimeError("VERIFIER_IMPORTED_PRODUCER")
        if checked.get("defined_term_evaluator_imported") is not False:
            raise RuntimeError("VERIFIER_IMPORTED_DEFINED_TERM_EVALUATOR")
        if checked.get("raw_context_compiler_imported") is not False:
            raise RuntimeError("VERIFIER_IMPORTED_RAW_CONTEXT_COMPILER")
        if checked.get("scope_parser_imported") is not False:
            raise RuntimeError("VERIFIER_IMPORTED_SCOPE_PARSER")
        if checked.get("model_dependency_count") != 0:
            raise RuntimeError("VERIFIER_MODEL_DEPENDENCY_NONZERO")
        if _sha(input_path) != pf["input_sha256"]:
            raise RuntimeError("INPUT_MUTATED_DURING_VERIFICATION")

        for key in (
            "policy_source_text_sha256",
            "fact_source_sha256",
            "typed_context_sha256",
            "condition_atom_id",
            "selected_branch",
        ):
            if stored.get(key) != pf.get(key):
                raise RuntimeError("PREFLIGHT_RESULT_DRIFT:" + key)

        contract = _raw_contract(str(request["goal"]))
        accepted_ids = list(
            (contract.get("acceptance_contract") or {}).get("required_obligation_ids") or []
        )
        if accepted_ids != pf["raw_acceptance_obligation_ids"]:
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
            "output_sha256": _sha(output_path),
            "semantic_scope": pf["semantic_scope"],
            "policy_source_id": stored.get("policy_source_id"),
            "policy_source_text_sha256": stored.get("policy_source_text_sha256"),
            "fact_source_id": stored.get("fact_source_id"),
            "fact_source_sha256": stored.get("fact_source_sha256"),
            "typed_context_sha256": stored.get("typed_context_sha256"),
            "defined_term": stored.get("defined_term"),
            "field_name": stored.get("field_name"),
            "condition_atom_id": stored.get("condition_atom_id"),
            "selected_branch": stored.get("selected_branch"),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "producer_result": deepcopy(dict(stored)),
            "acceptance_receipt": deepcopy(dict(checked)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "transaction_committed": True,
            "transaction_rolled_back": False,
            "input_immutability_verified": True,
            "authority_boundary": (
                "TASK_BOUND_EXPLICIT_DEFINED_TERM_AND_RAW_FACT_SUBREGION_ONLY;"
                "NO_SYNONYMY_ONTOLOGY_IMPLICIT_SECTOR_CONVENTION_CROSS_DOCUMENT_ENTITY_LINKING_"
                "EXTERNAL_WORLD_FACTUAL_TRUTH_OR_GENERAL_FINANCE_SEMANTICS"
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
            **_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "goal_sha256": pf.get("goal_sha256"),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "transaction_rolled_back": True,
            "rollback_complete": rollback,
            "reason": type(exc).__name__ + ":" + str(exc),
        }
