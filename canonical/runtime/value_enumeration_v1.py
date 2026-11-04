"""An answer is SEARCHED FOR, not looked up in a list of sentences.

WHY THIS FILE EXISTS.

`value_algebra_v1.compose` is 1,500 lines holding 17 operators and 16 `candidates.append`
calls, and there is not one loop in it that enumerates compositions. Measured: across ten
varied questions it produced FIVE distinct operator structures, and a question needing an
operator nobody had appended -- median, ratio, running total -- was refused while every
mechanism to answer it sat in the same file, unreachable.

That is the defect this project keeps re-finding one layer down. The primitives were
made typed, then composable, then sound. But the SET OF EXPRESSIONS was still a hand-
written list, so adding an operator added ONE answer instead of every composition of it.
A perfect verifier bolted to a fixed list certifies a fixed list.

WHAT THIS IS.

The operators become DATA: each carries its argument types, the type it produces, and
the words that name it. The search then walks that data by TYPE -- from the question's
columns outward, up to a bounded depth -- building every well-typed expression it can,
and asking the soundness check about each one. Adding an operator to `_OPERATORS` adds
every expression containing it, without anybody writing a sentence.

    compose      = enumerate well-typed trees, then choose
    _OPERATORS   = the whole vocabulary, in one place
    choose       = the existing scorer, untouched

The incumbent search is NOT replaced. Both run, and `compose` prefers the answer that
accounts for more of the question -- so this can only be an improvement or a measured
no-op, never a regression, until it has earned standing.

Every expected value in the tests is computed BY HAND from the fixture.
"""

from __future__ import annotations

import itertools

from canonical.runtime.value_algebra_v1 import (
    BOOL,
    NUMBER,
    NUMVEC,
    ROW,
    TABLE,
    TEXT,
    TEXTVEC,
    EvalError,
    Lexicon,
    Node,
    _AGG_WORDS,
    _CMP_WORDS,
    _MAP_WORDS,
    _columns,
    _literal_values,
    _n,
    _norm,
    _numeric_candidates,
    _numeric_columns,
    _structural_words,
    _text_candidates,
    evaluate,
    holds,
)

SCHEMA = "PROJECT_BRAIN_VALUE_ENUMERATION_V1"

# HOW DEEP THE SEARCH GOES.
#
# Not a magic number -- it is the number of OPERATOR LEVELS a useful answer can need.
# "the total in west" is aggregate(column_from(filter(table))): three operators stacked.
# A depth of 2 built the filter and the column but never the aggregate above them, so the
# question had no expression even though every piece of it had been constructed. The
# bound exists to stop an unbounded product, not to guess at sentence length.
_MAX_DEPTH = 5
# A hard ceiling on leaves and on generated expressions. A cap that is hit is recorded,
# never silently taken as "no answer exists".
_MAX_EXPRESSIONS = 4000
_MAX_PER_SHAPE = 60


# ---------------------------------------------------------------------------
# THE OPERATORS, AS DATA.
#
# Each entry: name, (argument types), result type, and the words that name it. This is
# the whole vocabulary in one place -- the inventory the old search kept spread across
# sixteen appends and eight separate word tables.
# ---------------------------------------------------------------------------
_ROW_AGGREGATES = ("count",)

_OPERATORS: dict[str, dict] = {
    "aggregate": {"args": ("AGG", "NUMVEC"), "type": NUMBER},
    "map": {"args": ("MAP", "NUMBER"), "type": NUMBER},
    "compare": {"args": ("CMP", "NUMBER", "NUMBER"), "type": BOOL},
    "vector": {"args": ("NUMVEC*",), "type": NUMVEC},
    "count": {"args": (("TEXTVEC", "NUMVEC", TABLE),), "type": NUMBER},
    "distinct": {"args": ("TABLE", "COL"), "type": TEXTVEC},
    "values_of": {"args": ("TABLE", "COL"), "type": (TEXTVEC, NUMVEC)},
    "filter": {"args": ("TABLE", "COL", "LIT"), "type": TABLE},
    "group": {"args": ("TABLE", "COL", "COL"), "type": "grouped"},
    "groups": {"args": ("grouped", "AGG", "COL", "COL"), "type": TABLE},
    "column_from": {"args": ("TABLE", "COL"), "type": NUMVEC},
    "argmax_table": {"args": ("TABLE", "COL", "EXTREME"), "type": ROW},
    "cell": {"args": ("ROW", "COL"), "type": (TEXT, NUMBER)},
    "contains_all": {"args": ("TEXTVEC", "TEXTVEC"), "type": BOOL},
}

_AGG_NAMES = tuple(_AGG_WORDS)
_MAP_NAMES = tuple(_MAP_WORDS)
_CMP_NAMES = tuple(_CMP_WORDS)


def _algebra():
    """The algebra module itself, so the vocabulary is never a stale import."""
    from canonical.runtime import value_algebra_v1 as _V
    return _V


def operator_inventory() -> dict:
    """The vocabulary as data -- what the search can actually build from."""
    return {k: dict(v) for k, v in _OPERATORS.items()}


# ---------------------------------------------------------------------------
# Leaves: what the tree offers, before any operator is applied.
# ---------------------------------------------------------------------------

def _distinct_values(rows: list, header: list[str], column: str) -> int:
    """How many distinct non-empty values a column holds -- does it partition the rows?"""
    if column not in header:
        return 0
    i = header.index(column)
    seen = set()
    for r in rows:
        if i < len(r):
            cell = r[i]
            if isinstance(cell, str) and cell.strip():
                seen.add(_norm(cell.strip()))
    return len(seen)


