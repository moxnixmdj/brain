import inspect
import json

import pytest

from canonical.runtime import astra_runtime
from canonical.runtime.certificate_gated_bound_capability_dispatch_v1 import (
    CertifiedRouteBindingError,
    context_digest,
    git_blob_sha_bytes,
    resolve_dispatch,
)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _fixture(tmp_path, *, context=None):
    context = context or {"domain": "test", "request": {"value": 7}}
    route_rel = "canonical/runtime/bound_capabilities/test_route.py"
    adequacy_rel = "canonical/verification/test_route_adequacy.json"
    admission_rel = "canonical/governance/test_route_admission.json"
    independent_rel = "canonical/verification/test_route_admission_verify.json"

    route = _write(
        tmp_path / route_rel,
        "def run(args, root):\n    return {'output_verified': True, 'value': args.get('value')}\n",
    )
    adequacy = _write(
        tmp_path / adequacy_rel,
        json.dumps(
            {
                "schema": "TEST_ADEQUACY_V1",
                "status": "PASS",
                "pass": True,
            },
            sort_keys=True,
        )
        + "\n",
    )
    route_sha = git_blob_sha_bytes(route.read_bytes())
    adequacy_sha = git_blob_sha_bytes(adequacy.read_bytes())

    admission_doc = {
        "schema": "PROJECT_BRAIN_SELECTED_ROUTE_ADMISSION_CERTIFICATE_V1",
        "status": "PASS",
        "pass": True,
        "context_digest": context_digest(context),
        "cell_id": "TEST_CELL",
        "route_id": "test.route",
        "route_blob_sha": route_sha,
        "adequacy_certificate_path": adequacy_rel,
        "adequacy_certificate_blob_sha": adequacy_sha,
        "independent_verification_path": independent_rel,
    }
    admission = _write(
        tmp_path / admission_rel,
        json.dumps(admission_doc, indent=2, sort_keys=True) + "\n",
    )
    admission_sha = git_blob_sha_bytes(admission.read_bytes())

    _write(
        tmp_path / independent_rel,
        json.dumps(
            {
                "schema": "PROJECT_BRAIN_SELECTED_ROUTE_ADMISSION_INDEPENDENT_VERIFICATION_V1",
                "status": "PASS",
                "pass": True,
                "subject_path": admission_rel,
                "subject_git_blob_sha": admission_sha,
                "context_digest": context_digest(context),
                "cell_id": "TEST_CELL",
                "route_id": "test.route",
                "route_path": route_rel,
                "route_blob_sha": route_sha,
                "adequacy_certificate_path": adequacy_rel,
                "adequacy_certificate_blob_sha": adequacy_sha,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    registry = {
        "test.route": {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "adapter_module": "test_route",
            "source": {
                "type": "python_stdlib",
                "adapter_path": route_rel,
                "module": "json",
            },
        }
    }
    args = {
        "context": context,
        "admission_certificate_paths": [admission_rel],
        "route_args_by_id": {"test.route": {"value": 7}},
    }
    return {
        "context": context,
        "route": route,
        "adequacy": adequacy,
        "admission": admission,
        "registry": registry,
        "args": args,
        "route_sha": route_sha,
        "adequacy_sha": adequacy_sha,
        "admission_sha": admission_sha,
    }


def test_content_bound_admission_selects_exact_verified_route(tmp_path):
    fx = _fixture(tmp_path)
    out = resolve_dispatch(root=tmp_path, args=fx["args"], registry=fx["registry"])
    assert out["status"] == "PASS__CERTIFICATE_GATED_ROUTE_SELECTED_AND_CONTENT_BOUND"
    assert out["actual_context_digest"] == context_digest(fx["context"])
    assert out["route_id"] == "test.route"
    assert out["cell_id"] == "TEST_CELL"
    assert out["route_blob_sha"] == fx["route_sha"]
    assert out["adequacy_certificate_blob_sha"] == fx["adequacy_sha"]
    assert out["admission_certificate_blob_sha"] == fx["admission_sha"]
    assert out["route_args"] == {"value": 7}


def test_route_byte_drift_fails_before_dispatch(tmp_path):
    fx = _fixture(tmp_path)
    fx["route"].write_text(
        "def run(args, root):\n    return {'output_verified': False}\n",
        encoding="utf-8",
    )
    with pytest.raises(CertifiedRouteBindingError, match="ROUTE_BLOB_SHA_MISMATCH"):
        resolve_dispatch(root=tmp_path, args=fx["args"], registry=fx["registry"])


def test_actual_context_drift_fails_before_dispatch(tmp_path):
    fx = _fixture(tmp_path)
    bad = dict(fx["args"])
    bad["context"] = {"domain": "test", "request": {"value": 8}}
    with pytest.raises(CertifiedRouteBindingError, match="ADMISSION_CONTEXT_DIGEST_MISMATCH"):
        resolve_dispatch(root=tmp_path, args=bad, registry=fx["registry"])


def test_independent_verification_binding_is_load_bearing(tmp_path):
    fx = _fixture(tmp_path)
    independent = tmp_path / "canonical/verification/test_route_admission_verify.json"
    doc = json.loads(independent.read_text(encoding="utf-8"))
    doc["route_blob_sha"] = "0" * 40
    independent.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(
        CertifiedRouteBindingError,
        match="ADMISSION_INDEPENDENT_VERIFICATION_BINDING_MISMATCH:route_blob_sha",
    ):
        resolve_dispatch(root=tmp_path, args=fx["args"], registry=fx["registry"])


def test_missing_actual_context_fails_closed(tmp_path):
    fx = _fixture(tmp_path)
    bad = dict(fx["args"])
    bad.pop("context")
    with pytest.raises(CertifiedRouteBindingError, match="ACTUAL_CONTEXT_REQUIRED"):
        resolve_dispatch(root=tmp_path, args=bad, registry=fx["registry"])


def test_astra_action_executes_only_router_selected_capability(monkeypatch):
    class StubHelper:
        @staticmethod
        def resolve_dispatch(*, root, args, registry):
            return {
                "schema": "PROJECT_BRAIN_CERTIFICATE_GATED_BOUND_CAPABILITY_DISPATCH_V1",
                "status": "PASS__CERTIFICATE_GATED_ROUTE_SELECTED_AND_CONTENT_BOUND",
                "actual_context_digest": "c" * 64,
                "cell_id": "CELL",
                "route_id": "selected.capability",
                "route_blob_sha": "1" * 40,
                "adequacy_certificate_blob_sha": "2" * 40,
                "admission_certificate_blob_sha": "3" * 40,
                "admission_certificate_path": "canonical/governance/admission.json",
                "independent_verification_path": "canonical/verification/admission_verify.json",
                "route_path": "canonical/runtime/bound_capabilities/selected.py",
                "adequacy_certificate_path": "canonical/verification/adequacy.json",
                "route_args": {"value": 9},
            }

    original_loader = astra_runtime._load_runtime_helper

    def load_helper(name):
        if name == "certificate_gated_bound_capability_dispatch_v1":
            return StubHelper
        return original_loader(name)

    called = {}

    def invoke(args):
        called.update(args)
        return {"output_verified": True, "value": args["value"]}

    monkeypatch.setattr(astra_runtime, "_load_runtime_helper", load_helper)
    monkeypatch.setattr(astra_runtime, "_load_bound_capability_registry", lambda: {})
    monkeypatch.setattr(astra_runtime, "_invoke_bound_capability", invoke)

    result = astra_runtime._goal_action(
        {
            "type": "invoke_certified_capability",
            "args": {
                "context": {"x": 1},
                "admission_certificate_paths": ["unused-by-stub"],
                "route_args_by_id": {"unused": {}},
            },
        }
    )
    assert called == {"capability_id": "selected.capability", "value": 9}
    assert result["output_verified"] is True
    assert result["certificate_gated_dispatch"]["route_id"] == "selected.capability"
    assert "route_args" not in result["certificate_gated_dispatch"]


def test_model_independent_controller_allowlist_includes_certified_route_action():
    source = inspect.getsource(astra_runtime._run_model_independent_goal)
    assert '"invoke_certified_capability"' in source
