"""Does a goal that no single door satisfies get a SEQUENCE, measured or not at all?

THE QUESTION THIS RECEIPT ANSWERS
---------------------------------
Round 4 answered "which door, for ONE move". Its own receipt named the wall: a goal
needing several moves IN ORDER is unanswered. This harness measures whether the join
now answers it -- and, because a plan is cheap to produce and easy to believe, it
refutes the plan against the real filesystem rather than trusting it.

WHAT IS MEASURED
----------------
1. Every door of `cp`, `mv`, `rm` and `gzip` is run on a seeded directory and its FULL
   signature is recorded. Full, not `moved()`: the subset looks like the natural saved
   row and it deletes the precondition -- see `a_goal_that_needs_two_moves_v1`.

2. A goal is fixed BEFORE the plan is made: "the name count fell at least once and
   content is still readable". That is the ordinary cleanup, and no single door does
   it -- `rm` falls the count but destroys content, `cp` keeps content but never falls
   the count. `one_move_answers` is required to come back empty; if it does not, the
   goal was not a sequence goal and the round has nothing to report.

3. The planner returns a sequence of move CLASSES. It is not told which doors exist
   beyond their measured signatures.

4. The plan is EXECUTED, twice, and both orders are recorded. The claim is not that a
   plan was produced; it is that the forward order achieves the goal on the real tree
   and the reverse order does not. A prediction that both orders satisfy, or neither,
   is a model that has not been tested by this experiment.

5. The same question is asked in three unrelated worlds, because a plan that only
   works in the world it was measured in is the exact defect the user named.

REFUSALS ARE MEASURED TOO
-------------------------
"That will never be refused" is worth testing. A goal that no sequence of the measured
moves can reach -- three readable contents from a one-content world -- must come back
`REFUSED` naming the missing fact, and the harness records it.

NO MODEL CALLS, NO PARAMETERS
-----------------------------
Nothing is fitted and nothing is asked of a model. The only inputs are the signatures
measured by running doors in a temporary directory, and the only output is a plan whose
every step is a measured class of move.
"""

from __future__ import annotations

import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import a_goal_that_needs_two_moves_v1 as P  # noqa: E402
from canonical.runtime import goal_to_door_v1 as G  # noqa: E402
from canonical.runtime import tool_census_v1 as C  # noqa: E402

SCHEMA = "PROJECT_BRAIN_A_GOAL_THAT_NEEDS_TWO_MOVES_RECEIPT_V1"
PROGRAMS = ("cp", "mv", "rm", "gzip")

#: The seed. `in.json` is present for a measured reason: the census binds `cp` and
#: `mv` to `in.json out.bin`, and without that file the door aborts on a missing
#: operand and produces no row at all. Round 4 seeded only `in.txt`/`in.gz`, so it
#: reported "4 programs" while `cp` and `mv` -- the two doors a person would reach for
#: -- contributed ZERO rows. That is measured here rather than inherited.
SEED = {
    "in.txt": b"PROBE_CONTENT_ALPHA",
    "in.gz": gzip.compress(b"PROBE_CONTENT_BETA", mtime=0),
    "in.json": b'{"a": 1, "b": [2, 3]}',
}

#: The goal, stated before any plan is made, and the same asking in every world:
#:
#:     remove the name the subject was in, and lose NOTHING doing it --
#:     the count of names and the count of readable names must be what they were.
#:
#: No single measured move meets it. `rm` falls the count. `cp` never removes a name.
#: `mv` removes one and creates one, so the count holds -- but `mv` does not count as a
#: removal, because a rename is not a cleanup. Two moves do it: copy, then delete.
#:
#: Two earlier goals were wrong and both were caught by the numbers rather than by
#: reading the code:
#:
#:   {REMOVED>=1, READABLE>=1}      `rm` met it outright in a three-name world, because
#:                                  those names held duplicate contents and deleting one
#:                                  destroyed nothing -- a goal a single door can meet
#:                                  says nothing about sequences.
#:   {REMOVED>=1, READABLE>=1, NAMES>=3}
#:                                  met by `rm` in any world already holding four names,
#:                                  so the same defect survived one world over.
#:
#: Making the threshold a function of the world's own size is what removes the escape:
#: the asking is always "just as many as there were", which no removal-only move meets.
def goal_for(names: int) -> P.Goal:
    return P.Goal(at_least={P.NAMES: names, P.READABLE: names, P.REMOVED: 1},
                  desc=(f"the subject's name removed, still {names} readable names "
                        f"-- nothing lost"))


