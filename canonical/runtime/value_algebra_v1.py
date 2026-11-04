"""Answers are BUILT OUT OF typed pieces, not looked up in a menu.

THE DEFECT THIS REPLACES
------------------------
`operation_trial_v1` moved dispatch from English phrasings to the tree, and that was
real progress: it resolved what a sentence names and tried the operations those things
permitted. But every operation it tried was a CLOSED FUNCTION with a hand-written name
(`_op_count_lines`, `_op_aggregate`, ...) and NO OPERATION'S INPUT COULD BE ANOTHER
OPERATION'S OUTPUT. Measured on five questions that need two steps:

    how many digits are in the total of the amounts      -> refused
    what is the average of the totals in a.csv and b.csv -> refused
    what is the largest amount doubled                   -> refused
    which region has the largest amount                  -> refused
    is the total of a.csv less than the total of b.csv   -> refused

0 of 5. Not because the door was wrong -- those refusals were honest -- but because
seven primitives can only ever answer seven shapes. Adding an eighth primitive for each
new question is the same defect as adding a ninth regex, displaced one layer up: the
answer space grows by ONE per unit of work.

WHAT REPLACES IT
----------------
Values have TYPES, and operators are typed. A number can be summed; a numeric column can
be summed into a number; a number can be counted, doubled, compared, or used to select a
row; a row can yield a cell; a cell is text. Because the operators COMPOSE, the set of
answerable questions is the PRODUCT of the primitives, not their sum. Ten primitives do
not answer ten questions; they answer the questions that can be built from ten typed
pieces, and nobody writes those down.

This is the difference between a menu and a grammar. It is also the difference the user
kept naming: a static program enumerates its answers, and a system that composes them
does not.

VERIFICATION, WHICH IS NOT OPTIONAL
-----------------------------------
Every node re-derives itself from the tree. A leaf re-reads the file and re-extracts the
values; an operator re-applies itself to its children's re-derived values. What is
returned is the value of a re-derived tree, or nothing. That is the same discipline the
counts always had, applied to the whole expression rather than to one step of it.

ACCOUNTING, WHICH IS ALSO NOT OPTIONAL
--------------------------------------
Every node declares which of the question's words it CONSUMES. The root's consumed set
must cover the question's subject. A composition that computes something perfectly and
leaves `digit` or `largest` or `region` unaccounted for is not an answer to the question
asked -- it is a correct answer to a different question. Measured before this rule:
`sum` won "how many digits are in the total", returned 500, verified, and was wrong.

The word lists below map words to PRIMITIVES. That mapping is irreducible -- a word has
to mean something -- but it is not a list of QUESTIONS: nothing here knows what any
particular sentence looks like.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_VALUE_ALGEBRA_V1"

_MAX_STEPS = 3_000          # hard search bound, so a bad question cannot hang the door


# ---------------------------------------------------------------------------
# Types. A value knows what it is, and an operator says what it accepts and returns.
# This is what makes composition checkable instead of guessed.
# ---------------------------------------------------------------------------

NUMBER = "number"
NUMVEC = "numvec"          # several numbers, e.g. one total per file
TEXT = "text"
TEXTVEC = "textvec"        # lines, or the cells of a column
ROW = "row"
TABLE = "table"
BOOL = "bool"


# ---------------------------------------------------------------------------
# Leaves: values taken from the tree.
# ---------------------------------------------------------------------------

class Node:
    """One typed value, with what it consumes and how to re-derive it."""

    __slots__ = ("op", "args", "type", "consumes", "label")

    def __init__(self, op: str, args: tuple, type: str, consumes: frozenset, label: str):
        self.op = op
        self.args = args
        self.type = type
        self.consumes = consumes
        self.label = label

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{self.label}:{self.type}>"


def _n(op, args, type, consumes, label):
    return Node(op, args, type, frozenset(consumes), label)


# --- tree readers. Each one is the ONLY place that touches disk for its kind. ---

def _read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:4096] or len(raw) > 2_000_000:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _rows_of(path: Path) -> list[list[str]] | None:
    text = _read_text(path)
    if text is None or not text.strip():
        return None
    try:
        rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    except Exception:
        return None
    return rows or None


def _to_float(cell: str) -> float | None:
    s = cell.strip().replace(",", "").replace("$", "").replace("%", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _norm(s: str) -> str:
    s = s.strip().lower()
    if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    return s


# ---------------------------------------------------------------------------
# Operators. (accepted type, result type, apply, words that select it)
# ---------------------------------------------------------------------------

def _aggregate(kind: str):
    fn = {
        "sum": lambda v: sum(v),
        "max": lambda v: max(v),
        "min": lambda v: min(v),
        "mean": lambda v: sum(v) / len(v),
        "count": lambda v: len(v),
    }[kind]

    def apply(values, *_):
        vals = list(values)
        if not vals:
            return None
        return fn(vals)

    return apply


def _digits(x, *_):
    """How many decimal digits the integer part has. A count, not a formatting choice."""
    n = abs(int(round(float(x))))
    return len(str(n)) if n else 1


def _double(x, *_):
    return float(x) * 2


def _half(x, *_):
    return float(x) / 2


def _negate(x, *_):
    return -float(x)


def _length(x, *_):
    return len(str(x))


def _cell_of(row, column):
    cells = row.get("_cells") or []
    idx = row.get("_index") or {}
    key = _norm(str(column))
    for name, i in idx.items():
        if _norm(name) == key and i < len(cells):
            return cells[i]
    return None


# words that select each operator. NOT a list of questions -- a lexicon of primitives.
_AGG_WORDS = {
    "sum": {"total", "sum", "added", "altogether", "combined", "overall", "add"},
    "max": {"largest", "biggest", "max", "maximum", "highest", "most", "greatest", "top"},
    "min": {"smallest", "least", "min", "minimum", "lowest", "fewest", "bottom"},
    "mean": {"average", "mean", "typical", "avg"},
    "count": {"how", "many", "number", "count"},
}
# The lexicon of UNARY PRIMITIVES. A word has to mean something; nothing here knows
# what any particular sentence looks like, and every operator composes with all the rest.
_MAP_WORDS = {
    "digits": {"digit", "digits"},
    "double": {"double", "doubled", "double", "twice", "two", "multiplied", "times",
               "tripled"},
    "half": {"half", "halved", "divided"},
    "negate": {"negated", "inverted", "negated"},
    "length": {"length", "characters", "chars"},
}
_CMP_WORDS = {
    "lt": {"less", "fewer", "below", "under", "smaller"},
    "gt": {"greater", "more", "above", "over", "bigger", "exceeds"},
    "eq": {"equal", "same", "equals"},
}
_SELECT_WORDS = {"which", "what", "whose", "row", "record", "entry"}
_VECTOR_WORDS = {"totals", "total", "sums", "sum", "amounts", "values", "averages"}


# ---------------------------------------------------------------------------
# Building candidate expressions from the entities and the question's words.
# ---------------------------------------------------------------------------

class Lexicon:
    """The question's words, minus what the entities already are."""

    def __init__(self, words: list[str]):
        self.raw = [w.lower() for w in words]
        self.set = set(self.raw)

    def pick(self, table: dict[str, set[str]]) -> list[str]:
        return [k for k, ws in table.items() if self.set & ws]

    def without(self, used: frozenset) -> set[str]:
        return self.set - set(used)


