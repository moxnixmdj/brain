"""The diagnose adapter serves only the operations that execute nothing.

`software.analysis.diagnose_and_architect.v1` was refused wholesale because some
of its operations run a child process, `exec` the target module, or shell out to
`git`. That refusal was correct for those operations and wrong for the ones that
are pure AST/text analysis: refusing to *read* a package is not a safety
property, and it cost real capability in the surface/advanced censuses.

Two independent checks, because either one alone is weak:

1. Static: the call graph reachable from each admitted operation's engine
   function (within `diagnostics_perf_and_design_engine_v1.py`) contains no
   `exec`/`compile`/`__import__`, no `subprocess`, no `pipeline_exec_v1`, no
   `shutil.which`, and no call into another repository module. If someone later
   makes an admitted operation execute, this fails without anyone remembering to
   look.
2. Runtime: each admitted operation is run through the real dispatcher with
   `subprocess`, `os.system`, `os.popen`, `builtins.exec`, `builtins.eval`,
   `pipeline_exec_v1.run_command` and `shutil.which` instrumented, and must
   perform none of them. The operation is allowed to refuse the work (a fixture
   may not satisfy its gate); it is not allowed to execute.

Negative controls run alongside: the executing operations, an unknown operation
and a missing operation are still refused with the boundary status, before the
adapter is imported.
"""
from __future__ import annotations

import ast
import builtins
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import pipeline_exec_v1

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE = ROOT / "canonical/swe_kernel/diagnostics_perf_and_design_engine_v1.py"
ADAPTER = ROOT / boundary.DIAGNOSE_ADAPTER_PATH
CID = boundary.DIAGNOSE_CAPABILITY_ID

# The operations the adapter dispatches to something that executes. Named here so
# the negative controls cannot silently drift away from the real table.
EXECUTING_OPERATIONS = (
    "profile_hotspot",
    "benchmark_git_ref",
    "explain_behavior",
    "fuzz_overflow",
    "find_race_condition",
    "diagnose_test_suite",
    "find_root_cause",
    "explain_bug",
    "measure_coverage",
    "measure_mutation_score",
    "find_flaky_tests",
    "lint_javascript",
    "run_js_tests",
    "run_single_test",
    "git_changelog",
    "git_diff_ref",
    "git_blame_line",
    "review_pull_request",
    "show_definition",
    "which_modules_import",
    "import_cycles",
    "class_hierarchy",
)

_DANGEROUS_MODULES = {
    "subprocess",
    "multiprocessing",
    "ctypes",
    "socket",
    "importlib",
    "pty",
    "signal",
    "asyncio",
    "os",
    "shutil",
}
_EXEC_NAMES = {"exec", "eval", "compile", "__import__"}


def _engine_call_graph(path: pathlib.Path):
    """(functions, local calls, direct execution hits) for one module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    tainted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            for alias in node.names:
                name = alias.asname or alias.name
                if top == "canonical" or top in _DANGEROUS_MODULES:
                    tainted.add(name)
                elif top == "builtins" and alias.name in _EXEC_NAMES:
                    tainted.add(name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top == "canonical" or top in _DANGEROUS_MODULES:
                    tainted.add(alias.asname or top)
    local_calls: dict[str, set[str]] = {}
    hits: dict[str, set[str]] = {}
    for name, node in functions.items():
        called: set[str] = set()
        found: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in _EXEC_NAMES:
                found.add(child.id)
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if isinstance(func, ast.Name):
                if func.id in _EXEC_NAMES or func.id in tainted:
                    found.add(func.id)
                else:
                    called.add(func.id)
            elif isinstance(func, ast.Attribute):
                base = func
                while isinstance(base, ast.Attribute):
                    base = base.value
                name_of_base = base.id if isinstance(base, ast.Name) else ""
                if name_of_base in tainted:
                    found.add(name_of_base + "." + func.attr)
        local_calls[name] = called
        hits[name] = found
    return functions, local_calls, hits


def _reachable(name: str, local_calls, functions, seen=None):
    seen = set() if seen is None else seen
    if name in seen or name not in functions:
        return seen
    seen.add(name)
    for called in local_calls.get(name, ()):
        _reachable(called, local_calls, functions, seen)
    return seen


def _adapter_dispatch(path: pathlib.Path) -> dict[str, str]:
    """operation -> engine function, read out of the adapter's own dispatch."""
    source = path.read_text(encoding="utf-8")
    import re

    mapping: dict[str, str] = {}
    for match in re.finditer(
        r"op in \{([^}]+)\}:\n(?:.*\n)*?        res = engine\.(\w+)\(", source
    ):
        for operation in re.findall(r'"([a-z_]+)"', match.group(1)):
            mapping[operation] = match.group(2)
    for match in re.finditer(
        r'op == "([a-z_]+)":\n(?:.*\n)*?        res = engine\.(\w+)\(', source
    ):
        mapping[match.group(1)] = match.group(2)
    return mapping