VARIANTS = (
    ("TWO_NAMES_ONE_CONTENT", {"in.txt": b"PROBE_CONTENT_ALPHA",
                               "in.gz": gzip.compress(b"PROBE_CONTENT_BETA", mtime=0),
                               "in.json": b'{"a": 1}'}),
    ("THREE_NAMES", {"in.txt": b"PROBE_X", "in.gz": gzip.compress(b"PROBE_Y", mtime=0),
                     "in.json": b'{"z": 9}', "extra.txt": b"PROBE_Z"}),
    ("ONE_CONTENT_ONLY", {"in.txt": b"PROBE_X", "in.json": b'{"z": 9}'}),
)


def _read(where: pathlib.Path) -> dict[str, bytes]:
    return {str(p.relative_to(where)): p.read_bytes()
            for p in sorted(where.rglob("*")) if p.is_file() and not p.is_symlink()}


def _run(argv: Sequence[str], where: pathlib.Path) -> int | None:
    """Run one door IN `where`. `cwd` is not optional: the first version ran every
    door in the repository root, so every row measured the wrong directory."""
    try:
        done = subprocess.run(list(argv), cwd=str(where), stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=C.TRIAL_TIMEOUT,
                              env={**os.environ, "HOME": str(where)})
        return done.returncode
    except (OSError, subprocess.TimeoutExpired):
        return None


def _template(argv: Sequence[str]) -> list[str]:
    """An argv with its operand paths replaced by placeholders.

    This is the separation the whole round rests on: the SIGNATURE is the class, and
    the path in an argv is one instantiation of it. Keeping the template lets the
    harness run the same measured class against a DIFFERENT subject without measuring
    a new class -- and it is why no path is saved in a row.

    It matters concretely: the census binds `cp` to `in.json` and `rm` to `in.txt`, so
    executing the two doors as recorded makes `cp` copy the wrong file and the
    sequence then destroys the very content it was supposed to preserve. That is not a
    defect in the plan; it is the harness conflating the class with one binding.
    """
    out = []
    for token in argv:
        text = str(token)
        out.append("{SRC}" if text in SEED else
                   ("{DST}" if text in _OUTPUT_NAMES else text))
    return out


def _bind(template: Sequence[str], src: str, dst: str) -> list[str]:
    return [t.replace("{SRC}", src).replace("{DST}", dst) for t in template]


def _seed(where: pathlib.Path, variant: dict[str, bytes]) -> dict[str, bytes]:
    for child in where.iterdir():
        shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink()
    for name, data in variant.items():
        (where / name).write_bytes(data)
    return _read(where)


def measure_rows(programs: Sequence[str] = PROGRAMS) -> list[dict[str, Any]]:
    """Every census door, run on the seed, with its FULL signature."""
    rows: list[dict[str, Any]] = []
    for program in programs:
        if shutil.which(program) is None:
            continue
        census = C.census(program, depth=2, max_ops=60)
        contract = C.parse_contract(C._own_text(program), program)
        bound = [C.bind(op, contract=contract) for op in census["operations"]]
        graded = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
        declared = {op["id"]: op for op in census["operations"]}
        where = pathlib.Path(tempfile.mkdtemp(prefix="brain-twomoves-" + program + "-"))
        try:
            for door in [r for r in graded["rows"] if r["verdict"] in C.DOOR_VERDICTS]:
                argv = list(door.get("winning_invoked_as") or door.get("invoked_as") or [])
                if not argv:
                    continue
                before = _seed(where, SEED)
                if _run(argv, where) is None:
                    continue
                after = _read(where)
                if before == after:
                    continue
                full = G.signature(before, after)
                if not G.moved(full):
                    continue
                op = declared.get(door["id"], {})
                rows.append({"id": f"{program}:{door['id']}",
                             "tool": program, "door": door["id"], "invoked_as": argv,
                             "template": _template(argv),
                             "signature": full, "moved": G.moved(full),
                             "artifact_span": G.artifact_span(op.get("effect_class"),
                                                              op.get("flag"),
                                                              op.get("description")),
                             "source": "CENSUS_DOOR"})
        finally:
            shutil.rmtree(where, ignore_errors=True)
    return rows


