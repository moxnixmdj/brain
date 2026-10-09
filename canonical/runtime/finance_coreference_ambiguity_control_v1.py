"""Bounded finance coreference ambiguity control V1.

This module does not resolve general coreference.  It takes an exact, declared
mention universe for one source, recomputes the source-grounded candidate graph,
and projects the candidate antecedents for one reference into the Brain-owned
finite semantic ambiguity controller.

The output is a control result:
- continue without disambiguation when all candidate antecedents imply the same
  complete terminal signature;
- acquire the minimum declared discriminator when terminally distinct candidates
  are separable;
- ask for clarification or stronger authentic information when they are not.

No antecedent identity, semantic truth, policy adequacy, execution, promotion, or
terminal authority is minted here.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import semantic_ambiguity_control_v1 as ambiguity
from canonical.runtime import source_grounded_coreference as coref

SCHEMA = "PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_CONTROL_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_RESULT_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _mention(raw: Mapping[str, Any], source_text: str) -> coref.Mention:
    if not isinstance(raw, Mapping):
        raise ValueError("MENTION_NOT_OBJECT")
    mid = str(raw.get("mention_id") or "").strip()
    text = str(raw.get("text") or "")
    start = raw.get("start")
    end = raw.get("end")
    sent = raw.get("sentence_index")
    if (
        not mid
        or not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or not isinstance(sent, int)
        or isinstance(sent, bool)
        or start < 0
        or end <= start
        or end > len(source_text)
        or source_text[start:end] != text
    ):
        raise ValueError("MENTION_SOURCE_BINDING_INVALID:" + mid)
    entity_class = str(raw.get("entity_class") or "UNKNOWN").upper()
    number = str(raw.get("number") or "UNKNOWN").upper()
    if entity_class not in {"PERSON", "NONPERSON", "UNKNOWN"}:
        raise ValueError("MENTION_ENTITY_CLASS_INVALID:" + mid)
    if number not in {"SINGULAR", "PLURAL", "UNKNOWN"}:
        raise ValueError("MENTION_NUMBER_INVALID:" + mid)
    is_reference = raw.get("is_reference")
    if not isinstance(is_reference, bool):
        raise ValueError("MENTION_REFERENCE_FLAG_INVALID:" + mid)
    return coref.Mention(
        mention_id=mid,
        text=text,
        start=start,
        end=end,
        sentence_index=sent,
        entity_class=entity_class,
        number=number,
        is_reference=is_reference,
    )


def _compile(case: Mapping[str, Any]) -> tuple[dict[str, Any], list[str], list[dict[str, Any]]]:
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if case.get("domain") != "FINANCE":
        raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")
    source_id = str(case.get("source_id") or "").strip()
    source_text = case.get("source_text")
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text:
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if case.get("mention_universe_complete") is not True:
        raise ValueError("MENTION_UNIVERSE_COMPLETENESS_REQUIRED")
    raw_mentions = case.get("mentions")
    if not isinstance(raw_mentions, Sequence) or isinstance(raw_mentions, (str, bytes)):
        raise ValueError("MENTIONS_REQUIRED")
    mentions = [_mention(x, source_text) for x in raw_mentions]
    graph = coref.compile_coreference_candidates(mentions)
    if graph.get("status") != "COMPILED":
        raise ValueError("COREFERENCE_GRAPH_NOT_COMPILED:" + str(graph.get("status")))

    reference_id = str(case.get("reference_id") or "").strip()
    if not reference_id:
        raise ValueError("REFERENCE_ID_REQUIRED")
    reference_rows = [m for m in mentions if m.mention_id == reference_id]
    if len(reference_rows) != 1 or reference_rows[0].is_reference is not True:
        raise ValueError("REFERENCE_ID_NOT_EXACT_REFERENCE_MENTION")

    unresolved_target = [
        row for row in (graph.get("unresolved_references") or [])
        if isinstance(row, Mapping) and row.get("reference_id") == reference_id
    ]
    if unresolved_target:
        raise ValueError("TARGET_REFERENCE_HAS_NO_BOUNDED_CANDIDATE_SET")

    candidate_ids = sorted({
        str(row.get("antecedent_id") or "")
        for row in (graph.get("candidate_edges") or [])
        if isinstance(row, Mapping) and row.get("reference_id") == reference_id
    })
    if not candidate_ids or any(not x for x in candidate_ids):
        raise ValueError("TARGET_REFERENCE_CANDIDATES_REQUIRED")

    terminal_rows = case.get("antecedent_terminal_signatures")
    if not isinstance(terminal_rows, Mapping) or set(terminal_rows) != set(candidate_ids):
        raise ValueError("TERMINAL_SIGNATURE_CANDIDATE_COVERAGE_INCOMPLETE")

    worlds = []
    for antecedent_id in candidate_ids:
        row = terminal_rows[antecedent_id]
        if (
            not isinstance(row, Mapping)
            or row.get("terminal_signature_complete") is not True
            or not isinstance(row.get("terminal_signature"), Mapping)
        ):
            raise ValueError("TERMINAL_SIGNATURE_INVALID:" + antecedent_id)
        worlds.append({
            "world_id": "antecedent:" + antecedent_id,
            "terminal_signature_complete": True,
            "terminal_signature": dict(row["terminal_signature"]),
        })

    raw_observations = case.get("observations", [])
    if not isinstance(raw_observations, Sequence) or isinstance(raw_observations, (str, bytes)):
        raise ValueError("OBSERVATIONS_INVALID")
    observations = []
    seen = set()
    for i, raw in enumerate(raw_observations):
        if not isinstance(raw, Mapping):
            raise ValueError("OBSERVATION_NOT_OBJECT:" + str(i))
        oid = str(raw.get("observation_id") or "").strip()
        outcomes = raw.get("outcomes")
        cost = raw.get("cost_units")
        if not oid or oid in seen:
            raise ValueError("OBSERVATION_ID_INVALID:" + str(i))
        seen.add(oid)
        if raw.get("outcome_map_complete") is not True:
            raise ValueError("OBSERVATION_OUTCOME_COMPLETENESS_REQUIRED:" + oid)
        if not isinstance(outcomes, Mapping) or set(outcomes) != set(candidate_ids):
            raise ValueError("OBSERVATION_CANDIDATE_COVERAGE_INCOMPLETE:" + oid)
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
            raise ValueError("OBSERVATION_COST_INVALID:" + oid)
        observations.append({
            "observation_id": oid,
            "cost_units": cost,
            "outcome_map_complete": True,
            "outcomes": {
                "antecedent:" + antecedent_id: outcomes[antecedent_id]
                for antecedent_id in candidate_ids
            },
        })

    return graph, candidate_ids, observations


def compute(case: Mapping[str, Any]) -> dict[str, Any]:
    graph, candidate_ids, observations = _compile(case)
    source_text = str(case["source_text"])
    reference_id = str(case["reference_id"])
    worlds = []
    terminals = case["antecedent_terminal_signatures"]
    for antecedent_id in candidate_ids:
        row = terminals[antecedent_id]
        worlds.append({
            "world_id": "antecedent:" + antecedent_id,
            "terminal_signature_complete": True,
            "terminal_signature": dict(row["terminal_signature"]),
        })

    control = ambiguity.decide({
        "ambiguity_owner": str(case.get("ambiguity_owner") or "").strip().upper(),
        "hypothesis_set_complete": True,
        "worlds": worlds,
        "observations": observations,
    })
    if not isinstance(control, Mapping):
        raise ValueError("AMBIGUITY_CONTROL_RESULT_INVALID")

    result_core = {
        "domain": "FINANCE",
        "source_id": str(case["source_id"]).strip(),
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "reference_id": reference_id,
        "candidate_antecedent_ids": candidate_ids,
        "candidate_count": len(candidate_ids),
        "candidate_graph_sha256": _sha(graph),
        "decision": dict(control),
    }
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__BOUNDED_FINANCE_COREFERENCE_AMBIGUITY_CONTROL_COMPUTED",
        "pass": True,
        **result_core,
        "result_sha256": _sha(result_core),
        "ambiguity_preserved": control.get("action") != "CONTINUE_WITHOUT_DISAMBIGUATION",
        "antecedent_identity_asserted": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "terminal_authority": False,
    }
