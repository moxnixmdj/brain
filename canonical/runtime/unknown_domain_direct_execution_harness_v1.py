"""Frozen interaction harness for Unknown-Domain direct evaluation V1.

The candidate receives only (case_visible, transcript). Hidden evaluator truth is
held by the harness and passed only to the frozen hidden scorer after a terminal
candidate action. Probe results enter the transcript only after the candidate
requests an allowed probe.

This module does not generate production cases and grants no execution authority.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_HARNESS_V1"
TERMINAL_TYPES={"CONCLUDE","ABSTAIN","REQUEST_DISCRIMINATOR"}
MAX_TRANSFER_PROBES=2
MAX_STEPS=4


class UnknownDomainHarnessError(ValueError):
    pass


def _allowed_probes(case_visible: Mapping[str,Any]) -> dict[str,Mapping[str,Any]]:
    leaf=case_visible.get("leaf_id")
    if leaf==scorer.TRANSFER:
        rows=case_visible.get("domain_b",{}).get("allowed_probes",[])
    elif leaf==scorer.ABSTAIN:
        rows=case_visible.get("allowed_probes",[])
    else:
        raise UnknownDomainHarnessError("LEAF_ID_UNKNOWN")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)):
        raise UnknownDomainHarnessError("ALLOWED_PROBES_INVALID")
    out={}
    for row in rows:
        if not isinstance(row,Mapping):
            raise UnknownDomainHarnessError("ALLOWED_PROBE_NOT_OBJECT")
        pid=str(row.get("probe_id") or "").strip()
        if not pid or pid in out:
            raise UnknownDomainHarnessError("ALLOWED_PROBE_ID_INVALID_OR_DUPLICATE")
        out[pid]=row
    return out


def _terminal_trace(action: Mapping[str,Any], *, probe_count:int) -> dict[str,Any]:
    kind=str(action.get("type") or "").strip()
    if kind not in TERMINAL_TYPES:
        raise UnknownDomainHarnessError("TERMINAL_ACTION_TYPE_INVALID")
    trace={k:v for k,v in action.items() if k!="type"}
    trace["decision"]=kind
    trace["domain_b_discovery_probe_count"]=probe_count
    return trace


def execute_case(
    *,
    candidate_step: Callable[[Mapping[str,Any], Sequence[Mapping[str,Any]]], Mapping[str,Any]],
    case_visible: Mapping[str,Any],
    hidden_record: Mapping[str,Any],
) -> dict[str,Any]:
    if not callable(candidate_step):
        raise UnknownDomainHarnessError("CANDIDATE_STEP_NOT_CALLABLE")
    if not isinstance(case_visible,Mapping) or not isinstance(hidden_record,Mapping):
        raise UnknownDomainHarnessError("CASE_PACKET_INVALID")
    if case_visible.get("case_id")!=hidden_record.get("case_id"):
        raise UnknownDomainHarnessError("CASE_ID_MISMATCH")
    if case_visible.get("leaf_id")!=hidden_record.get("leaf_id"):
        raise UnknownDomainHarnessError("LEAF_ID_MISMATCH")

    allowed=_allowed_probes(case_visible)
    hidden_table=hidden_record.get("allowed_probe_outcome_table",{})
    if not isinstance(hidden_table,Mapping):
        raise UnknownDomainHarnessError("HIDDEN_PROBE_TABLE_INVALID")

    transcript=[]
    requested=set()
    for step_index in range(MAX_STEPS):
        # Fresh containers prevent accidental mutation of harness-owned packets.
        visible_view=dict(case_visible)
        transcript_view=tuple(dict(x) for x in transcript)
        action=candidate_step(visible_view,transcript_view)
        if not isinstance(action,Mapping):
            raise UnknownDomainHarnessError("CANDIDATE_ACTION_NOT_OBJECT")
        kind=str(action.get("type") or "").strip()

        if kind=="REQUEST_PROBE":
            if case_visible.get("leaf_id")!=scorer.TRANSFER:
                raise UnknownDomainHarnessError("REQUEST_PROBE_ONLY_ALLOWED_FOR_TRANSFER")
            pid=str(action.get("probe_id") or "").strip()
            if pid not in allowed:
                raise UnknownDomainHarnessError("REQUESTED_PROBE_NOT_ALLOWED")
            if pid in requested:
                raise UnknownDomainHarnessError("REQUESTED_PROBE_DUPLICATE")
            if len(requested)>=MAX_TRANSFER_PROBES:
                raise UnknownDomainHarnessError("TRANSFER_PROBE_BUDGET_EXCEEDED")
            if pid not in hidden_table:
                raise UnknownDomainHarnessError("HIDDEN_PROBE_RESULT_MISSING")
            requested.add(pid)
            transcript.append({
                "step":step_index,
                "requested_probe_id":pid,
                "probe_result":hidden_table[pid],
            })
            continue

        if kind in TERMINAL_TYPES:
            trace=_terminal_trace(action,probe_count=len(requested))
            result=scorer.score_case(hidden_record,trace)
            return {
                "schema":SCHEMA,
                "case_id":case_visible.get("case_id"),
                "leaf_id":case_visible.get("leaf_id"),
                "candidate_terminal_action":dict(action),
                "transcript":transcript,
                "probe_count":len(requested),
                "scorer_result":result,
                "acceptance_credit_delta":0,
                "family_credit_delta":0,
                "promotion_authority":False,
            }

        raise UnknownDomainHarnessError("CANDIDATE_ACTION_TYPE_INVALID")

    raise UnknownDomainHarnessError("MAX_STEPS_EXCEEDED")
