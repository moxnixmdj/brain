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


# ---------------------------------------------------------------------------
# Loader-admitted (receipt-backed) capabilities.
#
# Measured before this path existed: the ownership manifest admits them through
# VERIFIED_BOUND_CAPABILITIES, whose selector is live_integrated_brain_v1.load_verified_registry,
# and the single front door (live_capability_invoker_v1, authority-pinned) routes `bound:<id>`
# here for every one of them. This adapter answered BOUND_CAPABILITY_UNKNOWN for all 294, so
# invocation coverage was green on their id prefix while dispatch failed in fact.
# ---------------------------------------------------------------------------

def _a_receipt_backed_capability_id(adapter_module=None):
    from canonical.runtime import live_integrated_brain_v1 as live_brain
    live_brain._REGISTRY_CACHE.clear()
    for cid, entry in sorted(live_brain.load_verified_registry().items()):
        if entry.get("capability_source") != "receipt_projection":
            continue
        if adapter_module is None or entry.get("adapter_module") == adapter_module:
            return cid
    assert False, "no loader-admitted receipt-backed capability found"


def test_receipt_backed_ids_are_absent_from_the_promoted_registry():
    """The reason this path must exist at all."""
    cid = _a_receipt_backed_capability_id()
    try:
        inspect(cid)
        assert False, "a receipt-backed capability was found in the promoted registry"
    except Exception as exc:
        assert "BOUND_CAPABILITY_UNKNOWN" in str(exc)


def test_unknown_capability_still_fails_closed():
    out = execute("definitely.not.present", inputs={})
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert "BOUND_CAPABILITY_UNKNOWN" in str(out["errors"])


def test_receipt_backed_capability_executes_and_reports_its_evidence():
    """Real execution: the entry comes from the loader, the run from run_adapter_locally."""
    cid = _a_receipt_backed_capability_id(adapter_module="cli_command")
    out = execute(cid, inputs={})
    assert out["pass"] is True, out
    assert out["status"] == "PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED"
    assert out["execution_authority"] == (
        "LOADER_ADMITTED_EXECUTION_RECEIPT_WITH_INDEPENDENT_OIDC_ATTESTED_REPRODUCTION")
    assert out["receipt_path"] and out["module_sha256"]
    assert out["incremental_spend_usd"] == 0
    # it must NOT claim the promoted-registry digests it never checked
    assert "registry_entry_sha256" not in out


def test_a_tool_that_reports_its_own_failure_never_returns_pass(monkeypatch):
    from canonical.runtime import live_brain_route_admission_v1 as route_admission
    cid = _a_receipt_backed_capability_id(adapter_module="cli_command")
    monkeypatch.setattr(route_admission, "run_adapter_locally",
                        lambda entry, action: {"capability_id": cid, "status": "UNRESOLVED"})
    out = execute(cid, inputs={})
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert "NON_SUCCESS" in str(out["errors"])


def test_caller_inputs_cannot_change_the_capability_id(monkeypatch):
    from canonical.runtime import live_brain_route_admission_v1 as route_admission
    cid = _a_receipt_backed_capability_id(adapter_module="cli_command")
    seen = {}
    monkeypatch.setattr(route_admission, "run_adapter_locally",
                        lambda entry, action: seen.update(entry=entry, action=action) or {"returncode": 0})
    out = execute(cid, inputs={"capability_id": "someone.else"})
    assert out["pass"] is True
    assert seen["entry"]["capability_id"] == cid
    assert seen["action"]["args"]["capability_id"] == cid


def test_the_advertised_bound_prefix_reaches_the_same_execution():
    """catalog() advertises live-owned ids in the invoker's `bound:` spelling, and the fabric's
    {capability_id, inputs} route passes that spelling through unstripped.  Measured before:
    both the 294 receipt-backed and the 67 promoted capabilities answered
    BOUND_CAPABILITY_UNKNOWN through that door - 408 advertised ids, 0 dispatched."""
    cid = _a_receipt_backed_capability_id()
    bare = execute(cid, inputs={})
    prefixed = execute("bound:" + cid, inputs={})
    assert bare["pass"] is True
    assert prefixed["status"] == bare["status"]
    assert prefixed["pass"] == bare["pass"]
    assert prefixed["receipt_path"] == bare["receipt_path"]


def test_another_capability_kind_is_never_silently_treated_as_bound():
    """Only `bound:` is this adapter's kind; an engine id must not be looked up in the
    promoted registry as if it were a bound capability."""
    out = execute("engine:ADAPTIVE_SOLVER", inputs={})
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert "BOUND_CAPABILITY_UNKNOWN" in str(out["errors"])
