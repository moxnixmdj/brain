"""Transactional direct R2 adequacy for exact literal DOCX creation goals.

Bounded accepted form:
  Create <canonical/*.docx> with title <...>, paragraph <...>, and a table
  with columns|headers <...> containing <rows>.
  Finally independently reopen the DOCX and verify all requested content.

Adequacy requires the current deterministic compiler to emit exactly:
  docx.document.create.python_docx
  -> docx.document.verify.intent_ooxml
  -> finish

The producer-created intent sidecar is not trusted by itself. This controller
independently binds it back to the exact raw creation clause, then reruns the
stdlib OOXML verifier and requires semantic equality with an independently
parsed expected structure. The DOCX and sidecar are one transaction and are
restored/removed together on every failed execution or acceptance path.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime import docx_goal_compiler
from canonical.runtime import live_integrated_brain_v1 as live_bound
from canonical.runtime.bound_capabilities import docx_verify_ooxml_intent
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA = "PROJECT_BRAIN_R2_DOCX_DIRECT_ADEQUACY_V1"
ROOT = Path(__file__).resolve().parents[2]
PRODUCER = "docx.document.create.python_docx"
VERIFIER = "docx.document.verify.intent_ooxml"
POLICY_PREFIX = "BOUND_CAPABILITY_POLICY::"
GOAL_SCOPE_MARKER = "::RAW_GOAL_SHA256::"


def _goal_scoped_policy_id(capability_id: str, goal: str) -> str:
    cid = str(capability_id or "").strip()
    text = str(goal or "").strip()
    if not cid or not text:
        raise ValueError("CAPABILITY_ID_AND_GOAL_REQUIRED")
    return POLICY_PREFIX + cid + GOAL_SCOPE_MARKER + sha256(text.encode("utf-8")).hexdigest()

_CREATION = re.compile(
    r"^Create (?P<output>canonical/[A-Za-z0-9_.\-/]+\.docx) "
    r"with title (?P<title>.+?), paragraph (?P<paragraph>.+?), and a table "
    r"with (?:columns|headers) (?P<headers>.+?) containing (?P<rows>.+)$",
    re.IGNORECASE,
)
_VERIFY_CLAUSE = re.compile(
    r"^Finally independently reopen the DOCX and verify all requested content$",
    re.IGNORECASE,
)


def _base(status: str, passed: bool = False, **extra: Any) -> dict[str, Any]:
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
        **extra,
    }


def _inside(root: Path, rel: str) -> Path:
    pp = PurePosixPath(str(rel))
    if pp.is_absolute() or ".." in pp.parts or not str(rel).startswith("canonical/"):
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    path = (root / str(rel)).resolve()
    rr = root.resolve()
    if path == rr or rr not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return path


def _snapshot(path: Path) -> tuple[bool, bytes | None]:
    return (True, path.read_bytes()) if path.is_file() else (False, None)


def _restore(path: Path, state: tuple[bool, bytes | None]) -> None:
    existed, prior = state
    if existed:
        assert prior is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def _routing_targets(compiled: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for part in compiled.get("compiled_parts") or []:
        if not isinstance(part, Mapping):
            continue
        for effect in part.get("target_effects") or []:
            if isinstance(effect, str) and effect and effect not in out:
                out.append(effect)
    return out


def preflight(request: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return _base("FAIL_CLOSED", reason="REQUEST_NOT_OBJECT")
    task_id = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task_id or not goal:
        return _base("FAIL_CLOSED", reason="TASK_ID_AND_GOAL_REQUIRED")

    clauses = goal_compiler.decompose_goal(goal)
    if len(clauses) != 2:
        return {**_base("NOT_APPLICABLE"), "matched": False}
    creation, verify_clause = clauses
    match = _CREATION.fullmatch(creation)
    if match is None or _VERIFY_CLAUSE.fullmatch(verify_clause) is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}

    root = Path(repo_root).resolve()
    try:
        output_path = match.group("output")
        output = _inside(root, output_path)
        intent_path = output_path + ".intent.json"
        intent = _inside(root, intent_path)

        expected = docx_goal_compiler.expected_from_creation(creation)
        if not isinstance(expected, Mapping):
            raise ValueError("DOCX_EXPECTED_STRUCTURE_UNRESOLVED")
        expected = deepcopy(dict(expected))
        if (
            expected.get("title") != match.group("title").strip(" .,:;")
            or not expected.get("paragraphs")
            or not expected.get("headers")
            or not expected.get("rows")
        ):
            raise ValueError("DOCX_EXPECTED_STRUCTURE_BINDING_MISMATCH")

        registry = live_bound.load_verified_registry()
        compiled = goal_compiler.compile_goal(goal, dict(registry), root)
        parts = compiled.get("compiled_parts")
        actions = compiled.get("controller_actions")
        if (
            compiled.get("compiler_mode") != "DETERMINISTIC_COMPOUND_ACTION_PLAN"
            or compiled.get("clause_coverage_verified") is not True
            or not isinstance(parts, list)
            or len(parts) != 2
            or not isinstance(actions, list)
            or len(actions) != 3
        ):
            raise ValueError("DOCX_COMPILED_SHAPE_INVALID")

        p0, p1 = parts
        a0, a1, a2 = actions
        if any(not isinstance(x, Mapping) for x in (p0, p1, a0, a1, a2)):
            raise ValueError("DOCX_COMPILED_ROW_INVALID")
        if (
            p0.get("index") != 0
            or p0.get("mode") != "VERIFIED_CAPABILITY"
            or p0.get("selected_capability") != PRODUCER
            or p0.get("subgoal") != creation
            or (p0.get("inputs") or {}).get("goal") != creation
            or (p0.get("inputs") or {}).get("output_path") != output_path
            or p1.get("index") != 1
            or p1.get("mode") != "VERIFIED_CAPABILITY"
            or p1.get("selected_capability") != VERIFIER
            or p1.get("subgoal") != verify_clause
        ):
            raise ValueError("DOCX_CAPABILITY_CHAIN_MISMATCH")

        if (
            a0.get("type") != "invoke_capability"
            or (a0.get("args") or {}).get("capability_id") != PRODUCER
            or (a0.get("args") or {}).get("goal") != creation
            or (a0.get("args") or {}).get("output_path") != output_path
            or (a0.get("expect") or {}).get("field") != "output_verified"
            or (a0.get("expect") or {}).get("value") is not True
            or a1.get("type") != "invoke_capability"
            or (a1.get("args") or {}).get("capability_id") != VERIFIER
            or (a1.get("args") or {}).get("path") != output_path
            or (a1.get("expect") or {}).get("field") != "verified"
            or (a1.get("expect") or {}).get("value") is not True
            or a2.get("type") != "finish"
            or (a2.get("args") or {}).get("summary") != "COMPOUND_GOAL_COMPLETE"
        ):
            raise ValueError("DOCX_ACTION_CHAIN_MISMATCH")

        producer_entry = registry.get(PRODUCER)
        verifier_entry = registry.get(VERIFIER)
        producer_verification = (
            producer_entry.get("verification") if isinstance(producer_entry, Mapping) else None
        )
        verifier_verification = (
            verifier_entry.get("verification") if isinstance(verifier_entry, Mapping) else None
        )
        sidecar_extension = (
            producer_verification.get("intent_sidecar_extension")
            if isinstance(producer_verification, Mapping)
            else None
        )
        if (
            not isinstance(producer_entry, Mapping)
            or producer_entry.get("status") != "VERIFIED_BOUND_CAPABILITY"
            or not isinstance(producer_verification, Mapping)
            or producer_verification.get("independently_verified_by") != "docx.document.verify.ooxml"
            or not isinstance(sidecar_extension, Mapping)
            or sidecar_extension.get("independently_reparsed") is not True
            or sidecar_extension.get("raw_intent_persisted") is not True
            or not isinstance(verifier_entry, Mapping)
            or verifier_entry.get("status") != "VERIFIED_BOUND_CAPABILITY"
            or verifier_entry.get("adapter_module") != "docx_verify_ooxml_intent"
            or not isinstance(verifier_verification, Mapping)
            or verifier_verification.get("independently_verified") is not True
            or (verifier_entry.get("source") or {}).get("type") != "python_stdlib"
        ):
            raise ValueError("DOCX_REGISTRY_INDEPENDENCE_BINDING_INVALID")

        targets = _routing_targets(compiled)
        if "docx.document.create" not in targets or "docx.document.verify" not in targets:
            raise ValueError("DOCX_ROUTING_EFFECTS_INCOMPLETE")
        contract = compile_contract(goal, source_id="user", routing_target_effects=targets)
        if contract.get("pass") is not True:
            raise ValueError("LOSSLESS_RAW_CONTRACT_FAILED")

        return {
            **_base("DIRECT_DOCX_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "task_id": task_id,
            "goal": goal,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "creation_clause": creation,
            "verification_clause": verify_clause,
            "output_path": output_path,
            "intent_path": intent_path,
            "expected": expected,
            "producer_capability_id": PRODUCER,
            "verifier_capability_id": VERIFIER,
            "policy_id": _goal_scoped_policy_id(PRODUCER, goal),
            "routing_target_effects": targets,
            "raw_contract": contract,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "acceptance_obligation_count": len(contract["acceptance_contract"]["obligations"]),
            "transaction_scope": "DOCX_PLUS_INTENT_SIDECAR",
            "preflight_execution_authority": False,
            "destination_existed_before": output.exists(),
            "intent_existed_before": intent.exists(),
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _trace_verified(raw: Mapping[str, Any], pf: Mapping[str, Any]) -> bool:
    controller = raw.get("controller_execution")
    trace = controller.get("trace") if isinstance(controller, Mapping) else None
    if (
        not isinstance(controller, Mapping)
        or controller.get("returncode") != 0
        or controller.get("controller_mode") != "MODEL_INDEPENDENT_ACTION_PLAN"
        or controller.get("final_summary") != "COMPOUND_GOAL_COMPLETE"
        or not isinstance(trace, list)
        or len(trace) != 3
    ):
        return False
    t0, t1, t2 = trace
    if any(not isinstance(x, Mapping) for x in (t0, t1, t2)):
        return False
    p0, r0 = t0.get("plan"), t0.get("result")
    p1, r1 = t1.get("plan"), t1.get("result")
    p2, r2 = t2.get("plan"), t2.get("result")
    return bool(
        isinstance(p0, Mapping)
        and p0.get("type") == "invoke_capability"
        and (p0.get("args") or {}).get("capability_id") == PRODUCER
        and (p0.get("args") or {}).get("goal") == pf["creation_clause"]
        and (p0.get("args") or {}).get("output_path") == pf["output_path"]
        and isinstance(r0, Mapping)
        and r0.get("output_verified") is True
        and r0.get("output_path") == pf["output_path"]
        and r0.get("intent_path") == pf["intent_path"]
        and isinstance(p1, Mapping)
        and p1.get("type") == "invoke_capability"
        and (p1.get("args") or {}).get("capability_id") == VERIFIER
        and (p1.get("args") or {}).get("path") == pf["output_path"]
        and isinstance(r1, Mapping)
        and r1.get("verified") is True
        and r1.get("producer_independent_verifier") is True
        and r1.get("intent_source_goal") == pf["creation_clause"]
        and r1.get("intent_derived_expected") == pf["expected"]
        and isinstance(p2, Mapping)
        and p2.get("type") == "finish"
        and (p2.get("args") or {}).get("summary") == "COMPOUND_GOAL_COMPLETE"
        and isinstance(r2, Mapping)
        and r2.get("summary") == "COMPOUND_GOAL_COMPLETE"
    )


def run(request: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    pf = preflight(request, repo_root=repo_root)
    if pf.get("matched") is not True or pf.get("status") == "FAIL_CLOSED":
        return pf

    root = Path(repo_root).resolve()
    output = _inside(root, str(pf["output_path"]))
    intent = _inside(root, str(pf["intent_path"]))
    output_state = _snapshot(output)
    intent_state = _snapshot(intent)

    def rollback() -> None:
        _restore(output, output_state)
        _restore(intent, intent_state)

    try:
        raw = live_bound.run_raw_goal(request)
        if (
            not isinstance(raw, Mapping)
            or raw.get("pass") is not True
            or raw.get("compiler_mode") != "DETERMINISTIC_COMPOUND_ACTION_PLAN"
            or raw.get("raw_goal_sha256") != pf["goal_sha256"]
            or raw.get("raw_source_coverage_complete") is not True
            or raw.get("raw_task_contract_sha256") != pf["raw_task_contract_sha256"]
            or not output.is_file()
            or not intent.is_file()
            or not _trace_verified(raw, pf)
        ):
            rollback()
            return {
                **_base("OPEN__TRANSACTIONAL_DOCX_EXECUTION_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "transaction_rolled_back": True,
                "raw_result": deepcopy(dict(raw)) if isinstance(raw, Mapping) else raw,
            }

        sidecar = json.loads(intent.read_text(encoding="utf-8"))
        if (
            sidecar.get("schema") != "PROJECT_BRAIN_DOCUMENT_INTENT_V1"
            or sidecar.get("source_goal") != pf["creation_clause"]
            or sidecar.get("output_path") != pf["output_path"]
        ):
            rollback()
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "reason": "DOCX_INTENT_SIDECAR_RAW_GOAL_BINDING_INVALID",
                "transaction_rolled_back": True,
            }

        evidence = docx_verify_ooxml_intent.run({"path": pf["output_path"]}, root)
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("verified") is not True
            or evidence.get("producer_independent_verifier") is not True
            or evidence.get("intent_source_goal") != pf["creation_clause"]
            or evidence.get("intent_derived_expected") != pf["expected"]
            or evidence.get("expected") != pf["expected"]
            or evidence.get("title_ok") is not True
            or evidence.get("paragraphs_ok") is not True
            or evidence.get("table_ok") is not True
        ):
            rollback()
            return {
                **_base("OPEN__INDEPENDENT_DOCX_ACCEPTANCE_DID_NOT_VERIFY"),
                "matched": True,
                "policy_id": pf["policy_id"],
                "transaction_rolled_back": True,
                "independent_verification": deepcopy(dict(evidence))
                if isinstance(evidence, Mapping) else None,
            }

        obligations = pf["raw_contract"]["acceptance_contract"]["obligations"]
        accepted_ids = [str(row["obligation_id"]) for row in obligations]
        if not accepted_ids:
            rollback()
            return {
                **_base("FAIL_CLOSED"),
                "matched": True,
                "reason": "DOCX_RAW_OBLIGATIONS_EMPTY",
                "transaction_rolled_back": True,
            }

        return {
            **_base("PASS__TRANSACTIONAL_DOCX_POLICY_ADEQUACY_VERIFIED", True),
            "matched": True,
            "policy_id": pf["policy_id"],
            "capability_id": PRODUCER,
            "goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": pf["raw_task_contract_sha256"],
            "output_path": pf["output_path"],
            "intent_path": pf["intent_path"],
            "expected": deepcopy(pf["expected"]),
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
                "ONLY_THE_EXACT_TWO_CLAUSE_LITERAL_DOCX_GRAMMAR;"
                "DOCX_PLUS_INTENT_SIDECAR_TRANSACTION;"
                "EXACT_SIDECAR_TO_RAW_CREATION_CLAUSE_BINDING;"
                "PRODUCER_INDEPENDENT_STDLIB_OOXML_SEMANTIC_VERIFICATION;"
                "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT_AUTHORITY"
            ),
        }
    except Exception as exc:
        rollback()
        return {
            **_base("FAIL_CLOSED"),
            "matched": True,
            "policy_id": pf.get("policy_id"),
            "reason": type(exc).__name__ + ":" + str(exc),
            "transaction_rolled_back": True,
        }
