"""Generate the input that reaches the changed line, then assert what it does there.

THE GAP THIS CLOSES
-------------------
Round 16 measured that the missing assertion cannot be recovered from the tests: 0 of 8 unpinned behavioural
parts of real fixes were pinnable, because a suite that passes contains, by construction, no input that
reaches the parts it does not observe. The missing thing is therefore an INPUT, not an assertion.

The 2026 field solved exactly this problem for vulnerability reproduction, under a name this tree did not use:
**directed greybox fuzzing**. WAFLGO (USENIX'24) directs input generation at the *change sites* of a commit;
AFLGo and ColorGo score seeds by distance to a target site; Driller/QSYM pair mutation with concolic solving
when mutation stalls. Its conclusion is the one that matters here: undirected iteration is hopeless, distance
to the target is what makes the search converge.

WHAT THIS DOES, AND WHAT IT REFUSES TO DO
-----------------------------------------
    seeds       the literal calls the human's own test makes (never invented arguments)
    mutations   byte insert/delete/replace, line duplication, seed splicing, literal splicing
    feedback    the set of lines the target file executed -- one traced child per batch, then distance
    target      the changed line of the reverted part (round 15's part boundaries)
    stopping    the target line executed; then compare the outcome under fix and mutant
    assertion   only if the outcome differs, and only if it is green on the fix and red on the mutant

No model, no network, no solver. Splicing is the operator that matters for real formats: two valid documents
concatenated produce the duplicate-key class of error that no single seed reaches.

WHAT IS DELIBERATELY NOT CLAIMED
--------------------------------
This is a search, so it can fail. A part it never reaches is reported `NOT_REACHED` with the executions spent,
and the closest distance achieved -- never as an absence of behaviour. And a reached part whose outcome does
not differ between fix and mutant is reported `REACHED_NO_DIFFERENCE`, because reaching a line is not the same
as observing its effect.
"""

from __future__ import annotations

import json
import pathlib
import random
import re
import sys
import tempfile
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

SCHEMA = "BRAIN_REACH_THE_CHANGED_SITE_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
BUDGET = 120
BATCH = 40
MAX_PARTS = 3
SEED = 20261116

PINNED = "PINNED__THE_INPUT_WAS_GENERATED_AND_THE_ASSERTION_VERIFIED"
REACHED_NO_DIFF = "REACHED_NO_DIFFERENCE"
NOT_REACHED = "NOT_REACHED"
REFUSED_CONTROL = "REFUSED__CONTROL_BROKEN"
REFUSED_NO_SEED = "REFUSED__NO_SEED"
REFUSED_REMOVAL = "REFUSED__PART_REMOVES_CODE"
REFUSED_NO_SEARCHABLE = "REFUSED__NO_SEARCHABLE_PART"

_BATCHER = r'''
import importlib, json, os, re, sys

ADDRESS = re.compile(r"0x[0-9a-fA-F]{6,}")
REQUEST = json.loads(os.environ["REACH_REQUEST"])
TARGET = os.path.realpath(REQUEST["target_file"])
TARGET_LINE = int(REQUEST["target_line"])

module_cache = {}
results = []
for item in REQUEST["cases"]:
    module = module_cache.setdefault(item["module"], importlib.import_module(item["module"]))
    target = getattr(module, item["function"], None)
    if target is None or not callable(target):
        results.append({"outcome": "MISSING", "lines": []})
        continue
    seen = set()
    def local(frame, event, arg, _seen=seen):
        if event == "line" and os.path.realpath(frame.f_code.co_filename) == TARGET:
            _seen.add(frame.f_lineno)
        return local
    sys.settrace(local)
    try:
        value = target(*item["args"])
        outcome = "RETURNED:" + ADDRESS.sub("0xADDR", repr(value))[:160]
    except BaseException as exc:
        outcome = "RAISED:%s:%s" % (type(exc).__name__, ADDRESS.sub("0xADDR", str(exc))[:160])
    finally:
        sys.settrace(None)
    results.append({"outcome": outcome, "lines": sorted(seen)})
print(json.dumps(results))
'''


