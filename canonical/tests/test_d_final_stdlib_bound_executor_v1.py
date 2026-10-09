import hashlib
import json
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import d_final_stdlib_bound_executor_v1 as ex


def canon_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class DFinalStdlibBoundExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = ex.ROOT / "canonical/astra_runtime/tmp/d-final-stdlib-executor-tests"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for p in sorted(self.tmp.rglob("*"), reverse=True):
            try:
                if p.is_file() or p.is_symlink():
                    p.unlink()
                elif p.is_dir():
                    p.rmdir()
            except OSError:
                pass
        try:
            self.tmp.rmdir()
        except OSError:
            pass

    def test_nonstdlib_registry_row_is_rejected(self):
        with self.assertRaisesRegex(ex.DFinalStdlibBoundError, "NON_STDLIB_SOURCE_REJECTED"):
            ex.inspect("pdf.extract.text.pypdf")

    def test_missing_template_input_fails_closed(self):
        out = ex.execute(
            "archive.tar_gz.create_from_manifest",
            inputs={"manifest_path": "canonical/astra_runtime/tmp/missing.json"},
        )
        self.assertFalse(out["pass"])
        self.assertTrue(any("BOUND_CAPABILITY_INPUT_MISSING" in x for x in out["errors"]))

    def test_archive_executes_through_small_kernel_and_trace_reverifies(self):
        source = self.tmp / "source.txt"
        manifest = self.tmp / "manifest.json"
        output = self.tmp / "bundle.tar.gz"
        source.write_text("fresh-kernel-archive", encoding="utf-8")
        manifest.write_text(
            json.dumps({
                "records": [{
                    "verification_paths": [
                        source.relative_to(ex.ROOT).as_posix()
                    ]
                }]
            }),
            encoding="utf-8",
        )
        prepared = ex.prepare(
            "archive.tar_gz.create_from_manifest",
            inputs={
                "manifest_path": manifest.relative_to(ex.ROOT).as_posix(),
                "output_path": output.relative_to(ex.ROOT).as_posix(),
            },
        )
        out = ex.execute(
            "archive.tar_gz.create_from_manifest",
            inputs={
                "manifest_path": manifest.relative_to(ex.ROOT).as_posix(),
                "output_path": output.relative_to(ex.ROOT).as_posix(),
            },
            expected_registry_file_sha256=prepared["registry_file_sha256"],
            expected_registry_entry_sha256=prepared["registry_entry_sha256"],
            expected_rendered_action_sha256=prepared["rendered_action_sha256"],
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["execution_verification"]["pass"], out)
        self.assertTrue(out["composition_capsule_head_hash"], out)
        self.assertEqual(out["dependency"]["type"], "python_stdlib")
        self.assertTrue(output.is_file())

    def test_registry_pin_mismatch_fails_closed(self):
        prepared = ex.prepare(
            "archive.tar_gz.create_from_manifest",
            inputs={
                "manifest_path": "canonical/astra_runtime/tmp/a.json",
                "output_path": "canonical/astra_runtime/tmp/a.tar.gz",
            },
        )
        out = ex.execute(
            "archive.tar_gz.create_from_manifest",
            inputs={
                "manifest_path": "canonical/astra_runtime/tmp/a.json",
                "output_path": "canonical/astra_runtime/tmp/a.tar.gz",
            },
            expected_registry_file_sha256="0" * 64,
            expected_registry_entry_sha256=prepared["registry_entry_sha256"],
            expected_rendered_action_sha256=prepared["rendered_action_sha256"],
        )
        self.assertFalse(out["pass"])
        self.assertTrue(any("REGISTRY_FILE_CHANGED_AFTER_PREPARATION" in x for x in out["errors"]))

    def test_decision_verifier_fresh_valid_and_tampered_result(self):
        nonce = "kernel-test"
        problem = {
            "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
            "decision_id": "KERNEL",
            "question": "Choose A",
            "alternatives": [{"id": "A", "label": "A"}],
            "constraints": [{
                "id": "c1",
                "alternative": "A",
                "required": True,
                "state": "SATISFIED",
                "description": nonce,
                "provenance": [{"source": "test", "ref": nonce}],
            }],
            "evidence": [{
                "id": "e1",
                "alternative": "A",
                "relation": "SUPPORTS",
                "confidence": 0.8,
                "strength": 1.0,
                "independence_group": "g1",
                "claim": nonce,
                "provenance": [{"source": "test", "ref": nonce}],
            }],
            "policy": {
                "minimum_support_ratio": 0.6,
                "maximum_conflict_ratio": 0.5,
                "minimum_independent_support_groups": 1,
                "minimum_net_margin": 0.1,
            },
        }
        result = {
            "schema": "PROJECT_BRAIN_TYPED_DECISION_RESULT_V1",
            "decision_id": "KERNEL",
            "input_sha256": canon_hash(problem),
            "status": "DECIDED",
            "selected_alternative": "A",
            "model_dependency_count": 0,
            "rankings": [{
                "alternative": "A",
                "constraint_state": "ADMISSIBLE",
                "violated_constraints": [],
                "unknown_constraints": [],
                "support_score": 0.8,
                "contradiction_score": 0.0,
                "net_score": 0.8,
                "support_ratio": 1.0,
                "conflict_ratio": 0.0,
                "independent_support_groups": ["g1"],
                "independent_contradiction_groups": [],
                "contributing_evidence": ["e1"],
                "eligible": True,
            }],
            "trace": [{"step": 1}, {"step": 2}, {"step": 3}, {"step": 4}],
        }
        input_path = self.tmp / "decision-input.json"
        result_path = self.tmp / "decision-result.json"
        input_path.write_text(json.dumps(problem), encoding="utf-8")
        result_path.write_text(json.dumps(result), encoding="utf-8")

        prepared = ex.prepare(
            "decision.synthesis.verify.stdlib",
            inputs={
                "input_path": input_path.relative_to(ex.ROOT).as_posix(),
                "result_path": result_path.relative_to(ex.ROOT).as_posix(),
            },
        )
        out = ex.execute(
            "decision.synthesis.verify.stdlib",
            inputs={
                "input_path": input_path.relative_to(ex.ROOT).as_posix(),
                "result_path": result_path.relative_to(ex.ROOT).as_posix(),
            },
            expected_registry_file_sha256=prepared["registry_file_sha256"],
            expected_registry_entry_sha256=prepared["registry_entry_sha256"],
            expected_rendered_action_sha256=prepared["rendered_action_sha256"],
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["result"]["verified"], out)
        self.assertEqual(out["result"]["model_dependency_count"], 0)

        tampered = dict(result)
        tampered["selected_alternative"] = None
        result_path.write_text(json.dumps(tampered), encoding="utf-8")
        bad = ex.execute(
            "decision.synthesis.verify.stdlib",
            inputs={
                "input_path": input_path.relative_to(ex.ROOT).as_posix(),
                "result_path": result_path.relative_to(ex.ROOT).as_posix(),
            },
        )
        self.assertFalse(bad["pass"])
        self.assertTrue(any("ACTION_EXPECTATION_FAILED:verified" in x for x in bad["errors"]))

    def test_registry_drift_between_prepare_and_second_inspect_fails_before_adapter_load(self):
        prepared = {
            "capability_id": "archive.tar_gz.create_from_manifest",
            "instance_id": "archive.tar_gz.create_from_manifest",
            "requires": ["manifest.json.available"],
            "provides": ["archive.tar_gz.create_from_manifest"],
            "result_fields": [],
            "inputs": {},
            "inputs_sha256": "1" * 64,
            "registry_file_sha256": "2" * 64,
            "registry_entry_sha256": "3" * 64,
            "rendered_action": {
                "type": "invoke_capability",
                "args": {"capability_id": "archive.tar_gz.create_from_manifest"},
            },
            "rendered_action_sha256": "4" * 64,
            "dependency": {"type": "python_stdlib"},
        }
        called = {"value": False}

        def forbidden(entry):
            called["value"] = True
            raise AssertionError("adapter load must not occur after registry drift")

        with patch.object(ex, "prepare", lambda *a, **k: dict(prepared)), \
             patch.object(
                 ex,
                 "inspect",
                 lambda cid: {
                     "capability_id": cid,
                     "entry": {"cost": 1},
                     "registry_file_sha256": "9" * 64,
                     "registry_entry_sha256": "3" * 64,
                     "dependency": {"type": "python_stdlib"},
                 },
             ), \
             patch.object(ex, "_load_adapter", forbidden):
            out = ex.execute("archive.tar_gz.create_from_manifest", inputs={})
        self.assertFalse(out["pass"])
        self.assertTrue(
            any("REGISTRY_FILE_CHANGED_AFTER_PREPARATION" in x for x in out["errors"])
        )
        self.assertFalse(called["value"])

    def test_active_d_epoch_uses_exact_checked_adapter_bytes_without_path_reopen(self):
        cid = "archive.tar_gz.create_from_manifest"
        entry = ex.inspect(cid)["entry"]
        adapter = ex.ROOT / "canonical/runtime/bound_capabilities/archive_tarfile.py"
        rel = adapter.resolve().relative_to(ex.ROOT.resolve()).as_posix()
        expected = ex.d_finality.git_blob_sha_file(adapter)
        fake_epoch = SimpleNamespace(material_bindings=((rel, expected),))

        def forbidden_loader(*args, **kwargs):
            raise AssertionError("importlib path loader reopened adapter during active D epoch")

        with patch.object(ex.d_finality, "has_active_epoch", lambda: True), \
             patch.object(
                 ex.d_finality,
                 "require_material_file_if_active",
                 lambda *a, **k: fake_epoch,
             ), \
             patch.object(ex.d_finality, "current_epoch", lambda: fake_epoch), \
             patch.object(ex.importlib.util, "spec_from_file_location", forbidden_loader):
            fn = ex._load_adapter(entry)
        self.assertTrue(callable(fn))

    def test_active_d_epoch_rejects_adapter_blob_mismatch_before_exec(self):
        cid = "archive.tar_gz.create_from_manifest"
        entry = ex.inspect(cid)["entry"]
        adapter = ex.ROOT / "canonical/runtime/bound_capabilities/archive_tarfile.py"
        rel = adapter.resolve().relative_to(ex.ROOT.resolve()).as_posix()
        fake_epoch = SimpleNamespace(material_bindings=((rel, "0" * 40),))

        with patch.object(ex.d_finality, "has_active_epoch", lambda: True), \
             patch.object(
                 ex.d_finality,
                 "require_material_file_if_active",
                 lambda *a, **k: fake_epoch,
             ), \
             patch.object(ex.d_finality, "current_epoch", lambda: fake_epoch):
            with self.assertRaisesRegex(
                ex.DFinalStdlibBoundError,
                "BOUND_CAPABILITY_ADAPTER_CHANGED_AFTER_EPOCH_CHECK",
            ):
                ex._load_adapter(entry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
