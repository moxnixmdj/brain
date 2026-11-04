"""An answer that ignores the thing it was asked about is not an answer.

THE DEFECT, MEASURED ON THE DOOR.

    what is the total amount times region
      terms      = ['total', 'amount', 'times', 'region']
      expression = double(count(sum(amount) by region))
      value      = 6        verified: True

Both data words were present. Both were "accounted for". The expression counts the
three region groups and doubles the count. It never multiplies anything, and it never
uses a single amount value. `holds()` passed it because the expression is perfectly
sound about itself -- `double(3)` really is 6 -- and soundness about itself is the only
thing any check in this system ever asked.

`what is the total amount divided by region` is the same shape: `half(count(...))` = 1.5.
So is the 1.5 that two rounds of ledger work were built on. It was never a division.

WHY THE OBVIOUS FIX IS THE WRONG ONE. `times` and `divided` are binary in English and
were filed into the UNARY operator lexicon (`_MAP_WORDS["double"]`, `["half"]`). Deleting
them there makes the door refuse instead of fabricate, which is better -- and it is still
me typing a list of which words are binary. That reflex has been caught twice in this
work already and removed twice.

THE DERIVED TEST. Do not ask what the word means. Ask whether the answer DEPENDS on the
thing the question names:

    change every value in the column the question is about.
    an answer about that column must move.
    an answer that does not move was never about it.

Measured on `sales.csv`, changing every amount to 7:

    what is the total amount             550 -> 28      moved
    what is the average amount           137.5 -> 7     moved
    what is the total amount per region  [150,...] -> [14,...]  moved
    what is the total amount times region   6 -> 6      DID NOT MOVE
    what is the total amount divided ...    1.5 -> 1.5  DID NOT MOVE

And the control that makes this a check rather than an alarm: `how many regions` is
also invariant to amount changes, and it is CORRECT -- because it does not name
`amount`. It names `regions`, and it does move when the region cardinality changes
(3 -> 2 -> 4). So the rule is not "every answer must be sensitive to every column"; it
is "an answer must be sensitive to THE column it claims to be about".

WHAT THIS IS NOT. It does not prove the answer is right. An expression could read the
amount column and still compute something wrong, and this test would pass it. It proves
only that the answer is ABOUT what was asked -- which is the weaker, different, and
previously unchecked statement. `holds()` answers "is this expression sound"; this
answers "is this expression an answer to this question". A system with only the first
will confidently answer questions it never understood.

LIMITS, stated rather than discovered later. The probe perturbs one column at a time and
needs a numeric column it can change; a question whose referent is text ("which region
has the largest total") is not covered here. A question naming a column that does not
exist is the door's job to refuse, not this check's.
"""

from __future__ import annotations

import csv
import io
import math
import pathlib
from pathlib import Path

#: THE PROBE MUST ACTUALLY CHANGE THE COLUMN. A fixed probe is a false-positive machine.
#:
#: Measured: on a tree where every amount is already 7, replacing the column with 7 changes
#: nothing, so `what is the total amount` was reported as IGNORING `amount` -- a correct
#: answer accused of not reading the column it is entirely made of. Three of three correct
#: answers were flagged on that tree.
#:
#: The probe is therefore derived from the data: pick a value that no cell in the column
#: currently holds, so the column provably differs afterwards. If the column is empty
#: there is nothing to perturb and the check says so instead of guessing.
def _probe_for(values: list[float]) -> float:
    """A number that appears nowhere in `values`, so the perturbation is real."""
    present = set()
    for v in values:
        try:
            present.add(float(v))
        except (TypeError, ValueError):
            continue
    # start from something of the same scale so sums and means stay in a sane range
    scale = max((abs(v) for v in present), default=1.0) or 1.0
    candidate = round(scale * 7.0 + 1.0, 6)
    while candidate in present:
        candidate = round(candidate * 1.5 + 1.0, 6)
    return candidate


def _read_table(path: Path) -> tuple[list[str], list[list[str]]] | None:
    try:
        text = path.read_text()
    except OSError:
        return None
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return None
    return rows[0], rows[1:]


def _numeric_columns(header: list[str], body: list[list[str]]) -> list[str]:
    out = []
    for i, name in enumerate(header):
        vals = [r[i] for r in body if i < len(r) and r[i].strip()]
        if not vals:
            continue
        ok = 0
        for v in vals:
            try:
                float(v)
                ok += 1
            except ValueError:
                break
        if ok == len(vals):
            out.append(name)
    return out


