#!/usr/bin/env python3
"""Every VERIFIED bound capability must be reachable: its source type satisfiable here, its adapter findable.

Two independent defects, both measured, both making a declared-and-present capability unreachable
on every path.

1. SOURCE TYPE.  The pinned kernel resolved dependencies for ``pypi``, ``npm``, ``apt``,
   ``git_source_tree``, ``python_stdlib`` and ``system_tool`` and raised
   ``BOUND_CAPABILITY_SOURCE_UNSUPPORTED`` for anything else.  Five registry source types fell
   outside that list -- ``python_stdlib_composition`` (6 entries), ``brain_native_deterministic``
   (4), ``brain_native_deterministic_composition`` (4), ``brain_bound_system_tool`` (1),
   ``brain_owned_python_composition`` (1).  Every one of those 16 entries declares a real adapter
   file and an ``invoke_capability`` template, so 16 of 72 -- 22% of the bound surface -- could
   never execute, including the whole AST software-repair family.  A composition of stdlib modules
   is still a stdlib dependency; a brain-owned Python adapter has no external dependency at all; a
   brain-bound system tool is a system tool whose executable is named by ``engine``.

2. ADAPTER PATH.  The loader looked for ``canonical/runtime/bound_capabilities/<adapter_module>.py``
   unconditionally.  One entry -- ``python.task.acceptance.measured.objective.v1``, the only one of
   72 that declares its own ``source.adapter_path`` -- keeps its adapter under
   ``canonical/runtime/``, and that file exists.  The declaration was ignored, so the capability was
   refused with ``BOUND_CAPABILITY_ADAPTER_MISSING`` while its adapter sat on disk.

Both repairs fail closed: the declared path must be relative, stay inside ``canonical/runtime/``,
name exactly the declared module, and exist.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

REGISTRY = json.loads((RUNTIME / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))
CAPS = REGISTRY["capabilities"]

_spec = importlib.util.spec_from_file_location("astra_runtime_source_types_v1", RUNTIME / "astra_runtime.py")
runtime = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = runtime
_spec.loader.exec_module(runtime)

# A real, tiny broken program with a failing test, so the repair loop has something honest to do.
WORK = ROOT / "astra_runtime" / "tmp" / "source_type_reachability_probe"


def _write_probe():
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (WORK / "test_calc.py").write_text(
        "import unittest, calc\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(calc.add(2, 3), 5)\n",
        encoding="utf-8",
    )
    return WORK


class SourceTypeReachabilityTests(unittest.TestCase):
    def test_the_five_composite_types_are_locally_satisfiable(self):
        # The kernel's local-dependency resolver must answer for every source type the registry
        # actually uses, or an entry carrying that type is dead on arrival.
        for typ in (
            "python_stdlib_composition",
            "brain_native_deterministic",
            "brain_native_deterministic_composition",
            "brain_bound_system_tool",
            "brain_owned_python_composition",
        ):
            self.assertIn(typ, runtime.LOCAL_SOURCE_BASE_TYPE, typ)

    def test_every_verified_entry_resolves_to_a_real_adapter_file(self):
        """No entry may name an adapter the loader cannot find.

        ``runtime_native_action`` is the deliberate exception: those two knowledge-lane entries are
        dispatched by the runtime itself and have no adapter file by design.
        """
        unreachable = []
        for cid, entry in sorted(CAPS.items()):
            module = str(entry.get("adapter_module") or "")
            if module == "runtime_native_action":
                continue
            try:
                path = runtime._resolve_bound_adapter_path(entry, module)
            except Exception as exc:  # noqa: BLE001 - the Blocker message is the finding
                unreachable.append((cid, str(exc)[:80]))
                continue
            if not pathlib.Path(path).is_file():
                unreachable.append((cid, "resolved path is not a file"))
        self.assertEqual(unreachable, [])

    def test_the_declared_adapter_path_entry_is_the_only_exception_to_the_convention(self):
        """Pin the shape this repair depends on.

        If a second entry ever declares an out-of-convention adapter path, that is a real event and
        this test should make someone look at it rather than silently widen the search.
        """
        declared = [
            cid
            for cid, e in CAPS.items()
            if "bound_capabilities/" not in str((e.get("source") or {}).get("adapter_path") or "x/")
            and (e.get("source") or {}).get("adapter_path")
        ]
        self.assertEqual(declared, ["python.task.acceptance.measured.objective.v1"])

    def test_repair_loop_executes_and_reports_honestly(self):
        """End to end: a stdlib-composition capability runs and writes a verified artifact.

        Before the repair this raised BOUND_CAPABILITY_SOURCE_UNSUPPORTED before reaching the
        adapter.  The assertion is on the receipt, not on a fix being found: the loop must run,
        replay verification, and say truthfully whether it improved anything.
        """
        work = _write_probe()
        out = work / "repair_report.json"
        result = runtime._invoke_bound_capability(
            {
                "capability_id": "python.software.repair.loop.strict_progress.ast.v1",
                "source_root": str(work),
                "test_paths": [str(work / "test_calc.py")],
                "test_argv": ["python3", "-m", "unittest", "test_calc"],
                "output_path": str(out),
            }
        )
        self.assertIsInstance(result.get("status"), str)
        self.assertIn("baseline_failure_score", result)
        self.assertIn("rounds", result)
        self.assertTrue(result.get("output_verified"), result.get("status"))
        self.assertTrue(out.is_file() and out.stat().st_size > 0)
        self.assertEqual(
            (result.get("dependency") or {}).get("status"),
            "LOCAL_VERIFIED",
        )

    def test_declared_path_entry_reaches_its_adapter(self):
        """The entry whose adapter lives outside bound_capabilities/ must resolve and run."""
        work = _write_probe()
        out = work / "acceptance.json"
        (work / "receipt.json").write_text(json.dumps({"not": "a real receipt"}), encoding="utf-8")
        result = runtime._invoke_bound_capability(
            {
                "capability_id": "python.task.acceptance.measured.objective.v1",
                "goal": "add two numbers",
                "measurement_receipt_path": str(work / "receipt.json"),
                "output_path": str(out),
            }
        )
        # A junk receipt must not be laundered into a pass -- reaching the adapter is the claim
        # under test, and the adapter's own fail-closed verdict is the correct outcome.
        self.assertIsInstance(result.get("status"), str)
        self.assertTrue(out.is_file() and out.stat().st_size > 0)


class DeclaredAdapterPathIsNarrowTests(unittest.TestCase):
    """The declaration is honoured, but it is not a way to load arbitrary code."""

    def _entry(self, adapter_path, module="python_measured_objective_acceptance_v1"):
        return {"adapter_module": module, "source": {"adapter_path": adapter_path}}

    def test_absolute_path_is_refused(self):
        with self.assertRaises(runtime.Blocker) as ctx:
            runtime._resolve_bound_adapter_path(
                self._entry("/etc/passwd"), "passwd"
            )
        self.assertIn("UNSAFE", str(ctx.exception))

    def test_escaping_path_is_refused(self):
        with self.assertRaises(runtime.Blocker) as ctx:
            runtime._resolve_bound_adapter_path(
                self._entry("canonical/runtime/../../../etc/shadow.py"), "shadow"
            )
        self.assertIn("UNSAFE", str(ctx.exception))

    def test_path_outside_runtime_is_refused(self):
        with self.assertRaises(runtime.Blocker) as ctx:
            runtime._resolve_bound_adapter_path(
                self._entry("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"), "x"
            )
        self.assertIn("OUTSIDE_RUNTIME", str(ctx.exception))

    def test_module_name_mismatch_is_refused(self):
        # A real file under canonical/runtime/, but not the module the entry declares.
        with self.assertRaises(runtime.Blocker) as ctx:
            runtime._resolve_bound_adapter_path(
                self._entry("canonical/runtime/goal_compiler.py"),
                "python_measured_objective_acceptance_v1",
            )
        self.assertIn("MODULE_MISMATCH", str(ctx.exception))

    def test_missing_declared_file_still_fails_closed(self):
        with self.assertRaises(runtime.Blocker) as ctx:
            runtime._resolve_bound_adapter_path(
                self._entry("canonical/runtime/does_not_exist_adapter_v1.py"),
                "does_not_exist_adapter_v1",
            )
        self.assertIn("ADAPTER_MISSING", str(ctx.exception))

    def test_undeclared_entry_keeps_the_convention(self):
        path = runtime._resolve_bound_adapter_path({"adapter_module": "objective_relevance_bm25"}, "objective_relevance_bm25")
        self.assertEqual(
            pathlib.Path(path),
            ROOT / "runtime" / "bound_capabilities" / "objective_relevance_bm25.py",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