def _leaves(lex: Lexicon, tables: dict, files: list) -> dict[str, list[Node]]:
    """Every well-typed starting point the question and the files provide, by type."""
    out: dict[str, list[Node]] = {TABLE: [], NUMVEC: [], TEXTVEC: [], "grouped": []}

    for ent in files:
        got = tables.get(getattr(ent, "rel", None))
        if got is None:
            continue
        header, rows = got
        numeric = list(_numeric_columns(header, rows))

        table = _n("table", (str(ent.path),), TABLE, set(), f"t@{ent.rel}")
        out[TABLE].append(table)

        # A column the question names, and -- when it names none -- the file's own
        # columns, because "the total in sales.csv" names a file and no column.
        for col in _numeric_candidates(lex, header, numeric)[:2]:
            out[NUMVEC].append(_n("column", (str(ent.path), col), NUMVEC,
                                  {_norm(col)}, f"col:{col}@{ent.rel}"))
        for col in _text_candidates(lex, header, numeric)[:2]:
            out[TEXTVEC].append(_n("values_of", (table, col), TEXTVEC,
                                   {_norm(col)}, f"values({col})@{ent.rel}"))

        if not _numeric_candidates(lex, header, numeric) and len(numeric) == 1:
            col = numeric[0]
            out[NUMVEC].append(_n("column", (str(ent.path), col), NUMVEC,
                                  set(), f"col:{col}@{ent.rel}"))

        # A grouping is a productive type: it is the leaf that makes "per <key>" and
        # "which <key> has the most" expressible at all.
        # A GROUPING KEY IS A COLUMN THAT IDENTIFIES ROWS, AND THE QUESTION NAMES IT.
        #
        # `_text_candidates` only offers columns the question names, and `_literal_values`
        # only finds VALUES the question names -- so "how many rows per region" named
        # `region`, which is a HEADER, and neither test matched it. The key was then found
        # by a fallback that skipped every column whose values were not in the question and
        # stopped at the first hit -- which gave ONE group, and the answer to a per-region
        # question was a list of one number.
        #
        # A key is any non-numeric column that actually partitions the rows. How many
        # groups it produces is a fact about the data, so the only requirement is that it
        # produces more than one; whether the question spelled it out decides ORDER.
        keys = _text_candidates(lex, header, numeric)
        named = [_norm(w) for w in lex.raw]
        for h in header:
            if h in numeric or h in keys:
                continue
            if _distinct_values(rows, header, h) > 1:
                keys.append(h)
        # a key the question named comes first; the rest are still available
        keys.sort(key=lambda k: 0 if _norm(k) in named else 1)
        vals = _numeric_candidates(lex, header, numeric) or (numeric if len(numeric) == 1 else [])
        for key in keys[:2]:
            # A GROUPING OVER "*" COUNTS ROWS.
            #
            # The question "how many rows per region" names a region and a count and no
            # quantity at all, so a grouping keyed on a NUMERIC COLUMN cannot express it:
            # count(amount) counts the cells that parse, and drops a row whose amount is
            # blank. The row itself is the quantity, so "*" is offered as one. This is a
            # leaf entry and nothing else -- `groups` already knows how to aggregate "*",
            # and no branch in `compose` was written for it.
            # "*" IS ONLY EVER COUNTED.
            #
            # Offered as a grouping quantity, `*` composed with every aggregate: `sum`
            # over it read each row as 1 and "the total amount" answered 5.0 -- the row
            # COUNT wearing the shape of a total, which is the worst kind of wrong answer
            # because it is a plausible number. A row has a count and nothing else, so
            # the aggregates it may feed are stated here rather than left to the
            # adjective in the question.
            out["grouped"].append(
                _n("group", (table, key, "*"), "grouped", set(),
                   f"group[{key}][row]@{ent.rel}"))
            for val in vals[:2]:
                out["grouped"].append(
                    _n("group", (table, key, val), "grouped", set(),
                       f"group[{key}]@{ent.rel}"))
    return out


# ---------------------------------------------------------------------------
# Application: one operator, applied to a pool of values, producing a pool.
# ---------------------------------------------------------------------------