def _perturb_reversed(path: Path, column: str) -> str | None:
    """The same table with `column` values REVERSED down the rows.

    WHY UNIFORM PERTURBATION IS NOT ENOUGH. Setting every value to the same number leaves
    the argmin/argmax unchanged -- every row ties, and the first one wins -- so
    `which region has the smallest amount` answered `north` no matter what the probe was,
    and was reported as ignoring `amount` while being entirely about it.

    Reversing the column keeps the multiset of values identical and changes WHICH ROW holds
    each one. A selection ("which region has the smallest") therefore flips, while an
    aggregate over the column does not move at all -- which is the correct, distinguishing
    behaviour: the two read the column in genuinely different ways.
    """
    got = _read_table(path)
    if got is None:
        return None
    header, body = got
    if column not in header:
        return None
    idx = header.index(column)
    values = [r[idx] if idx < len(r) else "" for r in body]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    for row, value in zip(body, reversed(values)):
        new = list(row)
        while len(new) <= idx:
            new.append("")
        new[idx] = value
        writer.writerow(new)
    return out.getvalue()


def _perturb(path: Path, column: str, value: float) -> str | None:
    """The same table with `column` set to `value` in every row, rendered as CSV text."""
    got = _read_table(path)
    if got is None:
        return None
    header, body = got
    if column not in header:
        return None
    idx = header.index(column)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    for row in body:
        new = list(row)
        while len(new) <= idx:
            new.append("")
        new[idx] = str(int(value)) if float(value).is_integer() else str(value)
        writer.writerow(new)
    return out.getvalue()


def _same(a, b) -> bool:
    """Values agree, comparing rendered answers as the proportions they represent."""
    if a is None or b is None:
        return a is None and b is None
    sa, sb = str(a).strip(), str(b).strip()
    if sa == sb:
        return True
    na, nb = _parse(sa), _parse(sb)
    if na is None or nb is None:
        return False
    if len(na) != len(nb):
        return False
    return all(abs(x - y) <= 1e-9 for x, y in zip(na, nb))


def _parse(text: str) -> list[float] | None:
    inner = text
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
    pieces = [p.strip() for p in inner.split(",")] if inner.strip() else []
    if not pieces:
        return None
    out = []
    for p in pieces:
        try:
            out.append(float(p))
        except ValueError:
            return None
    return out


def _referent_file(base: Path, column: str, prefer: str | None = None):
    for path in sorted(base.rglob("*.csv")):
        if prefer and path.name.lower() != prefer and path.stem.lower() != prefer:
            continue
        got = _read_table(path)
        if got and column in got[0]:
            return path
    return None


def depends_on_column(root: str, question_referent: str, ask, prefer_file=None) -> dict:
    """Does `ask(...)` change when the column it claims to be about changes?

    `ask` is called with a directory containing one perturbed table and returns the
    rendered answer, so this module never needs to know how the door works.

    Returns {"verdict": "depends" | "ignores" | "uncheckable", ...}. `uncheckable` is a
    real answer: a text referent, a missing column, or an answer that is not a number
    cannot be tested this way, and saying so is different from saying it passed.
    """
    base = Path(root)
    if not base.is_dir() or not question_referent:
        return {"verdict": "uncheckable", "why": "nothing to perturb"}

    first = _referent_file(base, question_referent, prefer_file)
    for path in ([first] if first else sorted(base.rglob("*.csv"))):
        got = _read_table(path)
        if got is None:
            continue
        header, body = got
        if question_referent not in header:
            continue
        if question_referent not in _numeric_columns(header, body):
            return {"verdict": "uncheckable",
                    "why": f"{question_referent!r} is not a numeric column, so changing "
                           f"it cannot be shown to affect a numeric answer"}
        original = ask(root)
        if original is None:
            return {"verdict": "uncheckable", "why": "the question was not answered"}

        idx = header.index(question_referent)
        col_values = []
        for r in body:
            if idx < len(r):
                try:
                    col_values.append(float(r[idx]))
                except ValueError:
                    pass
        probe = _probe_for(col_values)
        perturbed_text = _perturb(path, question_referent, probe)
        if perturbed_text is None:
            return {"verdict": "uncheckable", "why": "could not build the perturbed tree"}
        probe_root = _build_probe_tree(base, path, perturbed_text)
        if probe_root is None:
            return {"verdict": "uncheckable", "why": "could not build the perturbed tree"}
        try:
            moved = ask(probe_root)
        finally:
            _cleanup(probe_root)

        if _same(original, moved):
            return {"verdict": "ignores",
                    "column": question_referent,
                    "value": original,
                    "why": (f"the question names {question_referent!r}, and changing every "
                            f"value in that column to {probe:g} left the answer at "
                            f"{original}")}
        return {"verdict": "depends", "column": question_referent,
                "value": original, "perturbed": moved}

    return {"verdict": "uncheckable",
            "why": f"no table carries a column called {question_referent!r}"}


