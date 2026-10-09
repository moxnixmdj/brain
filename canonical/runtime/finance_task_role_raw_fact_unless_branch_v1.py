"""Bounded cross-document Finance UNLESS producer.

This module closes one narrow cross-document binding slice:
- the task record explicitly declares a bounded source set;
- the same task record explicitly assigns one declared path the policy role and
  one distinct declared path the fact role;
- the policy contains exactly one explicit named definition and one UNLESS rule;
- the definition RHS is exactly one typed fact-field identifier;
- the fact source is raw typed JSON compiled from exact bytes.

No synonymy, ontology inference, implicit source-role discovery, source-authority
discovery, or external-world fact authentication is performed.
"""
from __future__ import annotations

from hashlib import sha256
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.bounded_task_source_set_gate_v1 import compile_required_source_set
from canonical.runtime.certified_defined_term_raw_typed_condition_v2 import (
    evaluate_defined_unless_condition_from_raw_facts,
)
from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "PROJECT_BRAIN_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_BRANCH_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_RESULT_V1"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _safe(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("SOURCE_ROLE_PATH_INVALID")
    rel = Path(relative.strip().replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("SOURCE_ROLE_PATH_NONCANONICAL")
    root = root.resolve()
    target = (root / rel).resolve()
    if target == root or root not in target.parents:
        raise ValueError("SOURCE_ROLE_PATH_OUTSIDE_REPOSITORY")
    return target


def _role_paths(task_record: Mapping[str, Any]) -> tuple[str, str]:
    roles = task_record.get("source_roles")
    if not isinstance(roles, Mapping) or set(roles) != {"policy_source_path", "fact_source_path"}:
        raise ValueError("EXACT_POLICY_AND_FACT_SOURCE_ROLES_REQUIRED")
    policy = roles.get("policy_source_path")
    facts = roles.get("fact_source_path")
    if not isinstance(policy, str) or not policy.strip():
        raise ValueError("POLICY_SOURCE_ROLE_INVALID")
    if not isinstance(facts, str) or not facts.strip():
        raise ValueError("FACT_SOURCE_ROLE_INVALID")
    policy = policy.strip().replace("\\", "/")
    facts = facts.strip().replace("\\", "/")
    if policy == facts:
        raise ValueError("POLICY_AND_FACT_SOURCE_MUST_BE_DISTINCT")
    return policy, facts


def compute(case: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if set(case) != {"schema", "task_record"}:
        raise ValueError("CASE_FIELDS_INVALID")
    task_record = case.get("task_record")
    if not isinstance(task_record, Mapping):
        raise ValueError("TASK_RECORD_REQUIRED")

    source_set = compile_required_source_set(task_record)
    if source_set.get("pass") is not True:
        raise ValueError("BOUNDED_TASK_SOURCE_SET_INVALID:" + "|".join(source_set.get("errors") or []))

    policy_rel, fact_rel = _role_paths(task_record)
    declared = {row["path"] for row in source_set["sources"]}
    if policy_rel not in declared:
        raise ValueError("POLICY_SOURCE_ROLE_NOT_IN_DECLARED_SOURCE_SET")
    if fact_rel not in declared:
        raise ValueError("FACT_SOURCE_ROLE_NOT_IN_DECLARED_SOURCE_SET")

    root = Path(repo_root).resolve()
    policy_path = _safe(root, policy_rel)
    fact_path = _safe(root, fact_rel)
    if not policy_path.is_file():
        raise ValueError("POLICY_SOURCE_FILE_MISSING")
    if not fact_path.is_file():
        raise ValueError("FACT_SOURCE_FILE_MISSING")

    policy_raw = policy_path.read_bytes()
    fact_raw = fact_path.read_bytes()
    try:
        policy_text = policy_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("POLICY_SOURCE_NOT_UTF8") from exc

    sentences = [x.strip() for x in _SENTENCE_SPLIT.split(policy_text) if x.strip()]
    if len(sentences) != 2:
        raise ValueError("EXACTLY_TWO_POLICY_SENTENCES_REQUIRED")
    rule_text = sentences[1]
    rule_start = policy_text.find(rule_text)
    if rule_start < 0 or policy_text.find(rule_text, rule_start + 1) >= 0:
        raise ValueError("RULE_SENTENCE_NOT_UNIQUELY_LOCATED")

    scoped = parse_scope(rule_text, source=policy_rel + "#rule")
    parsed = scoped.get("parse") if scoped.get("status") == "PARSED" else None
    if not isinstance(parsed, Mapping) or parsed.get("relation") != "UNLESS":
        raise ValueError("EXACT_SINGLE_UNLESS_RULE_REQUIRED")

    evaluated = evaluate_defined_unless_condition_from_raw_facts(
        policy_text,
        policy_source_id=policy_rel,
        fact_source=fact_raw,
        fact_source_id=fact_rel,
    )
    if evaluated.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
        raise ValueError(
            "CROSS_DOCUMENT_DEFINED_CONDITION_NOT_PROVED:"
            + str(evaluated.get("reason") or evaluated.get("errors"))
        )

    holds = evaluated.get("condition_holds") is True
    local_span = parsed["right_span"] if holds else parsed["left_span"]
    selected_text = rule_text[local_span[0]:local_span[1]]
    selected_span = [rule_start + local_span[0], rule_start + local_span[1]]

    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__TASK_ROLE_BOUND_CROSS_DOCUMENT_FINANCE_UNLESS_BRANCH_SELECTED",
        "pass": True,
        "task_id": source_set["task_id"],
        "source_set_sha256": source_set["source_set_sha256"],
        "declared_source_count": source_set["source_count"],
        "policy_source_path": policy_rel,
        "policy_source_sha256": _sha(policy_raw),
        "fact_source_path": fact_rel,
        "fact_source_sha256": _sha(fact_raw),
        "typed_context_sha256": evaluated["typed_context_sha256"],
        "defined_term": evaluated["defined_term"],
        "field_name": evaluated["field_name"],
        "field_type": evaluated["field_type"],
        "operator": evaluated["operator"],
        "literal": evaluated["literal"],
        "condition_holds": holds,
        "condition_atom_id": evaluated["condition_atom_id"],
        "proved_constraint": evaluated["proved_constraint"],
        "rule_scope_id": parsed["scope_id"],
        "selected_branch": "EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH",
        "selected_span": selected_span,
        "selected_text": selected_text,
        "selected_text_sha256": sha256(selected_text.encode("utf-8")).hexdigest(),
        "source_role_authority": (
            "EXPLICIT_TASK_RECORD_ROLE_BINDING_WITHIN_DECLARED_BOUNDED_SOURCE_SET_ONLY"
        ),
        "implicit_source_role_discovery_used": False,
        "general_cross_document_binding_claimed": False,
        "external_world_fact_authority_claimed": False,
        "general_ontology_mapping_claimed": False,
        "model_dependency_count": 0,
        "terminal_authority": False,
    }