def _apply(name: str, pool: dict, lex: Lexicon, tables: dict,
           question: str = "") -> list[Node]:
    """Every node of `name` that type-checks against the pool, with no sentence written."""
    made: list[Node] = []
    spec = _OPERATORS[name]
    args = spec["args"]

    if name == "aggregate":
        # THE AGGREGATES COME FROM THE VOCABULARY, NOT FROM A TUPLE BESIDE IT.
        #
        # This looped over `_AGG_NAMES`, a second list that had to be edited whenever the
        # vocabulary was: adding `median` to `_AGG_WORDS` and to the evaluator produced
        # ZERO new expressions, because the builder never looked. That is the static menu
        # with an extra step -- the list had only moved from `compose` into this file.
        # Reading `_AGG_WORDS` makes the word table the single statement of which
        # aggregates exist, so a declaration IS a capability.
        #
        # AND READ THROUGH THE MODULE, NOT THROUGH A COPY TAKEN AT IMPORT.
        #
        # `from ... import _AGG_WORDS` binds the dict object once. Rebinding or extending
        # the vocabulary at runtime then changes the algebra and not this file, so a
        # declared operator produced no expressions and the two disagreed silently. The
        # module reference cannot go stale.
        words = _algebra()._AGG_WORDS
        for kind in tuple(words):
            # PLURALS ARE THE SAME WORD. The old search learned this (`names` had to
            # cancel `name`); the enumerator was written without it, so `totals` matched
            # no aggregate and "the average of the totals in a.csv and b.csv" could not
            # build a single `sum` -- the question was refused with no sum anywhere in
            # its enumeration.
            consumed = _words_matching(lex, words[kind])
            if not consumed:
                continue
            for child in pool.get(NUMVEC, [])[:_MAX_PER_SHAPE]:
                made.append(_n("aggregate", (kind, child), NUMBER, consumed,
                               f"{kind}({child.label})"))

    elif name == "map":
        for kind in _MAP_NAMES:
            # AN OPERATOR APPLIES ONLY WHEN THE QUESTION ASKED FOR IT.
            #
            # `double` is in the vocabulary, so every number could be doubled, and
            # "the total amount in sales.csv" was answered 1100 -- the sum of the file,
            # twice. The word sets are the question's side of the contract; an operator
            # that consumes no word of the question is not a candidate, it is a bigger
            # number. The same defect made `count` answer 8 for "how many regions".
            consumed = _words_matching(lex, _MAP_WORDS[kind])
            if not consumed:
                continue
            for child in pool.get(NUMBER, [])[:_MAX_PER_SHAPE]:
                made.append(_n("map", (kind, child), NUMBER, consumed,
                               f"{kind}({child.label})"))

    elif name == "compare":
        # OPERAND ORDER IS THE SENTENCE'S ORDER.
        #
        # `lt(a, b)` means a < b. The incumbent search learned this the hard way: taking
        # the resolver's dict order made a true statement answer False. An enumerator is
        # worse, because it builds BOTH orders and would pick one by label. So the order
        # is taken from where each operand's source file appears in the question, and a
        # comparison whose operands cannot be ordered by the sentence is not built.
        for kind in _CMP_NAMES:
            consumed = _words_matching(lex, _CMP_WORDS[kind])
            if not consumed:
                continue              # a comparison nobody asked for is not an answer
            operands = pool.get(NUMBER, [])[:6]
            for left, right in itertools.permutations(operands, 2):
                lpos, rpos = (_sentence_position(left, lex, question),
                              _sentence_position(right, lex, question))
                if lpos is None or rpos is None or lpos >= rpos:
                    continue          # not the order the sentence gives them
                made.append(_n("compare", (kind, left, right), BOOL, consumed,
                               f"{kind}({left.label},{right.label})"))

    elif name == "vector":
        # A VECTOR IS SEVERAL SOURCES, NOT SEVERAL WAYS OF READING ONE.
        #
        # "the average of the totals in a.csv and b.csv" needs [sum(a), sum(b)]. Taking
        # the first four numbers in the pool instead built vectors of four different
        # reductions OF THE SAME COLUMN, and `sum(...)` of that scored highest of all:
        # "the total in west" was answered 1600. A vector whose members come from one
        # source is not a collection of answers, it is the same answer counted repeatedly.
        by_source: dict = {}
        for node in pool.get(NUMBER, [])[:24]:
            by_source.setdefault(_source_key(node), []).append(node)
        if len(by_source) >= 2:
            items = tuple(next(iter(v)) for v in list(by_source.values())[:4])
            made.append(_n("vector", (items,), NUMVEC, set(),
                           f"[{','.join(i.label for i in items)}]"))

    elif name == "count":
        # A TABLE HAS A ROW COUNT TOO, AND IT IS NOT A COLUMN'S COUNT.
        #
        # "how many rows are in sales.csv" names a file and no column. The only thing
        # there is to count is the table, and without this branch the question had no
        # candidate at all -- while `count(t@file)` is precisely the expression `holds`
        # checks a row count with.
        for child in pool.get(TABLE, [])[:2]:
            made.append(_n("count", (child,), NUMBER,
                           lex.set & {"many", "count", "number"}, f"count({child.label})"))
        for child in (pool.get(TEXTVEC, []) + pool.get(NUMVEC, []))[:_MAX_PER_SHAPE]:
            made.append(_n("count", (child,), NUMBER,
                           lex.set & {"many", "count", "number"}, f"count({child.label})"))

    elif name in ("distinct", "values_of", "column_from"):
        want = (TEXTVEC, NUMVEC) if name == "values_of" else (
            TEXTVEC if name == "distinct" else NUMVEC)
        for table in pool.get(TABLE, [])[:6]:
            for col in _columns_of(table):
                for typ in (want if isinstance(want, tuple) else (want,)):
                    if name == "column_from" and col not in _numeric_columns_of(table):
                        continue
                    if name == "distinct" and col in _numeric_columns_of(table):
                        continue
                    # "PER <KEY>" IS THE WHOLE GROUPED COLUMN, one value per group -- and
                    # over a grouped table the aggregate column IS numeric, so `values_of`
                    # must be able to produce a NUMVEC there. Producing only TEXTVEC made
                    # "the total amount per region" unanswerable: the expression existed,
                    # typed as text, and no wanted type accepted it.
                    made.append(_n(name, (table, col), typ, {_norm(col)},
                                   f"{name}({col})@{table.label}"))

    elif name == "filter":
        for table in pool.get(TABLE, [])[:6]:
            for col in _columns_of(table):
                if col in _numeric_columns_of(table):
                    continue
                for value in _literal_values(lex, tables, col)[:4]:
                    made.append(_n("filter", (table, col, value), TABLE,
                                   {_norm(value)}, f"where {col}={value}"))

    elif name == "groups":
        for kind in ("sum", "max", "min", "count"):
            for grouped in pool.get("grouped", [])[:6]:
                key, val = grouped.args[1], grouped.args[2]
                # A ROW HAS A COUNT AND NOTHING ELSE. See `_ROW_AGGREGATES`.
                if val == "*" and kind not in _ROW_AGGREGATES:
                    continue
                made.append(_n("groups", (grouped, kind, key, val), TABLE,
                               _words_matching(lex, _AGG_WORDS.get(kind, set())),
                               f"{kind}({val}) by {key}"))

    elif name == "argmax_table":
        for extreme in ("max", "min"):
            for table in pool.get(TABLE, [])[:_MAX_PER_SHAPE]:
                # A GROUPED TABLE'S NUMERIC COLUMN IS ITS AGGREGATE, and choosing the
                # extreme row of it is exactly what "which region has the largest TOTAL"
                # asks. Applied to a raw table instead, the row chosen is a row of the
                # file and the word `total` is never accounted for -- the expression was
                # built, evaluated, and could not be offered because it had not dealt
                # with the question.
                consumed = set(_words_matching(lex, _AGG_WORDS[extreme]))
                if table.op == "groups":
                    kind = table.args[1]
                    consumed |= set(_words_matching(lex, _AGG_WORDS.get(kind, set())))
                for col in _numeric_columns_of(table):
                    made.append(_n("argmax_table", (table, col, extreme), ROW,
                                   consumed, f"argmax_{extreme}({col})"))

    elif name == "cell":
        for row in pool.get(ROW, [])[:_MAX_PER_SHAPE]:
            for col in _row_columns(row):
                made.append(_n("cell", (row, col), TEXT, {_norm(col)},
                               f"cell[{col}]({row.label})"))

    elif name == "contains_all":
        vecs = pool.get(TEXTVEC, [])[:4]
        for a, b in itertools.permutations(vecs, 2):
            made.append(_n("contains_all", (a, b), BOOL, set(),
                           f"contains_all({a.label},{b.label})"))

    return made


def _sentence_position(node: Node, lex: Lexicon, question: str = "") -> int | None:
    """Where in the question this value's source is named -- the sentence's own order.

    `lex.raw` is the SUBJECT words, and the door strips filenames out of those before it
    ever gets here: "the total in returns.csv versus inventory.csv" arrives as
    ['total','units','less'], so a comparison could not be ordered and was refused
    outright. The sentence itself still has the names in it, in the order it said them.
    """
    key = _source_key(node)
    stem = key.rsplit(".", 1)[0].lower()
    for i, word in enumerate(lex.raw):
        if word == key.lower() or word == stem or _norm(word) == _norm(stem):
            return i
    if question:
        import re as _re
        low = question.lower()
        hits = [low.find(w) for w in (key.lower(), stem) if w and low.find(w) >= 0]
        if hits:
            return min(hits) + 1000     # after every in-words position, still ordered
    return None


def _words_matching(lex: Lexicon, vocabulary) -> set[str]:
    """The question's own words that name this operator, allowing singular/plural.

    `vocabulary & lex.set` was exact, so `totals` -- the word a person writes -- matched
    nothing, and no `sum` was ever built for the question. Matching is by `_norm`, the one
    place that decides plural equality, so the vocabulary and the search cannot disagree
    about whether two spellings are one word.
    """
    wanted = set(vocabulary)
    return {w for w in lex.set if w in wanted or _norm(w) in wanted
            or w.rstrip("s") in wanted or _norm(w).rstrip("s") in wanted}


def _source_key(node: Node) -> str:
    """Which FILE a value comes from -- the identity a vector must range over."""
    seen = 0
    stack = [node]
    while stack and seen < 200:
        seen += 1
        cur = stack.pop()
        for arg in getattr(cur, "args", ()) or ():
            if isinstance(arg, Node):
                stack.append(arg)
            elif isinstance(arg, (list, tuple)):
                stack.extend(x for x in arg if isinstance(x, Node))
            elif isinstance(arg, str) and ("/" in arg or arg.endswith((".csv", ".json", ".txt", ".md", ".py"))):
                return arg.rsplit("/", 1)[-1]
    return node.label


def _rel_of(table: Node):
    return table.args[0] if table.op == "table" and table.args else None


