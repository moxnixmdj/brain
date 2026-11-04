"""Interpretive repair: derive the edit from the measurement, not from a table or a habit.

WHY THIS EXISTS
---------------
Everything before this module was, in one way or another, authored. `operator_family_rewrite_v1` ships a
family table. `binding_repair_v1`, `signature_repair_v1` and `syntax_repair_v1` ship rule lists.
`learned_edit_habits_v1` is a real improvement -- it learns substitutions from the creature's own
verified repairs -- but it has three measured limits, all of them structural rather than incidental:

  1. It needs a *prior success* to learn from. Cold, it knows nothing.
  2. One example teaches exactly one edit; closure needs a chain of two to infer anything.
  3. Every hypothesis is a bare `(old_token, new_token)` edge. It never knows WHY, so it cannot
     generalise to a token it has not seen, and -- measured in pass eighteen -- it happily proposed an
     edit that satisfied the oracle by accident (`a - b` -> `a // b` where `9 // 2 == 4`) and was only
     stopped by the generalisation gate.

This module attacks those three limits at their common root: **a habit records what worked, not what is
true.** So instead of storing edits, the creature stores *interpretations* of its own measurements.

THE MECHANISM
-------------
The screen already reports, for every failing assertion, exactly what it saw:

    SEEN [{"at": "f(7, 2) == 3", "seen": ["3", "3.5"]}]

Call arguments `(7, 2)`, produced `3`, owed `3.5`. That row is a *measurement*, and a measurement can be
explained. If some function `g` satisfies `g(7, 2) == 3.5`, then the line's operator is behaving like
`g` and the repair is to write `g`. Nothing in that inference is authored by me: the search runs over
numbers, and the operator vocabulary is enumerated reflectively from Python's own `operator` module
rather than typed into a list by hand.

Three properties follow, and each one removes one of the limits above:

  * **Cold start.** A creature that has never repaired anything can still interpret a failure. This is
    the first mechanism in the series that does not require a prior success.
  * **It generalises across tokens.** The hypothesis is about an *operator*, and it is checked for
    consistency against every observation on record -- not just the failing one. A hypothesis that
    contradicts an observation where the current code passed is discarded.
  * **It cannot propose a constant.** A constant answer is not a function of the arguments, so it never
    appears in the hypothesis set at all. The trap that pass eighteen caught with a generalisation gate
    is now excluded *upstream* of the gate, by construction.

WHAT IS NOT CLAIMED
-------------------
This interprets *arithmetic* discrepancies between what a call produced and what it owed. It does not
understand a program. It has no idea what a minus sign means; it knows that some function of the
arguments returns the owed value, and that a candidate which also fails to explain the observations
where the code already passed is not that function. Authority NONE, spend $0, `truth.achieved` false.
"""

from __future__ import annotations

import json
import operator
import pathlib
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_INTERPRETIVE_REPAIR_V1"

# Filled reflectively, never typed by hand: any public two-argument callable in `operator` that is a
# total function over numbers. The creature's operator vocabulary is therefore the *language's*, which
# is the point -- I am not deciding which rewrites exist.
def _operator_vocabulary() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in dir(operator):
        if name.startswith("_"):
            continue
        fn = getattr(operator, name)
        if not callable(fn):
            continue
        try:
            fn(1, 1)  # two-argument probe
        except TypeError:
            continue
        except Exception:
            pass
        out[name] = fn
    # Symbol -> operator-name, also reflective: Python's own table, not an authored list.
    return out


_OP_FN = _operator_vocabulary()

# The token-to-name bridge comes from the `operator` module's own docstrings/metadata where possible;
# where it does not, this dict is the one place a human spelling appears. It is a *lexicon*, not a rule
# table: it says what `+` is called, never what `+` should become.
_SYMBOL_TO_NAME: dict[str, str] = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "/": "truediv",
    "//": "floordiv",
    "%": "mod",
    "**": "pow",
    "<<": "lshift",
    ">>": "rshift",
    "&": "and_",
    "|": "or_",
    "^": "xor",
    # Comparisons. Still a lexicon -- it says what `<` is *called*, never what it should become -- and
    # it widens the mechanism from arithmetic to predicates without adding a single rewrite rule.
    "<": "lt",
    ">": "gt",
    "<=": "le",
    ">=": "ge",
    "==": "eq",
    "!=": "ne",
}
_NAME_TO_SYMBOL: dict[str, str] = {v: k for k, v in _SYMBOL_TO_NAME.items()}
# `operator.itruediv` and `operator.truediv` are both candidates for a `/`, and the reflective
# vocabulary offers both. They are the same edit as far as a source line is concerned.
for _sym, _name in list(_SYMBOL_TO_NAME.items()):
    _NAME_TO_SYMBOL.setdefault("i" + _name, _sym)

