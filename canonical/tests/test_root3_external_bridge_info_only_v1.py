from __future__ import annotations

import urllib.request
from pathlib import Path

import pytest

from canonical.runtime import astra_runtime
from canonical.runtime.root3_external_bridge_info_only_v1 import compile_surface


ASTRA_BLOB="f4f0d3c0bfa412fb43485e3b9bc09b3cde263e6d"


def test_post_is_rejected_before_bridge_invocation(monkeypatch):
    calls=[]
    monkeypatch.setattr(
        astra_runtime,
        "_external_tool_bridge",
        lambda *args,**kwargs: calls.append((args,kwargs)),
    )
    req=urllib.request.Request(
        "https://example.invalid/resource",
        data=b"x=1",
        method="POST",
    )
    with pytest.raises(
        astra_runtime.Blocker,
        match="EXTERNAL_URLOPEN_INFORMATION_ONLY_METHOD_FORBIDDEN:POST",
    ):
        astra_runtime._bridge_aware_urlopen(req)
    assert calls==[]


def test_bodyless_get_reaches_information_bridge(monkeypatch):
    seen=[]
    def bridge(kind,payload):
        seen.append((kind,payload))
        return {
            "status":200,
            "final_url":"https://example.invalid/resource",
            "body_b64":"",
            "headers":{},
        }
    monkeypatch.setattr(astra_runtime,"_external_tool_bridge",bridge)
    req=urllib.request.Request("https://example.invalid/resource",method="GET")
    with astra_runtime._bridge_aware_urlopen(req) as resp:
        assert resp.status==200
        assert resp.read()==b""
    assert seen[0][0]=="urlopen"
    assert seen[0][1]["method"]=="GET"
    assert seen[0][1]["data_b64"] is None


def test_static_bridge_surface_is_frozen():
    root=Path(__file__).resolve().parents[2]
    out=compile_surface(root,ASTRA_BLOB)
    assert out["all_bridge_kinds_literal"] is True
    assert out["urlopen_bodyless_get_only"] is True
    assert out["bridge_kinds"]==[
        "http_get",
        "package_name_search",
        "planner",
        "pypi_wheel_closure",
        "python_source_tree",
        "urlopen",
    ]
    assert out["external_process_internal_effect_totality_proved"] is False
    assert out["acceptance_credit_delta"]==0