def _source_table(table: Node) -> Node | None:
    """The TABLE node at the bottom of a table-valued expression.

    A filtered table is a table; asking which columns it has means asking its SOURCE,
    because a filter removes rows and never columns. Handling only a bare `table` here is
    the same defect as checking invariants only at the root -- the columns of
    `where region=west` read as `[]`, so `column_from` and every aggregate over a filtered
    table silently failed to build, and "the total in west" had no expression at all
    while its pieces were all present.
    """
    seen = 0
    node = table
    while isinstance(node, Node) and seen < 20:
        seen += 1
        if node.op == "table":
            return node
        nxt = None
        for arg in node.args:
            if isinstance(arg, Node) and arg.type == TABLE:
                nxt = arg
                break
        if nxt is None:
            return None
        node = nxt
    return None


def _columns_of(table: Node) -> list[str]:
    """The header of the table a node denotes, read from the file it names."""
    # A GROUPED TABLE HAS ITS OWN COLUMNS: the key and the aggregate. They are not in the
    # file's header, and asking the file for them returned the raw columns instead -- so
    # no expression could read the aggregate column by name.
    if isinstance(table, Node) and table.op == "groups":
        return [table.args[2], f"{table.args[1]}({table.args[3]})"]
    src = _source_table(table)
    rel = _rel_of(src) if src is not None else None
    if rel is None:
        return []
    got = _columns(_as_path(rel))
    return got[0] if got else []


def _numeric_columns_of(table: Node) -> list[str]:
    # A GROUPED TABLE'S AGGREGATE COLUMN IS NUMERIC BY CONSTRUCTION, and its name is
    # derived from the aggregation, not from the file's header. Reading the header made
    # `argmax_table` over a grouping see only the key's own columns.
    if isinstance(table, Node) and table.op == "groups":
        return [f"{table.args[1]}({table.args[3]})"]
    src = _source_table(table)
    rel = _rel_of(src) if src is not None else None
    if rel is None:
        return []
    got = _columns(_as_path(rel))
    if got is None:
        return []
    return list(_numeric_columns(got[0], got[1]))


def _row_columns(row: Node) -> list[str]:
    """The columns a chosen row carries -- the KEY and the AGGREGATE, when grouped.

    `_columns_of` walks to the source FILE, which is right for a raw table and wrong for
    a grouped one: a row of `sum(amount) by region` has the columns `region` and
    `sum(amount)`, and neither comes from the file's header. Reading the header meant
    `cell[region](argmax(groups(...)))` was never built, so "which region has the largest
    total" could only be answered by picking a row of the RAW file -- an expression that
    never accounts for the word `total`.
    """
    if row.op == "argmax_table" and row.args:
        table = row.args[0]
        if isinstance(table, Node):
            if table.op == "groups":
                # the row carries its key and its aggregate
                return [table.args[2], f"{table.args[1]}({table.args[3]})"]
            return _columns_of(table)
    return []


def _as_path(rel):
    import pathlib
    return pathlib.Path(rel)


# ---------------------------------------------------------------------------
# THE SEARCH.
# ---------------------------------------------------------------------------

class _ColumnFile:
    """Just enough of an entity for the leaves: a file found by a column it carries."""

    kind = "file"

    def __init__(self, path, rel):
        self.path = path
        self.rel = rel


def _files_named_by_columns(root: str, words: list[str]) -> list:
    """Files whose HEADER a question names, when the question names no file itself.

    Only headers count. A word that merely appears in the data (a region called "west")
    does not identify a table, because the same word can appear in any file -- resolving
    on data would make the answer depend on which rows happen to be there. A shared
    header name across two files is an ambiguity, and an ambiguous referent is refused.
    """
    import pathlib as _p

    wanted = {_norm(w) for w in words}
    found: dict[str, list[_p.Path]] = {}
    base = _p.Path(root)
    try:
        paths = sorted(base.rglob("*.csv"))[:200]
    except OSError:
        return []
    for path in paths:
        got = _columns(path)
        if not got:
            continue
        header = [_norm(h) for h in got[0]]
        for name in header:
            if name in wanted:
                found.setdefault(name, []).append(path)

    out, seen = [], set()
    for name, paths in found.items():
        if len(paths) == 1:                 # a header only ONE file carries: a referent
            path = paths[0]
            if str(path) not in seen:
                seen.add(str(path))
                try:
                    rel = str(path.relative_to(base))
                except ValueError:
                    rel = path.name
                out.append(_ColumnFile(path, rel))
    return out


def enumerate_expressions(question: str, root: str, ents, words: list[str],
                          max_depth: int = _MAX_DEPTH) -> dict:
    """Every well-typed expression up to `max_depth`, built by TYPE, not by sentence.

    Returns the expressions actually CONSTRUCTED -- not the ones that were evaluated --
    so the size of the answer space is a measurement rather than a claim.
    """
    lex = Lexicon(words)
    tables: dict = {}
    files = [e for e in (ents or []) if getattr(e, "rel", None)]

    # A QUESTION MAY NAME A COLUMN INSTEAD OF A FILE.
    #
    # "how many rows" names sales.csv; "what is the total amount" names no file at all --
    # and the old search reads `files`, finds none, and refuses, although `amount` occurs
    # in exactly one file. A column is a referent: it identifies the table it lives in.
    # So when the question names no file, the columns it does name are resolved to
    # files. Ambiguity is NOT resolved by preference -- if two files carry a column of
    # that name, picking one would be answering a question nobody asked, so the columns
    # that cannot be pinned down are withheld and the question stays refused.
    if not files:
        files = _files_named_by_columns(root, words)
    for ent in files:
        got = _columns(_as_path(ent.path))
        if got is not None:
            tables[ent.rel] = got

    pool = _leaves(lex, tables, files)
    by_type: dict[str, list[Node]] = {k: list(v) for k, v in pool.items()}
    everything: list[Node] = [n for vs in pool.values() for n in vs]
    constructed = 0

    # BUILD TO A FIXED POINT, NOT FOR A FIXED NUMBER OF PASSES.
    #
    # One pass over the operator table produces every expression whose arguments already
    # exist. "the average of the totals in a.csv and b.csv" needs sum(a) and sum(b) to
    # exist BEFORE the vector that holds them, and that vector to exist BEFORE the mean
    # above it -- three passes for one sentence. A fixed count either stops too early
    # (the question is refused with its pieces built) or wastes passes; iterating until
    # an iteration adds nothing new is both correct and self-limiting, because the pools
    # are pruned and every expression is counted against a hard ceiling.
    for _level in range(max(1, max_depth)):
        if constructed >= _MAX_EXPRESSIONS:
            break
        fresh: list[Node] = []
        seen_labels = {n.label for n in everything}
        for name in _OPERATORS:
            made = _apply(name, by_type, lex, tables, question)
            for node in made:
                if node.label in seen_labels:
                    continue          # already built; the fixed point is unchanged
                seen_labels.add(node.label)
                fresh.append(node)
            constructed += len(made)
            if constructed >= _MAX_EXPRESSIONS:
                break
        if not fresh:
            break
        for node in fresh:
            everything.append(node)
            by_type.setdefault(node.type, []).append(node)
        # keep the pools bounded in a way that favours the question's own words
        for typ, vs in by_type.items():
            if len(vs) > 40:
                vs.sort(key=lambda n: -len(lex.set & {_norm(w) for w in _structural_words(n)}))
                by_type[typ] = vs[:40]

    return {
        "schema": SCHEMA,
        "question": question,
        "expressions": everything,
        "constructed": constructed,
        "tables": tables,
        "by_type": {k: len(v) for k, v in by_type.items()},
    }


