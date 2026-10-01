"""Deterministic semantic-operator counterfactual oracle.

This module attacks a narrow but important failure mode in source-to-contract
compilation: two independent semantic extractors can agree while sharing the same
conceptual error. Explicit operators such as "at least", "must not", "before",
"every", and "only" have semantics that can be checked without trusting either
extractor.

The oracle:
1. extracts only an intentionally conservative set of explicit operators,
2. assigns stable operator identities and normalized semantics,
3. validates extractor/operator bindings against those semantics,
4. generates adversarial counterexample obligations implied by each operator,
5. fails closed when those obligations are absent from an acceptance plan.

It does NOT claim arbitrary natural-language understanding, noun/reference
resolution, implicit-world knowledge, domain-gold synthesis, or full semantic
correctness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Mapping, Sequence


class SemanticOperatorError(ValueError):
    pass


@dataclass(frozen=True)
class SemanticOperator:
    operator_id: str
    start: int
    end: int
    text: str
    semantic_class: str
    bound_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CounterfactualObligation:
    obligation_id: str
    operator_id: str
    counterfactual_kind: str
    semantic_class: str
    expected_relation: str
    bound_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Ordered longest/most-specific first. Patterns are deliberately narrow.
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("MIN_INCLUSIVE", re.compile(r"\b(?:at\s+least|no\s+less\s+than)\s+(-?\d+(?:\.\d+)?)\b", re.I)),
    ("MAX_INCLUSIVE", re.compile(r"\b(?:at\s+most|no\s+more\s+than)\s+(-?\d+(?:\.\d+)?)\b", re.I)),
    ("EXACT_VALUE", re.compile(r"\bexactly\s+(-?\d+(?:\.\d+)?)\b", re.I)),
    ("PROHIBITION", re.compile(r"\b(?:must\s+not|shall\s+not|do\s+not|never)\b", re.I)),
    ("TEMPORAL_BEFORE", re.compile(r"\bbefore\b", re.I)),
    ("TEMPORAL_AFTER", re.compile(r"\bafter\b", re.I)),
    ("UNIVERSAL_QUANTIFIER", re.compile(r"\b(?:every|each|all)\b", re.I)),
    ("AMBIGUOUS_ANY", re.compile(r"\bany\b", re.I)),
    ("EXCLUSIVITY", re.compile(r"\bonly\b", re.I)),
    ("CONDITIONAL_UNLESS", re.compile(r"\bunless\b", re.I)),
    ("CONDITIONAL_IF", re.compile(r"\bif\b", re.I)),
    ("CONDITIONAL_WHEN", re.compile(r"\bwhen\b", re.I)),
    ("ALWAYS", re.compile(r"\balways\b", re.I)),
)


def _stable_id(source: str, start: int, end: int, semantic_class: str, text: str) -> str:
    raw = f"{source}\0{start}\0{end}\0{semantic_class}\0{text.lower()}".encode("utf-8")
    return "OP-" + hashlib.sha256(raw).hexdigest()[:20]


def _parse_bound(match: re.Match[str]) -> float | None:
    if match.lastindex is None:
        return None
    raw = match.group(1)
    if raw is None:
        return None
    return float(raw)


def extract_semantic_operators(text: str, *, source: str = "source") -> list[SemanticOperator]:
    """Extract a conservative, non-overlapping set of explicit semantic operators."""
    if not isinstance(text, str) or not text:
        raise SemanticOperatorError("source text must be non-empty")
    if not isinstance(source, str) or not source.strip():
        raise SemanticOperatorError("source name must be non-empty")

    matches: list[tuple[int, int, int, str, re.Match[str]]] = []
    for priority, (semantic_class, pattern) in enumerate(_RULES):
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), priority, semantic_class, match))

    # Longest/specific rules win overlaps. Remaining ties use rule priority.
    matches.sort(key=lambda row: (row[0], -(row[1] - row[0]), row[2]))
    occupied: set[int] = set()
    accepted: list[SemanticOperator] = []
    for start, end, _priority, semantic_class, match in matches:
        positions = set(range(start, end))
        if positions & occupied:
            continue
        occupied.update(positions)
        raw = text[start:end]
        accepted.append(
            SemanticOperator(
                operator_id=_stable_id(source, start, end, semantic_class, raw),
                start=start,
                end=end,
                text=raw,
                semantic_class=semantic_class,
                bound_value=_parse_bound(match),
            )
        )
    accepted.sort(key=lambda op: (op.start, op.end, op.semantic_class))
    return accepted


def validate_operator_bindings(
    text: str,
    bindings: Sequence[Mapping[str, Any]],
    *,
    source: str = "source",
) -> dict[str, Any]:
    """Validate declared semantics against independently extracted explicit operators.

    A pair of extractors that both map "at least 3" to MAX_INCLUSIVE will fail here,
    even though they agree with each other.
    """
    operators = extract_semantic_operators(text, source=source)
    by_id = {op.operator_id: op for op in operators}
    errors: list[str] = []
    seen: set[str] = set()

    if not isinstance(bindings, Sequence) or isinstance(bindings, (str, bytes)):
        raise SemanticOperatorError("bindings must be a sequence")

    for index, binding in enumerate(bindings):
        if not isinstance(binding, Mapping):
            errors.append(f"BINDING_NOT_OBJECT:{index}")
            continue
        oid = str(binding.get("operator_id", ""))
        if not oid:
            errors.append(f"BINDING_OPERATOR_ID_MISSING:{index}")
            continue
        if oid in seen:
            errors.append(f"DUPLICATE_OPERATOR_BINDING:{oid}")
            continue
        seen.add(oid)
        op = by_id.get(oid)
        if op is None:
            errors.append(f"UNKNOWN_OPERATOR_BINDING:{oid}")
            continue

        claimed = str(binding.get("semantic_class", ""))
        if claimed != op.semantic_class:
            errors.append(
                f"SEMANTIC_OPERATOR_MISMATCH:{oid}:{claimed or 'MISSING'}!={op.semantic_class}"
            )

        if op.bound_value is not None:
            raw_bound = binding.get("bound_value")
            try:
                claimed_bound = float(raw_bound)
            except (TypeError, ValueError):
                errors.append(f"BOUND_VALUE_MISSING_OR_INVALID:{oid}")
            else:
                if claimed_bound != op.bound_value:
                    errors.append(
                        f"BOUND_VALUE_MISMATCH:{oid}:{claimed_bound}!={op.bound_value}"
                    )

        # "any" is context-sensitive. Treating it as a universal/existential fact
        # without explicit disambiguation is not allowed.
        if op.semantic_class == "AMBIGUOUS_ANY":
            interpretations = binding.get("interpretations")
            if not isinstance(interpretations, list) or len(interpretations) < 2:
                errors.append(f"AMBIGUOUS_ANY_WITHOUT_ALTERNATIVES:{oid}")

    missing = sorted(set(by_id) - seen)
    errors.extend(f"UNBOUND_EXPLICIT_SEMANTIC_OPERATOR:{oid}" for oid in missing)

    return {
        "schema": "BRAIN_EXPLICIT_SEMANTIC_OPERATOR_BINDING_VERDICT_V1",
        "pass": not errors,
        "operator_count": len(operators),
        "operators": [op.to_dict() for op in operators],
        "errors": sorted(set(errors)),
    }


def _obligation_id(operator_id: str, kind: str) -> str:
    return "CF-" + hashlib.sha256(f"{operator_id}\0{kind}".encode("utf-8")).hexdigest()[:20]


def generate_counterfactual_obligations(
    text: str,
    *,
    source: str = "source",
) -> list[CounterfactualObligation]:
    """Generate independent adversarial obligations implied by explicit operators."""
    out: list[CounterfactualObligation] = []
    for op in extract_semantic_operators(text, source=source):
        specs: list[tuple[str, str]] = []
        cls = op.semantic_class
        if cls == "MIN_INCLUSIVE":
            specs = [
                ("BOUNDARY_VALUE_MUST_BE_ACCEPTED", "value == bound is permitted"),
                ("BELOW_BOUND_MUST_BE_REJECTED", "value < bound is rejected"),
            ]
        elif cls == "MAX_INCLUSIVE":
            specs = [
                ("BOUNDARY_VALUE_MUST_BE_ACCEPTED", "value == bound is permitted"),
                ("ABOVE_BOUND_MUST_BE_REJECTED", "value > bound is rejected"),
            ]
        elif cls == "EXACT_VALUE":
            specs = [
                ("EXACT_VALUE_MUST_BE_ACCEPTED", "value == bound is permitted"),
                ("BELOW_EXACT_MUST_BE_REJECTED", "value < bound is rejected"),
                ("ABOVE_EXACT_MUST_BE_REJECTED", "value > bound is rejected"),
            ]
        elif cls == "PROHIBITION":
            specs = [
                ("PROHIBITED_ACTION_MUST_BE_REJECTED", "negated action cannot be admitted"),
            ]
        elif cls == "TEMPORAL_BEFORE":
            specs = [
                ("REVERSED_TEMPORAL_ORDER_MUST_BE_REJECTED", "after-order is not equivalent to before-order"),
            ]
        elif cls == "TEMPORAL_AFTER":
            specs = [
                ("REVERSED_TEMPORAL_ORDER_MUST_BE_REJECTED", "before-order is not equivalent to after-order"),
            ]
        elif cls == "UNIVERSAL_QUANTIFIER":
            specs = [
                ("SINGLE_COUNTEREXAMPLE_ITEM_MUST_FAIL_UNIVERSAL", "one violating member falsifies universal compliance"),
            ]
        elif cls == "AMBIGUOUS_ANY":
            specs = [
                ("ANY_SEMANTICS_MUST_BE_DISAMBIGUATED", "context-sensitive 'any' cannot be silently fixed to one quantifier"),
            ]
        elif cls == "EXCLUSIVITY":
            specs = [
                ("OUTSIDE_ALLOWED_SET_MUST_BE_REJECTED", "an alternative outside the exclusive set is not equivalent"),
            ]
        elif cls in {"CONDITIONAL_IF", "CONDITIONAL_WHEN"}:
            specs = [
                ("ANTECEDENT_TRUE_CONSEQUENT_FALSE_MUST_FAIL", "triggered condition cannot leave required consequence false"),
            ]
        elif cls == "CONDITIONAL_UNLESS":
            specs = [
                ("UNLESS_EXCEPTION_BRANCH_MUST_BE_DISTINGUISHED", "exception branch and ordinary branch must not collapse"),
            ]
        elif cls == "ALWAYS":
            specs = [
                ("SINGLE_EXCEPTION_MUST_FAIL_ALWAYS", "one counterexample falsifies always"),
            ]

        for kind, relation in specs:
            out.append(
                CounterfactualObligation(
                    obligation_id=_obligation_id(op.operator_id, kind),
                    operator_id=op.operator_id,
                    counterfactual_kind=kind,
                    semantic_class=op.semantic_class,
                    expected_relation=relation,
                    bound_value=op.bound_value,
                )
            )
    out.sort(key=lambda x: (x.operator_id, x.counterfactual_kind))
    return out


def validate_counterfactual_coverage(
    text: str,
    scenarios: Sequence[Mapping[str, Any]],
    *,
    source: str = "source",
) -> dict[str, Any]:
    """Require the acceptance plan to distinguish every operator counterfactual."""
    obligations = generate_counterfactual_obligations(text, source=source)
    required = {(o.operator_id, o.counterfactual_kind): o for o in obligations}
    observed: set[tuple[str, str]] = set()
    errors: list[str] = []

    if not isinstance(scenarios, Sequence) or isinstance(scenarios, (str, bytes)):
        raise SemanticOperatorError("scenarios must be a sequence")

    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, Mapping):
            errors.append(f"COUNTERFACTUAL_SCENARIO_NOT_OBJECT:{index}")
            continue
        oid = str(scenario.get("operator_id", ""))
        kind = str(scenario.get("counterfactual_kind", ""))
        key = (oid, kind)
        if key not in required:
            errors.append(f"UNKNOWN_COUNTERFACTUAL_SCENARIO:{oid}:{kind}")
            continue
        if key in observed:
            errors.append(f"DUPLICATE_COUNTERFACTUAL_SCENARIO:{oid}:{kind}")
        observed.add(key)

        # A scenario must have an independently observable expected disposition.
        disposition = str(scenario.get("expected_disposition", ""))
        if disposition not in {"ACCEPT", "REJECT", "DISAMBIGUATE"}:
            errors.append(f"COUNTERFACTUAL_DISPOSITION_INVALID:{oid}:{kind}")

    for key, obligation in required.items():
        if key not in observed:
            errors.append(
                f"MISSING_SEMANTIC_COUNTERFACTUAL:{obligation.operator_id}:{obligation.counterfactual_kind}"
            )

    return {
        "schema": "BRAIN_EXPLICIT_SEMANTIC_COUNTERFACTUAL_COVERAGE_V1",
        "pass": not errors,
        "required_count": len(obligations),
        "obligations": [o.to_dict() for o in obligations],
        "errors": sorted(set(errors)),
    }


def compile_explicit_operator_contract(
    text: str,
    *,
    bindings: Sequence[Mapping[str, Any]],
    scenarios: Sequence[Mapping[str, Any]],
    source: str = "source",
) -> dict[str, Any]:
    bindings_result = validate_operator_bindings(text, bindings, source=source)
    counterfactual_result = validate_counterfactual_coverage(text, scenarios, source=source)
    return {
        "schema": "BRAIN_EXPLICIT_SEMANTIC_OPERATOR_CONTRACT_V1",
        "pass": bool(bindings_result["pass"] and counterfactual_result["pass"]),
        "binding_verdict": bindings_result,
        "counterfactual_verdict": counterfactual_result,
        "claim_scope": "EXPLICIT_LEXICAL_SEMANTIC_OPERATORS_ONLY",
    }
