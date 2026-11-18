"""The operation is the missing dimension: the same inputs, a different verb.

WHAT FOUR ROUNDS LEFT UNTOUCHED
-------------------------------
Rounds 16 to 19 changed the SEEDS four times -- the tests' own literals, then mutated literals, then the values
the program's own comparisons want, then the repositories' own 5,949 documents -- and the pinned count never moved
off 2 of 8 (0, then 2, then 0 more, then 0 more and one lost to dilution). Every one of those searches kept the
same verb: construct a value, call the function the test calls, look at what comes back.

The verb is the part nobody varied, and the corpus says so out loud. `pypa/packaging`'s own fix carries a failing
case named `test_copy_and_pickle_preserve_state[False--None-copy]`: the behaviour that changed is what `copy.copy`
and `pickle` do to a `Version`, not what calling `Version(...)` returns. `checkability_by_differential_pin_v1`
drove every public callable of the touched module through an alphabet of empty-ish arguments and converted 0 of 13
drivable unguarded commits -- with the *right* verb missing, no argument alphabet can help.

WHAT THIS MEASURES
------------------
Seeds are held FIXED at the tests' own literal calls -- the same 5-6 seeds that produced 2 of 8. The only thing
that changes is that each seed's value is put through the protocol operations any Python value already has:

    pickle.loads(pickle.dumps(v))    copy.copy(v)      copy.deepcopy(v)     repr(v)
    str(v)                           hash(v)           copy.copy(v) == v    pickle round-trip == v

Each (seed, operation) pair is executed at BOTH states -- the fixed file and the same file with the audited part
reverted -- in one child process per state. A pin is an outcome that is stable at the fixed state and different at
the reverted one; the assertion is written from the observed outcome, then verified to pass at the fixed state and
fail at the reverted state. If it does not fail at the reverted state, it is not a pin and is not counted.

WHY THIS IS THE ULTIMATE FORM AND NOT ANOTHER ITERATION
-------------------------------------------------------
The seed rounds all searched for a better INPUT. This searches the space of OPERATIONS over the artifact's own
values -- the space a user actually exercises when they copy, pickle, compare, hash or print something. It needs
no model, no corpus, no vocabulary and no domain knowledge, because the operation alphabet is the language's own
protocol. Nothing is stored and no parameter holds knowledge: the artifact is the specification, the two states
are the oracle, the language is the action space.

KILL CRITERION, WRITTEN BEFORE THE RUN
--------------------------------------
If the operation dimension does not pin strictly more of the same parts than the literal-call search did (2 of 8),
the dimension is dead and the receipt says so.
"""

from __future__ import annotations

import argparse
import builtins
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import checkability_by_differential_pin_v1 as C  # noqa: E402  helpers, never modified
from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import reach_the_changed_site_v1 as R  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

SCHEMA = "BRAIN_THE_OPERATION_IS_THE_MISSING_DIMENSION_V1"

#: The selection rule for the operation population, stated as code so it cannot be quietly widened: a fix belongs
#: to it when the case its own commit made fail is NAMED after an operation. Selecting where a hypothesis applies is
#: not the same as supplying its answer -- the seeds are still only the test's literals and the assertion is still
#: built from a measured difference -- but the random sample is always reported beside it.
OPERATION_WORDS = ("copy", "pickle", "deepcopy", "equal", "eq", "hash", "repr", "str", "iter", "len", "state")
MODEL_CALLS = 0
NETWORK_CALLS = 0
MAX_PARTS = 3
PIN_TEST_NAME = "test_round20_operation_pin.py"

