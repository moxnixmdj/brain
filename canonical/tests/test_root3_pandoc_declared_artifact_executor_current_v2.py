from __future__ import annotations

import base64
import hashlib
import pathlib
import subprocess
import tempfile

from canonical.runtime import root3_pandoc_declared_artifact_executor_v1 as ex


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def context(root: pathlib.Path) -> dict:
    src = root / "in.md"
    src.write_text("# Hello\n", encoding="utf-8")
    out = root / "canonical/astra_runtime/artifacts/out.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    return {
        "effect_class": "DECLARED_ARTIFACT_PRODUCTION",
        "api": "subprocess.run",
        "args": (
            [
                "pandoc",
                str(src),
                "-o",
                str(out),
                "--pdf-engine=weasyprint",
            ],
        ),
        "kwargs": {
            "cwd": root,
            "text": True,
            "capture_output": True,
            "timeout": 120,
        },
        "callsite": {
            "module_path":
                "canonical/runtime/bound_capabilities/pandoc_weasyprint.py",
            "lineno": 24,
            "process_api": "subprocess.run",
        },
    }


def identity():
    return {
        "mission_id": "m1",
        "capsule_head_sha256": "c" * 64,
        "action_ref": "composition:0:deadbeef",
        "astra_runtime_git_blob_sha": ex.composition_context.EXPECTED_ASTRA_BLOB,
    }


def patch_prepare_for_temp_root(monkeypatch, root: pathlib.Path):
    monkeypatch.setattr(ex, "ROOT", root)
    monkeypatch.setattr(
        ex,
        "ARTIFACT_ROOT",
        (root / "canonical/astra_runtime/artifacts").resolve(),
    )
    monkeypatch.setattr(
        ex,
        "_resolved_system_tool",
        lambda name: pathlib.Path("/usr/bin/" + name),
    )
    monkeypatch.setattr(
        ex,
        "_toolchain_sha",
        lambda pandoc, weasyprint: "b" * 64,
    )


