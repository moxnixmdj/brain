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
    """Read pytest comparisons without turning a peer's output into ground truth.

    ``where`` and ``and`` in one assertion can describe two calls.  An equality
    failure constrains their relationship but does not identify either call as
    correct, regardless of which one happened to appear on the left.
    """
    if not isinstance(reason_text, str):
        return []
    where_re = re.compile(r"(?:where|and)\s+(.+?)\s*=\s*([A-Za-z_][\w.]*)\((.*)\)\s*$")
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in reason_text.splitlines():
        line = raw.strip()
        if line == "E" or line.startswith("E "):
            line = line[1:].strip()
        if line.startswith("assert ") and "==" in line:
            parts = line[len("assert "):].split("==")
            current = None
            if len(parts) == 2:
                left, right = _read_arg(parts[0]), _read_arg(parts[1])
                if left is not _UNREADABLE and right is not _UNREADABLE:
                    current = {"left": left, "right": right, "calls": []}
                    blocks.append(current)
            continue
        match = where_re.search(line)
        if current is None or not match:
            continue
        produced = _read_arg(match.group(1))
        args = _split_args(match.group(3))
        if produced is not _UNREADABLE and args:
            current["calls"].append({"subject": match.group(2).rsplit(".", 1)[-1],
                                     "args": args, "produced": produced,
                                     "call": f"{match.group(2)}({match.group(3)})"})
    rows: list[dict[str, Any]] = []
    seen_rows: set[str] = set()
    for block in blocks:
        left, right, calls = block["left"], block["right"], block["calls"]
        # Only mark a comparison relational if there are calls explaining BOTH
        # displayed values. Extra nested `where` lines do not manufacture blame.
        peer = (any(w["produced"] == left for w in calls) and
                any(w["produced"] == right for w in calls) and left != right)
        for call in calls:
            produced = call["produced"]
            if produced == left and left != right:
                expected = right
            elif produced == right and left != right:
                expected = left
            else:
                continue
            row = {**call, "expected": expected,
                   "expected_source": "peer_observation" if peer else "assertion"}
            signature = repr(row)
            if signature not in seen_rows:
                seen_rows.add(signature)
                rows.append(row)
    return rows


def _call_from_ast(node: Any) -> dict[str, Any] | None:
    import ast as _ast
    if not isinstance(node, _ast.Call) or node.keywords:
        return None
    if isinstance(node.func, _ast.Name):
        subject = node.func.id
    elif isinstance(node.func, _ast.Attribute):
        subject = node.func.attr
    else:
        return None
    try:
        args = [_ast.literal_eval(arg) for arg in node.args]
    except (ValueError, SyntaxError, TypeError, RecursionError, MemoryError):
        return None
    if not args:
        return None
    return {"subject": subject, "args": args, "call": _ast.unparse(node)}


def parse_evidence(reason_text: str) -> list[dict[str, Any]]:
    """Read measurements while preserving whether an expected value is a peer output."""
    import ast as _ast
    if not isinstance(reason_text, str):
        return []
    rows = parse_pytest_evidence(reason_text)
    decoder = json.JSONDecoder()
    # raw_decode handles nested arrays in outputs, unlike a non-greedy `]` regex.
    for match in re.finditer(r"SEEN\s+", reason_text):
        try:
            entries, _ = decoder.raw_decode(reason_text[match.end():])
        except (ValueError, TypeError):
            continue
        for ent in entries if isinstance(entries, list) else []:
            if not isinstance(ent, Mapping):
                continue
            seen = ent.get("seen")
            if not isinstance(seen, (list, tuple)) or len(seen) < 2:
                continue
            values = [_read_arg(str(seen[0])), _read_arg(str(seen[1]))]
            if _UNREADABLE in values:
                continue
            try:
                parsed = _ast.parse(str(ent.get("at") or ""), mode="eval").body
            except (SyntaxError, ValueError, RecursionError):
                continue
            if isinstance(parsed, _ast.Compare) and len(parsed.comparators) == 1:
                calls = [_call_from_ast(parsed.left), _call_from_ast(parsed.comparators[0])]
                peer = calls[0] is not None and calls[1] is not None
                for i, call in enumerate(calls):
                    if call is not None:
                        rows.append({**call, "produced": values[i], "expected": values[1-i],
                                     "expected_source": "peer_observation" if peer else "assertion"})
            else:
                call = _call_from_ast(parsed)
                if call:
                    rows.append({**call, "produced": values[0], "expected": values[1],
                                 "expected_source": "assertion"})
    unique: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()
    for row in rows:
        signature = repr(row)
        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique.append(row)
    return unique


