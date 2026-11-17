#!/usr/bin/env python3
"""Make unguarded work checkable: pin the behaviour of the artifact's own public surface.

THE QUESTION THIS ANSWERS
-------------------------
"Instant learning is solved, so give the model the most advanced coding actions, let it experience each
once, learn it permanently, and we have solved every problem and all computer use." The claim has one
multiplier nobody has checked: *you cannot learn what you cannot check.* The tree already measured its own
version of this -- of 14 real commits, 10 (71.4%) have no mechanical postcondition at all, and only 4.814%
of real fixes are ever reproduced exactly by an earlier one. The web independently agrees in November 2026:
across 4,882 agent-authored pull requests, existing tests execute 27.0% of changed Python lines, and in
64.8% of Python PRs **not one changed line is executed by any test** (arXiv 2607.18057).

So the binding term is not learning, not search, not model size, and not weights. It is CHECKABILITY: the
share of real work for which an independent, mechanical postcondition exists at all. Learning multiplies that
share; it cannot enlarge it.

WHAT THIS MODULE DOES
---------------------
The previous round built witness inversion and it refused on 18 of 18 real witnesses, for one reason: the
answer was content that did not exist in the artifact, so it could not be selected. That refusal is only a
verdict if nothing else can make the work checkable. This module asks the other half of the question:

    Of the work that has no tests at all, how much already has a postcondition that can be CONSTRUCTED
    mechanically, without the author's tests, without the author's intent, and without a model?

The constructor is differential pinning of the public surface:

  1. take a real commit's touched modules, and the same modules at the parent state;
  2. enumerate the public callables the module itself defines (from its own AST, not from the diff);
  3. drive each one through a bounded grid of empty-ish argument shapes -- values that need no knowledge of
     the domain, so the probe cannot smuggle in the answer;
  4. record the outcome triple (returned, raised type, message shape) at BOTH states;
  5. a PIN is an outcome that is stable at the fixed state and different at the parent.

A pin is a check that exists without anybody writing a test. It is a REGRESSION pin and not a correctness
proof, and this module never conflates them: a pin says "this behaviour must not change", never "this
behaviour is what the user wanted". That distinction is printed in the receipt, because the whole point of
the round is which term is binding, and a dishonest conversion would destroy the answer.

WHAT IT DOES NOT DO
-------------------
No model, no network at measurement time, no parameters, nothing stored. It does not modify any tree: every
probe runs in a child process against a materialised checkout. It does not claim a pin is a test of intent.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import witness_inversion_v1 as witness  # noqa: E402  read, never modified

SCHEMA = "BRAIN_CHECKABILITY_BY_DIFFERENTIAL_PIN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

#: the whole argument alphabet: values that require no knowledge of the repository to choose. An alphabet
#: that needed domain knowledge would be the answer smuggled in through the back door.
ARG_TOKENS: tuple[str, ...] = ("none", "empty_str", "zero", "one", "minus_one", "empty_bytes",
                               "empty_tuple", "empty_list", "empty_dict", "zero_float", "star", "a")
MAX_ARGS = 3
MAX_CALLABLES = 24

#: a child process, so that no import, no sys.modules entry and no global mutation can leak between states
PROBER = r'''
import importlib, json, os, re, sys, traceback

ADDRESS = re.compile(r"0x[0-9a-fA-F]+")


def canon(value):
    """Repr with identity removed. Two objects at different addresses are not two behaviours."""
    try:
        text = repr(value)
    except BaseException:
        return "<unrepresentable>"
    return ADDRESS.sub("0xADDR", text)[:200]


def content(value):
    """A returned value's BEHAVIOUR, not its identity: consume a bounded prefix of any iterator."""
    if hasattr(value, "__next__") or (hasattr(value, "__iter__")
                                      and not isinstance(value, (str, bytes, list, tuple, dict, set,
                                                                 frozenset))):
        items = []
        try:
            iterator = iter(value)
        except BaseException as exc:
            return "iter_error:" + type(exc).__name__
        for _ in range(8):
            try:
                items.append(canon(next(iterator)))
            except StopIteration:
                break
            except BaseException as exc:
                items.append("raised:" + type(exc).__name__)
                break
        return "iter[" + ", ".join(items) + "]"
    return canon(value)

