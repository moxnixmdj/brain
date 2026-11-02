"""The two file-fact rows answer without running anything, and without a shell.

The rows exist to answer ordinary questions in process, which is the whole point
of them: the requests they serve are the ones the door could only refuse with
``FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`` because nothing
was proposed, and a fix that answered them by spawning ``wc`` would just move the
refusal (a process needs a confinement this repository has not admitted).

So the no-execution property is not incidental hygiene -- it is what makes the
route legitimate. Two independent proofs, because either alone is weak:

1. **Reachability.** Read the adapters' source, build the call graph from their
   own module-level functions, and refuse the test if any node can reach a
   process API, ``eval``/``exec``, or a dynamic import. A docstring mentioning
   ``subprocess`` must not fail this, so only real call nodes count -- and a
   NEGATIVE CONTROL proves the walker can see a call when there is one.

2. **Runtime.** Replace ``subprocess.Popen``/``run``/``check_output``,
   ``os.system``, ``os.fork``, ``os.execv``, ``os.spawnv`` and ``builtins.exec``
   with functions that raise, then answer real questions against a real file.
   The answers must still be exact. A spy that is never armed proves nothing, so
   the control asserts the armed API raises when called directly.

usage:
  python3 -B canonical/tests/test_file_fact_adapters_never_execute_v1.py
"""
from __future__ import annotations

import ast
import builtins
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_composer_v1 as graph  # noqa: E402
from canonical.runtime.bound_capabilities import (  # noqa: E402
    file_command_view,
    file_line_count,
    file_stat,
    file_survey,
)

ADAPTERS = {
    "file_line_count": ROOT / "canonical/runtime/bound_capabilities/file_line_count.py",
    "file_stat": ROOT / "canonical/runtime/bound_capabilities/file_stat.py",
    "file_command_view": ROOT / "canonical/runtime/bound_capabilities/file_command_view.py",
    "file_survey": ROOT / "canonical/runtime/bound_capabilities/file_survey.py",
}

#: Names that mean "a process, a shell, or dynamic code".
FORBIDDEN_CALLS = {
    "system", "popen", "fork", "forkpty", "execv", "execve", "execvp", "execvpe",
    "execl", "execle", "execlp", "spawnv", "spawnve", "spawnvp", "spawnl",
    "posix_spawn", "posix_spawnp", "eval", "exec", "__import__", "compile",
    "run", "call", "check_call", "check_output", "Popen", "call_check_output",
    "import_module", "load_module", "system_popen",
}

#: Modules whose mere presence in an adapter is a process dependency.
FORBIDDEN_MODULES = {"subprocess", "ctypes", "multiprocessing", "pty", "shutil"}


