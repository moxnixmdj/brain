"""Source-aligned semantic entailment checker V1.

This is a deliberately small trusted fragment for proving directional semantic
relations from exact source spans. It does not infer relations from embeddings,
LLM confidence, lexical similarity, or an unverified whole-document parse.

Each proposed proof span is content-addressed and must exactly match one bounded
relation grammar. The checker recomputes the primitive relation, composes only
transitive inclusion/equivalence edges, and treats exact counterexamples as
load-bearing falsifiers.

The result proves entailment only relative to the supplied source spans and scope.
Source factual authority is separate from source-text entailment.
"""
from __future__ import annotations

from collections import deque
from hashlib import sha256
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph

SCHEMA = "PROJECT_BRAIN_SOURCE_ALIGNED_SEMANTIC_ENTAILMENT_V1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_RELATIONS = {
    "ANY_DIRECTIONAL_RELATION",
    "LEFT_ENTAILS_RIGHT",
    "RIGHT_ENTAILS_LEFT",
    "LOGICAL_EQUIVALENCE_IN_SCOPE",
}

_TERM = r"[A-Za-z][A-Za-z0-9 _/\-]{0,100}?"
_RULES = (
    (
        "LEFT_ENTAILS_RIGHT",
        re.compile(
            rf"^Every\s+(?P<left>{_TERM})\s+is\s+(?:a\s+|an\s+|the\s+)?(?P<right>{_TERM})$",
            re.I,
        ),
    ),
    (
        "LEFT_ENTAILS_RIGHT",
        re.compile(
            rf"^All\s+(?P<left>{_TERM})\s+are\s+(?:a\s+|an\s+|the\s+)?(?P<right>{_TERM})$",
            re.I,
        ),
    ),
    (
        "LEFT_ENTAILS_RIGHT",
        re.compile(
            rf"^(?P<left>{_TERM})\s+is\s+(?:a\s+|an\s+)?(?:type|kind|subtype|subset|form)\s+of\s+(?P<right>{_TERM})$",
            re.I,
        ),
    ),
)
_COUNTEREXAMPLES = (
    re.compile(
        rf"^Some\s+(?P<left>{_TERM})\s+(?:is|are)\s+not\s+(?:a\s+|an\s+|the\s+)?(?P<right>{_TERM})$",
        re.I,
    ),
    re.compile(
        rf"^At\s+least\s+one\s+(?P<left>{_TERM})\s+is\s+not\s+(?:a\s+|an\s+|the\s+)?(?P<right>{_TERM})$",
        re.I,
    ),
)


class SemanticEntailmentError(ValueError):
    pass


def _norm(value: Any) -> str:
    text = " ".join(str(value if value is not None else "").strip().split())
    return text.strip(" \t\r\n\"'").casefold()


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _stable_atom_id(source_id: str, span_sha256: str, kind: str, left: str, right: str) -> str:
    raw = f"{source_id}\0{span_sha256}\0{kind}\0{left}\0{right}".encode("utf-8")
    return "SEMREL-" + sha256(raw).hexdigest()[:20]


def _strip_sentence(text: str) -> str:
    return " ".join(text.strip().split()).rstrip(".!?").strip()


def _parse_span(source_id: str, span_text: str, span_sha256: str) -> list[dict[str, Any]]:
    sentence = _strip_sentence(span_text)
    if not sentence:
        raise SemanticEntailmentError("EMPTY_SOURCE_SPAN:" + source_id)

    # Reuse the existing exact definition compiler first. An exact source
    # declaration is bidirectional inside the declared source scope.
    graph = compile_reference_graph(span_text)
    if graph.get("status") == "COMPILED":
        definitions = [
            row for row in graph.get("definitions", [])
            if isinstance(row, Mapping)
        ]
        if definitions:
            if len(definitions) != 1:
                raise SemanticEntailmentError(
                    "SOURCE_SPAN_MUST_BIND_EXACTLY_ONE_RELATION:" + source_id
                )
            row = definitions[0]
            left = _norm(row.get("term"))
            right = _norm(row.get("definition"))
            if not left or not right:
                raise SemanticEntailmentError("DEFINITION_TERMS_INVALID:" + source_id)
            atom_id = _stable_atom_id(
                source_id, span_sha256, "EXACT_EQUIVALENCE", left, right
            )
            return [{
                "atom_id": atom_id,
                "kind": "EXACT_EQUIVALENCE",
                "left": left,
                "right": right,
                "source_id": source_id,
                "span_sha256": span_sha256,
            }]

    for pattern in _COUNTEREXAMPLES:
        match = pattern.fullmatch(sentence)
        if match:
            left = _norm(match.group("left"))
            right = _norm(match.group("right"))
            atom_id = _stable_atom_id(
                source_id, span_sha256, "COUNTEREXAMPLE_LEFT_NOT_RIGHT", left, right
            )
            return [{
                "atom_id": atom_id,
                "kind": "COUNTEREXAMPLE_LEFT_NOT_RIGHT",
                "left": left,
                "right": right,
                "source_id": source_id,
                "span_sha256": span_sha256,
            }]

    for kind, pattern in _RULES:
        match = pattern.fullmatch(sentence)
        if match:
            left = _norm(match.group("left"))
            right = _norm(match.group("right"))
            atom_id = _stable_atom_id(source_id, span_sha256, kind, left, right)
            return [{
                "atom_id": atom_id,
                "kind": kind,
                "left": left,
                "right": right,
                "source_id": source_id,
                "span_sha256": span_sha256,
            }]

    raise SemanticEntailmentError(
        "SOURCE_SPAN_OUTSIDE_CHECKED_RELATION_GRAMMAR:" + source_id
    )


