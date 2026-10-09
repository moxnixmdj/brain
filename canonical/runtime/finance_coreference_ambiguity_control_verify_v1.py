"""Independent verifier for bounded finance coreference ambiguity control V1.

The verifier does not import the producer.  It independently reconstructs the
bounded candidate set from source spans, rebuilds the finite semantic worlds, and
re-runs the Brain-owned ambiguity controller before comparing the exact result.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import semantic_ambiguity_control_v1 as ambiguity
from canonical.runtime import source_grounded_coreference as coref

INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_RESULT_V1"
SCHEMA = "PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_VERIFY_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _recompute(case: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if case.get("domain") != "FINANCE" or case.get("mention_universe_complete") is not True:
        raise ValueError("CASE_SCOPE_INVALID")
    source_text = case.get("source_text")
    source_id = str(case.get("source_id") or "").strip()
    if not isinstance(source_text, str) or not source_text or not source_id:
        raise ValueError("SOURCE_BINDING_INVALID")
    raw_mentions = case.get("mentions")
    if not isinstance(raw_mentions, Sequence) or isinstance(raw_mentions, (str, bytes)):
        raise ValueError("MENTIONS_INVALID")
    mentions = []
    for raw in raw_mentions:
        if not isinstance(raw, Mapping):
            raise ValueError("MENTION_NOT_OBJECT")
        start, end = raw.get("start"), raw.get("end")
        text = raw.get("text")
        mid = str(raw.get("mention_id") or "").strip()
        sent = raw.get("sentence_index")
        if (
            not mid
            or not isinstance(start, int) or isinstance(start, bool)
            or not isinstance(end, int) or isinstance(end, bool)
            or not isinstance(sent, int) or isinstance(sent, bool)
            or start < 0 or end <= start or end > len(source_text)
            or source_text[start:end] != text
        ):
            raise ValueError("MENTION_SOURCE_BINDING_INVALID")
        entity_class = str(raw.get("entity_class") or "UNKNOWN").upper()
        number = str(raw.get("number") or "UNKNOWN").upper()
        is_reference = raw.get("is_reference")
        if entity_class not in {"PERSON","NONPERSON","UNKNOWN"} or number not in {"SINGULAR","PLURAL","UNKNOWN"} or not isinstance(is_reference, bool):
            raise ValueError("MENTION_FEATURE_INVALID")
        mentions.append(coref.Mention(mid, str(text), start, end, sent, entity_class, number, is_reference))

    graph = coref.compile_coreference_candidates(mentions)
    if graph.get("status") != "COMPILED":
        raise ValueError("GRAPH_NOT_COMPILED")
    ref = str(case.get("reference_id") or "").strip()
    if len([m for m in mentions if m.mention_id == ref and m.is_reference]) != 1:
        raise ValueError("REFERENCE_INVALID")
    if any(
        isinstance(row, Mapping) and row.get("reference_id") == ref
        for row in (graph.get("unresolved_references") or [])
    ):
        raise ValueError("TARGET_REFERENCE_UNRESOLVED")
    cands = sorted({
        str(row.get("antecedent_id") or "")
        for row in (graph.get("candidate_edges") or [])
        if isinstance(row, Mapping) and row.get("reference_id") == ref
    })
    if not cands or any(not x for x in cands):
        raise ValueError("CANDIDATES_REQUIRED")

    terminals = case.get("antecedent_terminal_signatures")
    if not isinstance(terminals, Mapping) or set(terminals) != set(cands):
        raise ValueError("TERMINAL_COVERAGE_INVALID")
    worlds = []
    for cid in cands:
        row = terminals[cid]
        if not isinstance(row, Mapping) or row.get("terminal_signature_complete") is not True or not isinstance(row.get("terminal_signature"), Mapping):
            raise ValueError("TERMINAL_SIGNATURE_INVALID")
        worlds.append({
            "world_id": "antecedent:" + cid,
            "terminal_signature_complete": True,
            "terminal_signature": dict(row["terminal_signature"]),
        })

    raw_obs = case.get("observations", [])
    if not isinstance(raw_obs, Sequence) or isinstance(raw_obs, (str, bytes)):
        raise ValueError("OBSERVATIONS_INVALID")
    observations = []
    seen = set()
    for raw in raw_obs:
        if not isinstance(raw, Mapping):
            raise ValueError("OBSERVATION_INVALID")
        oid = str(raw.get("observation_id") or "").strip()
        outcomes = raw.get("outcomes")
        cost = raw.get("cost_units")
        if not oid or oid in seen or raw.get("outcome_map_complete") is not True:
            raise ValueError("OBSERVATION_ID_OR_COMPLETENESS_INVALID")
        seen.add(oid)
        if not isinstance(outcomes, Mapping) or set(outcomes) != set(cands):
            raise ValueError("OBSERVATION_COVERAGE_INVALID")
        if not isinstance(cost, (int,float)) or isinstance(cost, bool) or cost < 0:
            raise ValueError("OBSERVATION_COST_INVALID")
        observations.append({
            "observation_id": oid,
            "cost_units": cost,
            "outcome_map_complete": True,
            "outcomes": {"antecedent:" + cid: outcomes[cid] for cid in cands},
        })

    control = ambiguity.decide({
        "ambiguity_owner": str(case.get("ambiguity_owner") or "").strip().upper(),
        "hypothesis_set_complete": True,
        "worlds": worlds,
        "observations": observations,
    })
    core = {
        "domain": "FINANCE",
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "reference_id": ref,
        "candidate_antecedent_ids": cands,
        "candidate_count": len(cands),
        "candidate_graph_sha256": _sha(graph),
        "decision": dict(control),
    }
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__BOUNDED_FINANCE_COREFERENCE_AMBIGUITY_CONTROL_COMPUTED",
        "pass": True,
        **core,
        "result_sha256": _sha(core),
        "ambiguity_preserved": control.get("action") != "CONTINUE_WITHOUT_DISAMBIGUATION",
        "antecedent_identity_asserted": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
    }


def verify(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    try:
        expected = _recompute(case)
        if not isinstance(result, Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        if dict(result) != expected:
            raise ValueError("RESULT_RECOMPUTATION_MISMATCH")
        return {
            "schema": SCHEMA,
            "status": "PASS__PRODUCER_INDEPENDENT_COREFERENCE_AMBIGUITY_RECOMPUTATION",
            "pass": True,
            "verified": True,
            "producer_independent": True,
            "result_sha256": expected["result_sha256"],
            "antecedent_identity_asserted": False,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "verified": False,
            "producer_independent": True,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