#: The language's own protocol, not a vocabulary anybody wrote. Every Python value already has these verbs.
OPERATIONS: tuple[dict[str, str], ...] = (
    {"name": "pickle_roundtrip", "expr": "pickle.loads(pickle.dumps(value))"},
    {"name": "copy", "expr": "copy.copy(value)"},
    {"name": "deepcopy", "expr": "copy.deepcopy(value)"},
    {"name": "eq_copy", "expr": "copy.copy(value) == value"},
    {"name": "eq_pickle", "expr": "pickle.loads(pickle.dumps(value)) == value"},
    # An object's STATE is the observable a user actually loses when a copy silently drops a field, and repr and
    # __eq__ both hide it: `<Version('1.0')> == <Version('1.0')>` while one of them has forgotten its prereleases
    # override. `__dict__` and `__slots__` are the language's own protocol, not knowledge about the domain.
    {"name": "state_copy_equal", "expr": "state_of(value) == state_of(copy.copy(value))"},
    {"name": "state_pickle_equal", "expr": "state_of(value) == state_of(pickle.loads(pickle.dumps(value)))"},
    {"name": "repr", "expr": "repr(value)"},
    {"name": "str", "expr": "str(value)"},
)
# `hash(value)` is deliberately absent. For any object with the default __eq__, hash is derived from identity, so
# two child processes disagree for reasons that have nothing to do with the change -- the same artefact that made
# checkability_by_differential_pin_v1 report a false 21.1% before it removed identity from the comparison.

#: The prober's helpers -- canon(), content(), shape_value(), ADDRESS -- are imported rather than rewritten, so
#: that two modules cannot drift into two definitions of "the same behaviour". The prefix ends where the original
#: prober starts reading its request.
HELPERS = C.PROBER.split("\nresults = []")[0]
if not all(name in HELPERS for name in ("def canon(", "def content(", "def shape_value(", "ADDRESS")):
    # the split is a contract with the other module, so it is enforced rather than assumed
    raise RuntimeError("the reuse of checkability_by_differential_pin_v1.PROBER helpers has drifted")

CHILD = '''
import copy, importlib, itertools, json, os, pickle, sys
os.environ.setdefault("PIN_REQUEST", '{"calls": []}')   # the imported helpers read this once, at definition time
''' + HELPERS + '''
OPS = json.loads(os.environ["OP_REQUEST"])["ops"]
SEEDS = json.loads(os.environ["OP_REQUEST"])["seeds"]


def shape_message(text):
    return ADDRESS.sub("0xADDR", text)[:200]


def state_of(value):
    """The object's own exposed state: its __dict__, and every slot on its MRO. Identity is masked."""
    state = {}
    mapping = getattr(value, "__dict__", None)
    if isinstance(mapping, dict):
        for key, item in sorted(mapping.items(), key=lambda pair: str(pair[0])):
            state[str(key)] = canon(item)
    for klass in type(value).__mro__:
        slots = getattr(klass, "__slots__", ()) or ()
        if isinstance(slots, str):
            slots = (slots,)
        for slot in slots:
            if not isinstance(slot, str) or slot in ("__dict__", "__weakref__"):
                continue
            try:
                state["slot:" + slot] = canon(getattr(value, slot))
            except BaseException:
                state["slot:" + slot] = "<absent>"
    return state


def state_repr(value):
    try:
        return json.dumps(state_of(value), sort_keys=True)[:600]
    except BaseException:
        return "<unstateable>"


def build(seed):
    module = importlib.import_module(seed["module"])
    return getattr(module, seed["function"])(*[shape_value(token) for token in seed["args"]])


records = []
for seed in SEEDS:
    for op in OPS:
        record = {"label": seed["label"], "op": op["name"], "module": seed["module"],
                  "function": seed["function"], "args": seed["args"]}
        try:
            value = build(seed)
        except BaseException as exc:
            record.update(outcome="BUILD_RAISED", type=type(exc).__name__,
                          message_shape=shape_message(str(exc)))
            records.append(record)
            continue
        namespace = {"value": value, "copy": copy, "pickle": pickle, "itertools": itertools,
                     "sorted": sorted, "type": type, "len": len, "repr": repr, "str": str, "hash": hash}
        try:
            outcome = eval(op["expr"], dict(namespace))
        except BaseException as exc:
            record.update(outcome="RAISED", type=type(exc).__name__, message_shape=shape_message(str(exc)))
        else:
            record.update(outcome="RETURNED", type=type(outcome).__name__, value_repr=canon(outcome),
                          value_state=state_repr(outcome))
        records.append(record)
print("RESULTS " + json.dumps(records))
'''


