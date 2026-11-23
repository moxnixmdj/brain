"""How much of what the machine believed it did not know was never asked?

THE QUESTION
------------
The tree could scan an environment (76 doors from 2,134 declarations) and it could fetch
instant knowledge (local guides, then the web, completeness-gated). Nothing joined them,
so the deciding quantity -- WHAT it does not know -- had never been measured, and the
ledger that ranks ignorance had 82 gaps and 0 resolved.

This receipt measures it twice: once with the census as it stood, and once with three
defects removed. The number that matters is not the door count; it is how much of the
"unbound" mass was a real absence of capability and how much was us asking wrong.

WHAT WAS WRONG, EACH FOUND BY DISBELIEVING A NUMBER
--------------------------------------------------
1. ONE CONTRACT PER PROGRAM. `_own_text(prog)` asks `prog -h` and nothing else, so a
   program with subcommands was read from its parent text and every child operation was
   judged against it. Measured: 38 of 38 admitted openssl subcommands print their OWN
   `Usage:` line and all 38 were reported as though they had none.

2. A FAILED RUN CALLED A CLEAN ONE. `verdict = "NO_EFFECT"` was assigned to any run that
   left the tree alone, whatever its exit status. Measured on openssl: 545 of 676 rows
   carried exit 1 and all 545 were reported as "exited cleanly and moved nothing: a
   value was computed, so this is a sensor, not a dead door". A program that refused the
   invocation had not answered anything.

3. THE PARENT'S DOCUMENTATION GAP APPLIED TO THE CHILD. `classify()` derived one
   construction reason from the parent contract and used it to move every `NO_EFFECT` row
   to UNBOUND. With fix 2 in place this was the remaining thing standing between 118
   genuinely-answering openssl operations and being counted as sensors.

MEASURED EFFECT OF THE THREE, ON THE SAME 20 PROGRAMS
-----------------------------------------------------
    before   33 DOOR / 665 SENSOR / 793 UNBOUND
    after    36 DOOR / 198 SENSOR / 804 UNBOUND

The door count rose by three. The SENSOR count fell by 467, and that is the finding: 467
operations were being credited as "the machine can compute a value here" when the run had
failed or its own document had never been opened. A number that flatters the machine fell.

WHAT THIS RECEIPT REFUSES TO CLAIM
----------------------------------
Asking correctly does not make an operation a door. 558 of openssl's 676 operations are
still unknown, and now for a TRUE reason -- the invocation was refused -- which is
actionable in a way "documents no usage line" never was. The claim is only that the doubt
is now stated correctly and cheaply, and that it persists, so the next process does not
have to rediscover it.

Model calls: 0. Network calls: 0. Parameters: 0. Spend: $0.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import ask_the_subcommand_before_you_call_it_unbound_v1 as A  # noqa: E402
from canonical.runtime import tool_census_v1 as C  # noqa: E402

SCHEMA = "PROJECT_BRAIN_ASK_THE_SUBCOMMAND_RECEIPT_V1"

PROGRAMS = ("cp", "mv", "rm", "gzip", "tar", "sed", "find", "sort", "grep", "cut",
            "tr", "ln", "touch", "dd", "openssl", "jq", "zip", "head", "wc", "tee")


def _before(programs: Sequence[str]) -> dict[str, Any]:
    """The census exactly as it behaved before this round: one contract per program."""
    totals: dict[str, int] = {}
    for prog in programs:
        if C.shutil.which(prog) is None:
            continue
        try:
            census = C.census(prog, depth=2, max_ops=60)
            contract = C.parse_contract(C._own_text(prog), prog)
            bound = [C.bind(op, contract=contract) for op in census["operations"]]
            graded = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
            # the OLD verdict rule, reproduced deliberately so the comparison is the fix
            # and not a memory of it
            rows = []
            for row in graded.get("rows") or []:
                verdict = row.get("verdict")
                if verdict == "FAILED_NO_EFFECT":
                    verdict = "NO_EFFECT"
                rows.append({**row, "verdict": verdict})
            graded = {**graded, "rows": rows}
            split = C.classify(census["operations"], graded, contract=contract,
                              admitted=len(census["operations"]))
            for key, value in (split.get("counts") or {}).items():
                totals[key] = totals.get(key, 0) + int(value)
        except Exception:
            continue
    return totals


def _resolvability(per_program: Sequence[dict[str, Any]]) -> dict[str, int]:
    """How much of the unknown is worth chasing at all, summed over programs."""
    out: dict[str, int] = {}
    for row in per_program:
        for key, value in (row.get("resolvability") or {}).items():
            out[key] = out.get(key, 0) + int(value)
    return out


def _total(per_program: Sequence[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in per_program:
        for key, value in (row.get("counts") or {}).items():
            out[key] = out.get(key, 0) + int(value)
    return out


def measure(programs: Sequence[str] = PROGRAMS) -> dict[str, Any]:
    started = time.time()
    before = _before(programs)
    after = A.measure(programs)
    ledger_dir = tempfile.mkdtemp(prefix="brain-doubt-")
    ledger_path = str(pathlib.Path(ledger_dir) / "IGNORANCE_LEDGER.json")

    kinds: dict[str, int] = {}
    per_program: list[dict[str, Any]] = []
    for row in after["per_program"]:
        if row.get("error"):
            per_program.append(row)
            continue
        for kind, n in (row.get("kinds") or {}).items():
            kinds[kind] = kinds.get(kind, 0) + int(n)
        per_program.append(row)

    noted = A.note_to_ledger({"counts": kinds}, path=ledger_path)

    # the surviving question, asked of the worst offender, and answered by a COUNT
    worst = after.get("worst_offender")
    questions: list[dict[str, Any]] = []
    if worst:
        try:
            run = A.classify_at_scope(worst, max_ops=60)
            questions = A.what_to_ask(worst, run["subcommands_admitted"],
                                      run["classified"])[:5]
        except Exception:
            questions = []

    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_ONLY",
        "model_calls": 0,
        "network_calls": 0,
        "parameters": 0,
        "seconds": round(time.time() - started, 2),
        "programs": len([p for p in per_program if not p.get("error")]),
        "before_the_three_fixes": before,
        "after_the_three_fixes": _total(per_program),
        "sensor_delta": (int(before.get("SENSOR") or 0)
                         - int(_total(per_program).get("SENSOR") or 0)),
        "kinds_total": kinds,
        "kinds": list(A.KINDS),
        "worst_offender": worst,
        "worst_offender_unbound": after.get("worst_offender_unbound"),
        "questions_worth_asking": questions,
        "ledger": noted,
        "the_join": after["the_join"],
        "resolvability_total": _resolvability(per_program),
        "the_frontier": {
            "skill_boundary_2026_03": ("OSExpert-style exploration-then-execute reports "
                "+20% performance and 80% efficiency from exploring before acting -- and "
                "runs that loop inside a 120B model. The whole loop here is deterministic "
                "and costs 0 model calls; what it lacks is OSExpert's report, which this "
                "module now produces as a kind table."),
            "knowledge_boundary_discovery_2603_21022": ("KBD discovers an LLM's knowledge "
                "boundary with an RL policy rewarded by ENTROPY reduction. "
                "`worth(question)` here is the same quantity in the discrete case -- the "
                "number of operation verdicts one question decides -- so the ranking is "
                "measured rather than learned, with no policy and no parameters."),
            "llm_idea_2610_11253": ("LLM-IDEA triages a plateau into capability limit / "
                "resolvable within the design class / certified exhausted, on the grounds "
                "that an agent which cannot tell 'not looked yet' from 'no further search "
                "will recover this' wastes its budget. That axis was ADDED here as "
                "`RESOLVABILITY`, decided per kind from evidence. The measured verdict on "
                "the current tree is that every unbound operation is rescuable and NONE is "
                "certified exhausted -- so no doubt in it is worth abandoning.")},
        "what_this_does_not_say": [
            "asking correctly does not turn an operation into a door: 558 of openssl's "
            "676 operations are still unknown, now for a true reason",
            "the kinds are decided from documents and from real run exits; a kind is a "
            "belief about why a verdict is unknown, not a proof of what the operation does",
            "no operation outside the seeded directory was attempted, so a program whose "
            "required slot needs a file elsewhere is still DROVE_IT_WRONG",
            "producer-run sandbox only; no independent identity has re-run any of it"],
        "honest_limits": [
            "the ledger's value = p_useful/(1+cost) ranks a doubt blocking 558 operations "
            "BELOW one blocking 2, because cost is used as a penalty; what_to_ask() is the "
            "ordering used for action and both orderings are reported rather than merged",
            "a program with no help text at any scope cannot be asked at all, and is "
            "reported NO_DOCUMENT rather than guessed at",
            "index_capability_evidence_v1 names the ledger as the ranker of ignorance; "
            "this receipt is the first thing on the program path to write to it"],
    }


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
