"""One-sided source-aligned semantics for explicit imperative task directives.

This parser owns a deliberately narrow fact: a source segment explicitly begins
with a known imperative action verb and therefore contains a directive headed by
that verb over the exact remaining source tail.

It does NOT split coordinated/nested clauses, infer hidden arguments, identify
topics/audience/evidence, or claim that the directive tail is semantically
complete. The tail is preserved opaquely so partial extraction cannot invent
meaning.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "BRAIN_BOUNDED_TASK_DIRECTIVE_SEMANTICS_V1"

ACTION_VERBS = frozenset({
    "add","address","analyze","apply","assess","build","calculate","capture",
    "compare","compile","complete","consider","construct","copy","create",
    "define","deliver","describe","design","determine","develop","document",
    "draft","ensure","estimate","evaluate","explain","extract","fill","forecast",
    "format","generate","highlight","identify","include","incorporate","list",
    "make","model","organize","outline","perform","prepare","present","produce",
    "provide","recommend","report","research","review","select","show",
    "summarize","update","use","validate","verify","write",
})
_LIST = re.compile(r"^(?P<marker>(?:[-*•]\s+|\d+[.)]\s+))")
_HEAD = re.compile(r"^(?P<verb>[A-Za-z][A-Za-z-]*)\b(?P<tail>.*)$")
_TRAILING_PERIOD = re.compile(r"[.]\s*$")


def _fail(status: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "terminal_authority": False,
        "semantic_completeness_claim": False,
    }


def parse_directive(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return _fail("FAIL_CLOSED", "EMPTY_SOURCE")

    left = len(text) - len(text.lstrip())
    work = text[left:]
    marker_span = None

    m = _LIST.match(work)
    if m:
        marker_span = [left + m.start("marker"), left + m.end("marker")]
        left += m.end("marker")
        work = work[m.end("marker"):]

    if work.lower().startswith("please "):
        left += 7
        work = work[7:]

    hm = _HEAD.match(work)
    if not hm:
        return _fail("UNRESOLVED", "NO_DIRECTIVE_HEAD")

    verb_raw = hm.group("verb")
    verb = verb_raw.lower()
    if verb not in ACTION_VERBS:
        return _fail("UNRESOLVED", "DIRECTIVE_VERB_OUTSIDE_BOUND_SET")

    tail_raw = hm.group("tail")
    tail_leading = len(tail_raw) - len(tail_raw.lstrip())
    tail = tail_raw.strip()
    if not tail:
        return _fail("FAIL_CLOSED", "DIRECTIVE_TAIL_EMPTY")

    if tail.endswith(":"):
        return _fail("UNRESOLVED", "DIRECTIVE_REQUIRES_CONTINUATION_BINDING")
    if ";" in tail:
        return _fail("UNRESOLVED", "SEMICOLON_MULTI_CLAUSE_NOT_BOUND")

    # Remove only terminal sentence punctuation from the opaque tail. No clause
    # splitting or argument interpretation occurs.
    tail_clean = _TRAILING_PERIOD.sub("", tail).rstrip()
    if not tail_clean:
        return _fail("FAIL_CLOSED", "DIRECTIVE_TAIL_EMPTY_AFTER_PUNCTUATION")

    verb_start = left + hm.start("verb")
    tail_start = left + hm.start("tail") + tail_leading
    # Bind the exact cleaned tail by locating it at the computed tail start.
    if text[tail_start:tail_start + len(tail_clean)] != tail_clean:
        return _fail("FAIL_CLOSED", "SOURCE_SPAN_BINDING_FAILED")

    out = {
        "schema": SCHEMA,
        "status": "RESOLVED_ONE_SIDED_DIRECTIVE_HEAD",
        "directive": {
            "action": verb,
            "action_span": [verb_start, verb_start + len(verb_raw)],
            "directive_tail": tail_clean,
            "directive_tail_span": [tail_start, tail_start + len(tail_clean)],
            "implicit_addressee": "GRAMMATICAL_IMPERATIVE_ADDRESSEE",
            "tail_semantics": "OPAQUE_SOURCE_BOUND",
        },
        "terminal_authority": False,
        "semantic_completeness_claim": False,
        "coordination_split_performed": False,
        "hidden_argument_inference_performed": False,
        "scope": "FINITE_EXPLICIT_IMPERATIVE_ACTION_HEADS_WITH_OPAQUE_SOURCE_BOUND_TAIL",
    }
    if marker_span is not None:
        out["list_marker_span"] = marker_span
    return out