REQUEST = json.loads(os.environ["PIN_REQUEST"])


def shape_value(token):
    if isinstance(token, str) and token.startswith("="):
        return token[1:]                      # a string literal the artifact itself contains
    return {"none": None, "empty_str": "", "zero": 0, "one": 1, "minus_one": -1, "empty_bytes": b"",
            "empty_tuple": (), "empty_list": [], "empty_dict": {}, "zero_float": 0.0,
            "star": "*", "a": "a"}[token]


def call(module_name, function_name, tokens):
    out = {"module": module_name, "function": function_name, "args": tokens}
    try:
        module = importlib.import_module(module_name)
    except BaseException as exc:
        out["outcome"] = "IMPORT_FAILED"
        out["detail"] = type(exc).__name__ + ": " + str(exc)[:180]
        return out
    target = getattr(module, function_name, None)
    if target is None or not callable(target):
        out["outcome"] = "NOT_CALLABLE"
        return out
    args = [shape_value(token) for token in tokens]
    try:
        value = target(*args)
    except BaseException as exc:
        message = str(exc)
        # the message SHAPE, not the message: numbers and paths would make two states differ for reasons
        # that have nothing to do with the change
        shape = "".join("N" if ch.isdigit() else ("S" if ch.isalpha() else ch) for ch in message)[:200]
        out["outcome"] = "RAISED"
        out["type"] = type(exc).__name__
        out["message_shape"] = shape
        return out
    out["outcome"] = "RETURNED"
    out["type"] = type(value).__name__
    out["value_repr"] = content(value)
    return out


def signature(record):
    return json.dumps({key: record.get(key) for key in
                       ("outcome", "type", "value_repr", "message_shape")}, sort_keys=True)


def stable_signature(module_name, function_name, tokens):
    """The same call twice in the same interpreter. Determinism is a property of the call, measured once."""
    first = call(module_name, function_name, tokens)
    second = call(module_name, function_name, tokens)
    first["stable"] = signature(first) == signature(second)
    return first


results = []
for item in REQUEST["calls"]:
    results.append(stable_signature(item["module"], item["function"], item["args"]))
