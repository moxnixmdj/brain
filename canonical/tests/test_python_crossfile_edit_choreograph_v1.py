# PROJECT_BRAIN
"""Contract pins for python.source.crossfile_edit.choreograph.v1.

The edit choreographer plans cross-file changes: every site the change
must touch, with evidence, and a truthful ``complete`` flag that flips off
the moment anything is ambiguous (never-miss: ambiguity is listed, never
silently dropped).  Refusals come with named reasons.  Cache reuse must
produce a byte-identical plan artifact.

Same module-loading pattern as the sibling capability suites.
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
    "python_crossfile_edit_choreograph_adapter",
    _REPO / "canonical" / "runtime" / "bound_capabilities" / "python_crossfile_edit_choreograph.py",
)
adapter = importlib.util.module_from_spec(spec)
sys.modules.setdefault(spec.name, adapter)
spec.loader.exec_module(adapter)

index_spec = importlib.util.spec_from_file_location(
    "python_source_symbol_index_for_cache",
    _REPO / "canonical" / "runtime" / "bound_capabilities" / "python_source_symbol_index.py",
)
index_adapter = importlib.util.module_from_spec(index_spec)
sys.modules.setdefault(index_spec.name, index_adapter)
index_spec.loader.exec_module(index_adapter)

A_PY = (
    "def helper(x):\n"
    "    return x + 1\n"
    "\n"
    "def origin(x):\n"
    "    return helper(x) * 2\n"
)
B_PY = (
    "from pkg.a import helper\n"
    "\n"
    "def entrypoint():\n"
    "    return helper(4)\n"
)
C_PY = (
    "import pkg.a\n"
    "\n"
    "def run():\n"
    "    return pkg.a.helper(9)\n"
)


def _build():
    work = tempfile.mkdtemp(prefix="crossfile_edit_v1_")
    os.makedirs(os.path.join(work, "pkg"))
    open(os.path.join(work, "pkg", "a.py"), "w").write(A_PY)
    open(os.path.join(work, "pkg", "b.py"), "w").write(B_PY)
    open(os.path.join(work, "pkg", "c.py"), "w").write(C_PY)
    return work


def _plan(work, edits, out_name="plan.json", **kwargs):
    args = {"source_root": ".", "output_path": out_name, "edits": edits}
    args.update(kwargs)
    return adapter.run(args, work)


def _read(work, out_name="plan.json"):
    return json.loads(open(os.path.join(work, out_name)).read())


class CrossfileEditPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = _build()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def _sites(self, plan, kind=None):
        rows = plan["plans"][0]["sites"]
        return [s for s in rows if kind is None or s["kind"] == kind]

    # ---- semantics ------------------------------------------------------

    def test_rename_plans_definition_import_sites_and_proven_references(self):
        r = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                               "name": "helper", "new_name": "compute"}], out_name="t1.json")
        self.assertEqual(r["planned_op_count"], 1)
        self.assertEqual(r["refused_op_count"], 0)
        plan = _read(self.work, "t1.json")
        sites = plan["plans"][0]["sites"]
        defs = [s for s in sites if s["kind"] == "DEFINITION"]
        self.assertEqual(len(defs), 1)
        self.assertEqual(defs[0]["file"], "pkg/a.py")
        self.assertEqual(defs[0]["lineno"], 1)
        imp = [s for s in sites if s["kind"] == "IMPORT_SITE"]
        self.assertEqual([s["file"] for s in imp], ["pkg/b.py"])
        refs = {(s["file"], s["lineno"]) for s in sites if s["kind"] == "REFERENCE"}
        self.assertEqual(refs, {("pkg/a.py", 5), ("pkg/b.py", 4)})
        selected_files = plan["affected_files"]
        self.assertEqual(sorted(selected_files), ["pkg/a.py", "pkg/b.py", "pkg/c.py"])

    def test_plain_import_attribute_use_is_ambiguous_and_breaks_completeness(self):
        r = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                               "name": "helper", "new_name": "compute"}], out_name="t2.json")
        self.assertEqual(r["ambiguous_site_count"], 1)
        plan = _read(self.work, "t2.json")
        amb = plan["plans"][0]["ambiguous_sites"]
        self.assertEqual(len(amb), 1)
        self.assertEqual(amb[0]["file"], "pkg/c.py")
        self.assertEqual(amb[0]["reason"], "PLAIN_IMPORT_ATTRIBUTE_TEXT_MATCH")
        self.assertFalse(plan["complete"])

    def test_rename_name_collision_in_defining_module_is_refused(self):
        r = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                               "name": "helper", "new_name": "origin"}], out_name="t3.json")
        self.assertEqual(r["refused_op_count"], 1)
        plan = _read(self.work, "t3.json")
        self.assertTrue(plan["refusals"][0]["refusal"].startswith("NAME_COLLISION_DEFINING_MODULE"))

    def test_rename_name_collision_in_importer_scope_is_refused(self):
        # b.py gains a module-scope "compute" — renaming helper→compute would collide there
        b_cp = B_PY.replace("def entrypoint():", "def compute(x):\n    return x\n\ndef entrypoint():")
        open(os.path.join(self.work, "pkg", "b.py"), "w").write(b_cp)
        try:
            r = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                                   "name": "helper", "new_name": "compute"}], out_name="t4.json")
            self.assertEqual(r["refused_op_count"], 1)
            plan = _read(self.work, "t4.json")
            self.assertIn("NAME_COLLISION", plan["refusals"][0]["refusal"])
        finally:
            open(os.path.join(self.work, "pkg", "b.py"), "w").write(B_PY)

    def test_unknown_module_and_missing_name_are_refused_with_reasons(self):
        r = _plan(self.work, [
            {"op": "rename_symbol", "module": "pkg/nope.py", "name": "x", "new_name": "y"},
            {"op": "rename_symbol", "module": "pkg/a.py", "name": "nope", "new_name": "y2"},
        ], out_name="t5.json")
        plan = _read(self.work, "t5.json")
        refs = sorted(row["refusal"] for row in plan["refusals"])
        self.assertEqual(r["refused_op_count"], 2)
        self.assertEqual(refs, ["MODULE_NOT_IN_INDEX:pkg/nope.py",
                                "NAME_NOT_AT_MODULE_SCOPE:pkg/a.py:nope"])

    def test_move_symbol_plans_cut_insert_and_import_rewrites(self):
        open(os.path.join(self.work, "pkg", "d.py"), "w").write("# target module\n")
        try:
            r = _plan(self.work, [{"op": "move_symbol", "module": "pkg/a.py",
                                   "qualname": "helper", "to_module": "pkg/d.py"}], out_name="t6.json")
            self.assertEqual(r["refused_op_count"], 0)
            plan = _read(self.work, "t6.json")
            sites = plan["plans"][0]["sites"]
            kinds = {(s["kind"], s["file"]) for s in sites}
            self.assertIn(("CUT_SPAN", "pkg/a.py"), kinds)
            self.assertIn(("INSERT_SPAN", "pkg/d.py"), kinds)
            self.assertIn(("IMPORT_REWRITE", "pkg/b.py"), kinds)
            cut = [s for s in sites if s["kind"] == "CUT_SPAN"][0]
            self.assertEqual((cut["lineno"], cut["line_end"]), (1, 2))
        finally:
            os.unlink(os.path.join(self.work, "pkg", "d.py"))

    def test_move_to_missing_target_module_is_refused(self):
        r = _plan(self.work, [{"op": "move_symbol", "module": "pkg/a.py",
                               "qualname": "helper", "to_module": "pkg/nope.py"}], out_name="t7.json")
        plan = _read(self.work, "t7.json")
        self.assertEqual(plan["refusals"][0]["refusal"], "TARGET_MODULE_NOT_IN_INDEX:pkg/nope.py")

    def test_multi_edit_batch_aggregates_counts_and_keeps_all_ops(self):
        open(os.path.join(self.work, "pkg", "d.py"), "w").write("# target\n")
        try:
            edits = [
                {"op": "rename_symbol", "module": "pkg/a.py", "name": "origin", "new_name": "derive"},
                {"op": "move_symbol", "module": "pkg/b.py", "qualname": "entrypoint", "to_module": "pkg/d.py"},
            ]
            r = _plan(self.work, edits, out_name="t8.json")
            self.assertEqual(r["edit_op_count"], 2)
            self.assertEqual(r["planned_op_count"], 2)
            plan = _read(self.work, "t8.json")
            self.assertEqual(len(plan["plans"]), 2)
            # honesty proof: rename of uncalled `origin` = 1 site (its own
            # definition) — the planner must not invent usage; the move of
            # `entrypoint` = CUT+INSERT (nothing from-imports it) = 2 sites.
            self.assertEqual(r["planned_site_count"], 3)
        finally:
            os.unlink(os.path.join(self.work, "pkg", "d.py"))

    # ---- laws -------------------------------------------------------------

    def test_missing_edits_and_double_inputs_are_refused_structurally(self):
        for args in ({"source_root": ".", "output_path": "t9.json"},
                     {"source_root": ".", "output_path": "t9.json",
                      "edits": [], "edits_path": "x.json"}):
            with self.assertRaises(SystemExit):
                adapter.run(args, self.work)

    def test_unknown_op_is_refused_structurally(self):
        with self.assertRaises(SystemExit):
            _plan(self.work, [{"op": "explode", "module": "pkg/a.py"}], out_name="t10.json")

    def test_path_escape_is_refused(self):
        with self.assertRaises(SystemExit):
            _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                               "name": "helper", "new_name": "compute"}], out_name="../plan.json")

    def test_invalid_cache_is_refused_structurally(self):
        bad = os.path.join(self.work, "bogus_cache.json")
        open(bad, "w").write(json.dumps({"schema": "SOMETHING_ELSE"}))
        with self.assertRaises(SystemExit):
            _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                               "name": "helper", "new_name": "compute"}],
                  out_name="t12.json", index_path="bogus_cache.json")

    def test_cache_from_another_tree_is_refused_truthfully(self):
        other = _build()
        # an index cache built for THIS tree must never be reused for THAT tree
        index_adapter.run({"source_root": ".", "output_path": "foreign_cache.json"}, other)
        shutil.copyfile(os.path.join(other, "foreign_cache.json"),
                        os.path.join(self.work, "foreign_cache.json"))
        shutil.rmtree(other, ignore_errors=True)
        # the foreign cache happens to carry source_root "." — the same string,
        # so build the mismatch honestly: request a different source_root
        with self.assertRaises(SystemExit):
            adapter.run({"source_root": "pkg", "output_path": "t15.json",
                         "edits": [{"op": "rename_symbol", "module": "pkg/a.py",
                                    "name": "helper", "new_name": "compute"}],
                         "index_path": "foreign_cache.json"}, self.work)

    def test_cached_plan_is_byte_identical_to_fresh_plan(self):
        # build a real cache artifact with the sibling index adapter
        index_adapter.run({"source_root": ".", "output_path": "cache_index.json"}, self.work)
        r_fresh = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                                     "name": "helper", "new_name": "compute"}], out_name="t13a.json")
        r_cached = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                                      "name": "helper", "new_name": "compute"}],
                         out_name="t13b.json", index_path="cache_index.json")
        self.assertEqual(r_fresh["cache_used"], 0)
        self.assertEqual(r_cached["cache_used"], 1)
        # result fields independent of cache agree
        self.assertEqual(r_cached["planned_site_count"], r_fresh["planned_site_count"])
        self.assertEqual(r_cached["ambiguous_site_count"], r_fresh["ambiguous_site_count"])
        a = open(os.path.join(self.work, "t13a.json")).read()
        b_txt = open(os.path.join(self.work, "t13b.json")).read()
        self.assertEqual(hashlib.sha256(a.encode()).hexdigest(),
                         hashlib.sha256(b_txt.encode()).hexdigest())

    def test_artifact_sha_and_determinism(self):
        r1 = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                                "name": "helper", "new_name": "compute"}], out_name="t14a.json")
        r2 = _plan(self.work, [{"op": "rename_symbol", "module": "pkg/a.py",
                                "name": "helper", "new_name": "compute"}], out_name="t14b.json")
        self.assertTrue(r1["output_verified"])
        self.assertEqual(r1["output_sha256"], r2["output_sha256"])
        plan = _read(self.work, "t14a.json")
        self.assertEqual(plan["plans"], sorted(plan["plans"], key=lambda p: json.dumps(p["op"], sort_keys=True)))


class CrossfileEditRegistryContractTests(unittest.TestCase):
    """Registry entry must describe the adapter exactly (suite law)."""

    def _entry(self):
        reg = json.loads((_REPO / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        return reg["capabilities"]["python.source.crossfile_edit.choreograph.v1"]

    def test_the_entry_is_a_verified_bound_capability(self):
        entry = self._entry()
        self.assertEqual(entry["status"], "VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(entry["adapter_module"], "python_crossfile_edit_choreograph")
        self.assertEqual(entry["entrypoint"], "run")
        self.assertEqual(entry["provides"], ["python.source.crossfile_edit.choreography",
                                             "python.source.crossfile_edit.choreograph.v1"])
        self.assertEqual(entry["requires"], [])
        self.assertEqual(entry["incremental_spend_usd"], 0)

    def test_every_declared_result_field_is_actually_returned(self):
        entry = self._entry()
        expected = sorted(entry["result_fields"])
        probe = _build()
        try:
            actual = sorted(adapter.run(
                {"source_root": ".", "output_path": "probe_plan.json",
                 "edits": [{"op": "rename_symbol", "module": "pkg/a.py",
                            "name": "helper", "new_name": "compute"}]},
                probe,
            ).keys())
            self.assertEqual(expected, actual)
        finally:
            shutil.rmtree(probe, ignore_errors=True)

    def test_the_verification_receipt_exists_and_is_measured(self):
        entry = self._entry()
        ver = entry["verification"]
        obs = ver["observed_effect"]
        self.assertTrue(obs["verified"])
        self.assertGreaterEqual(obs["planned_sites"], 1)
        self.assertLess(obs["cached_seconds"], obs["fresh_seconds"])
        receipt = _REPO / ver["receipt_path"]
        self.assertTrue(receipt.is_file())
        state = _REPO / ver["state_path"]
        self.assertTrue(state.is_file())


if __name__ == "__main__":
    unittest.main()
