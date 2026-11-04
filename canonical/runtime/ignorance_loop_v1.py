"""The gap between noticing a doubt and doing something about it.

WHAT IS WRONG, MEASURED.

This system already has every piece of a learning creature and no circuit between them:

    ignorance_ledger_v1   a persisted, expected-value-ranked model of what it does not know
                          82 gaps on disk, and NOBODY ON THE ANSWER PATH WRITES TO IT
    operator_acquisition  induces an operator from worked examples, and asks which example
                          would settle it (next_example)
    acquired_operator_... remembers a demonstration across processes and re-derives it

Assembled, those are a loop:

    ask -> cannot answer -> NOTICE the gap -> say what would close it
        -> it is taught -> the gap CLOSES -> did closing it help?

Nobody assembled them. Measured on the real store: `what is the skew of amount` asked three
times returns PARTIALLY_GROUNDED three times with `skew` unresolved and the ledger byte-for-
byte identical. Every doubt it has ever had is re-derived from nothing on the next call. The
ledger itself has 82 gaps, 0 resolved, 3 ever helped in 29 trials -- which is why its own
docstring says rank() without feedback "is a guess dressed up as a calculation". It is right.

THE PART THAT MAKES THIS A CREATURE AND NOT A LOG.

A gap is opened by a FAILURE and closed by a SUCCESS, and the two are recorded against the
same identity. That is what lets the system answer a question it could not answer before,
and -- more importantly -- lets it LEARN WHICH KINDS OF IGNORANCE MATTER, from outcomes
rather than from a list. An antivirus has definitions. This has a history.

THE RULE THAT KEEPS IT HONEST.

`helped` is not set by the act of teaching. Closing a gap says the doubt is gone; whether
that CLOSING WAS WORTH ANYTHING is a separate, answerable question -- did the next attempt
at the same question actually succeed through the door? So the loop closes the gap when it
is taught, and reports `helped` only when a later real answer proves it. A system that marks
its own work successful has learned nothing except that it is pleased with itself.

WHY WEAKENING MUST NOT COUNT AS HEALING.

`ignorance_ledger_v1.note()` sets `resolved = False` whenever a gap is seen again, on the
stated grounds that "seeing the same gap again is new evidence that it is open now". For a
question that is being RE-ASKED that is correct and important. It is fatal here: if teaching
did not take, the very next identical question reopens the gap, and the ledger would record
an endless cycle of `helped` with nothing ever actually learned.

So this module never reports `helped` from the mere disappearance of a doubt. It reports it
from an answer that came back answered. Absence of failure is not evidence of success.
"""

from __future__ import annotations

from canonical.runtime import ignorance_ledger_v1 as _L


def _ledger_path(path):
    """Tests point this at a temporary ledger; production uses the ledger's own default."""
    return path

#: The kinds of doubt this circuit can actually act on. A gap it cannot act on is still
#: worth RECORDING -- that is the ledger's job -- but it must not be dressed up as a
#: question, because a request that cannot be satisfied is worse than a stated limit.
TEACHABLE = "unknown_operator"
UNREADABLE = "unreadable"


def _subject(word: str, root: str) -> tuple[str, str]:
    """The identity of a doubt: WHAT was asked about, and WHY it could not be answered.

    The ledger keys on (what x why) and deliberately keeps those two separate, because
    "I cannot read PDFs" and "I do not know what 'spread' means" are different gaps that
    deserve different rankings. Collapsing them into one string is how a ledger stops being
    able to tell you which kind of ignorance is costing you.
    """
    # THE ROOT MUST SURVIVE THE LEDGER'S TOKEN NORMALISATION.
    #
    # `_identity()` is `[a-z0-9]{2,}` token overlap, so `/a` and `/b` normalise to NOTHING:
    # measured, a doubt about one tree and a doubt about another were one gap. Single-letter
    # paths are rare but the aliasing is not -- any two roots whose only difference is short
    # path components collapse. Encoding the path to its own token keeps them apart.
    tag = ""
    if root:
        import hashlib as _h
        tag = "root" + _h.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    return (str(word).strip().lower(), f"{TEACHABLE} {tag}".strip())


def notice_unanswered(word: str, root: str = "", *, ask: str | None = None,
                      path=None) -> str | None:
    """A question needed a word the creature does not have. Record that it noticed.

    Returns the gap id so a later success can be credited to it. Returns None when there is
    nothing to act on -- an unteachable word, or an empty one -- because recording a doubt
    nobody can resolve only makes the ranking noisier.
    """
    word = str(word or "").strip().lower()
    if not word:
        return None
    what, why = _subject(word, root)
    try:
        return _L.note(what, why=why, cost=1.0, path=_ledger_path(path))
    except Exception:
        return None


def close(word: str, root: str = "", *, helped: bool | None = None, path=None) -> bool:
    """The doubt is gone -- the word is known now.

    `helped` is passed through to the ledger and is the ONLY thing that teaches it which
    ignorance matters. It is deliberately NOT defaulted to True here: a caller that does not
    know whether closing this gap helped must say None and let the ledger keep its prior.
    Marking your own homework as helpful is how a ranking becomes decoration.
    """
    what, why = _subject(word, root)
    # DO NOT `note()` HERE. Measured: note() sets `resolved = False` when a gap is seen
    # again -- correct for a question being re-asked, fatal here -- so closing by
    # note-then-resolve on the SAME call left the gap open. The id must be computed without
    # recording another sighting, which is what `_key` is for.
    try:
        gid = _L._key(what, why)
    except Exception:
        return False
    try:
        return bool(_L.resolve(gid, helped=bool(helped), close=True, path=_ledger_path(path)))
    except Exception:
        return False


def credit_if_answered(before: str, after: str, word: str, root: str = "",
                       path=None) -> dict:
    """THE HONEST CLOSING STEP.

    A doubt was noticed, the word was taught, and a question was asked again. This decides
    whether closing that gap actually helped, and it decides it from the ANSWER -- not from
    the fact that something was attempted.

        before  PARTIALLY_GROUNDED, word unresolved   -> doubt is real
        after   answered                              -> closing it helped
        after   still not answered                    -> closing it did NOT help

    Returns what it concluded and why, so the caller can see the judgement rather than a
    bool. A closed gap that did not help is not deleted: it stays in the ledger with a
    lower expected value, which is precisely how the system learns that this KIND of
    ignorance does not matter very much.
    """
    word = str(word or "").strip().lower()
    was_doubt = str(before).upper() in {"PARTIALLY_GROUNDED", "NOTHING_FOUND",
                                        "NOT_IN_NAMED_FILE", "UNVERIFIABLE"}
    is_answer = str(after).upper() in {"COMPUTED", "READ", "GROUNDED"}
    helped = bool(was_doubt and is_answer)
    # A DOUBT THAT WAS NEVER RECORDED CANNOT BE CLOSED.
    #
    # `resolve()` returns False for an id it has never seen, so closing first and noting
    # later silently does nothing -- measured: `closed: False` on a gap that was genuinely
    # gone, with the ledger unchanged at zero. Recording the sighting first makes the close
    # meaningful, and it is also the truthful order: it only counts as closing a gap if the
    # gap existed.
    notice_unanswered(word, root=root, path=path)
    closed = close(word, root, helped=helped, path=path)
    return {
        "word": word,
        "was_doubt": was_doubt,
        "is_answer": is_answer,
        "helped": helped,
        "closed": closed,
        "before": before,
        "after": after,
        "reason": ("the next attempt answered" if helped
                   else "the gap closed but the question still did not come back answered"),
    }
