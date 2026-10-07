"""Bounded source-bound request/complement semantics.

This module recognizes a narrow family of explicit task directives that are
declarative in surface form and therefore missed by imperative-head parsing.

It proves only that the source explicitly assigns/requires an action phrase to
the addressee. The action tail remains opaque. No coordination splitting,
pronoun resolution, world knowledge, whole-task completeness, or policy
adequacy is inferred.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

SCHEMA = "BRAIN_BOUNDED_REQUEST_COMPLEMENT_SEMANTICS_V1"

_ACTION = r"[A-Za-z][A-Za-z-]*"
_LIST = re.compile(r"^\s*(?:[-*•]+\s*|\d+[.)]\s*)?")
_SECOND_PERSON = re.compile(
    rf"^(?P<prefix>you\s+(?:should|will|need\s+to|will\s+need\s+to|are\s+required\s+to))\s+"
    rf"(?P<verb>{_ACTION})\b(?P<tail>.+)$",
    re.I,
)
_REQUESTED_THAT_YOU = re.compile(
    rf"^(?P<requester>.+?)\s+(?:has\s+|have\s+)?requested\s+that\s+you\s+"
    rf"(?P<verb>{_ACTION})\b(?P<tail>.+)$",
    re.I,
)
_ASKED_TO = re.compile(
    rf"^(?:(?:you(?:'|’)ve|you\s+have)\s+been\s+asked\s+to|"
    rf"(?P<requester>.+?)\s+(?:has\s+|have\s+)?asked\s+you\s+to)\s+"
    rf"(?P<verb>{_ACTION})\b(?P<tail>.+)$",
    re.I,
)
_WOULD_LIKE = re.compile(
    rf"^(?P<requester>.+?)\s+would\s+like\s+you\s+to\s+"
    rf"(?P<verb>{_ACTION})\b(?P<tail>.+)$",
    re.I,
)
_TASKED_WITH = re.compile(
    rf"^you\s+(?:are|were|'re|’re)\s+tasked\s+with\s+"
    rf"(?P<action>{_ACTION}(?:ing)?)\b(?P<tail>.+)$",
    re.I,
)
_USING_CONTEXT = re.compile(
    rf"^using\s+(?P<context>.+?),\s*(?P<verb>{_ACTION})\b(?P<tail>.+)$",
    re.I,
)
_PLEASE = re.compile(
    rf"^please\s+(?P<verb>{_ACTION})\b(?P<tail>.+)$",
    re.I,
)
_BARE_BULLET = re.compile(
    rf"^(?P<verb>{_ACTION})\b(?P<tail>.+)$",
    re.I,
)

# Closed action set. These are only admitted as explicit task actions under one
# of the source-bound constructions above.
VERBS = frozenset("""
account add analyze apply assess build calculate capture cite compare compile
complete conduct copy create define deliver describe design determine develop
document draft edit ensure estimate evaluate explain extract fill forecast
format generate highlight identify include incorporate list make mix model
organize outline perform prepare present produce provide recommend report
research review save select show summarize update use validate verify write
""".split())

_TRAIL = re.compile(r"[.!?]+\s*$")


def _trim(text: str) -> str:
    return _TRAIL.sub("", text).rstrip()


def _fail(status: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "terminal_authority": False,
        "semantic_completeness_claim": False,
    }


def _emit(source: str, *, construction: str, verb: str, action_text: str,
          context_text: str | None = None, requester_text: str | None = None) -> dict[str, Any]:
    verb_l = verb.lower()
    if verb_l not in VERBS:
        return _fail("UNRESOLVED", "ACTION_VERB_OUTSIDE_CERTIFIED_SET")
    action_text = _trim(action_text.strip())
    if not action_text:
        return _fail("FAIL_CLOSED", "ACTION_TEXT_EMPTY")

    first = source.find(action_text)
    if first < 0 or source.find(action_text, first + 1) >= 0:
        return _fail("FAIL_CLOSED", "ACTION_TEXT_SOURCE_BINDING_NOT_UNIQUE")

    out = {
        "schema": SCHEMA,
        "status": "RESOLVED_ONE_SIDED_REQUEST_COMPLEMENT",
        "construction": construction,
        "directive": {
            "actor": "ADDRESSEE",
            "predicate": verb_l,
            "action_text": action_text,
            "action_span": [first, first + len(action_text)],
            "modality": "REQUIRED",
            "polarity": "REQUIRED",
            "argument_semantics_resolved": False,
            "coordination_split": False,
        },
        "source_text": source,
        "source_sha256": sha256(source.encode("utf-8")).hexdigest(),
        "terminal_authority": False,
        "semantic_completeness_claim": False,
        "soundness_boundary": (
            "PROVES_ONLY_EXPLICIT_SOURCE_ASSIGNED_ACTION_PHRASE_TO_ADDRESSEE;"
            "ACTION_TAIL_REMAINS_OPAQUE;"
            "NO_WHOLE_TASK_SEMANTICS_OR_POLICY_ADEQUACY"
        ),
    }
    if context_text is not None:
        c = context_text.strip()
        pos = source.find(c)
        if pos < 0 or source.find(c, pos + 1) >= 0:
            return _fail("FAIL_CLOSED", "CONTEXT_SOURCE_BINDING_NOT_UNIQUE")
        out["context"] = {
            "text": c,
            "span": [pos, pos + len(c)],
            "semantic_resolution": "RAW_SOURCE_BOUND_CONTEXT_ONLY",
        }
    if requester_text is not None:
        r = requester_text.strip()
        if r:
            pos = source.find(r)
            if pos >= 0 and source.find(r, pos + 1) < 0:
                out["requester"] = {"text": r, "span": [pos, pos + len(r)]}
    return out


def parse_request_complement(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return _fail("FAIL_CLOSED", "EMPTY_SOURCE")

    source = text
    core = source.strip()
    # Permit bullets with or without a space after the marker.
    lm = _LIST.match(core)
    had_list = bool(lm and lm.group(0))
    if lm:
        core = core[lm.end():].strip()

    m = _SECOND_PERSON.match(core)
    if m:
        verb = m.group("verb")
        action = verb + m.group("tail")
        return _emit(source, construction="SECOND_PERSON_EXPLICIT_OBLIGATION",
                     verb=verb, action_text=_trim(action))

    m = _REQUESTED_THAT_YOU.match(core)
    if m:
        verb = m.group("verb")
        action = verb + m.group("tail")
        return _emit(source, construction="REQUESTED_THAT_YOU",
                     verb=verb, action_text=_trim(action),
                     requester_text=m.group("requester"))

    m = _ASKED_TO.match(core)
    if m:
        verb = m.group("verb")
        action = verb + m.group("tail")
        return _emit(source, construction="ASKED_YOU_TO",
                     verb=verb, action_text=_trim(action),
                     requester_text=m.groupdict().get("requester"))

    m = _WOULD_LIKE.match(core)
    if m:
        verb = m.group("verb")
        action = verb + m.group("tail")
        return _emit(source, construction="WOULD_LIKE_YOU_TO",
                     verb=verb, action_text=_trim(action),
                     requester_text=m.group("requester"))

    m = _TASKED_WITH.match(core)
    if m:
        surface = m.group("action")
        # Keep the surface action exact; only accept if a conservative stem is in
        # the closed verb set. This is not general lemmatization.
        candidates = [surface.lower()]
        if surface.lower().endswith("ing") and len(surface) > 4:
            stem = surface[:-3].lower()
            candidates.extend([stem, stem + "e"])
        verb = next((v for v in candidates if v in VERBS), None)
        if verb is None:
            return _fail("UNRESOLVED", "TASKED_WITH_ACTION_OUTSIDE_CERTIFIED_SET")
        action = surface + m.group("tail")
        return _emit(source, construction="TASKED_WITH",
                     verb=verb, action_text=_trim(action))

    m = _USING_CONTEXT.match(core)
    if m:
        verb = m.group("verb")
        action = verb + m.group("tail")
        return _emit(source, construction="USING_CONTEXT_IMPERATIVE",
                     verb=verb, action_text=_trim(action),
                     context_text=m.group("context"))

    m = _PLEASE.match(core)
    if m:
        verb = m.group("verb")
        action = verb + m.group("tail")
        return _emit(source, construction="PLEASE_IMPERATIVE",
                     verb=verb, action_text=_trim(action))

    # Bare action heads are admitted only when an explicit list marker was
    # present. This covers source bullets like "-Conduct research..." without
    # turning arbitrary declarative sentences into directives.
    if had_list:
        m = _BARE_BULLET.match(core)
        if m:
            verb = m.group("verb")
            action = verb + m.group("tail")
            return _emit(source, construction="BULLET_IMPERATIVE",
                         verb=verb, action_text=_trim(action))

    return _fail("UNRESOLVED", "OUTSIDE_BOUNDED_REQUEST_COMPLEMENT_GRAMMAR")
