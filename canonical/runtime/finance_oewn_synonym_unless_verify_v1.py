"""Independent verifier for bounded OEWN-backed Finance UNLESS synonym binding."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_OEWN_SYNONYM_UNLESS_RESULT_V1"
PINNED_OEWN_GIT_BLOB = "1d877629399aef04e12ad66b1e365aecb0500cd7"
_TOKEN = re.compile(r"[a-z0-9]+")
_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")
_UNLESS = re.compile(r"\bunless\b", re.I)
_RIGHT = re.compile(r"^\s*(?P<cue>[A-Za-z][A-Za-z0-9_-]*)\s+(?P<rest>.+?)\s*$")
_FIELD = r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
_BOOL = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*$", re.I)
_NUM_EQ = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*){_NUM}\s*$", re.I)
_MIN = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+least\s+{_NUM}\s*$", re.I)
_MAX = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+most\s+{_NUM}\s*$", re.I)
_EXACT = re.compile(rf"^\s*{_FIELD}\s+is\s+exactly\s+{_NUM}\s*$", re.I)
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_STOP = {"a","an","and","are","as","at","be","by","for","from","in","is","it","of","on","or","that","the","their","this","to","was","what","which","with"}


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _norm(v: Any) -> str:
    return " ".join(str(v or "").strip().lower().split())


def _tokens(v: Any) -> set[str]:
    return {x for x in _TOKEN.findall(str(v or "").lower()) if len(x) > 1 and x not in _STOP}


def _signature(row: Mapping[str, Any]) -> set[str]:
    pieces = [x for x in row.get("members", []) if isinstance(x, str)]
    if isinstance(row.get("definition"), str):
        pieces.append(row["definition"])
    pieces.extend(x for x in row.get("examples", []) if isinstance(x, str))
    if isinstance(row.get("lexname"), str):
        pieces.append(row["lexname"].replace(".", " "))
    return _tokens(" ".join(pieces))


def _safe(root: Path, rel: str) -> Path:
    p = Path(str(rel))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("PATH_INVALID")
    q = (root / p).resolve()
    if q == root or root not in q.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return q


def _trim(text: str, a: int, b: int) -> tuple[int, int]:
    while a < b and text[a].isspace():
        a += 1
    while b > a and (text[b - 1].isspace() or text[b - 1] in ".,;:"):
        b -= 1
    return a, b


def _scope_id(source_id: str, text: str, match: re.Match[str]) -> tuple[str, tuple[int, int], tuple[int, int]]:
    left = _trim(text, 0, match.start())
    right = _trim(text, match.end(), len(text))
    material = (
        f"{source_id}\0{match.start()}\0{match.end()}\0CONDITIONAL_UNLESS\0"
        f"{text[match.start():match.end()].lower()}"
    )
    operator_id = "OP-" + sha256(material.encode("utf-8")).hexdigest()[:20]
    scope_raw = f"{source_id}\0UNLESS\0{operator_id}\0{(left, right)!r}".encode("utf-8")
    return "SCOPE-" + sha256(scope_raw).hexdigest()[:20], left, right


def _atom(source_id: str, scope_id: str, field: str, operator: str, literal: str, digest: str) -> str:
    payload = {
        "source_id": source_id,
        "scope_id": scope_id,
        "field_name": field,
        "operator": operator,
        "literal": literal,
        "typed_context_sha256": digest,
    }
    return "CERTIFIED_CONDITION::" + sha256(_canon(payload).encode("utf-8")).hexdigest()


def _decimal(v: Any) -> Decimal:
    if not isinstance(v, str) or _DECIMAL.fullmatch(v) is None:
        raise ValueError("DECIMAL_STRING_INVALID")
    try:
        out = Decimal(v)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_STRING_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_STRING_NONFINITE")
    return out


def _resolve(cue: str, target: str, context: str, knowledge: Mapping[str, Any]):
    queries = knowledge.get("queries")
    query = queries.get(_norm(cue)) if isinstance(queries, Mapping) else None
    if not isinstance(query, Mapping) or query.get("noun_query_complete") is not True:
        raise ValueError("QUERY_NOT_COMPLETE")
    rows = query.get("records")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise ValueError("QUERY_RECORDS_INVALID")
    candidates = []
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            raise ValueError("RECORD_INVALID")
        members = row.get("members")
        if not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
            raise ValueError("MEMBERS_INVALID")
        mem = {_norm(x) for x in members}
        if _norm(cue) not in mem:
            raise ValueError("QUERY_COMPLETENESS_BROKEN")
        candidates.append((row["id"], mem, _signature(row)))
    target_n = _norm(target)
    eligible = [x for x in candidates if target_n in x[1]]
    if not eligible:
        raise ValueError("TARGET_FIELD_NOT_SYNONYM")
    if len(eligible) == len(candidates):
        return "SENSE_CONSENSUS_SYNONYM", sorted(x[0] for x in candidates), []
    ctx = _tokens(context)
    scored = sorted(
        [(len(ctx & x[2]), x[0], x, sorted(ctx & x[2])) for x in candidates],
        key=lambda x: (-x[0], x[1]),
    )
    if not scored or scored[0][0] <= 0 or (len(scored) > 1 and scored[0][0] == scored[1][0]):
        raise ValueError("LEXICAL_SENSE_AMBIGUOUS")
    best = scored[0]
    if target_n not in best[2][1]:
        raise ValueError("SELECTED_SENSE_NOT_TARGET_FIELD_SYNONYM")
    return "CONTEXT_UNIQUE_TOP_SENSE_SYNONYM", [best[1]], best[3]


def verify(case: Mapping[str, Any], result: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
            raise ValueError("CASE_SCHEMA_INVALID")
        if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
            raise ValueError("RESULT_SCHEMA_INVALID")
        source_id = str(case.get("source_id") or "").strip()
        source = str(case.get("source_text") or "")
        target = str(case.get("target_field") or "").strip()
        ctx = case.get("typed_context")
        if not source_id or not source or not target or not isinstance(ctx, Mapping):
            raise ValueError("INPUT_SHAPE_INVALID")
        digest = sha256(_canon(ctx).encode("utf-8")).hexdigest()
        if case.get("typed_context_sha256") != digest:
            raise ValueError("TYPED_CONTEXT_DIGEST_MISMATCH")
        path = _safe(root, str(case.get("knowledge_path") or ""))
        raw = path.read_bytes()
        if _blob(raw) != PINNED_OEWN_GIT_BLOB:
            raise ValueError("KNOWLEDGE_BLOB_MISMATCH")
        knowledge = json.loads(raw.decode("utf-8"))
        sentences = [x.strip() for x in _SENTENCES.split(source) if x.strip()]
        if len(sentences) != 2:
            raise ValueError("EXACTLY_TWO_SENTENCES_REQUIRED")
        context, rule = sentences
        matches = list(_UNLESS.finditer(rule))
        if len(matches) != 1:
            raise ValueError("EXACT_SINGLE_UNLESS_REQUIRED")
        left = _trim(rule, 0, matches[0].start())
        right = _trim(rule, matches[0].end(), len(rule))
        raw_condition = rule[right[0]:right[1]]
        rm = _RIGHT.fullmatch(raw_condition)
        if rm is None:
            raise ValueError("CUE_CONDITION_INVALID")
        mode, synsets, evidence = _resolve(rm.group("cue"), target, context, knowledge)
        ordinary = rule[left[0]:left[1]]
        expanded = ordinary + " unless " + target + " " + rm.group("rest") + "."
        expanded_matches = list(_UNLESS.finditer(expanded))
        if len(expanded_matches) != 1:
            raise ValueError("EXPANDED_UNLESS_INVALID")
        expanded_source_id = source_id + "#expanded"
        expanded_scope, _, _ = _scope_id(
            expanded_source_id,
            expanded,
            expanded_matches[0],
        )
        condition_text = target + " " + rm.group("rest")
        match = _BOOL.fullmatch(condition_text)
        field = operator = literal = required = ""
        holds = None
        if match:
            field = match.group("field")
            literal = match.group("bool").lower()
            operator = "BOOL_EQ"
            required = "BOOL"
        else:
            for rx, opname in ((_MIN, "DECIMAL_GE"), (_MAX, "DECIMAL_LE"), (_EXACT, "DECIMAL_EQ"), (_NUM_EQ, "DECIMAL_EQ")):
                match = rx.fullmatch(condition_text)
                if match:
                    field = match.group("field")
                    literal = match.group("num")
                    operator = opname
                    required = "DECIMAL_STRING"
                    break
        if not field:
            raise ValueError("CONDITION_OUTSIDE_TYPED_GRAMMAR")
        fields = ctx.get("fields")
        row = fields.get(field) if isinstance(fields, Mapping) else None
        if not isinstance(row, Mapping) or row.get("type") != required:
            raise ValueError("FIELD_OR_TYPE_MISMATCH")
        value = row.get("value")
        if operator == "BOOL_EQ":
            if not isinstance(value, bool):
                raise ValueError("BOOL_VALUE_INVALID")
            holds = value is (literal == "true")
        else:
            av, lv = _decimal(value), _decimal(literal)
            holds = av >= lv if operator == "DECIMAL_GE" else av <= lv if operator == "DECIMAL_LE" else av == lv
        atom_id = _atom(
            expanded_source_id,
            expanded_scope,
            field,
            operator,
            literal,
            digest,
        )
        atom = {"op": "ATOM", "id": atom_id}
        constraint = atom if holds else {"op": "NOT", "arg": atom}
        local = right if holds else left
        selected = rule[local[0]:local[1]]
        start = source.find(rule)
        if start < 0 or source.find(rule, start + 1) >= 0:
            raise ValueError("RULE_NOT_UNIQUE")
        expected = {
            "source_id": source_id,
            "source_text_sha256": _sha(source),
            "typed_context_sha256": digest,
            "knowledge_git_blob_sha": PINNED_OEWN_GIT_BLOB,
            "cue": _norm(rm.group("cue")),
            "target_field": _norm(target),
            "lexical_binding_mode": mode,
            "selected_synsets": synsets,
            "lexical_evidence_tokens": evidence,
            "query_record_count": len(knowledge["queries"][_norm(rm.group("cue"))]["records"]),
            "rule_text_sha256": _sha(rule),
            "expanded_rule_sha256": _sha(expanded),
            "condition_holds": holds,
            "condition_atom_id": atom_id,
            "proved_constraint": constraint,
            "field_name": field,
            "field_type": required,
            "operator": operator,
            "literal": literal,
            "selected_branch": "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH",
            "selected_span": [start + local[0], start + local[1]],
            "selected_text": selected,
            "selected_text_sha256": _sha(selected),
        }
        for key, value in expected.items():
            if result.get(key) != value:
                errors.append("MISMATCH:" + key)
        if result.get("model_dependency_count") != 0:
            errors.append("MODEL_DEPENDENCY_NONZERO")
        if result.get("persistent_learned_bytes") != 0:
            errors.append("PERSISTENT_LEARNED_BYTES_NONZERO")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_INVALID")
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))
    return {
        "schema": SCHEMA,
        "verified": not errors,
        "errors": sorted(set(errors)),
        "producer_independent": True,
        "knowledge_git_blob_sha": PINNED_OEWN_GIT_BLOB,
        "model_dependency_count": 0,
        "terminal_authority": False,
    }