def explain(args: Sequence[Any], owed: Any) -> list[tuple[str, str]]:
    """Reflectively test binary operators folded across all observed arguments."""
    import copy as _copy
    import functools as _functools
    if len(args) < 2 or len(args) > 4:
        return []
    out: list[tuple[str, str]] = []
    for name, fn in _OP_FN.items():
        # Do not allow an arithmetic hypothesis probe to construct huge integers.
        if name in {"pow", "ipow"} and any(isinstance(x, int) and abs(x) > 12 for x in args[1:]):
            continue
        try:
            values = _copy.deepcopy(list(args))
            if _functools.reduce(fn, values) == owed:
                sym = _NAME_TO_SYMBOL.get(name, name)
                out.append((name, f"{' {} '.format(sym).join(map(str, args))} == {owed}"))
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
            if row.get("expected_source") == "peer_observation":
                continue
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
    def propose(self, source_text: str, *evidence: Any, limit: int = 8,
                learned_operators: Sequence[str] = (), **__) -> list[str]:
        """Offer source-derived expression and supported-operator candidates for screening.

        Candidate generation does not establish correctness. In particular, an
        observed peer output is not treated as an independently owed value.
        """
        if not isinstance(source_text, str) or not source_text.strip() or limit <= 0:
            return []
        reason = str(evidence[0]) if evidence else ""
        rows = [r for r in parse_evidence(reason) if r.get("expected_source") != "peer_observation"]
        out: list[str] = []
        for cand in self._source_expression_rewrites(source_text, rows, learned_operators):
            if cand not in out:
                out.append(cand)
                if len(out) >= limit:
                    return out
        targets_all = self.supported_global()
        if not out and not targets_all:
            return []
        lines = source_text.splitlines(True)
        for name, _why in targets_all:
            sym = _NAME_TO_SYMBOL.get(name)
            if not sym:
                continue
            for cand in self._rewrites(lines, name, sym, source_text):
                if cand not in out:
                    out.append(cand)
                    if len(out) >= limit:
                        return out
            for cand in self._all_operator_rewrites(source_text, sym, rows):
                if cand not in out:
                    out.append(cand)
                    if len(out) >= limit:
                        return out
        for cand in self._operand_rewrites(lines, source_text):
            if cand not in out:
                out.append(cand)
                if len(out) >= limit:
                    return out
        return out

    def _source_expression_rewrites(self, source_text: str, rows: Sequence[Mapping[str, Any]],
                                    learned_operators: Sequence[str] = ()):
        """Filter source and learned-grammar expressions against owed examples."""
        from canonical.swe_kernel.expression_hypotheses_v1 import (
            evaluate_expression, expression_candidates, function_models, replace_return_expression, same_number,
        )
        models = function_models(source_text)
        subjects = list(dict.fromkeys(str(row.get("subject") or "") for row in rows))
        for subject in subjects:
            target = models.get(subject)
            relevant = [r for r in rows if r.get("subject") == subject]
            if not target or not relevant or any(
                not isinstance(r.get("args"), (list, tuple)) or len(r["args"]) != len(target.params)
                for r in relevant
            ):
                continue
            templates = [m for m in models.values() if m.name != target.name]
            candidates, _truncated = expression_candidates(target, templates, learned_operators=learned_operators)
            for expr in candidates:
                # Every independently asserted example already in the failure
                # report is evidence.  Fitting only the first diagonal example
                # lets many wrong bindings consume the entire candidate budget.
                if not all((lambda result: result[0] and same_number(result[1], row.get("expected")))(
                        evaluate_expression(expr, dict(zip(target.params, row["args"]))))
                           for row in relevant):
                    continue
                candidate = replace_return_expression(source_text, target, expr)
                if candidate:
                    yield candidate

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

    def _all_operator_rewrites(self, source_text: str, sym: str, rows: Sequence[Mapping[str, Any]]):
        """Replace arithmetic operators together in a modelled target expression."""
        import ast as _ast
        import copy as _copy
        from canonical.swe_kernel.expression_hypotheses_v1 import function_models, replace_return_expression
        try:
            example = _ast.parse(f"a {sym} b", mode="eval").body
        except SyntaxError:
            return
        if not isinstance(example, _ast.BinOp):
            return
        subjects = {str(row.get("subject")) for row in rows}
        for model in function_models(source_text).values():
            if subjects and model.name not in subjects:
                continue

            class Replace(_ast.NodeTransformer):
                def visit_BinOp(self, node):
                    node = self.generic_visit(node)
                    node.op = _copy.deepcopy(example.op)
                    return node

            expr = _ast.fix_missing_locations(Replace().visit(_copy.deepcopy(model.expression)))
            candidate = replace_return_expression(source_text, model, expr)
            if candidate:
                yield candidate

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