def _path(
    start: str,
    target: str,
    adjacency: Mapping[str, list[tuple[str, str]]],
) -> list[str] | None:
    if start == target:
        return []
    queue = deque([(start, [])])
    seen = {start}
    while queue:
        node, proof = queue.popleft()
        for nxt, atom_id in sorted(adjacency.get(node, [])):
            if nxt in seen:
                continue
            candidate = proof + [atom_id]
            if nxt == target:
                return candidate
            seen.add(nxt)
            queue.append((nxt, candidate))
    return None


def prove(problem: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            raise SemanticEntailmentError("PROBLEM_NOT_OBJECT")
        allowed = {
            "left_surface",
            "right_surface",
            "scope_id",
            "required_relation",
            "source_spans",
        }
        extra = set(problem) - allowed
        if extra:
            raise SemanticEntailmentError(
                "UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra))
            )

        left = _norm(problem.get("left_surface"))
        right = _norm(problem.get("right_surface"))
        scope_id = str(problem.get("scope_id") or "").strip()
        required = str(problem.get("required_relation") or "").strip().upper()
        spans = problem.get("source_spans")

        if not left or not right or left == right:
            raise SemanticEntailmentError("DISTINCT_LEFT_RIGHT_SURFACES_REQUIRED")
        if not scope_id:
            raise SemanticEntailmentError("SCOPE_ID_REQUIRED")
        if required not in REQUIRED_RELATIONS:
            raise SemanticEntailmentError("REQUIRED_RELATION_INVALID")
        if (
            not isinstance(spans, Sequence)
            or isinstance(spans, (str, bytes))
            or not spans
        ):
            raise SemanticEntailmentError("SOURCE_SPANS_REQUIRED")

        atoms: list[dict[str, Any]] = []
        seen_span_ids: set[tuple[str, str]] = set()
        for i, raw in enumerate(spans):
            if not isinstance(raw, Mapping):
                raise SemanticEntailmentError(f"SOURCE_SPAN_NOT_OBJECT:{i}")
            allowed_span = {"source_id", "scope_id", "span_text", "span_sha256"}
            extra_span = set(raw) - allowed_span
            if extra_span:
                raise SemanticEntailmentError(
                    f"UNMODELED_SOURCE_SPAN_FIELDS:{i}:"
                    + ",".join(sorted(str(x) for x in extra_span))
                )
            source_id = str(raw.get("source_id") or "").strip()
            row_scope = str(raw.get("scope_id") or "").strip()
            span_text = raw.get("span_text")
            span_sha256 = str(raw.get("span_sha256") or "").lower()

            if not source_id:
                raise SemanticEntailmentError(f"SOURCE_ID_REQUIRED:{i}")
            if row_scope != scope_id:
                raise SemanticEntailmentError(
                    f"SOURCE_SCOPE_MISMATCH:{source_id}"
                )
            if not isinstance(span_text, str) or not span_text.strip():
                raise SemanticEntailmentError(
                    f"SOURCE_SPAN_TEXT_REQUIRED:{source_id}"
                )
            if not _SHA256.fullmatch(span_sha256):
                raise SemanticEntailmentError(
                    f"SOURCE_SPAN_SHA256_INVALID:{source_id}"
                )
            if _digest(span_text) != span_sha256:
                raise SemanticEntailmentError(
                    f"SOURCE_SPAN_SHA256_MISMATCH:{source_id}"
                )
            span_key = (source_id, span_sha256)
            if span_key in seen_span_ids:
                raise SemanticEntailmentError(
                    f"DUPLICATE_SOURCE_SPAN:{source_id}:{span_sha256}"
                )
            seen_span_ids.add(span_key)
            atoms.extend(_parse_span(source_id, span_text, span_sha256))

        adjacency: dict[str, list[tuple[str, str]]] = {}
        counterexamples: dict[tuple[str, str], list[str]] = {}
        for atom in atoms:
            kind = atom["kind"]
            a = atom["left"]
            b = atom["right"]
            aid = atom["atom_id"]
            if kind == "EXACT_EQUIVALENCE":
                adjacency.setdefault(a, []).append((b, aid))
                adjacency.setdefault(b, []).append((a, aid))
            elif kind == "LEFT_ENTAILS_RIGHT":
                adjacency.setdefault(a, []).append((b, aid))
            elif kind == "COUNTEREXAMPLE_LEFT_NOT_RIGHT":
                counterexamples.setdefault((a, b), []).append(aid)
            else:
                raise SemanticEntailmentError("UNKNOWN_ATOM_KIND:" + str(kind))

        left_path = _path(left, right, adjacency)
        right_path = _path(right, left, adjacency)
        left_counter = sorted(counterexamples.get((left, right), []))
        right_counter = sorted(counterexamples.get((right, left), []))

        conflicts = []
        if left_path is not None and left_counter:
            conflicts.append("LEFT_TO_RIGHT_PROOF_AND_COUNTEREXAMPLE")
        if right_path is not None and right_counter:
            conflicts.append("RIGHT_TO_LEFT_PROOF_AND_COUNTEREXAMPLE")
        if conflicts:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__SEMANTIC_RELATION_EVIDENCE_CONFLICT",
                "scope_id": scope_id,
                "left_surface": left,
                "right_surface": right,
                "conflicts": conflicts,
                "left_to_right_proof_atom_ids": left_path,
                "right_to_left_proof_atom_ids": right_path,
                "left_to_right_counterexample_atom_ids": left_counter,
                "right_to_left_counterexample_atom_ids": right_counter,
                "atoms": atoms,
                "source_authority_is_separate_from_source_text_entailment": True,
                "semantic_truth_authority": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

        left_entails = left_path is not None and not left_counter
        right_entails = right_path is not None and not right_counter
        logical_equivalence = left_entails and right_entails

        if logical_equivalence:
            strongest = "LOGICAL_EQUIVALENCE_IN_SCOPE"
        elif left_entails:
            strongest = "LEFT_ENTAILS_RIGHT"
        elif right_entails:
            strongest = "RIGHT_ENTAILS_LEFT"
        elif left_counter and right_counter:
            strongest = "BIDIRECTIONAL_NONENTAILMENT_WITNESSED"
        elif left_counter:
            strongest = "LEFT_ENTAILS_RIGHT_DISPROVED"
        elif right_counter:
            strongest = "RIGHT_ENTAILS_LEFT_DISPROVED"
        else:
            strongest = "UNKNOWN"

        if required == "LOGICAL_EQUIVALENCE_IN_SCOPE":
            satisfied = logical_equivalence
        elif required == "LEFT_ENTAILS_RIGHT":
            satisfied = left_entails
        elif required == "RIGHT_ENTAILS_LEFT":
            satisfied = right_entails
        else:
            satisfied = strongest != "UNKNOWN"

        return {
            "schema": SCHEMA,
            "pass": satisfied,
            "status": (
                "PASS__SOURCE_ALIGNED_SEMANTIC_RELATION_PROVED"
                if satisfied
                else "OPEN__REQUIRED_SEMANTIC_RELATION_NOT_PROVED"
            ),
            "scope_id": scope_id,
            "left_surface": left,
            "right_surface": right,
            "required_relation": required,
            "strongest_proved_relation": strongest,
            "proved_facts": {
                "left_entails_right": left_entails,
                "right_entails_left": right_entails,
                "logical_equivalence_in_scope": logical_equivalence,
                "left_entails_right_disproved": bool(left_counter),
                "right_entails_left_disproved": bool(right_counter),
            },
            "left_to_right_proof_atom_ids": left_path,
            "right_to_left_proof_atom_ids": right_path,
            "left_to_right_counterexample_atom_ids": left_counter,
            "right_to_left_counterexample_atom_ids": right_counter,
            "atoms": atoms,
            "checked_fragment": [
                "EXACT_SOURCE_DECLARED_EQUIVALENCE",
                "EVERY_X_IS_Y",
                "ALL_X_ARE_Y",
                "X_IS_A_TYPE_KIND_SUBTYPE_SUBSET_OR_FORM_OF_Y",
                "SOME_X_IS_NOT_Y",
                "AT_LEAST_ONE_X_IS_NOT_Y",
                "TRANSITIVE_ENTAILMENT_COMPOSITION",
            ],
            "candidate_similarity_authority": False,
            "source_authority_is_separate_from_source_text_entailment": True,
            "semantic_truth_authority": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "hard_nonclaim": (
                "THIS_CHECKER_PROVES_ONLY_THE_BOUNDED_SOURCE_ALIGNED_FRAGMENT;"
                "OUT_OF_GRAMMAR_OR_UNAUTHENTICATED_SOURCE_TRUTH_REMAINS_SEPARATE"
            ),
        }
    except SemanticEntailmentError as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": str(exc),
            "semantic_truth_authority": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