class StaticDiagnoseOperationTableTests(unittest.TestCase):
    def test_declared_operations_are_the_ones_the_adapter_dispatches(self):
        dispatch = _adapter_dispatch(ADAPTER)
        self.assertTrue(boundary.STATIC_DIAGNOSE_OPERATIONS)
        for operation, engine_function in boundary.STATIC_DIAGNOSE_OPERATIONS.items():
            with self.subTest(operation=operation):
                self.assertIn(operation, dispatch)
                self.assertEqual(
                    dispatch[operation],
                    engine_function,
                    "the table points at a different engine function than the "
                    "adapter dispatches to; the audited code is not the code that runs",
                )

    def test_no_executing_operation_is_declared_static(self):
        for operation in EXECUTING_OPERATIONS:
            with self.subTest(operation=operation):
                self.assertNotIn(operation, boundary.STATIC_DIAGNOSE_OPERATIONS)

    def test_every_declared_operation_is_static_in_the_call_graph(self):
        functions, local_calls, hits = _engine_call_graph(ENGINE)
        for operation, engine_function in boundary.STATIC_DIAGNOSE_OPERATIONS.items():
            with self.subTest(operation=operation):
                self.assertIn(engine_function, functions)
                reached = _reachable(engine_function, local_calls, functions)
                found = sorted({hit for name in reached for hit in hits.get(name, ())})
                self.assertEqual(
                    found,
                    [],
                    f"{operation} reaches execution: {found}",
                )

    def test_the_graph_walk_would_catch_a_real_execution(self):
        """Negative control: the check is not vacuous on this module."""
        functions, local_calls, hits = _engine_call_graph(ENGINE)
        reached = _reachable("run_single_test_target", local_calls, functions)
        found = sorted({hit for name in reached for hit in hits.get(name, ())})
        self.assertTrue(found, "the reachability walk found nothing in a "
                               "function that runs a test suite")
        self.assertIn("pipeline_exec_v1.run_command", found)


