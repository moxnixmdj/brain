"""Independent verifier for bounded task-role cross-document Finance UNLESS."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_RESULT_V1"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_DEF = re.compile(
    r"^\s*(?P<term>[A-Za-z][A-Za-z0-9 _-]{0,80}?)\s+means\s+"
    r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*\.?\s*$",
    re.I,
)
_UNLESS = re.compile(r"\bunless\b", re.I)
_FIELD = r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
_BOOL_COND = lambda term: re.compile(
    rf"^\s*{re.escape(term)}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*$", re.I
)
_MIN_COND = lambda term: re.compile(
    rf"^\s*{re.escape(term)}\s+is\s+at\s+least\s+{_NUM}\s*$", re.I
)
_MAX_COND = lambda term: re.compile(
    rf"^\s*{re.escape(term)}\s+is\s+at\s+most\s+{_NUM}\s*$", re.I
)
_EXACT_COND = lambda term: re.compile(
    rf"^\s*{re.escape(term)}\s+is\s+exactly\s+{_NUM}\s*$", re.I
)
_NUM_EQ_COND = lambda term: re.compile(
    rf"^\s*{re.escape(term)}\s*(?:is\s+|=\s*){_NUM}\s*$", re.I
)
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _pairs_no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY:" + str(key))
        out[key] = value
    return out


def _safe(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("SOURCE_PATH_INVALID")
    rel = Path(relative.strip().replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("SOURCE_PATH_NONCANONICAL")
    root = root.resolve()
    target = (root / rel).resolve()
    if target == root or root not in target.parents:
        raise ValueError("SOURCE_PATH_OUTSIDE_REPOSITORY")
    return target


def _declared_source_set(task_record: Mapping[str, Any]) -> tuple[list[dict[str, str]], str]:
    task_id = task_record.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("TASK_ID_INVALID")
    rows: list[dict[str, str]] = []
    for field in ("task_md_path", "scenario_overview_path", "week_overview_path"):
        value = task_record.get(field)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(field + "_INVALID")
            rows.append({"path": value.strip().replace("\\", "/"), "origin": field})
    for field in ("shared_files", "week_files"):
        values = task_record.get(field)
        if not isinstance(values, list):
            raise ValueError(field + "_INVALID")
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(field + "_MEMBER_INVALID")
            rows.append({"path": value.strip().replace("\\", "/"), "origin": field})
    if not rows:
        raise ValueError("DECLARED_SOURCE_SET_EMPTY")
    seen = set()
    for row in rows:
        p = row["path"]
        if p.startswith("/") or p.startswith("../") or "/../" in p or "\x00" in p:
            raise ValueError("DECLARED_SOURCE_PATH_NONCANONICAL")
        if p in seen:
            raise ValueError("DECLARED_SOURCE_DUPLICATE:" + p)
        seen.add(p)
    rows.sort(key=lambda x: (x["path"], x["origin"]))
    material = "\n".join(row["path"] + "\t" + row["origin"] for row in rows)
    return rows, sha256(material.encode("utf-8")).hexdigest()


def _decimal(value: Any) -> Decimal:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError("DECIMAL_VALUE_INVALID")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_VALUE_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_VALUE_NONFINITE")
    return out


def verify(case: Mapping[str, Any], result: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
            raise ValueError("CASE_SCHEMA_INVALID")
        if set(case) != {"schema", "task_record"}:
            raise ValueError("CASE_FIELDS_INVALID")
        if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
            raise ValueError("RESULT_SCHEMA_INVALID")

        task = case.get("task_record")
        if not isinstance(task, Mapping):
            raise ValueError("TASK_RECORD_REQUIRED")
        rows, source_set_sha = _declared_source_set(task)
        declared = {row["path"] for row in rows}

        roles = task.get("source_roles")
        if not isinstance(roles, Mapping) or set(roles) != {"policy_source_path", "fact_source_path"}:
            raise ValueError("EXACT_POLICY_AND_FACT_SOURCE_ROLES_REQUIRED")
        policy_rel = str(roles["policy_source_path"]).strip().replace("\\", "/")
        fact_rel = str(roles["fact_source_path"]).strip().replace("\\", "/")
        if policy_rel == fact_rel:
            raise ValueError("POLICY_AND_FACT_SOURCE_MUST_BE_DISTINCT")
        if policy_rel not in declared:
            raise ValueError("POLICY_SOURCE_ROLE_NOT_DECLARED")
        if fact_rel not in declared:
            raise ValueError("FACT_SOURCE_ROLE_NOT_DECLARED")

        root = Path(repo_root).resolve()
        policy_path = _safe(root, policy_rel)
        fact_path = _safe(root, fact_rel)
        policy_raw = policy_path.read_bytes()
        fact_raw = fact_path.read_bytes()
        policy_text = policy_raw.decode("utf-8")

        sentences = [x.strip() for x in _SENTENCE_SPLIT.split(policy_text) if x.strip()]
        if len(sentences) != 2:
            raise ValueError("EXACTLY_TWO_POLICY_SENTENCES_REQUIRED")
        definition_sentence, rule_text = sentences

        dm = _DEF.fullmatch(definition_sentence)
        if dm is None:
            raise ValueError("EXPLICIT_TERM_TO_FIELD_DEFINITION_REQUIRED")
        term = " ".join(dm.group("term").split()).strip()
        field_name = dm.group("field")

        matches = list(_UNLESS.finditer(rule_text))
        if len(matches) != 1:
            raise ValueError("EXACT_SINGLE_UNLESS_REQUIRED")
        um = matches[0]
        left_start, left_end = 0, um.start()
        right_start, right_end = um.end(), len(rule_text)
        while left_start < left_end and rule_text[left_start].isspace():
            left_start += 1
        while left_end > left_start and (rule_text[left_end - 1].isspace() or rule_text[left_end - 1] in ".,;:"):
            left_end -= 1
        while right_start < right_end and rule_text[right_start].isspace():
            right_start += 1
        while right_end > right_start and (rule_text[right_end - 1].isspace() or rule_text[right_end - 1] in ".,;:"):
            right_end -= 1
        ordinary = rule_text[left_start:left_end]
        condition = rule_text[right_start:right_end]

        op = literal = required_type = None
        bm = _BOOL_COND(term).fullmatch(condition)
        if bm:
            op = "BOOL_EQ"
            literal = bm.group("bool").lower()
            required_type = "BOOL"
        else:
            for regex, candidate_op in (
                (_MIN_COND(term), "DECIMAL_GE"),
                (_MAX_COND(term), "DECIMAL_LE"),
                (_EXACT_COND(term), "DECIMAL_EQ"),
                (_NUM_EQ_COND(term), "DECIMAL_EQ"),
            ):
                m = regex.fullmatch(condition)
                if m:
                    op = candidate_op
                    literal = m.group("num")
                    required_type = "DECIMAL_STRING"
                    break
        if op is None:
            raise ValueError("DEFINED_TERM_CONDITION_OUTSIDE_CONTROLLED_GRAMMAR")

        facts = json.loads(fact_raw.decode("utf-8"), object_pairs_hook=_pairs_no_duplicates)
        if not isinstance(facts, Mapping) or set(facts) != {"schema_id", "fields"}:
            raise ValueError("FACT_SOURCE_TYPED_CONTEXT_SCHEMA_INVALID")
        fields = facts.get("fields")
        if not isinstance(fields, Mapping) or not fields:
            raise ValueError("FACT_FIELDS_INVALID")
        field = fields.get(field_name)
        if not isinstance(field, Mapping) or set(field) != {"type", "value"}:
            raise ValueError("DEFINED_FIELD_NOT_PRESENT_OR_INVALID")
        if field.get("type") != required_type:
            raise ValueError("DEFINED_FIELD_TYPE_MISMATCH")

        if op == "BOOL_EQ":
            value = field.get("value")
            if not isinstance(value, bool):
                raise ValueError("BOOL_FACT_VALUE_INVALID")
            holds = value is (literal == "true")
        else:
            actual = _decimal(field.get("value"))
            threshold = _decimal(literal)
            if op == "DECIMAL_GE":
                holds = actual >= threshold
            elif op == "DECIMAL_LE":
                holds = actual <= threshold
            else:
                holds = actual == threshold

        context = {
            "schema_id": str(facts.get("schema_id")).strip(),
            "fields": {
                str(k): {"type": v["type"], "value": v["value"]}
                for k, v in fields.items()
                if isinstance(v, Mapping) and set(v) == {"type", "value"}
            },
        }
        typed_digest = sha256(_canon(context).encode("utf-8")).hexdigest()
        selected_branch = "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH"
        selected_local = (right_start, right_end) if holds else (left_start, left_end)
        selected_text = rule_text[selected_local[0]:selected_local[1]]
        rule_start = policy_text.find(rule_text)
        if rule_start < 0 or policy_text.find(rule_text, rule_start + 1) >= 0:
            raise ValueError("RULE_SENTENCE_NOT_UNIQUE")
        selected_span = [rule_start + selected_local[0], rule_start + selected_local[1]]

        expected = {
            "task_id": str(task["task_id"]).strip(),
            "source_set_sha256": source_set_sha,
            "declared_source_count": len(rows),
            "policy_source_path": policy_rel,
            "policy_source_sha256": _sha(policy_raw),
            "fact_source_path": fact_rel,
            "fact_source_sha256": _sha(fact_raw),
            "typed_context_sha256": typed_digest,
            "defined_term": term,
            "field_name": field_name,
            "field_type": required_type,
            "operator": op,
            "literal": literal,
            "condition_holds": holds,
            "selected_branch": selected_branch,
            "selected_span": selected_span,
            "selected_text": selected_text,
            "selected_text_sha256": sha256(selected_text.encode("utf-8")).hexdigest(),
        }
        for key, value in expected.items():
            if result.get(key) != value:
                errors.append("MISMATCH:" + key)

        if result.get("pass") is not True:
            errors.append("PRODUCER_PASS_MISSING")
        if result.get("source_role_authority") != (
            "EXPLICIT_TASK_RECORD_ROLE_BINDING_WITHIN_DECLARED_BOUNDED_SOURCE_SET_ONLY"
        ):
            errors.append("SOURCE_ROLE_AUTHORITY_BOUNDARY_MISMATCH")
        for key in (
            "implicit_source_role_discovery_used",
            "general_cross_document_binding_claimed",
            "external_world_fact_authority_claimed",
            "general_ontology_mapping_claimed",
            "terminal_authority",
        ):
            if result.get(key) is not False:
                errors.append("AUTHORITY_BOUNDARY_VIOLATION:" + key)
        if result.get("model_dependency_count") != 0:
            errors.append("MODEL_DEPENDENCY_NONZERO")
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))

    return {
        "schema": SCHEMA,
        "verified": not errors,
        "status": (
            "PASS__INDEPENDENT_TASK_ROLE_CROSS_DOCUMENT_RECOMPUTATION"
            if not errors else "FAIL_CLOSED"
        ),
        "errors": sorted(set(errors)),
        "producer_independent": True,
        "model_dependency_count": 0,
        "terminal_authority": False,
        "boundary": (
            "TASK_RECORD_EXPLICITLY_BINDS_TWO_DECLARED_SOURCE_PATHS_TO_POLICY_AND_FACT_ROLES;"
            "POLICY_MUST_EXPLICITLY_DEFINE_ONE_TERM_AS_ONE_LITERAL_FACT_FIELD;"
            "NO_SOURCE_ROLE_DISCOVERY_NO_SYNONYMY_NO_ONTOLOGY_NO_EXTERNAL_WORLD_AUTHORITY"
        ),
    }
