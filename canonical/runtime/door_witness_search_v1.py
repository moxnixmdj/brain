#!/usr/bin/env python3
"""Turn a machine's DECLARED operations into operations it will actually run.

THE MEASURED PROBLEM THIS EXISTS FOR
------------------------------------
`the_machine_publishes_its_own_doors_v1` reads every program's own help text and
enumerates what it declares. On this machine it finds 5,760 declared operations across
36 programs. Run every one of them exactly as declared and most do not run at all:

    5,760 declared | 219 doors | 1,189 sensors | 4,352 UNBOUND

and 641 of 660 unbound rows in a depth-1 census are `FAILED_NO_EFFECT`: the process
exited non-zero and moved nothing. That is not a fact about the machine. It is a fact
about the invocation -- a *bare flag is not an action*, and the operand that turns a flag
into an action has a FORM the declaration names and the binder does not supply:

    grep --ignore-case in.txt          -> exit 1   (in.txt read as the PATTERN)
    grep --ignore-case alpha in.txt    -> exit 0   (pattern, then a file)
    diff --normal in.txt               -> exit 2   (FILES means two)
    diff --normal in.txt in.txt        -> exit 0
    cut --bytes=out.bin in.txt         -> exit 1   (BYTE-LIST, not a path)
    cut --bytes=1 in.txt               -> exit 0
    tar --list --file=out.bin in.txt   -> exit 2   (the trailing operand is not wanted)
    tar --list --file=<a real archive> -> exit 0

Every one of those flips on the FORM of a value, never on new knowledge about the
program. So the missing mechanism is not a bigger table. It is a SEARCH over a small,
universal alphabet of value forms, judged by the machine's own exit code.

WHAT THIS DOES
--------------
For one program: take the operations it DECLARES, and for each operation walk a bounded
sequence of *moves* over a *form alphabet* until the process exits 0. Nothing here names
a program, a flag, or a flag's meaning.

    FORMS   in.txt 1 1-2 alpha a.* : %s in.json real.tar real.zip out.bin
    MOVES   substitute a --flag=VALUE  |  append k operands  |  prepend k operands
            |  drop the last token, then append  |  drop the last two, then append

The room the trials run in is built from two things and no third: the census's own seed
forms, and whatever the program's OWN successful runs left behind (aliased under every
name the operations use, so a consumer that names `out.bin` receives an artifact a
producer actually made).

WHAT IS LEARNED, AND WHY IT TRANSFERS
-------------------------------------
Nothing is remembered per program. A success is recorded against the operation's SLOT
SIGNATURE -- a triple computed from the declaration alone:

    (required positional arity, whether any declared flag carries a value,
     number of optional positionals)

`diff FILES` and `join FILE1 FILE2` and `comm FILE1 FILE2` have the same signature, so a
move discovered on one is proposed for the others without a single trial. The ledger is
plain JSON: inspectable, editable, deletable, and it never rewrites what a trial measured.

WHAT THIS DOES NOT CLAIM
------------------------
- Exiting 0 is not competence. `grep a.*` with no match exits 1 legitimately; a sensor
  and a refusal are different rows and this module reports them separately.
- A residue remains, and it is the honest output. `convert`'s 251 operations want an
  IMAGE and this machine's declared surface contains no producer of one; `find`'s
  expression grammar wants a predicate before a path. Those are *domain gaps*, and the
  number of distinct gaps -- not the number of dead doors -- is what instant knowledge
  would have to close.
- Zero model calls, zero network, zero parameters, bounded trials.

Authority: NONE. Producer-run sandbox measurement.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import tool_census_v1 as C  # noqa: E402

SCHEMA = "PROJECT_BRAIN_DOOR_WITNESS_SEARCH_V1"
LEDGER_SCHEMA = "PROJECT_BRAIN_DOOR_WITNESS_LEDGER_V1"
DEFAULT_LEDGER = REPO / "canonical" / "astra_runtime" / "state" / "DOOR_WITNESS_LEDGER_V1.json"

#: THE UNIVERSAL ALPHABET. Ordered cheapest-and-most-likely first: the search stops at
#: the first form the machine accepts, so order is trial count, not knowledge. Every
#: member is a value a POSIX program can be handed on any machine in any locale.
FORMS: tuple[str, ...] = ("in.txt", "1", "1-2", "alpha", "a.*", ":", "%s",
                          "in.json", "real.tar", "real.zip", "out.bin")

#: Names every machine-made artifact is also reachable under. A consumer that declares
#: `--file=out.bin` gets a real archive under that name, because the producer wrote one.
ALIAS_NAMES: tuple[str, ...] = ("out.bin", "in.txt", "real.tar", "real.zip")

#: The tokens the census's own binder writes as a value. A substitution that does not
#: cover these covers nothing: `unzip -p in.txt` names its operand positionally, so the
#: first version of this module walked eleven forms that never entered the command and
#: reported zero recoveries on seven held-out programs. The list is the BINDER'S
#: vocabulary, not a program's: these are the strings `bind()` supplies when it has
#: nothing better, so replacing them is replacing ITS guess.
BINDER_VALUES: tuple[str, ...] = ("in.txt", "out.bin", "seed.txt", "data.txt",
                                  "a.txt", "out", "txt")

#: Moves, as (name, how many tokens to drop from the tail, operands to place, where).
#: There is no BARE move: dropping nothing and placing nothing IS the command already
#: tried, and eleven forms of it were eleven identical trials.
MOVES: tuple[tuple[str, int, int, str], ...] = (
    ("DROP1", 1, 0, "after"),
    ("DROP2", 2, 0, "after"),
    ("APPEND1", 0, 1, "after"),
    ("APPEND2", 0, 2, "after"),
    ("PREPEND1", 0, 1, "before"),
    ("PREPEND2", 0, 2, "before"),
    ("APPEND1", 1, 1, "after"),
    ("APPEND2", 1, 2, "after"),
    ("PREPEND1", 1, 1, "before"),
    ("APPEND1", 2, 1, "after"),
    ("APPEND2", 2, 2, "after"),
)

#: How many value-substitution trials one operation may spend. Substitution is tried
#: before placement because it is one token of change, not a new argument.
SUBSTITUTE_BUDGET = 0
#: Trials per operation, all moves together. Bounded so the census never becomes the
#: expensive part of the loop it feeds.
DEFAULT_BUDGET = 70

#: Seconds one trial may take. A witness command is a single program doing one thing on
#: a few small files; anything needing longer is not a witness, and waiting for it made a
#: held-out fleet of 250 operations cost 1,480 seconds -- almost all of it spent watching
#: `wget` time out. Two seconds is 45x the median and keeps the census cheap.
TRIAL_SECONDS = 2.0


# --------------------------------------------------------------------------- #
# signature: what a learned move is a rule ABOUT
# --------------------------------------------------------------------------- #

def signature(operation: dict[str, Any]) -> str:
    """The declaration's SHAPE, computed so that a rule can travel between programs.

    Three facts, none of which names a program, a flag, or a meaning:

      arity   how many positionals the declaration says it requires
      values  whether any declared flag carries a value of its own
      option  how many positionals the declaration brackets as optional

    `diff FILES` (2, False, 0) and `join FILE1 FILE2` (2, False, 0) share a signature,
    which is the whole reason one success can be reused on the other.
    """
    required = [name for name in (operation.get("required_slots") or [])
                if "OPTION" not in str(name).upper()]
    optional = [name for name in (operation.get("positionals") or [])
                if "OPTION" not in str(name).upper() and name not in required]
    carries = any(bool((flag or {}).get("placeholder"))
                  for flag in (operation.get("declared_flags") or [])
                  if isinstance(flag, dict))
    return f"arity={len(required)}|values={int(carries)}|option={len(optional)}"


# --------------------------------------------------------------------------- #
# the room
# --------------------------------------------------------------------------- #

def _artifact_room(program: str, operations: Sequence[dict[str, Any]],
                   *, timeout: float = TRIAL_SECONDS) -> tuple[str, dict[str, Any]]:
    """A room seeded with the census's forms and with what the program itself produced.

    The producer pass is what makes `--file=<archive>` testable at all: the machine is
    asked to make an archive, and the artifact it makes is offered back to the
    operations that read one. Every artifact is additionally written under every alias
    name, so a declaration that names `out.bin` is answered rather than refused.
    """
    root = tempfile.mkdtemp(prefix="brain-witness-room-")
    seeds = C.trial_seeds()
    for name, data in seeds:
        (pathlib.Path(root) / name).write_bytes(data)
    # EVERY CANDIDATE ARTIFACT GETS A NAME OF ITS OWN, AND THE SEARCH DECIDES.
    #
    # Writing a candidate over `out.bin` was unsound: a producer that copied the seed
    # passed the "did it read something" test and left a file that was not an archive
    # under the name every tar consumer reads. A unique name removes the need for any
    # oracle at all -- `tar --list --file=art3` exits 0 exactly when art3 is a real
    # archive, so the search is the judge and no content test is invented here.
    before = set(os.listdir(root))
    seen_hashes: set[str] = set()
    artifacts: list[str] = []
    counter = 0
    for operation in operations:
        if operation.get("effect_class") != "WRITES":
            continue
        argv = list(C._command_form(operation))
        for candidate in (argv, [*argv, "in.txt"]):
            if not any(token in before for token in candidate if not token.startswith("-")):
                continue
            trial = tempfile.mkdtemp(prefix="brain-witness-produce-")
            try:
                for name in os.listdir(root):
                    source = pathlib.Path(root) / name
                    if source.is_file():
                        shutil.copy2(source, pathlib.Path(trial) / name)
                observed = set(os.listdir(trial))
                run = C._run_capped(candidate, cwd=trial, timeout=timeout,
                                    env=dict(os.environ, HOME=trial))
                if run.get("exit") != 0:
                    continue
                admitted = False
                for name in sorted(set(os.listdir(trial)) - observed):
                    full = pathlib.Path(trial) / name
                    if not full.is_file():
                        continue
                    try:
                        data = full.read_bytes()
                    except OSError:
                        continue
                    if not data:
                        continue
                    import hashlib as _hashlib
                    digest = _hashlib.sha256(data).hexdigest()
                    if digest in seen_hashes:
                        continue
                    seen_hashes.add(digest)
                    target = pathlib.Path(root) / f"art{counter}"
                    counter += 1
                    target.write_bytes(data)
                    artifacts.append(target.name)
                    admitted = True
                if admitted:
                    break
            finally:
                shutil.rmtree(trial, ignore_errors=True)
    for builder in (C._tar_bytes, _zip_bytes):
        try:
            data = builder()
        except Exception:
            continue
        import hashlib as _hashlib
        digest = _hashlib.sha256(data).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        target = pathlib.Path(root) / f"art{counter}"
        counter += 1
        target.write_bytes(data)
        artifacts.append(target.name)
    return root, {"artifacts": artifacts, "named": sorted(before)}


def _zip_bytes() -> bytes:
    """A one-member zip, built from the standard library so no program is needed."""
    import io
    import zipfile
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("member.txt", b"alpha\n")
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# the moves
# --------------------------------------------------------------------------- #

def _with_value(argv: Sequence[str], form: str) -> list[list[str]]:
    """Every place a VALUE sits in the command, re-valued one at a time.

    Two places, and the second is the one that was missing: the right-hand side of
    `--flag=VALUE`, and any bare token the binder supplied as an operand (`in.txt`).
    A positional operand is as much a declared slot as a flag's value -- `grep -i in.txt`
    reads in.txt as the PATTERN -- so a search that only re-valued flags could never
    flip the programs whose slots are positional.
    """
    out: list[list[str]] = []
    for index, token in enumerate(argv):
        if token.startswith("-") and "=" in token and not token.startswith("--="):
            head, _, _value = token.partition("=")
            out.append([*argv[:index], f"{head}={form}", *argv[index + 1:]])
        elif token in BINDER_VALUES:
            out.append([*argv[:index], form, *argv[index + 1:]])
    return out


def variants(argv: Sequence[str], *, drop: int = 0, count: int = 0,
             where: str = "after", form: str = "in.txt") -> list[str]:
    """One move applied to one command: drop a tail, then place `count` operands."""
    argv = list(argv)
    body = argv[:len(argv) - drop] if drop else argv
    if len(body) < 1:
        return []
    if count == 0:
        return body
    operands = [form] * count
    if where == "before":
        return [*body[:1], *operands, *body[1:]]
    return [*body, *operands]


#: Move kinds, in the order an untaught search tries them. A taught search replaces
#: this order with one learned from what worked on OTHER programs.
#: CHEAPEST FIRST, AND COMPOSITION LAST. This order was measured, not chosen: putting
#: composition second -- where it looks most powerful -- spent a fixed budget on two-slot
#: trials before single-slot ones had been tried, and the addressable count fell from 358
#: to 348. Likewise a GLOBALLY RECOMPUTED order learned from earlier programs fell to 344:
#: what transfers between programs is the RULE for a signature, not the order of search.
#: Both were removed; the ledger still reports the move counts as evidence.
MOVE_KINDS: tuple[str, ...] = ("SUBSTITUTE", "DROP1", "DROP2", "APPEND1", "APPEND2",
                               "PREPEND1", "PREPEND2", "COMPOSE")


def _kind(label: str) -> str:
    return label.split(":", 1)[0]


def _trials(argv: Sequence[str], forms: Sequence[str] = FORMS,
            order: Sequence[str] = MOVE_KINDS) -> Iterable[tuple[str, list[str]]]:
    """The bounded search, ordered by what has worked before, if anything has.

    A bigger move set is not a better search: adding composition ADDED sixteen trials
    ahead of the moves that already worked and the addressable count fell from 358 to
    348. The budget is the constraint, so the only honest way to add a move is to learn
    where it belongs in the order.
    """
    rank = {kind: index for index, kind in enumerate(order)}
    generated: list[tuple[str, list[str]]] = []
    for item in _generate(argv, forms):
        generated.append(item)
    generated.sort(key=lambda item: rank.get(_kind(item[0]), len(rank)))
    yield from generated


def _generate(argv: Sequence[str], forms: Sequence[str]) -> Iterable[tuple[str, list[str]]]:
    """Every move, unordered."""
    for form in forms:
        for candidate in _with_value(argv, form):
            yield f"SUBSTITUTE:{form}", candidate
    # COMPOSITION: two declared slots filled at once.
    #
    # `grep --extended-regexp in.txt` needs the PATTERN and the FILE, and a search that
    # only ever changes one value can reach `grep -E alpha` (which reads standard input,
    # finds nothing and exits 1) or `grep -E in.txt` (which reads in.txt as the pattern
    # and exits 1) but never both. One slot at a time is a search of a projection; the
    # operations live in the product. The secondary alphabet is deliberately tiny -- the
    # seed file, an integer and a word -- because it is tried once per primary form.
    for form in forms:
        for secondary in ("in.txt", "1", "alpha"):
            for candidate in _with_value(argv, form):
                if secondary in candidate:
                    continue
                yield f"COMPOSE:{form}+{secondary}", [*candidate, secondary]
    for name, drop, count, where in MOVES:
        for form in forms:
            candidate = variants(argv, drop=drop, count=count, where=where, form=form)
            if candidate:
                yield f"{name}:{form}", candidate


# --------------------------------------------------------------------------- #
# driving one command
# --------------------------------------------------------------------------- #

def drive(argv: Sequence[str], room: str, *, snapshot: str | None = None,
          timeout: float = TRIAL_SECONDS) -> dict[str, Any]:
    """Run one command in the room; say what it exited with and whether the tree moved."""
    before = C._digest(room)
    run = C._run_capped(list(argv), cwd=room, timeout=timeout,
                        env=dict(os.environ, HOME=room))
    changed = C._digest(room) != before
    if snapshot:
        C._restore(snapshot, room)
    return {"argv": list(argv), "exit": run.get("exit"), "changed": changed,
            "text": (run.get("text") or "")[:400]}


def _first_success(argv: Sequence[str], room: str, snapshot: str, *,
                   budget: int, skip: str | None = None,
                   fingerprint: set[str] | None = None,
                   forms: Sequence[str] = FORMS,
                   order: Sequence[str] = MOVE_KINDS) -> dict[str, Any] | None:
    """Walk the search until the machine says the command ran AND DID SOMETHING.

    An exit-0 trial whose output is the program's own usage text is not a success, and
    stopping at it is how a search reports 250 phantom recoveries: `convert -adjoin`
    exits 0, prints its help, and has not converted anything. The walk therefore
    continues past INERT, and only a DOOR or a SENSOR ends it.
    """
    spent = 0
    timeouts = 0
    for label, candidate in _trials(argv, forms, order):
        if skip and label == skip:
            continue
        if spent >= budget or timeouts >= 2:
            return None
        spent += 1
        run = drive(candidate, room, snapshot=snapshot)
        if run["exit"] is None:
            # a command that does not return is not a command this search can judge.
            # Two of them are enough to abandon the operation: a network client's
            # thirty trials are thirty timeouts, and the census must stay cheap.
            timeouts += 1
        if run["exit"] == 0:
            effect = effect_of(run, fingerprint or set())
            if effect == "INERT":
                continue
            run["moved_by"] = label
            run["trials"] = spent
            run["effect"] = effect
            return run
    return None


def discover(program: str, operations: Sequence[dict[str, Any]], *,
             budget: int = DEFAULT_BUDGET, reuse: dict[str, str] | None = None,
             timeout: float = TRIAL_SECONDS,
             order: Sequence[str] = MOVE_KINDS) -> dict[str, Any]:
    """For one program: which declared operations will run, and what made them run.

    Three outcomes per operation, kept apart because they mean different things:

      DRIVEN     the command the census already built exits 0
      RECOVERED  a move from the alphabet made it exit 0 (the move is reported)
      REUSED     a move learned on ANOTHER operation's signature made it exit 0,
                 with no search spent on this program
      RESIDUE    nothing in the alphabet made it run; the signature is recorded so one
                 gap is counted once, not once per door
    """
    reuse = reuse or {}
    started = time.perf_counter()
    fingerprint = help_fingerprint(program)
    room, room_facts = _artifact_room(program, operations, timeout=timeout)
    # ARTIFACTS FIRST. A machine-made artifact is the witness a consumer is most likely
    # to accept, and putting the primitive forms ahead of it spent the whole budget on
    # `1` and `1-2` before the archive that actually works. Order is trial count only.
    forms = tuple(room_facts.get("artifacts") or ()) + tuple(FORMS)
    snapshot = C._snapshot(room)
    rows: list[dict[str, Any]] = []
    try:
        for operation in operations:
            argv = list(C._command_form(operation))
            sig = signature(operation)
            run = drive(argv, room, snapshot=snapshot)
            row: dict[str, Any] = {"id": operation["id"], "argv": argv, "signature": sig}
            if run["exit"] == 0:
                effect = effect_of(run, fingerprint)
                row.update(outcome="DRIVEN" if effect != "INERT" else "INERT",
                           effect=effect, changed=run["changed"])
                rows.append(row)
                continue
            if sig in reuse:
                candidate = variants(argv, form=reuse[sig].split(":")[-1],
                                     drop=_move(reuse[sig])[1],
                                     count=_move(reuse[sig])[2],
                                     where=_move(reuse[sig])[3])
                if candidate:
                    reuse_run = drive(candidate, room, snapshot=snapshot)
                    if reuse_run["exit"] == 0:
                        effect = effect_of(reuse_run, fingerprint)
                        if effect != "INERT":
                            row.update(outcome="REUSED", effect=effect,
                                       moved_by=reuse[sig], winning_argv=candidate,
                                       changed=reuse_run["changed"])
                            rows.append(row)
                            continue
            spent = _first_success(argv, room, snapshot, budget=budget,
                                   fingerprint=fingerprint, forms=forms, order=order)
            if spent:
                effect = spent.get("effect") or effect_of(spent, fingerprint)
                if effect != "INERT":
                    row.update(outcome="RECOVERED", effect=effect,
                               moved_by=spent["moved_by"], winning_argv=spent["argv"],
                               changed=spent["changed"], trials=spent["trials"],
                               exit_was=run["exit"], said=run["text"])
                    rows.append(row)
                    continue
            row.update(outcome="RESIDUE", exit_was=run["exit"], said=run["text"])
            rows.append(row)
    finally:
        shutil.rmtree(snapshot, ignore_errors=True)
        shutil.rmtree(room, ignore_errors=True)
    counts = collections.Counter(row["outcome"] for row in rows)
    return {"schema": SCHEMA, "program": program, "operations": len(rows),
            "counts": dict(counts), "rows": rows, "room": room_facts,
            "seconds": round(time.perf_counter() - started, 3),
            "model_calls": 0, "parameters": 0}


def _move(label: str) -> tuple[str, int, int, str]:
    """The move a label names, defaulting to the bare command."""
    for name, drop, count, where in MOVES:
        if label.startswith(name + ":") or label == name:
            return name, drop, count, where
    return "BARE", 0, 0, "after"


# --------------------------------------------------------------------------- #
# exit 0 is not an answer
# --------------------------------------------------------------------------- #

#: Lines long enough to be prose rather than a flag table's left column.
_PROSE = 24


def help_fingerprint(program: str) -> set[str]:
    """The lines the program prints when it is asked what it does.

    This is the knowledge-free test for the illusion this module was built to avoid:
    `convert -adjoin` alone exits 0 and prints its usage, which a search that scored
    "exit 0" would have booked as 250 recovered capabilities.
    """
    try:
        text = C._own_text(program)
    except Exception:
        return set()
    return {line.strip() for line in str(text).splitlines() if len(line.strip()) >= _PROSE}


def effect_of(run: dict[str, Any], fingerprint: set[str]) -> str:
    """What an exit-0 invocation actually did: DOOR, SENSOR, or INERT.

    DOOR    the tree moved
    SENSOR  the tree did not move and the program answered: a value printed, or silence
    INERT   the tree did not move and the output is the program's own usage text. A
            program that answers "you did not give me an argument" has not run; it asked.

    SILENCE IS AN ANSWER. `tar --diff` on an unchanged archive exits 0 and prints
    nothing, and `diff` on two identical files does the same: those are successful
    verifications, not dead doors. Treating an empty answer as INERT rejected every
    silent success the search found -- 146 of tar's operations -- which is the opposite
    failure to the one this function exists to catch, and just as dishonest.
    """
    if run.get("changed"):
        return "DOOR"
    text = run.get("text") or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "SENSOR"
    echoed = sum(1 for line in lines if line in fingerprint)
    if fingerprint and echoed / max(1, len(lines)) > 0.5:
        return "INERT"
    return "SENSOR"


# --------------------------------------------------------------------------- #
# learning: the ledger
# --------------------------------------------------------------------------- #

def learn(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Compile discoveries into rules over SIGNATURES -- the unit that transfers.

    A signature that needed two different moves in two places is not learned: it is
    reported as AMBIGUOUS, because a rule that contradicts itself is a guess wearing a
    rule's clothes.
    """
    proposals: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for row in rows:
        if row.get("outcome") in ("RECOVERED", "REUSED") and row.get("moved_by"):
            proposals[row["signature"]][row["moved_by"]] += 1
    rules: dict[str, Any] = {}
    ambiguous: dict[str, Any] = {}
    for sig, counter in proposals.items():
        move, count = counter.most_common(1)[0]
        if len(counter) > 1:
            ambiguous[sig] = {"all_moves": dict(counter), "kept": move,
                              "why_not": "the same signature accepted more than one move; "
                                         "the most frequent survived and the rest are recorded"}
        rules[sig] = {"move": move, "evidence": count,
                      "all_moves_seen": dict(counter)}
    kinds = collections.Counter()
    for row in rows:
        if row.get("outcome") in ("RECOVERED", "REUSED") and row.get("moved_by"):
            kinds[_kind(row["moved_by"])] += 1
    order = [kind for kind, _ in kinds.most_common()]
    order += [kind for kind in MOVE_KINDS if kind not in order]
    return {"rules": rules, "ambiguous": ambiguous, "move_kinds": dict(kinds),
            "order": order}


