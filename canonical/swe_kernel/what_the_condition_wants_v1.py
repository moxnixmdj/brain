"""Read the value a changed condition compares against, out of the program itself, then deliver it.

THE WALL ROUND 17 HIT
---------------------
`reach_the_changed_site_v1` generates inputs by mutation and descends a distance taken from the quantities a
changed block compares against. It reached and pinned 2 of 8 unpinned behavioural parts of real fixes. The
four it never reached all compare against STRUCTURE rather than a quantity:

    elif isinstance(state, dict) and state.keys() >= set(self.__slots__):
    suffix_location(state, "End of line or end of document not found after a statement" ...)

No integer means no distance means no gradient, and mutation stalls. The published field solves exactly this
with **input-to-state correspondence** (REDQUEEN, NDSS'19; CmpLog in AFL++; Fuzzy-SAT): record the operand
pairs at comparisons the run actually evaluates, and the operand that the input does not determine is the
value the check WANTS. Halo (Oakland'24) is the same idea turned into a filter and generates 43% reachable
inputs against AFLGo's 5.3% without symbolic execution. IDFuzz (USENIX'25) reaches further only by training a
neural model over past inputs -- the dependency this tree refuses.

WHY THE INSTRUMENT MUST NOT AIM AT THE TARGET LINE
--------------------------------------------------
A comparison at an unreached line never executes, so logging "at the target" harvests nothing -- the same
chicken-and-egg that makes the wall a wall. This module therefore instruments EVERY single-operator comparison
in the target file, runs the human's own seed inputs, and keeps the logged pairs that belong to the deepest
EXECUTED comparison at or before the target. That comparison is the last gate the run actually arrived at; its
operand that the input does not determine is what the next input must contain.

WHAT IT DOES
------------
    log        every `a <op> b` in the file, rewritten to evaluate each side once and record both operands
    harvest    the operand pairs from the executed frontier, tagged by type
    wanted     the operand that the seed input does not appear in (3-character colouring, as REDQUEEN does)
    deliver    a real Python value of the wanted type -- dict with those keys, set of those elements, the
               string, the integer -- because a value of the wrong type is not a value the check can accept
    decide     the same rule as round 17: an assertion only if it is green on the fix and red on the revert

WHAT IS DELIBERATELY NOT CLAIMED
--------------------------------
Not every condition is a comparison: `isinstance(state, dict)` is a call, and a wanted value that no executed
comparison mentions is never invented. A part that needs either is reported with the comparison it stopped at,
never with a claim of unreachability. The instrumentation is single-operator comparisons only; chained
comparisons are counted and skipped rather than rewritten into something whose semantics nobody checked.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import reach_the_changed_site_v1 as R  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

SCHEMA = "BRAIN_WHAT_THE_CONDITION_WANTS_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
BUDGET = 160
MAX_CANDIDATES = 12
MAX_PARTS = 3
ROUNDS = 10           # gates the walk may pass, one comparison at a time

REACHED_BY_AN_OPERAND = "REACHED_BY_AN_OPERAND__THE_VALUE_CAME_FROM_THE_PROGRAM"
PINNED = R.PINNED
REACHED_NO_DIFF = R.REACHED_NO_DIFF
NOT_REACHED = R.NOT_REACHED
REFUSED_NO_SEED = R.REFUSED_NO_SEED
REFUSED_REMOVAL = R.REFUSED_REMOVAL
REFUSED_CONTROL = R.REFUSED_CONTROL
REFUSED_NO_SEARCHABLE = "REFUSED__NO_EXECUTED_COMPARISON_TO_READ"

_PRELUDE = '''import json as _json
import os as _os


def __reach_cmplog__(tag, left, right, ok):
    path = _os.environ.get("REACH_CMPLOG")
    if not path:
        return

    def pack(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return [type(value).__name__, value]
        if isinstance(value, (set, frozenset)):
            return [type(value).__name__, sorted(repr(item)[:40] for item in value)[:12]]
        if isinstance(value, dict):
            return ["dict", {str(key)[:40]: repr(item)[:40] for key, item in list(value.items())[:12]}]
        if isinstance(value, (list, tuple)):
            return [type(value).__name__, [repr(item)[:40] for item in value][:12]]
        return [type(value).__name__, repr(value)[:120]]

    with open(path, "a", encoding="utf-8") as handle:
        handle.write(_json.dumps({"tag": tag, "a": pack(left), "b": pack(right), "ok": bool(ok)}) + "\\n")
def __reach_cmplog_call__(tag, arguments, result):
    path = _os.environ.get("REACH_CMPLOG")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(_json.dumps({"tag": tag, "kind": "call",
                                  "args": [repr(argument)[:60] for argument in arguments],
                                  "ok": bool(result)}) + "\\n")

'''


def _prelude_offset() -> int:  # noqa: D401 - measured at first use, after _instrument exists
    """Lines the prelude adds. PROVEN, not assumed: a traced child reports lines of the INSTRUMENTED file, so
    comparing them against a target line taken from the original file silently never matches. The first corpus
    run of this module reported 0 reach for a part whose walk had in fact passed line 733, entirely because of
    this shift."""
    probe = "def _probe(a, b):\n    return a > b\n"
    instrumented, _, _ = _instrument(probe, 1, 9)
    for number, line in enumerate(instrumented.splitlines(), start=1):
        if "return (__a1 := a)" in line or "__a1 := a" in line:
            return number - 2
    raise AssertionError("the prelude offset could not be measured")


class _LogComparisons(ast.NodeTransformer):
    """Rewrite `a <op> b` into `((x := a), (y := b), log(x, y), x <op> y)[-1]`: one evaluation per side."""

    def __init__(self, low: int, high: int) -> None:
        self.low, self.high = low, high
        self.rewritten = 0
        self.skipped = 0

    def visit_If(self, node: ast.If) -> ast.AST:
        node.test = self._instrument_test(node.test)
        self.generic_visit(node)
        return node

    def visit_While(self, node: ast.While) -> ast.AST:
        node.test = self._instrument_test(node.test)
        self.generic_visit(node)
        return node

    def _instrument_test(self, test: ast.AST) -> ast.AST:
        """A gate that is a CALL, not a comparison: `isinstance(state, dict)` is the packaging failure's wall.

        CmpLog hooks strcmp/memcmp for exactly this reason. The call's result and its arguments are logged, so
        the walk learns that the shape it sent was rejected -- which is the only thing that tells it to try a
        different shape. Starred and keyword arguments are left alone rather than rewritten blind.
        """
        calls = [node for node in ast.walk(test)
                 if isinstance(node, ast.Call) and not node.keywords
                 and not any(isinstance(argument, ast.Starred) for argument in node.args)]
        if not calls:
            return test
        self.calls = getattr(self, "calls", 0)
        for call in calls:
            self.calls += 1
            index = self.calls
            tag = f"call{index}@L{call.lineno}"
            value = ast.Name(id=f"__rc{index}", ctx=ast.Store())
            logged = ast.Tuple(elts=[self.visit(argument) if isinstance(argument, ast.Compare) else argument
                                     for argument in call.args], ctx=ast.Load())
            record = ast.Call(func=ast.Name(id="__reach_cmplog_call__", ctx=ast.Load()),
                              args=[ast.Constant(tag), logged, ast.Name(id=f"__rc{index}", ctx=ast.Load())],
                              keywords=[])
            packed = ast.Tuple(elts=[ast.NamedExpr(target=value, value=call), record,
                                     ast.Name(id=f"__rc{index}", ctx=ast.Load())], ctx=ast.Load())
            replacement = ast.Subscript(value=packed,
                                        slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1)),
                                        ctx=ast.Load())
            for parent in ast.walk(test):
                for field, child in ast.iter_fields(parent):
                    if child is call:
                        setattr(parent, field, ast.copy_location(replacement, call))
                    elif isinstance(child, list) and call in child:
                        child[child.index(call)] = ast.copy_location(replacement, call)
        return test

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        if len(node.ops) != 1:
            self.skipped += 1                          # a chain is three comparisons; not rewritten blind
            return node
        if not (self.low <= node.lineno <= self.high):
            return node
        self.rewritten += 1
        tag = f"cmp{self.rewritten}@L{node.lineno}"
        left, right = ast.Name(id=f"__a{self.rewritten}", ctx=ast.Store()), ast.Name(id=f"__b{self.rewritten}", ctx=ast.Store())
        bind = [ast.NamedExpr(target=left, value=node.left),
                ast.NamedExpr(target=right, value=node.comparators[0])]
        read = [ast.Name(id=f"__a{self.rewritten}", ctx=ast.Load()), ast.Name(id=f"__b{self.rewritten}", ctx=ast.Load())]
        core = ast.Compare(left=ast.Name(id=f"__a{self.rewritten}", ctx=ast.Load()), ops=node.ops,
                           comparators=[ast.Name(id=f"__b{self.rewritten}", ctx=ast.Load())])
        result = ast.Name(id=f"__c{self.rewritten}", ctx=ast.Store())
        log = ast.Call(func=ast.Name(id="__reach_cmplog__", ctx=ast.Load()),
                       args=[ast.Constant(tag), read[0], read[1],
                             ast.Name(id=f"__c{self.rewritten}", ctx=ast.Load())], keywords=[])
        packed = ast.Tuple(elts=[bind[0], bind[1], ast.NamedExpr(target=result, value=core), log,
                                 ast.Name(id=f"__c{self.rewritten}", ctx=ast.Load())], ctx=ast.Load())
        out = ast.Subscript(value=packed, slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1)), ctx=ast.Load())
        return ast.copy_location(out, node)


def _enclosing_range(source: str, line: int) -> tuple[int, int]:
    """The innermost function or class containing the changed line: the scope whose comparisons decide reach.

    Instrumenting only the changed block is the trap this module's own docstring warns about -- a comparison at
    an unreached line never executes, so nothing is logged, and the first corpus run measured exactly that:
    3 rewritten comparisons and 0 operand pairs across 8 parts. The comparisons that decide whether the block
    is reached sit in the ENCLOSING scope, so that is what gets instrumented.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 1, max(1, len(source.splitlines()))
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            end = getattr(node, "end_lineno", None) or node.lineno
            if start <= line <= end and (best is None or (end - start) < (best[1] - best[0])):
                best = (start, end)
    return best or (1, max(1, len(source.splitlines())))


