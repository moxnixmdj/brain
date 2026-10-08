"""Bounded R2 direct adequacy for model-independent typed evidence decisions."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import evidence_decision_synthesis as producer
from canonical.runtime.bound_capabilities import evidence_decision_verify as independent
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA = "PROJECT_BRAIN_R2_TYPED_DECISION_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]
PRODUCER_ID = "decision.synthesis.typed.stdlib"
VERIFIER_ID = "decision.synthesis.verify.stdlib"

_PATH = r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR = re.compile(
    r"^Decide from the typed evidence (?P<input>" + _PATH + r"\.json) "
    r"and write the result to (?P<output>" + _PATH + r"\.json)\.?$",
    re.IGNORECASE,
)


def _base(status: str, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _inside(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    rr = root.resolve()
    if path == rr or rr not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return path


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _verified_entry(registry: Mapping[str, Any], capability_id: str) -> Mapping[str, Any]:
    entry = registry.get(capability_id)
    if not isinstance(entry, Mapping) or entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
        raise ValueError("VERIFIED_BOUND_CAPABILITY_REQUIRED:" + capability_id)
    return entry


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}

    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    root = Path(repo_root).resolve()
    input_path = match.group("input")
    output_path = match.group("output")
    try:
        source = _inside(root, input_path)
        destination = _inside(root, output_path)
        if source == destination:
            raise ValueError("INPUT_OUTPUT_PATHS_MUST_DIFFER")
        if not source.is_file():
            raise ValueError("TYPED_DECISION_INPUT_MISSING")
        problem = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(problem, dict) or problem.get("schema") != producer.SCHEMA:
            raise ValueError("TYPED_DECISION_SCHEMA_INVALID")

        # Validate the typed contract without executing a decision or mutating state.
        producer._normalize(problem)

        registry = live_bound.load_verified_registry()
        producer_entry = _verified_entry(registry, PRODUCER_ID)
        verifier_entry = _verified_entry(registry, VERIFIER_ID)
        if str(producer_entry.get("adapter_module") or "") != "evidence_decision_synthesis":
            raise ValueError("DECISION_PRODUCER_ADAPTER_MISMATCH")
        if str(verifier_entry.get("adapter_module") or "") != "evidence_decision_verify":
            raise ValueError("DECISION_VERIFIER_ADAPTER_MISMATCH")
        pver = producer_entry.get("verification")
        vver = verifier_entry.get("verification")
        if (
            not isinstance(pver, Mapping)
            or pver.get("independently_verified_by") != VERIFIER_ID
            or int(pver.get("model_dependency_count", -1)) != 0
        ):
            raise ValueError("DECISION_PRODUCER_INDEPENDENT_VERIFICATION_BINDING_INVALID")
        if (
            not isinstance(vver, Mapping)
            or vver.get("producer_independent") is not True
            or int(vver.get("model_dependency_count", -1)) != 0
        ):
            raise ValueError("DECISION_VERIFIER_INDEPENDENCE_BINDING_INVALID")

        compiled_registry = goal_compiler._platform_admissible_registry(dict(registry))
        compiled = goal_compiler.compile_goal(goal, compiled_registry, root)
        if compiled.get("controller_actions") is not None:
            raise ValueError("COMPOUND_CONTROLLER_NOT_ALLOWED")
        if compiled.get("selected_capability") != PRODUCER_ID:
            raise ValueError("COMPILED_CAPABILITY_MISMATCH")
        inputs = compiled.get("inputs")
        if not isinstance(inputs, Mapping):
            raise ValueError("COMPILED_INPUTS_INVALID")
        if inputs.get("input_path") != input_path or inputs.get("output_path") != output_path:
            raise ValueError("COMPILED_PATH_BINDING_MISMATCH")
        targets = compiled.get("target_effects")
        if not isinstance(targets, list) or not targets:
            raise ValueError("COMPILED_TARGETS_INVALID")

        contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=targets,
        )
        if contract.get("pass") is not True:
            raise ValueError("LOSSLESS_RAW_CONTRACT_FAILED")

        return {
            **_base("DIRECT_TYPED_DECISION_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "policy_id": goal_scoped_policy_id(PRODUCER_ID, goal),
            "capability_id": PRODUCER_ID,
            "verifier_capability_id": VERIFIER_ID,
            "input_path": input_path,
            "output_path": output_path,
            "source_sha256": _sha(source),
            "decision_id": str(problem.get("decision_id") or ""),
            "raw_contract": contract,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "acceptance_obligation_count": len(contract["acceptance_contract"]["obligations"]),
            "transaction_scope": "ONE_REPOSITORY_LOCAL_OUTPUT_FILE",
            "preflight_execution_authority": False,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _restore(path: Path, existed: bool, prior: bytes | None) -> None:
    if existed:
        assert prior is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    verifier_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    pf = preflight(request, repo_root=repo_root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    root = Path(repo_root).resolve()
    source = _inside(root, str(pf["input_path"]))
    destination = _inside(root, str(pf["output_path"]))
    existed = destination.exists()
    prior = destination.read_bytes() if existed else None

    try:
        raw = live_bound.run_raw_goal(request)
        if not isinstance(raw, Mapping) or raw.get("pass") is not True:
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__TRANSACTIONAL_TYPED_DECISION_EXECUTION_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "transaction_rolled_back": True,
                "raw_result": deepcopy(dict(raw)) if isinstance(raw, Mapping) else raw,
            }

        if (
            raw.get("compiled_capability_id") != PRODUCER_ID
            or raw.get("raw_goal_sha256") != pf["goal_sha256"]
            or raw.get("raw_source_coverage_complete") is not True
            or not destination.is_file()
            or _sha(source) != pf["source_sha256"]
        ):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "reason": "EXECUTION_IDENTITY_OUTPUT_OR_SOURCE_IMMUTABILITY_MISMATCH",
                "transaction_rolled_back": True,
            }

        result = json.loads(destination.read_text(encoding="utf-8"))
        evidence = (
            verifier_provider(pf)
            if verifier_provider is not None
            else independent.run(
                {
                    "input_path": pf["input_path"],
                    "result_path": pf["output_path"],
                },
                root,
            )
        )
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("verified") is not True
            or evidence.get("producer_independent") is not True
            or int(evidence.get("model_dependency_count", -1)) != 0
        ):
            _restore(destination, existed, prior)
            return {
                **_base("OPEN__INDEPENDENT_TYPED_DECISION_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "transaction_rolled_back": True,
                "independent_verification": deepcopy(dict(evidence))
                if isinstance(evidence, Mapping) else None,
            }

        if (
            result.get("schema") != producer.RESULT_SCHEMA
            or result.get("decision_id") != pf["decision_id"]
            or result.get("model_dependency_count") != 0
        ):
            _restore(destination, existed, prior)
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "capability_id": pf["capability_id"],
                "reason": "VERIFIED_RESULT_IDENTITY_MISMATCH",
                "transaction_rolled_back": True,
            }

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        return {
            **_base("PASS__TRANSACTIONAL_TYPED_DECISION_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "policy_id": pf["policy_id"],
            "capability_id": PRODUCER_ID,
            "verifier_capability_id": VERIFIER_ID,
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "input_path": pf["input_path"],
            "output_path": pf["output_path"],
            "source_sha256": pf["source_sha256"],
            "decision_id": result.get("decision_id"),
            "decision_status": result.get("status"),
            "selected_alternative": result.get("selected_alternative"),
            "decision_confidence": result.get("decision_confidence"),
            "accepted_raw_obligation_ids": accepted_ids,
            "raw_acceptance_obligation_count": len(accepted_ids),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "policy_adequacy_authority": True,
            "transaction_committed": True,
            "transaction_rolled_back": False,
            "independent_verification": deepcopy(dict(evidence)),
            "raw_result": deepcopy(dict(raw)),
            "authority_boundary": (
                "ONLY_EXACT_TYPED_DECISION_JSON_TO_VERIFIED_DECISION_JSON_GRAMMAR;"
                "INPUT_MUST_ALREADY_SATISFY_PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1;"
                "SOURCE_BYTES_IMMUTABLE;ONE_REPOSITORY_LOCAL_OUTPUT;"
                "MODEL_DEPENDENCY_COUNT_ZERO;"
                "PRODUCER_INDEPENDENT_FULL_DECISION_RECOMPUTATION;"
                "NO_ARBITRARY_NATURAL_LANGUAGE_INTERPRETATION;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        _restore(destination, existed, prior)
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "policy_id": pf.get("policy_id"),
            "capability_id": pf.get("capability_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
            "transaction_rolled_back": True,
        }
