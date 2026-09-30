#!/usr/bin/env python3
"""Deterministic typed evidence-to-decision synthesis for Project Brain.

This module intentionally does not interpret arbitrary natural language. It
operates only on a typed decision problem: alternatives, hard constraints, and
support/contradiction evidence with provenance and independence groups.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

SCHEMA = "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_TYPED_DECISION_RESULT_V1"
RELATIONS = {"SUPPORTS", "CONTRADICTS"}
CONSTRAINT_STATES = {"SATISFIED", "VIOLATED", "UNKNOWN"}
TERMINAL = {"DECIDED", "CONFLICTED", "INSUFFICIENT", "NO_ADMISSIBLE_ALTERNATIVE"}


class DecisionSynthesisError(RuntimeError):
    pass


def _safe_path(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p == root or root not in p.parents:
        raise DecisionSynthesisError("PATH_OUTSIDE_REPOSITORY")
    return p


def _finite01(value, field):
    try:
        x = float(value)
    except Exception as exc:
        raise DecisionSynthesisError("INVALID_NUMBER:" + field) from exc
    if not math.isfinite(x) or x < 0.0 or x > 1.0:
        raise DecisionSynthesisError("NUMBER_OUT_OF_RANGE:" + field)
    return x


def _finite_nonnegative(value, field):
    try:
        x = float(value)
    except Exception as exc:
        raise DecisionSynthesisError("INVALID_NUMBER:" + field) from exc
    if not math.isfinite(x) or x < 0.0:
        raise DecisionSynthesisError("NEGATIVE_OR_NONFINITE:" + field)
    return x


def _nonempty_string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise DecisionSynthesisError("NONEMPTY_STRING_REQUIRED:" + field)
    return value.strip()


def _provenance(value, field):
    if not isinstance(value, list) or not value:
        raise DecisionSynthesisError("PROVENANCE_REQUIRED:" + field)
    out = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise DecisionSynthesisError(f"PROVENANCE_RECORD_INVALID:{field}:{index}")
        source = _nonempty_string(item.get("source"), f"{field}.{index}.source")
        ref = _nonempty_string(item.get("ref"), f"{field}.{index}.ref")
        out.append({"source": source, "ref": ref})
    return out


def _normalize(problem):
    if not isinstance(problem, dict) or problem.get("schema") != SCHEMA:
        raise DecisionSynthesisError("DECISION_SCHEMA_INVALID")
    decision_id = _nonempty_string(problem.get("decision_id"), "decision_id")
    question = _nonempty_string(problem.get("question"), "question")

    raw_alts = problem.get("alternatives")
    if not isinstance(raw_alts, list) or len(raw_alts) < 1 or len(raw_alts) > 64:
        raise DecisionSynthesisError("ALTERNATIVES_INVALID")
    alternatives = []
    seen = set()
    for index, raw in enumerate(raw_alts):
        if not isinstance(raw, dict):
            raise DecisionSynthesisError(f"ALTERNATIVE_INVALID:{index}")
        aid = _nonempty_string(raw.get("id"), f"alternatives.{index}.id")
        if aid in seen:
            raise DecisionSynthesisError("ALTERNATIVE_DUPLICATE:" + aid)
        seen.add(aid)
        alternatives.append({
            "id": aid,
            "label": _nonempty_string(raw.get("label") or aid, f"alternatives.{index}.label"),
        })

    constraints = []
    seen_constraints = set()
    for index, raw in enumerate(problem.get("constraints") or []):
        if not isinstance(raw, dict):
            raise DecisionSynthesisError(f"CONSTRAINT_INVALID:{index}")
        cid = _nonempty_string(raw.get("id"), f"constraints.{index}.id")
        if cid in seen_constraints:
            raise DecisionSynthesisError("CONSTRAINT_DUPLICATE:" + cid)
        seen_constraints.add(cid)
        alternative = _nonempty_string(raw.get("alternative"), f"constraints.{index}.alternative")
        if alternative not in seen:
            raise DecisionSynthesisError("CONSTRAINT_ALTERNATIVE_UNKNOWN:" + alternative)
        state = str(raw.get("state") or "").upper()
        if state not in CONSTRAINT_STATES:
            raise DecisionSynthesisError("CONSTRAINT_STATE_INVALID:" + cid)
        required = raw.get("required", True)
        if not isinstance(required, bool):
            raise DecisionSynthesisError("CONSTRAINT_REQUIRED_NOT_BOOLEAN:" + cid)
        constraints.append({
            "id": cid,
            "alternative": alternative,
            "state": state,
            "required": required,
            "description": _nonempty_string(raw.get("description"), f"constraints.{index}.description"),
            "provenance": _provenance(raw.get("provenance"), f"constraints.{index}.provenance"),
        })

    evidence = []
    seen_evidence = set()
    for index, raw in enumerate(problem.get("evidence") or []):
        if not isinstance(raw, dict):
            raise DecisionSynthesisError(f"EVIDENCE_INVALID:{index}")
        eid = _nonempty_string(raw.get("id"), f"evidence.{index}.id")
        if eid in seen_evidence:
            raise DecisionSynthesisError("EVIDENCE_DUPLICATE:" + eid)
        seen_evidence.add(eid)
        alternative = _nonempty_string(raw.get("alternative"), f"evidence.{index}.alternative")
        if alternative not in seen:
            raise DecisionSynthesisError("EVIDENCE_ALTERNATIVE_UNKNOWN:" + alternative)
        relation = str(raw.get("relation") or "").upper()
        if relation not in RELATIONS:
            raise DecisionSynthesisError("EVIDENCE_RELATION_INVALID:" + eid)
        evidence.append({
            "id": eid,
            "alternative": alternative,
            "relation": relation,
            "confidence": _finite01(raw.get("confidence"), f"evidence.{index}.confidence"),
            "strength": _finite01(raw.get("strength", 1.0), f"evidence.{index}.strength"),
            "independence_group": _nonempty_string(raw.get("independence_group"), f"evidence.{index}.independence_group"),
            "claim": _nonempty_string(raw.get("claim"), f"evidence.{index}.claim"),
            "provenance": _provenance(raw.get("provenance"), f"evidence.{index}.provenance"),
        })

    policy = problem.get("policy") or {}
    if not isinstance(policy, dict):
        raise DecisionSynthesisError("POLICY_INVALID")
    normalized_policy = {
        "minimum_support_ratio": _finite01(policy.get("minimum_support_ratio", 0.60), "policy.minimum_support_ratio"),
        "maximum_conflict_ratio": _finite01(policy.get("maximum_conflict_ratio", 0.50), "policy.maximum_conflict_ratio"),
        "minimum_independent_support_groups": int(policy.get("minimum_independent_support_groups", 1)),
        "minimum_net_margin": _finite_nonnegative(policy.get("minimum_net_margin", 0.10), "policy.minimum_net_margin"),
    }
    if normalized_policy["minimum_independent_support_groups"] < 1:
        raise DecisionSynthesisError("MINIMUM_SUPPORT_GROUPS_INVALID")

    return {
        "decision_id": decision_id,
        "question": question,
        "alternatives": alternatives,
        "constraints": constraints,
        "evidence": evidence,
        "policy": normalized_policy,
    }


def _input_hash(problem):
    canonical = json.dumps(problem, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def synthesize(problem):
    normalized = _normalize(problem)
    alternative_ids = [x["id"] for x in normalized["alternatives"]]
    policy = normalized["policy"]
    trace = [{
        "step": "NORMALIZE_TYPED_INPUT",
        "alternative_count": len(alternative_ids),
        "constraint_count": len(normalized["constraints"]),
        "evidence_count": len(normalized["evidence"]),
    }]

    by_alt = {}
    for aid in alternative_ids:
        required_constraints = [c for c in normalized["constraints"] if c["alternative"] == aid and c["required"]]
        violated = [c for c in required_constraints if c["state"] == "VIOLATED"]
        unknown = [c for c in required_constraints if c["state"] == "UNKNOWN"]
        if violated:
            constraint_state = "DISQUALIFIED"
        elif unknown:
            constraint_state = "UNRESOLVED"
        else:
            constraint_state = "ADMISSIBLE"

        group_support = {}
        group_contradict = {}
        contributing_ids = []
        for item in normalized["evidence"]:
            if item["alternative"] != aid:
                continue
            weight = item["confidence"] * item["strength"]
            target = group_support if item["relation"] == "SUPPORTS" else group_contradict
            group = item["independence_group"]
            if weight > target.get(group, 0.0):
                target[group] = weight
            contributing_ids.append(item["id"])

        support = sum(group_support.values())
        contradiction = sum(group_contradict.values())
        total = support + contradiction
        support_ratio = support / total if total > 0 else 0.0
        conflict_ratio = (2.0 * min(support, contradiction) / total) if total > 0 else 0.0
        net_score = support - contradiction
        support_groups = sum(1 for value in group_support.values() if value > 0)

        reasons = []
        if constraint_state == "DISQUALIFIED":
            reasons.append("REQUIRED_CONSTRAINT_VIOLATED")
        if constraint_state == "UNRESOLVED":
            reasons.append("REQUIRED_CONSTRAINT_UNKNOWN")
        if total <= 0:
            reasons.append("NO_EVIDENCE")
        if support_groups < policy["minimum_independent_support_groups"]:
            reasons.append("INSUFFICIENT_INDEPENDENT_SUPPORT_GROUPS")
        if support_ratio < policy["minimum_support_ratio"]:
            reasons.append("SUPPORT_RATIO_BELOW_MINIMUM")
        if conflict_ratio > policy["maximum_conflict_ratio"]:
            reasons.append("CONFLICT_RATIO_ABOVE_MAXIMUM")

        eligible = (
            constraint_state == "ADMISSIBLE"
            and total > 0
            and support_groups >= policy["minimum_independent_support_groups"]
            and support_ratio >= policy["minimum_support_ratio"]
            and conflict_ratio <= policy["maximum_conflict_ratio"]
        )
        by_alt[aid] = {
            "alternative": aid,
            "constraint_state": constraint_state,
            "violated_constraints": sorted(c["id"] for c in violated),
            "unknown_constraints": sorted(c["id"] for c in unknown),
            "support_score": support,
            "contradiction_score": contradiction,
            "net_score": net_score,
            "support_ratio": support_ratio,
            "conflict_ratio": conflict_ratio,
            "independent_support_groups": sorted(group_support),
            "independent_contradiction_groups": sorted(group_contradict),
            "contributing_evidence": sorted(set(contributing_ids)),
            "eligible": eligible,
            "reasons": reasons,
        }

    trace.append({
        "step": "APPLY_HARD_CONSTRAINTS",
        "states": {aid: by_alt[aid]["constraint_state"] for aid in alternative_ids},
    })
    trace.append({
        "step": "AGGREGATE_INDEPENDENT_EVIDENCE",
        "rule": "MAX_WEIGHT_PER_RELATION_PER_INDEPENDENCE_GROUP",
        "scores": {
            aid: {
                "support": by_alt[aid]["support_score"],
                "contradiction": by_alt[aid]["contradiction_score"],
                "net": by_alt[aid]["net_score"],
                "support_ratio": by_alt[aid]["support_ratio"],
                "conflict_ratio": by_alt[aid]["conflict_ratio"],
            }
            for aid in alternative_ids
        },
    })

    admissible = [x for x in by_alt.values() if x["constraint_state"] == "ADMISSIBLE"]
    unresolved = [x for x in by_alt.values() if x["constraint_state"] == "UNRESOLVED"]
    eligible = [x for x in by_alt.values() if x["eligible"]]
    eligible.sort(key=lambda x: (-x["net_score"], -x["support_ratio"], x["alternative"]))

    selected = None
    terminal_reason = None
    if not admissible:
        if unresolved:
            status = "INSUFFICIENT"
            terminal_reason = "NO_ADMISSIBLE_ALTERNATIVE_WITH_RESOLVED_REQUIRED_CONSTRAINTS"
        else:
            status = "NO_ADMISSIBLE_ALTERNATIVE"
            terminal_reason = "ALL_ALTERNATIVES_VIOLATE_REQUIRED_CONSTRAINTS"
    elif not eligible:
        if any(x["conflict_ratio"] > policy["maximum_conflict_ratio"] for x in admissible):
            status = "CONFLICTED"
            terminal_reason = "ADMISSIBLE_ALTERNATIVES_EXCEED_CONFLICT_LIMIT"
        else:
            status = "INSUFFICIENT"
            terminal_reason = "NO_ADMISSIBLE_ALTERNATIVE_MEETS_EVIDENCE_THRESHOLD"
    else:
        top = eligible[0]
        if len(eligible) > 1:
            runner_up = eligible[1]
            margin = top["net_score"] - runner_up["net_score"]
            if margin < policy["minimum_net_margin"]:
                status = "CONFLICTED"
                terminal_reason = "TOP_ALTERNATIVES_WITHIN_MINIMUM_NET_MARGIN"
            else:
                status = "DECIDED"
                selected = top["alternative"]
                terminal_reason = "TOP_ELIGIBLE_ALTERNATIVE_EXCEEDS_MARGIN"
        else:
            status = "DECIDED"
            selected = top["alternative"]
            terminal_reason = "ONLY_ELIGIBLE_ALTERNATIVE"

    if status not in TERMINAL:
        raise DecisionSynthesisError("INTERNAL_TERMINAL_STATUS_INVALID")

    rankings = sorted(
        by_alt.values(),
        key=lambda x: (
            0 if x["constraint_state"] == "ADMISSIBLE" else 1 if x["constraint_state"] == "UNRESOLVED" else 2,
            -x["net_score"],
            -x["support_ratio"],
            x["alternative"],
        ),
    )
    unresolved_items = []
    conflicts = []
    for item in rankings:
        if item["unknown_constraints"]:
            unresolved_items.append({
                "alternative": item["alternative"],
                "type": "UNKNOWN_REQUIRED_CONSTRAINT",
                "constraints": item["unknown_constraints"],
            })
        if item["conflict_ratio"] > 0:
            conflicts.append({
                "alternative": item["alternative"],
                "conflict_ratio": item["conflict_ratio"],
                "support_score": item["support_score"],
                "contradiction_score": item["contradiction_score"],
            })

    trace.append({
        "step": "APPLY_TERMINAL_POLICY",
        "eligible_alternatives": [x["alternative"] for x in eligible],
        "selected_alternative": selected,
        "status": status,
        "reason": terminal_reason,
    })

    decision_confidence = 0.0
    if selected is not None:
        x = by_alt[selected]
        decision_confidence = max(0.0, min(1.0, x["support_ratio"] * (1.0 - x["conflict_ratio"])))

    return {
        "schema": RESULT_SCHEMA,
        "decision_id": normalized["decision_id"],
        "question": normalized["question"],
        "input_sha256": _input_hash(problem),
        "status": status,
        "selected_alternative": selected,
        "decision_confidence": decision_confidence,
        "terminal_reason": terminal_reason,
        "policy": policy,
        "rankings": rankings,
        "unresolved": unresolved_items,
        "conflicts": conflicts,
        "trace": trace,
        "model_dependency_count": 0,
    }


def run(args, root):
    input_path = _safe_path(root, args.get("input_path"))
    output_path = _safe_path(root, args.get("output_path"))
    if not input_path.is_file():
        raise DecisionSynthesisError("DECISION_INPUT_MISSING")
    try:
        problem = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionSynthesisError("DECISION_INPUT_JSON_INVALID") from exc
    result = synthesize(problem)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw = output_path.read_bytes()
    return {
        "adapter": "evidence_decision_synthesis",
        "status": result["status"],
        "selected_alternative": result["selected_alternative"],
        "decision_confidence": result["decision_confidence"],
        "input_path": str(input_path.relative_to(pathlib.Path(root).resolve())).replace("\\", "/"),
        "output_path": str(output_path.relative_to(pathlib.Path(root).resolve())).replace("\\", "/"),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
        "model_dependency_count": 0,
    }
