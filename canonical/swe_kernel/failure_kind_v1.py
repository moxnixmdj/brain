"""What KIND of failure is this? A classifier over the text the run already produced.

Why this exists (pass twelve): the screen can now report what a candidate saw, and the first obvious
use of it -- ranking candidates by distance from the expected value -- was measured to be WORSE than
blind ordering in 4 of 6 shapes, by up to 13 probes. Output distance is not structural distance.

The signal that is structural is the failure KIND. A NameError is a binding problem; a TypeError is a
signature problem; a timeout is a termination problem; an AssertionError carrying a value comparison
is a value problem. Those demand mutually exclusive repairs, so the kind can choose WHICH producer
runs first instead of racing every producer on every failure.

Cost: zero. The text is already in hand -- the failing test is run once before any candidate is
proposed, and its output was previously thrown away.
"""

from __future__ import annotations

import re

# Ordered: the first kind whose evidence is present wins. Order is by specificity, not by frequency.
_KINDS = (
    "SYNTAX",       # the file does not parse -- no behavioural repair can be screened
    "TERMINATION",  # it never finished
    "BINDING",      # a name or module does not exist where it is used
    "SIGNATURE",    # the call and the definition disagree
    "VALUE",        # it ran, produced a number/object, and the number/object is wrong
)

_PATTERNS = {
    "TERMINATION": re.compile(r"\bTIMEOUT\b|TimeoutExpired|took too long|infinite loop", re.I),
    "BINDING": re.compile(
        r"\b(NameError|UnboundLocalError|ModuleNotFoundError|ImportError)\b"
        r"|is not defined|cannot import name|No module named",
        re.I,
    ),
    "SIGNATURE": re.compile(
        r"\b(TypeError|AttributeError)\b|takes \d+ positional argument|unexpected keyword"
        r"|has no attribute|not callable|missing \d+ required",
        re.I,
    ),
    "VALUE": re.compile(
        r"\bAssertionError\b|\bassert\b|!=\s*-?\d|==\s*-?\d", re.I
    ),
}

_SYNTAX = re.compile(r"\b(SyntaxError|IndentationError)\b")


def classify(text: str) -> str:
    """One of SYNTAX / TERMINATION / BINDING / SIGNATURE / VALUE / UNKNOWN.

    SYNTAX is checked separately and first because a file that does not parse makes every other
    reading meaningless: pytest reports a SyntaxError with the offending line, and nothing about
    behaviour can be screened until it is fixed.
    """
    if not isinstance(text, str) or not text.strip():
        return "UNKNOWN"
    if _SYNTAX.search(text):
        return "SYNTAX"
    for kind in ("TERMINATION", "BINDING", "SIGNATURE", "VALUE"):
        if _PATTERNS[kind].search(text):
            return kind
    return "UNKNOWN"


# Which producer family is most likely to contain the fix, per kind. This is a PRIOR, not a rule: it
# only decides order, and every candidate is still screened by execution and the acceptance gate, so
# a wrong prior costs probes rather than correctness.
_FAMILY_FOR = {
    "VALUE": ("operator_family", "deterministic_ast", "stun_guard", "guided"),
    "TERMINATION": ("operator_family", "deterministic_ast", "stun_guard", "guided"),
    "BINDING": ("stun_guard", "guided", "operator_family", "deterministic_ast"),
    "SIGNATURE": ("guided", "stun_guard", "operator_family", "deterministic_ast"),
    "SYNTAX": ("guided", "stun_guard", "operator_family", "deterministic_ast"),
    "UNKNOWN": ("operator_family", "stun_guard", "guided", "deterministic_ast"),
}


def family_order(kind: str) -> tuple[str, ...]:
    return _FAMILY_FOR.get(kind, _FAMILY_FOR["UNKNOWN"])
