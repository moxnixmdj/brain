"""Syntax repairs: a file that does not parse, where no behavioural oracle can run yet.

Why this exists (pass fourteen, S10): SYNTAX was the last failure kind solved by no producer. It is
the hardest of the three holes for a specific reason -- every other repair in this system is verified
by RUNNING the owed test, and a file with a syntax error cannot be run at all. The oracle that has
authorised every repair in this project is unavailable exactly where the repair is needed.

So verification here is two-stage, and the order is what keeps it honest:
    1. the candidate must `ast.parse` -- this is a PRECONDITION, never a repair
    2. the candidate must then pass the owed test, through the normal screen and the normal gate
A candidate that only parses is NOT a repair and is never reported as one. Nothing in this module
widens an acceptance rule; it only produces candidates that a parser will accept so the existing
oracle can speak.

The repairs are the four the CPython parser actually names, and nothing else:
    - missing ':' after a compound statement header
    - unclosed bracket / parenthesis
    - unterminated string literal
    - unexpected indent (dedent to the previous statement's level)
"""

from __future__ import annotations

import ast
import re

_MISSING_COLON = re.compile(r"SyntaxError: expected ':'", re.I)
_UNCLOSED = re.compile(r"SyntaxError: '\(' was never closed|SyntaxError: unexpected EOF while parsing|"
                       r"SyntaxError: '\[' was never closed|SyntaxError: '\{' was never closed", re.I)
_STRING = re.compile(r"SyntaxError: unterminated string literal|SyntaxError: EOL while scanning string literal", re.I)
_INDENT = re.compile(r"IndentationError: unexpected indent", re.I)
_LINE_NO = re.compile(r"line (\d+)", re.I)


def _line_of(failure_text: str) -> int | None:
    m = _LINE_NO.search(failure_text or "")
    return int(m.group(1)) if m else None


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def propose_syntax_repairs(
    source_text: str,
    failure_text: str,
    *,
    max_candidates: int = 8,
) -> list[str]:
    """Candidates that make the file parse. Every one is checked with ast.parse before it is emitted."""
    if not isinstance(source_text, str) or not source_text.strip():
        return []
    if not isinstance(failure_text, str):
        return []
    lines = source_text.splitlines(keepends=True)
    out: list[str] = []
    seen: set[str] = {source_text}

    def emit(cand: str) -> None:
        if cand in seen or len(out) >= max_candidates:
            return
        if not _parses(cand):
            return  # a candidate that still does not parse is not a hypothesis, it is noise
        seen.add(cand)
        out.append(cand)

    target = _line_of(failure_text)

    # (a) missing ':' after a compound header
    if _MISSING_COLON.search(failure_text):
        rng = [target - 1] if target and 1 <= target <= len(lines) else range(len(lines))
        for i in rng:
            ln = lines[i]
            stripped = ln.rstrip("\n")
            if ":" in stripped:
                continue
            if re.match(r"\s*(if|for|while|def|class|else|elif|try|except|finally|with|async\s+def)\b", stripped):
                nl = "\n" if ln.endswith("\n") else ""
                cand = "".join(lines[:i]) + stripped + ":" + nl + "".join(lines[i + 1:])
                emit(cand)

    # (b) unclosed bracket: append the matching closers at the end of the offending line and of the file
    if _UNCLOSED.search(failure_text):
        for i in range(len(lines)):
            ln = lines[i]
            opens = sum(ln.count(c) for c in "([{")
            closes = sum(ln.count(c) for c in ")]}")
            if opens <= closes:
                continue
            need = []
            for ch in ln:
                if ch == "(":
                    need.append(")")
                elif ch == "[":
                    need.append("]")
                elif ch == "{":
                    need.append("}")
                elif ch in ")]}" and need:
                    need.pop()
            if not need:
                continue
            close = "".join(reversed(need))
            nl = "\n" if ln.endswith("\n") else ""
            emit("".join(lines[:i]) + ln.rstrip("\n") + close + nl + "".join(lines[i + 1:]))
        # and a whole-file variant, which covers a bracket left open across several lines
        opens = source_text.count("(") - source_text.count(")")
        if opens > 0:
            emit(source_text.rstrip("\n") + ")" * opens + "\n")

    # (c) unterminated string literal: close it on the line the parser names
    if _STRING.search(failure_text):
        rng = [target - 1] if target and 1 <= target <= len(lines) else range(len(lines))
        for i in rng:
            ln = lines[i]
            for quote in ('"""', "'''", '"', "'"):
                if ln.count(quote) % 2 == 1:
                    nl = "\n" if ln.endswith("\n") else ""
                    emit("".join(lines[:i]) + ln.rstrip("\n") + quote + nl + "".join(lines[i + 1:]))
                    break

    # (d) unexpected indent: dedent the named line to the previous non-blank line's indentation
    if _INDENT.search(failure_text):
        rng = [target - 1] if target and 1 <= target <= len(lines) else range(len(lines))
        for i in rng:
            ln = lines[i]
            prev = next((lines[j] for j in range(i - 1, -1, -1) if lines[j].strip()), None)
            if prev is None:
                continue
            want = prev[: len(prev) - len(prev.lstrip())]
            body = ln.lstrip()
            # (i) dedent the line to the previous line's level
            emit("".join(lines[:i]) + want + body + "".join(lines[i + 1:]))
            # (ii) JOIN it onto the previous line. This is the repair when the indent was a
            # continuation that got stray whitespace in front of it (`return a` then `    + 1`),
            # which dedenting alone leaves as a no-op expression statement. Both are emitted and the
            # screen decides; neither is assumed.
            joined = "".join(lines[: i - 1]) + prev.rstrip("\n") + " " + body + "".join(lines[i + 1:])
            emit(joined)

    return out
