#!/usr/bin/env python3
"""Goal-directed sufficiency gate: read, ask one gap, admit one rule, or refuse.

This module is deliberately not a new learner. It composes mechanisms that already
exist in this repository:

* ``learn_or_read_v1`` -- reading first; no policy where the instruction suffices;
* ``applicability_v1`` -- a proof that repetition cannot repair the observables;
* ``active_question_v1`` / ``settlement_v1`` -- EIG only over a closed, reachable
  version space;
* ``contrast_selection_v1`` -- one reachable contrast that actually splits
  surviving requirements;
* ``perfect_algorithm_v1.generalize/admit`` -- one experience becomes an external
  abstraction only after fresh instances reach the goal.

World facts and evidence stay outside weights. The model/runtime uses no other
model, no network, and no learned parameter. The ordering itself is architecture
bias; zero parameter writes is not zero bias. A stored row is a falsifiable
abstraction, never an exact trace, path, argv, content, answer, reward or caller
authority claim.

Authority: NONE__PRODUCER_RUN_SANDBOX. This is not a frontier benchmark score,
own-weights qualification, independent cloud attestation, GUI/DOM oracle, or §6.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.runtime import active_question_v1 as aq
from canonical.runtime import applicability_v1 as app
from canonical.runtime import contrast_selection_v1 as cs
from canonical.runtime import learn_or_read_v1 as lor
from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.runtime import settlement_v1 as sv

SCHEMA = "BRAIN_GOAL_DIRECTED_SUFFICIENCY_GATE_V1"
STORE_SCHEMA = "BRAIN_GOAL_DIRECTED_SUFFICIENCY_STORE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "canonical" / "astra_runtime" / "state" / "GOAL_DIRECTED_SUFFICIENCY_GATE_V1.json"

READ_ONLY = "READ_ONLY__NO_STORE_WRITE"
ASK_SETTLED = "ASK__SETTLED_NAMED_GAP"
SAVE_ADMITTED = "SAVE__ABSTRACTION_ADMITTED"
DENY_AUTHORITY = "REFUSED__CALLER_AUTHORITY_DENIED"
DENY_RAW = "REFUSED__RAW_EXPERIENCE_IS_NOT_A_RULE"
DENY_CANDIDATE = "REFUSED__STORE_CANDIDATE_NOT_ADMITTED"
DENY_INSUFFICIENT = "REFUSED__OBSERVABLE_VOCABULARY_INSUFFICIENT"
DENY_DYNAMIC = "REFUSED__DYNAMIC_UPDATE_REQUIRES_FRESH_OBSERVATION"
DENY_NO_SPACE = "REFUSED__NO_CLOSED_HYPOTHESIS_SPACE"
DENY_OPEN = "REFUSED__OPEN_HYPOTHESIS_SPACE"
DENY_OUTSIDE = "REFUSED__EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE"
DENY_BLIND = "REFUSED__INSTRUMENT_BLIND"
DENY_QUESTION = "REFUSED__QUESTION_NOT_SETTLED"
DENY_CONTRAST = "REFUSED__NO_DECISIVE_CONTRAST"
DENY_ADMISSION = "REFUSED__ADMISSION_NOT_REACHED_ON_FRESH_INSTANCES"

AUTHORITY_KEYS = frozenset({
    "force_learn", "store_now", "trust_retrieved", "independent_verified",
    "execution_authorized", "benchmark_score_claimed", "truth_achieved",
})
FORBIDDEN_TOKENS = (
    "path", "argv", "content", "trace", "answer", "reward", "outcome",
    "exact_action", "source_bytes", "raw", "gold",
)


def canonical_bytes(value: Any) -> bytes:
    """Deterministic JSON bytes for a hash. ``default=str`` never invents facts."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def forbidden_fields(value: Any, prefix: str = "") -> list[str]:
    """Recursively name raw-record fields that must never enter an admitted store."""
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            lowered = label.lower()
            if any(token in lowered for token in FORBIDDEN_TOKENS):
                found.append(label)
            found.extend(forbidden_fields(child, label))
    elif isinstance(value, str):
        lowered = value.lower()
        if any(token in lowered for token in FORBIDDEN_TOKENS):
            found.append(prefix or "<string>")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for i, child in enumerate(value):
            found.extend(forbidden_fields(child, f"{prefix}[{i}]"))
    return sorted(set(found))


def caller_authority(case: Mapping[str, Any]) -> list[str]:
    claims: list[str] = []
    for key in AUTHORITY_KEYS:
        if bool(case.get(key)):
            claims.append(str(key))
    nested = case.get("caller_flags")
    if isinstance(nested, Mapping):
        for key in AUTHORITY_KEYS:
            if bool(nested.get(key)):
                claims.append(f"caller_flags.{key}")
    return sorted(set(claims))


