from __future__ import annotations

import ast
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import brain_unified_model_v1 as model_runtime
from canonical.runtime import compile_brain_unified_model_v1 as compiler

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / model_runtime.DEFAULT_ARTIFACT
SCRATCH_PARENT = ROOT / "canonical" / "astra_runtime" / "tmp"


class BrainUnifiedModelV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()

    def make_scratch(self) -> Path:
        SCRATCH_PARENT.mkdir(parents=True, exist_ok=True)
        path = Path(tempfile.mkdtemp(prefix="TEST_UNIFIED_MODEL_", dir=SCRATCH_PARENT))
        self.addCleanup(shutil.rmtree, path, True)
        return path

    def rel(self, path: Path) -> str:
        return path.relative_to(ROOT).as_posix()

    # ------------------------------------------------------------------ artifact

    def test_artifact_exists_and_schema_is_exact(self):
        self.assertTrue(ARTIFACT.is_file())
        raw = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema"], model_runtime.SCHEMA)
        self.assertEqual(raw["model_id"], "BRAIN-UNIFIED-MODEL-V1")

    def test_declared_digest_recomputes(self):
        raw = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            raw["digest"]["value"], model_runtime.artifact_digest(raw)
        )

    def test_tampering_is_rejected(self):
        raw = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        raw["capabilities"][0]["triggers"] = ["tampered"]
        scratch = self.make_scratch()
        path = scratch / "tampered.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(
            model_runtime.UnifiedModelError, "MODEL_DIGEST_MISMATCH"
        ):
            model_runtime.load_model(path)

    def test_compilation_is_deterministic(self):
        recompiled = compiler.compile_model()
        raw = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            compiler.canonical_json(recompiled), compiler.canonical_json(raw)
        )
        self.assertEqual(
            recompiled["digest"]["value"], raw["digest"]["value"]
        )

    # ------------------------------------------------------------------ coverage

    def test_every_live_capability_is_modelled(self):
        from canonical.runtime import live_integrated_brain_v1 as live_brain

        live = set(live_brain.load_verified_registry())
        modelled = set(self.model.capabilities)
        self.assertEqual(live, modelled)
        self.assertEqual(len(modelled), 363)

    def test_every_capability_has_a_trigger_and_a_route(self):
        for cid, row in self.model.capabilities.items():
            with self.subTest(cid=cid):
                self.assertTrue(row.get("triggers"))
                self.assertEqual(
                    row["route"]["carrier"],
                    "verified_bound_capability_execution_adapter_v1.execute",
                )
                self.assertEqual(row.get("incremental_spend_usd"), 0)

    def test_every_capability_is_addressable_by_its_own_id(self):
        for cid in self.model.capabilities:
            with self.subTest(cid=cid):
                routed = self.model.route(cid)
                self.assertTrue(routed["confident"], cid)
                self.assertEqual(routed["best"]["id"], cid)

    def test_engines_and_skills_are_present(self):
        self.assertGreaterEqual(len(self.model.engines), 25)
        self.assertIn("engine:ADEQUATE_DECISION", self.model.engines)
        self.assertGreaterEqual(len(self.model.skills), 18)
        for row in self.model.skills:
            self.assertTrue(row["procedure"], row["id"])

    # ------------------------------------------------------------------ routing

    def test_known_goals_route_to_the_expected_capability(self):
        cases = {
            "extract text from a pdf document": "pdf.extract.text.pypdf",
            "create a sqlite table from json records": "sqlite.table.create_from_json_records",
            "rank sources by relevance to an objective": "source.objective_relevance.rank.bm25",
            "audit python source structure and imports": "python.source.audit.ast",
        }
        for goal, expected in cases.items():
            with self.subTest(goal=goal):
                routed = self.model.route(goal)
                self.assertTrue(routed["confident"])
                self.assertEqual(routed["best"]["id"], expected)

    def test_out_of_domain_goal_fails_closed(self):
        routed = self.model.route("launch a weather satellite into low earth orbit")
        self.assertFalse(routed["confident"])
        self.assertEqual(
            routed["reason"], "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED"
        )

    def test_unknown_goal_returns_fail_closed_not_an_answer(self):
        out = self.model.solve("compose a symphony in the style of debussy")
        self.assertIs(out.get("pass"), False)
        self.assertEqual(
            out["reason"], "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED"
        )
        self.assertEqual(out["credit"]["capability_credit_delta"], 0)

    # ------------------------------------------------------------------ recall

    def test_recall_returns_a_real_external_path(self):
        out = self.model.recall("zero incremental spend rule")
        self.assertGreater(out["hit_count"], 0)
        for hit in out["hits"]:
            self.assertTrue((ROOT / hit["path"]).is_file(), hit["path"])

    def test_current_law_outranks_its_own_history(self):
        out = self.model.recall("capability acquisition engine law", top_k=3)
        paths = [hit["path"] for hit in out["hits"]]
        self.assertEqual(
            paths[0], "canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V8.md"
        )

    def test_history_is_still_retrievable_by_its_own_version(self):
        out = self.model.recall("capability acquisition engine law v4", top_k=5)
        paths = [hit["path"] for hit in out["hits"]]
        self.assertTrue(
            any("CAPABILITY_ACQUISITION_ENGINE_LAW_V4.md" in path for path in paths)
        )

    # ---------------------------------------------------------------- execution

    def test_python_source_audit_matches_independent_ast_oracle(self):
        scratch = self.make_scratch()
        src = scratch / "src"
        src.mkdir()
        (src / "sample.py").write_text(
            "import json\nimport pathlib\n\n"
            "def one(x):\n    return x\n\n"
            "def two(x):\n    return x\n\n"
            "class A:\n    pass\n\nclass B:\n    pass\n",
            encoding="utf-8",
        )
        out = self.model.solve(
            "audit python source structure",
            inputs={
                "source_root": self.rel(src),
                "output_path": self.rel(scratch / "out" / "audit.json"),
            },
        )
        self.assertIs(out.get("pass"), True, out.get("reason"))
        result = out["execution"]["result"]
        tree = ast.parse((src / "sample.py").read_text(encoding="utf-8"))
        functions = sum(
            1 for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        classes = sum(1 for n in tree.body if isinstance(n, ast.ClassDef))
        self.assertEqual(result["file_count"], 1)
        self.assertEqual(result["function_count"], functions)
        self.assertEqual(result["class_count"], classes)
        self.assertEqual(functions, 2)
        self.assertEqual(classes, 2)
        self.assertGreaterEqual(result["distinct_imported_module_count"], 2)

    def test_sqlite_creation_matches_sqlite3_oracle(self):
        scratch = self.make_scratch()
        records = {
            "records": {
                "r1": {"status": "READY", "name": "a", "v": 1},
                "r2": {"status": "READY", "name": "b", "v": 2},
            }
        }
        json_path = scratch / "records.json"
        json_path.write_text(json.dumps(records), encoding="utf-8")
        db_path = scratch / "records.db"
        out = self.model.solve(
            "create a sqlite table from json records with columns name and v",
            inputs={
                "goal": (
                    "Create a table named records with columns name and v. "
                    "The status value is READY."
                ),
                "json_path": self.rel(json_path),
                "output_path": self.rel(db_path),
            },
        )
        self.assertIs(out.get("pass"), True, out.get("reason"))
        self.assertTrue(db_path.is_file())
        conn = sqlite3.connect(str(db_path))
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(records)")]
            count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(columns, ["name", "v"])
        self.assertEqual(count, 2)

    def test_missing_inputs_fail_closed(self):
        out = self.model.solve(
            "audit python source structure",
            capability_id="python.source.audit.ast",
            inputs={},
        )
        self.assertIs(out.get("pass"), False)
        self.assertTrue(str(out["reason"]).startswith("CAPABILITY_INPUTS_MISSING"))

    def test_engine_without_host_providers_fails_closed(self):
        out = self.model.solve(
            "compute an adequate decision",
            capability_id="engine:ADEQUATE_DECISION",
            inputs={},
        )
        self.assertIs(out.get("pass"), False)
        self.assertEqual(out["reason"], "ENGINE_DID_NOT_REPORT_SUCCESS")

    def test_unknown_capability_id_is_rejected(self):
        with self.assertRaisesRegex(
            model_runtime.UnifiedModelError, "CAPABILITY_NOT_IN_MODEL"
        ):
            self.model.solve("x", capability_id="bound:does.not.exist")

    # ---------------------------------------------------------------- dependence

    def test_runtime_imports_no_model_client(self):
        forbidden = {
            "openai",
            "anthropic",
            "transformers",
            "torch",
            "llama_cpp",
            "ollama",
            "litellm",
        }
        for rel in (
            "canonical/runtime/brain_unified_model_v1.py",
            "canonical/runtime/compile_brain_unified_model_v1.py",
            "canonical/runtime/verify_brain_unified_model_v1.py",
        ):
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            names: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.add(node.module.split(".")[0])
            with self.subTest(path=rel):
                self.assertFalse(names & forbidden, sorted(names & forbidden))

    def test_artifact_declares_zero_model_and_spend(self):
        raw = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        provenance = raw["provenance"]
        self.assertEqual(provenance["external_model_calls"], 0)
        self.assertEqual(provenance["network_calls"], 0)
        self.assertEqual(provenance["incremental_spend_usd"], 0)
        for row in raw["capabilities"]:
            self.assertEqual(row["incremental_spend_usd"], 0, row["id"])


if __name__ == "__main__":
    unittest.main()


class DeclaredContextBindingTests(unittest.TestCase):
    """``solve()`` may bind from resources the caller explicitly declared.

    The rule that makes this safe: a slot is filled only from the declared
    list, or by a destination the binder synthesizes deterministically. With no
    declaration the code path is not entered at all, so an unstated input still
    fails closed and ``missing_inputs_fail_closed`` cannot regress.
    """

    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()
        cls.pdf = ROOT / "canonical" / "astra_runtime" / "tmp" / "BOUND_PDF_TEXT_TEST.pdf"

    def test_no_declared_context_still_fails_closed(self):
        out = self.model.solve("Read a PDF and extract its text.")
        self.assertIs(out.get("pass"), False)
        self.assertTrue(str(out["reason"]).startswith("CAPABILITY_INPUTS_MISSING"))
        self.assertNotIn("binding_provenance", out)

    def test_declared_context_binds_the_declared_path_only(self):
        if not self.pdf.exists():
            self.skipTest("fixture pdf not present")
        rel = self.pdf.relative_to(ROOT).as_posix()
        out = self.model.solve("Read a PDF and extract its text.", context_paths=[rel])

        # The refusal must no longer be about a missing input: the slot bound.
        self.assertFalse(
            str(out.get("reason") or "").startswith("CAPABILITY_INPUTS_MISSING"),
            out.get("reason"),
        )
        prov = out.get("binding_provenance") or {}
        self.assertIn("pdf_path", prov.get("filled_from_declared_context") or [])
        self.assertEqual(prov.get("values", {}).get("pdf_path"), rel)
        self.assertEqual(prov.get("declared_context"), [rel])

    def test_a_path_outside_the_declaration_is_never_used(self):
        """The binder may find other files; only declared ones are admissible."""
        other = "canonical/runtime/brain_unified_model_v1.py"
        out = self.model.solve(
            "Read a PDF and extract its text.", context_paths=[other]
        )
        # A .py file cannot satisfy pdf_path, so this must stay refused rather
        # than silently reach into the repository for some other PDF.
        self.assertIs(out.get("pass"), False)
        self.assertTrue(
            str(out.get("reason") or "").startswith("CAPABILITY_INPUTS_MISSING"),
            out.get("reason"),
        )
        self.assertNotIn("binding_provenance", out)

    def test_declaration_cannot_override_an_explicit_input(self):
        if not self.pdf.exists():
            self.skipTest("fixture pdf not present")
        rel = self.pdf.relative_to(ROOT).as_posix()
        sentinel = "canonical/astra_runtime/tmp/EXPLICIT_SENTINEL.pdf"
        out = self.model.solve(
            "Read a PDF and extract its text.",
            inputs={"pdf_path": sentinel, "output_path": "canonical/astra_runtime/tmp/o.json"},
            context_paths=[rel],
        )
        prov = out.get("binding_provenance")
        # pdf_path was supplied by the caller, so the binder must not touch it.
        if prov:
            self.assertNotIn("pdf_path", prov.get("filled_from_declared_context") or [])

    def test_a_goal_text_slot_binds_from_the_callers_own_words(self):
        """`goal` is the sentence handed in, not a discovered resource.

        This is what separates the caller's words from an invented resource:
        filling `goal` from the sentence invents nothing, while filling
        `source_root` from a default would choose what to operate on. The
        capability declares only `goal` and `output_path`, both of which are
        admissible, so it executes end to end from a plain sentence.
        """
        cid = "plain_goal.bound_capability.grounding.stdlib"
        if cid not in self.model.capabilities:
            self.skipTest("capability not in model")
        row = self.model.capabilities[cid]
        self.assertEqual(
            [str(x) for x in (row.get("input_names") or [])], ["goal", "output_path"]
        )

        goal = "Ground this plain goal against a bound capability."
        out = self.model.solve(goal, capability_id=cid, context_paths=["AGENTS.md"])

        self.assertIs(out.get("pass"), True, out.get("reason"))
        prov = out.get("binding_provenance") or {}
        self.assertIn("goal", prov.get("filled_from_declared_context") or [])
        # The value must be the caller's own sentence, verbatim.
        self.assertEqual(prov.get("values", {}).get("goal"), goal)

    def test_source_root_is_never_filled_by_default(self):
        """The invention case: a root the goal never named must stay unbound."""
        out = self.model.solve(
            "Audit the python source tree with an AST.",
            context_paths=["AGENTS.md"],
        )
        self.assertIs(out.get("pass"), False)
        self.assertIn("source_root", str(out.get("reason") or ""))
        prov = out.get("binding_provenance") or {}
        self.assertNotIn("source_root", prov.get("filled_from_declared_context") or [])

    def test_a_path_named_in_the_goal_beats_declared_context(self):
        """A file the caller typed must never be displaced by an invented one.

        `complete_inputs` honours `goal_paths` verbatim, so passing only the
        declared context used to discard the path the sentence names and let
        the binder pick some other JSON file in the repository -- while still
        reporting that nothing was missing. This goal names its own input, so
        the bound value has to be that path and nothing else.
        """
        cid = "xlsx.table.create_from_json_records"
        if cid not in self.model.capabilities:
            self.skipTest("capability not in model")
        named = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        if not (ROOT / named).exists():
            self.skipTest("named fixture not present")

        goal = "Create an xlsx table from the JSON records in " + named + "."
        out = self.model.solve(goal, capability_id=cid, context_paths=["AGENTS.md"])

        # Binding must have got past the missing-input stage.
        self.assertFalse(
            str(out.get("reason") or "").startswith("CAPABILITY_INPUTS_MISSING"),
            out.get("reason"),
        )
        values = (out.get("binding_provenance") or {}).get("values") or {}
        self.assertEqual(values.get("json_path"), named)
        # The regression, named explicitly: no other file may be substituted.
        self.assertNotEqual(values.get("json_path"), "MIGRATION_STATUS_2026-09-10.json")

    def test_declared_context_still_binds_when_the_goal_names_nothing(self):
        """Widening `allowed` must not weaken the declaration-only path."""
        if not self.pdf.exists():
            self.skipTest("fixture pdf not present")
        rel = self.pdf.relative_to(ROOT).as_posix()
        out = self.model.solve("Read a PDF and extract its text.", context_paths=[rel])
        prov = out.get("binding_provenance") or {}
        self.assertEqual(prov.get("values", {}).get("pdf_path"), rel)
