"""Laws are synthesised, not typed.

THE CONSTRAINT THIS REMOVES. Every law in this system so far was a form I wrote down:
within_inputs, bounded_by_extremes, is_one_of_the_inputs, is_a_whole_number,
is_the_row_count. Five of them. They were measured -- the arithmetic decides which survive --
but the INVENTORY was mine, so an operator whose honest law is not in my five could not be
declared at all. `prod` is the standing proof: a product of [5, 15, 7] is 525, genuinely
different from every declared operator, and it is REFUSED because no form of mine is true of
it. Capability was being limited by a list of sentences.

AND THE FIVE WERE ALSO WEAK. The induced law for a median accepts 15 as the median of
[5, 15, 7], because 15 is an input and every form I wrote is a BOUND. A bound cannot see
order. What can see order is how many inputs lie below and above the result -- below == above
is what makes a number the middle one -- and no form of mine mentions it.

WHAT THIS DOES INSTEAD. A law is a RELATION between measurable features of (inputs, result):
how many inputs are below it, how many above, the count, the sum, the extremes, the mean. The
relations are generated, not chosen:

    feature  ::= n | sum | min | max | mean | r | below | above | n*min | n*max | r*n | n/2
    relation ::= A == B | A <= B | A >= B | A < B | A > B | |A-B| <= tol

That is a space of a few hundred forms, and the arithmetic decides which of them are TRUE.
The survivors are then ranked by how much of the wrong-answer space they exclude, and the
strongest is the law. A form that is true and says nothing is discarded, exactly as before --
the difference is that nothing is discarded for not being on my list.

THIS IS A SEARCH, NOT A PROOF. The space is finite and the forms are implications of the
data, so a stronger form that exists one relation away will be missed. What it does mean is
that the inventory grows with the FEATURES rather than with the sentences I thought of, and
that a law can be stronger than any I would have written -- which is the test below.
"""

from __future__ import annotations

import itertools

TOL = 1e-9

#: Features of an (inputs, result) pair. A feature is a number computed from the pair, or
#: None when it is undefined -- a form that needs an undefined feature does not hold.
FEATURES = (
    "n", "sum", "min", "max", "mean", "r",
    "below", "above", "n_min", "n_max", "r_n", "half_n", "n_r",
    "r_minus_min", "max_minus_r", "range", "r_over_n",
)


def features(values, result) -> dict:
    """Measure the pair. Nothing here knows what operator produced `result`."""
    vs = [float(v) for v in values if v is not None]
    n = len(vs)
    if not n or result is None:
        return {}
    try:
        r = float(result)
    except (TypeError, ValueError):
        return {}
    lo, hi, total = min(vs), max(vs), sum(vs)
    return {
        "n": float(n),
        "sum": total,
        "min": lo,
        "max": hi,
        "mean": total / n,
        "r": r,
        "below": float(sum(1 for v in vs if v < r)),
        "above": float(sum(1 for v in vs if v > r)),
        "n_min": n * lo,
        "n_max": n * hi,
        "r_n": r * n,
        "half_n": n / 2.0,
        "n_r": n / r if r else None,
        "r_minus_min": r - lo,
        "max_minus_r": hi - r,
        "range": hi - lo,
        "r_over_n": r / n,
    }


def _rel_eq(a, b):
    return a is not None and b is not None and abs(a - b) <= TOL


def _rel_le(a, b):
    return a is not None and b is not None and a <= b + TOL


def _rel_ge(a, b):
    return a is not None and b is not None and a >= b - TOL


def _rel_lt(a, b):
    return a is not None and b is not None and a < b - TOL


def _rel_gt(a, b):
    return a is not None and b is not None and a > b + TOL


def _rel_abs_le(a, b):
    # the tolerance that made below==above work on repeated values: |below - above| <= 1
    return a is not None and b is not None and abs(a - b) <= 1.0 + TOL


RELATIONS = (
    ("==", _rel_eq),
    ("<=", _rel_le),
    (">=", _rel_ge),
    ("<", _rel_lt),
    (">", _rel_gt),
    ("~=", _rel_abs_le),
)