def load_ledger(path: pathlib.Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_LEDGER
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"schema": LEDGER_SCHEMA, "rules": {}, "ambiguous": {}}
    if not isinstance(data, dict) or data.get("schema") != LEDGER_SCHEMA:
        return {"schema": LEDGER_SCHEMA, "rules": {}, "ambiguous": {},
                "refused": f"LEDGER_SCHEMA_MISMATCH:{path}"}
    data.setdefault("rules", {})
    data.setdefault("ambiguous", {})
    return data


def save_ledger(ledger: dict[str, Any], path: pathlib.Path | None = None) -> dict[str, Any]:
    """Atomic whole-file replacement; the store is never appended to in place."""
    path = pathlib.Path(path or DEFAULT_LEDGER)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return {"schema": LEDGER_SCHEMA, "path": str(path),
            "rules": len(ledger.get("rules") or {})}


def reuse_map(ledger: dict[str, Any]) -> dict[str, str]:
    return {sig: row["move"] for sig, row in (ledger.get("rules") or {}).items()
            if isinstance(row, dict) and row.get("move")}


# --------------------------------------------------------------------------- #
# the census over a fleet
# --------------------------------------------------------------------------- #

def operations_of(program: str, *, depth: int = 1) -> list[dict[str, Any]]:
    contract = C.parse_contract(C._own_text(program), program)
    census = C.census(program, depth=depth)
    return [C.bind(operation, contract=contract) for operation in census["operations"]]


