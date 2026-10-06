from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import browser_state_information_safe_candidate as browser_candidate
from canonical.runtime import browser_state_information_safe_proof as browser
from canonical.runtime import contract_native_brain_candidate as contract_candidate
from canonical.runtime import contract_native_proof_suites as contract
from canonical.runtime import delegation_structural_variety_proof_v3 as delegation_v3
from canonical.runtime import delegation_whole_scope_candidate_v2 as delegation_candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_v2
from canonical.runtime import m0a_raw_source_brain_candidate_v2 as m0_candidate
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0
from canonical.runtime import native_artifact_cross_format_candidate_v1 as native_candidate
from canonical.runtime import native_artifact_cross_format_proof_v1 as native
from canonical.runtime import tool_discovery_information_safe_candidate as tool_candidate
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool

KINDS = {
    "browser",
    "tool",
    "delegation_v2",
    "delegation_v3",
    "m0",
    "m0_change",
    "structured",
    "p1",
    "p2",
    "p3",
    "native",
}


class TokenAdapterError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TokenAdapterError("TOKEN_INVALID")
    return value.strip()


def _replace_in_set(value: set[str], old: str, new: str) -> set[str]:
    return {new if x == old else x for x in value}


def inject_token(kind: str, raw_case: Mapping[str, Any], token: str) -> dict[str, Any]:
    if kind not in KINDS:
        raise TokenAdapterError("KIND_INVALID:" + str(kind))
    token = _token(token)
    case = copy.deepcopy(dict(raw_case))

    if kind == "browser":
        old = str(case["_oracle"]["target"])
        if token in case["_initial_state"]["statuses"] and token != old:
            raise TokenAdapterError("BROWSER_TOKEN_COLLISION")
        case["goal"]["record_id"] = token
        case["_oracle"]["target"] = token
        statuses = case["_initial_state"]["statuses"]
        statuses[token] = statuses.pop(old)
        if case["_initial_state"]["selected"] == old:
            case["_initial_state"]["selected"] = token
        return case

    if kind == "tool":
        old = str(case["stage1"]["required_capabilities"][0])
        for stage in ("stage1", "stage2"):
            row = case[stage]
            row["required_capabilities"] = [
                token if str(x) == old else str(x)
                for x in row["required_capabilities"]
            ]
        for table_name in ("epoch0", "epoch1"):
            table = case["_oracle"][table_name]
            for tid in list(table):
                table[tid] = _replace_in_set(set(table[tid]), old, token)
        return case

    if kind in {"delegation_v2", "delegation_v3"}:
        task = case["task"]
        required = set(task["required_outputs"])
        finals = [
            row for row in task["steps"]
            if required.intersection(set(row["produces"]))
        ]
        if not finals:
            raise TokenAdapterError("DELEGATION_FINAL_STEP_NOT_FOUND")
        for final in finals:
            final["evidence_outputs"] = list(final["evidence_outputs"]) + [token]
        return case

    if kind in {"m0", "m0_change"}:
        oracle = case["_oracle"]
        requirements = oracle.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            raise TokenAdapterError("M0_RESOLVED_REQUIREMENT_REQUIRED")
        first = requirements[0]
        old = str(first["object"])
        if old not in case["raw_source"]:
            raise TokenAdapterError("M0_OBJECT_NOT_IN_SOURCE")
        case["raw_source"] = case["raw_source"].replace(old, token, 1)
        first["object"] = token
        return case

    if kind == "structured":
        reqs = case["task"]["requirements"]
        if not reqs:
            raise TokenAdapterError("STRUCTURED_REQUIREMENT_REQUIRED")
        old = str(reqs[0]["id"])
        reqs[0]["id"] = token
        vi = case["task"]["visible_inputs"]
        vi[token] = vi.pop(old)
        for probe in case["_oracle"]["hidden_probes"]:
            probe[token] = probe.pop(old)
        return case

    if kind == "p1":
        old = str(case["_oracle"]["repair_id"])
        found = False
        for row in case["task"]["repair_candidates"]:
            if str(row["id"]) == old:
                row["id"] = token
                found = True
                break
        if not found:
            raise TokenAdapterError("P1_REPAIR_NOT_FOUND")
        case["_oracle"]["repair_id"] = token
        return case

    if kind == "p2":
        actions = case["task"]["edit_candidates"]
        if not actions:
            raise TokenAdapterError("P2_ACTION_REQUIRED")
        chosen = actions[0]
        chosen["id"] = token
        chosen["supported"] = True
        chosen["hard_violation"] = False
        chosen["cost"] = 1
        chosen["scores"] = {
            key: 100 for key in case["task"]["rubric_weights"]
        }
        case["task"]["edit_budget"] = max(
            1, int(case["task"]["edit_budget"])
        )
        return case

    if kind == "p3":
        evidence = case["task"]["evidence"]
        required = [row for row in evidence if row.get("role") == "required"]
        if not required:
            raise TokenAdapterError("P3_REQUIRED_CLAIM_NOT_FOUND")
        row = required[0]
        old = str(row["claim_id"])
        row["claim_id"] = token
        for key in ("required", "allowed_optional", "forbidden", "uncertainty"):
            vals = list(case["_oracle"][key])
            case["_oracle"][key] = [
                token if str(x) == old else str(x)
                for x in vals
            ]
        return case

    if kind == "native":
        fmt = str(case["task"]["format"])
        edit = case["task"]["edit"]
        source = native._unb64(case["task"]["document_b64"])
        old = str(case["_oracle"]["old"])
        case["_oracle"]["new"] = token
        if fmt == "pdf":
            edit["new"] = token
        else:
            edit["new_text"] = token
            case["_oracle"]["expected_snapshot"] = native._expected_snapshot(
                fmt, source, old, token
            )
        return case

    raise AssertionError(kind)