def distinct_classes(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """How many classes of move the rows actually distinguish.

    A high door count with a low class count is the honest headline: 12 gzip doors and
    1 class is one move measured twelve times.
    """
    by_sig: dict[tuple, list[str]] = {}
    for row in rows:
        key = tuple(sorted(row["signature"].items()))
        by_sig.setdefault(key, []).append(f"{row['tool']}:{row['door']}")
    return {"doors": len(rows), "classes": len(by_sig),
            "by_class": [{"signature": dict(k), "doors": v} for k, v in by_sig.items()]}


def _execute(order: Sequence[str], where: pathlib.Path, variant: dict[str, bytes],
             src: str, dst: str, names_i_had: int) -> dict[str, Any]:
    """Run a sequence of measured classes for real, all bound to ONE subject."""
    before = _seed(where, variant)
    kept = {_payload(blob) for blob in before.values()}
    used = []
    for door_id in order:
        argv = _argv_of(door_id, src, dst)
        if argv is None:
            return {"ran": False, "reason": f"no measured argv for {door_id}"}
        rc = _run(argv, where)
        used.append({"door": door_id, "invoked_as": argv, "exit": rc})
        if rc != 0:
            return {"ran": False, "reason": f"{door_id} exited {rc}", "steps": used,
                    "after": sorted(_read(where))}
    after = _read(where)
    vanished = _vanished(before, after)
    lost = sorted(kept - {_payload(b) for b in after.values()})
    # the goal, MEASURED on the tree rather than read off the plan: a name went away
    # and no content that was readable before stopped being recoverable
    # THE SAME PREDICATE AS THE PLAN'S GOAL, read off the tree instead of the model.
    # Holding the counts to `names_i_had` is what "lose nothing" means on disk.
    return {"ran": True, "steps": used, "before": sorted(before), "after": sorted(after),
            "names_before": len(before), "names_after": len(after),
            "names_vanished": vanished, "contents_lost": len(lost),
            "goal_holds": (vanished >= 1 and not lost
                           and len(after) >= names_i_had)}


def _payload(blob: bytes) -> str:
    """One identity for the content a reader could recover from these bytes."""
    return G._payload_digest(blob)


#: door id -> the argv class, with its operands still as placeholders
_TEMPLATE: dict[str, list[str]] = {}

_OUTPUT_NAMES = ("out.bin",)


def _argv_of(door_id: str, src: str, dst: str) -> list[str] | None:
    template = _TEMPLATE.get(door_id)
    return None if template is None else _bind(template, src, dst)


def _vanished(before: dict[str, bytes], after: dict[str, bytes]) -> int:
    """How many NAMES went away, counted name by name.

    The first version compared `len(after) < len(before)` and was wrong in a way that
    made every sequence look like a failure: a copy adds a name and a delete removes
    one, so a net count of zero hid a real removal. REMOVED counts the times the count
    FELL, which is a cumulative fact and has to be measured that way.
    """
    return sum(1 for name in before if name not in after)


def measure() -> dict[str, Any]:
    started = time.time()
    rows = measure_rows()
    classes = distinct_classes(rows)
    for row in rows:
        _TEMPLATE[row["id"]] = list(row["template"])

    moves = [P.move_of(row, signature=row["signature"]) for row in rows]
    # one Move per CLASS, so the planner is not handed the same class 12 times
    unique: dict[tuple, P.Move] = {}
    for move, row in zip(moves, rows):
        unique.setdefault(tuple(sorted(row["signature"].items())), move)
    class_moves = list(unique.values())

    worlds = []
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-twomoves-exec-"))
    try:
        for label, variant in VARIANTS:
            start = P.world(names=len(variant), readable=len(variant))
            single = P.one_move_answers(goal_for(len(variant)), class_moves, start)
            entry: dict[str, Any] = {
                "world": label, "names": len(variant),
                "start": dict(start),
                "one_move_answers": single, "no_single_door": not single,
            }
            try:
                order = P.plan(start, goal_for(len(variant)), class_moves)
                entry["plan"] = [{"move": m, "tool": _tool_of(m, rows)} for m in order]
                # the subject is a file in the world whose content is UNIQUE there,
                # so losing it is measurable and duplicating it is visible
                src = next((n for n, b in variant.items() if n.endswith(".txt")),
                           sorted(variant)[0])
                forward = _execute(order, where, variant, src, "COPY", len(variant))
                reverse = _execute(list(reversed(order)), where, variant, src, "COPY",
                                    len(variant))
                entry["forward"] = forward
                entry["reverse"] = reverse
                entry["forward_holds"] = bool(forward.get("goal_holds"))
                entry["reverse_holds"] = bool(reverse.get("goal_holds"))
                entry["sequence_was_necessary"] = (entry["forward_holds"]
                                                   and not entry["reverse_holds"])
            except P.Refusal as refusal:
                entry["refused"] = refusal.code
                entry["refused_because"] = refusal.detail
            worlds.append(entry)
    finally:
        shutil.rmtree(where, ignore_errors=True)

    honest = [w for w in worlds if w.get("refused") is None]
    # -- the refusal control: a goal no sequence of these moves can reach ---------- #
    #
    # The first control was "three readable names", which is REACHABLE -- `cp` twice
    # gets there -- so the planner rightly produced a plan and the control proved
    # nothing. A control has to be a goal the moves genuinely cannot reach: keep
    # content readable while the name count falls to ZERO. That needs a move which
    # removes a name and retains its content one place over, and no measured class
    # does it: `rm` loses the content, `mv` does not lower the count.
    control: dict[str, Any]
    try:
        P.plan(P.world(names=2, readable=2),
               P.Goal(at_most={P.NAMES: 0}, at_least={P.READABLE: 1},
                      desc="no names left, yet content still readable"),
               class_moves)
        control = {"refused": False,
                   "note": "a goal outside the moves' reach was NOT refused"}
    except P.Refusal as refusal:
        control = {"refused": True, "code": refusal.code, "because": refusal.detail}

    # -- the order experiment, stated directly ------------------------------------- #
    ordering = P.why_order_matters(class_moves, P.world(names=1, readable=1))

    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_ONLY",
        "model_calls": 0,
        "network_calls": 0,
        "parameters": 0,
        "seconds": round(time.time() - started, 2),
        "the_unit": ("a move CLASS, derived from the six relations its own signature "
                     "moved; the plan is over relation dimensions, never over filenames"),
        "doors_measured": len(rows),
        "copies_do_they_exist": {
            "cp_rows": sum(1 for r in rows if r["tool"] == "cp"),
            "mv_rows": sum(1 for r in rows if r["tool"] == "mv"),
            "note": ("round 4 seeded only in.txt/in.gz, so cp and mv aborted on their "
                     "own bound operand and produced zero rows; this receipt seeds "
                     "in.json and they appear"),
        },
        "distinct_classes": classes,
        "class_moves": [m.as_dict() for m in class_moves],
        "goal": goal_for(len(VARIANTS[0][1])).as_dict(),
        "worlds": worlds,
        "all_forward_hold": all(w.get("forward_holds") for w in honest) if honest else False,
        "no_world_had_a_single_door": all(w["no_single_door"] for w in worlds),
        "sequence_necessary_in_every_world": (all(w.get("sequence_was_necessary")
                                                  for w in honest) if honest else False),
        "refusal_control": control,
        "order_experiment": ordering,
        "the_round_4_measurement_defect": _round4_defect(),
        "what_was_wrong_first": _wrong_first(),
        "honest_limits": _limits(rows, classes, class_moves),
    }


