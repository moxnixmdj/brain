from __future__ import annotations

import base64
import json
import pathlib
from types import SimpleNamespace
from unittest import mock

import pytest

from canonical.runtime import root3_confined_astra_entry_v1 as entry
from canonical.runtime import root3_typed_durable_admin_write_v1 as admin


def fake_astra(tmp_path:pathlib.Path, order:list[str]|None=None):
    order=order if order is not None else []
    class Blocker(RuntimeError):
        pass
    def authorize(kind,payload):
        order.append("authorize:"+str(kind))
        return {"pass":True}
    return SimpleNamespace(
        ROOT=tmp_path,
        Blocker=Blocker,
        _authorize_external_information=authorize,
        _load_runtime_helper=lambda name: admin if name=="root3_typed_durable_admin_write_v1" else (_ for _ in ()).throw(AssertionError(name)),
        _admin_expected_prestate=lambda p:"ABSENT",
        _typed_admin_commit=lambda *a,**k:(_ for _ in ()).throw(AssertionError("LOCAL_ADMIN_COMMIT_USED")),
        _external_tool_bridge=lambda *a,**k:(_ for _ in ()).throw(AssertionError("LOCAL_EXTERNAL_BRIDGE_USED")),
    )


def test_install_transport_pings_and_replaces_exact_two_chokepoints(tmp_path,monkeypatch):
    calls=[]
    def call(fd,**kw):
        calls.append((fd,kw))
        if kw["kind"]=="PING":
            return {"pong":True}
        return {"ok":True}
    monkeypatch.setattr(entry.rpc,"call_fd",call)
    astra=fake_astra(tmp_path)
    out=entry.install_effect_transport(astra,fd=9,agent_id="A1",task_id="T1")
    assert out["broker_ping"] is True
    assert calls==[(9,{"kind":"PING","agent_id":"A1","task_id":"T1","payload":{}})]
    assert callable(astra._typed_admin_commit)
    assert callable(astra._external_tool_bridge)


def test_external_tool_authorizes_before_broker_call(tmp_path,monkeypatch):
    order=[]
    def call(fd,**kw):
        order.append("broker:"+kw["kind"])
        return {"pong":True} if kw["kind"]=="PING" else {"status":200}
    monkeypatch.setattr(entry.rpc,"call_fd",call)
    astra=fake_astra(tmp_path,order)
    entry.install_effect_transport(astra,fd=9,agent_id="A1",task_id="T1")
    order.clear()
    out=astra._external_tool_bridge("http_get",{"url":"https://example.invalid"})
    assert out=={"status":200}
    assert order==["authorize:http_get","broker:EXTERNAL_TOOL"]


def test_durable_admin_builds_existing_plan_then_brokers_payload(tmp_path,monkeypatch):
    calls=[]
    def call(fd,**kw):
        calls.append(kw)
        return {"pong":True} if kw["kind"]=="PING" else {"status":"COMMITTED"}
    monkeypatch.setattr(entry.rpc,"call_fd",call)
    astra=fake_astra(tmp_path)
    entry.install_effect_transport(astra,fd=9,agent_id="A1",task_id="T1")
    payload=b'{"x":1}\n'
    target=tmp_path/"canonical/astra_runtime/state/T1.json"
    out=astra._typed_admin_commit(target,payload,"ASTRA_STATE_JSON","REPLACE")
    assert out["status"]=="COMMITTED"
    req=calls[-1]
    assert req["kind"]=="DURABLE_ADMIN_WRITE"
    plan=req["payload"]["plan"]
    assert plan["path"]=="canonical/astra_runtime/state/T1.json"
    assert plan["destination_class"]=="ASTRA_STATE_JSON"
    assert plan["operation"]=="REPLACE"
    assert base64.b64decode(req["payload"]["payload_b64"])==payload


def test_broker_error_propagates_fail_closed(tmp_path,monkeypatch):
    n={"count":0}
    def call(fd,**kw):
        n["count"]+=1
        if kw["kind"]=="PING":
            return {"pong":True}
        raise entry.rpc.BrokerProtocolError("BROKER_REQUEST_FAILED:DENY")
    monkeypatch.setattr(entry.rpc,"call_fd",call)
    astra=fake_astra(tmp_path)
    entry.install_effect_transport(astra,fd=9,agent_id="A1",task_id="T1")
    with pytest.raises(entry.rpc.BrokerProtocolError,match="DENY"):
        astra._external_tool_bridge("http_get",{"url":"https://example.invalid"})
    assert n["count"]==2


def test_load_astra_installs_subprocess_guards_before_import(monkeypatch):
    order=[]
    fake=SimpleNamespace(__file__="/input/canonical/runtime/astra_runtime.py")
    monkeypatch.setattr(
        entry.bootstrap,"install_current",
        lambda authorizer,authority_id: order.append("install") or {
            "run_guard_active":True,"popen_guard_active":True
        },
    )
    monkeypatch.setattr(
        entry.bootstrap.mediator,"status",
        lambda:{"run_guard_active":True,"popen_guard_active":True},
    )
    monkeypatch.setattr(
        entry.importlib,"import_module",
        lambda name: order.append("import:"+name) or fake,
    )
    got=entry.load_astra_inside_membrane()
    assert got is fake
    assert order==["install","import:canonical.runtime.astra_runtime"]


def test_load_astra_rejects_lost_guard(monkeypatch):
    fake=SimpleNamespace(__file__="/input/canonical/runtime/astra_runtime.py")
    monkeypatch.setattr(
        entry.bootstrap,"install_current",
        lambda authorizer,authority_id: {
            "run_guard_active":True,"popen_guard_active":True
        },
    )
    monkeypatch.setattr(entry.importlib,"import_module",lambda name:fake)
    monkeypatch.setattr(
        entry.bootstrap.mediator,"status",
        lambda:{"run_guard_active":False,"popen_guard_active":True},
    )
    with pytest.raises(entry.ConfinedEntryError,match="GUARDS_LOST"):
        entry.load_astra_inside_membrane()


def test_mission_identity_defaults_task_to_mission(tmp_path,monkeypatch):
    p=tmp_path/"mission.json"
    p.write_text(json.dumps({"mission_id":"M1"}),encoding="utf-8")
    monkeypatch.delenv("PROJECT_BRAIN_AGENT_ID",raising=False)
    monkeypatch.delenv("PROJECT_BRAIN_TASK_ID",raising=False)
    agent,task,mission=entry._mission_identity(p)
    assert agent=="ASTRA-PARENT-MEMBRANE-V1"
    assert task=="M1"
    assert mission["mission_id"]=="M1"


def test_invalid_ambient_identity_fails_closed(tmp_path,monkeypatch):
    p=tmp_path/"mission.json"
    p.write_text(json.dumps({"mission_id":"M1"}),encoding="utf-8")
    monkeypatch.setenv("PROJECT_BRAIN_TASK_ID","../escape")
    with pytest.raises(entry.ConfinedEntryError,match="TASK_ID_INVALID"):
        entry._mission_identity(p)