def _read_columns(node: Node) -> set[str]:
    """Every column an expression actually READS AS A VALUE, at any depth."""
    out: set[str] = set()
    if node.op in ("column", "column_from", "values_of", "distinct", "filter"):
        col = node.args[1]
        # `amount` and `sum(amount)` are different names, and only the first is a column
        # a question can mention. A computed name that leaks into this set makes the
        # expression look as though it read something it was only aggregating over.
        if isinstance(col, str) and "(" not in col:
            out.add(_norm(col))
    if node.op == "group":
        out |= _read_columns(node.args[0])
        if node.args[2] != "*":
            out.add(_norm(node.args[2]))
    elif node.op == "groups":
        out |= _read_columns(node.args[0])
        if node.args[3] != "*":
            out.add(_norm(node.args[3]))
    elif node.op == "aggregate":
        out |= _read_columns(node.args[1])
    elif node.op == "map":
        out |= _read_columns(node.args[1])
    elif node.op == "compare":
        out |= _read_columns(node.args[1]) | _read_columns(node.args[2])
    elif node.op == "vector":
        for c in node.args[0]:
            out |= _read_columns(c)
    elif node.op == "cell":
        out |= _read_columns(node.args[0])
    elif node.op == "argmax_table":
        out |= _read_columns(node.args[0])
        out.add(_norm(node.args[1]))
    elif node.op == "contains_all":
        out |= _read_columns(node.args[0]) | _read_columns(node.args[1])
    else:
        for a in node.args:
            if isinstance(a, Node):
                out |= _read_columns(a)
    return out


def _row_words(node: Node) -> set[str]:
    """The words an expression spends by saying ROW rather than by naming a column.

    `*` still costs the word that asked for a count -- "how many rows per region" says
    `rows` and must be able to spend it -- but it must NOT spend the word that asks for
    a TOTAL. `sum` over a row count is the row count, so letting `count(*)` account for
    `total` was how "the total amount" answered 5.0.
    """
    spends: set[str] = set()
    if node.op in ("groups", "group") and node.args[-1] == "*":
        spends |= {"count", "how", "many", "much", "number", "row", "rows", "record",
                   "records", "entry", "entries", "line", "lines"}
    if node.op == "groups" and node.args[3] == "*":
        spends |= {"count", "how", "many", "much", "number", "row", "rows", "record",
                   "records", "entry", "entries", "line", "lines"}
    for a in node.args:
        if isinstance(a, Node):
            spends |= _row_words(a)
        elif isinstance(a, (list, tuple)):
            for item in a:
                if isinstance(item, Node):
                    spends |= _row_words(item)
    return spends


def _unread_columns(node: Node, lex: Lexicon, tables: dict) -> set[str]:
    """Columns the QUESTION names that the expression never measures.

    The mirror of "every word must be accounted for", and the same kind of statement.

    `sum(column_from(count(*)) by amount)` returned 5 for "the total amount": it groups
    BY amount, so the word `amount` is consumed and the account is balanced -- but it
    sums a count of rows, so the amount column was never measured. Grouping by a column
    is not measuring it. A question that names a quantity has to have that quantity read
    as a value somewhere in the expression that answers it, and a flat set of spent words
    cannot say so, because it records only that a word was used, not what it was used AS.
    """
    # ANY COLUMN THE QUESTION NAMES, NOT ONLY THE NUMERIC ONES.
    #
    # Restricting this to numeric columns made the check powerless exactly when it was
    # needed: one `n/a` cell takes `amount` out of the numeric set, and "the total
    # amount" was then answered by `sum` over a row COUNT grouped by amount -- 2. The
    # question named `amount`; the expression grouped by it and never measured it. That
    # is not a numeric question, it is a question about a referent, and a referent is
    # named whether or not its cells happen to parse.
    # A KEY IS A USE, NOT A FAILURE TO MEASURE.
    #
    # "how many rows per region" names `region`; "which region has the largest total"
    # names `region` too, and the answer is that column's VALUE -- picking it out is the
    # whole question. A column that identities a row or a group is doing its job.
    #
    # "the total amount" is the one case that differs, and not because of a keyword: it
    # names a QUANTITY and asks for a statement about that quantity, so grouping by it is
    # answering something else. The distinction is measure-of-a-quantity versus
    # identity-of-a-row, and it is read from what the question asks for: a count or a
    # picked-out name is not a measurement; a total is.
    if _asks_how_many(lex) or node.type == TEXT:
        return set()
    # MEASUREMENT IS A REQUIREMENT ON QUANTITIES, NOT ON NAMES.
    #
    # "the total amount per region" names `region`, and the answer reads it as a KEY --
    # grouping by it is what "per region" asks for. Requiring the expression to MEASURE
    # a text column as well rejected the correct [150,150,250] and refused the question.
    # A column of numbers that the question names must be measured; a column of names
    # that the question names is an identity, and reading it as a key is using it.
    return _numeric_of(lex, tables) - _read_columns(node)


def _numeric_of(lex: Lexicon, tables: dict) -> set[str]:
    """The columns this question names that hold NUMBERS -- in any cell at all.

    Not `_numeric_columns`, which asks whether EVERY cell parses. A column that is
    `100, n/a` is still the quantity the question is about: one bad cell does not turn
    a quantity into a name. Asking the strict question made this check vanish exactly
    when it was needed -- with an `n/a` present, no column was "numeric", so nothing had
    to be measured, and "the total amount" was answered by `sum` over a row count
    grouped by `amount`: 2.

    A column with NO parseable number anywhere -- `region`, `item`, `name` -- is an
    identity, and reading it as a key is using it rather than failing to measure it.
    """
    from canonical.runtime.value_algebra_v1 import _to_float
    named = {_norm(w) for w in lex.raw}
    out: set[str] = set()
    for _rel, (header, rows) in (tables or {}).items():
        for i, col in enumerate(header):
            if _norm(col) not in named:
                continue
            for r in rows:
                cell = r[i] if i < len(r) else ""
                if isinstance(cell, str) and not cell.strip():
                    continue
                if _to_float(cell) is not None:
                    out.add(_norm(col))
                    break
    return out


def wanted_columns(lex: Lexicon, tables: dict) -> set[str]:
    """The columns this question names, normalised."""
    named = {_norm(w) for w in lex.raw}
    out: set[str] = set()
    for _rel, (header, _rows) in (tables or {}).items():
        for col in header:
            if _norm(col) in named:
                out.add(_norm(col))
    return out


