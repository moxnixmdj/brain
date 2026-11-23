"""Ask the subcommand before you call it unbound.

THE WALL THIS ANSWERS, AND THE MEASUREMENT THAT FOUND IT
--------------------------------------------------------
The owner's proposal was: enter an arbitrary environment, scan it, then retrieve what
you know and what you do NOT know, and close the gaps from instant knowledge. The tree
already has every half of that -- a census that scans and classifies, an instant-knowledge
tier (local guides then web, completeness-gated), and `ignorance_ledger_v1` which ranks
gaps by expected value and whose own index entry reads "ranks what it does not know".

Nothing joined them, so the question this round asked is not "how do we build the
retrieval" but **"what, exactly, does the machine not know"** -- because that is the
quantity every other part is a function of, and nobody had measured it.

Measured on 20 real programs (1,491 declared operations, 33 doors):

    793 UNBOUND  665 SENSOR  33 DOOR          <- classify()'s three-way split
    of the 793:  689 "documents_no_usage_line"
                 103 "requires a slot"
                   1 ran and failed

Then the 793 were collapsed into KINDS, and the result is the whole of this module:

    3 kinds of ignorance, not 793 unknowns -- and one program (openssl, 676) is 85% of it.

That mattered enough to check before designing anything. Opening the *parent* help text
of a program that has subcommands and believing it describes the child is the defect:

    openssl --help              -> no usage line, 0 flags, 38 subcommand candidates
    openssl asn1parse -help     -> "Usage: asn1parse [options]" and 9 flags

Measured: 38 of 38 admitted subcommands have their OWN usage line, and all 38 were being
reported as though they had none. `_own_text(prog)` asks exactly one question --
`prog -h` -- so a contract is built from the parent and then applied to every child.

So the 689-op kind was not "the program documents nothing". It was **we asked the wrong
question**. That is the owner's own instinct, arrived at by measurement rather than by
assertion, and it is worth stating exactly: a doubt that has not been *asked* is not
knowledge of a gap. It is a gap in the asking, and it is fixed by asking.

THE UNIT OF IGNORANCE IS A QUESTION, AND ITS PRICE IS THE DOUBT IT DELETES
-------------------------------------------------------------------------
`ignorance_ledger_v1` ranks a gap by a Laplace-smoothed success rate divided by cost. Its
docstring is honest that this is a prior, not a measurement:

    p_useful = (times closing it helped + 0.5) / (times tried + 1)

An untried doubt and an untried doubt about something else both score 0.5. That is right
for exploration and useless for deciding what to so much as ask: it cannot say that one
question settles 676 operations while another settles one, because it has never counted
the operations behind a doubt.

Here a doubt is a QUESTION, and what it is worth is measured before anything is tried:

    worth(question) = how many operations' verdicts this one question decides

Not a prior, not a rate, not a fitted weight: a count, computed from the census's own
rows. `what_to_ask()` returns the questions in that order, so the first ask is the one
that deletes the most doubt per unit of work -- 676 operations in one subcommand sweep.
That is the "expected value" idea kept and the unfalsifiable half dropped.

WHY THIS IS NOT A NEW PLANNER, A NEW SCANNER, OR A NEW LEDGER
------------------------------------------------------------
Every mechanism here already existed and is REUSED, not rebuilt:

    C.census, C.parse_contract, C.bind, C.commit_check_many, C.classify   the scan
    C.admits, C.looks_like_help, C._run_capped                            the asking
    ignorance_ledger_v1.note / resolve                                    the persistence

What is new is one join: the contract must be taken from **the scope the operation runs
in**. `classify()` already returns a three-way split; this module gives each unbound
operation the narrowest contract that could decide it, and reports which questions are
worth asking in what order.

THE HONEST LIMIT, MEASURED
--------------------------
Asking is not learning. A subcommand whose own usage line is complete turns 676 UNBOUND
into operations that are merely FEWER UNBOUND -- many of them still unbound, now for a
truer reason ("this flag needs a file that is not here"). The claim this module makes is
only the one it can prove: the DOUBT was mis-stated, and stating it correctly is cheaper
than any amount of retrieving. It does not claim the operations become doors, and the
receipt reports how many did.

Model calls: 0. Network calls: 0. Parameters: 0. Spend: $0.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import tool_census_v1 as C

SCHEMA = "PROJECT_BRAIN_ASK_THE_SUBCOMMAND_V1"

#: The kinds of doubt, decided STRUCTURALLY -- from evidence we hold, never from the
#: prose sentence `classify()` writes. `classify()`'s `why` strings are good for a human
#: reading a receipt and are the wrong input for a machine deciding what to do next: the
#: first version of this module classify-by-substring and inherited the "documents no
#: usage line" wording for operations whose document simply had not been fetched.
NOT_ASKED = "NOT_ASKED"
"""The document exists at a narrower scope and was never read. Fixed by asking."""

DROVE_IT_WRONG = "DROVE_IT_WRONG"
"""It ran and FAILED (non-zero exit) without moving the tree. This is not the machine
failing to understand the program; it is us handing the program an argument it refused.
It was invisible before: the census called any unchanged run `NO_EFFECT`, so 545 of
openssl's 676 rows were reported as "exited cleanly and moved nothing" while carrying
exit 1. The fix is a better invocation, and the doubt is about OUR driving."""

NO_DOCUMENT = "NO_DOCUMENT"
"""Asked at every scope and the program emits no usage line anywhere. Not fixable."""

SLOT_UNSUPPLIED = "SLOT_UNSUPPLIED"
"""The document has a required slot and the binder has nothing to put in it."""

NEEDS_CONSTRUCTION = "NEEDS_CONSTRUCTION"
"""Documented, and the operation still did not run to completion. The remaining kind."""

KINDS = (NOT_ASKED, DROVE_IT_WRONG, NO_DOCUMENT, SLOT_UNSUPPLIED, NEEDS_CONSTRUCTION)

#: Whether chasing a doubt can pay, decided from what has already been asked.
#:
#: The frontier's best idea for this is LLM-IDEA's triage of a plateau into "capability
#: limit / resolvable within the design class / certified exhausted" -- the point being
#: that an agent which cannot tell "I have not looked yet" from "no further search will
#: recover this" either keeps refining against a target its data cannot constrain, or
#: gives up on something one more question would have settled. It arrives here as a
#: property of each KIND, earned from the evidence rather than from a learned ranker:
#:
#:   ASK            nothing at this scope has been read yet -- one question settles it
#:   DRIVE          it was asked and the invocation was refused -- the fix is ours
#:   EXHAUSTED      asked at every scope and no document exists -- stop here
#:   UNDETERMINED   documented and still not run to completion -- needs the next step
ASK, DRIVE, EXHAUSTED, UNDETERMINED = (
    "RESOLVABLE_BY_ASKING", "RESOLVABLE_BY_DRIVING", "CERTIFIED_EXHAUSTED",
    "UNDETERMINED")

RESOLVABILITY = {
    NOT_ASKED: ASK,
    DROVE_IT_WRONG: DRIVE,
    SLOT_UNSUPPLIED: DRIVE,
    NO_DOCUMENT: EXHAUSTED,
    NEEDS_CONSTRUCTION: UNDETERMINED,
}

_USAGE = re.compile(r"^\s*usage:", re.IGNORECASE | re.MULTILINE)
_REQUIRED = re.compile(r"[<(\[]([A-Z][A-Z0-9_-]{1,24})[>)|\]]")


def own_text_here(prog: str, subcommand: str | None = None) -> str:
    """The program's own description of ITSELF AT THIS SCOPE, or "".

    `tool_census_v1._own_text` asks `prog -h` and nothing else, which is correct for a
    program and wrong for a subcommand: `openssl -h` describes no operation, while
    `openssl asn1parse -h` describes nine. This asks the narrowest scope that exists.

    `-h` first, for the reason the census already documents: `--help` on some programs
    opens a pager or a man viewer and hands back an error message as if it were a manual.
    """
    argv = [prog] if subcommand is None else [prog, subcommand]
    best = ""
    for flag in ("-h", "--help"):
        text = C._run_capped([*argv, flag])["text"]
        # KEEP THE LONGEST text, not the first one `looks_like_help` accepts.
        #
        # Measured: `openssl -h` prints a genuine subcommand table that
        # `looks_like_help()` rejects, so the first version returned "" for a program
        # that had answered perfectly. Gating a DOCUMENT on a predicate about what a
        # help page looks like is the wrong test -- the question is "did this scope say
        # anything about itself", and length with a usage line or a name table is the
        # evidence. The census uses `looks_like_help` to decide whether a probe is worth
        # trusting; here the text is kept and the KIND decides later.
        if len(text) > len(best):
            best = text
        if C.looks_like_help(text):
            return text
    return best


def scope_text(prog: str, subcommand: str | None = None) -> dict[str, Any]:
    """What was asked, what came back, and whether it was a document at all."""
    text = own_text_here(prog, subcommand)
    return {"prog": prog, "subcommand": subcommand,
            "asked_as": [prog] + ([] if subcommand is None else [subcommand]) + ["-h"],
            "chars": len(text), "has_usage": bool(_USAGE.search(text)), "text": text}


def contracts_by_scope(prog: str, subcommands: Sequence[str] = (),
                       parent: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """A contract PER SCOPE, so an operation is read against the scope it runs in.

    The parent is always asked (it is the only thing that can name the subcommands in the
    first place). Each admitted subcommand then gets its own text and its own contract,
    and that contract -- not the parent's -- is what the binder reads.
    """
    parent_text = dict(parent or {})
    if "text" not in parent_text:
        parent_text = scope_text(prog)
    parent_contract = C.parse_contract(parent_text["text"], prog)
    out: dict[str, Any] = {"": {"text": parent_text, "contract": parent_contract}}
    for sub in subcommands:
        got = scope_text(prog, sub)
        # a subcommand that refused the question is not a document; falling back to the
        # parent is the truth for it, and recording that is better than inventing a scope
        out[sub] = {"text": got,
                    "contract": C.parse_contract(got["text"], prog) if got["text"]
                    else parent_contract,
                    "fell_back_to_parent": not got["text"]}
    return out


def subcommands_of(prog: str, parent_text: str | None = None) -> list[str]:
    """The words the program's own help puts in its name column, ADMITTED by asking.

    Admission is the census's decision and is reused, not re-derived: a word that refuses
    with a usage error is prose, not a door.
    """
    text = parent_text if parent_text is not None else scope_text(prog)["text"]
    contract = C.parse_contract(text, prog)
    admitted: list[str] = []
    for name in contract.get("subcommand_candidates") or []:
        if C.admits(prog, name, parent_text=text).get("admitted"):
            admitted.append(str(name))
    return admitted


# --------------------------------------------------------------------------- #
# the kinds, decided structurally
# --------------------------------------------------------------------------- #
def kind_of(operation: Mapping[str, Any], *, scope: Mapping[str, Any],
            subcommand: str | None) -> tuple[str, str]:
    """Which KIND of doubt this operation actually is, and the evidence for it.

    None of these branches reads a sentence. Each asks a question whose answer is in the
    documents: does a document exist here (SLOT/askable), is there a usage line in it, and
    does it carry a required slot the binder cannot fill.
    """
    text = str(scope.get("text") or "")
    has_usage = bool(_USAGE.search(text))
    if subcommand is not None and not has_usage:
        # the narrow scope was asked and answered nothing. If the PARENT has a usage line
        # the program does document itself and this word is prose; the census already
        # decides that by admission, so reaching here means the word was admitted and
        # still documented nothing -- a genuinely undocumented operation.
        return NO_DOCUMENT, f"{subcommand!r} was asked and printed no usage line"
    if not has_usage:
        return NO_DOCUMENT, "asked at every scope and no usage line was printed"
    required = [m.group(1) for m in _REQUIRED.finditer(text)]
    if required and not any(word in " ".join(required).upper()
                            for word in ("SCRIPT", "COMMAND")):
        return SLOT_UNSUPPLIED, f"the usage line requires {required[0]}"
    return NEEDS_CONSTRUCTION, ("documented and still did not run to completion: "
                                f"declared {operation.get('effect_class')}")


def kinds_of_ignorance(classified: Mapping[str, Any],
                       scopes: Mapping[str, Any],
                       rows: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Every unbound operation, sorted into kinds, with the question that would decide it.

    The grouping IS the answer to "what should we ask first": operations that share a
    question are one doubt, not many, and the questions are ranked by how many verdicts
    each one decides.
    """
    verdicts = {str(r.get("id")): r for r in rows}
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in KINDS}
    for row in classified.get("unbound") or []:
        rid = str(row.get("id") or "")
        sub = rid.split(".")[0] if "." in rid else None
        scope = (scopes.get(sub) or scopes.get("") or {}).get("text") or {}
        measured = verdicts.get(rid) or {}
        if str(measured.get("verdict") or "") == "FAILED_NO_EFFECT":
            # the strongest evidence there is: the program REFUSED the invocation. It
            # outranks every documentary guess, because it is a fact about a real run.
            kind, why = (DROVE_IT_WRONG,
                         f"exited {measured.get('exit')} and moved nothing: the "
                         f"invocation was refused")
        else:
            kind, why = kind_of(row, scope=scope, subcommand=sub)
        buckets[kind].append({"id": rid, "subcommand": sub, "evidence": why})
    by_res: dict[str, int] = {}
    for kind, rows in buckets.items():
        by_res[RESOLVABILITY[kind]] = by_res.get(RESOLVABILITY[kind], 0) + len(rows)
    return {"schema": SCHEMA + "_KINDS",
            "counts": {k: len(v) for k, v in buckets.items()},
            "total": sum(len(v) for v in buckets.values()),
            # THE DISTINCTION THAT DECIDES WHETHER TO SPEND: a doubt that one question
            # would settle and a doubt that no question can settle are both "unknown",
            # and treating them alike is how an agent burns its budget re-asking a
            # program that documents nothing -- or gives up on one it never asked.
            "resolvability": by_res,
            "chase": {r: n for r, n in by_res.items() if r != EXHAUSTED},
            "by_kind": buckets}