def _facts(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        return tuple(sorted(str(k) for k, v in value.items() if bool(v)))
    return tuple(sorted(str(x) for x in (value or ())))


def _evidence(case: Mapping[str, Any]) -> list[tuple[tuple[str, ...], bool]]:
    return [
        (_facts(row.get("facts")), bool(row.get("outcome")))
        for row in (case.get("evidence") or [])
        if isinstance(row, Mapping)
    ]


def _versions(case: Mapping[str, Any]) -> list[int]:
    return [int(row.get("version", 0)) for row in (case.get("evidence") or [])
            if isinstance(row, Mapping)]


def _probes(case: Mapping[str, Any]) -> list[tuple[str, ...]]:
    return [tuple(str(x) for x in row) for row in (case.get("probes") or [])]


def _goal_probes(case: Mapping[str, Any]) -> list[tuple[str, ...]]:
    return [tuple(str(x) for x in row) for row in (case.get("goal_probes") or [])]


def _base(case: Mapping[str, Any], decision: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "case_id": str(case.get("case_id") or "?"),
        "decision": decision,
        "reason": reason,
        "store_write": False,
        "probes_executed": 0,
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
        "parameters_written": 0,
        "written_to_weights": False,
    }


def store_payload(rules: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The exact external-store payload whose digest is checked after restart."""
    return {"schema": STORE_SCHEMA, "authority": AUTHORITY, "rules": [dict(r) for r in rules]}


def store_status(path: str | Path = STORE_PATH) -> dict[str, Any]:
    """Read, reject missing/invalid/editable stores, and recompute the digest."""
    p = Path(path)
    if not p.is_file():
        return {"schema": STORE_SCHEMA, "status": "STORE_MISSING__REFUSE", "digest": None,
                "rule_count": 0}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": STORE_SCHEMA, "status": "STORE_INVALID__REFUSE", "digest": None,
                "rule_count": 0}
    if not isinstance(data, Mapping) or data.get("schema") != STORE_SCHEMA:
        return {"schema": STORE_SCHEMA, "status": "STORE_INVALID__REFUSE", "digest": None,
                "rule_count": 0}
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules or forbidden_fields(rules):
        return {"schema": STORE_SCHEMA, "status": "STORE_INVALID__REFUSE", "digest": None,
                "rule_count": 0}
    computed = digest(store_payload(rules))
    declared = str(data.get("digest") or "")
    if declared != computed:
        return {"schema": STORE_SCHEMA, "status": "STORE_DIGEST_MISMATCH__REFUSE",
                "digest": computed, "declared_digest": declared, "rule_count": len(rules)}
    return {"schema": STORE_SCHEMA, "status": "PASS__STORE_VERIFIED", "digest": computed,
            "declared_digest": declared, "rule_count": len(rules)}


def write_rule(rule: Mapping[str, Any], path: str | Path = STORE_PATH) -> dict[str, Any]:
    """Persist one admitted abstraction; refuse any raw-experience field."""
    bad = forbidden_fields(rule)
    if bad:
        return {"schema": STORE_SCHEMA, "status": DENY_RAW, "forbidden_fields": bad,
                "store_write": False}
    clean = dict(rule)
    rules: list[dict[str, Any]] = []
    p = Path(path)
    if p.is_file():
        prior = store_status(p)
        if prior["status"] == "PASS__STORE_VERIFIED":
            try:
                old = json.loads(p.read_text(encoding="utf-8")).get("rules") or []
                rules = [dict(r) for r in old if isinstance(r, Mapping)
                         and r.get("rule_id") != clean.get("rule_id")]
            except Exception:
                rules = []
    rules.append(clean)
    payload = store_payload(rules)
    payload["digest"] = digest(payload)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = store_status(p)
    return {"schema": STORE_SCHEMA, "status": status["status"], "store_write": True,
            "digest": status["digest"], "rule_count": status["rule_count"],
            "rule": clean, "path_is_external_json": True}


class _AdmissionWorld:
    """A tiny fresh-instance oracle; it holds no path, content, or reward."""

    def __init__(self, row: Mapping[str, Any]) -> None:
        self.instance_id = str(row.get("instance_id") or "?")
        self.expected_plan = tuple(str(x) for x in (row.get("expected_plan") or ()))
        self.actions: list[str] = []

    def reset(self) -> None:
        self.actions = []

    def act(self, action: Any) -> None:
        self.actions.append(str(action))

    def state(self) -> dict[str, Any]:
        return {"instance_id": self.instance_id, "actions": tuple(self.actions),
                "expected_plan": self.expected_plan}


def _goal_predicate(state: Mapping[str, Any]) -> bool:
    return tuple(state.get("actions") or ()) == tuple(state.get("expected_plan") or ())


def _admit_abstraction(case: Mapping[str, Any], contrast: cs.Contrast) -> dict[str, Any]:
    """Use the existing generalize/admit path; return only an abstract rule."""
    plan = [str(x) for x in (case.get("plan_sketch") or ())]
    trace = [dict(row) for row in (case.get("experience_trace") or ())]
    fresh = [dict(row) for row in (case.get("fresh_instances") or ())]
    raw = forbidden_fields({"abstract_evidence": trace, "fresh_instances": fresh,
                            "plan_sketch": plan})
    if raw:
        return {"status": DENY_RAW, "raw_fields": raw, "rule": None, "admission": None}
    if not plan or not trace or not fresh:
        return {"status": DENY_ADMISSION,
                "reason": "NO_PLAN_OR_EXPERIENCE_OR_FRESH_INSTANCE", "rule": None,
                "admission": None}
    generalized = pa.generalize(
        trace,
        str(case.get("goal_family") or "unknown_goal_family"),
        goal_family=str(case.get("goal_family") or "unknown_goal_family"),
        env_kind=str(case.get("env_kind") or "unknown_environment"),
        plan=plan,
        evidence={"contrast": contrast.as_row()},
    )
    gen = generalized.get("generalization")
    if not isinstance(gen, Mapping):
        return {"status": DENY_ADMISSION, "reason": generalized.get("status"),
                "rule": None, "admission": None}
    worlds = [_AdmissionWorld(row) for row in fresh]
    admission = pa.admit(
        gen, worlds, _goal_predicate,
        reset=lambda world: world.reset(),
        act=lambda world, action: world.act(action),
        state=lambda world: world.state(),
    )
    if admission.get("verdict") != "ADMIT" or int(admission.get("reached") or 0) != len(worlds):
        return {"status": DENY_ADMISSION, "reason": "FRESH_INSTANCES_DID_NOT_ALL_REACH_GOAL",
                "rule": None, "admission": admission}
    rule = {
        "schema": "BRAIN_GOAL_DIRECTED_ABSTRACT_RULE_V1",
        "authority": AUTHORITY,
        "rule_id": str(gen.get("rule_id") or digest([plan, trace, fresh])[:16]),
        "goal_family": str(gen.get("goal_family") or "unknown_goal_family"),
        "env_kind": str(gen.get("env_kind") or "unknown_environment"),
        "scope": dict(gen.get("scope") or {}),
        "relation_signature": sorted(str(x) for x in contrast.discriminating_facts),
        "artifact_span": sorted(str(x) for x in (case.get("artifact_span") or ())),
        "mechanism_signature": digest(sorted({str(x).split("_", 1)[0] for x in plan})),
        "mechanism_role_count": len({str(x).split("_", 1)[0] for x in plan}),
        "plan_length": int(gen.get("plan_length") or len(plan)),
        "evidence_digest": str((gen.get("evidence") or {}).get("trace_sha256") or ""),
        "admission_counts": {
            "fresh_instances": len(worlds),
            "fresh_instances_reached": int(admission.get("reached") or 0),
            "contrast_guaranteed_elimination": int(contrast.guaranteed_elimination()),
        },
    }
    bad = forbidden_fields(rule)
    if bad:
        return {"status": DENY_RAW, "raw_fields": bad, "rule": None, "admission": admission}
    return {"status": SAVE_ADMITTED, "reason": "CONTRAST_AND_FRESH_INSTANCES_ADMITTED",
            "rule": rule, "admission": admission}


def assess(
    case: Mapping[str, Any],
    *,
    oracle: Callable[[tuple[str, ...]], str] | None = None,
    store_path: str | Path = STORE_PATH,
    write_store: bool = False,
) -> dict[str, Any]:
    """Decide the next knowledge action, or refuse with a named reason."""
    claims = caller_authority(case)
    if claims:
        row = _base(case, DENY_AUTHORITY, "CALLER_CANNOT_GRANT_LEARNING_OR_VERIFICATION_AUTHORITY")
        row["caller_authority_claims"] = claims
        return row

    reading = lor.decide(str(case.get("instruction") or ""), case.get("observation") or {})
    if reading.learning_forbidden:
        row = _base(case, READ_ONLY, "THE_LIVE_READING_DETERMINES_THE_ACTION")
        row["reading"] = reading.as_dict()
        return row

    candidate_payload = case.get("candidate_store_payload")
    if candidate_payload is not None:
        bad = forbidden_fields(candidate_payload)
        if bad:
            row = _base(case, DENY_RAW, "A_RAW_RECORDING_IS_NOT_A_GENERALIZATION")
            row["forbidden_fields"] = bad
            return row
        if not bool(case.get("candidate_store_payload_admitted")):
            row = _base(case, DENY_CANDIDATE, "CANDIDATE_STORE_ROW_HAS_NO_FRESH_INSTANCE_ADMISSION")
            return row

    evidence = _evidence(case)
    witness = app.insufficiency_witness(evidence) if evidence else None
    if witness:
        row = _base(case, DENY_INSUFFICIENT, "MORE_RUNS_CANNOT_REPAIR_THE_OBSERVABLE_VOCABULARY")
        row["witness"] = witness
        row["reading"] = reading.as_dict()
        return row

    versions = _versions(case)
    current_version = int(case.get("current_version") or 0)
    max_version = max(versions or [0])
    if current_version > max_version:
        row = _base(case, DENY_DYNAMIC, "THE_ENVIRONMENT_CHANGED_AFTER_ALL_STORED_EVIDENCE")
        row["current_version"] = current_version
        row["max_evidence_version"] = max_version
        row["reading"] = reading.as_dict()
        return row

    goal_facts = set(_facts(case.get("goal_facts")))
    scan_facts = set(_facts(case.get("scan_facts")))
    missing = sorted(goal_facts - scan_facts)
    if missing:
        rows = [dict(r) for r in (case.get("regime_rows") or []) if isinstance(r, Mapping)]
        probes = _probes(case)
        goal_probes = _goal_probes(case)
        if not rows or not probes or oracle is None:
            row = _base(case, DENY_NO_SPACE, "NO_CLOSED_REACHABLE_QUESTION_SPACE")
            row["missing_goal_facts"] = missing
            row["reading"] = reading.as_dict()
            return row
        space = aq.build_space(rows)
        if not aq.closed(space):
            row = _base(case, DENY_OPEN, "EIG_REFUSED_OVER_AN_OPEN_PROPOSAL_SPACE")
            row["hypothesis_count"] = len(space.hypotheses)
            row["closed_space_cap"] = aq.MAX_CLOSED_SPACE
            row["missing_goal_facts"] = missing
            row["reading"] = reading.as_dict()
            return row
        question = aq.ask(space, probes, oracle=oracle,
                          domain=probes + goal_probes, budget=4, confidence=0.99)
        row = _base(case, DENY_QUESTION, "THE_QUESTION_SPACE_DID_NOT_SETTLE")
        row["missing_goal_facts"] = missing
        row["question"] = question
        row["probes_executed"] = len(question.get("asked") or [])
        row["reading"] = reading.as_dict()
        settlement_status = str((question.get("settlement") or {}).get("status") or "")
        if settlement_status == sv.EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE:
            row["decision"] = DENY_OUTSIDE
            row["reason"] = "NO_HYPOTHESIS_EXPLAINS_THE_ENVIRONMENT_ANSWER"
            return row
        if question.get("policy") == "REFUSED__INSTRUMENT_BLIND" or settlement_status == "REFUSED__INSTRUMENT_BLIND":
            row["decision"] = DENY_BLIND
            row["reason"] = "NO_REACHABLE_PROBE_SPLITS_THE_SURVIVING_REGIMES"
            return row
        if settlement_status != sv.SETTLED or not question.get("winner"):
            return row
        prediction = aq.predict(space, goal_probes[0] if goal_probes else probes[0])
        if prediction.startswith("REFUSED") or prediction == "UNKNOWN":
            row["reason"] = "THE_SETTLED_WINNER_DOES_NOT_ANSWER_THE_GOAL_PROBE"
            return row
        row["decision"] = ASK_SETTLED
        row["reason"] = "ONE_NAMED_GAP_WAS_SETTLED_BY_A_CLOSED_EIG_QUESTION"
        row["prediction"] = prediction
        return row

    reachable = [_facts(row) for row in (case.get("candidate_states") or [])]
    reachable.extend(facts for facts, _ in evidence)
    contrast = cs.select_contrast(evidence, reachable)
    row = _base(case, DENY_CONTRAST, "NO_REACHABLE_CONTRAST_SPLITS_THE_SURVIVORS")
    row["contrast"] = contrast.as_row()
    row["reading"] = reading.as_dict()
    if not contrast.informative or contrast.guaranteed_elimination() <= 0:
        return row
    admitted = _admit_abstraction(case, contrast)
    row["admission"] = admitted.get("admission")
    if admitted["status"] != SAVE_ADMITTED or not isinstance(admitted.get("rule"), Mapping):
        row["decision"] = admitted["status"]
        row["reason"] = str(admitted.get("reason") or admitted["status"])
        row["raw_fields"] = admitted.get("raw_fields") or []
        return row
    row["decision"] = SAVE_ADMITTED
    row["reason"] = admitted["reason"]
    row["rule"] = admitted["rule"]
    if write_store:
        stored = write_rule(admitted["rule"], store_path)
        row["store"] = stored
        row["store_write"] = bool(stored.get("store_write"))
        if not row["store_write"] or stored.get("status") != "PASS__STORE_VERIFIED":
            row["decision"] = "REFUSED__STORE_WRITE_FAILED"
            row["reason"] = str(stored.get("status"))
    return row