def _reads_aggregate_column(node: Node) -> bool:
    """Does this expression read a grouping's AGGREGATE -- i.e. the number per group?

    A grouped table's aggregate column is named `sum(amount)` or `count(*)`. Reading it
    is reporting the quantity for each group; reading the key column is reporting the
    group's NAME. Both are text vectors when read with `values_of`, and only the first
    answers "the total amount per region".
    """
    stack = [node]
    while stack:
        cur = stack.pop()
        if not isinstance(cur, Node):
            continue
        if cur.op in ("values_of", "column_from", "distinct"):
            src = cur.args[0]
            if isinstance(src, Node) and src.op == "groups":
                col = cur.args[1] if isinstance(cur.args[1], str) else ""
                if "(" in col:
                    return True
        for a in cur.args:
            if isinstance(a, Node):
                stack.append(a)
            elif isinstance(a, (list, tuple)):
                stack.extend(x for x in a if isinstance(x, Node))
    return False


def _under_grouping(node) -> bool:
    """Does this node's value come out of a grouping rather than out of a column?"""
    seen = 0
    while isinstance(node, Node) and seen < 20:
        seen += 1
        if node.op in ("groups", "group"):
            return True
        if node.op in ("column_from", "values_of", "distinct", "cell"):
            node = node.args[0]
            continue
        if node.op == "aggregate":
            node = node.args[1]
            continue
        return False
    return False


def choose(question: str, root: str, ents, words: list[str],
           max_depth: int = _MAX_DEPTH) -> dict | None:
    """The best expression the enumeration finds, by the SAME rules the old search used.

    An expression is an answer when it (1) is the type asked for, (2) accounts for every
    word of the question, (3) evaluates, and (4) holds its own operator's invariant. The
    rules are not new; what is new is that they are applied to an ENUMERATED set instead
    of to sixteen appends.
    """
    from canonical.runtime.value_algebra_v1 import _PER_WORDS, _DISTINCT_WORDS, _noise

    built = enumerate_expressions(question, root, ents, words, max_depth=max_depth)
    lex = Lexicon(words)
    want_types = _wanted_types(lex)

    best = None
    unsound = False
    for node in built["expressions"]:
        if node.type not in want_types:
            continue
        # AGGREGATE VOCABULARY IS NOT SPENT BY A ROW COUNT.
        #
        # `sum(*)-by-region` and `count(*)` both "consume" whatever aggregate words they
        # like through `_AGG_WORDS`; the difference is that a count of rows may not claim
        # the words of a SUM. Removing what the row-count genuinely spends, then what the
        # expression still needs, is the whole rule.
        spent = {_norm(w) for w in (node.consumes | _structural_words(node))}
        spent |= {_norm(w) for w in _row_words(node)}
        consumed = spent
        left = {_norm(w) for w in lex.raw} - consumed - {_norm(w) for w in _noise}
        if left:
            continue                      # does not account for the question
        if _unread_columns(node, lex, built["tables"]):
            continue                      # names a quantity it never measures
        if _counts_something_else(node, lex, built["tables"]):
            continue                      # asked how many rows, counted something else
        if lex.set & _DISTINCT_WORDS and node.op in ("count", "aggregate"):
            child = node.args[1] if node.op == "aggregate" else node.args[0]
            if isinstance(child, Node) and child.op == "values_of":
                continue
        if lex.set & _PER_WORDS and node.op == "count":
            continue                      # a single count cannot answer "per"
        try:
            value = evaluate(node)
        except (EvalError, TypeError, ValueError, ZeroDivisionError,
                AttributeError, KeyError, IndexError):
            continue
        if value is None:
            continue
        if holds(node, value) is False:
            # AN UNSOUND CANDIDATE IS A CONTRADICTION, NOT A WEAKER OPTION.
            #
            # The same rule the incumbent search learned: with a `groups` that loses a
            # bucket, the totals are correctly rejected -- and the search then answered
            # `values_of(region)` = ['north','south'] for a question about AMOUNTS. Seeing
            # the violation and quietly substituting a different question is the defect
            # this project exists to catch. It was cheaper to re-learn it here than to
            # remember it, which is itself the argument for one implementation.
            unsound = True
            break
        # THE SMALLEST EXPRESSION THAT ACCOUNTS FOR THE WHOLE QUESTION.
        #
        # Scoring by how many words an expression touches rewards SIZE: a node sitting on
        # top of a large subtree inherits every word below it, so `sum(vector(...))` beat
        # `sum(where region=west)` 15 words to 13 and "the total in west" came back 1600.
        # That is the SAME defect fixed in the old search -- a node credited with words its
        # value does not depend on -- reproduced by the enumerator, which is what an
        # enumerator does left to itself: more expressions, all plausible.
        #
        # Every candidate here has already accounted for every word of the question (the
        # `left` check above). Among those, the one that needs the FEWEST OPERATORS is the
        # least speculative reading. Words are a filter, not a score.
        # WHEN THE QUESTION SAYS "PER", ONLY A VECTOR IS AN ANSWER.
        #
        # `count(groups by region)` = 4 and `values_of(groups by region)` = [150,150,250]
        # both account for every word, and "fewest operators" then preferred the shorter
        # one -- a cardinality handed over for a question about the values themselves.
        # `per` is not a preference; it changes what the answer IS, so it filters the
        # candidates rather than ranking them.
        # "PER <GROUP>" IS ANSWERED BY THE GROUP'S QUANTITIES, NOT BY ITS NAMES.
        #
        # With the size comparison finally the right way round, `distinct(region) by
        # region` is the SMALLEST accounting expression -- three nodes to
        # `column_from(sum(amount)) by region`'s four -- and it answered "the total
        # amount per region" with ['north','south','west']. Every word was accounted
        # for, including `amount`, because the grouping is keyed BY amount in the
        # candidate that won. The question asks for a number per group; a list of the
        # group names is the right shape and a different question.
        #
        # A text vector can only be the answer when the question asks for the groups
        # THEMSELVES ("which regions", "what are the regions"), which is a question
        # about identity. When it asks for a quantity per group, the answer is numeric.
        if lex.set & _PER_WORDS:
            if node.type not in (NUMVEC, TEXTVEC):
                continue
            if (node.type == TEXTVEC and _quantity_named(lex, built["tables"])
                    and not _reads_aggregate_column(node)):
                continue
        if _overconsumed(node, {_norm(w) for w in lex.raw}):
            continue
        size = _size(node)
        # THE EXPRESSION THAT INVENTS THE LEAST WINS.
        #
        # `count(col:amount)` and `count(t@file)` are both size 4 and both account for the
        # question, which said "rows" and never said "amount". They differ by one row,
        # because counting a column skips a row whose cell is blank -- and by label the
        # wrong one won. Two candidates that tie on size are not equally good; the one
        # that reached for a column nobody mentioned is answering a question that was not
        # asked. This sits ABOVE the label so the answer is decided by the question, not
        # by alphabetical order.
        # SMALLER WINS, AND THE COMPARISON MUST AGREE WITH THE SIGN.
        #
        # This was `(-size, ...)` compared with `<`, which keeps the SMALLEST tuple --
        # so the LOWEST negation -- so the LARGEST expression won every time. Every
        # comment around it said "fewest operators"; the code said the opposite. The
        # symptom was "the total qty" answering 3.0: `sum(column_from(count(qty)) by
        # item)` is size 5 and `sum(col:qty)` is size 2, and the 5 was chosen.
        #
        # A negation in front of a compared quantity is a sign waiting to be flipped, so
        # the score is stored un-negated and the comparison reads left to right.
        score = (size, _tiebreak(node, lex))
        if best is None or score < best[0]:
            best = (score, node, value)

    if unsound:
        return None
    if best is None:
        return None
    _, node, value = best
    return {"node": node, "value": value,
            "accounted": sorted(node.consumes | _structural_words(node)),
            "enumerated": built["constructed"]}