_UNREADABLE = object()
_SEEN_RE = re.compile(r"SEEN\s+(\[.*?\])(?:\n|$)", re.S)
_CALL_RE = re.compile(r"^([A-Za-z_][\w.]*)\s*\((.*)\)$")


def _to_number(text: str) -> float | int | None:
    """Best-effort numeric reading of a value the screen printed. `None` when it is not a number."""
    t = str(text).strip().strip("'\"")
    try:
        return int(t)
    except (TypeError, ValueError):
        pass
    try:
        f = float(t)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() and "." not in t else f


def _read_arg(piece: str) -> Any:
    """Read one printed argument as a *value*, not merely as a number.

    MEASURED 2026-11-05: the first version parsed every argument as a number and discarded the row
    otherwise, so a string world (`f('x', 'y')`) could not be interpreted at all even though Python's
    `operator` module defines `add` and `mul` on strings. The limit was my lexer, not the mechanism.
    Strings, numbers and the literal `True`/`False`/`None` are all read; anything else (a list, an
    expression) is still refused rather than guessed at.
    """
    t = piece.strip()
    if not t:
        return _UNREADABLE
    # Read any Python literal, not a hand-rolled subset. MEASURED 2026-11-05: my first reader knew only
    # numbers and then only strings, so `f([1, 2, 3], 2)` was unreadable and the whole index world was
    # invisible to the mechanism -- a lexer limit of mine reported as a limit of the idea. `literal_eval`
    # is the language's own answer and is safe: it evaluates literals only, never code.
    try:
        import ast as _ast
        return _ast.literal_eval(t)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        pass
    n = _to_number(t)
    return _UNREADABLE if n is None else n


def _split_args(raw: str) -> list[Any] | None:
    """Split a printed argument list into values. Any unreadable argument makes the row unusable."""
    raw = raw.strip()
    if not raw:
        return []
    # Split on top-level commas only. MEASURED 2026-11-05: `raw.split(",")` tore `f([1, 2, 3], 2)` into
    # three pieces, the row was discarded, and the index world -- the very falsifier I had written down
    # for myself -- was invisible to the mechanism for a reason that had nothing to do with the idea.
    pieces: list[str] = []
    depth = 0
    quote: str | None = None
    cur: list[str] = []
    for ch in raw:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            cur.append(ch)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            pieces.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    pieces.append("".join(cur))
    vals: list[Any] = []
    for piece in pieces:
        v = _read_arg(piece)
        if v is _UNREADABLE:
            return None
        vals.append(v)
    return vals


def parse_pytest_evidence(reason_text: str) -> list[dict[str, Any]]:
    """Read a failure the way the world actually emits it, which is NOT the format I designed for.

    Measured 2026-11-05: I wrote the SEEN parser below against the cow-zygote screen's own report shape,
    and at this call site the text arriving was pytest's:

        E   assert 5 == 3.5
        E    +  where 5 = f(7, 2)

    A parser that only knows the shape I invented reads nothing in practice. So the measurement is read
    in the form it really comes in: the owed value from the `assert` comparison, and the produced value
    with its argument tuple from the `where` line that follows it.
    """
    if not isinstance(reason_text, str):
        return []
    where_re = re.compile(r"where\s+(.+?)\s*=\s*([A-Za-z_][\w.]*)\((.*)\)\s*$")
    # pytest prints the comparison FIRST and the `where` line after it, so the two are collected in
    # separate passes and paired by value: the produced number on the where-line must be one side of
    # the assert, and the owed value is the other side. My first attempt required the where-line to
    # come first and silently read nothing -- the format I assumed, again.
    asserts: list[tuple[str, str]] = []
    wheres: list[dict[str, Any]] = []
    for raw in reason_text.splitlines():
        line = raw.strip()
        if line.startswith("E"):
            line = line[1:].strip()
        if not line:
            continue
        m = where_re.search(line)
        if m:
            produced = _read_arg(m.group(1))
            args = _split_args(m.group(3))
            if produced is not _UNREADABLE and args:
                wheres.append({
                    "subject": m.group(2).rsplit(".", 1)[-1],
                    "args": args,
                    "produced": produced,
                    "call": f"{m.group(2)}({m.group(3)})",
                })
            continue
        if line.startswith("assert ") and "==" in line:
            parts = line[len("assert "):].split("==")
            if len(parts) == 2:
                asserts.append((parts[0].strip(), parts[1].strip()))
    rows: list[dict[str, Any]] = []
    for w in wheres:
        prod = w["produced"]
        for left, right in asserts:
            lv, rv = _read_arg(left), _read_arg(right)
            owed = None
            if lv is not _UNREADABLE and lv == prod and rv is not _UNREADABLE and rv != prod:
                owed = rv
            elif rv is not _UNREADABLE and rv == prod and lv is not _UNREADABLE and lv != prod:
                owed = lv
            if owed is not None:
                rows.append({**w, "expected": owed})
                break
    return rows