def run_fleet(programs: Sequence[str], *, depth: int = 1, budget: int = DEFAULT_BUDGET,
              ledger: dict[str, Any] | None = None, learn_online: bool = True,
              timeout: float = TRIAL_SECONDS) -> dict[str, Any]:
    """Every program, in order; rules learned on one are available to the next.

    `learn_online=False` measures the opposite thing honestly: a program is driven with
    NOTHING learned from the ones before it, which is the zero-shot number.
    """
    reuse = reuse_map(ledger or {})
    order = MOVE_KINDS
    reports = []
    for program in programs:
        if not shutil.which(program):
            reports.append({"program": program, "absent": True})
            continue
        operations = operations_of(program, depth=depth)
        report = discover(program, operations, budget=budget, reuse=reuse,
                          timeout=timeout, order=order)
        reports.append(report)
        if learn_online:
            learned = learn(report["rows"])
            merged = dict(reuse)
            merged.update({sig: row["move"] for sig, row in learned["rules"].items()})
            reuse = merged
            # NOTE, MEASURED: carrying a globally learned ORDER to the next program made
            # the result worse (344 against 358 addressable). What transfers is the
            # signature RULE; the order does not. The ledger records the order as
            # evidence and the search does not use it.
    counts = collections.Counter()
    effects = collections.Counter()
    for report in reports:
        for key, value in (report.get("counts") or {}).items():
            counts[key] += value
    total = sum(counts.values())
    # ADDRESSABLE MEANS THE ROW DID SOMETHING.
    #
    # The first version computed total - RESIDUE, which counts every INERT row -- an
    # operation that exited 0 by printing its own usage -- as addressable. `convert`
    # alone inflated the headline by 30. The honest count is the rows whose effect is
    # DOOR or SENSOR, which is exactly DRIVEN + RECOVERED + REUSED.
    for report in reports:
        for row in report.get("rows") or []:
            effects[row.get("effect") or "NONE"] += 1
    return {"schema": SCHEMA + "_FLEET", "programs": reports, "totals": dict(counts),
            "operations": total, "effects": dict(effects),
            "doors": effects.get("DOOR", 0), "sensors": effects.get("SENSOR", 0),
            "inert": effects.get("INERT", 0),
            "driven_first": counts.get("DRIVEN", 0),
            "addressable": effects.get("DOOR", 0) + effects.get("SENSOR", 0),
            "addressable_fraction": round(
                (effects.get("DOOR", 0) + effects.get("SENSOR", 0)) / total, 4)
            if total else 0.0,
            "learned_rules": len(reuse)}


