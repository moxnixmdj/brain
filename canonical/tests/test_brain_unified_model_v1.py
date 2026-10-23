from __future__ import annotations

import ast
import hashlib
import json
import shutil
import tarfile
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
        self.assertEqual(len(modelled), 367)

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

    def test_a_slot_reserved_for_a_produced_artifact_is_never_filled_from_context(self):
        """A contract-declared `effect_result` slot must not take a caller path.

        `result_path` is declared as an effect_result of
        `plain_goal.bound_capability.grounding`: the capability reads it from
        another capability's output. Filling it from a declared file satisfies
        the letter of the contract while violating its meaning, and the failure
        only surfaces later as an opaque decode error instead of a refusal.
        """
        cid = "plain_goal.bound_capability.grounding.verify.stdlib"
        if cid not in self.model.capabilities:
            self.skipTest("capability not in model")
        try:
            from canonical.runtime import live_integrated_brain_v1 as lb

            entry = dict(lb.load_verified_registry()).get(cid) or {}
        except Exception:
            self.skipTest("registry unavailable")
        spec = (entry.get("proposal_bindings") or {}).get("result_path") or {}
        self.assertEqual(spec.get("type"), "effect_result")

        out = self.model.solve(
            "Compile a plain goal into a bound capability and verify the grounding.",
            context_paths=["canonical/astra_runtime/tmp/BOUND_PDF_TEXT_TEST.pdf"],
        )

        self.assertIs(out.get("pass"), False)
        self.assertTrue(
            str(out.get("reason") or "").startswith("CAPABILITY_INPUTS_MISSING"),
            out.get("reason"),
        )
        self.assertIn("result_path", str(out.get("reason")))
        prov = out.get("binding_provenance") or {}
        self.assertNotIn("result_path", prov.get("filled_from_declared_context") or [])

    def test_a_gate_approved_capability_executes_end_to_end_against_an_independent_oracle(self):
        """Pin the strongest verification path in the system.

        `archive.verify.tar_gz.gnu` passes the execution gate on its own
        evidence, and its adapter cross-checks three things that do not share
        an implementation: GNU `tar -tzf` for the member listing, Python's own
        `tarfile` for the member set, and a source-vs-archive SHA-256
        comparison. Nothing else in the suite exercises a real execution that
        depends on an oracle outside this repository, so a regression in the
        gate, the adapter, or the trace check would otherwise be invisible.

        The two benchmark goals that reach this capability refuse with
        MANIFEST_INPUT_REQUIRED because the sentence names no archive. That
        refusal is correct; this test supplies the resources the sentence
        omitted and asserts the capability really runs.
        """
        cid = "archive.verify.tar_gz.gnu"
        if cid not in self.model.capabilities:
            self.skipTest("capability not in model")
        if shutil.which("tar") is None:
            self.skipTest("GNU tar not present")

        tmp = ROOT / "canonical" / "astra_runtime" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        src = tmp / "_e2e_oracle_src.txt"
        man = tmp / "_e2e_oracle_manifest.json"
        arc = tmp / "_e2e_oracle_bundle.tar.gz"
        rel = [p.relative_to(ROOT).as_posix() for p in (src, man, arc)]
        try:
            src.write_text("end-to-end oracle payload\n", encoding="utf-8")
            man.write_text(
                json.dumps(
                    {"records": [{"verification_paths": [rel[0]]}]},
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            with tarfile.open(arc, "w:gz") as tf:
                tf.add(man, arcname=rel[1])
                tf.add(src, arcname=rel[0])

            out = self.model.solve(
                "Verify a tar.gz archive against its manifest.",
                capability_id=cid,
                inputs={"manifest_path": rel[1], "archive_path": rel[2]},
                context_paths=[rel[1], rel[2]],
            )

            self.assertIs(out.get("pass"), True, out.get("reason"))
            self.assertEqual(
                out.get("status"),
                "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
            )
            # The envelope must report what the adapter established, not a
            # stronger word for it.
            self.assertEqual(
                out.get("status"), (out.get("execution") or {}).get("status")
            )
        finally:
            # Leave nothing behind: canonical/astra_runtime/state is tracked, so
            # a stray artifact would break the next run and the integrity guard.
            for path in (arc, man, src):
                path.unlink(missing_ok=True)

    def test_a_tampered_archive_is_rejected_by_the_oracle_not_accepted(self):
        """The same path must fail when the archive disagrees with its source.

        Without this, the passing test above could be satisfied by a capability
        that always returns verified. Corrupting one byte of the archived copy
        must break the SHA-256 comparison and refuse.
        """
        cid = "archive.verify.tar_gz.gnu"
        if cid not in self.model.capabilities or shutil.which("tar") is None:
            self.skipTest("capability not in model or GNU tar absent")

        tmp = ROOT / "canonical" / "astra_runtime" / "tmp"
        src = tmp / "_e2e_tamper_src.txt"
        man = tmp / "_e2e_tamper_manifest.json"
        arc = tmp / "_e2e_tamper_bundle.tar.gz"
        rel = [p.relative_to(ROOT).as_posix() for p in (src, man, arc)]
        try:
            src.write_text("authoritative source bytes\n", encoding="utf-8")
            man.write_text(
                json.dumps(
                    {"records": [{"verification_paths": [rel[0]]}]},
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            # Archive a DIFFERENT payload under the same member name, so the
            # member set matches but the content hash cannot.
            decoy = tmp / "_e2e_tamper_decoy.txt"
            decoy.write_text("substituted bytes\n", encoding="utf-8")
            with tarfile.open(arc, "w:gz") as tf:
                tf.add(man, arcname=rel[1])
                tf.add(decoy, arcname=rel[0])
            decoy.unlink(missing_ok=True)

            out = self.model.solve(
                "Verify a tar.gz archive against its manifest.",
                capability_id=cid,
                inputs={"manifest_path": rel[1], "archive_path": rel[2]},
                context_paths=[rel[1], rel[2]],
            )
            self.assertIsNot(out.get("pass"), True, out)
        finally:
            for path in (arc, man, src):
                path.unlink(missing_ok=True)

    def test_two_gate_approved_capabilities_compose_producer_then_consumer(self):
        """Pin the composition, not just the parts.

        #5922 pinned `archive.verify.tar_gz.gnu` against an archive the test
        built itself. That leaves the actual claim of a compiled model untested:
        that one capability's output is another's input, through the front door,
        with no hand-built artifact in between.

        Here the producer writes the bundle and the consumer verifies the very
        bytes the producer wrote. The two share no implementation -- the producer
        is Python's `tarfile`, the consumer is GNU `tar` cross-checked against
        `tarfile` and a source SHA-256 -- so agreement between them is real
        corroboration rather than a capability confirming its own output.
        """
        producer = "archive.tar_gz.create_from_manifest"
        consumer = "archive.verify.tar_gz.gnu"
        if producer not in self.model.capabilities:
            self.skipTest("producer not in model")
        if consumer not in self.model.capabilities:
            self.skipTest("consumer not in model")
        if shutil.which("tar") is None:
            self.skipTest("GNU tar not present")

        tmp = ROOT / "canonical" / "astra_runtime" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        src = tmp / "_compose_src.txt"
        man = tmp / "_compose_manifest.json"
        arc = tmp / "_compose_bundle.tar.gz"
        rel = [p.relative_to(ROOT).as_posix() for p in (src, man, arc)]
        try:
            src.write_text("producer-consumer payload\n", encoding="utf-8")
            man.write_text(
                json.dumps(
                    {"records": [{"verification_paths": [rel[0]]}]},
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            built = self.model.solve(
                "Create a tar.gz archive from a manifest.",
                capability_id=producer,
                inputs={"manifest_path": rel[1], "output_path": rel[2]},
                context_paths=[rel[1]],
            )
            self.assertIs(built.get("pass"), True, built.get("reason"))

            # The consumer reads what the producer wrote. Nothing is built by
            # the test between the two calls.
            self.assertTrue((ROOT / rel[2]).is_file(), "producer wrote no archive")
            verified = self.model.solve(
                "Verify a tar.gz archive against its manifest.",
                capability_id=consumer,
                inputs={"manifest_path": rel[1], "archive_path": rel[2]},
                context_paths=[rel[1], rel[2]],
            )
            self.assertIs(verified.get("pass"), True, verified.get("reason"))
            self.assertEqual(
                verified.get("status"),
                "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
            )
            self.assertEqual(
                verified.get("status"),
                (verified.get("execution") or {}).get("status"),
            )
        finally:
            for path in (arc, man, src):
                path.unlink(missing_ok=True)

    def test_a_corrupted_producer_output_is_caught_by_the_consumer(self):
        """The composition must fail if the bytes change between the two steps.

        Without this the passing test above could be satisfied by a consumer
        that trusts the producer. The archive the producer wrote is rewritten
        with substituted bytes under the same member name, so the member set
        still matches and only the content hash can catch it.
        """
        producer = "archive.tar_gz.create_from_manifest"
        consumer = "archive.verify.tar_gz.gnu"
        if (
            producer not in self.model.capabilities
            or consumer not in self.model.capabilities
            or shutil.which("tar") is None
        ):
            self.skipTest("pair not in model or GNU tar absent")

        tmp = ROOT / "canonical" / "astra_runtime" / "tmp"
        src = tmp / "_compose_tamper_src.txt"
        man = tmp / "_compose_tamper_manifest.json"
        arc = tmp / "_compose_tamper_bundle.tar.gz"
        rel = [p.relative_to(ROOT).as_posix() for p in (src, man, arc)]
        try:
            src.write_text("authoritative bytes from the producer\n", encoding="utf-8")
            man.write_text(
                json.dumps(
                    {"records": [{"verification_paths": [rel[0]]}]},
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            built = self.model.solve(
                "Create a tar.gz archive from a manifest.",
                capability_id=producer,
                inputs={"manifest_path": rel[1], "output_path": rel[2]},
                context_paths=[rel[1]],
            )
            self.assertIs(built.get("pass"), True, built.get("reason"))

            # Rebuild the bundle with substituted bytes under the same member
            # names, between the producer and the consumer.
            decoy = tmp / "_compose_tamper_decoy.txt"
            decoy.write_text("substituted after the producer ran\n", encoding="utf-8")
            with tarfile.open(arc, "w:gz") as tf:
                tf.add(man, arcname=rel[1])
                tf.add(decoy, arcname=rel[0])
            decoy.unlink(missing_ok=True)

            verified = self.model.solve(
                "Verify a tar.gz archive against its manifest.",
                capability_id=consumer,
                inputs={"manifest_path": rel[1], "archive_path": rel[2]},
                context_paths=[rel[1], rel[2]],
            )
            self.assertIsNot(verified.get("pass"), True, verified)
        finally:
            for path in (arc, man, src):
                path.unlink(missing_ok=True)

    def test_the_grounding_verifier_passes_only_when_grounding_found_nothing(self):
        """A green check from the grounding verifier certifies emptiness, not success.

        Measured across all 23 benchmark goals: the producer never emits
        ``GROUNDED`` or ``AMBIGUOUS_BOUNDED``. It emits ``UNRESOLVED`` (found
        no candidate) or ``UNBOUND_INPUTS_NOT_GROUNDED`` (found exactly one
        candidate whose proposed bindings do not cover its declared inputs).
        The verifier's accepted vocabulary is the former plus the two statuses
        the producer never emits, so the two capabilities line up as:

            verify PASS  <=>  grounded_clause_count == 0
            grounded >= 1 =>  verify FAIL (STATUS_INVALID)

        That is the opposite of what a passing check looks like from outside.
        This test pins it so a green grounding verification is never mistaken
        for a grounded goal, and so the 16/7 split cannot move unnoticed.

        Widening the verifier to accept ``UNBOUND_INPUTS_NOT_GROUNDED`` would
        invalidate the ``ACQUIRED_VERIFIED`` receipt that pins this adapter's
        git blob byte-for-byte (see the next test), which is why the gap is
        pinned rather than closed here.
        """
        producer = "plain_goal.bound_capability.grounding.stdlib"
        verifier = "plain_goal.bound_capability.grounding.verify.stdlib"
        if not all(c in self.model.capabilities for c in (producer, verifier)):
            self.skipTest("grounding pair not in model")

        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        tmp = ROOT / "canonical" / "astra_runtime" / "tmp"
        out = tmp / "_grounding_invariant.json"
        rel = out.relative_to(ROOT).as_posix()
        never_emitted = {"GROUNDED", "AMBIGUOUS_BOUNDED"}
        passed = failed = 0
        try:
            for case in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS):
                out.unlink(missing_ok=True)
                goal = case["goal"]
                produced = self.model.solve(
                    goal,
                    capability_id=producer,
                    inputs={"goal": goal, "output_path": rel},
                    context_paths=["AGENTS.md"],
                )
                if produced.get("pass") is not True or not out.is_file():
                    continue
                record = json.loads(out.read_text(encoding="utf-8"))
                clauses = record.get("clauses") or []
                statuses = {clause.get("status") for clause in clauses}

                # The producer never reaches a genuinely grounded clause on
                # any benchmark goal. If that ever changes, this invariant is
                # describing a different system and must be re-measured.
                self.assertFalse(
                    statuses & never_emitted,
                    f"{case['id']}: producer now emits {sorted(statuses & never_emitted)}",
                )

                checked = self.model.solve(
                    goal,
                    capability_id=verifier,
                    inputs={"goal": goal, "result_path": rel},
                    context_paths=[rel],
                )
                ok = checked.get("pass") is True
                grounded = record.get("grounded_clause_count") or 0
                if ok:
                    passed += 1
                else:
                    failed += 1
                # The load-bearing claim: PASS means nothing was grounded.
                self.assertEqual(
                    ok,
                    grounded == 0,
                    f"{case['id']}: verify={ok} but grounded_clause_count={grounded}",
                )
        finally:
            out.unlink(missing_ok=True)

        self.assertEqual((passed, failed), (16, 7), "the measured split moved")

    def test_the_grounding_verifier_adapter_still_matches_its_acquisition_receipt(self):
        """The verifier adapter is pinned byte-for-byte by its own receipt.

        ``MODEL_INDEPENDENT_PLAIN_GOAL_BOUND_GROUNDING_ACQUISITION_20260930_V1``
        records ``status: ACQUIRED_VERIFIED`` against CI run 36746452335 and
        pins ``exact_candidate_blobs.verifier``. The registry carries the same
        value as ``verification.verifier_git_blob``, and the adapter on disk
        hashes to exactly it.

        Any edit to that adapter -- including the tempting one-status widening
        of its accepted vocabulary -- silently turns that receipt into a claim
        about code that no longer exists, and the receipt cannot be re-minted
        without fresh independent CI runs. So the blob is asserted here: a
        change must arrive with a new receipt, not quietly beside the old one.
        """
        cid = "plain_goal.bound_capability.grounding.verify.stdlib"
        from canonical.runtime import live_integrated_brain_v1 as live_brain

        entry = dict(live_brain.load_verified_registry()).get(cid)
        if not entry:
            self.skipTest(f"{cid} not in registry")
        pinned = (entry.get("verification") or {}).get("verifier_git_blob")
        adapter = (entry.get("source") or {}).get("adapter_path")
        if not pinned or not adapter:
            self.skipTest("receipt does not pin this adapter")

        path = ROOT / adapter
        self.assertTrue(path.is_file(), f"adapter missing: {adapter}")
        data = path.read_bytes()
        actual = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        self.assertEqual(
            actual,
            pinned,
            f"{adapter} no longer matches verifier_git_blob {pinned}; "
            "the ACQUIRED_VERIFIED receipt describes different code now",
        )

    def test_a_receipt_backed_execution_never_claims_trace_verification(self):
        """`solve()` must report what the adapter established, not more.

        295 of the 367 modelled capabilities are `RECEIPT_BACKED_CAPABILITY`:
        their only evidence is an execution receipt, and the registry marks them
        `RECEIPT_BACKED_PENDING_PROMOTION`. When one runs, the adapter returns
        `PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED`, which states that the
        thing ran, while `solve()` used to relabel every pass as
        `PASS__CAPABILITY_EXECUTED_AND_TRACE_VERIFIED` -- asserting a trace
        check that never ran, on a capability that is explicitly not promoted.

        The distinction is the adapter's own, so the invariant asserted here is
        that the envelope carries it through unchanged. The capability is
        addressed by id: routing no longer offers it for a plain goal, which is
        asserted separately below, and this test is about the envelope's honesty
        once the adapter has actually run.
        """
        target = "canonical/verification/run_long_horizon_continuity_v1.py.auto.v1"
        if target not in self.model.capabilities:
            self.skipTest("receipt-backed probe capability not in model")
        row = self.model.capabilities[target]
        self.assertEqual(row.get("kind"), "RECEIPT_BACKED_CAPABILITY")

        out = self.model.solve("run the long horizon continuity replay", capability_id=target)
        execution = out.get("execution") or {}
        self.assertEqual(
            execution.get("status"),
            "PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED",
            f"probe did not take the receipt-backed path: {execution.get('status')}",
        )

        # The load-bearing claim: the envelope never upgrades the adapter.
        self.assertEqual(out.get("status"), execution.get("status"))
        self.assertNotIn("TRACE_VERIFIED", str(out.get("status")))

    def test_no_pass_status_is_invented_by_the_envelope(self):
        """Every PASS status `solve()` emits must be one the adapter produced.

        The overclaim was a single hard-coded string, so it is pinned
        structurally rather than case by case: on any pass, the envelope status
        and the adapter status are the same string. Both adapter verdicts are
        exercised -- the receipt-backed one and the promoted, trace-verified
        one -- so the assertion covers the distinction rather than one side.
        """
        tmp = ROOT / "canonical" / "astra_runtime" / "tmp"
        src = tmp / "_envelope_src.txt"
        man = tmp / "_envelope_manifest.json"
        arc = tmp / "_envelope_bundle.tar.gz"
        rel = [p.relative_to(ROOT).as_posix() for p in (src, man, arc)]

        receipt_backed = "canonical/verification/run_long_horizon_continuity_v1.py.auto.v1"
        results = []
        if receipt_backed in self.model.capabilities:
            results.append(
                self.model.solve("run the long horizon continuity replay",
                                 capability_id=receipt_backed)
            )
        try:
            if "archive.tar_gz.create_from_manifest" in self.model.capabilities:
                src.write_text("authoritative bytes\n", encoding="utf-8")
                man.write_text(
                    json.dumps({"records": [{"verification_paths": [rel[0]]}]},
                               indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                results.append(
                    self.model.solve(
                        "Create a tar.gz archive from a manifest.",
                        capability_id="archive.tar_gz.create_from_manifest",
                        inputs={"manifest_path": rel[1], "output_path": rel[2]},
                        context_paths=[rel[1]],
                    )
                )
        finally:
            for path in (arc, man, src):
                path.unlink(missing_ok=True)

        checked = 0
        seen_statuses = set()
        for out in results:
            execution = out.get("execution") or {}
            if not execution:
                continue
            checked += 1
            seen_statuses.add(str(execution.get("status")))
            with self.subTest(capability=out.get("capability_id")):
                if out.get("pass") is True:
                    self.assertEqual(
                        out.get("status"),
                        execution.get("status"),
                        "envelope upgraded the adapter's own status",
                    )
                    self.assertTrue(str(out.get("status")).startswith("PASS__"))
                else:
                    self.assertEqual(
                        out.get("status"), "FAIL_CLOSED__CAPABILITY_DID_NOT_PASS"
                    )
        self.assertGreaterEqual(checked, 1, "no goal reached the execution adapter")
        # If both adapter verdicts were reachable, the envelope must have kept
        # them distinct rather than collapsing them onto one string.
        if checked >= 2:
            self.assertEqual(len(seen_statuses), checked, seen_statuses)

    def test_a_short_filename_word_does_not_select_and_run_a_script(self):
        """A common verb must not reach a script via its own filename.

        Receipt-backed capabilities are compiled into the routing index under
        every word of their path, so `run_long_horizon_continuity_v1.py` was
        reachable by the ordinary verb "run". `solve()` then executed that
        script -- `python3 canonical/verification/run_long_horizon_continuity_v1.py`
        -- and reported success for a goal that had nothing to do with it.

        The index now keeps only the tokens the verifier itself treats as a
        capability's triggers: declared triggers that are not path segments and
        are longer than three characters. "run" is three characters, so it is
        not one. The capability stays reachable when addressed by name, which
        the test above relies on.
        """
        target = "canonical/verification/run_long_horizon_continuity_v1.py.auto.v1"
        if target not in self.model.capabilities:
            self.skipTest("probe capability not in model")

        self.assertNotIn("run", self.model._declared_triggers(target))
        self.assertNotIn(
            target,
            self.model.index.get("run") or {},
            "'run' still indexes the script",
        )

        out = self.model.solve("Run the unittest suite and report the pass rate.")
        self.assertIsNot(
            out.get("capability_id"),
            target,
            "a plain goal selected a script on the strength of one short word",
        )
        self.assertIsNot(out.get("pass"), True, out.get("status"))


class VerifierRoutingStabilityTests(unittest.TestCase):
    """The verifier's own routing check must not fail on luck.

    `check_routing` composes goals at run time from a capability's trigger
    words plus two distractor tokens drawn from other capabilities. The script
    itself notes that this can produce an unfair case, where the distractors are
    stronger than the target's own words. That is a property of the generator,
    so the only honest control on it is sample size.

    At 60 draws a single unfair case moved the rate by 1/60 = 0.0167, which was
    enough to cross the 0.80 threshold: measured over 60 seeds driven through
    the script, 3 of 60 runs failed with no code change at all. The threshold
    was not moved to fix this; the sample size was raised to 300, which puts the
    observed mean about 4.8 standard deviations clear of it.

    This test pins that the check is stable across seeds. If the sample size is
    ever reduced again, it fails here rather than intermittently in CI.
    """

    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()

    def test_routing_check_is_stable_across_seeds(self):
        import random

        from canonical.runtime import verify_brain_unified_model_v1 as verifier

        attempts = self._attempts(verifier)
        self.assertGreaterEqual(
            attempts,
            300,
            "reducing the sample size reintroduces a ~5% spurious failure rate",
        )

        gen = random.Random(20261021)
        seeds = [gen.randbytes(8).hex() for _ in range(25)]
        self.assertEqual(len(set(seeds)), len(seeds), "seeds must be distinct")

        failures = []
        for seed in seeds:
            category = verifier.check_routing(self.model, random.Random(seed))
            if not category["pass"]:
                failures.append((seed, category["failed_cases"]))
        self.assertEqual(
            failures,
            [],
            f"check_routing failed on {len(failures)}/25 seeds: {failures[:3]}",
        )

    def test_the_known_unstable_seeds_now_pass(self):
        """Seeds that failed at 60 draws are pinned as passing.

        These are the exact seeds observed failing with no code change, plus one
        that still failed at 150 draws. They are recorded so the fix is tied to
        the instances that motivated it rather than to an average.
        """
        import random

        from canonical.runtime import verify_brain_unified_model_v1 as verifier

        known_bad = [
            "ffd510f92c75fbab",
            "9f4a630e0ed20734",
            "f043de59351b7ddc",
            "53c7c38527d8159b",
            "29fb388c22e44cb6",
        ]
        for seed in known_bad:
            with self.subTest(seed=seed):
                category = verifier.check_routing(self.model, random.Random(seed))
                self.assertTrue(
                    category["pass"],
                    f"seed {seed} regressed: {category['failed_cases']}",
                )

    @staticmethod
    def _attempts(verifier) -> int:
        """Read the sample size the routing check actually uses."""
        import inspect

        source = inspect.getsource(verifier.check_routing)
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("attempts ="):
                return int(stripped.split("=", 1)[1].strip())
        raise AssertionError("could not find the attempts assignment in check_routing")


class DeclaredDependencyEnvironmentIndependenceTests(unittest.TestCase):
    """The artifact must be a function of the tree, not of the compiling machine.

    The compiler used to answer "are this capability's dependencies present?" by
    calling ``shutil.which`` and ``importlib.util.find_spec`` at compile time and
    baking the answers into the artifact. That contradicted the compiler's own
    contract -- "no environment-derived values ... compiling twice from the same
    tree produces byte-identical output".

    It was not theoretical. Installing Pillow and nothing else changed the model
    digest from ``4d7e627e...`` to ``8c158876...`` across six capabilities, and
    the verifier's ``recompilation_is_byte_identical`` case failed on that
    machine -- so ``33/33`` depended on which packages the compiling host had.

    Presence is a property of the machine answering, so it now belongs at run
    time. These tests pin that separation.
    """

    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()

    def test_the_compiler_cannot_probe_the_environment(self):
        """No import that could observe the machine remains in the compiler."""
        for name in ("shutil", "importlib"):
            with self.subTest(module=name):
                self.assertIsNone(
                    getattr(compiler, name, None),
                    f"the compiler imports {name}, so the artifact can depend on the host",
                )

    def test_the_declaration_records_no_presence_verdict(self):
        """`declared_dependencies` states what is needed, never what is installed."""
        forbidden = {"declared_dependencies_present", "declared_dependencies_missing"}
        offenders = {}
        for cid, row in self.model.capabilities.items():
            keys = set((row.get("declared_dependencies") or {}).keys())
            leaked = keys & forbidden
            if leaked:
                offenders[cid] = sorted(leaked)
        self.assertEqual(
            offenders,
            {},
            f"{len(offenders)} capabilities bake a host-specific presence verdict "
            f"into the artifact, e.g. {list(offenders.items())[:3]}",
        )

    def test_the_declaration_is_unchanged_by_a_different_machine(self):
        """Simulating two opposite machines must not move the declaration.

        This is the control that fails if environment probing is reintroduced:
        under a host where every dependency resolves, and one where none does,
        the recorded declaration must be byte-identical.
        """
        import importlib
        import shutil
        from unittest import mock

        entry = {
            "source": {"type": "pypi", "module": "pypdf", "executable": "pdftotext"}
        }
        python_entry = {"source": {"type": "python", "path": "canonical/runtime/goal_compiler.py"}}

        def _declare(everything_present: bool):
            with mock.patch.object(shutil, "which", lambda _n: "/usr/bin/x" if everything_present else None), \
                 mock.patch.object(importlib.util, "find_spec", lambda _n: object() if everything_present else None):
                return [
                    compiler._dependency_declaration(entry, model_runtime.ROOT),
                    compiler._dependency_declaration(python_entry, model_runtime.ROOT),
                ]

        self.assertEqual(
            _declare(True),
            _declare(False),
            "the declaration changed with the simulated host, so the artifact is "
            "still environment-derived",
        )

    def test_status_reports_the_machine_it_actually_runs_on(self):
        """Presence is measured live, so it tracks the real interpreter."""
        status = self.model.status()
        self.assertEqual(status["counts"]["capabilities"], 367)
        self.assertEqual(
            status["declared_dependencies_present"] + status["declared_dependencies_missing"],
            367,
            "present + missing must account for every capability",
        )

        import shutil
        from unittest import mock

        row = self.model.capabilities.get("web.browser.rendered.capture.chromedriver")
        self.assertIsNotNone(row, "the chromedriver capability should exist")

        # This used to assert that chromedriver is *absent*. That is a fact
        # about one host, not a property of the model: GitHub's ubuntu runners
        # ship Chrome and chromedriver, so the assertion held in the sandbox
        # and failed in CI -- measured, 'chromedriver' not found in []. Two
        # claims replace it, and both hold on any machine.

        # 1. The reported answer must agree with an independent live probe of
        #    PATH. That is the actual "tracks the real interpreter" claim, and
        #    it is true whether or not chromedriver is installed here.
        self.assertEqual(
            "chromedriver" in model_runtime._missing_declared_dependencies(row),
            shutil.which("chromedriver") is None,
            "reported presence disagrees with a live probe of PATH, so the "
            "answer is not being measured on this machine",
        )

        # 2. The answer must move when the probe moves. If the value were baked
        #    into the artifact at compile time neither patch would change it and
        #    both assertions would fail -- the regression this exists to catch,
        #    and a strictly stronger test than the absence it replaces.
        with mock.patch.object(shutil, "which", lambda _name: None):
            on_a_bare_host = model_runtime._missing_declared_dependencies(row)
        with mock.patch.object(shutil, "which", lambda _name: "/usr/bin/true"):
            on_a_complete_host = model_runtime._missing_declared_dependencies(row)

        self.assertIn(
            "chromedriver",
            on_a_bare_host,
            "a host without chromedriver on PATH must report it missing",
        )
        self.assertNotIn(
            "chromedriver",
            on_a_complete_host,
            "a host with chromedriver on PATH must not report it missing",
        )


class SourceIndexTests(unittest.TestCase):
    """The model addresses the whole runtime tree without claiming to run it.

    Measured, the capability registry reached 291 of 2189 ``canonical/runtime``
    modules -- 13%. The honest fix is not to promote the rest to capabilities:
    only 404 are entry points, 39 are internal helpers and the remainder are
    imported by nobody, so calling them capabilities would claim execution that
    has never been observed. It is equally wrong to leave 1859 real modules
    invisible to a model that claims to be the whole brain.

    So they are indexed as *source*. These tests pin the line between the two:
    the partition must be exact, and nothing indexed may claim to be executable.
    """

    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()

    def test_the_partition_of_the_runtime_tree_is_exact(self):
        """Every runtime module is either a capability or indexed source, never both."""
        import pathlib

        root = model_runtime.ROOT
        on_disk = {
            p.relative_to(root).as_posix()
            for p in (root / "canonical" / "runtime").rglob("*.py")
            if ".git" not in p.parts
        }

        capability_paths = {
            cid[: -len(".auto.v1")]
            for cid in self.model.capabilities
            if cid.endswith(".auto.v1")
        }
        capability_paths.update(
            str((row.get("provenance") or {}).get("source_path"))
            for row in self.model.capabilities.values()
            if isinstance((row.get("provenance") or {}).get("source_path"), str)
        )
        capability_paths &= on_disk
        indexed = set(self.model.source_index)

        self.assertEqual(
            capability_paths & indexed,
            set(),
            "a module that is already a capability must not also be indexed as "
            "non-executable source -- that is a contradiction on its face",
        )
        self.assertEqual(
            on_disk - capability_paths - indexed,
            set(),
            "every runtime module must be reachable one way or the other",
        )
        self.assertEqual(
            len(capability_paths) + len(indexed),
            len(on_disk),
            "the two sets must partition the tree exactly",
        )

    def test_nothing_indexed_claims_to_be_a_capability(self):
        offenders = {
            path: row.get("capability")
            for path, row in self.model.source_index.items()
            if row.get("capability") is not False
        }
        self.assertEqual(
            offenders,
            {},
            f"{len(offenders)} indexed modules claim capability status",
        )

    def test_find_source_never_reports_something_executable(self):
        """`find_source` answers 'where is this?', never 'run this'."""
        for query in ("pdf text extraction", "docx document verify", "sqlite query"):
            with self.subTest(query=query):
                result = self.model.find_source(query, top_k=10)
                self.assertTrue(result["candidates"], f"no candidates for {query!r}")
                for row in result["candidates"]:
                    self.assertFalse(row["executable"], row["path"])
                    self.assertFalse(row["capability"], row["path"])
                self.assertIn("NOT_EXECUTABLE", result["reason"])

    def test_find_source_is_not_reachable_from_solve(self):
        """Indexing a module must not make `solve()` able to select it."""
        before = set(self.model.capabilities)
        for path in list(self.model.source_index)[:50]:
            self.assertNotIn(path, before, f"{path} leaked into capabilities")
        # And solve() still refuses a goal that only indexed source could serve.
        out = self.model.solve("Inspect the type directed sampler internals.")
        self.assertIs(out.get("pass"), False, out.get("status"))

    def test_idf_outranks_ubiquitous_tokens(self):
        """A rare term must beat one that appears in most of the index.

        This is the control for the original defect: with raw term overlap the
        token "v1" -- present in 1132 of 1859 rows -- decided the ranking, and a
        query for "docx document verify" returned an unrelated module first.
        """
        self.assertGreater(len(self.model.source_index), 1000)
        # "v1" is ubiquitous, so it must carry almost no weight on its own.
        df_v1 = self.model._source_df.get("v1", 0)
        df_docx = self.model._source_df.get("docx", 0)
        self.assertGreater(df_v1, df_docx * 10, "expected v1 to be far more common")

        result = self.model.find_source("docx document verify", top_k=1)
        self.assertIsNotNone(result["best"])
        self.assertIn("docx", result["best"]["path"].casefold())

    def test_counts_declare_the_index_and_stay_true(self):
        counts = self.model.model.get("counts") or {}
        self.assertEqual(
            int(counts.get("source_index_modules", -1)),
            len(self.model.source_index),
        )
        entry_points = sum(
            1
            for row in self.model.source_index.values()
            if row.get("classification") == "ENTRY_POINT"
        )
        self.assertEqual(int(counts.get("source_index_entry_points", -1)), entry_points)
        # The capability count must not have been inflated by indexing.
        self.assertEqual(int(counts.get("capabilities", -1)), 367)

    def test_status_reports_the_source_index_it_holds(self):
        """The model's self-description must not omit what it indexes.

        `status()` builds its counts from a hardcoded list, so adding a section
        to the artifact does not make it appear here. Measured after the source
        index shipped: the artifact declared `source_index_modules: 1859` while
        `status()` reported no source figure at all -- asking the model what it
        is returned an answer that never mentioned 1859 of the modules it holds.

        The counts are derived live from what the model actually loaded rather
        than read back from the declared block, so they cannot drift.
        """
        status = self.model.status()
        counts = status["counts"]

        self.assertEqual(
            int(counts.get("source_index_modules", -1)),
            len(self.model.source_index),
        )
        self.assertGreater(int(counts["source_index_modules"]), 1000)

        self.assertEqual(
            int(counts.get("source_index_entry_points", -1)),
            sum(
                1
                for row in self.model.source_index.values()
                if row.get("classification") == "ENTRY_POINT"
            ),
        )

        # The distinction must be stated wherever the larger number appears, so
        # it cannot be read as a capability gain.
        self.assertIs(status.get("source_index_is_addressable_not_executable"), True)
        self.assertEqual(int(counts["capabilities"]), 367)

    def test_status_does_not_overcount_reachable_modules(self):
        """A tempting derived figure that is wrong must not be reported.

        `len(capabilities) + len(source_index)` is 2223, but only 330 of the 367
        capabilities are runtime files -- 69 are named or bound entries -- so the
        true figure is 2189. Deriving it correctly needs a filesystem walk, which
        would put host coupling back inside `status()`. Reporting nothing is
        better than reporting 2222.
        """
        status = self.model.status()
        self.assertNotIn("runtime_modules_reachable", status)
        self.assertNotIn("runtime_modules_reachable", status["counts"])


class ResearchIndexTests(unittest.TestCase):
    """The research record is indexed as evidence, never as capability.

    Governance decisions, verification receipts and action intents are the
    reasoning behind the capabilities -- 6256 files that were previously
    unreachable through the model. They are indexed so `find_research` can
    answer "where was this decided?", with the same line held as the source
    index: a record is evidence *about* a capability, never a capability.
    """

    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()

    def test_the_research_corpora_are_indexed(self):
        roots = ("canonical/governance/", "canonical/verification/", "canonical/action_intents/")
        counts = {r: 0 for r in roots}
        for path in self.model.research_index:
            for r in roots:
                if path.startswith(r):
                    counts[r] += 1
        for root, n in counts.items():
            with self.subTest(root=root):
                self.assertGreater(n, 100, f"{root} should be substantially indexed, got {n}")
        self.assertGreater(len(self.model.research_index), 6000)

    def test_no_research_record_claims_to_be_a_capability(self):
        offenders = {
            path: row.get("capability")
            for path, row in self.model.research_index.items()
            if row.get("capability") is not False
        }
        self.assertEqual(offenders, {}, f"{len(offenders)} records claim capability status")

    def test_generated_outputs_are_excluded_so_the_compile_converges(self):
        """The receipt is written *from* the artifact, so it must not be in it.

        This is the control for a real cycle, not a hypothetical one. Indexing
        the verification receipt inside the artifact makes the build diverge:
        the artifact hashes the receipt, the receipt records the artifact's
        digest, so each recompile changes the other. Measured, the digest
        differed on every pass until these paths were excluded.

        Note this is a genuine cycle and not the same as `source_index` hashing
        the runtime module -- that converges, because the module does not embed
        the digest.
        """
        for path in sorted(compiler._GENERATED_OUTPUTS):
            with self.subTest(path=path):
                self.assertNotIn(path, self.model.research_index)
                self.assertNotIn(path, self.model.source_index)

    def test_the_compile_is_a_fixed_point(self):
        """Recompiling must not move the digest.

        The artifact hashes files it lives beside, so a self-referential index
        shows up here rather than in CI. This is the end-to-end form of the
        exclusion test above.
        """
        model = compiler.compile_model()
        again = compiler.compile_model()
        self.assertEqual(
            model["digest"]["value"],
            again["digest"]["value"],
            "compiling twice produced different digests -- the build is not a fixed point",
        )
        self.assertEqual(model["digest"]["value"], self.model.digest)

    def test_find_research_ranks_by_rare_terms_not_ubiquitous_ones(self):
        """'v1' occurs in 79% of these records, so raw overlap would be noise."""
        df_v1 = self.model._research_df.get("v1", 0)
        total = len(self.model.research_index)
        self.assertGreater(df_v1, total * 0.5, "expected v1 to be ubiquitous")

        result = self.model.find_research("verifier routing sample size", top_k=5)
        self.assertTrue(result["candidates"])
        self.assertIn("EVIDENCE_NOT_CAPABILITY", result["reason"])
        for row in result["candidates"]:
            self.assertFalse(row["capability"])
        best = result["best"]["path"].casefold()
        self.assertIn("sample_size", best)

    def test_find_research_is_not_reachable_from_solve(self):
        indexed = set(self.model.research_index)
        self.assertTrue(indexed)
        for path in list(indexed)[:50]:
            self.assertNotIn(path, self.model.capabilities)

    def test_status_reports_the_research_index(self):
        counts = self.model.status()["counts"]
        self.assertEqual(
            int(counts.get("research_index_records", -1)),
            len(self.model.research_index),
        )
        self.assertEqual(int(counts["capabilities"]), 367)