def _batch(tree: pathlib.Path, target_file: str, target_line: int,
           cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not cases:
        return []
    script = pathlib.Path(tempfile.mkdtemp(prefix="reach-")) / "batch.py"
    script.write_text(_BATCHER, encoding="utf-8")
    env = G._env_for(tree)
    env["REACH_REQUEST"] = json.dumps({"target_file": target_file, "target_line": target_line,
                                       "cases": [dict(case) for case in cases]})
    try:
        import subprocess
        done = subprocess.run([sys.executable, str(script)], cwd=str(tree), env=env,
                              capture_output=True, text=True, timeout=300)
        return json.loads(done.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001 - a failed batch is reported, never silently scored
        return [{"outcome": "BATCH_FAILED", "lines": []} for _ in cases]


def _hints(added_source: str) -> list[int]:
    """Quantities the changed block compares against. Directed fuzzers call this the distance to the target;
    it is the only gradient available without semantics, and it is read off the artifact, not supplied."""
    numbers = sorted({int(token) for token in re.findall(r"(?<![\w.])\d+(?![\w.])", added_source)})
    return [number for number in numbers if number > 1][:4]


def _distance(text: str, hints: Sequence[int]) -> int | None:
    return min(abs(len(text) - hint) for hint in hints) if hints else None


def _mutate(seed: str, alphabet: str, rng: random.Random, hints: Sequence[int] = ()) -> str:
    """A mutation grammar, not a template: the field's rule is that splicing beats point mutation on formats."""
    choice = rng.random()
    if hints and choice < 0.30:                      # aim at the quantity the changed block compares against
        if seed.strip().lstrip("-").isdigit():
            return str(rng.choice(hints) + rng.choice((-1, 0, 1, 2)))
        target = rng.choice(hints)
        return seed * (target // max(1, len(seed)) + 2)
    if not seed:
        return rng.choice(alphabet) * 2
    position = rng.randrange(len(seed))
    if choice < 0.25:
        return seed[:position] + rng.choice(alphabet) + seed[position:]
    if choice < 0.45:
        return seed[:position] + seed[position + 1:]
    if choice < 0.65:
        return seed[:position] + rng.choice(alphabet) + seed[position + 1:]
    if choice < 0.80:
        lines = seed.splitlines(keepends=True)
        if len(lines) > 1:
            index = rng.randrange(len(lines))
            return "".join(lines[:index] + [lines[index]] + lines[index:])
        return seed + seed
    return seed + seed                              # splicing: the duplicate-key class lives here


def _alphabet(test_source: str, module_source: str) -> str:
    """Characters the artifact and its tests actually use -- the field's 'dictionary', harvested not written."""
    used = sorted({character for character in test_source + module_source
                   if not character.isalnum() and character not in "\r\n"})
    return "".join(used[:24]) or ".:-=[]{}"


def reach_part(tree: pathlib.Path, source_rel: str, test_rel: str, fixed: str, mutant: str,
               part: Mapping[str, Any], calls: Sequence[Mapping[str, Any]],
               budget: int = BUDGET) -> dict[str, Any]:
    """Directed search for an input that executes the changed line, then an assertion if it observes it."""
    if not str(part.get("added") or "").strip():
        # A deletion adds no line, so there is no line to reach: the deleted statement exists only in the
        # mutant. Searching the mutant is a different measurement; refuse rather than report a search failure.
        return {"state": REFUSED_REMOVAL, "executions": 0}
    target = tree / source_rel
    original = target.read_bytes()
    # Aim at the BODY of the added block, never its header: an `if` header executes on every call, so
    # reaching it proves nothing. The last added line is the deepest statement the condition guards.
    target_line = part["new"][1] if part["new"][1] > part["new"][0] else max(1, part["new"][0])
    target_file = str(tree / source_rel)
    seeds = [call for call in calls if call["args"] and isinstance(call["args"][0], str)]
    if not seeds:
        return {"state": REFUSED_NO_SEED, "executions": 0}
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace")
    added = "\n".join(fixed.splitlines()[part["new"][0]:part["new"][1]])
    hints = _hints(added)
    alphabet = _alphabet(test_source, mutant)          # pre-fix vocabulary only: the fix is the answer
    rng = random.Random(SEED)
    corpus = [dict(seed) for seed in seeds]
    shapes: set[tuple[int, ...]] = set()
    seen_inputs: set[str] = set()
    executions = 0
    best_distance = None
    reached = None
    try:
        target.write_text(fixed, encoding="utf-8")          # the FIXED state is where reaching is measured
        while executions < budget:
            cases = []
            for _ in range(min(BATCH, budget - executions)):
                base = rng.choice(corpus)
                text = _mutate(str(base["args"][0]), alphabet, rng, hints)
                if text in seen_inputs:
                    continue
                seen_inputs.add(text)
                cases.append({"module": base["module"], "function": base["function"],
                              "args": [text] + list(base["args"][1:])})
            if not cases:
                break
            results = _batch(tree, target_file, target_line, cases)
            executions += len(cases)
            for case, result in zip(cases, results):
                if result.get("outcome") in ("BATCH_FAILED", "MISSING"):
                    continue
                lines = result.get("lines") or []
                if target_line in lines:
                    reached = {"outcome": result["outcome"], "input": case["args"][0],
                               "module": case["module"], "function": case["function"]}
                    break
                if not lines:
                    continue
                shape = tuple(lines)
                distance = _distance(str(case["args"][0]), hints)
                closer = distance is not None and (best_distance is None or distance < best_distance)
                if shape in shapes and not closer:
                    continue
                shapes.add(shape)
                if closer:
                    best_distance = distance
                corpus.append({"module": case["module"], "function": case["function"], "args": case["args"]})
                corpus = corpus[-8:]
            if reached:
                break
        if not reached:
            return {"state": NOT_REACHED, "executions": executions, "best_distance": best_distance,
                    "hints": hints, "corpus": len(corpus)}
        target.write_text(mutant, encoding="utf-8")
        cold = _batch(tree, target_file, target_line, [{"module": reached["module"],
                                                        "function": reached["function"],
                                                        "args": [reached["input"]]}])
        if not cold or cold[0].get("outcome") == reached["outcome"]:
            return {"state": REACHED_NO_DIFF, "executions": executions, "best_distance": 0,
                    "outcome": reached["outcome"][:120]}
        call = {"module": reached["module"], "function": reached["function"], "args": [reached["input"]]}
        assertion = SYN._assertion(call, reached["outcome"])
        if assertion is None:
            return {"state": REACHED_NO_DIFF, "executions": executions, "best_distance": 0,
                    "outcome": reached["outcome"][:120], "note": "outcome not expressible as an assertion"}
        synth = tree / "_reach_synth_test.py"
        try:
            synth.write_text(SYN._testfile(assertion, reached["module"]), encoding="utf-8")
            target.write_text(fixed, encoding="utf-8")
            green = G.run_test(tree, synth.name)["passed"]
            target.write_text(mutant, encoding="utf-8")
            red = not G.run_test(tree, synth.name)["passed"]
        finally:
            synth.unlink(missing_ok=True)
        if green and red:
            return {"state": PINNED, "executions": executions, "best_distance": 0,
                    "input": reached["input"][:160], "assertion": assertion.strip()}
        return {"state": REACHED_NO_DIFF, "executions": executions, "best_distance": 0,
                "outcome": reached["outcome"][:120], "green": green, "red": red}
    finally:
        target.write_bytes(original)


def audit_task(task: Mapping[str, Any], grammar: Sequence[Mapping[str, Any]],
               cap: int = MAX_PARTS) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    entry = next((g for g in grammar if g["sha"] == task["sha"] and g["source"] == source_rel), None)
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    if entry is None:
        return {**row, "state": PINS.REFUSED_NO_GRAMMAR}
    fixed, defective = entry["repaired"], entry["defective"]
    if G.try_candidate(tree, source_rel, test_rel, defective)["passed"] or \
            not G.try_candidate(tree, source_rel, test_rel, fixed)["passed"]:
        return {**row, "state": REFUSED_CONTROL}
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") \
        if (tree / test_rel).is_file() else ""
    calls = SYN.calls_from_the_test(test_source)
    row["calls_from_the_test"] = len(calls)
    judged: list[dict[str, Any]] = []
    for part in PINS.hunks(defective, fixed):
        if len(judged) >= cap:
            break
        if not PINS.is_behavioural(fixed, part) or PINS.typing_only(fixed, part):
            continue
        mutant = PINS.revert(fixed, defective, part)
        if G.try_candidate(tree, source_rel, test_rel, mutant)["passed"] is False:
            continue                                  # already pinned by the suite
        verdict = reach_part(tree, source_rel, test_rel, fixed, mutant, part, calls)
        judged.append({**verdict, "part_head": part["added"][:120] or "(removal)"})
    pinned = sum(1 for item in judged if item["state"] == PINNED)
    return {**row, "parts": judged, "unpinned_parts": len(judged), "pinned_by_generation": pinned,
            "executions": sum(item.get("executions") or 0 for item in judged),
            "state": (PINNED if pinned else PINS.FULLY_PINNED if not judged else
                      REFUSED_NO_SEARCHABLE if all(str(item["state"]).startswith("REFUSED") for item in judged)
                      else NOT_REACHED)}


def measure(tasks: Sequence[Mapping[str, Any]], grammar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [audit_task(task, grammar) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    parts = [item for row in rows for item in (row.get("parts") or [])]
    pinned = sum(1 for item in parts if item["state"] == PINNED)
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {
            "tasks": len(rows), "states": states, "parts_audited": len(parts), "pinned_by_generation": pinned,
            "reached": sum(1 for item in parts if item["state"] in (PINNED, REACHED_NO_DIFF)),
            "not_reached": sum(1 for item in parts if item["state"] == NOT_REACHED),
            "executions": sum(item.get("executions") or 0 for item in parts),
            "certified_share_before": 0.714, "certified_share_after":
                round((30 + pinned) / 42, 3) if parts else None,
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [row for row in report["rows"] if row.get("pinned_by_generation")]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]}: "
                       + " | ".join(item["assertion"].replace("\n", " ") for item in row["parts"]
                                    if item["state"] == PINNED) for row in won)
    return (f"{totals['tasks']} real fixes: {totals['parts_audited']} parts the suite accepts without, "
            f"{totals['reached']} reached by generated input, {totals['pinned_by_generation']} pinned and verified "
            f"in {totals['executions']} executions. Certified share {totals['certified_share_before']} -> "
            f"{totals['certified_share_after']}. States: "
            + ", ".join(f"{state} {count}" for state, count in sorted(totals["states"].items()))
            + (f". {detail}" if detail else "") + ".")


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args(argv)
    tasks = SHAPE.prepare_corpus(args.manifest, args.hist, args.work, limit=args.limit)
    grammar = json.loads(args.manifest.read_text(encoding="utf-8"))["grammar"]
    report = measure(tasks, grammar)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