def _tool_of(move_id: str, rows: Sequence[dict[str, Any]]) -> str:
    for row in rows:
        if row["id"] == move_id:
            return row["tool"]
    return ""


def _round4_defect() -> dict[str, Any]:
    """What round 4 actually measured, re-run rather than quoted.

    Round 4's receipt reports "54 census rows = 4 programs". Seeding the way it seeded
    and counting rows by tool says otherwise, so the discrepancy is measured here
    instead of being inherited: the census binds `cp`/`mv` to `in.json`, round 4 seeded
    no such file, the doors aborted on a missing operand, and an aborted door produces
    no row. Two of the four programs contributed nothing.
    """
    out: dict[str, Any] = {"claimed_programs": 4}
    try:
        from canonical.tools import the_goal_picks_the_door_v1 as OLD
        rows = OLD.census_rows()
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["tool"]] = counts.get(row["tool"], 0) + 1
        out["round_4_seed_rows_by_tool"] = counts
        out["round_4_distinct_programs_with_rows"] = len(counts)
        out["verdict"] = ("cp and mv produced zero rows, so the round-4 join was measured "
                          "on two programs while reporting four")
    except Exception as exc:  # pragma: no cover - the old harness must stay runnable
        out["verdict"] = f"could not re-run the round-4 harness: {exc}"
    return out