def _token_in_native_output(case: Mapping[str, Any], candidate: Mapping[str, Any], token: str) -> bool:
    try:
        out = native._unb64(candidate["output_b64"])
        fmt = str(case["task"]["format"])
        if fmt == "pdf":
            snapshot = native._pdf_snapshot(out)
        else:
            snapshot = native._snapshot(fmt, out)
        return token in json.dumps(snapshot, sort_keys=True, default=str)
    except Exception:
        return False


def run_component(kind: str, case: Mapping[str, Any], token: str) -> dict[str, Any]:
    if kind not in KINDS:
        raise TokenAdapterError("KIND_INVALID:" + str(kind))
    token = _token(token)

    if kind == "browser":
        verdict = browser.run_episode(case, browser_candidate.next_action)
        observed = token if verdict.get("pass") is True else None
        candidate = {"history": verdict.get("history", [])}

    elif kind == "tool":
        verdict = tool.score_episode(case, tool_candidate.next_action)
        observed = token if (
            verdict.get("pass") is True
            and token in json.dumps(verdict, sort_keys=True, default=str)
        ) else None
        candidate = {
            "stage1": verdict.get("stage1"),
            "stage2": verdict.get("stage2"),
        }

    elif kind == "delegation_v2":
        first = delegation_candidate.solve_initial(
            delegation_v2.public_initial(case)
        )
        second = delegation_candidate.solve_after_receipt(
            delegation_v2.public_after_receipt(case), first
        )
        verdict = delegation_v2.score_episode(case, first, second)
        candidate = {"initial": first, "revised": second}
        observed = token if (
            verdict.get("pass") is True
            and token in set(first.get("terminal_evidence") or [])
            and token in set(second.get("terminal_evidence") or [])
        ) else None

    elif kind == "delegation_v3":
        candidate = delegation_candidate._solve(
            delegation_v3.public_case(case)["task"]
        )
        verdict = delegation_v3.score_case(case, candidate)
        observed = token if (
            verdict.get("pass") is True
            and token in set(candidate.get("terminal_evidence") or [])
        ) else None

    elif kind in {"m0", "m0_change"}:
        candidate = m0_candidate.solve(m0.public_task(case))
        verdict = m0.score_case(case, candidate)
        objects = {
            str(row.get("object"))
            for row in candidate.get("requirements", [])
            if isinstance(row, Mapping)
        }
        observed = token if verdict.get("pass") is True and token in objects else None

    elif kind in {"structured", "p1", "p2", "p3"}:
        candidate = contract_candidate.solve(contract.public_task(case))
        verdict = contract.score_case(case, candidate)
        if kind == "structured":
            vals = {
                str(row.get("factor"))
                for row in candidate.get("graph", [])
                if isinstance(row, Mapping)
            }
        elif kind == "p1":
            vals = {str(candidate.get("repair_id"))}
        elif kind == "p2":
            vals = {str(x) for x in candidate.get("selected_edits", [])}
        else:
            vals = {str(x) for x in candidate.get("selected_claims", [])}
        observed = token if verdict.get("pass") is True and token in vals else None

    elif kind == "native":
        candidate = native_candidate.solve(native.public_task(case))
        verdict = native.score_case(case, candidate)
        observed = token if (
            verdict.get("pass") is True
            and _token_in_native_output(case, candidate, token)
        ) else None

    else:
        raise AssertionError(kind)

    passed = bool(verdict.get("pass") is True and observed == token)
    return {
        "schema": "PROJECT_BRAIN_MATCHED_SUCCESS_SEMANTIC_TOKEN_COMPONENT_RESULT_V1",
        "kind": kind,
        "pass": passed,
        "base_scorer_pass": verdict.get("pass") is True,
        "observed_token": observed,
        "candidate_sha256": _sha(candidate),
        "scorer_result_sha256": _sha(verdict),
        "case_sha256": _sha(case),
        "candidate": candidate,
        "verdict": verdict,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