def what_to_ask(prog: str, subcommands: Sequence[str] = (),
                classified: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """The questions worth asking, most doubt deleted first. A COUNT, not a prior.

    Each row is one question -- "ask this scope for its own description" -- and its worth
    is the number of operation verdicts that question decides. That number is computed
    from the census's rows, so it is a measurement of damage, not an estimate of value,
    and it cannot be gamed by a ranking that flatters itself.
    """
    if classified is None:
        classified = classify_at_scope(prog, subcommands)["classified"]
    unbound = list(classified.get("unbound") or [])
    if not unbound:
        return []
    grouped: dict[str | None, list[str]] = {}
    for row in unbound:
        rid = str(row.get("id") or "")
        sub = rid.split(".")[0] if "." in rid else None
        grouped.setdefault(sub, []).append(rid)
    questions = [{"ask": [prog] + ([] if sub is None else [sub]) + ["-h"],
                  "scope": sub, "decides": len(ids), "operations": ids}
                 for sub, ids in grouped.items()]
    questions.sort(key=lambda q: (-q["decides"], str(q["scope"])))
    for i, q in enumerate(questions, 1):
        q["rank"] = i
    return questions


def classify_at_scope(prog: str, subcommands: Sequence[str] = (),
                      max_ops: int = 60) -> dict[str, Any]:
    """Census, then re-read every operation against the contract OF ITS OWN SCOPE.

    The census's own `classify()` is fed one contract taken from the parent, so it is the
    thing that produced the false kind in the first place. Here the operations are the
    census's, and only the contract each one is bound with changes -- which is exactly
    the defect, isolated: one input, and the verdicts move.
    """
    census = C.census(prog, depth=2, max_ops=max_ops)
    parent = scope_text(prog)
    # REUSE the census's admission: it already asked every candidate and recorded which
    # words are doors and how many operations each scope declares. Discovering them again
    # here was a second probe of the same thing, and the second one was worse.
    if subcommands:
        subs = list(subcommands)
    else:
        subs = [str(row.get("subcommand")) for row in
                (census.get("subcommands_admitted") or []) if row.get("subcommand")]
    scopes = contracts_by_scope(prog, subs, parent=parent)
    bound = []
    for op in census["operations"]:
        rid = str(op.get("id") or "")
        sub = rid.split(".")[0] if "." in rid and rid.split(".")[0] in scopes else None
        contract = scopes[sub or ""]["contract"]
        bound.append(C.bind(op, contract=contract))
    graded = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
    # classify() is reused for the three-way split, with the PARENT contract only for its
    # own construction-reason string -- that string is not used for the kinds, and saying
    # so here is cheaper than a reader wondering which one is authoritative. The KINDS are
    # decided by `kinds_of_ignorance`, from the documents, never from this string.
    classified = C.classify(census["operations"], graded,
                            contract=scopes[""]["contract"],
                            admitted=len(census["operations"]))
    return {"prog": prog, "subcommands_admitted": subs, "scopes_asked": len(scopes),
            "classified": classified, "rows": list(graded.get("rows") or [])}


def measure(programs: Sequence[str] = ("cp", "mv", "rm", "gzip", "tar", "sed", "find",
                                       "sort", "grep", "cut", "ln", "touch", "zip",
                                       "openssl"),
            max_ops: int = 60) -> dict[str, Any]:
    """What is actually unbound once every operation is read in its own scope."""
    per_program: list[dict[str, Any]] = []
    totals = {k: 0 for k in KINDS}
    before_after = {"unbound_before": 0, "unbound_after": 0}
    for prog in programs:
        if C.shutil.which(prog) is None:
            continue
        try:
            run = classify_at_scope(prog, max_ops=max_ops)
        except Exception as exc:  # a program that cannot be read is reported, not hidden
            per_program.append({"prog": prog, "error": f"{type(exc).__name__}: {exc}"})
            continue
        cl = run["classified"]
        kinds = kinds_of_ignorance(cl, contracts_by_scope(
            prog, run["subcommands_admitted"], parent=scope_text(prog)),
            run.get("rows") or ())
        for k in KINDS:
            totals[k] += kinds["counts"][k]
        per_program.append({
            "prog": prog,
            "subcommands_admitted": run["subcommands_admitted"],
            "counts": dict(cl.get("counts") or {}),
            "kinds": kinds["counts"],
            "resolvability": kinds["resolvability"],
            "questions": what_to_ask(prog, run["subcommands_admitted"], cl)[:3]})
        before_after["unbound_after"] += int((cl.get("counts") or {}).get("UNBOUND") or 0)
    ranked = sorted(per_program, key=lambda r: -(r.get("counts") or {}).get("UNBOUND", 0))
    return {"schema": SCHEMA,
            "authority": "NONE__PRODUCER_RUN_SANDBOX_ONLY",
            "model_calls": 0, "network_calls": 0, "parameters": 0,
            "programs_measured": len(per_program),
            "kinds_total": totals,
            "kinds": list(KINDS),
            "per_program": per_program,
            "worst_offender": (ranked[0]["prog"] if ranked else None),
            "worst_offender_unbound": ((ranked[0].get("counts") or {}).get("UNBOUND", 0)
                                       if ranked else 0),
            "the_join": ("an operation is bound against the contract of the scope it "
                         "runs in; the census asked every operation against the parent")}


# --------------------------------------------------------------------------- #
# the join to what the tree already had: a doubt must survive the process
# --------------------------------------------------------------------------- #
def note_to_ledger(kinds: Mapping[str, Any], *, path: str | None = None) -> dict[str, Any]:
    """Write each KIND as one doubt in `ignorance_ledger_v1`, with its measured price.

    THE POINT OF THIS FUNCTION is that it was missing. The ledger's own index entry reads
    "ranks what it does not know by expected value", and NOTHING ON THE CENSUS PATH EVER
    WROTE TO IT: 960 unbound operations were re-derived from nothing on the next run, and
    every doubt the machine has ever had about a program was forgotten when the process
    exited. `ignorance_loop_v1` had already assembled the circuit for the
    financial-QA path; the program path was never joined to it.

    `cost` is set to the number of operations behind the doubt, NOT to a guess at how long
    closing it takes. The ledger's `value = p_useful / (1 + cost)` then ranks a doubt that
    blocks 558 operations below one that blocks 2 -- which is backwards for choosing what
    to fix. So this function passes `cost` honestly as the count and lets `what_to_ask()`
    be the ordering that is used for action. Two orderings, and the receipt says which one
    is which rather than pretending one number serves both questions.
    """
    from canonical.runtime import ignorance_ledger_v1 as L

    out: dict[str, Any] = {"schema": SCHEMA + "_LEDGER", "noted": [], "ledger_path": None}
    for kind in KINDS:
        n = int((kinds.get("counts") or {}).get(kind) or 0)
        if not n:
            continue
        gid = L.note(f"program doubt kind {kind}",
                     why=f"{kind} holds {n} operations whose verdict is unknown",
                     cost=float(n), path=path)
        out["noted"].append({"kind": kind, "operations": n, "gap_id": gid})
    try:
        out["ledger_path"] = str(path or L.DEFAULT_STATE)
        out["open_after"] = L.open_gaps(path)
    except Exception:
        pass
    return out