def test_wrong_callsite_denies_before_child(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        patch_prepare_for_temp_root(monkeypatch, root)
        c = context(root)
        c["callsite"]["lineno"] = 25
        try:
            ex._prepare(c)
        except ex.DeclaredArtifactExecutorDenied as exc:
            assert "CALLSITE_NOT_SUPPORTED" in str(exc)
        else:
            raise AssertionError("wrong callsite accepted")


def test_destination_outside_reserved_artifact_root_denies(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        patch_prepare_for_temp_root(monkeypatch, root)
        c = context(root)
        c["args"][0][3] = str(root / "escape.pdf")
        try:
            ex._prepare(c)
        except ex.DeclaredArtifactExecutorDenied as exc:
            assert "PDF_OUTPUT_NOT_RESERVED_ARTIFACT_ROOT" in str(exc)
        else:
            raise AssertionError("outside destination accepted")


def test_nonzero_child_never_calls_finalizer(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        patch_prepare_for_temp_root(monkeypatch, root)
        c = context(root)
        called = []

        def confined(spec, popen_impl):
            return {
                "timed_out": False,
                "returncode": 7,
                "stdout_b64": "",
                "stderr_b64": base64.b64encode(b"bad").decode(),
            }

        monkeypatch.setattr(
            ex.finalizer,
            "commit",
            lambda *a, **k: called.append((a, k)),
        )
        runner = ex.make_executor(
            popen_impl=lambda *a, **k: None,
            context_provider=identity,
            repo_root=root,
            confined_runner=confined,
        )
        cp = runner(c)
        assert cp.returncode == 7
        assert called == []
        assert not (
            root / "canonical/astra_runtime/artifacts/out.pdf"
        ).exists()


def test_successful_child_delegates_only_durable_commit_to_finalizer(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        patch_prepare_for_temp_root(monkeypatch, root)
        c = context(root)
        payload = b"%PDF-1.7\ncurrent\n"
        calls = []

        def confined(spec, popen_impl):
            pathlib.Path(spec["output_dir"], "result.pdf").write_bytes(payload)
            return {
                "timed_out": False,
                "returncode": 0,
                "stdout_b64": base64.b64encode(b"ok").decode(),
                "stderr_b64": "",
            }

        def fake_build_plan(**kw):
            calls.append(("build_plan", dict(kw)))
            return {
                **kw,
                "artifact_sha256": sha(kw["payload"]),
            }

        def fake_request(plan, raw):
            calls.append(("effect_request", dict(plan)))
            return {
                "request_sha256": "r" * 64,
                "payload_sha256": sha(raw),
            }

        def fake_grant(request):
            calls.append(("grant", dict(request)))
            return {"grant_sha256": "g" * 64}

        def fake_commit(repo_root, plan, raw, grant):
            calls.append(("commit", {
                "repo_root": str(repo_root),
                "plan": dict(plan),
                "grant": dict(grant),
                "payload_sha256": sha(raw),
            }))
            dst = repo_root / plan["destination_path"]
            dst.write_bytes(raw)
            return {
                "status": "COMMITTED",
                "destination_path": plan["destination_path"],
                "post_sha256": sha(raw),
                "exact_readback": True,
            }

        monkeypatch.setattr(ex.finalizer, "build_plan", fake_build_plan)
        monkeypatch.setattr(ex.finalizer, "effect_request", fake_request)
        monkeypatch.setattr(ex, "_artifact_grant", fake_grant)
        monkeypatch.setattr(ex.finalizer, "commit", fake_commit)

        runner = ex.make_executor(
            popen_impl=lambda *a, **k: None,
            context_provider=identity,
            repo_root=root,
            confined_runner=confined,
        )
        cp = runner(c)
        assert cp.returncode == 0
        assert [x[0] for x in calls] == [
            "build_plan", "effect_request", "grant", "commit"
        ]
        assert (
            root / "canonical/astra_runtime/artifacts/out.pdf"
        ).read_bytes() == payload


def test_composition_identity_blob_mismatch_denies_before_finalizer(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        patch_prepare_for_temp_root(monkeypatch, root)
        c = context(root)
        payload = b"%PDF-1.7\ncurrent\n"
        called = []

        def confined(spec, popen_impl):
            pathlib.Path(spec["output_dir"], "result.pdf").write_bytes(payload)
            return {
                "timed_out": False,
                "returncode": 0,
                "stdout_b64": "",
                "stderr_b64": "",
            }

        bad = identity()
        bad["astra_runtime_git_blob_sha"] = "0" * 40
        monkeypatch.setattr(
            ex.finalizer,
            "commit",
            lambda *a, **k: called.append((a, k)),
        )
        runner = ex.make_executor(
            popen_impl=lambda *a, **k: None,
            context_provider=lambda: bad,
            repo_root=root,
            confined_runner=confined,
        )
        try:
            runner(c)
        except ex.DeclaredArtifactExecutorDenied as exc:
            assert "ASTRA_CONTEXT_BLOB_MISMATCH" in str(exc)
        else:
            raise AssertionError("bad composition identity accepted")
        assert called == []


def test_invalid_finalizer_receipt_denies(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        patch_prepare_for_temp_root(monkeypatch, root)
        c = context(root)
        payload = b"%PDF-1.7\ncurrent\n"

        def confined(spec, popen_impl):
            pathlib.Path(spec["output_dir"], "result.pdf").write_bytes(payload)
            return {
                "timed_out": False,
                "returncode": 0,
                "stdout_b64": "",
                "stderr_b64": "",
            }

        monkeypatch.setattr(
            ex.finalizer,
            "build_plan",
            lambda **kw: kw,
        )
        monkeypatch.setattr(
            ex.finalizer,
            "effect_request",
            lambda plan, raw: {
                "request_sha256": "r" * 64,
                "payload_sha256": sha(raw),
            },
        )
        monkeypatch.setattr(
            ex,
            "_artifact_grant",
            lambda request: {"grant_sha256": "g" * 64},
        )
        monkeypatch.setattr(
            ex.finalizer,
            "commit",
            lambda *a, **k: {
                "status": "COMMITTED",
                "destination_path":
                    "canonical/astra_runtime/artifacts/out.pdf",
                "post_sha256": "0" * 64,
                "exact_readback": True,
            },
        )
        runner = ex.make_executor(
            popen_impl=lambda *a, **k: None,
            context_provider=identity,
            repo_root=root,
            confined_runner=confined,
        )
        try:
            runner(c)
        except ex.DeclaredArtifactExecutorDenied as exc:
            assert "FINALIZER_RECEIPT_INVALID" in str(exc)
        else:
            raise AssertionError("invalid finalizer receipt accepted")
