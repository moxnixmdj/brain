import json

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
