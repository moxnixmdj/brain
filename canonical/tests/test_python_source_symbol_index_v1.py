"""The semantic symbol index: navigation without grep (``python.source.symbols.index.ast``).

The structural audit could count classes and imports but could not answer the
working questions of an engineer: where is this symbol defined, who calls it,
what is in scope at this line. This adapter indexes a Python tree with the
stdlib parser into definitions (kind, qualname, line range), references with
resolution classes (local/module/builtin/unknown), call edges, and an inverted
``callers_of`` index -- in one deterministic pass, with zero dependencies.

These tests pin the real behavior on known fixture code, the fail-closed path
laws, determinism, and the registry contract the rest of the runtime binds to.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ADAPTER_PATH = os.path.join(
    REPO_ROOT, "canonical", "runtime", "bound_capabilities",
    "python_source_symbol_index.py",
)
_spec = importlib.util.spec_from_file_location(
    "python_source_symbol_index_test", ADAPTER_PATH
)
adapter = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = adapter
_spec.loader.exec_module(adapter)

CAPABILITY_ID = "python.source.symbols.index.ast"

FIXTURE = '''\
"""fixture module."""

CONSTANT = 1

class Base:
    def origin(self, x):
        return x

class Child(Base):
    def origin(self, x):
        # overrides Base.origin
        value = helper(x) + CONSTANT
        return value

def helper(x):
    return x * 2

def entrypoint():
    c = Child()
    return c.origin(3)

def never_called():
    return entrypoint()
'''

BROKEN = "def broken(:\n    pass\n"


def _run(work):
    src = os.path.join(work, "pkg")
    os.makedirs(src, exist_ok=True)
    with open(os.path.join(src, "mod.py"), "w", encoding="utf-8") as handle:
        handle.write(FIXTURE)
    out = os.path.join(work, "index.json")
    return adapter.run({"source_root": src, "output_path": out}, work), out


class SymbolIndexBehaviorTests(unittest.TestCase):
    """The index answers the navigation questions on known fixture code."""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="symindex-test-")
        self.addCleanup(shutil.rmtree, self.work, True)
        self.result, self.out = _run(self.work)
        with open(self.out, "r", encoding="utf-8") as handle:
            self.report = json.load(handle)

    def test_the_adapter_reports_verified_with_counts(self):
        self.assertTrue(self.result["output_verified"])
        self.assertEqual(self.result["file_count"], 1)
        self.assertEqual(self.result["unparseable_count"], 0)
        self.assertGreaterEqual(self.result["symbol_count"], 8)
        self.assertGreater(self.result["call_edge_count"], 0)

    def test_definitions_carry_kind_qualname_and_line_range(self):
        module = self.report["modules"][0]
        defs = {d["qualname"]: d for d in module["definitions"]}
        self.assertEqual(defs["Base"]["kind"], "class")
        self.assertEqual(defs["Base.origin"]["kind"], "method")
        self.assertEqual(defs["helper"]["signature"], ["x"])
        self.assertEqual(defs["Child"]["bases"], ["Base"])
        self.assertGreater(defs["Child"]["end_lineno"], defs["Child"]["lineno"])
        self.assertEqual(defs["CONSTANT"]["kind"], "variable")

    def test_references_resolve_local_module_builtin_unknown(self):
        module = self.report["modules"][0]
        by = {}
        for ref in module["references"]:
            by.setdefault((ref["name"], ref["resolution"]), []).append(ref)
        self.assertIn(("CONSTANT", "module"), by)
        self.assertIn(("helper", "module"), by)
        self.assertIn(("x", "local"), by)

    def test_the_who_calls_index_is_the_navigation_answer(self):
        callers = self.report["callers_of"]
        # origin is called only from entrypoint(); helper only from
        # Child.origin; entrypoint only from never_called.
        self.assertEqual(callers.get("entrypoint"), ["never_called"])
        self.assertEqual(callers.get("helper"), ["Child.origin"])
        self.assertEqual(callers.get("origin"), ["entrypoint"])

    def test_the_flat_symbol_table_is_module_qualified(self):
        keys = [k for k in self.report["symbols"] if k.endswith(":helper")]
        self.assertEqual(len(keys), 1)
        self.assertTrue(keys[0].startswith("pkg.mod"), keys[0])

    def test_a_forward_reference_resolves_to_the_module_scope(self):
        """`helper` is called at line 12 and DEFINED at line 15 -- legal
        Python, because the call site executes after the module finished.
        The index must not misread it as unknown."""
        module = self.report["modules"][0]
        helper_refs = [
            r for r in module["references"] if r["name"] == "helper"
        ]
        self.assertTrue(helper_refs)
        self.assertTrue(
            all(r["resolution"] == "module" for r in helper_refs),
            helper_refs,
        )

    def test_the_artifact_sha256_matches_the_written_bytes(self):
        data = open(self.out, "rb").read()
        self.assertEqual(
            self.result["output_sha256"], hashlib.sha256(data).hexdigest()
        )


class SymbolIndexNegativeControls(unittest.TestCase):
    """The laws that keep the index honest."""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="symindex-neg-")
        self.addCleanup(shutil.rmtree, self.work, True)

    def test_an_unparseable_file_is_a_finding_not_a_crash(self):
        src = os.path.join(self.work, "pkg")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "bad.py"), "w", encoding="utf-8") as h:
            h.write(BROKEN)
        with open(os.path.join(src, "good.py"), "w", encoding="utf-8") as h:
            h.write("ok = 1\n")
        result = adapter.run(
            {"source_root": src, "output_path": os.path.join(self.work, "o.json")},
            self.work,
        )
        self.assertEqual(result["unparseable_count"], 1)
        self.assertEqual(result["unparseable_paths"], ["pkg/bad.py"])
        self.assertEqual(result["file_count"], 1)

    def test_a_source_root_outside_the_repository_is_refused(self):
        with self.assertRaises(RuntimeError) as caught:
            adapter.run({
                "source_root": "..",
                "output_path": os.path.join(self.work, "o.json"),
            }, self.work)
        self.assertIn("PATH_OUTSIDE_REPOSITORY", str(caught.exception))

    def test_an_output_path_outside_the_repository_is_refused(self):
        src = os.path.join(self.work, "pkg")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "ok.py"), "w", encoding="utf-8") as h:
            h.write("ok = 1\n")
        with self.assertRaises(RuntimeError) as caught:
            adapter.run({
                "source_root": src,
                "output_path": os.path.join(tempfile.gettempdir(), "o.json"),
            }, self.work)
        self.assertIn("PATH_OUTSIDE_REPOSITORY", str(caught.exception))

    def test_an_empty_tree_is_refused_rather_than_silently_indexed(self):
        src = os.path.join(self.work, "empty")
        os.makedirs(src, exist_ok=True)
        with self.assertRaises(RuntimeError) as caught:
            adapter.run({
                "source_root": src,
                "output_path": os.path.join(self.work, "o.json"),
            }, self.work)
        self.assertIn("PYTHON_INDEX_EMPTY", str(caught.exception))

    def test_determinism_identical_input_identical_sha(self):
        result_a, out_a = _run(self.work)
        result_b, out_b = _run(self.work)
        self.assertEqual(result_a["output_sha256"], result_b["output_sha256"])


class SymbolIndexRegistryContractTests(unittest.TestCase):
    """The registry entry the planner/binder/runtime bind against."""

    def setUp(self):
        with open(os.path.join(
            REPO_ROOT, "canonical", "runtime", "BOUND_CAPABILITY_REGISTRY_V1.json"
        ), "r", encoding="utf-8") as handle:
            self.entry = json.load(handle)["capabilities"][CAPABILITY_ID]

    def test_the_entry_is_a_verified_bound_capability(self):
        self.assertEqual(self.entry["status"], "VERIFIED_BOUND_CAPABILITY")
        # Both declared effects denote the existing index artifact; the
        # canonical effect is consumed by the actual index-to-intent chain.
        self.assertEqual(self.entry["provides"],
                         ["python.source.symbol_index", "python.source.symbols.index.ast"])
        self.assertEqual(self.entry["requires"], [])
        self.assertEqual(self.entry["adapter_module"], "python_source_symbol_index")
        self.assertEqual(self.entry["incremental_spend_usd"], 0)

    def test_every_declared_result_field_is_actually_returned(self):
        work = tempfile.mkdtemp(prefix="symindex-contract-")
        self.addCleanup(shutil.rmtree, work, True)
        result, _ = _run(work)
        self.assertEqual(
            sorted(result),
            sorted(self.entry["result_fields"]),
            "result_fields is the contract; the adapter must return exactly it",
        )

    def test_the_verification_observed_effect_is_measured_and_present(self):
        verification = self.entry["verification"]
        self.assertTrue(verification["independently_verified"])
        receipt = os.path.join(REPO_ROOT, verification["receipt_path"])
        state = os.path.join(REPO_ROOT, verification["state_path"])
        self.assertTrue(os.path.isfile(receipt))
        self.assertTrue(os.path.isfile(state))
        effect = verification["observed_effect"]
        for key in ("files", "symbols", "references", "call_edges"):
            self.assertGreater(effect[key], 0)
        self.assertTrue(effect["verified"])


if __name__ == "__main__":
    unittest.main()