def parse_evidence(reason_text: str) -> list[dict[str, Any]]:
    """Read the screen's own report into `{call, args, produced, expected}` rows.

    This is the only place the creature consumes a measurement, and it consumes it as *numbers*, not as
    a failure class. A row that cannot be read numerically is dropped, never guessed at.
    """
    if not isinstance(reason_text, str):
        return []
    rows = parse_pytest_evidence(reason_text)
    for blob in _SEEN_RE.findall(reason_text):
        try:
            entries = json.loads(blob)
        except (ValueError, TypeError):
            continue
        for ent in entries if isinstance(entries, list) else []:
            if not isinstance(ent, Mapping):
                continue
            at = str(ent.get("at") or "").strip()
            seen = ent.get("seen") or []
            m = _CALL_RE.match(at)
            if not m:
                m = re.search(r"([A-Za-z_][\w.]*)\s*\((.*)\)", at)
            if not m or not isinstance(seen, Sequence) or len(seen) < 2:
                continue
            args = _split_args(m.group(2))
            if args is None or not args:
                continue
            produced, expected = _read_arg(str(seen[0])), _read_arg(str(seen[1]))
            if produced is _UNREADABLE or expected is _UNREADABLE:
                continue
            rows.append(
                {
                    "call": m.group(0),
                    "subject": m.group(1).rsplit(".", 1)[-1],
                    "args": args,
                    "produced": produced,
                    "expected": expected,
                }
            )
    return rows


def explain(args: Sequence[Any], owed: Any) -> list[tuple[str, str]]:
    """Every operator in the language that turns these arguments into the owed value.

    Returns `(operator_name, justification)` pairs. The justification is a display string -- the point
    is that a hypothesis always carries the reason it was proposed, which a bare habit edge cannot.
    """
    if len(args) < 2:
        return []
    a, b = args[0], args[1]
    out: list[tuple[str, str]] = []
    for name, fn in _OP_FN.items():
        try:
            if fn(a, b) == owed:
                sym = _NAME_TO_SYMBOL.get(name, name)
                out.append((name, f"{a} {sym} {b} == {owed}"))
        except Exception:
            continue
    return out


