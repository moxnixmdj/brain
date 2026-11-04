"""A measured conclusion outlives the process that measured it.

WHAT WAS WRONG, MEASURED. Every measurement this system makes is thrown away when the
process exits:

    canonical/runtime/answer_ledger_v1.py     _LEDGER   in-process list, reset() clears it
    canonical/runtime/decomposition_law_v1.py _CACHE    in-process dict
    canonical/runtime/referent_dependence_v1  nothing persisted at all

A fresh process reports `cache: 0` and rediscovers `sum -> sum`, `mean -> nothing`, and
that `[150,150,250]` recombines by sum, FOREVER. `answer()` is a pure function of
(question, tree), so nothing it learns can ever change what it does next. That is as
static as code gets, and it is the thing that made six rounds of checks into six rounds
of the same check.

AND IT WAS ALREADY SOLVED. `experience_v1` records a recurring fact as (what x how it
failed), persists it, gates it with an e-process, and lets a suppression EXPIRE into a
forced retry so a memory can be wrong. Its own docstring describes the defect above:
"Ask the same thing twice and the machine started from nothing." Nothing on the answer
path read it -- zero references in inspect_v1, decomposition_law_v1, answer_ledger_v1,
referent_dependence_v1.

This module is the missing join, and it is deliberately small: it does not invent a
memory, it calls the one that exists.

THE GATE, AND WHY NOT `is_suppressed`. `experience_v1.status` reports two different
things and only one of them is usable here:

    credited     e >= 20 AND mean > 0 -- this held, repeatedly. REUSE IS SAFE.
    suppressed   STRUCTURAL evidence only, because -- its comment says it plainly --
                 "a statistical run of failures is usually a fact about WHAT WAS ASKED,
                 not about the machine, so it must not disable anything."

Reusing a discovery on `credited` is the e-process doing its proper job: crediting a
correction. Suppressing an answer because it failed before would be the system refusing a
question on the grounds that it has answered it wrongly in the past, which is a grudge,
not a memory. So the ledger never suppresses an answer; it remembers which CONSTRUCTIONS
produced answers that ignored their referent, and it records the discovery itself.

WHY A DISCOVERY IS RECORDED AS A SUCCESS. `decomposes_by("sum") == "sum"` is a true,
checkable statement about the operator's own function. Every time the door answers a
question using a sum over groups, it is evidence that the sum decomposition held. Record
it, and after ten consistent observations the system reuses the discovery instead of
re-probing -- the e-process crediting a correction, which is exactly its documented job.

THE LIMIT, STATED. A credited cell is a shortcut, not a proof: `decide()` returns the
remembered recombination and the caller is still expected to check the answer it produces
with it. Memory removes the NEED TO MEASURE, never the need to check -- the same rule
`teach_resolution` states for itself.
"""

from __future__ import annotations

from canonical.runtime import experience_v1 as _E

#: Separates the kinds of thing this module remembers. A discovery about an operator and
#: a pathology in an answer are different sorts of fact and must not share a prefix.
_DISCOVERY = "decompose"
_PATHOLOGY = "referent"


def _cell(kind: str, subject: str) -> str:
    return f"{kind}.{_E.cell_of(subject, kind)}".replace("|", ".")


def remember_decomposition(kind: str, combination: str | None, path=None) -> dict:
    """Record that this aggregate decomposes (or does not) this way. Call on every use."""
    verdict = "DECOMPOSES_BY_" + combination.upper() if combination else "DOES_NOT_DECOMPOSE"
    return _E.record(f"{_DISCOVERY}.{kind}", verdict, succeeded=True, path=path)


def recall_decomposition(kind: str, path=None) -> tuple[bool, str | None]:
    """The remembered recombination for this aggregate -- ONLY once it has earned reuse.

    Returns (known, combination). `known` is False when there is no memory or the evidence
    has not cleared the gate, and the caller is expected to MEASURE. Returning a guess on
    thin evidence would make the system confident about something it has not established,
    which is the disease this module exists to cure.

    The first version of this built the cell name by hand and never matched what `record`
    wrote, so it returned "unknown" forever and the memory did nothing -- a cache that is
    always empty is indistinguishable from no cache, which is the exact defect being fixed
    one layer down. It now reads the cells that exist under this operator's prefix.
    """
    best: tuple[bool, str | None] = (False, None)
    best_e = 0.0
    for cell in _decomposition_cells(kind, path=path):
        state = _E.status(cell, path=path)
        if not state.get("credited"):
            continue
        if float(state.get("e_value") or 0.0) > best_e:
            best_e = float(state.get("e_value") or 0.0)
            best = (True, _combination_from(cell))
    return best


def _decomposition_cells(kind: str, path=None) -> list[str]:
    from canonical.runtime import experience_v1 as E

    try:
        state = E._load(path)
        cells = state.get("cells", {})
    except (OSError, ValueError, AttributeError):
        return []
    prefix = f"{_DISCOVERY}.{kind}|"
    return [c for c in cells if str(c).startswith(prefix)]


def _combination_from(cell: str) -> str | None:
    why = str(cell).split("|", 1)[-1]
    if why.startswith("decomposes_by_"):
        return why[len("decomposes_by_"):]
    return None


def remember_referent_ignored(question: str, column: str, expression: str, path=None) -> dict:
    """Record a construction that produced an answer ignoring the column it named.

    NOT A BAN. This is evidence about a CONSTRUCTION, kept so that the same construction
    is visible as having failed before. `experience_v1` is explicit that statistical
    failure must not disable a capability, and that rule is honoured here: this records,
    it does not suppress.
    """
    return _E.record(f"{_PATHOLOGY}.{column}",
                     f"ignored_by.{_E.signature_of(expression)}",
                     succeeded=False, path=path)


def referent_pathology(column: str, expression: str, path=None) -> dict:
    """How much evidence there is that this construction ignores this column."""
    cell = _E.cell_of(f"{_PATHOLOGY}.{column}",
                      f"ignored_by.{_E.signature_of(expression)}")
    return _E.status(cell, path=path)
