"""The value to type is usually a COMPUTATION over what is on the page, not a word found in it.

The failure this removes
-----------------------
Measured 2026-11-16 on the pages the 1500-action search never solved: at a budget of 400
actions the search fails on them too, so they are not budget problems. They are GENERATOR
problems, and a look at the page says which one:

    simple-arithmetic   page shows "7 + 0 ="      the field wants "7"
    simple-algebra      page shows "x + 7 = 5"    the field wants "-2"
    scroll-text         a 900-character text area the field wants its LAST WORD, "et"
    enter-time          instruction says "7:55 PM" a time field wants "19:55"
    text-transform      the page shows "3" "X" "Z" the field wants them joined / re-cased

In every one of those, everything needed is visible, and the ONLY reason the shipped hand
cannot reach success is that its single way to produce text is `type_candidates`: a quoted
span of the instruction, a word of the instruction, or a string already on the page. None of
those is `7`, `-2`, `et`, `19:55`, or `3XZ`. So the search is not failing to find the answer;
it is unable to EXPRESS it, at any budget, on any page of this kind. That is the same defect
`WHAT_ONE_DEMONSTRATION_BUYS_20261116_V1.md` found in the edit vocabulary (a fix nothing can
build is unreachable, not slow), one level up: not the edit, the operand.

What this is
------------
A stated, bounded algebra of **derivations**: a small set of operators, each with a
precondition over what the agent can see, each producing a value together with the rule that
produced it. Not a bigger hand -- a handful of aimed actions instead of every word of every
instruction. Measured on the same pages, the number of candidate values per state falls from
tens to one or two, and the actions that remain are the ones that can be right.

Every operator is one of:

    IDENTITY      the literal as it stands (the existing behaviour, kept as the baseline)
    STRIP         edge punctuation removed          "Et." -> "Et"
    CASE          upper / lower as the instruction asks
    WORD          the first, last or n-th word, when the instruction names which
    JOIN          consecutive shown literals, when the instruction names the group
    ARITHMETIC    a page expression evaluated      "7 + 0 =" -> "7"
    LINEAR        a one-variable linear equation solved   "x + 7 = 5" -> "-2"
    CLOCK24       "7:55 PM" -> "19:55" for a time field

The precondition is the part that makes this a prior and not a guess: an operator fires only
when the observation contains the structure it needs (a text area longer than it shows, an
expression, a time-type field, a quoted literal). An operator that cannot fire says so.

Safety, because a computed value is executed
--------------------------------------------
`ARITHMETIC` and `LINEAR` evaluate text taken from a page, so the evaluator is an allow-list
AST walk with no names, no calls, no attributes, no strings, a node budget and a magnitude
guard. It is arithmetic, not an interpreter: `EVAL_REFUSED` is a normal outcome and is
reported, not raised. Nothing here reads a reward, a `done` flag, a network, a model or a file.

What it is not
--------------
  * Not a solver of arbitrary word problems. The algebra is finite and declared; a page whose
    answer needs an operator that is not in the list fails here, and the list is short on
    purpose (the best part is no part).
  * Not a learner. It produces candidates with their rules; whether a candidate is right is
    decided by execution, which is the caller's verifier and never this module's opinion.
  * Not a model. `K3 = 0`, `$0`, no weights.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DERIVED_VALUE_V1"

#: Hard ceiling on how many values one state may offer. The whole point is that a derivation
#: basis is SMALLER than the word list it replaces; a basis that grows without limit has
#: become the enumeration it was meant to kill.
MAX_DERIVATIONS = 12

#: Magnitude guard for arithmetic taken off a page. A number this large is not an answer to a
#: form; refusing it keeps `2 ** 10 ** 9` from being evaluated as a favour.
MAX_MAGNITUDE = 10 ** 12

_EDGE = ".,;:!?\"'()[]{}<>«»“”‘’"
_TIME_ = re.compile(r"\b(\d{1,2}):(\d{2})\s*([AaPp])\.?\s*[Mm]\.?\b")
_ARITH_ = re.compile(r"^[\s\d+\-*/().]+$")
_WHOLE = re.compile(r"(?<![\w.])\d+(?![\w.])")


# --------------------------------------------------------------------------- #
# the evaluator: arithmetic on a page, and nothing else
# --------------------------------------------------------------------------- #
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub,
            ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd, ast.Pow, ast.Load)
_MAX_NODES = 64


def evaluate_arithmetic(text: str) -> tuple[str | None, str]:
    """Evaluate a pure arithmetic expression read off a page.

    Returns (value, reason). `value` is None and `reason` names the refusal; a refusal is a
    fact about the page, not an error. The tree is walked with an allow-list, so `__import__`,
    a name, a call, an attribute or a string is REFUSED rather than executed.
    """
    source = str(text or "").strip()
    if not source:
        return None, "EVAL_EMPTY"
    # A page prints its expression with a trailing "=" ("7 + 0 ="). Strip it BEFORE the purity
    # check, or the one character every such page has makes every one of them refuse.
    source = source.rstrip("= ").strip()
    if not source:
        return None, "EVAL_NOTHING_BUT_EQUALS"
    if not _ARITH_.match(source):
        return None, "EVAL_NOT_PURE_ARITHMETIC"
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError:
        return None, "EVAL_UNPARSEABLE"
    nodes = list(ast.walk(tree))
    if len(nodes) > _MAX_NODES:
        return None, "EVAL_TOO_LARGE"
    for node in nodes:
        if not isinstance(node, _ALLOWED):
            return None, f"EVAL_REFUSED_{type(node).__name__}"
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            return None, "EVAL_REFUSED_NON_NUMBER"
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            right = node.right
            if not (isinstance(right, ast.Constant) and isinstance(right.value, int)
                    and 0 <= right.value <= 8):
                return None, "EVAL_REFUSED_EXPONENT"
    try:
        value = eval(compile(tree, "<page>", "eval"), {"__builtins__": {}}, {})  # noqa: S307
    except ZeroDivisionError:
        return None, "EVAL_DIVIDED_BY_ZERO"
    except Exception as error:  # noqa: BLE001 -- a page may contain anything
        return None, f"EVAL_FAILED_{type(error).__name__}"
    number = float(value)
    if abs(number) > MAX_MAGNITUDE or number != number:
        return None, "EVAL_OUT_OF_RANGE"
    return format_number(number), "EVAL_OK"


def format_number(value: float) -> str:
    """A form does not want `7.0`. Integral results are written as integers."""
    return str(int(round(value))) if abs(value - round(value)) < 1e-9 else f"{value:g}"


_TERM = re.compile(r"[+-]?[^+-]+")


def _linear_side(expression: str) -> tuple[float, float] | None:
    """One side of an equation as `coefficient * x + constant`, or None if it is not linear.

    Written after the corpus corrected a first draft: the page puts the unknown on EITHER side
    (`x + 7 = 5` and `8 + x = 33` both occur), so a solver that assumed the left side was a
    coefficient and the right side a number refused half the pages. The rule is the general
    linear one, and it is still only linear: one variable, no powers, no products of unknowns.
    """
    text = str(expression or "").replace("−", "-").replace("*", "").replace(" ", "")
    if not text:
        return None
    if any(ch not in "0123456789.+-x" for ch in text):
        return None
    coefficient = 0.0
    constant = 0.0
    for term in _TERM.findall(text):
        if "x" in term:
            if term.count("x") != 1 or not term.endswith("x"):
                return None                      # x*x, x2, 2x3 ... not linear in this algebra
            head = term[:-1]
            if head in ("", "+"):
                coefficient += 1.0
            elif head == "-":
                coefficient -= 1.0
            else:
                try:
                    coefficient += float(head)
                except ValueError:
                    return None
        else:
            try:
                constant += float(term)
            except ValueError:
                return None
    return coefficient, constant


def solve_linear(text: str) -> tuple[str | None, str]:
    """Solve a one-variable linear equation read off a page: `x + 7 = 5`, `8 + x = 33`.

    The algebra is deliberately one operator wide. A form asks "solve for x"; anything that is
    not linear is refused BY NAME, so a page needing a wider operator is visible as such rather
    than silently counted as unreachable.
    """
    source = str(text or "").strip()
    if source.count("=") != 1:
        return None, "LINEAR_NOT_AN_EQUATION"
    if "x" not in source.lower():
        return None, "LINEAR_NO_VARIABLE"
    left, right = source.split("=")
    a = _linear_side(left)
    b = _linear_side(right)
    if a is None or b is None:
        return None, "LINEAR_NOT_LINEAR"
    coefficient = a[0] - b[0]
    if coefficient == 0:
        return None, "LINEAR_NO_VARIABLE"
    value = (b[1] - a[1]) / coefficient
    if abs(value) > MAX_MAGNITUDE or value != value:
        return None, "LINEAR_OUT_OF_RANGE"
    return format_number(value), "LINEAR_SOLVED"


def clock24(text: str) -> tuple[str | None, str]:
    """`7:55 PM` -> `19:55`, the value an `input[type=time]` takes."""
    match = _TIME_.search(str(text or ""))
    if not match:
        return None, "CLOCK_NO_TIME_FOUND"
    hour, minute, meridiem = int(match.group(1)), match.group(2), match.group(3).upper()
    if not 1 <= hour <= 12 or int(minute) > 59:
        return None, "CLOCK_OUT_OF_RANGE"
    hour = hour % 12 + (12 if meridiem == "P" else 0)
    return f"{hour:02d}:{minute}", "CLOCK_CONVERTED"


# --------------------------------------------------------------------------- #
# reading the page: what can be derived, and from what
# --------------------------------------------------------------------------- #
def words_of(text: Any) -> list[str]:
    return [w.strip(_EDGE) for w in str(text or "").split() if w.strip(_EDGE)]


CONTROL_TAGS = frozenset({"button", "input", "option", "select", "a", "label"})


def visible_texts(observation: Mapping[str, Any], *, content_only: bool = False
                  ) -> list[tuple[int, str, str]]:
    """Every string on the page that a hand could copy from, as (index, where, text).

    `where` names which field it came from, because a text area's FULL text and the part of it
    that is SHOWN are two different strings, and the interesting one is usually the full text
    (that is how "the last word in the text area" is reachable at all).
    """
    out: list[tuple[int, str, str]] = []
    for element in observation.get("elements") or []:
        index = int(element.get("index", -1))
        tag = str(element.get("tag") or "").lower()
        if content_only and tag in CONTROL_TAGS:
            continue
        for field in ("text", "value"):
            value = str(element.get(field) or "").strip()
            if value and (index, field, value) not in out:
                out.append((index, field, value))
    return out


#: Order of trying, as a rank per rule. The instruction is what the user asked for, so a value
#: taken verbatim from it comes first; a COMPUTED value is aimed and comes next; a bare copy of
#: page content is the broadest and least aimed, so it comes last. Measured 2026-11-16: the
#: order is not cosmetic. On a page where a wrong value makes the page unreachable, trying the
#: right value second costs the whole run.
_BUCKET = {
    # Computed values are produced by a rule that had to read the page's structure, so they are
    # more aimed than a word quoted out of the instruction: a quote may be naming a control
    # ("press \"Search\"") rather than a value, and typing it into a box is a guess.
    "LINEAR": 0, "ARITHMETIC": 0, "CLOCK24": 0, "JOIN_SHOWN": 0, "JOIN_SHOWN_UPPER": 0,
    "JOIN_SHOWN_LOWER": 0, "LAST_WORD": 0, "LAST_WORD_CASE": 0, "FIRST_WORD": 0,
    "STRIP": 1, "CASE_UPPER": 1, "CASE_LOWER": 1, "LINEAR_ALT": 1, "ARITHMETIC": 1, "CLOCK24": 1, "JOIN_SHOWN": 1, "JOIN_SHOWN_UPPER": 1,
    "JOIN_SHOWN_LOWER": 1, "LAST_WORD": 1, "LAST_WORD_CASE": 1, "FIRST_WORD": 1,
    "PAGE_LITERAL": 2,
}


def derivations(observation: Mapping[str, Any], *, limit: int = MAX_DERIVATIONS) -> list[dict[str, Any]]:
    """Every value the algebra can produce here, with the rule and the witness that produced it.

    Ordered by how aimed the value is: the instruction's own words, then computed values, then
    bare copies of page content. The list is capped, and the cap is a design statement -- if the
    basis needs more than `limit` values it has stopped being a prior, and the caller should
    know that rather than pay for it silently.
    """
    utterance = str(observation.get("utterance") or "")
    said = utterance.lower()
    found: list[dict[str, Any]] = []

    def offer(value: Any, rule: str, witness: str, *, target: str | None = None) -> None:
        text = str(value or "").strip()
        if not text or len(text) > 200:
            return
        for row in found:
            if row["value"] == text:
                return
        found.append({"value": text, "rule": rule, "witness": witness[:120],
                      "target": target, "rank": _BUCKET.get(rule, 3)})

    # 1. the instruction's own quoted words, as they stand and repaired -- minus the ones that
    # name a control, which are press targets and not values
    labels = control_labels(observation)
    for span in quoted_spans(utterance):
        if span.strip(_EDGE).lower() in labels:
            continue
        offer(span.strip(_EDGE), "STRIP", span)
        if "upper" in said or "capital" in said:
            offer(span.upper(), "CASE_UPPER", span)
        if "lower" in said:
            offer(span.lower(), "CASE_LOWER", span)

    # 2. values COMPUTED from what the page shows; each has a precondition on the page's shape
    for index, where, text in visible_texts(observation):
        if "=" in text or "+" in text or "\u2212" in text or "*" in text or "/" in text:
            value, reason = solve_linear(text)
            if value is not None:
                offer(value, "LINEAR", f"{where}@{index}:{text}", target=reason)
            value, reason = evaluate_arithmetic(text)
            if value is not None:
                offer(value, "ARITHMETIC", f"{where}@{index}:{text}", target=reason)

    wants_first = any(word in said for word in ("first word", "first character", "starts with"))
    wants_last = any(word in said for word in ("last word", "last character", "ends with"))
    for index, where, text in visible_texts(observation):
        if len(text) < 40:
            continue
        parts = words_of(text)
        if not parts:
            continue
        if wants_last:
            offer(parts[-1], "LAST_WORD", f"{where}@{index}")
            offer(parts[-1].upper(), "LAST_WORD_CASE", f"{where}@{index}")
        if wants_first:
            offer(parts[0], "FIRST_WORD", f"{where}@{index}")

    has_time_field = any(str(e.get("type") or "").lower() == "time"
                         for e in observation.get("elements") or [])
    if has_time_field or "time" in said:
        value, reason = clock24(utterance)
        if value is not None:
            offer(value, "CLOCK24", utterance, target=reason)

    if any(word in said for word in ("below", "shown", "following", "these", "the characters")):
        literals = [t for _, _, t in visible_texts(observation, content_only=True)
                    if len(t) <= 3 and not t.endswith((".", ","))]
        if 2 <= len(literals) <= 6:
            joined = "".join(literals)
            offer(joined, "JOIN_SHOWN", "+".join(literals))
            offer(joined.upper(), "JOIN_SHOWN_UPPER", "+".join(literals))
            offer(joined.lower(), "JOIN_SHOWN_LOWER", "+".join(literals))

    # 3. bare copies of page content: broad, least aimed, tried last
    for index, where, text in visible_texts(observation, content_only=True):
        if len(text) <= 40:
            offer(text, "PAGE_LITERAL", f"{where}@{index}")

    found.sort(key=lambda row: row["rank"])
    ordered: list[dict[str, Any]] = []
    for row in found:
        row = dict(row)
        row.pop("rank", None)
        ordered.append(row)
    return ordered[:max(0, int(limit))]


_QUOTED = re.compile(r'"([^"]+)"|(?<![A-Za-z0-9])\'([^\']+)\'(?![A-Za-z0-9])')


def control_labels(observation: Mapping[str, Any]) -> set[str]:
    """The strings that NAME a control on the page rather than hold content.

    `press "Search"` quotes a button, and the button's own label is the quote. Typing that label
    into a box is a guess about the user's intent that a quote cannot support, and on the pages
    measured it was actively harmful: the search box then held the wrong query and the page
    became unreachable. A quote that equals a control's label is therefore not a value to type.
    """
    labels: set[str] = set()
    for element in observation.get("elements") or []:
        tag = str(element.get("tag") or "").lower()
        is_control = tag in CONTROL_TAGS or str(element.get("role") or "").lower() == "button"
        if not is_control:
            continue
        for field in ("text", "value", "aria-label", "title", "placeholder", "alt"):
            label = str(element.get(field) or "").strip()
            if label:
                labels.add(label.lower())
    return labels


def quoted_spans(utterance: str) -> list[str]:
    out: list[str] = []
    for match in _QUOTED.finditer(utterance or ""):
        value = match.group(1) if match.group(1) is not None else match.group(2)
        if value and value not in out:
            out.append(value)
    return out


def typed_actions(observation: Mapping[str, Any], *, limit: int = MAX_DERIVATIONS) -> list[str]:
    """The derived values as `type@index=value` actions for every field that takes text.

    Kept here, next to the algebra, so a caller that wants aimed typing does not have to
    re-derive the mapping and drift from the rules.
    """
    fields = [int(e["index"]) for e in observation.get("elements") or [] if e.get("can_type")]
    out: list[str] = []
    for row in derivations(observation, limit=limit):
        for index in fields:
            action = f"type@{index}={row['value']}"
            if action not in out:
                out.append(action)
    return out


def rule_of(observation: Mapping[str, Any], action: str) -> dict[str, Any] | None:
    """Which derivation produced a `type@index=value` action, or None if it was not one.

    This is what makes a success learnable: a hit is not "the string was right", it is "the
    rule ARITHMETIC was right on a page that showed an expression". A rule that is recorded is
    a knowledge claim the caller can price, admit or refuse.
    """
    text = str(action)
    if not text.startswith("type@"):
        return None
    _, _, rest = text.partition("=")
    value = rest
    for row in derivations(observation, limit=MAX_DERIVATIONS * 4):
        if row["value"] == value:
            return {"value": value, "rule": row["rule"], "witness": row["witness"],
                    "target": row["target"], "schema": SCHEMA}
    return None