def _overconsumed(node: Node, question_words: set[str]) -> bool:
    """Does any word of the question get SPENT MORE THAN ONCE in this expression?

    A word names one thing in the question, and only one operator should claim it.
    Without this rule the enumerator's own productiveness defeats it:

      - `double(double(sum(qty)))` accounted for "doubled" TWICE, so "the total qty
        doubled" was answered 432 -- four doublings -- because the deepest accounting
        expression won on tie-break;
      - `mean` inside a vector claimed "average" for each member, so "the average of the
        totals in a.csv and b.csv" built [mean(a), mean(b)] instead of [sum(a), sum(b)],
        spending `average` on the parts and leaving nothing for the whole.

    The old hand-written search could not make this mistake: it only ever built the one
    expression somebody had written down. An enumerator can, so it needs the rule that a
    sentence's word means one thing.
    """
    # ONLY WORDS AN OPERATOR SPENDS ITSELF COUNT.
    #
    # `consumes` holds two different things: the words an operator's own VOCABULARY
    # accounts for (`double` spends "doubled"; `sum` spends "total"), and the words that
    # NAME a binding it reads (`cell[region]` re-states the `region` its grouping already
    # bound). The first is spending a word of the sentence; the second is referring to a
    # binding that exists. Counting both flagged `cell[region](argmax_max(sum(amount)))`
    # -- the correct answer `west` -- as over-consumption, because `region` appeared once
    # in the grouping and once in the selection.
    #
    # So a claim is counted only when it comes from an operator's VOCABULARY, which is a
    # closed set we can check rather than a guess about intent.
    vocab = set()
    for table in (_AGG_WORDS, _MAP_WORDS, _CMP_WORDS):
        for words in table.values():
            vocab |= {_norm(w) for w in words}
    claims: dict[str, int] = {}
    stack = [node]
    while stack:
        cur = stack.pop()
        if not isinstance(cur, Node):
            continue
        for word in cur.consumes:
            key = _norm(word)
            if key not in vocab:
                continue              # a binding name, not a spent word
            claims[key] = claims.get(key, 0) + 1
        for arg in cur.args:
            if isinstance(arg, Node):
                stack.append(arg)
            elif isinstance(arg, (list, tuple)):
                stack.extend(a for a in arg if isinstance(a, Node))
    # THE SAME WORD TWICE IS ONLY A CONTRADICTION WHEN IT PICKS TWO DIFFERENT THINGS.
    #
    # `double(double(x))` spends "doubled" twice, and the two doublings are the same
    # operation applied to itself: the second is not a second reading of the sentence, it
    # is the first one repeated. That is the mistake to catch.
    #
    # `argmax_max(sum(amount))` also has two claims in the tree -- `sum` spends "total"
    # and `argmax` spends "largest" -- but they are DIFFERENT words naming DIFFERENT
    # roles: the quantity, and which way to pick it. Rejecting equal counts would have
    # refused "which region has the largest total", which is the correct answer `west`.
    #
    # So the test is whether repetition ADDS ANYTHING: a repeated word is a defect when
    # the enclosing operation is the SAME OPERATOR as the one that already claimed it.
    stack = [node]
    while stack:
        cur = stack.pop()
        if not isinstance(cur, Node):
            continue
        own = {_norm(w) for w in cur.consumes} & question_words
        for arg in cur.args:
            kids = arg if isinstance(arg, (list, tuple)) else (arg,)
            for kid in kids:
                if not isinstance(kid, Node):
                    continue
                if kid.op == cur.op and (own & {_norm(w) for w in kid.consumes}):
                    return True       # the same operator spending the same word again
        for arg in cur.args:
            kids = arg if isinstance(arg, (list, tuple)) else (arg,)
            for kid in kids:
                if isinstance(kid, Node):
                    stack.append(kid)
    return False


def _size(node: Node) -> int:
    """How many operators the expression contains. Fewer is less speculative."""
    total = 0
    stack = [node]
    while stack:
        cur = stack.pop()
        if not isinstance(cur, Node):
            continue
        total += 1
        for arg in cur.args:
            if isinstance(arg, Node):
                stack.append(arg)
            elif isinstance(arg, (list, tuple)):
                stack.extend(a for a in arg if isinstance(a, Node))
    return total


_ROW_WORD_SET = frozenset({"row", "rows", "record", "records", "line", "lines",
                           "entry", "entries"})


def _columns_named(lex: Lexicon, tables: dict) -> set[str]:
    """Columns the question names in so many words."""
    named = {_norm(w) for w in lex.raw}
    out: set[str] = set()
    for _rel, (header, _rows) in (tables or {}).items():
        for h in header:
            if _norm(h) in named:
                out.add(_norm(h))
    return out


def _counts_something_else(node: Node, lex: Lexicon, tables: dict) -> bool:
    """Is this a count of a named thing where the question asked how many ROWS?

    "how many rows are in sales.csv" says `rows` and names no column. The answer must
    therefore be the number of rows -- 5. `count(distinct(region))` is also a count, is
    also over that file, and accounts for every word, because `region` is spent by the
    column leaf whether or not the question mentioned it. It answers 3, and 3 is the
    number of REGIONS, not the number of rows.

    A word like `rows` names the ROW ITSELF, so when it is what asked for a count and no
    column was named to count, the count has to be over the table. This is not a
    preference between candidates: a distinct count is the answer to a different
    question, and the question says which one it is.
    """
    if not (lex.set & _ROW_WORD_SET):
        return False
    if _columns_named(lex, tables):
        return False                      # something was named; it may be counted
    # `count` is spelled `aggregate("count", child)` in the tree, not `count(child)`.
    # Asking for `node.op == "count"` here was false for every count that exists, so the
    # rule never fired and "how many rows" kept answering 4: it was counting the amount
    # COLUMN, which has a blank and therefore four parseable cells in five rows.
    if node.op == "aggregate" and node.args[0] == "count":
        child = node.args[1]
    elif node.op == "count":
        child = node.args[0]
    else:
        return False
    if isinstance(child, Node) and child.op == "table":
        return False                      # already counting the rows themselves
    # a count of an aggregate column of a grouping is also a count of rows
    if isinstance(child, Node) and child.op in ("column_from", "values_of"):
        inner = child.args[0]
        if isinstance(inner, Node) and inner.op == "groups" and inner.args[3] == "*":
            return False
    return True


