"""Zero-learned bounded compositional language compiler for H100.

This runtime compiles a deliberately bounded compositional language into a small
proposition IR: signed role assertions, directional edges, metadata exclusions,
and bounded discourse references. It is not an open-world parser. Unsupported or
ambiguous references fail closed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_COMPOSITIONAL_LANGUAGE_V1"
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"

_INPUT_ROLE_WORDS = {
    "predictor", "predictors", "input", "inputs", "feature", "features",
    "covariate", "covariates", "regressor", "regressors",
    "independent variable", "independent variables",
    "explanatory variable", "explanatory variables",
}
_TARGET_ROLE_WORDS = {
    "response", "target", "output", "label", "outcome", "regressand", "result",
    "dependent variable",
}
_DIRECTION_RE = re.compile(
    r"^(.+?)\s+(?:(does\s+not|do\s+not)\s+)?(predicts?|affects?|influences?)\s+(.+?)$",
    re.IGNORECASE,
)
_ROLE_RE = re.compile(
    r"^(.+?)\s+(is|are)\s+(?:also\s+)?(?:(not)\s+)?(?:(?:an?|the)\s+)?(.+?)$",
    re.IGNORECASE,
)
_GENERIC_VAR_RE = re.compile(
    r"^(.+?)\s+(?:is|are)\s+(?:(?:an?|the)\s+)?variables?$",
    re.IGNORECASE,
)
_RELATIVE_TARGET_RE = re.compile(
    r"^(.+?),\s*which\s+is\s+(?:(?:an?|the)\s+)?(.+?)$",
    re.IGNORECASE,
)


class CompositionalLanguageError(ValueError):
    pass


@dataclass
class Discourse:
    last_group: list[str] = field(default_factory=list)
    last_pair: list[str] = field(default_factory=list)
    last_singular: str | None = None


@dataclass
class State:
    positive: dict[str, set[str]] = field(default_factory=dict)
    negative: dict[str, set[str]] = field(default_factory=dict)
    metadata: set[str] = field(default_factory=set)
    reference_error: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)


def _norm(text: Any) -> str:
    if not isinstance(text, str) or not text.strip():
        raise CompositionalLanguageError("TEXT_INVALID")
    return " ".join(text.strip().split())


def _split_clauses(text: str) -> list[str]:
    # "but" is a truth-functional boundary for this bounded grammar.
    raw = re.split(r"\s*(?:[.;]|\bbut\b)\s*", text, flags=re.IGNORECASE)
    return [x.strip(" ,") for x in raw if x.strip(" ,")]


def _parse_explicit_names(expr: str) -> list[str] | None:
    cleaned = expr.strip()
    parts = [
        x.strip()
        for x in re.split(r"\s*(?:,|\band\b)\s*", cleaned, flags=re.IGNORECASE)
        if x.strip()
    ]
    if not parts:
        return None
    if any(re.fullmatch(_IDENT, x) is None for x in parts):
        return None
    lowered = [x.lower() for x in parts]
    if len(lowered) != len(set(lowered)):
        raise CompositionalLanguageError("ENTITY_DUPLICATE")
    return lowered


def _resolve_expr(expr: str, d: Discourse, *, plural_allowed: bool) -> tuple[list[str] | None, bool]:
    e = " ".join(expr.strip().lower().split())
    if e == "the former":
        return ([d.last_pair[0]] if len(d.last_pair) == 2 else None, len(d.last_pair) != 2)
    if e == "the latter":
        return ([d.last_pair[1]] if len(d.last_pair) == 2 else None, len(d.last_pair) != 2)
    if e in {"they", "both"}:
        ok = len(d.last_group) >= 2
        return (list(d.last_group) if ok else None, not ok)
    if e == "it":
        return ([d.last_singular] if d.last_singular else None, d.last_singular is None)
    names = _parse_explicit_names(expr)
    if names is None:
        return None, True
    if not plural_allowed and len(names) != 1:
        return None, True
    return names, False


def _remember_explicit(expr: str, d: Discourse) -> None:
    names = _parse_explicit_names(expr)
    if names is None:
        return
    d.last_group = list(names)
    if len(names) == 2:
        d.last_pair = list(names)
        d.last_singular = None
    elif len(names) == 1:
        d.last_singular = names[0]
        d.last_group = list(names)


def _role(wording: str) -> str | None:
    w = " ".join(wording.strip().lower().split())
    if w in _INPUT_ROLE_WORDS:
        return "INPUT"
    if w in _TARGET_ROLE_WORDS:
        return "TARGET"
    return None


def _add_fact(state: State, entity: str, role: str, positive: bool, source: str) -> None:
    table = state.positive if positive else state.negative
    table.setdefault(entity, set()).add(role)
    state.events.append(
        {"kind": "ROLE_ASSERTION", "entity": entity, "role": role, "positive": positive, "source": source}
    )


def _mark_metadata(state: State, entities: list[str], source: str) -> None:
    for entity in entities:
        state.metadata.add(entity)
        # Metadata is an explicit correction in this bounded grammar.
        state.positive.get(entity, set()).discard("INPUT")
        state.positive.get(entity, set()).discard("TARGET")
        state.events.append({"kind": "METADATA_EXCLUSION", "entity": entity, "source": source})


def _process_role_clause(clause: str, d: Discourse, state: State) -> bool:
    m = _ROLE_RE.fullmatch(clause)
    if not m:
        return False
    subject_expr, _verb, neg, wording = m.groups()
    wording_n = " ".join(wording.lower().split())

    if wording_n == "metadata":
        entities, bad = _resolve_expr(subject_expr, d, plural_allowed=True)
        if bad or entities is None:
            state.reference_error = True
            return True
        _mark_metadata(state, entities, clause)
        _remember_explicit(subject_expr, d)
        return True

    role = _role(wording)
    if role is None:
        return False

    entities, bad = _resolve_expr(subject_expr, d, plural_allowed=True)
    if bad or entities is None:
        state.reference_error = True
        return True
    for entity in entities:
        _add_fact(state, entity, role, positive=(neg is None), source=clause)
    _remember_explicit(subject_expr, d)
    if len(entities) == 1:
        d.last_singular = entities[0]
    return True


def _process_direction_clause(clause: str, d: Discourse, state: State) -> bool:
    m = _DIRECTION_RE.fullmatch(clause)
    if not m:
        return False
    subject_expr, neg, relation, object_expr = m.groups()

    relative_role = None
    rm = _RELATIVE_TARGET_RE.fullmatch(object_expr)
    if rm:
        object_expr, relative_wording = rm.groups()
        relative_role = _role(relative_wording)
        if relative_role is None:
            return False

    subjects, bad_s = _resolve_expr(subject_expr, d, plural_allowed=True)
    objects, bad_o = _resolve_expr(object_expr, d, plural_allowed=False)
    if bad_s or bad_o or subjects is None or objects is None:
        state.reference_error = True
        return True
    obj = objects[0]

    positive_edge = neg is None
    state.events.append(
        {
            "kind": "DIRECTIONAL_EDGE",
            "subjects": list(subjects),
            "object": obj,
            "relation": relation.lower(),
            "positive": positive_edge,
            "source": clause,
        }
    )
    if positive_edge:
        for entity in subjects:
            _add_fact(state, entity, "INPUT", True, clause)
        _add_fact(state, obj, "TARGET", True, clause)
    if relative_role is not None:
        _add_fact(state, obj, relative_role, True, clause)

    _remember_explicit(subject_expr, d)
    # The explicit object is the most recent singular mention.
    explicit_object = _parse_explicit_names(object_expr)
    if explicit_object and len(explicit_object) == 1:
        d.last_singular = explicit_object[0]
    return True


def _process_generic_clause(clause: str, d: Discourse, state: State) -> bool:
    m = _GENERIC_VAR_RE.fullmatch(clause)
    if not m:
        return False
    subject_expr = m.group(1)
    entities, bad = _resolve_expr(subject_expr, d, plural_allowed=True)
    if bad or entities is None:
        state.reference_error = True
        return True
    _remember_explicit(subject_expr, d)
    state.events.append({"kind": "MENTION_ONLY", "entities": list(entities), "source": clause})
    return True


def _status_result(status: str, state: State) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "inputs": [],
        "target": None,
        "events": state.events,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "hard_nonclaim": "FINITE_BOUNDED_COMPOSITIONAL_GRAMMAR_IS_NOT_OPEN_WORLD_LANGUAGE_UNDERSTANDING",
    }


def compile_compositional_roles(text: Any) -> dict[str, Any]:
    source = _norm(text)
    clauses = _split_clauses(source)
    if not clauses:
        raise CompositionalLanguageError("CLAUSES_EMPTY")

    d = Discourse()
    state = State()
    unsupported = []

    for clause in clauses:
        if _process_direction_clause(clause, d, state):
            continue
        if _process_role_clause(clause, d, state):
            continue
        if _process_generic_clause(clause, d, state):
            continue
        unsupported.append(clause)

    if state.reference_error:
        return _status_result("ABSTAIN_REFERENCE_AMBIGUOUS", state)

    for entity in set(state.positive) | set(state.negative):
        both = state.positive.get(entity, set()) & state.negative.get(entity, set())
        if both:
            return _status_result("ABSTAIN_CONTRADICTION", state)

    positive_targets = sorted(
        entity
        for entity, roles in state.positive.items()
        if "TARGET" in roles and entity not in state.metadata
    )
    if len(positive_targets) > 1:
        return _status_result("ABSTAIN_MULTIPLE_TARGETS", state)

    target = positive_targets[0] if len(positive_targets) == 1 else None
    inputs = sorted(
        entity
        for entity, roles in state.positive.items()
        if "INPUT" in roles and entity not in state.metadata and entity != target
    )

    # Unsupported clauses are tolerated only if the load-bearing roles were already
    # derived and the unsupported text contains no bounded reference token.
    if unsupported:
        risky = any(
            re.search(r"\b(it|they|former|latter|which|both)\b", clause, re.IGNORECASE)
            for clause in unsupported
        )
        if risky:
            return _status_result("ABSTAIN_REFERENCE_AMBIGUOUS", state)

    if target is None or not inputs:
        return _status_result("ABSTAIN_DIRECTION_NOT_IDENTIFIED", state)

    return {
        "schema": SCHEMA,
        "status": "ROLES_IDENTIFIED",
        "inputs": inputs,
        "target": target,
        "events": state.events,
        "unsupported_clauses": unsupported,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "hard_nonclaim": "FINITE_BOUNDED_COMPOSITIONAL_GRAMMAR_IS_NOT_OPEN_WORLD_LANGUAGE_UNDERSTANDING",
    }
