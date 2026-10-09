from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import canonical.runtime.astra_runtime as astra
import canonical.runtime.verified_bound_capability_execution_adapter_v1 as promoted


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class BoundDFinalityProviderHardeningTests(unittest.TestCase):
    def test_promoted_executor_rejects_registry_drift_before_invocation(self):
        prepared = {
            "capability_id": "cap:test",
            "instance_id": "cap:test",
            "requires": [],
            "provides": ["effect:test"],
            "result_fields": [],
            "inputs_sha256": "1" * 64,
            "registry_file_sha256": "2" * 64,
            "registry_entry_sha256": "3" * 64,
            "rendered_action_sha256": "4" * 64,
            "rendered_action": {
                "type": "invoke_capability",
                "args": {"capability_id": "cap:test"},
            },
        }
        called = {"value": False}

        def forbidden(*args, **kwargs):
            called["value"] = True
            raise AssertionError("invocation must not occur after registry drift")

        with patch.object(promoted, "prepare", lambda *a, **k: dict(prepared)), \
             patch.object(
                 promoted,
                 "inspect",
                 lambda cid: {
                     "capability_id": cid,
                     "entry": {
                         "cost": 1,
                         "requires": [],
                         "provides": ["effect:test"],
                     },
                     "registry_file_sha256": "9" * 64,
                     "registry_entry_sha256": "3" * 64,
                 },
             ), \
             patch.object(astra, "_invoke_bound_capability_entry", forbidden):
            out = promoted.execute("cap:test", inputs={})

        self.assertFalse(out["pass"])
        self.assertTrue(
            any("REGISTRY_FILE_CHANGED_AFTER_PREPARATION" in x for x in out["errors"])
        )
        self.assertFalse(called["value"])

    def test_astra_public_bound_wrapper_loads_registry_once_then_uses_frozen_entry(self):
        calls = {"loads": 0, "entry_calls": 0}
        frozen = {
            "incremental_spend_usd": 0,
            "source": {},
            "adapter_module": "unused",
        }

        def load():
            calls["loads"] += 1
            return {"cap:test": frozen}

        def invoke_entry(args, entry):
            calls["entry_calls"] += 1
            self.assertIs(entry, frozen)
            return {"capability_id": args["capability_id"], "ok": True}

        with patch.object(astra, "_load_bound_capability_registry", load), \
             patch.object(astra, "_invoke_bound_capability_entry", invoke_entry):
            out = astra._invoke_bound_capability({"capability_id": "cap:test"})

        self.assertTrue(out["ok"])
        self.assertEqual(calls, {"loads": 1, "entry_calls": 1})

    def test_active_d_epoch_executes_exact_checked_adapter_bytes_without_importlib_reread(self):
        cid = "archive.tar_gz.create_from_manifest"
        entry = astra._load_bound_capability_registry()[cid]
        adapter_path = astra.ROOT / "canonical/runtime/bound_capabilities/archive_tarfile.py"
        rel = adapter_path.resolve().relative_to(astra.ROOT.resolve()).as_posix()
        expected_blob = _git_blob(adapter_path)
        fake_epoch = SimpleNamespace(material_bindings=((rel, expected_blob),))

        def forbidden_loader(*args, **kwargs):
            raise AssertionError("importlib path loader reopened adapter during D epoch")

        temp_dir = astra.ROOT / "canonical/astra_runtime/tmp/d-final-provider-hardening"
        temp_dir.mkdir(parents=True, exist_ok=True)
        source = temp_dir / "source.txt"
        manifest = temp_dir / "manifest.json"
        output = temp_dir / "bundle.tar.gz"
        source.write_text("provider-hardening", encoding="utf-8")
        manifest.write_text(
            '{"records":[{"verification_paths":["'
            + source.relative_to(astra.ROOT).as_posix()
            + '"]}]}',
            encoding="utf-8",
        )
        try:
            with patch.object(astra.d_finality, "has_active_epoch", lambda: True), \
                 patch.object(
                     astra.d_finality,
                     "require_material_file_if_active",
                     lambda *a, **k: fake_epoch,
                 ), \
                 patch.object(astra.d_finality, "current_epoch", lambda: fake_epoch), \
                 patch.object(astra.importlib.util, "spec_from_file_location", forbidden_loader):
                result = astra._invoke_bound_capability_entry(
                    {
                        "capability_id": cid,
                        "manifest_path": manifest.relative_to(astra.ROOT).as_posix(),
                        "output_path": output.relative_to(astra.ROOT).as_posix(),
                    },
                    dict(entry),
                )
            self.assertTrue(result["output_verified"])
            self.assertTrue(output.is_file())
        finally:
            output.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)
            source.unlink(missing_ok=True)
            try:
                temp_dir.rmdir()
            except OSError:
                pass

    def test_active_d_epoch_rejects_adapter_blob_mismatch_before_exec(self):
        cid = "archive.tar_gz.create_from_manifest"
        entry = astra._load_bound_capability_registry()[cid]
        adapter_path = astra.ROOT / "canonical/runtime/bound_capabilities/archive_tarfile.py"
        rel = adapter_path.resolve().relative_to(astra.ROOT.resolve()).as_posix()
        fake_epoch = SimpleNamespace(material_bindings=((rel, "0" * 40),))

        with patch.object(astra.d_finality, "has_active_epoch", lambda: True), \
             patch.object(
                 astra.d_finality,
                 "require_material_file_if_active",
                 lambda *a, **k: fake_epoch,
             ), \
             patch.object(astra.d_finality, "current_epoch", lambda: fake_epoch):
            with self.assertRaisesRegex(
                Exception, "BOUND_CAPABILITY_ADAPTER_CHANGED_AFTER_EPOCH_CHECK"
            ):
                astra._invoke_bound_capability_entry(
                    {"capability_id": cid},
                    dict(entry),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