print(json.dumps(results))
'''


def _git(*argv: str, cwd: pathlib.Path) -> str:
    done = subprocess.run(("git",) + argv, cwd=str(cwd), capture_output=True, text=True)
    return done.stdout


def public_callables(source: str, module_name_parts: Sequence[str]) -> list[dict[str, Any]]:
    """What the module itself offers, read from its own AST. Never from the diff, never from the fix."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    offered: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            args = node.args
            required = len(args.posonlyargs) + len(args.args) - len(args.defaults)
            if args.vararg is not None or args.kwarg is not None or args.kwonlyargs:
                continue
            if required > MAX_ARGS or required < 0:
                continue
            offered.append({"function": node.name, "required": required, "kind": "function"})
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            offered.append({"function": node.name, "required": 0, "kind": "class"})
    return offered[:MAX_CALLABLES]


def probe(tree: pathlib.Path, calls: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One child process, one environment, one honest outcome per call."""
    if not calls:
        return []
    request = {"calls": [dict(item) for item in calls]}
    with tempfile.TemporaryDirectory(prefix="pin-") as scratch:
        script = pathlib.Path(scratch) / "prober.py"
        script.write_text(PROBER, encoding="utf-8")
        env = witness._env(tree)
        env["PIN_REQUEST"] = json.dumps(request)
        try:
            done = subprocess.run([sys.executable, str(script)], cwd=str(tree), capture_output=True,
                                  text=True, timeout=180, env=env)
        except subprocess.TimeoutExpired:
            return [{"outcome": "TIMEOUT"} for _ in calls]
    if done.returncode != 0 and not done.stdout.strip():
        return [{"outcome": "PROBER_DIED", "detail": (done.stderr or "")[-300:]} for _ in calls]
    try:
        parsed = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return [{"outcome": "UNPARSED", "detail": (done.stdout + done.stderr)[-300:]} for _ in calls]
    return parsed


def _signature(outcome: Mapping[str, Any]) -> str:
    return json.dumps({key: outcome.get(key) for key in
                       ("outcome", "type", "value_repr", "message_shape")}, sort_keys=True)


def module_literals(source: str, limit: int = 14) -> list[str]:
    """The strings the module itself already contains. The alphabet comes from the artifact: this is the one
    lesson of dictionary-guided repair (arXiv 2609.01775) applied without a vocabulary anyone wrote."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
            if not text or len(text) > 60 or text in found:
                continue
            found.append(text)
    found.sort(key=len)
    return ["=" + text for text in found[:limit]]


def doctest_checkability(clone: pathlib.Path, commit: Mapping[str, Any], work: pathlib.Path,
                         parent_tree: pathlib.Path, fixed_tree: pathlib.Path) -> dict[str, Any]:
    """The artifact's own doctests, run at both states. A doctest that fails at the parent and passes at the
    fix is a postcondition that already existed in the artifact, written by the author of the code and not by
    the author of the change -- so it is independent of the change, which is the whole point."""
    row: dict[str, Any] = {"examples_run": 0, "discriminating": 0, "modules": []}
    for relative in commit["sources"]:
        path = pathlib.Path(relative)
        if path.suffix != ".py":
            continue
        if not (parent_tree / relative).is_file() or not (fixed_tree / relative).is_file():
            continue
        result = {}
        for state, tree in (("parent", parent_tree), ("fixed", fixed_tree)):
            done = subprocess.run([sys.executable, "-m", "pytest", "--doctest-modules", str(tree / relative),
                                   "-q", "-p", "no:cacheprovider"],
                                  cwd=str(tree), capture_output=True, text=True, timeout=180,
                                  env=witness._env(tree))
            text = done.stdout + done.stderr
            result[state] = {"returncode": done.returncode,
                             "collected": "no tests ran" not in text,
                             "tail": text[-160:]}
        row["modules"].append({"module": relative, "parent": result["parent"], "fixed": result["fixed"],
                               "discriminates": bool(result["parent"]["returncode"] != 0
                                                     and result["fixed"]["returncode"] == 0
                                                     and result["fixed"]["collected"])})
        if result["fixed"]["collected"]:
            row["examples_run"] += 1
        if row["modules"][-1]["discriminates"]:
            row["discriminating"] += 1
    return row


def commits_touching_sources(clone: pathlib.Path, old: str, new: str) -> list[dict[str, Any]]:
    """Every real commit between two releases that changes a source file -- whether or not it ships tests.

    `witness.candidate_commits` deliberately keeps only commits that change a source AND a test, because its
    job is to find a specification. This module's job is the complement: the work that ships no spec at all.
    """
    log = _git("log", "--format=COMMIT|%H|%s", "--name-only", "%s..%s" % (old, new), cwd=clone)
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in log.splitlines():
        if line.startswith("COMMIT|"):
            if current:
                records.append(current)
            _, sha, message = line.split("|", 2)
            current = {"sha": sha, "message": message, "files": []}
        elif line.strip() and current is not None:
            current["files"].append(line.strip())
    if current:
        records.append(current)
    found: list[dict[str, Any]] = []
    for record in records:
        sources = [f for f in record["files"]
                   if f.endswith(".py") and "/tests/" not in f and not f.startswith("tests/")
                   and not pathlib.PurePosixPath(f).name.startswith("test_")]
        tests = [f for f in record["files"]
                 if f.endswith(".py") and ("/tests/" in f or pathlib.PurePosixPath(f).name.startswith("test_"))]
        if sources:
            found.append({"sha": record["sha"], "message": record["message"],
                          "files": record["files"], "sources": sources, "tests": tests})
    return found


def pins_for_commit(clone: pathlib.Path, commit: Mapping[str, Any], work: pathlib.Path) -> dict[str, Any]:
    """Both states of one real commit, the same probes on both, and only the differences that are stable."""
    parent_tree, note_parent = witness.materialise(clone, _git("rev-parse", "%s^" % commit["sha"],
                                                              cwd=clone).strip(), work)
    fixed_tree, note_fixed = witness.materialise(clone, commit["sha"], work, suffix="-pin")
    record: dict[str, Any] = {"commit": commit["sha"], "message": commit["message"][:90],
                              "sources": list(commit["sources"]), "tests_in_commit": bool(commit["tests"])}
    if parent_tree is None or fixed_tree is None:
        record["state"] = "NO_TREE"
        record["detail"] = note_parent or note_fixed
        return record

    rows: list[dict[str, Any]] = []
    for relative in commit["sources"]:
        if not relative.endswith(".py"):
            continue
        parent_file, fixed_file = parent_tree / relative, fixed_tree / relative
        if not parent_file.is_file() or not fixed_file.is_file():
            continue
        parts = relative[:-3].split("/")
        while parts and parts[0] in ("src", "lib"):
            parts = parts[1:]
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        module = ".".join(parts)
        source_text = fixed_file.read_text(encoding="utf-8", errors="replace")
        offered = public_callables(source_text, parts)
        vocabulary = ARG_TOKENS + tuple(module_literals(source_text))
        if not offered:
            rows.append({"module": module, "state": "NOTHING_PUBLIC_TO_PROBE"})
            continue
        calls: list[dict[str, Any]] = []
        for item in offered:
            for token in vocabulary:
                calls.append({"module": module, "function": item["function"],
                              "args": [token] * item["required"]})
        before = probe(parent_tree, calls)
        after = probe(fixed_tree, calls)
        repeat = after
        pairs = []
        for index, call in enumerate(calls):
            parent_outcome = before[index] if index < len(before) else {"outcome": "MISSING"}
            fixed_outcome = after[index] if index < len(after) else {"outcome": "MISSING"}
            again = repeat[index] if index < len(repeat) else {"outcome": "MISSING"}
            stable = bool(fixed_outcome.get("stable")) and fixed_outcome.get("outcome") in ("RETURNED",
                                                                                            "RAISED")
            differs = _signature(fixed_outcome) != _signature(parent_outcome)
            pairs.append({"call": call, "parent": parent_outcome, "fixed": fixed_outcome,
                          "stable": stable, "differs": differs,
                          "pin": bool(stable and differs and parent_outcome.get("outcome") in ("RETURNED",
                                                                                               "RAISED"))})
        rows.append({"module": module,
                     "callables": [item["function"] for item in offered],
                     "calls": len(calls),
                     "importable_at_fixed": sum(1 for item in after if item.get("outcome") != "IMPORT_FAILED"),
                     "pins": [item for item in pairs if item["pin"]],
                     "differences_unstable": sum(1 for item in pairs if item["differs"] and not item["stable"])})
    record["modules"] = rows
    record["doctests"] = doctest_checkability(clone, commit, work, parent_tree, fixed_tree)
    record["pins"] = sum(len(row.get("pins", [])) for row in rows)
    record["modules_probed"] = sum(1 for row in rows if row.get("calls"))
    if not record["modules_probed"]:
        record["state"] = "NOTHING_PROBEABLE"
    elif record.get("doctests", {}).get("discriminating"):
        record["state"] = "CHECKABLE_BY_THE_ARTIFACT'S_OWN_EXAMPLES"
    elif record["pins"]:
        record["state"] = "CHECKABLE_WITHOUT_ANY_TEST"
    else:
        record["state"] = "NO_DIFFERENCE_VISIBLE_FROM_THE_PUBLIC_SURFACE"
    return record


def run_corpus(cache: pathlib.Path, work: pathlib.Path, limit: int = 14,
               only_untested: bool = True) -> dict[str, Any]:
    """Real commits only. `only_untested` is the share the tree's own instrument called unguarded."""
    states: dict[str, int] = {"commits": 0, "with_tests": 0, "untested": 0, "probed": 0,
                              "checkable": 0, "pins": 0}
    rows: list[dict[str, Any]] = []
    for repo, old, new in witness.CORPUS_REPOS:
        if states["commits"] >= limit:
            break
        clone = witness.fetch(repo, old, new, cache)
        if clone is None:
            continue
        for commit in commits_touching_sources(clone, old, new):
            if states["commits"] >= limit:
                break
            states["commits"] += 1
            if commit["tests"]:
                states["with_tests"] += 1
                if only_untested:
                    continue
            else:
                states["untested"] += 1
            row = pins_for_commit(clone, commit, work)
            row["repo"] = repo
            rows.append(row)
            if row.get("modules_probed"):
                states["probed"] += 1
            if row.get("pins"):
                states["checkable"] += 1
                states["pins"] += row["pins"]
    return {"states": states, "commits": rows}


def _headline(report: Mapping[str, Any]) -> str:
    st = report["states"]
    share = (st.get("checkable", 0) / st["untested"]) if st.get("untested") else 0.0
    return (
        "%d real commits were taken at both states. %d changed code under test and shipped their own tests; "
        "%d changed code and shipped none -- work that has no mechanical postcondition of its own. Of those, "
        "%d could be driven through the module's own public surface and %d yielded at least one STABLE "
        "differential pin: behaviour that is reproducible at the fixed state and different at the parent. "
        "That is %.1f%% of the unguarded work converted into a check that exists without anybody writing a "
        "test -- a regression pin, never a proof of intent. The remaining %.1f%% could not be converted by "
        "anything the artifact already contains, and that is the point: behaviour changes are input-specific, "
        "so the DISCRIMINATING INPUT is itself knowledge. It arrives with a test, with a demonstration, or "
        "with a stated intent -- and no amount of experience, search, synthesis or verification manufactures "
        "it. That input is the bottleneck."
        % (st.get("commits", 0), st.get("with_tests", 0), st.get("untested", 0), st.get("probed", 0),
           st.get("checkable", 0), 100.0 * share, 100.0 * (1.0 - share)))


def measure(corpus: Mapping[str, Any] | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "the_law": ("C = CHECKABLE SHARE, and every other term is a multiplier on it: "
                    "P(solved) = C x (IN-GRAMMAR + SYNTHESISABLE + MEMORISABLE) x VERIFICATION. "
                    "Learning enlarges only MEMORISABLE, which is 4.814% of real fixes; it leaves C alone."),
        "external_confirmation": {
            "paper": "arXiv 2607.18057 (July 2026), 4,882 agent-authored PRs",
            "existing_tests_cover_changed_python_lines": 0.270,
            "python_prs_with_no_changed_line_executed": 0.648,
            "verification_bottleneck": ("'the verification bottleneck is now the center of the workflow' "
                                        "(Nov 2026 industry analysis); Stanford CS329A (Aug 2026): 'verification "
                                        "is the bottleneck for self-improvement'"),
            "self_grading_is_not_verification": ("Stack Overflow, 13 Nov 2026: of 1,000 AI-authored unit tests "
                                                 "audited, 9.6% were useful verification checks"),
        },
        "in_tree_prior": {
            "refuse_share_of_real_commits": 0.7142857142857143,
            "memorisable_share_of_real_fixes": 0.04814,
            "pool_is_badly_populated": "canonical/verification/OBSERVATIONAL_POOL_IS_EMPTY_BY_CONSTRUCTION_20261116_V1.json",
            "reach_ceiling": "canonical/verification/REACH_OF_THE_GRAMMAR_20261116_V1.json",
            "witness_inversion_refusals": "canonical/verification/WITNESS_INVERSION_20261116_V1.json",
        },
        "states": {"commits": 0, "with_tests": 0, "untested": 0, "probed": 0, "checkable": 0, "pins": 0},
        "commits": [],
    }
    if corpus is None:
        report["corpus"] = ("not fetched in this run: the clone cache is absent and no network measurement "
                            "was taken. The constructor is tested offline; the corpus number is producer-run "
                            "and pinned by commit in the receipt.")
        return report
    report.update(corpus)
    report["states"] = corpus["states"]
    report["what_this_shows"] = _headline(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="How much unguarded real work has a postcondition that can be constructed without a test?")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--cache", default="/tmp/pins/cache")
    parser.add_argument("--work", default="/tmp/pins/work")
    parser.add_argument("--limit", type=int, default=14)
    parser.add_argument("--include-tested", action="store_true")
    ns = parser.parse_args(argv)
    corpus = None
    if ns.corpus:
        corpus = run_corpus(pathlib.Path(ns.cache), pathlib.Path(ns.work), limit=ns.limit,
                            only_untested=not ns.include_tested)
    report = measure(corpus)
    print(json.dumps({key: report[key] for key in ("schema", "states") if key in report}, indent=1))
    if "what_this_shows" in report:
        print(report["what_this_shows"])
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("written:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
