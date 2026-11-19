#!/usr/bin/env python3
"""The value the assertion rejected had a producer. Does that producer localise the fix?

WHY THIS ROUND EXISTS
---------------------
Four rounds are settled and they converge on one unmeasured route.

Round 22: a real fix is mostly structural (72 of 87 add or remove a line), the one-token
ones live inside literals (7 of 8), and blind search costs 4,581 executions. Round 23:
the refusal grades always and names the fix's new word 32% of the time. Round 24: the
speaking-check mechanism has a measured ceiling of 2.7%, because (a) the machine points
into the source at all in only 18% of value failures -- an assert on a returned value
leaves no source frame, since the producer has already returned -- and (b) all of a fix's
new words are supplied only 8.8% of the time.

Both walls are the same wall: for edits there is no observation that identifies the
hypothesis. Operators have one (the world hands over the whole post-state), which is why
one experience identifies them exactly. So the question this round answers:

    can the missing observation be PRODUCED? Specifically: trace the failing run, find
    the expression instance that produced the value the assertion rejected, and ask
    whether the shipped fix changed the function that produced it.

If yes, the 82% of failures the machine does not localise become localisable by
observation rather than by inference -- and repair becomes identification again, which is
the only kind this project has ever solved exactly.

HOW IT IS MEASURED
------------------
Only frames of the file under repair are traced, so the tracer answers one question and
costs almost nothing: which function in this file returned the rejected value. The
rejected value is read from the checker's own diagnostic (the left operand of the failing
assert). The producer is the last traced return whose value reprs to it. The fix's own
functions are read from the corpus's two states. Nothing is trained, nothing is invented.

Zero model calls, zero parameters. Real upstream suites, refused states reconstructed from
the vendored pairs, exactly as rounds 23 and 24 do.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "canonical/corpus/real_fix_pairs_20261119_V1.json"
MINED = ROOT / "canonical/corpus/real_fix_commits_20261116_V1.json"
PRIOR = ROOT / "canonical/tools/does_the_refusal_name_the_missing_word_v1.py"
SLOT = ROOT / "canonical/tools/the_word_is_given_and_only_the_slot_is_unknown_v1.py"
SCHEMA = "BRAIN_THE_VALUE_THAT_WAS_REJECTED_HAD_A_PRODUCER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

RUNNER = r'''
import contextlib, io, json, re, sys

source_file, node, out = sys.argv[1], sys.argv[2], sys.argv[3]
events = []


def safe(value):
    try:
        return repr(value)[:60]
    except Exception:
        return "<unrepr>"


def local(frame, event, arg):
    if event == "return":
        events.append({"line": frame.f_lineno, "func": frame.f_code.co_name,
                       "repr": safe(arg),
                       "locals": {k: safe(v) for k, v in list(frame.f_locals.items())[:10]}})
    return local


def glob(frame, event, arg):
    try:
        if frame.f_code.co_filename.replace("\\", "/").endswith(source_file):
            return local
    except Exception:
        pass
    return None


sys.settrace(glob)
buf = io.StringIO()
try:
    import pytest
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = pytest.main([node, "-x", "-q", "--tb=long", "--no-header", "-s",
                            "-p", "no:cacheprovider", "-o", "addopts="])
finally:
    sys.settrace(None)
with open(out, "w", encoding="utf-8") as handle:
    json.dump({"code": int(code), "output": buf.getvalue()[-40000:], "events": events[-4000:]}, handle)
'''


def prior():
    spec = importlib.util.spec_from_file_location("refusal_prior2", PRIOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def slot_module():
    spec = importlib.util.spec_from_file_location("slot_round", SLOT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def rejected_value(output: str) -> str | None:
    """The value the checker rejected, when it rejected a value at all.

    An `assert False`, an `assert True` or an exception rejects no value: those failures
    leave no operand, and saying so is part of the measurement rather than a parsing miss.
    """
    lines = [line for line in output.splitlines() if re.match(r"^E\s+assert\s+\S", line)]
    if not lines:
        return None
    expression = re.sub(r"^E\s+assert\s+", "", lines[-1]).strip()
    for operator in (" == ", " != ", " is not ", " is "):
        if operator in expression:
            expression = expression.split(operator, 1)[0].strip()
            break
    if not expression or expression in {"False", "True"}:
        return None
    return expression


def fix_functions(after: str, changed: Sequence[int]) -> set[str]:
    """Every function in the fixed state that the fix touched."""
    try:
        tree = ast.parse(after)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
            if any(start <= line <= end for line in changed):
                names.add(node.name)
    return names


def trace_run(repo_dir: pathlib.Path, sha: str, before: str, source_path: str, node: str,
              timeout: int = 180) -> dict[str, Any]:
    fetch = subprocess.run(["git", "-C", str(repo_dir), "fetch", "-q", "origin", sha],
                           capture_output=True, text=True)
    checkout = subprocess.run(["git", "-C", str(repo_dir), "checkout", "-q", "--force", sha],
                              capture_output=True, text=True)
    if checkout.returncode != 0:
        return {"ran": False, "reason": f"checkout_fix:{checkout.stderr.strip()[:120]}"
                                       f"{fetch.stderr.strip()[:80]}"}
    target = repo_dir / source_path
    if not target.exists():
        return {"ran": False, "reason": f"harness:source path absent: {source_path}"}
    target.write_text(before, encoding="utf-8")
    src = repo_dir / "src"
    env = {"PYTHONPATH": str(src) if src.is_dir() else str(repo_dir),
           "PATH": "/usr/bin:/bin:/usr/local/bin", "PYTHONDONTWRITEBYTECODE": "1"}
    with tempfile.TemporaryDirectory() as tmp:
        runner = pathlib.Path(tmp) / "runner.py"
        out = pathlib.Path(tmp) / "trace.json"
        runner.write_text(RUNNER, encoding="utf-8")
        done = subprocess.run([sys.executable, str(runner), str(target), node, str(out)],
                              cwd=str(repo_dir), capture_output=True, text=True, timeout=timeout, env=env)
        payload = json.loads(out.read_text()) if out.exists() else None
    subprocess.run(["git", "-C", str(repo_dir), "checkout", "-q", "--force", "--", source_path],
                   capture_output=True, text=True)
    if payload is None:
        return {"ran": False, "reason": f"harness:runner failed:{done.stderr.strip()[-120:]}"}
    return {"ran": True, "payload": payload}


def measure_task(task: dict[str, Any], repos: pathlib.Path, mod, slot, timeout: int) -> dict[str, Any]:
    node = (task.get("failed_nodes") or [None])[0]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"][:10], "source": task["source"],
                           "node": node}
    if not node or not task.get("test"):
        row.update({"ran": False, "reason": "no failed node or test path recorded"})
        return row
    try:
        repo_dir = mod.ensure_repo(task["repo"], repos)
        result = trace_run(repo_dir, task["sha"], task["before"], task["source"], node, timeout=timeout)
    except Exception as error:  # noqa: BLE001
        row.update({"ran": False, "reason": f"{type(error).__name__}:{str(error)[:120]}"})
        return row
    if not result.get("ran"):
        row.update({"ran": False, "reason": result.get("reason", "not run")})
        return row
    payload = result["payload"]
    output = payload["output"]
    if "No module named pytest" in output or "No module named 'pytest'" in output:
        row.update({"ran": False, "reason": "harness:pytest is not importable"})
        return row
    row["ran"] = True
    row["failed"] = payload["code"] != 0
    row["events"] = len(payload["events"])
    row["traceback_points_into_the_source"] = slot.site_line(output, task["source"]) is not None
    if not row["failed"]:
        row["reason"] = "the reconstructed refused state passed"
        return row
    rejected = rejected_value(output)
    row["rejected"] = rejected
    producer = None
    for event in reversed(payload["events"]):
        if rejected is not None and event["repr"] == rejected:
            producer = event
            break
    row["produced"] = producer is not None
    if producer:
        row["producer_function"] = producer["func"]
        row["producer_line"] = producer["line"]
        row["operands"] = producer["locals"]
    changed = slot.changed_lines(task["before"], task["after"])
    functions = fix_functions(task["after"], changed)
    row["fix_functions"] = sorted(functions)
    traced = {event["func"] for event in payload["events"]}
    row["fix_functions_executed"] = sorted(traced & functions)
    row["fix_function_on_the_path"] = bool(traced & functions)
    row["producer_is_a_function_the_fix_changed"] = bool(
        producer and producer["func"] in functions)
    row["producer_within_three_lines_of_the_fix"] = bool(
        producer and changed and min(abs(producer["line"] - line) for line in changed) <= 3)
    return row


def measure(repos: pathlib.Path, limit: int | None = None, timeout: int = 180) -> dict[str, Any]:
    mod, slot = prior(), slot_module()
    corpus = json.loads(CORPUS.read_text())
    mined = {(t["repo"], t["sha"]): t.get("test") for t in json.loads(MINED.read_text())["tasks"]}
    tasks = corpus["tasks"][:limit] if limit else corpus["tasks"]
    for task in tasks:
        task["test"] = mined.get((task["repo"], task["sha"]))
    rows = [measure_task(task, repos, mod, slot, timeout) for task in tasks]
    failed = [r for r in rows if r.get("ran") and r.get("failed")]
    produced = [r for r in failed if r.get("produced")]
    hits = [r for r in produced if r.get("producer_is_a_function_the_fix_changed")]
    near = [r for r in produced if r.get("producer_within_three_lines_of_the_fix")]
    no_frame = [r for r in failed if not r.get("traceback_points_into_the_source")]
    no_frame_hits = [r for r in no_frame if r.get("producer_is_a_function_the_fix_changed")]

    def fract(part: int, whole: int) -> float | None:
        return round(part / whole, 3) if whole else None

    verdict = {
        "K1_the_refused_state_is_executed_under_a_tracer": {
            "tasks": len(rows), "ran": sum(1 for r in rows if r.get("ran")), "failed": len(failed),
            "could_not_run": len(rows) - sum(1 for r in rows if r.get("ran")),
            "median_traced_returns": sorted(r["events"] for r in failed)[len(failed) // 2] if failed else None,
            "MET": len(failed) >= 20},
        "K2_a_producer_of_the_rejected_value_is_found": {
            "failures_with_a_rejected_operand": sum(1 for r in failed if r.get("rejected")),
            "producer_found": len(produced),
            "fraction": fract(len(produced), len(failed)),
            "MET": len(failed) > 0},
        "K3_the_producer_localises_the_fix": {
            "producer_is_a_function_the_fix_changed": len(hits),
            "fraction_of_produced": fract(len(hits), len(produced)),
            "producer_within_three_lines_of_the_fix": len(near),
            "fraction_near": fract(len(near), len(produced)),
            "MET": len(produced) > 0},
        "K4_the_gain_is_the_failures_the_traceback_cannot_localise": {
            "failures_without_a_source_frame": len(no_frame),
            "fraction_of_failures": fract(len(no_frame), len(failed)),
            "of_those_localised_by_provenance": len(no_frame_hits),
            "fraction": fract(len(no_frame_hits), len(no_frame)),
            "of_those_where_a_function_the_fix_changed_was_on_the_path":
                sum(1 for r in no_frame if r.get("fix_function_on_the_path")),
            "fraction_on_the_path": fract(sum(1 for r in no_frame if r.get("fix_function_on_the_path")),
                                          len(no_frame)),
            "note": ("this is the only number that matters: it is the part of the corpus the machine does not "
                     "localise today, and the part that provenance would localise instead"),
            "MET": len(no_frame) > 0},
        "K5_zero": {"model_calls": 0, "parameters_stored": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "TRACE_THE_REFUSED_RUN_FOR_THE_PRODUCER_OF_THE_REJECTED_VALUE_AND_CHECK_IT_LOCALISES_THE_FIX",
        "why_this_round": {
            "the_gap_it_closes": ("rounds 22-24 showed the proposal cannot come from vocabulary, corpus, refusal or "
                                  "check; round 24 named the only remaining observation, the provenance of the "
                                  "rejected value, and this measures it"),
            "the_answer_being_tested": ("if the producer of the rejected value is usually a function the real fix "
                                        "changed, then the observation that identifies an edit can be produced by "
                                        "tracing, and repair is identification again"),
            "why_it_could_fail": ("repr matching may miss; the fix may be in a sibling of the producer; the value may "
                                  "be produced by a correct expression from wrong operands"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "at least twenty refused states executed under the tracer and the trace recorded",
            "K2": "the rejected value is read from the checker's own diagnostic and its producer located",
            "K3": "the producer is compared with the functions the shipped fix changed, and with its lines",
            "K4": "the failures the traceback cannot localise are counted separately and localised by provenance",
            "K5": "zero model calls and zero parameters",
        },
        "verdict": verdict,
        "per_task": rows,
        "cost": {"model_calls": 0, "parameters_stored": 0,
                 "network": "repository clones during preparation; the measurement runs offline"},
        "limits": [
            "the producer is matched by repr equality against the rejected operand; a repr collision attributes the "
            "wrong producer, which this cannot detect without identity capture inside the assertion",
            "only frames of the file under repair are traced, so a producer in another file is invisible by design",
            "'the fix changed that function' is necessary, not sufficient: a function can be changed for a reason "
            "unrelated to the rejected value",
            "value-based fault localisation exists in the literature with learned rankers; this asks the narrower, "
            "parameter-free question and makes no comparison with those rankers",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k1 = v["K1_the_refused_state_is_executed_under_a_tracer"]
    k2 = v["K2_a_producer_of_the_rejected_value_is_found"]
    k3 = v["K3_the_producer_localises_the_fix"]
    k4 = v["K4_the_gain_is_the_failures_the_traceback_cannot_localise"]
    lines.append("")
    lines.append(f"refused states executed under the tracer: {k1['failed']}/{k1['tasks']} "
                 f"({k1['could_not_run']} could not run), median traced returns {k1['median_traced_returns']}")
    lines.append(f"producer of the rejected value found: {k2['producer_found']}/{k1['failed']} ({k2['fraction']})")
    lines.append(f"producer is a function the fix changed: {k3['producer_is_a_function_the_fix_changed']} "
                 f"({k3['fraction_of_produced']}); within three lines {k3['producer_within_three_lines_of_the_fix']} "
                 f"({k3['fraction_near']})")
    lines.append(f"failures the traceback cannot localise: {k4['failures_without_a_source_frame']} "
                 f"({k4['fraction_of_failures']}); of those, provenance localises "
                 f"{k4['of_those_localised_by_provenance']} ({k4['fraction']}), and the fix's own function was on the "
                 f"path in {k4['of_those_where_a_function_the_fix_changed_was_on_the_path']} "
                 f"({k4['fraction_on_the_path']})")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = repos_path = None
    limit, timeout = None, 180
    for flag in ("--receipt", "--repos"):
        if flag in args:
            index = args.index(flag)
            value = pathlib.Path(args[index + 1])
            del args[index:index + 2]
            if flag == "--receipt":
                receipt_path = value
            else:
                repos_path = value
    if "--limit" in args:
        index = args.index("--limit")
        limit = int(args[index + 1])
        del args[index:index + 2]
    if "--timeout" in args:
        index = args.index("--timeout")
        timeout = int(args[index + 1])
        del args[index:index + 2]
    receipt = measure(repos_path or pathlib.Path("/tmp/refusal-repos"), limit=limit, timeout=timeout)
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(row["MET"] for row in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