def _columns(path: Path) -> tuple[list[str], list[list[str]]] | None:
    rows = _rows_of(path)
    if not rows or len(rows) < 2:
        return None
    return rows[0], rows[1:]


def _numeric_columns(header: list[str], rows: list[list[str]]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for i, name in enumerate(header):
        vals = []
        ok = True
        for r in rows:
            if i >= len(r):
                ok = False
                break
            v = _to_float(r[i])
            if v is None:
                ok = False
                break
            vals.append(v)
        if ok and vals:
            out[name] = vals
    return out


def _column_leaf(path: Path, rel: str, name: str, consumes: set[str]) -> Node | None:
    """A numeric column, resolved from the file's own header."""
    got = _columns(path)
    if got is None:
        return None
    header, rows = got
    nums = _numeric_columns(header, rows)
    idx = {_norm(h): h for h in header}
    target = None
    if _norm(name) in idx:
        target = idx[_norm(name)]
    else:
        for h in header:
            if _norm(h) and (_norm(h) in _norm(name) or _norm(name) in _norm(h)) and len(_norm(h)) > 2:
                target = h
                break
    if target is None or target not in nums:
        return None
    return _n("column", (str(path), target), NUMVEC, consumes, f"col:{target}@{rel}")


def _column_at(rel: str, name: str) -> list[float] | None:
    got = _columns(Path(rel))
    if got is None:
        return None
    header, rows = got
    return _numeric_columns(header, rows).get(name)


# ---------------------------------------------------------------------------
# Evaluation: re-derive from disk, top to bottom. Nothing is cached between runs.
# ---------------------------------------------------------------------------

class EvalError(Exception):
    pass


def _row_leaf(rel: str, column: str, index: int, header: list[str]) -> dict:
    rows = _rows_of(Path(rel))
    if rows is None or index >= len(rows) - 1:
        raise EvalError("row gone")
    cells = rows[index + 1]
    return {"_cells": cells, "_index": {h: i for i, h in enumerate(header)}}


def evaluate(node: Node, *, derived: dict | None = None) -> object:
    """The value of an expression, computed freshly from the tree."""
    op = node.op
    if op == "column":
        rel, name = node.args
        vals = _column_at(rel, name)
        if vals is None:
            raise EvalError(f"column {name!r} gone")
        return vals
    if op == "aggregate":
        kind, child = node.args
        return _aggregate(kind)(evaluate(child), kind)
    if op == "map":
        kind, child = node.args
        v = evaluate(child)
        fn = {"digits": _digits, "double": _double, "half": _half,
              "negate": _negate, "length": _length}[kind]
        return fn(v)
    if op == "compare":
        kind, left, right = node.args
        a, b = evaluate(left), evaluate(right)
        return {"lt": a < b, "gt": a > b, "eq": abs(float(a) - float(b)) < 1e-9}[kind]
    if op == "vector":
        return [evaluate(c) for c in node.args[0]]
    if op == "argmax":
        rel, column, by, extreme = node.args
        rows = _rows_of(Path(rel))
        if rows is None:
            raise EvalError("table gone")
        header, body = rows[0], rows[1:]
        idx = {h: i for i, h in enumerate(header)}
        if by not in idx:
            raise EvalError("column gone")
        better = (lambda v, best: v > best) if extreme == "max" \
            else (lambda v, best: v < best)
        best, best_i = None, None
        for i, r in enumerate(body):
            if idx[by] >= len(r):
                continue
            v = _to_float(r[idx[by]])
            if v is None:
                continue
            if best is None or better(v, best):
                best, best_i = v, i
        if best_i is None:
            raise EvalError("no numeric rows")
        return {"_cells": body[best_i], "_index": idx, "_row": best_i}
    if op == "cell":
        row, column = node.args
        v = _cell_of(evaluate(row), column)
        if v is None:
            raise EvalError("no such cell")
        return v
    raise EvalError(f"unknown op {op}")


# ---------------------------------------------------------------------------
# The search. Typed, bounded, and driven by the question's own words.
# ---------------------------------------------------------------------------

def _candidate_columns(lex: Lexicon, header: list[str] | None,
                       numeric: list[str] | None = None) -> list[str]:
    """Which column the question is about, decided by the FILE'S header.

    When the question names no column and the file has exactly ONE numeric column, that
    column is the referent: the tree resolves it, and the question does not have to use
    the header's spelling. This was missing here after being added to the single-file
    aggregate, and it made every multi-file question unbuildable over columns called
    `x` -- the same fix, needed twice, which is why it now lives in one place.
    """
    if not header:
        return []
    wanted = {_norm(w) for w in lex.raw}
    out = [h for h in header if _norm(h) in wanted]
    if out:
        return out
    out = [h for h in header if any(
        _norm(h) and (_norm(h) in _norm(w) or _norm(w) in _norm(h)) and len(_norm(h)) > 2
        for w in lex.raw)]
    if out:
        return out
    if numeric and len(numeric) == 1:
        return list(numeric)
    return []


def compose(question: str, root: str, ents, words: list[str]) -> dict | None:
    """Try to BUILD an answer out of typed pieces. None when nothing builds.

    The search is bounded and typed, and it is not a table of question shapes: it
    enumerates operators that TYPE-CHECK against the values the tree provides, which is
    why a question nobody wrote down can still be answered.
    """
    lex = Lexicon(words)
    steps = 0
    files = [e for e in ents if e.kind == "file"]

    aggs = lex.pick(_AGG_WORDS)
    maps = lex.pick(_MAP_WORDS)
    cmps = lex.pick(_CMP_WORDS)
    # ASKING FOR A ROW IS ASKING FOR ONE OF ITS CELLS.
    #
    # "which region has ...", "which item has ...", "whose amount is highest" all ask
    # for a cell of the extreme row. The trigger is not a list of column names -- it is
    # whether the question names a column the row can yield, OR uses a word that asks
    # for one. `item` was only in the latter, which is where it failed.
    _selection_headers: set[str] = set()
    for _e in files:
        _got = _columns(_e.path)
        if _got is not None:
            _h, _r = _got
            _selection_headers |= {_norm(h) for h in _h}
    wants_select = (bool(lex.set & _SELECT_WORDS)
                    or bool({_norm(w) for w in lex.set} & _selection_headers)
                    or bool(lex.set & {"region", "name", "label", "item", "name"}))

    # ---- leaf columns ----------------------------------------------------
    # Every (entity, column) pair the words point at, with the words it consumes.

    column_leaves: list[Node] = []
    tables: dict[str, tuple[list[str], list[list[str]]]] = {}
    for ent in files:
        got = _columns(ent.path)
        if got is None:
            continue
        header, rows = got
        tables[ent.rel] = got
        numeric_names = list(_numeric_columns(header, rows))
        for name in _candidate_columns(lex, header, numeric_names):
            steps += 1
            if steps > _MAX_STEPS:
                return None
            consumed = {w for w in lex.set if _norm(w) == _norm(name)
                        or (_norm(name) and _norm(name) in _norm(w))}
            node = _column_leaf(ent.path, ent.rel, name, consumed)
            if node is not None:
                column_leaves.append(node)

    if not column_leaves:
        return None

    # ---- build: aggregate over column, or over per-file aggregates --------

    def per_file_aggregates(kind: str) -> Node | None:
        """`mean` over one total from each file -- "the average of the totals"."""
        wanted = {w for w in lex.set if _norm(w) in {_norm(x) for x in _VECTOR_WORDS}}
        parts: list[Node] = []
        used = set()
        for ent in files:
            got = tables.get(ent.rel)
            if got is None:
                continue
            header, rows = got
            nums = _numeric_columns(header, rows)
            if len(nums) != 1:
                continue
            (colname, _vals), = nums.items()
            leaf = _column_leaf(ent.path, ent.rel, colname,
                                {x for x in lex.set if _norm(x) == _norm(colname)})
            if leaf is None:
                continue
            inner = _n("aggregate", ("sum", leaf), NUMBER, set(), f"sum({leaf.label})")
            parts.append(inner)
            used |= {w for w in lex.set if _norm(w) == _norm(colname)}
        if len(parts) < 2:
            return None
        # THE LABEL MUST SHOW THE STRUCTURE.
        #
        # This said `mean(totals)`, which is true and hides that the mean is over TWO
        # separately computed sums -- a reader could not tell a one-step average of a
        # column from a two-step average of totals. An answer's expression is the
        # evidence that it was built, so it has to be legible.
        vec = _n("vector", (tuple(parts),), NUMVEC, wanted | used,
                 "vector(" + ",".join(part.label for part in parts) + ")")
        return _n("aggregate", (kind, vec), NUMBER, wanted,
                  f"{kind}({vec.label})")

    candidates: list[Node] = []

    for kind in aggs:
        for leaf in column_leaves:
            candidates.append(_n("aggregate", (kind, leaf), NUMBER,
                                 lex.set & _AGG_WORDS[kind], f"{kind}({leaf.label})"))
        pv = per_file_aggregates(kind)
        if pv is not None:
            candidates.append(pv)

    # ---- map: digits / double / half over a number -----------------------
    if maps:
        bases = list(candidates) + [_n("aggregate", (a, l), NUMBER, lex.set & _AGG_WORDS[a],
                                       f"{a}({l.label})")
                                    for a in aggs for l in column_leaves]
        for m in maps:
            for b in bases:
                candidates.append(_n("map", (m, b), NUMBER,
                                     lex.set & _MAP_WORDS[m], f"{m}({b.label})"))

    # ---- select a row by an extreme, then take a cell --------------------
    if wants_select and aggs and tables:
        for by_kind in ("max", "min"):
            if by_kind not in aggs:
                continue
            for ent in files:
                got = tables.get(ent.rel)
                if got is None:
                    continue
                header, rows = got
                nums = _numeric_columns(header, rows)
                for by_col in nums:
                    row = _n("argmax", (ent.path, ent.rel, by_col, by_kind), ROW,
                             lex.set & _AGG_WORDS[by_kind] | {_norm(by_col)}
                             | {w for w in lex.set if _norm(w) == _norm(by_col)},
                             f"argmax:{by_col}@{ent.rel}")
                    candidates.append(row)
                    # A CELL IS TEXT ONLY IF THAT COLUMN HOLDS TEXT.
                    #
                    # This offered every column, so "which item has the biggest price"
                    # could return a PRICE -- a number presented as the name of the
                    # thing. The type has to be decided by the data, not by the word
                    # `which`: a cell is text when the column it comes from is text.
                    for h in header:
                        if h == by_col or h in nums:
                            continue
                        candidates.append(_n("cell", (row, h), TEXT,
                                             {_norm(h)}, f"cell[{h}]({row.label})"))

    # ---- compare two numbers --------------------------------------------
    if cmps:
        # A comparison needs one number from each of two files -- not an aggregate word in
        # the question. "is the total of a.csv less than the total of b.csv" names `total`;
        # "is a.csv bigger than b.csv" does not, and both are comparisons.
        #
        # WHICH COLUMN is resolved the way every other column is: the question's own word
        # when it names one ("the total UNITS in ..."), and only when it names none does
        # the file have to have exactly one numeric column. Requiring the count to be one
        # made a comparison impossible on any file with two numeric columns, even when the
        # question said which one it meant.
        sums: dict[str, Node] = {}
        for ent in files:
            got = tables.get(ent.rel)
            if got is None:
                continue
            header, rows = got
            nums = _numeric_columns(header, rows)
            if not nums:
                continue
            chosen = _candidate_columns(lex, header, list(nums))
            chosen = [c for c in chosen if c in nums]
            if len(chosen) != 1:
                continue
            # THE COLUMN WORD IS PART OF THE ACCOUNT, even when it was resolved by the
            # file rather than by the question. Building this leaf with an empty
            # `consumes` left `units` unaccounted for and rejected the whole comparison
            # -- the door refusing a question it had already worked out: True, and the
            # true answer was False. An answer that is not accounted for is not shown,
            # so an under-accounted CORRECT computation reads as a refusal.
            col_consumed = {x for x in lex.set
                            if _norm(x) == _norm(chosen[0])
                            or (_norm(chosen[0]) and _norm(chosen[0]) in _norm(x))}
            leaf = _column_leaf(ent.path, ent.rel, chosen[0], col_consumed)
            if leaf is not None:
                sums[ent.rel] = _n("aggregate", ("sum", leaf), NUMBER, set(),
                                   f"sum({leaf.label})")
        if len(sums) == 2:
            # OPERAND ORDER IS THE SENTENCE'S ORDER, NOT THE RESOLVER'S.
            #
            # Entities come back in resolution order, which is neither reading order nor
            # meaningful. `lt(a, b)` means a < b, so taking the dict's order literally
            # made "is the total units in returns.csv less than the total units in
            # inventory.csv" answer `False` -- the reverse of the truth, verified, and
            # rendered as an answer. A relation is between its operands AS WRITTEN.
            ordered = sorted(sums.items(), key=lambda kv: question.find(kv[0]))
            (ra, a), (rb, b) = ordered
            for kind in cmps:
                candidates.append(_n("compare", (kind, a, b), BOOL,
                                     lex.set & _CMP_WORDS[kind], f"{kind}({ra},{rb})"))

    # ---- choose: right type, accounts for the question, verifies ---------
    # THE TYPE OF THE ANSWER IS WHAT WAS ASKED FOR.
    #
    # This became TEXT whenever any column was named, so "what is the total of the
    # amounts in sales.csv" -- which names the column `amount` -- stopped accepting a
    # NUMBER and the question went unbuilt. Select only when a row is asked for AND no
    # aggregate was: an aggregate over a named column is still a number.
    if cmps:
        want_types = {BOOL}
    elif wants_select and not aggs:
        want_types = {TEXT}
    elif wants_select and aggs:
        want_types = {TEXT, NUMBER}
    else:
        want_types = {NUMBER}

    best = None
    for cand in candidates:
        steps += 1
        if steps > _MAX_STEPS:
            break
        if cand.type not in want_types:
            continue
        # THE ROOT MUST ACCOUNT FOR THE QUESTION'S WORDS.
        # A correct answer to a different question is not an answer.
        left = lex.without(cand.consumes | _structural_words(cand))
        if left - _noise:
            continue
        try:
            value = evaluate(cand)
        except (EvalError, TypeError, ValueError, ZeroDivisionError):
            continue
        if value is None:
            continue
        best = (cand, value)
        break

    if best is None:
        return None
    cand, value = best
    return {"node": cand, "value": value,
            # WHAT THE EXPRESSION CONSUMED, stated by the expression. Reconstructing this
            # from the operation's name is what reported `digits` as an unanswered word
            # of a question that had just been answered with the digits.
            "accounted": sorted(cand.consumes | _structural_words(cand))}


# Words that describe the ACT of asking rather than the thing asked about.
_noise = {
    "how", "many", "what", "which", "is", "are", "the", "of", "in", "a", "an", "and",
    "do", "does", "it", "that", "this", "there", "for", "to", "than", "then", "be",
    "tell", "me", "give", "show", "please", "from", "on", "at", "by", "with", "value",
    "result", "answer",
}


def _structural_words(node: Node) -> frozenset:
    """Every word an expression consumes, at any depth.

    This must start from the node's OWN `consumes` and union the children, not rebuild
    the set from the operators alone. Rebuilding dropped what each leaf had already
    accounted for -- the column leaf consumed `amounts`, this function did not know it,
    and every composition was rejected with `amounts` unaccounted. Two derivations of
    one fact, disagreeing: the same defect as the three phrasing lists, one layer down
    inside the replacement for them.
    """
    out: set[str] = set(node.consumes)
    if node.op == "aggregate":
        out |= _AGG_WORDS.get(node.args[0], set())
        out |= _structural_words(node.args[1])
    elif node.op == "map":
        out |= _MAP_WORDS.get(node.args[0], set())
        out |= _structural_words(node.args[1])
    elif node.op == "compare":
        out |= _CMP_WORDS.get(node.args[0], set())
        out |= _structural_words(node.args[1]) | _structural_words(node.args[2])
    elif node.op == "vector":
        for c in node.args[0]:
            out |= _structural_words(c)
        out |= _VECTOR_WORDS
    elif node.op == "cell":
        out |= _structural_words(node.args[0])
    elif node.op == "argmax":
        out |= _SELECT_WORDS | {"row", "record", "entry"}
    return frozenset(out)


# ---------------------------------------------------------------------------
# Re-derivation. The expression is rebuilt from the tree and re-evaluated; only the
# re-derived value is ever reported.
# ---------------------------------------------------------------------------

def verify(question: str, root: str, result: dict) -> bool:
    node = result.get("node")
    if node is None:
        return False
    try:
        again = evaluate(node)
    except (EvalError, TypeError, ValueError, ZeroDivisionError):
        return False
    a, b = again, result.get("value")
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    return a == b


def describe(node: Node) -> str:
    return node.label


def render(result: dict) -> str:
    node = result["node"]
    value = result["value"]
    if isinstance(value, bool):
        text = "yes" if value else "no"
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value)
    return f"{text}   [built: {node.label}]"
