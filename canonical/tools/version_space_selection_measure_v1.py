#!/usr/bin/env python3
"""Measure version-space selection on the scored HumanEvalFix bugs.

The question this answers, and only this question:

    the closed loop already returns a repair that passes the tests.
    When that repair is not the published fix, can a LABELLED question
    settle it -- and how many questions does it take?

The candidate set is produced exactly as `closed_loop_trace_abduction_measure_v1`
produces it (dev + QuixBugs lessons only; a scored bug's own fix is never among
its lessons). Nothing here uses the published fix except as the ORACLE whose
answers are queried -- which is the honest model of "show it once": the
demonstration IS an oracle answer. The count of oracle calls is therefore the
price of the guarantee, and is reported per bug.

Zero model calls. Authority: NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import closed_loop_trace_abduction_repair_v1 as cl  # noqa: E402
from canonical.swe_kernel import repair_version_space_selection_v1 as vspace  # noqa: E402
from canonical.tools import closed_loop_trace_abduction_measure_v1 as clm  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402

SCHEMA = "BRAIN_VERSION_SPACE_SELECTION_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
def _probe_path() -> pathlib.Path:
    """The probe lives in a scratch directory, never in the tree: a measurement
    must not write into the repository it is measuring."""
    directory = pathlib.Path(tempfile.mkdtemp(prefix="vspace_probe_src_"))
    path = directory / "probe.py"
    path.write_text(_PROBE_SOURCE, encoding="utf-8")
    return path

_PROBE_SOURCE = '''#!/usr/bin/env python3
"""Print a behaviour matrix: programs x inputs -> outcome keys.

