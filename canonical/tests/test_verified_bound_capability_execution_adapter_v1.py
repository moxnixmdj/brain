import json
import pathlib
import tempfile

import canonical.runtime.verified_bound_capability_execution_adapter_v1 as subject
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import (
    inspect,
    execute,
)


def test_inspect_rejects_nonexistent_capability():
    try:
        inspect("definitely.not.present")
        assert False, "expected failure"
    except Exception as exc:
        assert "BOUND_CAPABILITY_UNKNOWN" in str(exc)


def test_verified_stdlib_archive_entry_is_admissible_for_execution():
    out = inspect("archive.tar_gz.create_from_manifest")
    assert out["entry"]["status"] == "VERIFIED_BOUND_CAPABILITY"
    assert out["entry"]["incremental_spend_usd"] == 0
    assert len(out["registry_file_sha256"]) == 64
    assert len(out["registry_entry_sha256"]) == 64


def test_execute_manifest_archive_through_promoted_registry_and_reverify_trace(tmp_path, monkeypatch):
    # The bound archive adapter is repository-root confined. Create a tiny manifest
    # under the actual repo's ephemeral Astra directory rather than tmp_path.
    from canonical.runtime.verified_bound_capability_execution_adapter_v1 import ROOT
    temp_dir = ROOT / "canonical/astra_runtime/tmp/bound-exec-test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    source = temp_dir / "source.txt"
    manifest = temp_dir / "manifest.json"
    output = temp_dir / "bundle.tar.gz"
    source.write_text("alpha", encoding="utf-8")
    manifest.write_text(
        json.dumps({
            "verification_paths": [str(source.relative_to(ROOT)).replace("\\", "/")]
        }),
        encoding="utf-8",
    )
    if output.exists():
        output.unlink()
    out = execute(
        "archive.tar_gz.create_from_manifest",
        inputs={
            "manifest_path": str(manifest.relative_to(ROOT)).replace("\\", "/"),
            "output_path": str(output.relative_to(ROOT)).replace("\\", "/"),
        },
    )
    assert out["pass"] is True, out
    assert out["execution_verification"]["pass"] is True
    assert out["composition_capsule_head_hash"]
    assert output.is_file()
    output.unlink()
    manifest.unlink()
    source.unlink()


def test_missing_template_input_fails_closed():
    out = execute(
        "archive.tar_gz.create_from_manifest",
        inputs={"manifest_path": "x.json"},
    )
    assert out["pass"] is False
    assert any("BOUND_TEMPLATE_RENDER_FAILED" in x for x in out["errors"])



def test_execute_uses_one_frozen_registry_entry_without_reread(monkeypatch):
    calls = {"inspect": 0}
    frozen_entry = {
        "status": "VERIFIED_BOUND_CAPABILITY",
        "incremental_spend_usd": 0,
        "verification": {"producer_independent": True},
        "action_template": {
            "type": "invoke_capability",
            "args": {"capability_id": "cap.test"},
        },
        "requires": [],
        "provides": ["effect.test"],
        "result_fields": [],
        "cost": 1,
        "source": {},
        "adapter_module": "unused",
        "entrypoint": "run",
    }

    def fake_inspect(capability_id):
        calls["inspect"] += 1
        if calls["inspect"] > 1:
            raise AssertionError("registry was re-read after preparation")
        return {
            "capability_id": capability_id,
            "entry": dict(frozen_entry),
            "registry_file_sha256": "1" * 64,
            "registry_entry_sha256": "2" * 64,
        }

    monkeypatch.setattr(subject, "inspect", fake_inspect)
    monkeypatch.setattr(
        subject.astra_runtime,
        "_render_bound_template",
        lambda template, inputs: {
            "type": "invoke_capability",
            "args": {"capability_id": "cap.test"},
        },
    )
    monkeypatch.setattr(
        subject,
        "_invoke_frozen_bound_capability",
        lambda entry, args, expected_adapter_git_blob_sha=None: (
            {"output_verified": True},
            "3" * 40,
        ),
    )
    monkeypatch.setattr(subject.astra_runtime, "_verify_action_expectation", lambda a, r: None)
    monkeypatch.setattr(
        subject,
        "plan_actions",
        lambda problem: {"actions": [{"type": "invoke_capability"}, {"type": "finish"}]},
    )
    monkeypatch.setattr(
        subject,
        "verify_execution",
        lambda payload, proposal: {
            "pass": True,
            "verified_output": {"capsule_head_hash": "4" * 64},
        },
    )

    out = subject.execute("cap.test", inputs={})
    assert out["pass"] is True, out
    assert calls["inspect"] == 1
    assert out["adapter_git_blob_sha"] == "3" * 40


def test_frozen_adapter_copy_executes_captured_bytes_even_if_source_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    adapter_dir = tmp_path / "canonical/runtime/bound_capabilities"
    adapter_dir.mkdir(parents=True)
    adapter_path = adapter_dir / "frozen_probe.py"
    old_source = b'def run(args, root):\n    return {"marker":"OLD"}\n'
    new_source = b'def run(args, root):\n    return {"marker":"NEW"}\n'
    adapter_path.write_bytes(old_source)
    expected = subject._git_blob_sha(old_source)

    real_tempdir = tempfile.TemporaryDirectory

    class MutatingTemporaryDirectory:
        def __init__(self, *args, **kwargs):
            self.inner = real_tempdir(*args, **kwargs)

        def __enter__(self):
            adapter_path.write_bytes(new_source)
            return self.inner.__enter__()

        def __exit__(self, exc_type, exc, tb):
            return self.inner.__exit__(exc_type, exc, tb)

    monkeypatch.setattr(subject.tempfile, "TemporaryDirectory", MutatingTemporaryDirectory)
    entry = {
        "source": {},
        "adapter_module": "frozen_probe",
        "entrypoint": "run",
    }
    result, observed = subject._invoke_frozen_bound_capability(
        entry,
        {"capability_id": "cap.test"},
        expected_adapter_git_blob_sha=expected,
    )
    assert observed == expected
    assert result["marker"] == "OLD"
    assert adapter_path.read_bytes() == new_source


def test_wrong_expected_adapter_blob_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    adapter_dir = tmp_path / "canonical/runtime/bound_capabilities"
    adapter_dir.mkdir(parents=True)
    adapter_path = adapter_dir / "frozen_probe.py"
    adapter_path.write_text('def run(args, root):\n    return {"ok": True}\n', encoding="utf-8")
    entry = {
        "source": {},
        "adapter_module": "frozen_probe",
        "entrypoint": "run",
    }
    try:
        subject._invoke_frozen_bound_capability(
            entry,
            {"capability_id": "cap.test"},
            expected_adapter_git_blob_sha="0" * 40,
        )
        assert False, "expected adapter blob mismatch"
    except Exception as exc:
        assert "BOUND_CAPABILITY_ADAPTER_BLOB_MISMATCH" in str(exc)
