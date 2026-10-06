from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest import mock

from canonical.runtime import astra_runtime as runtime
from canonical.runtime import continuous_obs_runtime as obs
from canonical.runtime import root3_production_astra_launcher_v1 as launcher


class _FakeResponse:
    status = 200
    headers = {}
    def __init__(self, url: str):
        self._url = url
    def geturl(self):
        return self._url
    def read(self, n=-1):
        return b"ok"
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _open_discovery_context() -> dict:
    pointer = json.loads((runtime.ROOT / "canonical/CANONICAL_POINTER.json").read_text(encoding="utf-8"))
    return {
        "schema": obs.SCHEMA,
        "status": "CURRENT",
        "canonical_generation": pointer["canonical_generation"],
        "dependency_inventory_complete": True,
        "material_world_state_dependencies_complete": True,
        "information_boundary_complete": True,
        "information_policy": {
            "mode": "OPEN_DISCOVERY",
            "allowed_exact_sources": [],
            "allowed_external_tool_kinds": [],
        },
        "unknown_material_dependencies": [],
        "stale_authority_absent": True,
        "valid_proof_action_priority": True,
        "obs_layers_current": {
            key: True for key in obs.REQUIRED_LAYERS
        },
        "canonical_state_dependencies": [
            {
                "path": rel,
                "sha256": _sha(runtime.ROOT / rel),
            }
            for rel in obs.REQUIRED_STATE_PATHS
        ],
        "dependencies": [
            {
                "dependency_id": "root3-parent-network-countermodel",
                "class": "EXECUTION_SURFACE",
                "material": True,
                "volatility": "STATIC",
                "scope": "TASK_SPECIFIC",
                "status": "READY",
                "evidence": ["current production ASTRA bytes"],
            }
        ],
    }


def test_current_open_discovery_information_policy_authorizes_url():
    context = _open_discovery_context()
    verdict = obs.authorize_information_action(
        context,
        {
            "kind": "EXACT_FETCH",
            "source": "https://example.test/data",
            "tool_kind": "urlopen",
        },
        root=runtime.ROOT,
    )
    assert verdict["pass"] is True, verdict


def test_parent_direct_network_fallback_reaches_original_host_urlopen_without_root3_broker():
    context = _open_discovery_context()
    host_calls = []
    receipts = []
    helper_loads = []

    def fake_host_urlopen(request, timeout=20, *args, **kwargs):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        host_calls.append({"url": url, "timeout": timeout})
        return _FakeResponse(url)

    original_loader = runtime._load_runtime_helper

    def observing_loader(name):
        helper_loads.append(str(name))
        if name == "root3_effect_broker_bridge_v1":
            raise AssertionError("ROOT3_BROKER_SHOULD_HAVE_BEEN_LOAD_BEARING_BEFORE_HOST_NETWORK")
        return original_loader(name)

    old_context = runtime._ACTIVE_CONTINUOUS_OBS_CONTEXT
    old_module = runtime._ACTIVE_CONTINUOUS_OBS_MODULE
    old_mid = runtime._ACTIVE_CONTINUOUS_OBS_MISSION_ID
    try:
        runtime._ACTIVE_CONTINUOUS_OBS_CONTEXT = context
        runtime._ACTIVE_CONTINUOUS_OBS_MODULE = obs
        runtime._ACTIVE_CONTINUOUS_OBS_MISSION_ID = "ROOT3-NETWORK-COUNTERMODEL"
        with (
            mock.patch.dict(runtime.os.environ, {}, clear=False),
            mock.patch.object(runtime, "_ORIGINAL_URLOPEN", side_effect=fake_host_urlopen),
            mock.patch.object(runtime, "_append_admin_jsonl", side_effect=lambda p, x: receipts.append(x)),
            mock.patch.object(runtime, "_load_runtime_helper", side_effect=observing_loader),
        ):
            runtime.os.environ.pop("PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR", None)
            response = runtime._bridge_aware_urlopen("https://example.test/data", timeout=7)
            assert response.status == 200
    finally:
        runtime._ACTIVE_CONTINUOUS_OBS_CONTEXT = old_context
        runtime._ACTIVE_CONTINUOUS_OBS_MODULE = old_module
        runtime._ACTIVE_CONTINUOUS_OBS_MISSION_ID = old_mid

    assert host_calls == [{"url": "https://example.test/data", "timeout": 7}]
    assert any(x.get("phase") == "ATTEMPT" for x in receipts)
    assert any(x.get("phase") == "OPENED" for x in receipts)
    assert "root3_effect_broker_bridge_v1" not in helper_loads


def test_production_launcher_binds_subprocess_guard_not_namespace_membrane():
    source = Path(launcher.__file__).read_text(encoding="utf-8")
    assert "root3_strict_current_bootstrap_v2" in source
    assert "root3_two_class_attempt_authorizer_v1" in source
    assert "zero_ambient_namespace_launcher_v1" not in source
    assert "root3_effect_broker_bridge_v1" not in source