def _wrong_first() -> list[str]:
    """The designs this round tried and the measurement that killed each one.

    Kept in the artifact because a defect that is only in a chat log gets made again.
    """
    return [
        "an add-only plan: `capability_planner` returned ['gzip','cp'] for a goal needing "
        "both, and running it failed because gzip consumed the file cp needed -- the plan "
        "was IMPOSSIBLE, not merely suboptimal, because the planner has no delete list",
        "the moved() subset as input: it drops `LOT: RETAINED` as 'unchanged', which "
        "deleted the precondition, so a rename was applicable to an empty world",
        "CARD alone as the state: `cp` and `touch` both raise the count by one and only "
        "one leaves a readable second name",
        "a delete subtracting BOTH READABLE and CONTENTS for one loss: `cp; rm` then "
        "reported zero readable names while the content sat readable in the copy",
        "a goal of {REMOVED>=1, READABLE>=1}: `rm` met it outright in a world holding a "
        "duplicate content, so no sequence was needed and the experiment proved nothing",
        "a goal of {REMOVED>=1, READABLE>=1, NAMES>=3}: still met by `rm` in a world "
        "already holding four names -- the same escape one world over",
        "two doors executed as recorded against DIFFERENT files: the census binds `cp` to "
        "in.json and `rm` to in.txt, so the sequence copied one file and deleted another "
        "and the content looked lost",
        "`len(after) < len(before)` as the removal test: a copy adds a name and a delete "
        "removes one, so a net count of zero hid a real removal",
        "a refusal control of 'three readable names', which is reachable by cp twice -- "
        "the planner rightly planned it and the control proved nothing",
    ]


def _limits(rows, classes, class_moves) -> list[str]:
    out = []
    if classes["classes"] <= 1:
        out.append("only one class of move was measured, so no sequence can be told apart")
    tools = sorted({r["tool"] for r in rows})
    out.append(f"the classes come from {len(tools)} programs ({', '.join(tools)}); a "
               f"move class no program here implements cannot be planned with, and the "
               f"planner refuses rather than inventing it")
    out.append("CONTENTS and READABLE are clamped by NAMES, so a world where a name "
               "outlives its content must be stated with `world(readable=...)`; the "
               "planner will not discover that state by itself")
    out.append("an operation that raises CARD while writing nothing readable (`touch`) "
               "shares the copy's signature, so it is mis-modelled as a copy -- no "
               "signature over these six relations separates them")
    out.append("the plan is shortest in MOVE COUNT, not in cost; no wall-clock or "
               "money model is applied to a step")
    return out


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    receipt = measure()
    text = json.dumps(receipt, indent=1, sort_keys=True)
    if "--receipt" in argv:
        path = pathlib.Path(argv[argv.index("--receipt") + 1])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n")
        print(f"wrote {path}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
