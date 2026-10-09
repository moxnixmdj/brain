"""Bounded OEWN-backed inferred-synonym Finance UNLESS branch selector.

Scope:
- exactly two source sentences: one lexical context sentence, then one UNLESS rule;
- the UNLESS condition begins with one OEWN-queried noun cue;
- a caller-proposed typed-context field is accepted only when the selected OEWN
  sense contains that exact field lemma as a member;
- a cue query must be complete in the pinned independently verified OEWN pack;
- polysemy requires a unique positive context-overlap winner unless every sense
  already maps to the same target field.

No open-world lexical completeness, ontology inference, or world truth is claimed.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.certified_typed_unless_condition_v1 import evaluate_unless_condition
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256

SCHEMA = "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_BRANCH_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_RESULT_V1"
PINNED_OEWN_GIT_BLOB = "1d877629399aef04e12ad66b1e365aecb0500cd7"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_CUE_CONDITION = re.compile(r"^\s*(?P<cue>[A-Za-z][A-Za-z0-9_-]*)\s+(?P<rest>.+?)\s*$")
_STOP = {
    "a","an","and","are","as","at","be","by","for","from","in","is","it","of","on",
    "or","that","the","their","this","to","was","what","which","with",
}


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _git_blob_sha(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _norm(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(label + "_INVALID")
    text = " ".join(value.strip().lower().split())
    if not text:
        raise ValueError(label + "_EMPTY")
    return text


def _tokens(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    return {x for x in _TOKEN_RE.findall(value.lower()) if len(x) > 1 and x not in _STOP}


def _record_signature(record: Mapping[str, Any]) -> set[str]:
    parts: list[str] = []
    for item in record.get("members", []):
        if isinstance(item, str):
            parts.append(item)
    if isinstance(record.get("definition"), str):
        parts.append(record["definition"])
    for item in record.get("examples", []):
        if isinstance(item, str):
            parts.append(item)
    if isinstance(record.get("lexname"), str):
        parts.append(record["lexname"].replace(".", " "))
    return _tokens(" ".join(parts))


def _safe(root: Path, rel: str) -> Path:
    p = Path(str(rel))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("KNOWLEDGE_PATH_INVALID")
    q = (root / p).resolve()
    if q == root or root not in q.parents:
        raise ValueError("KNOWLEDGE_PATH_OUTSIDE_REPOSITORY")
    return q


def _load_knowledge(case: Mapping[str, Any], root: Path) -> tuple[dict[str, Any], str]:
    rel = case.get("knowledge_path")
    if not isinstance(rel, str) or not rel:
        raise ValueError("KNOWLEDGE_PATH_REQUIRED")
    path = _safe(root, rel)
    if not path.is_file():
        raise ValueError("KNOWLEDGE_FILE_MISSING")
    raw = path.read_bytes()
    blob = _git_blob_sha(raw)
    if blob != PINNED_OEWN_GIT_BLOB:
        raise ValueError("KNOWLEDGE_BLOB_MISMATCH:" + blob)
    try:
        knowledge = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("KNOWLEDGE_JSON_INVALID") from exc
    if knowledge.get("schema") != "PROJECT_BRAIN_H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1":
        raise ValueError("KNOWLEDGE_SCHEMA_INVALID")
    return knowledge, blob


def _resolve_synonym(cue: str, target: str, context: str, knowledge: Mapping[str, Any]) -> dict[str, Any]:
    cue_n = _norm(cue, "CUE")
    target_n = _norm(target, "TARGET_FIELD")
    queries = knowledge.get("queries")
    if not isinstance(queries, Mapping):
        raise ValueError("KNOWLEDGE_QUERIES_INVALID")
    query = queries.get(cue_n)
    if not isinstance(query, Mapping):
        raise ValueError("LEXICAL_QUERY_NOT_PINNED:" + cue_n)
    if query.get("noun_query_complete") is not True:
        raise ValueError("LEXICAL_QUERY_INCOMPLETE:" + cue_n)
    records = query.get("records")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
        raise ValueError("LEXICAL_QUERY_RECORDS_INVALID:" + cue_n)

    candidates: list[dict[str, Any]] = []
    for i, raw in enumerate(records):
        if not isinstance(raw, Mapping):
            raise ValueError(f"LEXICAL_RECORD_INVALID:{cue_n}:{i}")
        sid = raw.get("id")
        members = raw.get("members")
        if not isinstance(sid, str) or not sid.endswith("-n"):
            raise ValueError(f"LEXICAL_RECORD_ID_INVALID:{cue_n}:{i}")
        if not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
            raise ValueError(f"LEXICAL_RECORD_MEMBERS_INVALID:{cue_n}:{i}")
        normalized = {_norm(x, f"MEMBER:{cue_n}:{i}") for x in members}
        if cue_n not in normalized:
            raise ValueError("LEXICAL_QUERY_COMPLETENESS_BROKEN:" + cue_n + ":" + sid)
        candidates.append({
            "id": sid,
            "members": normalized,
            "signature": _record_signature(raw),
        })

    target_candidates = [x for x in candidates if target_n in x["members"]]
    if not target_candidates:
        raise ValueError("TARGET_FIELD_NOT_SYNONYM:" + target_n)
    if len(target_candidates) == len(candidates):
        return {
            "cue": cue_n,
            "target_field": target_n,
            "mode": "SENSE_CONSENSUS_SYNONYM",
            "selected_synsets": sorted(x["id"] for x in candidates),
            "evidence_tokens": [],
            "query_record_count": len(candidates),
        }

    context_tokens = _tokens(context)
    if not context_tokens:
        raise ValueError("LEXICAL_SENSE_AMBIGUOUS:NO_CONTEXT_EVIDENCE")
    scored = []
    for item in candidates:
        overlap = sorted(context_tokens & item["signature"])
        scored.append((len(overlap), item["id"], item, overlap))
    scored.sort(key=lambda row: (-row[0], row[1]))
    best = scored[0]
    second = scored[1][0] if len(scored) > 1 else -1
    if best[0] <= 0 or best[0] == second:
        raise ValueError("LEXICAL_SENSE_AMBIGUOUS")
    if target_n not in best[2]["members"]:
        raise ValueError("SELECTED_SENSE_NOT_TARGET_FIELD_SYNONYM:" + best[1])
    return {
        "cue": cue_n,
        "target_field": target_n,
        "mode": "CONTEXT_UNIQUE_TOP_SENSE_SYNONYM",
        "selected_synsets": [best[1]],
        "evidence_tokens": best[3],
        "query_record_count": len(candidates),
    }


def compute(case: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    source_id = case.get("source_id")
    source_text = case.get("source_text")
    target_field = case.get("target_field")
    ctx = case.get("typed_context")
    expected = case.get("typed_context_sha256")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if not isinstance(target_field, str) or not target_field.strip():
        raise ValueError("TARGET_FIELD_REQUIRED")
    if not isinstance(ctx, Mapping):
        raise ValueError("TYPED_CONTEXT_REQUIRED")
    actual = typed_context_sha256(ctx)
    if not isinstance(expected, str) or expected != actual:
        raise ValueError("TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH")
    fields = ctx.get("fields")
    if not isinstance(fields, Mapping) or target_field not in fields:
        raise ValueError("TARGET_FIELD_NOT_IN_TYPED_CONTEXT")

    knowledge, knowledge_blob = _load_knowledge(case, root)
    sentences = [x.strip() for x in _SENTENCE_SPLIT.split(source_text) if x.strip()]
    if len(sentences) != 2:
        raise ValueError("EXACTLY_TWO_SOURCE_SENTENCES_REQUIRED")
    context_text, rule_text = sentences
    scoped = parse_scope(rule_text, source=source_id.strip() + "#rule")
    parsed = scoped.get("parse") if scoped.get("status") == "PARSED" else None
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "UNLESS":
        raise ValueError("EXACT_SINGLE_UNLESS_RULE_REQUIRED")
    left_span, right_span = parsed.get("left_span"), parsed.get("right_span")
    if not isinstance(left_span, list) or not isinstance(right_span, list):
        raise ValueError("UNLESS_BRANCH_SPAN_INVALID")
    ordinary = rule_text[left_span[0]:left_span[1]]
    raw_condition = rule_text[right_span[0]:right_span[1]]
    match = _CUE_CONDITION.fullmatch(raw_condition)
    if match is None:
        raise ValueError("OEWN_CUE_CONDITION_INVALID")
    cue = match.group("cue")
    rest = match.group("rest")
    binding = _resolve_synonym(cue, target_field, context_text, knowledge)

    expanded = ordinary + " unless " + target_field + " " + rest + "."
    condition = evaluate_unless_condition(
        expanded,
        source_id=source_id.strip() + "#expanded",
        typed_context=ctx,
        expected_typed_context_sha256=actual,
    )
    if condition.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
        raise ValueError("BOUND_TYPED_CONDITION_NOT_PROVED:" + str(condition.get("reason") or condition.get("errors")))
    holds = condition.get("condition_holds") is True
    local_span = right_span if holds else left_span
    selected_text = rule_text[local_span[0]:local_span[1]]
    rule_start = source_text.find(rule_text)
    if rule_start < 0 or source_text.find(rule_text, rule_start + 1) >= 0:
        raise ValueError("RULE_SENTENCE_NOT_UNIQUELY_LOCATED")

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__OEWN_SYNONYM_TYPED_FINANCE_UNLESS_BRANCH_SELECTED",
        "pass": True,
        "source_id": source_id.strip(),
        "source_text_sha256": _sha(source_text),
        "typed_context_sha256": actual,
        "knowledge_git_blob_sha": knowledge_blob,
        "cue": binding["cue"],
        "target_field": binding["target_field"],
        "lexical_binding_mode": binding["mode"],
        "selected_synsets": binding["selected_synsets"],
        "lexical_evidence_tokens": binding["evidence_tokens"],
        "query_record_count": binding["query_record_count"],
        "rule_text_sha256": _sha(rule_text),
        "expanded_rule_sha256": _sha(expanded),
        "condition_holds": holds,
        "condition_atom_id": condition.get("condition_atom_id"),
        "proved_constraint": condition.get("proved_constraint"),
        "field_name": condition.get("field_name"),
        "field_type": condition.get("field_type"),
        "operator": condition.get("operator"),
        "literal": condition.get("literal"),
        "selected_branch": "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH",
        "selected_span": [rule_start + local_span[0], rule_start + local_span[1]],
        "selected_text": selected_text,
        "selected_text_sha256": _sha(selected_text),
        "model_dependency_count": 0,
        "persistent_learned_bytes": 0,
        "raw_external_knowledge_used": True,
        "inferred_synonymy_authority": "PINNED_COMPLETE_OEWN_QUERY_SELECTED_SENSE_SAME_SYNSET_MEMBER",
        "context_word_sense_authority": "UNIQUE_POSITIVE_CONTEXT_OVERLAP_OR_ALL_SENSES_TARGET_EQUIVALENT",
        "open_world_lexical_completeness_claimed": False,
        "ontology_mapping_claimed": False,
        "external_world_truth_claimed": False,
        "terminal_authority": False,
    }
