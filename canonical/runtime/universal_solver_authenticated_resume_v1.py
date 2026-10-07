"""Authenticated cross-run resume for Universal Verified Adaptive Solver.

A resume state is authoritative only when:
- its exact JSON bytes are content-addressed;
- a separate independent-verification receipt binds those exact bytes;
- the exact solver problem digest, task/episode/scope IDs, fact capsule head,
  and value capsule head all match;
- both append-only capsules independently re-verify now;
- the trace is structurally consistent with both capsules;
- the independent verifier explicitly reverified capsule integrity, trace/capsule
  consistency, and any prior effect outcomes.

This module does not create independent verification. It only authenticates it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)
from canonical.runtime.composition_state_capsule_v2 import verify_capsule
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_AUTHENTICATED_RESUME_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_RESUME_STATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_RESUME_STATE_INDEPENDENT_VERIFICATION_V1"


class ResumeError(ValueError):
    pass


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ResumeError(label + "_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ResumeError(label + "_ITEM_INVALID")
        token = item.strip()
        if token in out:
            raise ResumeError(label + "_DUPLICATE:" + token)
        out.append(token)
    return out


def _caps(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = problem.get("capabilities")
    if not isinstance(raw, list) or not raw:
        raise ResumeError("CAPABILITIES_REQUIRED")
    out: dict[str, Mapping[str, Any]] = {}
    for row in raw:
        if not isinstance(row, Mapping):
            raise ResumeError("CAPABILITY_NOT_OBJECT")
        cid = row.get("id")
        if not isinstance(cid, str) or not cid or cid in out:
            raise ResumeError("CAPABILITY_ID_INVALID_OR_DUPLICATE")
        out[cid] = row
    return out


def _trace_capsule_consistent(
    problem: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule: Mapping[str, Any],
    value_capsule: Mapping[str, Any],
) -> dict[str, Any]:
    fv = verify_capsule(fact_capsule)
    vv = verify_capsule(value_capsule)
    if fv.get("status") != "PASS":
        raise ResumeError("FACT_CAPSULE_INVALID:" + str(fv.get("reason")))
    if vv.get("status") != "PASS":
        raise ResumeError("VALUE_CAPSULE_INVALID:" + str(vv.get("reason")))

    initial = _tokens(problem.get("initial_facts", []), "INITIAL_FACTS")
    fact_records = fact_capsule.get("records")
    value_records = value_capsule.get("records")
    if not isinstance(fact_records, list) or not isinstance(value_records, list):
        raise ResumeError("CAPSULE_RECORDS_INVALID")
    offset = 1 if initial else 0
    if len(fact_records) != len(trace) + offset:
        raise ResumeError("FACT_CAPSULE_TRACE_CARDINALITY_MISMATCH")
    if len(value_records) != len(trace) + offset:
        raise ResumeError("VALUE_CAPSULE_TRACE_CARDINALITY_MISMATCH")

    caps = _caps(problem)
    for i, row in enumerate(trace):
        if not isinstance(row, Mapping):
            raise ResumeError("TRACE_ROW_INVALID:" + str(i))
        cid = row.get("capability_id")
        if not isinstance(cid, str) or cid not in caps:
            raise ResumeError("TRACE_CAPABILITY_UNKNOWN:" + str(i))
        cap = caps[cid]
        frec = fact_records[i + offset]
        vrec = value_records[i + offset]
        if frec.get("producer_ref") != cid or vrec.get("producer_ref") != cid:
            raise ResumeError("TRACE_CAPSULE_PRODUCER_MISMATCH:" + cid)

        requires = _tokens(cap.get("requires", []), cid + ".REQUIRES")
        provides = _tokens(cap.get("provides", []), cid + ".PROVIDES")
        if frec.get("requires") != ["fact:" + x for x in requires]:
            raise ResumeError("FACT_CAPSULE_REQUIRES_MISMATCH:" + cid)
        if frec.get("provides") != ["fact:" + x for x in provides]:
            raise ResumeError("FACT_CAPSULE_PROVIDES_MISMATCH:" + cid)
        if vrec.get("requires") != requires or vrec.get("provides") != provides:
            raise ResumeError("VALUE_CAPSULE_EFFECT_GRAPH_MISMATCH:" + cid)
        if sorted(row.get("new_verified_facts") or []) != sorted(provides):
            raise ResumeError("TRACE_PROVIDES_MISMATCH:" + cid)

        resolved_action = row.get("resolved_action")
        action_sha = row.get("action_contract_sha256")
        if not isinstance(resolved_action, Mapping):
            raise ResumeError("TRACE_RESOLVED_ACTION_MISSING:" + cid)
        if not isinstance(action_sha, str) or action_sha != v1._digest(resolved_action):
            raise ResumeError("TRACE_RESOLVED_ACTION_DIGEST_MISMATCH:" + cid)

        fprod = frec.get("producer_descriptor")
        if not isinstance(fprod, Mapping) or fprod.get("action_contract_sha256") != action_sha:
            raise ResumeError("FACT_CAPSULE_ACTION_DIGEST_MISMATCH:" + cid)

        fad = frec.get("action_descriptor")
        if not isinstance(fad, Mapping):
            raise ResumeError("FACT_CAPSULE_ACTION_DESCRIPTOR_INVALID:" + cid)
        for key in ("proposal_sha256", "verifier_id"):
            if fad.get(key) != row.get(key):
                raise ResumeError("FACT_CAPSULE_TRACE_FIELD_MISMATCH:" + cid + ":" + key)

        ev = frec.get("evidence_values")
        if not isinstance(ev, Mapping):
            raise ResumeError("FACT_CAPSULE_EVIDENCE_INVALID:" + cid)
        effect_sha = row.get("effect_outcome_sha256")
        has_effect_evidence = "effect_outcome" in ev
        if (effect_sha is not None) != has_effect_evidence:
            raise ResumeError("EFFECT_EVIDENCE_PRESENCE_MISMATCH:" + cid)
        if effect_sha is not None:
            if ev["effect_outcome"].get("effect_outcome_sha256") != effect_sha:
                raise ResumeError("EFFECT_EVIDENCE_DIGEST_MISMATCH:" + cid)

    fact_latest = fv.get("latest") or {}
    value_latest = vv.get("latest") or {}
    facts = sorted(k[5:] for k in fact_latest if isinstance(k, str) and k.startswith("fact:"))
    values = sorted(str(k) for k in value_latest)
    if facts != values:
        raise ResumeError("FACT_VALUE_CAPSULE_LATEST_DOMAIN_MISMATCH")

    return {
        "fact_capsule_head_hash": fv["head_hash"],
        "value_capsule_head_hash": vv["head_hash"],
        "current_facts": facts,
        "trace_length": len(trace),
        "effectful_transition_count": sum(
            1 for row in trace if isinstance(row, Mapping) and row.get("effect_outcome_sha256")
        ),
    }


def authenticate(
    binding: Mapping[str, Any],
    *,
    problem: Mapping[str, Any],
    repo_root: str | Path,
    expected_episode_id: str,
    expected_scope_id: str,
) -> dict[str, Any]:
    try:
        if not isinstance(binding, Mapping):
            raise ResumeError("RESUME_BINDING_INVALID")
        rr = resolve_receipt_bytes(binding.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(binding.get("verification"), repo_root=repo_root)
        rd = rr["document"]
        vd = vr["document"]
        if rd.get("schema") != RECEIPT_SCHEMA:
            raise ResumeError("RESUME_RECEIPT_SCHEMA_INVALID")
        if vd.get("schema") != VERIFY_SCHEMA:
            raise ResumeError("RESUME_VERIFY_SCHEMA_INVALID")
        if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
            raise ResumeError("RESUME_VERIFY_SUBJECT_MISMATCH")

        problem_sha = v1._digest(problem)
        required = {
            "problem_sha256": problem_sha,
            "task_id": problem.get("task_id"),
            "episode_id": expected_episode_id,
            "scope_id": expected_scope_id,
        }
        for key, expected in required.items():
            if rd.get(key) != expected:
                raise ResumeError("RESUME_RECEIPT_BINDING_MISMATCH:" + key)
            if vd.get(key) != expected:
                raise ResumeError("RESUME_VERIFY_BINDING_MISMATCH:" + key)

        fact_capsule = rd.get("fact_capsule")
        value_capsule = rd.get("value_capsule")
        trace = rd.get("trace")
        attempts = rd.get("attempts", [])
        counterexamples = rd.get("counterexamples", [])
        falsified = _tokens(rd.get("falsified_capability_ids", []), "FALSIFIED_CAPABILITY_IDS")
        deferred = _tokens(rd.get("deferred_capability_ids", []), "DEFERRED_CAPABILITY_IDS")
        if not isinstance(fact_capsule, Mapping) or not isinstance(value_capsule, Mapping):
            raise ResumeError("RESUME_CAPSULES_INVALID")
        if not isinstance(trace, list) or not isinstance(attempts, list) or not isinstance(counterexamples, list):
            raise ResumeError("RESUME_HISTORY_INVALID")

        consistency = _trace_capsule_consistent(problem, trace, fact_capsule, value_capsule)
        for key in ("fact_capsule_head_hash", "value_capsule_head_hash"):
            if rd.get(key) != consistency[key]:
                raise ResumeError("RESUME_RECEIPT_HEAD_MISMATCH:" + key)
            if vd.get(key) != consistency[key]:
                raise ResumeError("RESUME_VERIFY_HEAD_MISMATCH:" + key)

        verify_flags = (
            "pass",
            "independent_verified",
            "capsule_integrity_reverified",
            "trace_capsule_consistency_reverified",
        )
        if any(vd.get(key) is not True for key in verify_flags):
            raise ResumeError("RESUME_INDEPENDENT_VERIFICATION_INCOMPLETE")
        if consistency["effectful_transition_count"] and vd.get("effect_outcomes_reverified") is not True:
            raise ResumeError("RESUME_EFFECT_OUTCOMES_NOT_REVERIFIED")
        verifier_id = vd.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise ResumeError("RESUME_INDEPENDENT_VERIFIER_ID_MISSING")

        return {
            "schema": SCHEMA,
            "status": "PASS__AUTHENTICATED_SOLVER_RESUME_STATE",
            "pass": True,
            "receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
            "verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
            "independent_verifier_id": verifier_id.strip(),
            "problem_sha256": problem_sha,
            "current_facts": consistency["current_facts"],
            "fact_capsule": fact_capsule,
            "value_capsule": value_capsule,
            "trace": trace,
            "attempts": attempts,
            "counterexamples": counterexamples,
            "falsified_capability_ids": falsified,
            "deferred_capability_ids": deferred,
            "fact_capsule_head_hash": consistency["fact_capsule_head_hash"],
            "value_capsule_head_hash": consistency["value_capsule_head_hash"],
            "effectful_transition_count": consistency["effectful_transition_count"],
            "terminal_authority": False,
        }
    except (Exception, ReceiptResolutionError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
        }