def _tokens(args: Sequence[Any]) -> list[str]:
    """A seed argument as a reversible token: strings by value, everything else as JSON."""
    out: list[str] = []
    for argument in args:
        if isinstance(argument, str):
            out.append("=" + argument)
        else:
            try:
                out.append("@json:" + json.dumps(argument))
            except (TypeError, ValueError):
                continue
    return out


def _literal(token: str) -> str:
    if token.startswith("="):
        return repr(token[1:])
    return repr(json.loads(token[len("@json:"):]))


def seeds_from_calls(calls: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seeds, seen = [], set()
    for call in calls:
        args = _tokens(call.get("args") or [])
        if not args or args[0].startswith("=@builtin") or "module" not in call:
            continue
        label = f"{call['module']}.{call['function']}({', '.join(args)})"
        if label in seen:
            continue
        seen.add(label)
        seeds.append({"label": label, "module": call["module"], "function": call["function"], "args": args})
    return seeds


def probe_state(tree: pathlib.Path, seeds: Sequence[Mapping[str, Any]],
                operations: Sequence[Mapping[str, str]] = OPERATIONS) -> list[dict[str, Any]]:
    """One child process at whatever state the tree is in now."""
    if not seeds:
        return []
    request = {"seeds": [dict(seed) for seed in seeds], "ops": [dict(op) for op in operations]}
    with tempfile.TemporaryDirectory(prefix="opdim-") as scratch:
        script = pathlib.Path(scratch) / "child.py"
        script.write_text(CHILD, encoding="utf-8")
        env = G._env_for(tree)
        env["OP_REQUEST"] = json.dumps(request)
        try:
            done = subprocess.run([sys.executable, str(script)], cwd=str(tree), capture_output=True, text=True,
                                  timeout=300, env=env)
        except subprocess.TimeoutExpired:
            return []
    for line in reversed(done.stdout.splitlines()):
        if line.startswith("RESULTS "):
            try:
                return json.loads(line[len("RESULTS "):])
            except ValueError:
                return []
    return []


def _signature(record: Mapping[str, Any]) -> str:
    return json.dumps({key: record.get(key) for key in
                       ("outcome", "type", "value_repr", "value_state", "message_shape")}, sort_keys=True)


def _at_state(tree: pathlib.Path, source_rel: str, text: str, seeds, operations=OPERATIONS):
    """Probe with the file at `text`, then ALWAYS restore. A tree left modified makes every later number a lie."""
    target = tree / source_rel
    original = target.read_bytes()
    try:
        target.write_text(text, encoding="utf-8")
        return probe_state(tree, seeds, operations)
    finally:
        target.write_bytes(original)


def _assertion(record: Mapping[str, Any]) -> str | None:
    """The smallest test that states what this operation did, expressed only in literals."""
    make = f"_make({', '.join(_literal(token) for token in record['args'])})"
    expression = next(op["expr"] for op in OPERATIONS if op["name"] == record["op"])
    body = expression.replace("value", make)
    if record.get("outcome") == "RETURNED":
        rendered = record.get("value_repr") or ""
        if not rendered or "0xADDR" in rendered or len(rendered) > 180:
            return None
        return f"    assert repr({body}) == {rendered!r}\n"
    if record.get("outcome") == "RAISED":
        name = str(record.get("type") or "")
        if not hasattr(builtins, name):
            return None                       # a custom exception needs the artifact's own import: not this round
        return f"    with pytest.raises({name}):\n        {body}\n"
    if record.get("outcome") == "BUILD_RAISED":
        name = str(record.get("type") or "")
        if not hasattr(builtins, name):
            return None
        return f"    with pytest.raises({name}):\n        {make}\n"
    return None


def _pin_source(record: Mapping[str, Any]) -> str | None:
    body = _assertion(record)
    if body is None:
        return None
    # the operation's own imports are emitted with the assertion: a pin that fails on NameError at the fixed state
    # would be indistinguishable from a pin that does not hold, and the verifier would silently drop both
    helper = ""
    if "state_of(" in body:
        helper = ("\n\ndef state_of(value):\n    state = {}\n    mapping = getattr(value, \"__dict__\", None)\n"
                  "    if isinstance(mapping, dict):\n        for key, item in sorted(mapping.items(), key=lambda p: str(p[0])):\n"
                  "            state[str(key)] = repr(item)\n    for klass in type(value).__mro__:\n"
                  "        slots = getattr(klass, \"__slots__\", ()) or ()\n        if isinstance(slots, str):\n"
                  "            slots = (slots,)\n        for slot in slots:\n"
                  "            if not isinstance(slot, str) or slot in (\"__dict__\", \"__weakref__\"):\n"
                  "                continue\n            try:\n                state[\"slot:\" + slot] = repr(getattr(value, slot))\n"
                  "            except BaseException:\n                state[\"slot:\" + slot] = \"<absent>\"\n    return state\n")
    return ("import copy\nimport pickle\n\nimport pytest\n\nfrom " + record["module"] + " import "
            + record["function"] + " as _make\n" + helper + "\n\ndef test_the_operation_the_fix_changed():\n" + body)


def judge_part(tree: pathlib.Path, source_rel: str, test_rel: str, fixed: str, mutant: str,
               seeds: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Does any operation over the tests' own seeds separate the two states, and does the separating assertion hold?"""
    at_fixed = _at_state(tree, source_rel, fixed, seeds)
    at_mutant = _at_state(tree, source_rel, mutant, seeds)
    if not at_fixed or len(at_fixed) != len(at_mutant):
        return {"state": R.REFUSED_NO_SEED, "differences": 0}
    differences = []
    for left, right in zip(at_fixed, at_mutant):
        if left.get("label") != right.get("label") or left.get("op") != right.get("op"):
            continue
        if _signature(left) != _signature(right):
            differences.append((left, right))
    if not differences:
        return {"state": R.NOT_REACHED, "differences": 0, "cases": len(at_fixed)}

    pin_file = tree / PIN_TEST_NAME
    verified: list[dict[str, Any]] = []
    try:
        for fixed_record, mutant_record in differences:
            source = _pin_source(fixed_record)
            if source is None:
                continue
            pin_file.write_text(source, encoding="utf-8")
            # verified against the FIXED TEXT, not against whatever the checkout currently holds: a tree on disk
            # sits at the parent state, so running the pin here would test it against the bug it is meant to catch
            if not G.try_candidate(tree, source_rel, PIN_TEST_NAME, fixed)["passed"]:
                continue                                  # does not even hold at the fixed state
            if G.try_candidate(tree, source_rel, PIN_TEST_NAME, mutant)["passed"]:
                continue                                  # passes on the reverted part: not a pin
            verified.append({"op": fixed_record["op"], "label": fixed_record["label"],
                             "seen": _signature(fixed_record), "was": _signature(mutant_record),
                             "assertion": source})
            break
    finally:
        pin_file.unlink(missing_ok=True)
    return {"state": R.PINNED if verified else R.REACHED_NO_DIFF, "differences": len(differences),
            "cases": len(at_fixed), "pin": verified[0] if verified else None}


def selects_operation(task: Mapping[str, Any]) -> bool:
    names = " ".join(task.get("failed_nodes") or []).lower()
    return any(word in names for word in OPERATION_WORDS)


def audit_task(task: Mapping[str, Any], grammar: Sequence[Mapping[str, Any]], cap: int = MAX_PARTS,
               baseline: bool = False) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    entry = next((g for g in grammar if g["sha"] == task["sha"] and g["source"] == source_rel), None)
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    if entry is None:
        return {**row, "state": PINS.REFUSED_NO_GRAMMAR}
    fixed, defective = entry["repaired"], entry["defective"]
    if G.try_candidate(tree, source_rel, test_rel, defective)["passed"] or \
            not G.try_candidate(tree, source_rel, test_rel, fixed)["passed"]:
        return {**row, "state": R.REFUSED_CONTROL}
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") \
        if (tree / test_rel).is_file() else ""
    seeds = seeds_from_calls(SYN.calls_from_the_test(test_source))
    row["seeds"] = len(seeds)
    judged: list[dict[str, Any]] = []
    for part in PINS.hunks(defective, fixed):
        if len(judged) >= cap:
            break
        if not PINS.is_behavioural(fixed, part) or PINS.typing_only(fixed, part):
            continue
        mutant = PINS.revert(fixed, defective, part)
        if G.try_candidate(tree, source_rel, test_rel, mutant)["passed"] is False:
            continue                       # the suite already pins this part: nothing to search
        verdict = judge_part(tree, source_rel, test_rel, fixed, mutant, seeds)
        verdict["part_head"] = str(part.get("added") or "").strip()[:120] or "(removal)"
        if baseline:
            from canonical.swe_kernel import the_repository_is_the_seed_corpus_v1 as SEEDS_ONLY
            verdict["literal_calls"] = SEEDS_ONLY.judge(tree, source_rel, test_rel, fixed, mutant, part,
                                                        SYN.calls_from_the_test(test_source))["state"]
        judged.append(verdict)
    pinned = sum(1 for item in judged if item["state"] == R.PINNED)
    return {**row, "parts": judged, "unpinned_parts": len(judged), "pinned": pinned,
            "state": R.PINNED if pinned else (PINS.FULLY_PINNED if not judged else R.NOT_REACHED)}


def measure(tasks: Sequence[Mapping[str, Any]], grammar: Sequence[Mapping[str, Any]],
            baseline: bool = False) -> dict[str, Any]:
    rows = [audit_task(task, grammar, baseline=baseline) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    parts = [item for row in rows for item in (row.get("parts") or [])]
    pinned = [item for item in parts if item["state"] == R.PINNED]
    by_operation: dict[str, int] = {}
    for item in pinned:
        name = (item.get("pin") or {}).get("op") or "?"
        by_operation[name] = by_operation.get(name, 0) + 1
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "kill_criterion": "if the operation dimension does not pin strictly more of the same parts than the "
                          "literal-call search (2 of 8), the dimension is dead",
        "totals": {
            "tasks": len(rows), "states": states, "parts_audited": len(parts), "parts_pinned": len(pinned),
            "pinned_by_operation": by_operation,
            "cases_executed": sum(item.get("cases") or 0 for item in parts),
            "differences_found": sum(item.get("differences") or 0 for item in parts),
            "literal_call_baseline_pinned": 2,
            "baseline_on_this_population": sum(1 for item in parts
                                               if item.get("literal_calls") == R.PINNED)
            if baseline else None,
            "gain_over_the_seed_search": len(pinned) - 2,
            "certified_share_before": 0.762,
            "certified_share_after": round((32 + max(0, len(pinned) - 2)) / 42, 3) if parts else None,
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [(row, item) for row in report["rows"] for item in (row.get("parts") or []) if item["state"] == R.PINNED]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]} via {(item['pin'] or {}).get('op')}: "
                       + str((item["pin"] or {}).get("label") or "")[:70] for row, item in won)
    return (f"{totals['tasks']} real fixes: {totals['parts_audited']} parts the suite accepts without. The literal-call "
            f"search pinned {totals['literal_call_baseline_pinned']} of 8. The same seeds through the language's own "
            f"protocol operations pin {totals['parts_pinned']} ({totals['differences_found']} separating outcomes in "
            f"{totals['cases_executed']} executions). Gain {totals['gain_over_the_seed_search']:+d}; by operation "
            f"{totals['pinned_by_operation']}. Certified share {totals['certified_share_before']} -> "
            f"{totals['certified_share_after']}." + (f" {detail}" if detail else ""))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--select", choices=("random", "operations"), default="random",
                        help="which population to test; `operations` keeps only fixes whose failing case is named "
                             "after an operation, and always reports the literal-call baseline beside the result")
    args = parser.parse_args(argv)
    from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest = args.manifest
    if args.select == "operations":
        chosen = [task for task in payload["tasks"] if selects_operation(task)]
        scratch = pathlib.Path(tempfile.mkdtemp(prefix="opsel-")) / "manifest.json"
        scratch.write_text(json.dumps({**payload, "tasks": chosen}, indent=1) + "\n", encoding="utf-8")
        manifest = scratch
        print(f"operation population: {len(chosen)} of {len(payload['tasks'])} tasks")
    tasks = SHAPE.prepare_corpus(manifest, args.hist, args.work, limit=None if args.select == "operations"
                                 else args.limit)
    grammar = payload["grammar"]
    report = measure(tasks, grammar, baseline=args.select == "operations")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