def _instrument(source: str, low: int, high: int) -> tuple[str, int, int]:
    """Every single-operator comparison between two line numbers, logged. Returns (source, rewritten, skipped)."""
    tree = ast.parse(source)
    logger = _LogComparisons(low, high)
    tree = logger.visit(tree)
    ast.fix_missing_locations(tree)
    return _PRELUDE + "\n" + ast.unparse(tree) + "\n", logger.rewritten, logger.skipped


_BATCHER = r'''import json, os, re, sys

ADDRESS = re.compile(r"0x[0-9a-fA-F]{6,}")
REQUEST = json.loads(os.environ["REACH_REQUEST"])
TARGET = os.path.realpath(REQUEST["target_file"])
TARGET_LINE = int(REQUEST["target_line"])


def build(args, kinds):
    out = []
    for value, kind in zip(args, kinds):
        if kind == "set" and isinstance(value, list):
            out.append(frozenset(value))
        elif kind == "tuple" and isinstance(value, list):
            out.append(tuple(value))
        elif kind == "list" and isinstance(value, list):
            out.append(list(value))
        else:
            out.append(value)
    return out


results = []
cache = {}
for item in REQUEST["cases"]:
    module = cache.setdefault(item["module"], __import__(item["module"], fromlist=["x"]))
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
        value = target(*build(item.get("args") or [], item.get("kinds") or []))
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
    script = pathlib.Path(tempfile.mkdtemp(prefix="wants-")) / "batch.py"
    script.write_text(_BATCHER, encoding="utf-8")
    env = G._env_for(tree)
    env["REACH_REQUEST"] = json.dumps({"target_file": target_file, "target_line": target_line,
                                       "cases": [dict(case) for case in cases]})
    try:
        done = subprocess.run([sys.executable, str(script)], cwd=str(tree), env=env,
                              capture_output=True, text=True, timeout=300)
        return json.loads(done.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001 - a failed batch is reported, never silently scored
        return [{"outcome": "BATCH_FAILED", "lines": []} for _ in cases]


def _unpack(tagged: Sequence[Any]) -> Any:
    """Turn one logged operand back into a real Python value, so the delivered argument has the right type."""
    kind, payload = tagged[0], tagged[1]
    if kind in ("str", "int", "float", "bool", "NoneType"):
        return payload
    if kind in ("set", "frozenset"):
        return {ast.literal_eval(item) for item in payload
                if item and item[0] in "'\"" or item.lstrip("-").isdigit()}
    if kind == "dict":
        return {key: 1 for key in payload}
    if kind in ("list", "tuple"):
        return [ast.literal_eval(item) for item in payload if item]
    return None


def _derived_from(tagged: Sequence[Any], inputs: Sequence[str]) -> bool:
    """REDQUEEN's colouring, at 3 characters: does the input appear inside this operand?"""
    text = json.dumps(tagged[1])
    for seed in inputs:
        for start in range(0, max(0, len(seed) - 2)):
            if seed[start:start + 3] in text:
                return True
    return False


def _line_of(entry: Mapping[str, Any]) -> int:
    match = re.search(r"@L(\d+)", str(entry.get("tag") or ""))
    return int(match.group(1)) if match else 0


def _turned_away(entries: Sequence[Mapping[str, Any]], target_line: int) -> list[dict[str, Any]]:
    """The comparisons that evaluated FALSE at or before the target: those are the gates the run did not pass.

    A comparison that returned True on the path is not what stopped the run, and a comparison after the target
    cannot be what stopped it either. Both orderings matter: the first corpus run took the deepest logged
    comparison instead, and delivered the operands of comparisons that had already succeeded.
    """
    failed = [entry for entry in entries if entry.get("ok") is False and _line_of(entry) <= target_line]
    if not failed:
        return []
    deepest = max(_line_of(entry) for entry in failed)
    return [entry for entry in failed if _line_of(entry) == deepest]


def _wanted(entries: Sequence[Mapping[str, Any]], inputs: Sequence[str]) -> list[Any]:
    """The operand the input does NOT determine, in the order the frontier produced it."""
    out: list[Any] = []
    seen: set[str] = set()
    for entry in entries:
        if str(entry.get("kind") or "") == "call":
            continue                                # a call gate names a SHAPE, not a value
        for mine, other in ((entry["a"], entry["b"]), (entry["b"], entry["a"])):
            if _derived_from(mine, inputs) and not _derived_from(other, inputs):
                value = _unpack(other)
                if value is None or isinstance(value, (dict, set, list, tuple)) and not value:
                    continue
                key = f"{type(value).__name__}:{value!r}"[:200]
                if key in seen:
                    continue
                seen.add(key)
                out.append(value)
    return out[:MAX_CANDIDATES]


def _type_rerolls(seeds: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The gate is a call, so nothing names a value; what it rejected is the SHAPE. Send the other shapes.

    `isinstance(state, dict)` refuses a string and a list identically, and the comparison behind it -- the one
    that would name the wanted keys -- only becomes visible once a mapping arrives. So the seed's own content is
    re-delivered as a mapping keyed by it, as a set, as a tuple, and as a list.
    """
    cases = []
    for seed in seeds:
        if not seed["args"]:
            continue
        first = seed["args"][0]
        rest = [argument for argument in seed["args"][1:]
                if isinstance(argument, (str, int, float, bool, list, dict, type(None)))]
        items = list(first) if isinstance(first, (str, list, tuple)) else [first]
        items = [item for item in items if isinstance(item, (str, int, float, bool))][:12]
        shapes: list[Any] = []
        if items:
            shapes.append({str(item): 1 for item in items})
            shapes.append(list(items))
            shapes.append(tuple(items))
        if isinstance(first, str) and first:
            shapes.append(first)
        for shape in shapes:
            kind = "tuple" if isinstance(shape, tuple) else "raw"
            wire = list(shape) if isinstance(shape, tuple) else shape
            cases.append({"module": seed["module"], "function": seed["function"], "args": [wire] + rest,
                          "kinds": [kind] + ["raw"] * len(rest), "value": repr(shape)[:120]})
    return cases


def _substitutions(value: Any, seeds: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """REDQUEEN's replacement, at the position the seed already occupies: the wanted bytes go INTO the input."""
    cases = []
    text = value if isinstance(value, str) else (str(value) if isinstance(value, int) and not isinstance(value, bool) else None)
    if text is None:
        return cases
    for seed in seeds:
        if not seed["args"] or not isinstance(seed["args"][0], str):
            continue
        original = seed["args"][0]
        rest = [argument for argument in seed["args"][1:]
                if isinstance(argument, (str, int, float, bool, list, dict, type(None)))]
        for shaped in (original + text, text + original, original[:-1] + text if original else text,
                       original[:1] + text + original[1:] if original else text):
            cases.append({"module": seed["module"], "function": seed["function"], "args": [shaped] + rest,
                          "kinds": ["raw"] * (1 + len(rest)), "value": repr(shaped)[:120]})
    return cases


def _cases_for(wanted: Sequence[Any], call: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Each wanted value delivered in every shape that can carry it, carrying the rest of the test's arguments.

    A wanted set is not always accepted as a set: `state.keys() >= {"a", "b"}` states that the WANTED thing is a
    container keyed by those names, and the function refuses anything that is not a mapping before the comparison
    is ever reached. So a collection of scalars is delivered twice -- as itself, and as a mapping keyed by its
    elements -- and the search decides which shape the program actually accepts.
    """
    cases = []
    for value in wanted:
        kind = ("set" if isinstance(value, (set, frozenset)) else "tuple" if isinstance(value, tuple)
                else "list" if isinstance(value, list) else "raw")
        wire = sorted(value) if isinstance(value, (set, frozenset)) else value
        if kind in ("set", "tuple", "list"):
            wire = [item for item in wire if isinstance(item, (str, int, float, bool))]
        args = [wire] + [argument for argument in call["args"][1:]
                         if isinstance(argument, (str, int, float, bool, list, dict, type(None)))]
        kinds = [kind] + ["raw"] * (len(args) - 1)
        cases.append({"module": call["module"], "function": call["function"], "args": args,
                      "kinds": kinds, "value": repr(value)[:120]})
        elements = sorted(value) if isinstance(value, (set, frozenset)) else (
            list(value) if isinstance(value, (list, tuple)) else None)
        if elements and all(isinstance(item, (str, int, float, bool)) for item in elements):
            mapping = {str(item): 1 for item in elements}
            cases.append({"module": call["module"], "function": call["function"],
                          "args": [mapping] + [argument for argument in call["args"][1:]
                                               if isinstance(argument, (str, int, float, bool, list, dict, type(None)))],
                          "kinds": ["raw"] * (1 + len(call["args"]) - 1), "value": repr(mapping)[:120]})
    return cases


def harvest(tree: pathlib.Path, source_rel: str, source: str, low: int, high: int,
            calls: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int, int, list[dict[str, Any]]]:
    """Instrument the fixed file, run the human's seeds, return (logged pairs, rewritten, skipped, results)."""
    target = tree / source_rel
    original = target.read_bytes()
    log = pathlib.Path(tempfile.mkdtemp(prefix="cmplog-")) / "operands.jsonl"
    try:
        scope_low, scope_high = _enclosing_range(source, high)
        instrumented, rewritten, skipped = _instrument(source, scope_low, scope_high)
        target.write_text(instrumented, encoding="utf-8")
        env_log = log
        cases = [{"module": call["module"], "function": call["function"],
                  "args": list(call["args"]), "kinds": ["raw"] * len(call["args"])} for call in calls]
        script = pathlib.Path(tempfile.mkdtemp(prefix="wants-")) / "batch.py"
        script.write_text(_BATCHER, encoding="utf-8")
        env = G._env_for(tree)
        env["REACH_CMPLOG"] = str(env_log)
        env["REACH_REQUEST"] = json.dumps({"target_file": str(target), "target_line": high + _prelude_offset(),
                                           "cases": cases})
        try:
            done = subprocess.run([sys.executable, str(script)], cwd=str(tree), env=env,
                                  capture_output=True, text=True, timeout=300)
            results = json.loads(done.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            results = [{"outcome": "BATCH_FAILED", "lines": []} for _ in cases]
        offset = _prelude_offset()
        results = [{**result, "lines": [line - offset for line in (result.get("lines") or [])]}
                   for result in results]
        entries = [json.loads(line) for line in env_log.read_text().splitlines() if line.strip()] \
            if env_log.exists() else []
        return entries, rewritten, skipped, results
    finally:
        target.write_bytes(original)


def _walk(tree: pathlib.Path, source_rel: str, source: str, target_line: int,
          calls: Sequence[Mapping[str, Any]], budget: int) -> dict[str, Any]:
    """Walk the gates: harvest the failing comparison, deliver its wanted value, keep whatever goes deeper, repeat.

    One substitution passes one gate. A parser's changed line sits behind a SEQUENCE of them -- the first corpus
    run logged its seeds failing at line 90 while the target was line 109 -- so the reached input has to become
    the next round's seed. This is REDQUEEN's replacement driven by the frontier, which is what Halo (Oakland'24)
    measures at 43% reachable-input generation against AFLGo's 5.3%.
    """
    target = tree / source_rel
    corpus = [dict(call) for call in calls]
    best_distance, best_args, best_outcome = None, None, None
    seeded: set[str] = set()
    spent = 0
    for _ in range(ROUNDS):
        if spent >= budget:
            break
        fresh = [call for call in corpus if json.dumps(call["args"], default=str) not in seeded]
        for call in fresh:
            seeded.add(json.dumps(call["args"], default=str))
        if not fresh:
            break
        entries, _, _, results = harvest(tree, source_rel, source, 1, target_line, fresh)
        spent += len(fresh)
        told_away = _turned_away(entries, target_line)
        if not told_away:
            break                                   # nothing failed in front of us: no operand names the gate
        inputs = []
        for call in fresh:
            for argument in call["args"]:
                inputs.append(str(argument))
                inputs.append(json.dumps(argument, default=str))
        wanted = _wanted(told_away, inputs)
        calls_only = all(str(entry.get("kind")) == "call" for entry in told_away)
        if not wanted and not calls_only:
            break
        cases = []
        for value in wanted:                       # every operand the frontier named, not only the first
            cases.extend(_substitutions(value, fresh))
        if calls_only or not wanted:
            cases.extend(_type_rerolls(fresh))
        if wanted:
            cases.extend(_cases_for(wanted, fresh[0]))
        cases = [case for case in cases if json.dumps(case["args"], default=str) not in seeded]
        if not cases or spent >= budget:
            break
        cases = cases[: max(4, (budget - spent) // max(1, ROUNDS // 2))]
        scored = _batch(tree, str(target), target_line, cases)
        spent += len(cases)
        progressed = False
        for case, scored_case in zip(cases, scored):
            lines = scored_case.get("lines") or []
            if scored_case.get("outcome") in ("BATCH_FAILED", "MISSING"):
                continue
            if target_line in lines:
                return {"reached": True, "spent": spent,
                        "call": {"module": case["module"], "function": case["function"], "args": case["args"],
                                 "kinds": case["kinds"]}, "outcome": scored_case["outcome"],
                        "gates_passed": len(told_away)}
            # Distance to the target, not the largest line number: this file's main parse loop sits at line 733
            # while the changed function is at 109, so "deeper" by line number walks AWAY from the target.
            distance = min(abs(line - target_line) for line in lines) if lines else None
            if distance is not None and (best_distance is None or distance < best_distance):
                best_distance, best_args, best_outcome = distance, case, scored_case["outcome"]
                progressed = True
        if best_args is not None and progressed:
            corpus.append({"module": best_args["module"], "function": best_args["function"],
                           "args": list(best_args["args"]), "kinds": list(best_args["kinds"])})
        else:
            break
    return {"reached": False, "spent": spent, "best_distance": best_distance, "best_outcome": best_outcome}


def what_the_condition_wants(tree: pathlib.Path, source_rel: str, test_rel: str, fixed: str, mutant: str,
                             part: Mapping[str, Any], calls: Sequence[Mapping[str, Any]],
                             budget: int = BUDGET) -> dict[str, Any]:
    """Harvest the frontier's wanted values, deliver them at their own type, and pin what the revert changes."""
    if not str(part.get("added") or "").strip():
        return {"state": REFUSED_REMOVAL, "executions": 0}
    if not calls:
        return {"state": REFUSED_NO_SEED, "executions": 0}
    target = tree / source_rel
    target_line = part["new"][1] if part["new"][1] > part["new"][0] else max(1, part["new"][0])
    low, high = part["new"][0] or 1, part["new"][1] or 1
    original = target.read_bytes()
    try:
        target.write_text(fixed, encoding="utf-8")               # the fixed state is what we search against
        entries, rewritten, skipped, seeds = harvest(tree, source_rel, fixed, low, high, calls)
        walk = _walk(tree, source_rel, fixed, target_line, calls, budget)
        # Colourisation runs over the SEED's serialised form, whatever its type: a dict seed determines an
        # operand just as a string seed does, and restricting this to str arguments made every collection
        # seed determine nothing (measured on the first fixture of this module).
        inputs = []
        for call in calls:
            for argument in call["args"]:
                inputs.append(str(argument))
                try:
                    inputs.append(json.dumps(argument, default=str))
                except (TypeError, ValueError):
                    pass
        wanted = _wanted(entries, inputs)
        executed = sorted({line for result in seeds for line in (result.get("lines") or [])})
        if walk.get("reached"):
            case, result = walk["call"], {"outcome": walk["outcome"], "lines": [target_line]}
            target.write_text(mutant, encoding="utf-8")
            cold = _batch(tree, str(target), target_line,
                          [{"module": case["module"], "function": case["function"],
                            "args": case["args"], "kinds": case["kinds"]}])
            reached = {"outcome": result["outcome"], "args": case["args"], "kinds": case["kinds"],
                       "value": repr(case["args"][0])[:120], "gates_passed": walk.get("gates_passed"),
                       "executions": walk.get("spent")}
            if cold and cold[0].get("outcome") != result["outcome"]:
                call = {"module": case["module"], "function": case["function"], "args": case["args"]}
                assertion = SYN._assertion(call, result["outcome"])
                synth = tree / "_wants_synth_test.py"
                if assertion is not None:
                    try:
                        synth.write_text(SYN._testfile(assertion, case["module"]), encoding="utf-8")
                        target.write_text(fixed, encoding="utf-8")
                        green = G.run_test(tree, synth.name)["passed"]
                        target.write_text(mutant, encoding="utf-8")
                        red = not G.run_test(tree, synth.name)["passed"]
                    finally:
                        synth.unlink(missing_ok=True)
                    if green and red:
                        return {"state": PINNED, "comparisons_rewritten": rewritten,
                                "operands_logged": len(entries), "assertion": assertion.strip(), **reached}
            return {"state": REACHED_NO_DIFF, "comparisons_rewritten": rewritten,
                    "operands_logged": len(entries), **reached}
        turned_away = _turned_away(entries, target_line)
        if turned_away:
            entries = turned_away + [entry for entry in entries if entry not in turned_away]
            wanted = _wanted(entries, inputs)
        if not wanted:
            return {"state": REFUSED_NO_SEARCHABLE, "executions": len(seeds), "comparisons_rewritten": rewritten,
                    "chained_skipped": skipped, "operands_logged": len(entries), "executed_lines": len(executed),
                    "failed_comparisons": sum(1 for entry in entries if entry.get("ok") is False),
                    "walk_best_distance": walk.get("best_distance"), "walk_spent": walk.get("spent")}
        frontier = max([line for line in executed if line <= target_line], default=None)
        cases = _substitutions(wanted[0], calls) + _cases_for(wanted, calls[0])
        results = _batch(tree, str(target), target_line, cases)
        executions = len(seeds) + len(cases)
        hit = None
        for case, result in zip(cases, results):
            if result.get("outcome") in ("BATCH_FAILED", "MISSING"):
                continue
            if target_line in (result.get("lines") or []):
                hit = (case, result)
                break
        if hit is None:
            return {"state": NOT_REACHED, "executions": executions + (walk.get("spent") or 0),
                    "walk_best_distance": walk.get("best_distance"),
                    "walk_outcome": str(walk.get("best_outcome"))[:80],
                    "comparisons_rewritten": rewritten,
                    "chained_skipped": skipped, "operands_logged": len(entries), "wanted": [repr(v)[:60] for v in wanted],
                    "frontier_line": frontier, "executed_lines": len(executed)}
        case, result = hit
        target.write_text(mutant, encoding="utf-8")
        cold = _batch(tree, str(target), target_line,
                      [{"module": case["module"], "function": case["function"],
                        "args": case["args"], "kinds": case["kinds"]}])
        reached = {"outcome": result["outcome"], "args": case["args"], "kinds": case["kinds"],
                   "value": case["value"]}
        if not cold or cold[0].get("outcome") == result["outcome"]:
            return {"state": REACHED_NO_DIFF, "executions": executions, "reached_by": REACHED_BY_AN_OPERAND,
                    **reached}
        call = {"module": case["module"], "function": case["function"], "args": case["args"]}
        assertion = SYN._assertion(call, result["outcome"])
        if assertion is None:
            return {"state": REACHED_NO_DIFF, "executions": executions, "note": "outcome not expressible as an assertion",
                    **reached}
        synth = tree / "_wants_synth_test.py"
        try:
            synth.write_text(SYN._testfile(assertion, case["module"]), encoding="utf-8")
            target.write_text(fixed, encoding="utf-8")
            green = G.run_test(tree, synth.name)["passed"]
            target.write_text(mutant, encoding="utf-8")
            red = not G.run_test(tree, synth.name)["passed"]
        finally:
            synth.unlink(missing_ok=True)
        if green and red:
            return {"state": PINNED, "executions": executions, "assertion": assertion.strip(),
                    "comparisons_rewritten": rewritten, "operands_logged": len(entries), **reached}
        return {"state": REACHED_NO_DIFF, "executions": executions, "green": green, "red": red, **reached}
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
            continue                                   # the suite already pins this part
        # The operand channel is composed with round 17's mutation search, never reported as its replacement:
        # the mutation engine already pins 2 of these 8 parts, and an operator that only substitutes operands
        # is narrower than it. Composing is the deletion test -- no second pipeline, one extra operator.
        by_mutation = R.reach_part(tree, source_rel, test_rel, fixed, mutant, part, calls)
        by_operand = what_the_condition_wants(tree, source_rel, test_rel, fixed, mutant, part, calls)
        winner = by_operand if by_operand["state"] == PINNED else by_mutation
        judged.append({**winner, "by_mutation": by_mutation["state"], "by_operand": by_operand["state"],
                       "operand_detail": {key: by_operand.get(key) for key in
                                          ("operands_logged", "wanted", "walk_best_distance", "walk_spent",
                                           "failed_comparisons", "comparisons_rewritten")
                                          if by_operand.get(key) is not None},
                       "part_head": str(part.get("added") or "").strip()[:120] or "(removal)"})
    pinned = sum(1 for item in judged if item["state"] == PINNED)
    return {**row, "parts": judged, "unpinned_parts": len(judged), "pinned_by_operand": pinned,
            "pinned_by_mutation": sum(1 for item in judged if item.get("by_mutation") == PINNED),
            "pinned_by_the_operand_channel": sum(1 for item in judged if item.get("by_operand") == PINNED),
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
            "tasks": len(rows), "states": states, "parts_audited": len(parts), "pinned_by_operand": pinned,
            "pinned_by_mutation": sum(1 for item in parts if item.get("by_mutation") == PINNED),
            "pinned_by_the_operand_channel": sum(1 for item in parts if item.get("by_operand") == PINNED),
            "reached": sum(1 for item in parts if item["state"] in (PINNED, REACHED_NO_DIFF)),
            "not_reached": sum(1 for item in parts if item["state"] == NOT_REACHED),
            "comparisons_rewritten": sum((item.get("operand_detail") or {}).get("comparisons_rewritten") or 0
                                         for item in parts),
            "operands_logged": sum((item.get("operand_detail") or {}).get("operands_logged") or 0 for item in parts),
            # The 32 of 42 already includes the two parts round 17 pinned by mutation. Only a part the OPERAND
            # channel pins that mutation does NOT pin is a new one -- counting the union would be self-flattery.
            "new_pins": sum(1 for item in parts if item.get("by_operand") == PINNED
                            and item.get("by_mutation") != PINNED),
            "certified_share_before": 0.762,
            "certified_share_after": round((32 + sum(1 for item in parts if item.get("by_operand") == PINNED
                                                     and item.get("by_mutation") != PINNED)) / 42, 3)
            if parts else None,
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [row for row in report["rows"] if row.get("pinned_by_operand")]
    detail = "; ".join(
        f"{row['repo'].split('/')[-1]} {row['sha'][:8]}: "
        + " | ".join(str(item.get("assertion") or "").replace("\n", " ") for item in row["parts"]
                     if item["state"] == PINNED) for row in won)
    return (f"{totals['tasks']} real fixes: {totals['parts_audited']} parts the suite accepts without, "
            f"{totals['reached']} reached, {totals['pinned_by_operand']} pinned and verified "
            f"({totals['pinned_by_mutation']} by mutation, {totals['pinned_by_the_operand_channel']} by the operand "
            f"channel), {totals['not_reached']} never reached, over "
            f"{totals['comparisons_rewritten']} rewritten comparisons that logged "
            f"{totals['operands_logged']} operand pairs. Certified share {totals['certified_share_before']} -> "
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
    from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE
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
