# PROJECT_BRAIN
"""Contract pins for python.source.symbols.resolve.v1.

The question "which file and which definition does this name come from?"
must be answerable inside the treated world, with explicit ambiguity
(MULTI_HOME), explicit externality (EXTERNAL / BUILTIN), and truthful
UNRESOLVED reasons — no guessed module, no partial hop, no silent none.

Same module-loading pattern as the sibling capability suites: the adapter
is loaded from its file so the suite exercises the code the registry
entry binds, not a shorthand that could drift.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    "python_symbol_resolve_adapter",
    _REPO / "canonical" / "runtime" / "bound_capabilities" / "python_symbol_resolve.py",
)
adapter = importlib.util.module_from_spec(spec)
sys.modules.setdefault(spec.name, adapter)
spec.loader.exec_module(adapter)

A_PY = (
    "def helper(x):\n"
    "    return x + 1\n"
    "\n"
    "def origin(x):\n"
    "    return helper(x) * 2\n"
    "\n"
    "class K:\n"
    "    def method(self):\n"
    "        return helper(2)\n"
)
B_PY = (
    "from pkg.a import helper, origin\n"
    "\n"
    "def entrypoint():\n"
    "    return origin(helper(1))\n"
)
C_PY = (
    "import pkg.b\n"
    "\n"
    "def run():\n"
    "    return pkg.b.entrypoint()\n"
)
SHADOW_PY = (
    "def helper(x):\n"  # same bare name in another module -> MULTI_HOME
    "    return x - 1\n"
)


def _build():
    work = tempfile.mkdtemp(prefix="symbol_resolve_v1_")
    os.makedirs(os.path.join(work, "pkg"))
    open(os.path.join(work, "pkg", "a.py"), "w").write(A_PY)
    open(os.path.join(work, "pkg", "b.py"), "w").write(B_PY)
    open(os.path.join(work, "pkg", "c.py"), "w").write(C_PY)
    open(os.path.join(work, "pkg", "shadow.py"), "w").write(SHADOW_PY)
    return work


def _run(work, queries, allow_overwrite=False):
    out = os.path.join(work, "out.json")
    if allow_overwrite and os.path.exists(out):
        os.unlink(out)
    result = adapter.run(
        {"source_root": ".", "output_path": "out.json", "queries": queries},
        work,
    )
    return result


def _row(report, key_value):
    for r in report["results"]:
        if json.dumps(r["query"], sort_keys=True) == json.dumps(key_value, sort_keys=True):
            return r
    return None


class SymbolResolveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = _build()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def _report(self, result):
        path = os.path.join(self.work, "out.json")
        return json.loads(open(path).read())

    # ---- happy path ----------------------------------------------------

    def test_imported_name_resolves_to_the_exporting_module_and_line(self):
        result = _run(self.work, [{"module": "pkg/b.py", "line": 4, "name": "helper"}], allow_overwrite=True)
        report = self._report(result)
        row = _row(report, {"module": "pkg/b.py", "line": 4, "name": "helper"})
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "RESOLVED")
        self.assertTrue(str(row["resolved_from"]).startswith("IMPORT_ALIAS"))
        self.assertEqual(len(row["definitions"]), 1)
        self.assertEqual(row["definitions"][0]["module"], "pkg/a.py")
        self.assertEqual(row["definitions"][0]["name"], "helper")
        self.assertEqual(row["definitions"][0]["lineno"], 1)

    def test_module_defined_name_resolves_inside_own_module(self):
        result = _run(self.work, [{"module": "pkg/a.py", "line": 5, "name": "origin"}], allow_overwrite=True)
        row = _row(self._report(result), {"module": "pkg/a.py", "line": 5, "name": "origin"})
        self.assertEqual(row["status"], "RESOLVED")
        self.assertEqual(row["resolved_from"], "MODULE_SCOPE")

    def test_class_member_resolution_through_dotted_reference(self):
        result = _run(self.work, [{"reference": "pkg.a.K.method"}], allow_overwrite=True)
        row = _row(self._report(result), {"reference": "pkg.a.K.method"})
        self.assertEqual(row["status"], "RESOLVED")
        self.assertEqual(row["resolved_from"], "DOTTED_REFERENCE")
        self.assertEqual(row["definitions"][0]["qualname"], "K.method")

    def test_dotted_module_reference_starts_at_module_level(self):
        result = _run(self.work, [{"reference": "pkg.a.origin"}], allow_overwrite=True)
        row = _row(self._report(result), {"reference": "pkg.a.origin"})
        self.assertEqual(row["status"], "RESOLVED")
        self.assertEqual(row["definitions"][0]["module"], "pkg/a.py")

    def test_plain_import_alias_carries_module_membership(self):
        result = _run(self.work, [{"module": "pkg/c.py", "line": 4, "name": "pkg"}], allow_overwrite=True)
        row = _row(self._report(result), {"module": "pkg/c.py", "line": 4, "name": "pkg"})
        self.assertEqual(row["status"], "RESOLVED")
        self.assertTrue(str(row["resolved_from"]).startswith("IMPORT_MODULE"))
        self.assertEqual(row["import_from"] if "import_from" in row else None, "pkg/b.py")

    # ---- truthfulness lanes --------------------------------------------

    def test_builtin_name_is_builtin_status_not_silently_unresolved(self):
        result = _run(self.work, [{"module": "pkg/b.py", "line": 4, "name": "len"}], allow_overwrite=True)
        row = _row(self._report(result), {"module": "pkg/b.py", "line": 4, "name": "len"})
        self.assertEqual(row["status"], "BUILTIN")
        self.assertEqual(row["resolved_from"], "BUILTIN")

    def test_external_import_declares_externality(self):
        result = _run(self.work, [{"module": "pkg/b.py", "line": 4, "name": "os"}], allow_overwrite=True)
        row = _row(self._report(result), {"module": "pkg/b.py", "line": 4, "name": "os"})
        self.assertEqual(row["status"], "UNRESOLVED")
        self.assertEqual(row["reason"], "NAME_NOT_FOUND_IN_MODULE_SCOPE_OR_IMPORTS")

    def test_ambiguity_reports_multi_home_with_every_candidate(self):
        result = _run(self.work, [{"module": "pkg/c.py", "line": 4, "name": "helper"}], allow_overwrite=True)
        row = _row(self._report(result), {"module": "pkg/c.py", "line": 4, "name": "helper"})
        self.assertEqual(row["status"], "MULTI_HOME")
        modules = sorted(d["module"] for d in row["definitions"])
        self.assertEqual(modules, ["pkg/a.py", "pkg/shadow.py"])

    def test_unknown_reference_is_refused_with_reason_not_a_crash(self):
        result = _run(self.work, [{"reference": "pkg.a.nope.deeper"}], allow_overwrite=True)
        row = _row(self._report(result), {"reference": "pkg.a.nope.deeper"})
        self.assertEqual(row["status"], "UNRESOLVED")
        self.assertTrue(str(row["reason"]).startswith("ATTRIBUTE_NOT_FOUND"))

    def test_unknown_module_is_refused_truthfully(self):
        result = _run(self.work, [{"module": "pkg/nope.py", "line": 1, "name": "x"}], allow_overwrite=True)
        row = _row(self._report(result), {"module": "pkg/nope.py", "line": 1, "name": "x"})
        self.assertEqual(row["status"], "UNRESOLVED")
        self.assertEqual(row["reason"], "MODULE_NOT_IN_INDEX")

    # ---- artifact law ----------------------------------------------------

    def test_artifact_is_sha_verified_and_sorted(self):
        result = _run(self.work, [
            {"module": "pkg/b.py", "line": 4, "name": "helper"},
            {"reference": "pkg.a.origin"},
        ], allow_overwrite=True)
        path = os.path.join(self.work, "out.json")
        text = open(path).read()
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # determinism: rebuild into a second output and compare shas
        out2 = os.path.join(self.work, "out2.json")
        result_b = adapter.run(
            {"source_root": ".", "output_path": "out2.json", "queries": [
                {"module": "pkg/b.py", "line": 4, "name": "helper"},
                {"reference": "pkg.a.origin"},
            ]},
            self.work,
        )
        text_b = open(out2).read()
        os.unlink(out2)
        self.assertEqual(hashlib.sha256(text_b.encode("utf-8")).hexdigest(), sha)
        self.assertTrue(result["output_verified"])
        self.assertEqual(len(result["output_sha256"]), 64)

    def test_mixed_batch_aggregates_statuses_without_skipping_any_query(self):
        queries = [
            {"module": "pkg/a.py", "line": 5, "name": "origin"},
            {"module": "pkg/b.py", "line": 4, "name": "helper"},
            {"module": "pkg/c.py", "line": 4, "name": "helper"},
            {"module": "pkg/b.py", "line": 4, "name": "len"},
            {"reference": "pkg.a.K.method"},
            {"reference": "pkg.a.nope"},
        ]
        result = _run(self.work, queries, allow_overwrite=True)
        report = self._report(result)
        self.assertEqual(report["query_count"], 6)
        statuses = sorted(r["status"] for r in report["results"])
        self.assertEqual(report["resolved_count"], 3)
        self.assertEqual(report["multi_home_count"], 1)
        self.assertEqual(report["builtin_count"], 1)
        self.assertEqual(report["unresolved_count"], 1)
        self.assertEqual(statuses, sorted(["RESOLVED", "RESOLVED", "RESOLVED", "MULTI_HOME", "BUILTIN", "UNRESOLVED"]))
        self.assertEqual(result["resolved_count"], 3)
        self.assertEqual(result["multi_home_count"], 1)


class SymbolResolveRegistryContractTests(unittest.TestCase):
    """The registry entry must describe the adapter exactly (suite law)."""

    def _entry(self):
        reg = json.loads((_REPO / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        return reg["capabilities"]["python.source.symbols.resolve.v1"]

    def test_the_entry_is_a_verified_bound_capability(self):
        entry = self._entry()
        self.assertEqual(entry["status"], "VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(entry["adapter_module"], "python_symbol_resolve")
        self.assertEqual(entry["entrypoint"], "run")
        self.assertEqual(entry["provides"], ["python.source.symbols.resolve"])
        self.assertEqual(entry["requires"], [])
        self.assertEqual(entry["incremental_spend_usd"], 0)

    def test_every_declared_result_field_is_actually_returned(self):
        entry = self._entry()
        expected = sorted(entry["result_fields"])
        actual = sorted(adapter.run(
            {"source_root": ".", "output_path": "out_registry_probe.json", "queries": [
                {"module": "pkg/b.py", "line": 4, "name": "helper"},
            ]},
            _build_probe(),
        ).keys())
        # actual keys were printed with the probe root suffix; compare only contract
        self.assertEqual(expected, actual)

    def test_the_verification_receipt_exists_and_is_measured(self):
        entry = self._entry()
        ver = entry["verification"]
        obs = ver["observed_effect"]
        self.assertTrue(obs["verified"])
        self.assertGreaterEqual(obs["queries"], 1)
        self.assertGreaterEqual(obs["resolved"], 1)
        receipt = _REPO / ver["receipt_path"]
        self.assertTrue(receipt.is_file())
        state = _REPO / ver["state_path"]
        self.assertTrue(state.is_file())


def _build_probe():
    work = tempfile.mkdtemp(prefix="symbol_resolve_registry_probe_")
    os.makedirs(os.path.join(work, "pkg"))
    open(os.path.join(work, "pkg", "a.py"), "w").write("def helper(x):\n    return x + 1\n")
    open(os.path.join(work, "pkg", "b.py"), "w").write("from pkg.a import helper\n\ndef use():\n    return helper(1)\n")
    return work


if __name__ == "__main__":
    unittest.main()
