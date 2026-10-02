"""Bounded deterministic contextual-reference proposal operators for M0A.

This module does not claim general natural-language semantics.  It recognizes a
small set of structurally identifiable contextual forms and emits exact
source-span proposals for the independent M0A semantic consensus gate.

Unsupported or multiply interpretable forms remain explicit unresolved holes.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "BRAIN_CONTEXTUAL_REFERENCE_OPERATORS_V1"
ROUTE_ID = "brain_contextual_reference_operators_v1"
INDEPENDENCE_GROUP = "brain_deterministic_structural_context"

_MODAL = r"(?:shall|must)"
_SENTENCE = re.compile(r"[^.!?]+[.!?]?", re.S)


def _sentences(source: str) -> list[tuple[int, int, str]]:
    rows = []
    for m in _SENTENCE.finditer(source):
        raw = m.group(0)
        if not raw.strip():
            continue
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        rows.append((m.start() + left, m.start() + right, raw[left:right]))
    return rows


def _abs_span(sentence_start: int, match: re.Match[str], group: str) -> list[int]:
    return [sentence_start + match.start(group), sentence_start + match.end(group)]


def _proposal() -> dict[str, Any]:
    return {
        "route_id": ROUTE_ID,
        "independence_group": INDEPENDENCE_GROUP,
        "bindings": [],
        "relations": [],
        "obligations": [],
    }


def propose_contextual_references(source: str) -> dict[str, Any]:
    if not isinstance(source, str) or not source.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["EMPTY_SOURCE"]}

    proposal = _proposal()
    unresolved: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    sents = _sentences(source)

    # 1) Bounded cross-sentence subject pronoun continuation.
    # Previous sentence must expose exactly one modal subject. "They" requires an
    # explicit conjunction in that subject; "It" requires no conjunction.
    for i in range(1, len(sents)):
        pstart, _, prev = sents[i - 1]
        cstart, _, cur = sents[i]
        pm = re.match(
            rf"(?P<subject>(?:The|A|An)\s+.+?)\s+{_MODAL}\b",
            prev,
            re.I,
        )
        cm = re.match(
            rf"(?P<pron>It|They)\s+{_MODAL}\b",
            cur,
            re.I,
        )
        if pm and cm:
            subject = pm.group("subject")
            pron = cm.group("pron").casefold()
            plural = bool(re.search(r"\band\b", subject, re.I))
            number_ok = (pron == "they" and plural) or (pron == "it" and not plural)
            if number_ok:
                proposal["bindings"].append({
                    "mention_span": _abs_span(cstart, cm, "pron"),
                    "target_span": _abs_span(pstart, pm, "subject"),
                    "kind": "subject_pronoun_continuation",
                })
            else:
                unresolved.append({
                    "type": "PRONOUN_NUMBER_MISMATCH_OR_UNSUPPORTED",
                    "sentence_index": i,
                })

    # 2) Explicit "that mode" anaphora from a preceding "X mode is enabled".
    mode_targets = list(re.finditer(
        r"\bIf\s+(?P<target>(?:the\s+)?[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,3}\s+mode)\s+is\s+enabled",
        source,
        re.I,
    ))
    mode_mentions = list(re.finditer(r"(?P<mention>that\s+mode)\b", source, re.I))
    for mention in mode_mentions:
        prior = [m for m in mode_targets if m.end("target") <= mention.start("mention")]
        if len(prior) == 1:
            target = prior[0]
            proposal["bindings"].append({
                "mention_span": [mention.start("mention"), mention.end("mention")],
                "target_span": [target.start("target"), target.end("target")],
                "kind": "explicit_mode_anaphora",
            })
        elif len(prior) > 1:
            unresolved.append({
                "type": "MULTIPLE_MODE_ANTECEDENTS",
                "mention_span": [mention.start("mention"), mention.end("mention")],
            })

    # 3) Bounded predicate ellipsis: "A must P. B must, too."
    for i in range(1, len(sents)):
        pstart, _, prev = sents[i - 1]
        cstart, _, cur = sents[i]
        pm = re.match(
            r"(?P<subject>.+?)\s+(?P<modal>must|shall)\s+(?P<predicate>[^.!?]+?)[.!?]?$",
            prev,
            re.I,
        )
        cm = re.match(
            r"(?P<subject>.+?)\s+(?P<modal>must|shall)\s*,?\s*too\s*[.!?]?$",
            cur,
            re.I,
        )
        if pm and cm and pm.group("modal").casefold() == cm.group("modal").casefold():
            proposal["obligations"].append({
                "subject_span": _abs_span(cstart, cm, "subject"),
                "predicate_span": _abs_span(pstart, pm, "predicate"),
                "modality": cm.group("modal").casefold(),
            })

    # 4) Explicit two-by-two "respectively" mapping.
    # Deliberately bounded to short noun/object spans and one shared verb.
    resp = re.compile(
        r"(?P<s1>(?:The\s+)?[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2})"
        r"\s+and\s+"
        r"(?P<s2>(?:the\s+)?[A-Za-z][A-Za-z0-9_-]*(?:\s+[A-Za-z][A-Za-z0-9_-]*){0,2})"
        r"\s+(?P<modal>shall|must)\s+"
        r"(?P<verb>[A-Za-z][A-Za-z0-9_-]*)\s+"
        r"(?P<o1>[A-Za-z0-9_.:/-]+)\s+and\s+(?P<o2>[A-Za-z0-9_.:/-]+)"
        r"\s*,\s*respectively\b",
        re.I,
    )
    for m in resp.finditer(source):
        modality = m.group("modal").casefold()
        verb_span = [m.start("verb"), m.end("verb")]
        proposal["obligations"].extend([
            {
                "subject_span": [m.start("s1"), m.end("s1")],
                "predicate_span": verb_span,
                "object_span": [m.start("o1"), m.end("o1")],
                "modality": modality,
            },
            {
                "subject_span": [m.start("s2"), m.end("s2")],
                "predicate_span": verb_span,
                "object_span": [m.start("o2"), m.end("o2")],
                "modality": modality,
            },
        ])
        proposal["relations"].append({
            "left_span": [m.start("s1"), m.end("s1")],
            "right_span": [m.start("o1"), m.end("o1")],
            "kind": "respectively_pair_1",
        })
        proposal["relations"].append({
            "left_span": [m.start("s2"), m.end("s2")],
            "right_span": [m.start("o2"), m.end("o2")],
            "kind": "respectively_pair_2",
        })

    # 5) former/latter is only safe when there is one uniquely identified pair.
    # We intentionally do not guess here. Existing real examples can contain
    # multiple salient subject/object pairs.
    for m in re.finditer(r"\b(?:former|latter)\b", source, re.I):
        unresolved.append({
            "type": "FORMER_LATTER_REQUIRES_UNIQUE_PAIR_GRAPH",
            "mention_span": [m.start(), m.end()],
        })

    # 6) Demonstrative event phrases need event-type semantics, not mere string
    # reference. Preserve the hole unless another independent route supplies it.
    for m in re.finditer(r"\b(?:This|That)\s+(?:validation|operation|action|process|step|event)\b", source):
        unresolved.append({
            "type": "DEMONSTRATIVE_EVENT_REFERENCE_REQUIRES_EVENT_SEMANTICS",
            "mention_span": [m.start(), m.end()],
        })

    if proposal["bindings"] or proposal["relations"] or proposal["obligations"]:
        status = "PROPOSED_WITH_UNRESOLVED" if unresolved else "PROPOSED"
    else:
        status = "UNRESOLVED" if unresolved else "NO_BOUNDED_PATTERN"

    return {
        "schema": SCHEMA,
        "status": status,
        "proposal": proposal,
        "unresolved": unresolved,
        "diagnostics": diagnostics,
        "terminal_authority": False,
        "scope": [
            "BOUNDED_CROSS_SENTENCE_SUBJECT_PRONOUN_CONTINUATION",
            "EXPLICIT_THAT_MODE_ANAPHORA",
            "BOUNDED_MODAL_ELLIPSIS_TOO",
            "EXPLICIT_TWO_BY_TWO_RESPECTIVELY_MAPPING",
        ],
    }