def _build_probe_tree(base: Path, changed: Path, text: str) -> str | None:
    """A copy of the tree with one file replaced. Copy, never mutate in place."""
    import shutil
    import tempfile

    try:
        dest = Path(tempfile.mkdtemp())
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            target = dest / path.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        (dest / changed.relative_to(base)).write_text(text)
        return str(dest)
    except OSError:
        return None


def _cleanup(root: str) -> None:
    import shutil

    shutil.rmtree(root, ignore_errors=True)


def numeric_referent(question: str, root: str) -> str | None:
    """Which column does this question name, if it names exactly one numeric column?

    THE FALSE POSITIVE THIS PREVENTS, measured before it shipped. `depends_on_column` was
    given the column to perturb by its caller, and the first caller passed `amount` for
    every question. `how many regions` was then reported as IGNORING `amount` -- which it
    does, correctly, because it never named amount. A question is only obliged to depend
    on the column it actually names.

    So the referent is read from the question's own words, matched against the table's
    headers, and the check applies only when the question picks out exactly one numeric
    column. Zero or several means there is nothing to hold it to, and this check says so.
    """
    words = [w.lower().strip("?,.:;!") for w in question.split()]
    words = [w for w in words if w]
    if not words:
        return None
    base = Path(root)
    # THE REFERENT IS SCOPED TO THE FILE THE QUESTION NAMES.
    #
    # Measured false positive: with `inventory.csv` and `returns.csv` both carrying
    # `units`, `what is the total units in returns.csv` perturbed inventory.csv -- the
    # answer correctly did not move, and it was reported as IGNORING its own referent.
    # When a question names a file, the column in that file is the referent and the same
    # header elsewhere is a different column about a different thing.
    named = {w.strip("?,.:;!") for w in words}
    tables = [(p, _read_table(p)) for p in sorted(base.rglob("*.csv"))]
    named_tables = [(p, t) for p, t in tables
                    if p.name.lower() in named or p.stem.lower() in named]
    if named_tables:
        tables = named_tables
    matches = set()
    for path, got in tables:
        if got is None:
            continue
        header, body = got
        numeric = set(_numeric_columns(header, body))
        for name in numeric:
            low = name.lower()
            for w in words:
                if w == low or w == low + "s" or w == low + "es":
                    matches.add(name)
    return matches.pop() if len(matches) == 1 else None


def check(root: str, question: str, ask) -> dict:
    """The whole check: find the column the question names, then perturb it."""
    referent = numeric_referent(question, root)
    if referent is None:
        return {"verdict": "uncheckable",
                "why": "the question does not pick out exactly one numeric column, so "
                       "there is no column it is obliged to depend on"}
    return depends_on_column(root, referent, ask)


def is_ordinal(answer) -> bool:
    """Is this answer a DECISION or a LABEL, as opposed to a quantity or a listing?

    THE FALSE POSITIVES THAT MADE THIS NECESSARY, each measured.

      * A comparison: `is the total units in returns.csv less than ...` answers `yes`. It
        is entirely about `units`, and its answer cannot move gradually because it is
        ordinal.
      * A selection: `which region has the smallest amount` answers `north`. Also entirely
        about `amount`. (This one needed a second fix -- a uniform probe leaves every row
        tied and the argmin unchanged; see `_perturb_reversed`.)

    AND THE CASE THAT MADE IT TOO BROAD. Treating every non-number as a decision flagged
    `what is amount in sales.csv` -- answered `3 line(s)`, a LISTING -- as ignoring
    `amount`. A listing is not about the column's values at all, so demanding that it move
    with them is a category error of the opposite kind.

    So this is deliberately narrow: a yes/no word, or a single short bare word that could
    be a cell value. Anything with structure -- a count of lines, a bracketed vector, a
    sentence -- is not a decision and is not given the flip test.
    """
    text = str(answer).strip()
    low = text.lower()
    if low in {"yes", "no", "true", "false"}:
        return True
    if _parse(text) is not None:
        return False
    # a bare label like `north`; not `3 line(s)`, not `[1, 2]`, not a rendered sentence
    return bool(text) and " " not in text and "(" not in text and not text.startswith("[")