def _make_form(left: str, op: str, right: str):
    rel = dict(RELATIONS)[op]

    def form(values, result):
        f = features(values, result)
        if not f:
            return False
        return rel(f.get(left), f.get(right))

    form.__name__ = f"law_{left}_{op.replace('=', 'e').replace('<', 'lt').replace('>', 'gt')}_{right}"
    form._source = (left, op, right)
    return form


def candidate_forms():
    """Every relation between two features. Generated, not chosen."""
    for left, right in itertools.permutations(FEATURES, 2):
        for op, _ in RELATIONS:
            yield _make_form(left, op, right)


def _true_on(form, tested) -> bool:
    return all(form(values, result) for values, result in tested)


def _rejects(form, tested) -> int:
    """How many CROSS-DATA wrong answers does this form refuse?

    A value that is honest for DIFFERENT inputs is a wrong answer for these ones. That is
    the same cross-data test that caught the constant arithmetic: a form which cannot tell
    one input set's answer from another's is not a check.
    """
    rejected = 0
    for i, (values_i, _) in enumerate(tested):
        for j, (_, result_j) in enumerate(tested):
            if i != j and not form(values_i, result_j):
                rejected += 1
    return rejected


#: Synthesis is a pure function of (arithmetic, probes) and costs ~1600 form evaluations, so
#: it is computed once per arithmetic. Without this the acquisition survey re-synthesised for
#: every candidate and a single test file took a minute.
_CACHE: dict = {}


def synthesise(fn, probes) -> list[dict]:
    """Every generated form that is TRUE of `fn` on the probes, with its reach.

    Returns them strongest first, deduplicated by the set of candidate values they reject
    -- two forms with the same reach are the same check with different wording.
    """
    key = (getattr(fn, "__qualname__", repr(fn)) + str(id(fn) if
            getattr(fn, "__qualname__", "").endswith("<locals>") else ""),
           tuple(tuple(p) for p in probes))
    if key in _CACHE:
        return _CACHE[key]
    tested = []
    for values in probes:
        try:
            got = fn(list(values))
        except Exception:
            return []
        if got is None:
            continue
        try:
            tested.append((list(values), float(got)))
        except (TypeError, ValueError):
            return []
    if len(tested) < 2:
        _CACHE[key] = []
        return []
    if len({round(r, 9) for _, r in tested}) < 2:
        _CACHE[key] = []              # a constant: no form about its data can check it
        return []

    out, seen = [], set()
    for form in candidate_forms():
        if not _true_on(form, tested):
            continue
        rejected = _rejects(form, tested)
        if not rejected:
            continue                  # true and says nothing
        # THE SIGNATURE IS WHAT THE FORM ACCEPTS, NOT WHAT IT REJECTS ON ONE SAMPLE.
        #
        # The first version fingerprinted a single invented wrong value per probe, so
        # `sum <= r` and `sum == r` looked different there and the weaker one was ranked
        # first on a counting tie-break. A form's character is the whole SET of values it
        # admits; two forms with the same admissible set are the same check.
        admitted = tuple(
            1 if form(values, result + k) else 0
            for values, result in tested
            for k in (-1000.0, -100.0, -10.0, -1.0, 0.0, 1.0, 10.0, 100.0, 1000.0)
        )
        if admitted in seen:
            continue
        seen.add(admitted)
        out.append({"form": form, "source": form._source,
                    "rejected": rejected, "reach": admitted})
    # THE REACH IS THE RANKING, and it is measured against the space of values that are
    # plausible answers, not against an arbitrary off-by-thousand.
    for row in out:
        row["excluded"] = _excluded_fraction(row["form"], tested)
    out.sort(key=lambda row: (-row["excluded"], -row["rejected"]))
    _CACHE[key] = out
    return out


def _excluded_fraction(form, tested) -> float:
    """What fraction of candidate answers between the extremes does this form refuse?

    The candidates are drawn from the data's own scale, because a wrong answer that is a
    thousand away is easy for anything to refuse and says nothing about a law's quality.
    """
    refused = considered = 0
    for values, honest in tested:
        span = max(max(abs(v) for v in values), abs(honest), 1.0)
        for k in range(-20, 21):
            considered += 1
            if not form(values, honest + k * span / 20.0):
                refused += 1
    return refused / considered if considered else 0.0