def residue_as_gaps(reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Count the DISTINCT gaps, not the dead doors.

    Every residue row carries the declaration's signature and the machine's own last
    words. Grouping by signature turns "250 operations cannot run" into "one domain is
    missing an image", which is the number instant knowledge would actually have to
    close.
    """
    gaps: dict[str, dict[str, Any]] = {}
    for report in reports:
        for row in report.get("rows") or []:
            if row.get("outcome") != "RESIDUE":
                continue
            gap = gaps.setdefault(row["signature"], {"signature": row["signature"],
                                                     "operations": 0, "programs": [],
                                                     "example_argv": row["argv"],
                                                     "said": row.get("said")})
            gap["operations"] += 1
            if report["program"] not in gap["programs"]:
                gap["programs"].append(report["program"])
    return {"distinct_gaps": len(gaps), "gaps": gaps}


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #

FLEET = ("tar", "jq", "gzip", "zip", "unzip", "xz", "openssl", "sort", "grep", "sed",
         "find", "stat", "tr", "cut", "comm", "join", "paste", "nl", "fold", "expand",
         "wc", "diff", "patch", "base64", "md5sum", "sha256sum", "split", "cksum", "seq",
         "yes", "timeout", "pr", "fmt", "od", "convert", "git", "ruff")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--programs", nargs="*", default=None)
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--ledger", type=pathlib.Path, default=None)
    parser.add_argument("--no-learn-online", action="store_true")
    args = parser.parse_args(argv)
    wanted = args.programs or [name for name in FLEET if shutil.which(name)]
    ledger = load_ledger(args.ledger)
    report = run_fleet(wanted, depth=args.depth, budget=args.budget, ledger=ledger,
                       learn_online=not args.no_learn_online)
    learned = learn(row for program in report["programs"]
                    for row in (program.get("rows") or []))
    merged = dict(ledger)
    merged.update({"schema": LEDGER_SCHEMA,
                   "rules": {**(ledger.get("rules") or {}), **learned["rules"]},
                   "ambiguous": {**(ledger.get("ambiguous") or {}), **learned["ambiguous"]}})
    saved = save_ledger(merged, args.ledger)
    gaps = residue_as_gaps(report["programs"])
    receipt = {"schema": SCHEMA + "_RECEIPT", "report": report, "learned": learned,
               "gaps": {"distinct_gaps": gaps["distinct_gaps"],
                        "gaps": gaps["gaps"]},
               "ledger": saved,
               "authority": "NONE__PRODUCER_RUN_SANDBOX"}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(json.dumps({"operations": report["operations"], "totals": report["totals"],
                      "addressable": report["addressable"],
                      "fraction": report["addressable_fraction"],
                      "learned_rules": len(learned["rules"]),
                      "distinct_gaps": gaps["distinct_gaps"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
