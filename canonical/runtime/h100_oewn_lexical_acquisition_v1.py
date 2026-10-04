"""Zero-learned lexical acquisition and sense disambiguation over a pinned OEWN slice.

The runtime receives normalized Open English WordNet records as raw external knowledge.
It may select among senses using deterministic token overlap with supplied context, but
it may never invent a semantic role. Roles come only from explicit content-addressed
anchor synset sets in the knowledge pack.

This is deliberately fail-closed: incomplete lemma queries, tied senses, zero-evidence
sense choices, or selected senses outside the role anchors all abstain.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_OEWN_REAL_LEXICAL_ACQUISITION_V1"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "a","an","and","are","as","at","be","by","for","from","in","is","it","of","on",
    "or","that","the","their","this","to","was","what","which","with"
}

class OEWNLexicalError(ValueError):
    pass

def _norm(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise OEWNLexicalError(label + "_INVALID")
    text = " ".join(value.strip().lower().split())
    if not text:
        raise OEWNLexicalError(label + "_EMPTY")
    return text

def _tokens(text: Any) -> set[str]:
    if not isinstance(text, str):
        return set()
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1}

def _validate_pack(knowledge: Mapping[str, Any]) -> tuple[dict[str, Any], set[str], set[str]]:
    if not isinstance(knowledge, Mapping):
        raise OEWNLexicalError("KNOWLEDGE_INVALID")
    if knowledge.get("schema") != "PROJECT_BRAIN_H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1":
        raise OEWNLexicalError("KNOWLEDGE_SCHEMA_INVALID")
    queries = knowledge.get("queries")
    anchors = knowledge.get("anchors")
    if not isinstance(queries, Mapping) or not isinstance(anchors, Mapping):
        raise OEWNLexicalError("KNOWLEDGE_STRUCTURE_INVALID")
    input_ids = anchors.get("input_synsets")
    target_ids = anchors.get("target_synsets")
    if not isinstance(input_ids, Sequence) or isinstance(input_ids, (str, bytes)):
        raise OEWNLexicalError("INPUT_ANCHORS_INVALID")
    if not isinstance(target_ids, Sequence) or isinstance(target_ids, (str, bytes)):
        raise OEWNLexicalError("TARGET_ANCHORS_INVALID")
    input_set = {str(x) for x in input_ids}
    target_set = {str(x) for x in target_ids}
    if not input_set or not target_set or input_set & target_set:
        raise OEWNLexicalError("ROLE_ANCHORS_INVALID")
    return dict(queries), input_set, target_set

def _record_signature(record: Mapping[str, Any]) -> set[str]:
    pieces = []
    for member in record.get("members", []):
        if isinstance(member, str):
            pieces.append(member)
    definition = record.get("definition")
    if isinstance(definition, str):
        pieces.append(definition)
    for example in record.get("examples", []):
        if isinstance(example, str):
            pieces.append(example)
    lexname = record.get("lexname")
    if isinstance(lexname, str):
        pieces.append(lexname.replace(".", " "))
    return _tokens(" ".join(pieces))

def _role_for(synset_id: str, input_set: set[str], target_set: set[str]) -> str | None:
    if synset_id in input_set:
        return "INPUT"
    if synset_id in target_set:
        return "TARGET"
    return None

def resolve_lexical_role(cue: Any, context: Any, knowledge: Mapping[str, Any]) -> dict[str, Any]:
    cue_n = _norm(cue, "CUE")
    context_s = "" if context is None else str(context)
    queries, input_set, target_set = _validate_pack(knowledge)

    query = queries.get(cue_n)
    if not isinstance(query, Mapping):
        return _abstain("ABSTAIN_LEXICAL_QUERY_NOT_PINNED", cue_n)
    if query.get("noun_query_complete") is not True:
        return _abstain("ABSTAIN_LEXICAL_QUERY_INCOMPLETE", cue_n)

    records = query.get("records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        raise OEWNLexicalError("QUERY_RECORDS_INVALID:" + cue_n)

    candidates = []
    for i, raw in enumerate(records):
        if not isinstance(raw, Mapping):
            raise OEWNLexicalError(f"RECORD_INVALID:{cue_n}:{i}")
        sid = raw.get("id")
        members = raw.get("members")
        if not isinstance(sid, str) or not sid.endswith("-n"):
            raise OEWNLexicalError(f"RECORD_ID_INVALID:{cue_n}:{i}")
        if not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
            raise OEWNLexicalError(f"RECORD_MEMBERS_INVALID:{cue_n}:{i}")
        normalized_members = {_norm(x, f"MEMBER:{cue_n}:{i}") for x in members}
        if cue_n not in normalized_members:
            raise OEWNLexicalError(f"QUERY_COMPLETENESS_BROKEN:{cue_n}:{sid}")
        candidates.append({
            "id":sid,
            "role":_role_for(sid,input_set,target_set),
            "signature":_record_signature(raw),
        })

    roles = {c["role"] for c in candidates}
    if len(roles) == 1 and None not in roles:
        role = next(iter(roles))
        return _success(cue_n, role, "SENSE_CONSENSUS", [c["id"] for c in candidates], None)

    context_tokens = _tokens(context_s)
    if not context_tokens:
        return _abstain("ABSTAIN_LEXICAL_SENSE_AMBIGUOUS", cue_n)

    scored = []
    for c in candidates:
        overlap = sorted(context_tokens & c["signature"])
        scored.append((len(overlap), c["id"], c["role"], overlap))
    scored.sort(key=lambda row: (-row[0], row[1]))
    best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else -1

    if best[0] <= 0 or best[0] == second_score:
        return _abstain("ABSTAIN_LEXICAL_SENSE_AMBIGUOUS", cue_n)
    if best[2] is None:
        return _abstain("ABSTAIN_LEXICAL_SENSE_UNSUPPORTED", cue_n, selected_synset=best[1], evidence_tokens=best[3])

    return _success(cue_n, best[2], "CONTEXT_UNIQUE_TOP_SENSE", [best[1]], best[3])

def _success(cue: str, role: str, mode: str, synsets: list[str], evidence_tokens: list[str] | None) -> dict[str, Any]:
    return {
        "schema":SCHEMA,
        "status":"ROLE_IDENTIFIED",
        "cue":cue,
        "role":role,
        "mode":mode,
        "selected_synsets":synsets,
        "evidence_tokens":evidence_tokens or [],
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "raw_external_knowledge_used":True,
        "hard_nonclaim":"FINITE_PINNED_OEWN_SLICE_DOES_NOT_PROVE_OPEN_WORLD_LEXICAL_COMPLETENESS",
    }

def _abstain(status: str, cue: str, selected_synset: str | None=None, evidence_tokens: list[str] | None=None) -> dict[str, Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "cue":cue,
        "role":None,
        "mode":"ABSTAIN",
        "selected_synsets":[selected_synset] if selected_synset else [],
        "evidence_tokens":evidence_tokens or [],
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "raw_external_knowledge_used":True,
        "hard_nonclaim":"ABSTENTION_PRESERVES_UNKNOWN_AMBIGUOUS_OR_UNSUPPORTED_LEXICAL_SEMANTICS",
    }
