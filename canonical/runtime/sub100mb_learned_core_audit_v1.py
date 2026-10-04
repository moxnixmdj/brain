from __future__ import annotations

from typing import Any, Dict, Iterable

INPUT_SCHEMA = "PROJECT_BRAIN_SUB100MB_LEARNED_CORE_AUDIT_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_SUB100MB_LEARNED_CORE_AUDIT_OUTPUT_V1"
LEARNED_STATE_BUDGET_BYTES = 100_000_000
REQUIRED_FAMILY_COUNT = 19
REQUIRED_ATOMIC_COUNT = 38

_ALLOWED_CLASSES = {"LEARNED", "DETERMINISTIC", "EXTERNAL_KNOWLEDGE"}


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _ids(rows: Iterable[Dict[str, Any]]) -> list[str]:
    return [str(row.get("id", "")) for row in rows]


def audit_sub100mb_contract(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []

    if payload.get("schema") != INPUT_SCHEMA:
        errors.append("SCHEMA_MISMATCH")

    components = payload.get("persistent_state_components")
    if not isinstance(components, list):
        errors.append("PERSISTENT_STATE_COMPONENTS_NOT_LIST")
        components = []

    seen_component_ids: set[str] = set()
    learned_bytes = 0
    for idx, component in enumerate(components):
        if not isinstance(component, dict):
            errors.append(f"COMPONENT_NOT_OBJECT:{idx}")
            continue
        cid = component.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"COMPONENT_ID_INVALID:{idx}")
        elif cid in seen_component_ids:
            errors.append(f"COMPONENT_ID_DUPLICATE:{cid}")
        else:
            seen_component_ids.add(cid)

        cls = component.get("class")
        if cls not in _ALLOWED_CLASSES:
            errors.append(f"COMPONENT_CLASS_INVALID:{idx}")
            continue

        byte_count = component.get("bytes")
        if not _nonnegative_int(byte_count):
            errors.append(f"COMPONENT_BYTES_INVALID:{idx}")
            continue

        if cls == "LEARNED":
            learned_bytes += byte_count

    scored_execution = payload.get("scored_execution")
    if not isinstance(scored_execution, dict):
        errors.append("SCORED_EXECUTION_NOT_OBJECT")
        scored_execution = {}

    providers = scored_execution.get("external_learned_capability_providers", [])
    if not isinstance(providers, list):
        errors.append("EXTERNAL_LEARNED_PROVIDERS_NOT_LIST")
        providers = []
    if providers:
        errors.append("EXTERNAL_LEARNED_CAPABILITY_PROVIDER_PRESENT")

    knowledge_sources = scored_execution.get("external_knowledge_sources", [])
    if not isinstance(knowledge_sources, list):
        errors.append("EXTERNAL_KNOWLEDGE_SOURCES_NOT_LIST")

    predicates = payload.get("atomic_predicates")
    if not isinstance(predicates, list):
        errors.append("ATOMIC_PREDICATES_NOT_LIST")
        predicates = []

    predicate_ids = _ids([p for p in predicates if isinstance(p, dict)])
    if len(predicates) != REQUIRED_ATOMIC_COUNT:
        errors.append(f"ATOMIC_PREDICATE_COUNT_INVALID:{len(predicates)}")
    if len(predicate_ids) != len(set(predicate_ids)):
        errors.append("ATOMIC_PREDICATE_ID_DUPLICATE")

    accepted_predicates = 0
    for idx, predicate in enumerate(predicates):
        if not isinstance(predicate, dict):
            errors.append(f"ATOMIC_PREDICATE_NOT_OBJECT:{idx}")
            continue
        if not isinstance(predicate.get("accepted"), bool):
            errors.append(f"ATOMIC_PREDICATE_ACCEPTANCE_INVALID:{idx}")
        elif predicate["accepted"]:
            accepted_predicates += 1

    families = payload.get("capability_families")
    if not isinstance(families, list):
        errors.append("CAPABILITY_FAMILIES_NOT_LIST")
        families = []

    family_ids = _ids([f for f in families if isinstance(f, dict)])
    if len(families) != REQUIRED_FAMILY_COUNT:
        errors.append(f"CAPABILITY_FAMILY_COUNT_INVALID:{len(families)}")
    if len(family_ids) != len(set(family_ids)):
        errors.append("CAPABILITY_FAMILY_ID_DUPLICATE")

    accepted_families = 0
    for idx, family in enumerate(families):
        if not isinstance(family, dict):
            errors.append(f"CAPABILITY_FAMILY_NOT_OBJECT:{idx}")
            continue
        if not isinstance(family.get("accepted"), bool):
            errors.append(f"CAPABILITY_FAMILY_ACCEPTANCE_INVALID:{idx}")
        elif family["accepted"]:
            accepted_families += 1

    if learned_bytes > LEARNED_STATE_BUDGET_BYTES:
        errors.append(
            f"LEARNED_STATE_BUDGET_EXCEEDED:{learned_bytes}>{LEARNED_STATE_BUDGET_BYTES}"
        )

    structural_valid = not errors
    terminal_pass = (
        structural_valid
        and learned_bytes <= LEARNED_STATE_BUDGET_BYTES
        and accepted_predicates == REQUIRED_ATOMIC_COUNT
        and accepted_families == REQUIRED_FAMILY_COUNT
        and not providers
    )

    return {
        "schema": OUTPUT_SCHEMA,
        "status": "PASS" if terminal_pass else ("FAIL_CLOSED" if errors else "OPEN"),
        "pass": terminal_pass,
        "learned_state_bytes": learned_bytes,
        "learned_state_budget_bytes": LEARNED_STATE_BUDGET_BYTES,
        "learned_state_margin_bytes": LEARNED_STATE_BUDGET_BYTES - learned_bytes,
        "accepted_atomic_predicates": accepted_predicates,
        "required_atomic_predicates": REQUIRED_ATOMIC_COUNT,
        "accepted_capability_families": accepted_families,
        "required_capability_families": REQUIRED_FAMILY_COUNT,
        "external_learned_capability_provider_count": len(providers),
        "errors": sorted(errors),
        "accounting_rule": (
            "COUNT_EVERY_PERSISTENT_LEARNED_BYTE_REGARDLESS_OF_LABEL_OR_MODULE;"
            "EXTERNAL_KNOWLEDGE_ALLOWED;EXTERNAL_LEARNED_CAPABILITY_FORBIDDEN_DURING_SCORED_EXECUTION"
        ),
    }