def depends_ordinal(root: str, column: str, ask, prefer_file=None) -> dict:
    """For a yes/no answer, look for a FLIP rather than for movement.

    A comparison is about its operands even though its answer is a decision, so the probe
    sweeps the column in both directions and asks whether the decision ever changes. If it
    never does, the comparison is not about that column and the accusation stands.
    """
    from pathlib import Path

    base = Path(root)
    pick = _referent_file(base, column, prefer_file)
    for path in [pick] if pick else sorted(base.rglob("*.csv")):
        got = _read_table(path)
        if got is None:
            continue
        header, body = got
        if column not in header:
            continue
        if column not in _numeric_columns(header, body):
            return {"verdict": "uncheckable",
                    "why": f"{column!r} is not a numeric column"}
        original = ask(root)
        if original is None:
            return {"verdict": "uncheckable", "why": "the question was not answered"}
        idx = header.index(column)
        values = []
        for row in body:
            if idx < len(row):
                try:
                    values.append(float(row[idx]))
                except ValueError:
                    pass
        if not values:
            return {"verdict": "uncheckable", "why": "the column holds no numbers"}
        low, high = min(values), max(values)
        span = (abs(high - low) or abs(high) or 1.0)
        # sweep far enough either way that any comparison against this column flips
        reversals = [_perturb_reversed(path, column)]
        for probe in (low - span * 10, high + span * 10, 0.0, low, high):
            reversals.append(_perturb(path, column, probe))
        for text in reversals:
            if text is None:
                continue
            probe_root = _build_probe_tree(base, path, text)
            if probe_root is None:
                continue
            try:
                moved = ask(probe_root)
            finally:
                _cleanup(probe_root)
            if not _same(original, moved):
                return {"verdict": "depends", "column": column,
                        "value": original, "perturbed": moved}
        return {"verdict": "ignores", "column": column, "value": original,
                "why": (f"the question names {column!r} and the answer is {original}, but "
                        f"sweeping that column far past either side of its range never "
                        f"changed the decision")}
    return {"verdict": "uncheckable", "why": f"no table carries {column!r}"}


def named_file_in(question: str, root: str) -> str | None:
    """The file name the question mentions, if it mentions exactly one."""
    words = {w.lower().strip("?,.:;!") for w in str(question).split()}
    hits = []
    for path in sorted(pathlib.Path(root).rglob("*.csv")):
        if path.name.lower() in words or path.stem.lower() in words:
            hits.append(path.name)
    return hits[0] if len(hits) == 1 else None


def check_answer(root: str, question: str, ask, answer=None) -> dict:
    """The entry point the door uses: ordinal answers get the flip test."""
    referent = numeric_referent(question, root)
    if referent is None:
        return {"verdict": "uncheckable",
                "why": "the question does not pick out exactly one numeric column"}
    prefer = named_file_in(question, root)
    if answer is not None and is_ordinal(answer):
        return depends_ordinal(root, referent, ask, prefer_file=prefer)
    if answer is not None and _parse(str(answer)) is None:
        # A LISTING IS NOT A QUANTITY AND CANNOT BE EXPECTED TO MOVE.
        #
        # `what is amount in sales.csv` answers `3 line(s)` -- it lists the file. That
        # answer is not a function of the column's VALUES, so demanding that it change
        # when they change is a category error. Measured: it was reported as ignoring
        # `amount`, which is the worst possible verdict for it -- the question was
        # answered, the reader just wanted to know what is in the file.
        #
        # Saying so is different from saying it passed, which is why this is its own
        # verdict rather than a quiet True.
        return {"verdict": "uncheckable", "column": referent,
                "why": (f"the answer {answer!r} is not a quantity, so there is no sense in "
                        f"which it could depend on the values of {referent!r}")}
    return depends_on_column(root, referent, ask, prefer_file=prefer)