def _introduces(node: Node, asked: set[str] | None = None) -> int:
    """How many words this expression SPENDS that the question never said.

    `count(col:amount)` and `count(t@file)` are both well-typed counts over the same
    file, and the question "how many rows" mentions neither. They differ by one row,
    because counting a COLUMN skips a row whose cell is blank -- and the tie was settled
    alphabetically. The question cannot say which is right; it can say which one invented
    something, and the one that did is answering a question that was not asked.
    """
    if not isinstance(node, Node):
        return 0
    if asked is None:
        asked = set()
    spent = {_norm(w) for w in (node.consumes | _structural_words(node))}
    n = len(spent - asked)
    for a in node.args:
        if isinstance(a, Node):
            n += _introduces(a, asked)
        elif isinstance(a, (list, tuple)):
            for item in a:
                if isinstance(item, Node):
                    n += _introduces(item, asked)
    return n


def _tiebreak(node: Node, lex: "Lexicon" | None = None) -> str:
    """Which of several equally small, equally accounting expressions to show.

    A tie is a real ambiguity -- `sum`, `mean` and `count` over the same vector are all
    correct answers to DIFFERENT questions, and all three were sitting in the pool for
    "the average of the totals". Choosing by label alone gave `count` = 2. The question
    said "average", so an expression whose OWN OPERATOR is the one the question named
    must win; the label is only the last resort, and exists so that the same question
    never gets two answers.
    """
    # WHICH OPERATOR DID THE QUESTION NAME -- THE ONE AT THE TOP, OR ONE INSIDE?
    #
    # `sum([sum(a), sum(b)])`, `mean([sum(a), sum(b)])` and `count([...])` are the same
    # size and all account for every word, because "totals" is spent by the INNER sums in
    # all three. So every candidate looked equally "named". What separates them is the
    # operator at the ROOT: the question said "average", and only the root is the reading
    # of what the answer IS. An inner operator is how a part was obtained.
    named = 1
    if lex is not None and node.op == "aggregate":
        own = _words_matching(lex, _AGG_WORDS.get(node.args[0], set()))
        # the words this root owns, EXCLUDING any its children also spend
        child_words = set()
        stack = [c for c in node.args if isinstance(c, Node)]
        while stack:
            cur = stack.pop()
            child_words |= {_norm(w) for w in cur.consumes}
            for arg in cur.args:
                kids = arg if isinstance(arg, (list, tuple)) else (arg,)
                stack.extend(k for k in kids if isinstance(k, Node))
        own = {w for w in own if _norm(w) not in child_words}
        named = 0 if own else 1
    filtered = 0 if _mentions(node, "filter") else 1
    return (named, filtered, node.label)


def _mentions(node: Node, op: str) -> bool:
    stack = [node]
    while stack:
        cur = stack.pop()
        if not isinstance(cur, Node):
            continue
        if cur.op == op:
            return True
        for arg in cur.args:
            if isinstance(arg, Node):
                stack.append(arg)
            elif isinstance(arg, (list, tuple)):
                stack.extend(a for a in arg if isinstance(a, Node))
    return False


_HOW_MANY = {"how", "many", "much", "number"}


def _quantity_named(lex: Lexicon, tables: dict) -> bool:
    """Does the question name a numeric column -- a quantity to be reported per group?"""
    named = {_norm(w) for w in lex.raw}
    for _rel, (header, rows) in (tables or {}).items():
        for col in _numeric_columns(header, rows):
            if _norm(col) in named:
                return True
    return False


def _asks_how_many(lex: Lexicon) -> bool:
    """Does the question ask for a count?  "how many rows" yes, "which region" no."""
    return bool({_norm(w) for w in lex.raw} & _HOW_MANY)


def _wanted_types(lex: Lexicon) -> set:
    """The type the question asks for, read from its own words.

    `_SELECT_WORDS` held {"which","what","row",...} -- and `what` is in almost every
    question, so "which region has the largest total" was classified as asking for TEXT
    only by accident of `which` also being there, while "what is the total in west" was
    classified as a SELECTION question and its NUMBER was rejected. The distinction that
    matters is not WHICH interrogative was used; it is whether the question asks to pick
    SOMETHING OUT of the data or to measure it. A superlative (`largest`, `smallest`)
    settles it: the answer is the thing that wins.
    """
    from canonical.runtime.value_algebra_v1 import _PER_WORDS
    cmp_words = set().union(*_CMP_WORDS.values()) if _CMP_WORDS else set()
    extremes = set().union(_AGG_WORDS["max"], _AGG_WORDS["min"])
    if lex.set & cmp_words:
        return {BOOL}
    if lex.set & _PER_WORDS:
        # "HOW MANY ... PER <GROUP>" IS A COUNT PER GROUP, NOT A LIST OF THE GROUPS.
        #
        # This returned {NUMVEC, TEXTVEC, NUMBER} and accepted a TEXTVEC, so with a blank
        # cell in the data -- which made the row-count unbuildable at the time -- the
        # search answered "how many rows per region" with the region NAMES. A vector of
        # text can never be the answer to a question that asks HOW MANY: it has the right
        # shape and answers a different question. When the question asks for a count, the
        # text vector is not a weaker candidate, it is not a candidate.
        if _asks_how_many(lex):
            return {NUMVEC, NUMBER}
        return {NUMVEC, TEXTVEC, NUMBER}
    # "which region has the largest total" wants the KEY; "what is the largest total"
    # wants the NUMBER -- and both are stripped to the same four words minus the
    # interrogative, because `which` is an ask-word, not a subject. So the interrogative
    # cannot decide it. What does decide it is that the question still names a TEXT KEY
    # while asking for an extreme: there is something to pick out, and the extreme says
    # to pick it. Without a key noun there is nothing to pick, and the number is wanted.
    if (lex.set & extremes) and _text_key_named(lex):
        return {TEXT}
    # AN AGGREGATE OF SEVERAL FILES IS AN AGGREGATE OF A VECTOR.
    #
    # "the average of the totals in a.csv and b.csv" needs [sum(a), sum(b)] and then a
    # mean over it. The vector is an intermediate, so a question whose answer is a single
    # number must still accept the vector candidates that the outer aggregate consumes --
    # otherwise the only candidate that accounts for `average` was never selectable and
    # the question was refused with its answer sitting in the enumeration.
    #
    # Widening to include vectors is safe because every candidate still has to account
    # for EVERY word of the question and pass its own invariants; the type narrows what
    # can be offered, it does not certify it.
    if lex.set & {"average", "mean", "typical", "avg"}:
        return {NUMBER, NUMVEC}
    return {NUMBER}


_TEXT_KEY = {"region", "name", "item", "sku", "label", "category", "group", "kind",
             "type", "city", "country", "product", "customer", "team", "author", "file"}


def _text_key_named(lex: Lexicon) -> bool:
    """Is a text key among the question's words?

    A closed vocabulary here would be the ninth-regex defect, so it is used only as a
    HINT: the caller also accepts TEXT from candidates whose evaluation succeeds. It
    decides the TYPE ORDER, never whether an answer exists.
    """
    return bool(set(lex.set) & _TEXT_KEY)
