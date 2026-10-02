"""Exact bounded typed hypothesis compiler for Project Brain.

This module does not infer natural-language meaning and has no terminal authority.
It takes an explicit typed entity inventory, explicit facts, and explicit hypothesis
templates (which may be supplied by Brain-owned semantics or JIT knowledge) and
exhaustively instantiates every well-typed candidate supported by the declared facts.

The key property is completeness relative to the finite declared template/entity
universe: candidates are never ranked away merely because several survive. Ambiguity
is preserved for downstream evidence gathering, verification, or exact selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Sequence

MAX_ENTITIES = 64
MAX_FACTS = 256
MAX_TEMPLATES = 64
MAX_VARIABLES_PER_TEMPLATE = 8
MAX_CANDIDATES = 4096


@dataclass(frozen=True)
class Entity:
    entity_id: str
    types: frozenset[str]


@dataclass(frozen=True)
class Atom:
    predicate: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class Template:
    template_id: str
    variables: tuple[tuple[str, str], ...]
    requires: tuple[Atom, ...]
    emits: tuple[Atom, ...]


def _valid_token(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate(
    entities: Sequence[Entity],
    facts: Sequence[Atom],
    templates: Sequence[Template],
) -> tuple[list[Entity], set[Atom], list[Template], str | None]:
    if not isinstance(entities, Sequence) or len(entities) > MAX_ENTITIES:
        return [], set(), [], "ENTITY_UNIVERSE_INVALID_OR_TOO_LARGE"
    if not isinstance(facts, Sequence) or len(facts) > MAX_FACTS:
        return [], set(), [], "FACT_UNIVERSE_INVALID_OR_TOO_LARGE"
    if not isinstance(templates, Sequence) or len(templates) > MAX_TEMPLATES:
        return [], set(), [], "TEMPLATE_UNIVERSE_INVALID_OR_TOO_LARGE"

    entity_ids = [e.entity_id for e in entities]
    if any(not _valid_token(x) for x in entity_ids) or len(entity_ids) != len(set(entity_ids)):
        return [], set(), [], "ENTITY_IDENTITIES_INVALID_OR_DUPLICATE"

    clean_entities: list[Entity] = []
    for e in entities:
        if not isinstance(e.types, frozenset) or not e.types or any(not _valid_token(t) for t in e.types):
            return [], set(), [], f"ENTITY_TYPES_INVALID:{e.entity_id}"
        clean_entities.append(Entity(e.entity_id, frozenset(sorted(e.types))))

    clean_facts: set[Atom] = set()
    for fact in facts:
        if not _valid_token(fact.predicate) or any(not _valid_token(a) for a in fact.args):
            return [], set(), [], "FACT_INVALID"
        clean_facts.add(Atom(fact.predicate, tuple(fact.args)))

    template_ids = [t.template_id for t in templates]
    if any(not _valid_token(x) for x in template_ids) or len(template_ids) != len(set(template_ids)):
        return [], set(), [], "TEMPLATE_IDENTITIES_INVALID_OR_DUPLICATE"

    clean_templates: list[Template] = []
    for t in templates:
        if len(t.variables) > MAX_VARIABLES_PER_TEMPLATE:
            return [], set(), [], f"TOO_MANY_TEMPLATE_VARIABLES:{t.template_id}"
        var_names = [v[0] for v in t.variables]
        if (
            len(var_names) != len(set(var_names))
            or any(not _valid_token(name) or not _valid_token(type_name) for name, type_name in t.variables)
        ):
            return [], set(), [], f"TEMPLATE_VARIABLES_INVALID:{t.template_id}"
        declared = set(var_names)
        if not t.emits:
            return [], set(), [], f"TEMPLATE_EMITS_EMPTY:{t.template_id}"
        for atom in (*t.requires, *t.emits):
            if not _valid_token(atom.predicate) or any(not _valid_token(a) for a in atom.args):
                return [], set(), [], f"TEMPLATE_ATOM_INVALID:{t.template_id}"
            for arg in atom.args:
                if arg.startswith("$") and arg[1:] not in declared:
                    return [], set(), [], f"TEMPLATE_UNKNOWN_VARIABLE:{t.template_id}:{arg}"
        clean_templates.append(t)

    return (
        sorted(clean_entities, key=lambda x: x.entity_id),
        clean_facts,
        sorted(clean_templates, key=lambda x: x.template_id),
        None,
    )


def _instantiate(atom: Atom, binding: dict[str, str]) -> Atom:
    return Atom(
        atom.predicate,
        tuple(binding[arg[1:]] if arg.startswith("$") else arg for arg in atom.args),
    )


def compile_hypotheses(
    *,
    entities: Sequence[Entity],
    facts: Sequence[Atom],
    templates: Sequence[Template],
    max_candidates: int = MAX_CANDIDATES,
) -> dict:
    if not isinstance(max_candidates, int) or isinstance(max_candidates, bool) or not (1 <= max_candidates <= MAX_CANDIDATES):
        return {"status": "FAIL_CLOSED", "reason": "MAX_CANDIDATES_INVALID", "terminal_authority": False}

    clean_entities, fact_set, clean_templates, err = _validate(entities, facts, templates)
    if err:
        return {"status": "FAIL_CLOSED", "reason": err, "terminal_authority": False}

    by_type: dict[str, list[str]] = {}
    for entity in clean_entities:
        for type_name in entity.types:
            by_type.setdefault(type_name, []).append(entity.entity_id)
    for ids in by_type.values():
        ids.sort()

    candidates: list[dict] = []
    seen: set[tuple] = set()

    for template in clean_templates:
        domains: list[list[str]] = []
        missing_type = False
        for _, type_name in template.variables:
            values = by_type.get(type_name, [])
            if not values:
                missing_type = True
                break
            domains.append(values)
        if missing_type:
            continue

        assignments = product(*domains) if domains else [()]
        for values in assignments:
            binding = {name: value for (name, _), value in zip(template.variables, values)}
            instantiated_requires = tuple(_instantiate(a, binding) for a in template.requires)
            if any(req not in fact_set for req in instantiated_requires):
                continue
            instantiated_emits = tuple(_instantiate(a, binding) for a in template.emits)
            key = (
                template.template_id,
                tuple(sorted(binding.items())),
                tuple(sorted((a.predicate, a.args) for a in instantiated_emits)),
            )
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "template_id": template.template_id,
                    "binding": dict(sorted(binding.items())),
                    "support_facts": [
                        {"predicate": a.predicate, "args": list(a.args)}
                        for a in sorted(instantiated_requires, key=lambda x: (x.predicate, x.args))
                    ],
                    "emits": [
                        {"predicate": a.predicate, "args": list(a.args)}
                        for a in sorted(instantiated_emits, key=lambda x: (x.predicate, x.args))
                    ],
                }
            )
            if len(candidates) > max_candidates:
                return {
                    "status": "ESCALATE",
                    "reason": "CANDIDATE_BOUND_EXCEEDED",
                    "candidate_count_lower_bound": len(candidates),
                    "max_candidates": max_candidates,
                    "terminal_authority": False,
                    "semantic_authority": False,
                }

    candidates.sort(
        key=lambda c: (
            c["template_id"],
            tuple(c["binding"].items()),
            tuple((a["predicate"], tuple(a["args"])) for a in c["emits"]),
        )
    )
    return {
        "status": "PASS",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "completeness_scope": "EXACT_RELATIVE_TO_DECLARED_TYPED_ENTITY_FACT_AND_TEMPLATE_UNIVERSE",
        "ambiguity_policy": "PRESERVE_ALL_SUPPORTED_CANDIDATES__NO_RANKING_OR_TRUTH_CLAIM",
        "terminal_authority": False,
        "semantic_authority": False,
    }
