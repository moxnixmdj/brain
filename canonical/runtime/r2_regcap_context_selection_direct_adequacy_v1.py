"""R2 direct adequacy for explicit bounded CCoB/CCyB/TLAC context selection V1."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import regcap_context_selection_v1 as producer
from canonical.runtime import regcap_context_selection_verify_v1 as verifier

SCHEMA = "PROJECT_BRAIN_R2_REGCAP_CONTEXT_SELECTION_DIRECT_ADEQUACY_V1"
ROUTE_ID = "DIRECT_ADEQUACY::REGCAP_CONTEXT_SELECTION_CCOB_CCYB_TLAC_V1"
CAPABILITY_ID = "finance.regcap.context_selection.ccob_ccyb_tlac"
VERIFIER_CAPABILITY_ID = "finance.regcap.context_selection.verify.stdlib"
ROOT = Path(__file__).resolve().parents[2]

PATH_RE = r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR = re.compile(
    r'^Using the bounded regulatory-capital context case at '
    r'(?P<input>' + PATH_RE + r'\.json), identify which of CCoB, CCyB, and TLAC '
    r'is selected for "loss-absorbing cushion" and save the independently verified '
    r'bounded selection to (?P<output>' + PATH_RE + r'\.json)\.?$',
    re.I,
)


def _base(status: str, passed: bool = False) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "matched": False,
        "direct_route_semantic_open": False,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "direct_adequacy_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _safe(root: str | Path, rel: str, *, require_file: bool = False) -> Path:
    root = Path(root).resolve()
    p = Path(str(rel or "").strip())
    if (
        p.is_absolute()
        or ".." in p.parts
        or not p.as_posix().startswith("canonical/")
    ):
        raise ValueError("PATH_INVALID")
    q = (root / p).resolve()
    if q == root or root not in q.parents or q.is_symlink():
        raise ValueError("PATH_OUTSIDE_REPOSITORY_OR_SYMLINK")
    if require_file and not q.is_file():
        raise ValueError("INPUT_FILE_REQUIRED")
    return q


def _load_case(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("CASE_JSON_INVALID") from exc
    if not isinstance(obj, dict):
        raise ValueError("CASE_OBJECT_REQUIRED")
    return raw, obj


def _contract(goal: str) -> list[str]:
    out = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=[
            "finance.regcap.context_selection.ccob_ccyb_tlac",
        ],
    )
    ids = list(
        (out.get("acceptance_contract") or {}).get("required_obligation_ids")
        or []
    )
    if out.get("pass") is not True or not ids:
        raise ValueError("RAW_TASK_CONTRACT_INVALID")
    return ids


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    if not isinstance(request, Mapping):
        return {**_base("FAIL_CLOSED"), "reason": "REQUEST_NOT_OBJECT"}
    task = str(request.get("task_id") or "").strip()
    goal = str(request.get("goal") or "").strip()
    if not task or not goal:
        return {**_base("FAIL_CLOSED"), "reason": "TASK_ID_AND_GOAL_REQUIRED"}
    match = GRAMMAR.fullmatch(goal)
    if match is None:
        return {**_base("NOT_APPLICABLE"), "matched": False}
    try:
        inp = match.group("input")
        out = match.group("output")
        ip = _safe(root, inp, require_file=True)
        op = _safe(root, out)
        if ip == op:
            raise ValueError("INPUT_OUTPUT_COLLISION")
        raw, case = _load_case(ip)

        produced = producer.compute(case, repo_root=root)
        if produced.get("status") == "FAIL_CLOSED":
            raise ValueError(
                "CONTEXT_SELECTION_FAIL_CLOSED:"
                + str(produced.get("reason") or "UNKNOWN")
            )
        if produced.get("pass") is not True:
            return {
                **_base("OPEN__REGCAP_CONTEXT_SELECTION_NOT_YET_PROVED"),
                "matched": False,
                "direct_route_semantic_open": True,
                "route_id": ROUTE_ID,
                "capability_id": CAPABILITY_ID,
                "input_path": inp,
                "input_sha256": sha256(raw).hexdigest(),
                "output_path": out,
                "effect_status": produced.get("status"),
                "minimum_discriminator_slots": [
                    "CCOB_2_5_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
                    "CCYB_RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
                    "TLAC_G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
                ],
                "producer_result": produced,
            }

        checked = verifier.verify(case, produced, repo_root=root)
        if checked.get("verified") is not True:
            raise ValueError(
                "PREFLIGHT_INDEPENDENT_RECOMPUTATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )
        ids = _contract(goal)
        gsha = sha256(goal.encode("utf-8")).hexdigest()
        isha = sha256(raw).hexdigest()
        return {
            **_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),
            "matched": True,
            "route_id": ROUTE_ID,
            "capability_id": CAPABILITY_ID,
            "verifier_capability_id": VERIFIER_CAPABILITY_ID,
            "policy_id": "R2_REGCAP_CONTEXT_SELECTION::" + gsha + "::" + isha,
            "goal_sha256": gsha,
            "input_path": inp,
            "input_sha256": isha,
            "output_path": out,
            "selected_concept_id": produced["selected_concept_id"],
            "raw_acceptance_obligation_ids": ids,
            "semantic_scope": (
                "EXPLICIT_TASK_UNIVERSE_CCOB_CCYB_TLAC__"
                "EXACT_ONE_loss-absorbing_cushion_OCCURRENCE__"
                "BOUNDED_CONTEXT_SIGNATURES_ONLY"
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


def _restore(path: Path, existed: bool, old: bytes | None) -> None:
    if existed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(old or b"")
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    pf = preflight(request, repo_root=root)
    if pf.get("matched") is not True:
        return pf
    if pf.get("status") == "FAIL_CLOSED":
        return pf

    ip = _safe(root, pf["input_path"], require_file=True)
    op = _safe(root, pf["output_path"])
    existed = op.is_file()
    old = op.read_bytes() if existed else None
    try:
        before = ip.read_bytes()
        if sha256(before).hexdigest() != pf["input_sha256"]:
            raise RuntimeError("INPUT_DRIFT_BEFORE_EXECUTION")
        case = json.loads(before.decode("utf-8"))
        produced = producer.compute(case, repo_root=root)
        if produced.get("pass") is not True:
            raise RuntimeError(
                "PRODUCER_SELECTION_NOT_PROVED:"
                + str(produced.get("status") or "UNKNOWN")
            )
        checked = verifier.verify(case, produced, repo_root=root)
        if (
            checked.get("verified") is not True
            or checked.get("producer_independent") is not True
            or checked.get("expected_concept_id") != produced.get("selected_concept_id")
        ):
            raise RuntimeError("INDEPENDENT_SELECTION_VERIFICATION_FAILED")

        output = {
            "schema": producer.RESULT_SCHEMA if hasattr(producer, "RESULT_SCHEMA") else produced["schema"],
            **dict(produced),
            "independent_verification": deepcopy(dict(checked)),
        }
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(
            json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        reread = json.loads(op.read_text(encoding="utf-8"))
        # Re-verify the producer portion rather than trusting the persisted
        # acceptance receipt to certify itself.
        producer_view = {
            key: value
            for key, value in reread.items()
            if key != "independent_verification"
        }
        checked2 = verifier.verify(case, producer_view, repo_root=root)
        if checked2.get("verified") is not True:
            raise RuntimeError("OUTPUT_READBACK_REVERIFICATION_FAILED")
        if ip.read_bytes() != before:
            raise RuntimeError("INPUT_MUTATION_DETECTED")
        ids = _contract(str(request["goal"]))
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
            "output_sha256": sha256(op.read_bytes()).hexdigest(),
            "selected_concept_id": produced["selected_concept_id"],
            "candidate_ids": list(produced["candidate_ids"]),
            "candidate_scope_complete_for_task": True,
            "global_phrase_identity_authority": False,
            "open_world_candidate_set_complete": False,
            "semantic_scope": pf["semantic_scope"],
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "direct_adequacy_authority": True,
            "accepted_raw_obligation_ids": ids,
            "raw_acceptance_obligation_count": len(ids),
            "acceptance_receipt": deepcopy(dict(checked2)),
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "source_immutability_verified": True,
            "authority_boundary": (
                "EXACT_EXPLICIT_THREE_RIVAL_TASK_SELECTION_ONLY__"
                "NO_GLOBAL_loss-absorbing_cushion_SYNONYMY__"
                "NO_OPEN_WORLD_REGCAP_CANDIDATE_COMPLETENESS"
            ),
        }
    except Exception as exc:
        _restore(op, existed, old)
        rollback = (
            op.is_file() and existed and op.read_bytes() == (old or b"")
            if existed else not op.exists()
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