def _calls_in(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                found.add(func.id)
            elif isinstance(func, ast.Attribute):
                found.add(func.attr)
    return found


def _reachable_calls(tree: ast.Module) -> tuple[set[str], dict[str, set[str]]]:
    """Every call reachable from any function defined in the module."""
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    edges = {name: _calls_in(node) for name, node in functions.items()}
    seen: set[str] = set()
    stack = list(functions)
    while stack:
        current = stack.pop()
        for called in edges.get(current, set()):
            if called in functions and called not in seen:
                seen.add(called)
                stack.append(called)
    calls: set[str] = set()
    for name in functions:
        calls |= edges[name]
    return calls, edges


def test_no_reachable_process_or_dynamic_code_call() -> None:
    for name, path in ADAPTERS.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls, edges = _reachable_calls(tree)
        bad = sorted(calls & FORBIDDEN_CALLS)
        assert not bad, "%s can call %s" % (name, bad)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        bad_modules = sorted(imported & FORBIDDEN_MODULES)
        assert not bad_modules, "%s imports %s" % (name, bad_modules)
        assert "run" in edges, "%s has no run() to inspect" % name
        # The adapter's own run() must be the only entry the registry needs.
        assert "run" in edges


def test_the_walker_sees_a_process_call_when_there_is_one() -> None:
    """Negative control: the AST test above is only meaningful if it can fail."""
    control = ast.parse(
        "import subprocess\n"
        "def helper(argv):\n"
        "    return subprocess.run(argv)\n"
        "def run(args, root):\n"
        "    return helper(['wc', '-l'])\n"
    )
    calls, _edges = _reachable_calls(control)
    assert "run" in calls, calls
    assert calls & FORBIDDEN_CALLS, calls


def _armed_spy(record: list[str]):
    """Every process API raises and records itself."""

    def boom(api: str):
        def _raise(*_a, **_k):
            record.append(api)
            raise AssertionError("PROCESS_API_CALLED:" + api)
        return _raise

    originals = {
        "subprocess.Popen": subprocess.Popen,
        "subprocess.run": subprocess.run,
        "subprocess.call": subprocess.call,
        "subprocess.check_call": subprocess.check_call,
        "subprocess.check_output": subprocess.check_output,
        "os.system": os.system,
        "builtins.exec": builtins.exec,
    }
    subprocess.Popen = boom("subprocess.Popen")
    subprocess.run = boom("subprocess.run")
    subprocess.call = boom("subprocess.call")
    subprocess.check_call = boom("subprocess.check_call")
    subprocess.check_output = boom("subprocess.check_output")
    os.system = boom("os.system")
    builtins.exec = boom("builtins.exec")
    for attr in ("fork", "execv", "execvp", "spawnv", "spawnvp"):
        if hasattr(os, attr):
            originals["os." + attr] = getattr(os, attr)
            setattr(os, attr, boom("os." + attr))
    return originals


def _disarm(originals) -> None:
    for dotted, value in originals.items():
        module_name, attr = dotted.split(".")
        module = {"subprocess": subprocess, "os": os, "builtins": builtins}[module_name]
        setattr(module, attr, value)


def test_the_armed_api_really_raises() -> None:
    """The spy is only evidence if it fires. Control for `test_answers_with_no_process`."""
    record: list[str] = []
    originals = _armed_spy(record)
    try:
        try:
            subprocess.run([sys.executable, "-c", "pass"], check=False)
        except AssertionError as exc:
            assert "PROCESS_API_CALLED:subprocess.run" in str(exc)
        else:  # pragma: no cover - the spy must fire
            raise AssertionError("THE_SPY_DID_NOT_FIRE")
    finally:
        _disarm(originals)
    assert record == ["subprocess.run"], record


def test_answers_with_no_process() -> None:
    record: list[str] = []
    originals = _armed_spy(record)
    try:
        with tempfile.TemporaryDirectory(dir=str(ROOT / "canonical/astra_runtime/tmp")) as tmp:
            base = pathlib.Path(tmp)
            target = base / "three.txt"
            target.write_text("alpha\nbeta\ngamma", encoding="utf-8")
            rel = target.relative_to(ROOT.resolve()).as_posix()

            counted = file_line_count.run({"path": rel}, ROOT)
            assert counted["line_count"] == 3, counted
            assert counted["newline_count"] == 2, counted
            assert counted["ends_with_newline"] is False

            statted = file_stat.run({"path": rel}, ROOT)
            assert statted["size_bytes"] == target.stat().st_size, statted
            assert statted["is_file"] is True
    finally:
        _disarm(originals)
    assert record == [], record


def test_the_command_view_answers_with_no_process() -> None:
    """The command-shaped rows must not answer by running the command.

    `sort`, `tac` and `cat` are programs. Answering with them would put the
    original refusal back one layer down -- the door would dispatch an adapter
    that spawns a process it has no confinement for -- so the armed spy is used
    on the command view exactly as on the two counters.
    """
    record: list[str] = []
    originals = _armed_spy(record)
    try:
        with tempfile.TemporaryDirectory(dir=str(ROOT / "canonical/astra_runtime/tmp")) as tmp:
            base = pathlib.Path(tmp)
            target = base / "u.txt"
            target.write_text("gamma\nalpha\nbeta\n", encoding="utf-8")
            rel = target.relative_to(ROOT.resolve()).as_posix()
            sorted_out = file_command_view.run({"command": "sort", "path": rel}, ROOT)
            assert sorted_out["answer"] == "alpha\nbeta\ngamma\n", sorted_out["answer"]
            reversed_out = file_command_view.run({"command": "tac", "path": rel}, ROOT)
            assert reversed_out["answer"] == "beta\nalpha\ngamma\n", reversed_out["answer"]
            cat_out = file_command_view.run({"command": "cat", "path": rel}, ROOT)
            assert cat_out["answer"] == "gamma\nalpha\nbeta\n", cat_out["answer"]
            # A closed vocabulary: a command it does not implement is refused, not
            # approximated. Measured control for the table itself.
            for bad in ({"command": "sed", "path": rel}, {"command": "rm", "path": rel},
                        {"command": "sort", "path": "-n"}):
                try:
                    file_command_view.run(bad, ROOT)
                except RuntimeError as exc:
                    assert "NOT_IMPLEMENTED" in str(exc) or "OPERANDS_REQUIRED" in str(exc), exc
                else:
                    raise AssertionError("the command view attempted %r" % (bad,))
    finally:
        _disarm(originals)
    assert record == [], record


def test_the_survey_answers_with_no_process() -> None:
    record: list[str] = []
    originals = _armed_spy(record)
    try:
        with tempfile.TemporaryDirectory(dir=str(ROOT / "canonical/astra_runtime/tmp")) as tmp:
            base = pathlib.Path(tmp)
            (base / "words.txt").write_text("apple banana banana\n", encoding="utf-8")
            (base / "sub").mkdir()
            rel = base.relative_to(ROOT.resolve()).as_posix()
            counted = file_survey.run(
                {"command": "word_frequency", "path": rel + "/words.txt"}, ROOT)
            assert counted["most_common_word"] == "banana", counted
            listed = file_survey.run({"command": "directory_list", "path": rel}, ROOT)
            assert sorted(listed["names"]) == ["sub", "words.txt"], listed["names"]
            searched = file_survey.run(
                {"command": "directory_search", "path": rel,
                 "goal": "Which files in %s contain banana?" % rel}, ROOT)
            assert [p.rsplit("/", 1)[-1] for p in searched["files_with_matches"]] == ["words.txt"], searched
            for bad in ({"command": "rm", "path": rel},
                        {"command": "directory_list", "path": rel + "/words.txt"}):
                try:
                    file_survey.run(bad, ROOT)
                except RuntimeError as exc:
                    assert "NOT_IMPLEMENTED" in str(exc) or "NOT_A_DIRECTORY" in str(exc), exc
                else:
                    raise AssertionError("the survey attempted %r" % (bad,))
    finally:
        _disarm(originals)
    assert record == [], record


def test_refusals_happen_before_any_read_of_the_outside_world() -> None:
    for module in (file_line_count, file_stat):
        try:
            module.run({"path": "/etc/passwd"}, ROOT)
        except RuntimeError as exc:
            assert "PATH_OUTSIDE_REPOSITORY" in str(exc), exc
        else:  # pragma: no cover - the refusal is the contract
            raise AssertionError("%s reached outside the repository" % module.__name__)
        try:
            module.run({"path": "canonical/astra_runtime/tmp/does_not_exist_%d" % os.getpid()}, ROOT)
        except RuntimeError as exc:
            assert "PATH_NOT_FOUND" in str(exc) or "PATH_NOT_A_REGULAR_FILE" in str(exc), exc
        else:  # pragma: no cover
            raise AssertionError("%s answered about a missing path" % module.__name__)


def test_the_registry_rows_are_dispatchable_and_declare_what_they_return() -> None:
    """A row that cannot be dispatched is not a capability, however good its adapter.

    Written after a measured defect in this very change: the rows were added
    without an ``entrypoint``, so ``admit`` refused them with
    EXECUTABLE_ENTRY_INCOMPLETE and the size question -- which had just started
    passing -- went back to being refused, with nothing in the adapter to blame.
    The field is cheap to forget and expensive to debug, so it is checked here
    alongside the fields the adapter actually returns.
    """
    from canonical.runtime import capability_selection_retrieval_v1 as selection

    registry = graph.load_registry()
    world = pathlib.Path(tempfile.mkdtemp(dir=str(ROOT / "canonical/astra_runtime/tmp")))
    try:
        (world / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        rel = (world / "a.txt").relative_to(ROOT.resolve()).as_posix()
        for cid, module in (("file.line_count.v1", file_line_count),
                            ("file.stat.v1", file_stat),
                            ("file.contents.v1", file_command_view),
                            ("file.sorted.v1", file_command_view),
                            ("file.reversed.v1", file_command_view),
                            ("file.word_frequency.v1", file_survey),
                            ("file.directory_listing.v1", file_survey),
                            ("file.directory_search.v1", file_survey)):
            entry = registry[cid]
            assert entry.get("entrypoint") == "run", (cid, entry.get("entrypoint"))
            assert callable(getattr(module, entry["entrypoint"])), cid
            assert selection._is_executable(entry) is True, cid
            assert entry.get("status") == "VERIFIED_BOUND_CAPABILITY", cid
            assert entry.get("incremental_spend_usd") == 0, cid
            assert entry.get("read_only") is True, cid
            declared = set(entry.get("result_fields") or ())
            call = {"path": str(world.relative_to(ROOT.resolve()).as_posix()) if cid in (
                "file.directory_listing.v1", "file.directory_search.v1") else rel}
            if module is file_command_view:
                call["command"] = entry["computes_command"]["argvs"][0][0]
            elif module is file_survey:
                call["command"] = entry["action_template"]["args"]["command"]
                if cid == "file.directory_search.v1":
                    call["goal"] = "Which files in %s contain alpha?" % call["path"]
            returned = set(module.run(call, ROOT))
            assert returned <= declared, (cid, sorted(returned - declared))
    finally:
        import shutil
        shutil.rmtree(world, ignore_errors=True)


def main() -> int:
    tests = [value for key, value in sorted(globals().items())
             if key.startswith("test_") and callable(value)]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        else:
            print("ok   %s" % test.__name__)
    print("\n%d/%d passed" % (len(tests) - failures, len(tests)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