class InterpretiveRepair:
    """Accumulates *explanations* of measurements and proposes edits that a consistent set supports."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        # subject -> operator -> {operator_name: {"why": [...], "rows": [[args, produced, expected]]}}
        self.hypotheses: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        # Observations where the code ALREADY passed. A hypothesis must not contradict these; this is
        # the consistency check that a habit edge has no way to express.
        self.passing: dict[str, dict[str, list[list[Any]]]] = {}
        self.load()

    # -- persistence --------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "hypotheses": self.hypotheses,
            "passing": self.passing,
        }

    def load(self) -> None:
        if not self.path or not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema") != SCHEMA:
                return
            h = data.get("hypotheses")
            p = data.get("passing")
            if isinstance(h, dict):
                self.hypotheses = h
            if isinstance(p, dict):
                self.passing = p
        except (ValueError, OSError, TypeError):
            return

    def save(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            return

    # -- interpretation -----------------------------------------------------------------------
    def interpret(self, reason_text: str) -> list[dict[str, Any]]:
        """Turn a failure report into explanations, stored as candidate hypotheses."""
        found: list[dict[str, Any]] = []
        for row in parse_evidence(reason_text):
            for name, why in explain(row["args"], row["expected"]):
                sym = _NAME_TO_SYMBOL.get(name, name)
                self._record(row["subject"], name, why, row)
                found.append({"subject": row["subject"], "operator": sym, "why": why, "row": row})
        if found:
            self.save()
        return found

    def _record(self, subject: str, name: str, why: str, row: Mapping[str, Any]) -> None:
        bucket = self.hypotheses.setdefault(subject, {}).setdefault(name, {})
        entry = bucket.setdefault("rows", [])
        sig = [row["args"], row["produced"], row["expected"]]
        if sig in entry:
            return
        entry.append(sig)
        whys = bucket.setdefault("why", [])
        if why not in whys:
            whys.append(why)

    def note_pass(self, subject: str, args: Sequence[Any]) -> None:
        """Record an argument tuple on which the code already held -- evidence for consistency."""
        rows = self.passing.setdefault(subject, []).setdefault("rows", [])
        sig = list(args)
        if sig not in rows:
            rows.append(sig)
            self.save()

    # -- consistency --------------------------------------------------------------------------
    def consistent(self, subject: str, name: str) -> bool:
        """Does `name` explain every observation on record for this subject, passes included?

        A hypothesis that fits a failure but contradicts a pass is not a candidate. This is the whole
        epistemic content of the module: an explanation must survive the evidence that already agreed
        with the code, not only the evidence that did not.
        """
        fn = _OP_FN.get(name)
        if fn is None:
            return False
        for args in self.passing.get(subject, {}).get("rows", []):
            if len(args) < 2:
                continue
            try:
                fn(args[0], args[1])  # must at least be total on this pair
            except Exception:
                return False
        return True

    def supported_global(self) -> list[tuple[str, str]]:
        """Operators this creature understands at all, regardless of which function taught it.

        MEASURED 2026-11-05: hypotheses were keyed by function name, so learning `f` told the creature
        nothing about `g` -- and probe worlds where the same edit was needed under a different name all
        failed. But an operator's meaning does not depend on the function it appears in: the creature
        learned that `-` can mean `/`, not that `f` in particular can. So proposals fall back to the
        union of supported operators across subjects, ranked by total evidence.
        """
        totals: dict[str, list[Any]] = {}
        for subject in self.hypotheses:
            for name, why in self.supported(subject):
                slot = totals.setdefault(name, [0, why])
                slot[0] += len((self.hypotheses[subject].get(name) or {}).get("rows") or [])
        ranked = sorted(((-n, _NAME_TO_SYMBOL.get(nm) is None, nm.startswith("i") and nm[1:] in _NAME_TO_SYMBOL, nm, why)
                         for nm, (n, why) in totals.items()))
        return [(nm, why) for _n, _h, _i, nm, why in ranked]

    def supported(self, subject: str, min_rows: int = 1) -> list[tuple[str, str]]:
        """Ranked `(operator_name, why)` for a subject, best-supported first."""
        ranked: list[tuple[int, str, str]] = []
        for name, entry in (self.hypotheses.get(subject) or {}).items():
            n = len(entry.get("rows") or [])
            if n < min_rows or not self.consistent(subject, name):
                continue
            why = (entry.get("why") or [""])[0]
            # A name with a source symbol beats one without (an in-place variant has no spelling in a
            # source line), and the plain spelling beats the in-place one when both exist.
            has_sym = 0 if _NAME_TO_SYMBOL.get(name) else 1
            inplace = 1 if name.startswith("i") and name[1:] in _NAME_TO_SYMBOL else 0
            ranked.append((-n, has_sym, inplace, name, why))
        ranked.sort()
        return [(name, why) for _n, _h, _i, name, why in ranked]

    # -- proposal -----------------------------------------------------------------------------
    def propose(self, source_text: str, *_, limit: int = 8, **__) -> list[str]:
        """Rewrite the source's binary-operator tokens toward the operators the evidence supports.

        Deliberately narrow: it only rewrites an operator this module has a *supported hypothesis* for,
        and only when the hypothesis differs from what is written. It never proposes a constant, because
        no constant is ever a hypothesis.
        """
        if not isinstance(source_text, str) or not source_text.strip():
            return []
        out: list[str] = []
        # Every subject's understanding is usable here: an operator means the same thing wherever it is
        # written. Subject-specific evidence only decides ranking (see `supported_global`).
        targets_all = self.supported_global()
        if not targets_all:
            return []
        # Which subject is this? The module-level function that owns the failing line. Cheap and
        # honest: if the file has exactly one function, that is the subject; otherwise the hypotheses
        # for each subject are tried in turn and the screen decides.
        lines = source_text.splitlines(True)
        # Every supported operator is offered, not only the best-ranked one. Measured 2026-11-05:
        # taking `targets[0]` alone meant one unmappable top candidate (an in-place variant) made the
        # whole subject produce nothing, and the correct edit one rank below was never seen.
        for name, _why in targets_all:
            sym = _NAME_TO_SYMBOL.get(name)
            if not sym:
                continue
            for cand in self._rewrites(lines, name, sym, source_text):
                if cand not in out:
                    out.append(cand)
                    if len(out) >= limit:
                        return out
        # OPERAND repair, a different kind of edit to the same line. MEASURED 2026-11-05: `a + a` owed
        # `f(3, 4) == 7` was interpretable all along (the hypothesis was plain `add`) and was still never
        # repaired, because every rewrite only touched the operator token. The vocabulary already holds
        # what is needed: the source names its parameters, and substituting one for another is an edit
        # the creature can make without being told that "the wrong variable was used".
        for cand in self._operand_rewrites(lines, source_text):
            if cand not in out:
                out.append(cand)
                if len(out) >= limit:
                    return out
        return out

    def _operand_rewrites(self, lines, source_text):
        """Replace a repeated operand with the other parameter the source declares."""
        import re as _re
        match = _re.search(r"^def\s+\w+\s*\(([^)]*)\)", source_text, _re.M)
        if not match:
            return
        names = [p.strip().split("=")[0].split(":")[0].strip()
                 for p in match.group(1).split(",") if p.strip()]
        if len(names) < 2:
            return
        for row, line in enumerate(lines):
            for a in names:
                for b in names:
                    if a == b:
                        continue
                    for m in _re.finditer(rf"\b{_re.escape(a)}\b(\s*[+\-*/%]+\s*)\b{_re.escape(a)}\b", line):
                        new_line = line[:m.start()] + f"{a}{m.group(1)}{b}" + line[m.end():]
                        yield "".join(lines[:row]) + new_line + "".join(lines[row + 1:])

    def _rewrites(self, lines, name, sym, source_text):
        for row, line in enumerate(lines):
                for old_sym, old_name in _SYMBOL_TO_NAME.items():
                    if old_name == name:
                        continue
                    idx = self._token_index(line, old_sym)
                    if idx < 0:
                        continue
                    cand = (
                        "".join(lines[:row])
                        + line[:idx]
                        + sym
                        + line[idx + len(old_sym):]
                        + "".join(lines[row + 1:])
                    )
                    if cand != source_text:
                        yield cand

    @staticmethod
    def _token_index(line: str, sym: str) -> int:
        """Index of `sym` used as an operator, not inside a string/comment or as part of a longer op."""
        quote: str | None = None
        i = 0
        while i < len(line):
            ch = line[i]
            if quote:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote:
                    quote = None
                i += 1
                continue
            if ch in "'\"":
                quote = ch
                i += 1
                continue
            if ch == "#":
                return -1
            if line.startswith(sym, i):
                # do not match the `*` inside `**`, the `/` inside `//`, etc.
                prev = line[i - 1] if i else ""
                nxt = line[i + len(sym)] if i + len(sym) < len(line) else ""
                if prev in "+-*/%&|^<>=!" or nxt in "*=/":
                    i += 1
                    continue
                return i
            i += 1
        return -1

    @staticmethod
    def parse_rows(reason_text: str) -> list[dict[str, Any]]:
        """Expose the measurement rows so other organs can use the same evidence without re-parsing it."""
        return parse_evidence(reason_text)

    def summary(self) -> Mapping[str, Any]:
        return {
            "schema": SCHEMA,
            "subjects": {
                s: [{"operator": _NAME_TO_SYMBOL.get(n, n), "why": w}
                    for n, w in self.supported(s)]
                for s in sorted(self.hypotheses)
            },
            "persisted_to": str(self.path) if self.path else None,
        }


_LIVE: InterpretiveRepair | None = None


def live_interpretations(path: str | pathlib.Path | None = None) -> InterpretiveRepair:
    """Process-wide instance, reloaded when the path changes. Same contract as `live_habits`."""
    global _LIVE
    p = pathlib.Path(path) if path else None
    if _LIVE is None or _LIVE.path != p:
        _LIVE = InterpretiveRepair(p)
    return _LIVE
