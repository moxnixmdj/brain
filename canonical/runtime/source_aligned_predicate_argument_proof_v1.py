from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.bounded_predicate_argument_semantics import parse_clause

SCHEMA = "BRAIN_SOURCE_ALIGNED_PREDICATE_ARGUMENT_PROOF_V1"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _atom(parsed: Mapping[str, Any]) -> str:
    graph = parsed["semantic_graph"]
    condition = parsed.get("condition")
    payload = {
        "subject": graph["subject"],
        "predicate": graph["predicate"],
        "object": graph["object"],
        "modality": graph["modality"],
        "polarity": graph["polarity"],
        "voice": graph["voice"],
        "subject_span": list(graph["subject_span"]),
        "predicate_span": list(graph["predicate_span"]),
        "object_span": list(graph["object_span"]),
        "condition": (
            {
                "relation": condition["relation"],
                "text": condition["text"],
                "span": list(condition["span"]),
            }
            if isinstance(condition, Mapping)
            else None
        ),
    }
    return "PREDICATE_ARGUMENT::" + sha256(_canon(payload).encode("utf-8")).hexdigest()


def verify_predicate_argument(source_text: str, claim: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_TEXT_MISSING","terminal_authority":False}
    if not isinstance(claim, Mapping):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"CLAIM_NOT_OBJECT","terminal_authority":False}

    parsed = parse_clause(source_text)
    if parsed.get("status") != "RESOLVED":
        return {
            "schema":SCHEMA,
            "status":"UNRESOLVED",
            "reason":"PREDICATE_ARGUMENT_NOT_CERTIFIABLY_PARSED",
            "parse_status":parsed.get("status"),
            "parse_reason":parsed.get("reason"),
            "terminal_authority":False,
        }

    graph = parsed["semantic_graph"]
    expected = {
        "subject":str(graph["subject"]),
        "predicate":str(graph["predicate"]),
        "object":str(graph["object"]),
        "modality":str(graph["modality"]),
        "polarity":str(graph["polarity"]),
        "voice":str(graph["voice"]),
    }
    claimed = {k:str(claim.get(k) or "") for k in expected}
    mismatch = [k for k in expected if claimed[k] != expected[k]]

    condition = parsed.get("condition")
    claimed_condition = claim.get("condition")
    if condition is None:
        if claimed_condition not in (None, {}):
            mismatch.append("condition")
    else:
        if not isinstance(claimed_condition, Mapping):
            mismatch.append("condition")
        else:
            for k in ("relation","text"):
                if str(claimed_condition.get(k) or "") != str(condition[k]):
                    mismatch.append("condition."+k)

    if mismatch:
        return {
            "schema":SCHEMA,
            "status":"REJECTED",
            "reason":"PREDICATE_ARGUMENT_MISMATCH",
            "mismatch_fields":sorted(set(mismatch)),
            "expected":expected,
            "claimed":claimed,
            "terminal_authority":False,
        }

    out = {
        "schema":SCHEMA,
        "status":"PROOF_CHECKED",
        "proved_constraint":{"op":"ATOM","id":_atom(parsed)},
        "semantic_graph":{
            **expected,
            "subject_span":list(graph["subject_span"]),
            "predicate_span":list(graph["predicate_span"]),
            "object_span":list(graph["object_span"]),
        },
        "terminal_authority":False,
        "soundness_boundary":"PROVES_ONLY_THE_BOUNDED_SOURCE_EXPLICIT_MODAL_PREDICATE_ARGUMENT_STRUCTURE__NO_COREFERENCE_DOMAIN_ENTITY_IDENTITY_WORLD_APPLICABILITY_OR_POLICY_ADEQUACY",
    }
    if isinstance(condition, Mapping):
        out["condition"]={
            "relation":str(condition["relation"]),
            "text":str(condition["text"]),
            "span":list(condition["span"]),
        }
    return out