A fresh, isolated interpreter; one wall-clock limit per call; one marked JSON
line so a caller can never mistake partial output for an answer.
"""
import copy, json, signal, sys

spec = json.load(open(sys.argv[1]))


class Late(BaseException):
    pass


def _late(*_):
    raise Late()


signal.signal(signal.SIGALRM, _late)


def load(text, entry):
    space = {"__name__": "__program__"}
    exec(compile(spec["prelude"], "<prelude>", "exec"), space)
    exec(compile(text, "<program>", "exec"), space)
    return space[entry]


def outcome(fn, args, limit):
    signal.setitimer(signal.ITIMER_REAL, limit)
    try:
        return ["value", repr(fn(*copy.deepcopy(args)))[:160]]
    except Late:
        return ["late"]
    except BaseException as exc:  # noqa: BLE001
        return ["raised", type(exc).__name__]
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


rows = []
for program in spec["programs"]:
    try:
        fn = load(program, spec["entry"])
    except BaseException as exc:  # noqa: BLE001
        rows.append({"load_error": f"{type(exc).__name__}: {exc}"[:200], "outcomes": []})
        continue
    rows.append({"load_error": None,
                 "outcomes": [outcome(fn, args, spec["limit"]) for args in spec["inputs"]]})
print("@@" + json.dumps({"rows": rows}))
'''


def probe_inputs(bug: dict[str, Any], cap: int = 120) -> list[list[Any]]:
    """The FREE library: inputs only, never labels.

    Test arguments, their boundary perturbations, and anything the caller adds.
    Building this uses the tests' *inputs*; no expected value is read.
    """
    fn = cl.load_function(hef.ast.unparse(hef.ast.parse(bug["buggy"])), bug["entry"], hef.PRELUDE)
    cases = cl.extract_assert_cases(bug["test"], bug["entry"], fn)
    outs: list[list[Any]] = []
    for case in cases:
        if not case.args:
            continue
        outs.append(list(case.args))
        for perturbed in cl._perturbations(case.args):
            outs.append(list(perturbed))

    # `assert correct_bracketing("()")` carries an input but no expected value, so
    # `extract_assert_cases` (which recovers args from `== expected`) reports none.
    # The arguments are still free information: read them off the call itself.
    entry = bug["entry"]
    try:
        test_tree = hef.ast.parse(bug["test"])
    except (SyntaxError, ValueError):
        test_tree = None
    if test_tree is not None:
        for node in hef.ast.walk(test_tree):
            if not isinstance(node, hef.ast.Assert):
                continue
            for call in [n for n in hef.ast.walk(node.test) if isinstance(n, hef.ast.Call)]:
                name = getattr(call.func, "id", None) or getattr(call.func, "attr", None)
                if name != entry:
                    continue
                try:
                    args = tuple(hef.ast.literal_eval(a) for a in call.args)
                except (ValueError, SyntaxError):
                    continue
                outs.append(list(args))
                for perturbed in cl._perturbations(args):
                    outs.append(list(perturbed))
    uniq: list[list[Any]] = []
    seen: set[str] = set()
    for args in outs:
        key = json.dumps(args, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            uniq.append(args)
    return uniq[:cap]


def behaviour_matrix(programs: Sequence[str], entry: str, inputs: Sequence[Sequence[Any]],
                     *, limit_s: float = 1.0) -> list[list[Any]] | None:
    with tempfile.TemporaryDirectory(prefix="vspace_probe_") as scratch:
        spec = pathlib.Path(scratch) / "spec.json"
        spec.write_text(json.dumps({"prelude": hef.PRELUDE, "entry": entry,
                                    "programs": list(programs),
                                    "inputs": [list(a) for a in inputs],
                                    "limit": limit_s}))
        try:
            done = subprocess.run([sys.executable, "-I", "-B", str(_probe_path()), str(spec)],
                                  cwd=scratch, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True,
                                  timeout=60 + limit_s * len(inputs) * max(1, len(programs)) / 4)
        except subprocess.TimeoutExpired:
            return None
    marked = [line for line in done.stdout.splitlines() if line.startswith("@@")]
    if done.returncode != 0 or not marked:
        return None
    return json.loads(marked[-1][2:])["rows"]


def one_bug(bug: dict[str, Any], lessons: Any, extra: dict[int, dict[str, Any]],
            where: pathlib.Path, *, budget: int) -> dict[str, Any]:
    started = time.monotonic()
    hef.lay_out(bug, where)
    proposals = cl.proposals_for(bug["buggy"], bug["entry"], bug["test"], lessons,
                                 prelude=hef.PRELUDE, budget=budget)
    sources = [p["source"] for p in proposals][:budget]
    published = hef.ast.unparse(hef.ast.parse(bug["fixed"]))

    from canonical.swe_kernel.zygote_worker_pool_v1 import screen_python_candidates_cow
    answer = screen_python_candidates_cow(str(where), hef.PROGRAM, [hef.TESTS],
                                         [hef.PRELUDE + s for s in sources],
                                         stop_on_first_pass=False,
                                         timeout_s=len(sources) * hef.SCREEN_LIMIT_S + 20.0,
                                         per_candidate_timeout_s=hef.SCREEN_LIMIT_S)
    out: dict[str, Any] = {"bug_type": bug["bug_type"], "budget": budget,
                           "candidates": len(sources)}
    if not (answer.get("ok") and answer.get("screen_authoritative")):
        out["status"] = "SCREEN_NOT_AUTHORITATIVE"
        return out
    passing = sorted(int(i) for i in answer.get("passing_indices") or [])
    out["passing"] = len(passing)
    if not passing:
        out["status"] = "NO_CANDIDATE_PASSES_THE_TESTS"
        out["seconds"] = round(time.monotonic() - started, 2)
        return out

    inputs = probe_inputs(bug)
    ids = [f"c{i}" for i in passing]
    programs = [sources[i] for i in passing]
    rows = behaviour_matrix(programs + [published], bug["entry"], inputs,
                            limit_s=1.0 if len(programs) < 8 else 0.5)
    if rows is None:
        out["status"] = "PROBE_FAILED"
        return out
    rows = rows[:len(programs)] + [rows[-1]]  # keep the reference row aligned
    vectors = {}
    broken = []
    for cid, row in zip(ids, rows[:-1]):
        if row.get("load_error"):
            broken.append(cid)
            continue
        vectors[cid] = [tuple(o) for o in row["outcomes"]]
        vectors[cid] = [tuple(map(str, v)) for v in vectors[cid]]
    if broken:
        out["did_not_load"] = broken[:5]
    part = vspace.partition(list(vectors), vectors)
    out["partition"] = {"status": part.get("status"), "distinct": part.get("distinct"),
                        "classes": len(part.get("classes") or []),
                        "largest": max((len(c) for c in part.get("classes") or []), default=0)}
    out["diagnosis"] = vspace.diagnose(part).get("verdict")

    # the shipped repair: what the closed loop returns when it stops at the first pass
    shipped = ids[0]
    ref_vector = [tuple(map(str, o)) for o in rows[-1]["outcomes"]]
    published_in_set = published in programs
    out["shipped_is_published_fix"] = published_in_set and programs[0] == published
    out["shipped_behaviour_equals_reference"] = tuple(vectors.get(shipped) or ()) == tuple(ref_vector)
    out["reference_behaviour_is_in_the_candidate_set"] = tuple(ref_vector) in set(
        tuple(v) for v in vectors.values())

    if part.get("status") != "OK":
        out["status"] = "PARTITION_REFUSED"
        out["seconds"] = round(time.monotonic() - started, 2)
        return out

    # the oracle answers ONE question at a time; each answer costs one call
    def oracle(_probe_index: int) -> tuple:
        return tuple(rows[-1]["outcomes"][_probe_index])

    # The published fix may itself be among the candidates. It is KEPT: the scoring
    # rule is behavioural (does the chosen candidate's outcome vector equal the
    # reference's on the whole probe library?), never textual, so a candidate that
    # happens to be the published text is judged the same way as any other -- and if
    # it is settled on, that is a correct settlement, not a shortcut. Dropping it was
    # tried and measured worse: Python/163 lost its only correct candidate.
    out["published_fix_was_also_a_candidate"] = published_in_set
    selection = vspace.ask_until_settled(
        {cid: programs[ids.index(cid)] for cid in ids},
        list(range(len(inputs))),
        lambda source, probe: vectors[ids[programs.index(source)]][probe],
        oracle, max_questions=3)
    out["decision"] = selection.decision
    out["disposition"] = selection.disposition
    out["chosen_class_size"] = selection.class_size
    out["questions_asked"] = selection.rounds
    out["refused_because"] = selection.refused_because
    if selection.decision == "ACCEPT" and selection.accepted:
        chosen = programs[ids.index(selection.accepted)]
        out["chosen_is_published_fix"] = chosen == published
        out["chosen_behaviour_equals_reference"] = (
            tuple(vectors[selection.accepted]) == tuple(ref_vector))
        # the chosen behaviour is checked against the published fix on inputs the
        # tests never reach -- out of sample, not the probe library
        agreement = hef.agreement(bug, chosen, extra.get(bug["number"]))
        out["on_inputs_the_tests_do_not_have"] = agreement
    out["status"] = "MEASURED"
    out["seconds"] = round(time.monotonic() - started, 2)
    return out


def summarise(per_bug: dict[str, Any]) -> dict[str, Any]:
    rows = [r for r in per_bug.values() if r.get("status") == "MEASURED"]
    decisions: dict[str, int] = {}
    for r in rows:
        decisions[r["decision"]] = decisions.get(r["decision"], 0) + 1
    dispositions: dict[str, int] = {}
    for r in rows:
        dispositions[r.get("disposition", "")] = dispositions.get(r.get("disposition", ""), 0) + 1
    accepted = [r for r in rows if r["decision"] == "ACCEPT"]
    return {
        "bugs_asked": len(per_bug),
        "bugs_measured": len(rows),
        "status_counts": {s: sum(1 for r in per_bug.values() if r.get("status") == s)
                          for s in sorted({r.get("status") for r in per_bug.values()})},
        "decision_counts": dict(sorted(decisions.items())),
        "disposition_counts": dict(sorted(dispositions.items())),
        "candidates_passing_tests": sum(r.get("passing", 0) for r in rows),
        "shipped_equals_reference_behaviour": sum(
            1 for r in rows if r.get("shipped_behaviour_equals_reference")),
        "reference_behaviour_was_in_the_candidate_set": sum(
            1 for r in rows if r.get("reference_behaviour_is_in_the_candidate_set")),
        "accepted": len(accepted),
        "accepted_and_is_the_published_fix": sum(
            1 for r in accepted if r.get("chosen_is_published_fix")),
        "accepted_and_equal_to_the_reference_behaviour": sum(
            1 for r in accepted if r.get("chosen_behaviour_equals_reference")),
        "SETTLED_by_a_question": sum(
            1 for r in rows if r.get("disposition") == "SETTLED_BY_QUESTION"),
        "SETTLED_and_equal_to_the_reference_behaviour": sum(
            1 for r in rows if r.get("disposition") == "SETTLED_BY_QUESTION"
            and r.get("chosen_behaviour_equals_reference")),
        "SETTLED_TO_A_CLASS_by_a_question": sum(
            1 for r in rows if r.get("disposition") == "SETTLED_TO_A_BEHAVIOUR_CLASS"),
        "SETTLED_TO_A_CLASS_and_equal_to_the_reference_behaviour": sum(
            1 for r in rows if r.get("disposition") == "SETTLED_TO_A_BEHAVIOUR_CLASS"
            and r.get("chosen_behaviour_equals_reference")),
        "ANY_SETTLEMENT_by_a_question": sum(
            1 for r in rows if r.get("disposition", "").startswith("SETTLED")),
        "ANY_SETTLEMENT_and_equal_to_the_reference_behaviour": sum(
            1 for r in rows if r.get("disposition", "").startswith("SETTLED")
            and r.get("chosen_behaviour_equals_reference")),
        "UNSEPARATED": sum(1 for r in rows if r.get("disposition", "").startswith("UNSEPARATED")),
        "UNSEPARATED_and_equal_to_the_reference_behaviour": sum(
            1 for r in rows if r.get("disposition", "").startswith("UNSEPARATED")
            and r.get("chosen_behaviour_equals_reference")),
        "questions_asked_total": sum(r.get("questions_asked", 0) for r in rows),
        "questions_asked_median": sorted(r.get("questions_asked", 0) for r in rows)[
            len(rows) // 2] if rows else 0,
        "refused": sum(1 for r in rows if r["decision"] == "REFUSE"),
        "refusal_reasons": {k: sum(1 for r in rows if r.get("refused_because") == k)
                            for k in sorted({r.get("refused_because") for r in rows
                                             if r["decision"] == "REFUSE"})},
        "seconds": round(sum(r.get("seconds", 0) for r in per_bug.values()), 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path)
    parser.add_argument("--quixbugs-dir", required=True, type=pathlib.Path)
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--which", choices=("development", "scored"), default="scored")
    parser.add_argument("--bugs", nargs="*", default=None)
    parser.add_argument("--shard", default="0/1")
    parser.add_argument("--budget", type=int, default=200)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    bugs = hef.load_bugs(args.humanevalfix)
    development, scored = hef.split(bugs)
    chosen_names = development if args.which == "development" else scored
    index, of = (int(x) for x in args.shard.split("/"))
    names = [n for i, n in enumerate(chosen_names) if i % of == index]
    if args.bugs:
        wanted = set(args.bugs)
        names = [n for n in names if n in wanted] or [n for n in args.bugs]
    lessons = clm.taught_lessons(bugs, development, hef.quixbugs_lessons(args.quixbugs_dir))
    extra = hef.extra_inputs(args.extra_inputs)
    by_name = {b["name"]: b for b in bugs}
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "model_calls": 0,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "which": args.which, "shard": args.shard, "budget": args.budget,
        "names": names,
        "split": {"seed": hef.SPLIT_SEED, "scored": len(scored),
                  "development": len(development)},
        "benchmark": {"humanevalfix_sha256":
                      hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(),
                      "bugs": len(bugs)},
        "code_sha256": {
            "canonical/swe_kernel/repair_version_space_selection_v1.py":
                hashlib.sha256((ROOT / "canonical/swe_kernel/repair_version_space_selection_v1.py").read_bytes()).hexdigest(),
            "canonical/tools/version_space_selection_measure_v1.py":
                hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
            "canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py":
                hashlib.sha256((ROOT / "canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py").read_bytes()).hexdigest(),
        },
        "lessons": {"given": len(lessons.lessons), "operators": len(lessons.operators)},
    }
    per_bug: dict[str, Any] = {}
    for name in names:
        bug = by_name[name]
        where = args.work_dir / name.replace("/", "_")
        try:
            per_bug[name] = one_bug(bug, lessons, extra, where, budget=args.budget)
        except Exception as exc:  # noqa: BLE001 -- a crash is a result, not a stop
            per_bug[name] = {"status": "CRASHED", "error": f"{type(exc).__name__}: {exc}"[:300]}
        import shutil
        shutil.rmtree(where, ignore_errors=True)
        row = per_bug[name]
        print(f"{name:11s} {row.get('bug_type', ''):16s} {row.get('status'):28s} "
              f"passing={row.get('passing')} decision={row.get('decision')} "
              f"questions={row.get('questions_asked')}", flush=True)
        record["per_bug"] = dict(per_bug)
        args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    record["summary"] = summarise(per_bug)
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps(record["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