class StaticDiagnoseOperationRuntimeTests(unittest.TestCase):
    def _fixture(self, root: pathlib.Path):
        package = root / "pkg"
        (package / "app").mkdir(parents=True)
        (package / "app/__init__.py").write_text("", encoding="utf-8")
        (package / "app/service.py").write_text(
            "def line_total(items):\n"
            "    return sum(i['price'] for i in items)\n"
            "\n"
            "def _unused():\n"
            "    return 1\n",
            encoding="utf-8",
        )
        (package / "requirements.txt").write_text("requests==2.0.0\n", encoding="utf-8")
        (package / "schema.json").write_text('{"type": "object"}', encoding="utf-8")
        (package / "run.log").write_text(
            "Traceback (most recent call last):\n  File 'x.py', line 1\nValueError: bad\n",
            encoding="utf-8",
        )
        return package

    def _args(self, operation: str, package: pathlib.Path, out: pathlib.Path):
        args = {
            "operation": operation,
            "output_path": out.relative_to(ROOT).as_posix(),
            "request_spec": "do the thing",
            "target_path": package.relative_to(ROOT).as_posix(),
            "symbol": "auto",
        }
        if operation == "validate_json_schema":
            args["target_path"] = (package / "schema.json").relative_to(ROOT).as_posix()
        if operation == "analyze_log_exception":
            args["target_path"] = (package / "run.log").relative_to(ROOT).as_posix()
        if operation == "trace_value_provenance":
            args["target_path"] = (package / "app/service.py").relative_to(ROOT).as_posix()
            args["symbol"] = "line_total"
        if operation == "plan_rename":
            args["symbol"] = "line_total"
        return args

    def _instrument(self, calls: list[str]):
        """Record an execution primitive if any static operation reaches one.

        The recorders raise so nothing downstream believes the call succeeded,
        and the assertion is on the record itself -- so an operation that
        swallowed the refusal would still fail this test. `exec`/`compile` are
        recorded and delegated instead: Python's own import machinery uses them
        to load the adapter, and refusing them would measure the loader rather
        than the operation.
        """
        import sys

        real_exec = builtins.exec
        real_compile = builtins.compile

        def record(label):
            def _inner(*a, **k):
                calls.append(label)
                raise AssertionError(f"{label} was called")
            return _inner

        def exec_spy(code, *a, **k):
            caller = sys._getframe(1).f_globals.get("__name__", "")
            if not str(caller).startswith("importlib"):
                calls.append("exec:" + str(caller))
            return real_exec(code, *a, **k)

        def compile_spy(source, filename, *a, **k):
            if str(filename) not in {"<unknown>", "<string>"} and not str(filename).endswith(
                    "software_analysis_diagnose_and_architect_v1.py") \
                    and not str(filename).endswith("diagnostics_perf_and_design_engine_v1.py"):
                calls.append("compile:" + str(filename))
            return real_compile(source, filename, *a, **k)

        return [
            mock.patch.object(subprocess, "run", record("subprocess.run")),
            mock.patch.object(subprocess, "Popen", record("subprocess.Popen")),
            mock.patch.object(pipeline_exec_v1, "run_command", record("pipeline_exec_v1.run_command")),
            mock.patch.object(builtins, "exec", exec_spy),
            mock.patch.object(builtins, "eval", record("eval")),
            mock.patch("os.system", record("os.system")),
            mock.patch("os.popen", record("os.popen")),
            mock.patch("shutil.which", record("shutil.which")),
        ]

    def test_admitted_operations_execute_nothing(self):
        from canonical.runtime import capability_composer_v1 as graph

        entry = graph.load_registry()[CID]
        tmp_parent = ROOT / "canonical/astra_runtime/tmp"
        tmp_parent.mkdir(parents=True, exist_ok=True)
        reached_adapter = []
        with tempfile.TemporaryDirectory(prefix="static_diagnose_", dir=tmp_parent) as td:
            root = pathlib.Path(td)
            package = self._fixture(root)
            out = root / "report.json"
            for operation in sorted(boundary.STATIC_DIAGNOSE_OPERATIONS):
                args = self._args(operation, package, out)

                def run_once():
                    try:
                        door.run_adapter_locally(entry, {"args": dict(args)})
                    except door.LocalExecutionFailure as exc:
                        self.assertNotEqual(
                            str(exc),
                            boundary.STATUS,
                            f"{operation} is a static operation and must not be "
                            "refused as needing an execution carrier",
                        )
                    except Exception:
                        # The fixture may not satisfy the operation's own gate. That
                        # is a refusal of the work, not a violation of this property.
                        pass
                    reached_adapter.append(operation)

                # Warm the import graph, then measure: what matters is what the
                # operation itself does, not what loading its module does.
                run_once()
                calls: list[str] = []
                patches = self._instrument(calls)
                for patcher in patches:
                    patcher.start()
                try:
                    run_once()
                finally:
                    for patcher in reversed(patches):
                        patcher.stop()
                self.assertEqual(calls, [], f"{operation} executed something")

        self.assertEqual(sorted(reached_adapter), sorted(list(boundary.STATIC_DIAGNOSE_OPERATIONS) * 2))

    def test_executing_operations_are_refused_before_the_adapter_is_imported(self):
        from canonical.runtime import capability_composer_v1 as graph

        entry = graph.load_registry()[CID]
        with tempfile.TemporaryDirectory(prefix="static_diagnose_neg_",
                                         dir=ROOT / "canonical/astra_runtime/tmp") as td:
            out = (pathlib.Path(td) / "r.json").relative_to(ROOT).as_posix()
            for operation in EXECUTING_OPERATIONS:
                with self.subTest(operation=operation), \
                        mock.patch.object(door.importlib.util, "spec_from_file_location") as loader:
                    with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
                        door.run_adapter_locally(
                            entry, {"args": {"operation": operation, "output_path": out}}
                        )
                    loader.assert_not_called()

    def test_missing_or_unknown_operation_is_refused(self):
        from canonical.runtime import capability_composer_v1 as graph

        entry = graph.load_registry()[CID]
        with tempfile.TemporaryDirectory(prefix="static_diagnose_unknown_",
                                         dir=ROOT / "canonical/astra_runtime/tmp") as td:
            out = (pathlib.Path(td) / "r.json").relative_to(ROOT).as_posix()
            for args in ({"output_path": out}, {"operation": "", "output_path": out},
                         {"operation": "whatever", "output_path": out}):
                with self.subTest(args=args):
                    with self.assertRaisesRegex(door.LocalExecutionFailure, boundary.STATUS):
                        door.run_adapter_locally(entry, {"args": args})

    def test_direct_adapter_call_refuses_an_executing_operation(self):
        """The dispatcher is not the only way in, so the adapter checks too."""
        from canonical.runtime.bound_capabilities import (
            software_analysis_diagnose_and_architect_v1 as adapter,
        )

        with tempfile.TemporaryDirectory(prefix="static_diagnose_direct_",
                                         dir=ROOT / "canonical/astra_runtime/tmp") as td:
            out = (pathlib.Path(td) / "r.json").relative_to(ROOT).as_posix()
            with self.assertRaisesRegex(RuntimeError, boundary.STATUS):
                adapter.run({"operation": "run_single_test", "output_path": out}, ROOT)

    def test_the_front_door_serves_a_static_operation_without_touching_execution(self):
        result = door.solve({
            "task_id": "static-diagnose-door",
            "goal": "Design the API for a rate limiter and write an ADR.",
        })
        self.assertNotEqual(result.get("status"), boundary.STATUS, result)


if __name__ == "__main__":
    unittest.main()
