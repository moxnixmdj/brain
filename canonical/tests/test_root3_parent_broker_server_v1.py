from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import tempfile

import pytest

from canonical.runtime import root3_parent_broker_server_v1 as srv
from canonical.runtime import root3_typed_durable_admin_write_v1 as admin
from canonical.runtime import root3_broker_rpc_v1 as rpc


def mkrepo(tmp_path:pathlib.Path)->pathlib.Path:
    for rel in (
        "canonical/astra_runtime/state",
        "canonical/astra_runtime/evidence",
        "canonical/same_identity_worker/external_tool_bridge/T1",
    ):
        (tmp_path/rel).mkdir(parents=True,exist_ok=True)
    return tmp_path


def req(kind,payload):
    return rpc.build_request(
        kind=kind,agent_id="A1",task_id="T1",payload=payload
    )


def test_ping():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        broker=srv.ParentBroker(repo_root=root)
        assert broker.handle(req("PING",{}))=={"pong":True}


def test_durable_admin_write_uses_existing_typed_commit():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        payload=b'{"x":1}\n'
        plan=admin.build_plan(
            operation="REPLACE",
            destination_class="ASTRA_STATE_JSON",
            path="canonical/astra_runtime/state/T1.json",
            payload=payload,
            expected_pre_sha256="ABSENT",
        )
        broker=srv.ParentBroker(repo_root=root)
        out=broker.handle(req("DURABLE_ADMIN_WRITE",{
            "plan":plan,
            "payload_b64":base64.b64encode(payload).decode(),
        }))
        assert out["status"]=="COMMITTED"
        assert (root/"canonical/astra_runtime/state/T1.json").read_bytes()==payload


def test_durable_admin_wrong_prestate_denied():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        target=root/"canonical/astra_runtime/state/T1.json"
        target.write_text('{"old":1}\n')
        payload=b'{"x":1}\n'
        plan=admin.build_plan(
            operation="REPLACE",
            destination_class="ASTRA_STATE_JSON",
            path="canonical/astra_runtime/state/T1.json",
            payload=payload,
            expected_pre_sha256="ABSENT",
        )
        broker=srv.ParentBroker(repo_root=root)
        with pytest.raises(srv.ParentBrokerDenied,match="PRESTATE_MISMATCH"):
            broker.handle(req("DURABLE_ADMIN_WRITE",{
                "plan":plan,
                "payload_b64":base64.b64encode(payload).decode(),
            }))


def test_external_tool_relay_preserves_existing_request_contract():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        bridge=root/"canonical/same_identity_worker/external_tool_bridge/T1"
        tool_payload={"url":"https://example.invalid/data","timeout_s":1}
        base={
            "schema":srv.EXTERNAL_REQUEST_SCHEMA,
            "kind":"http_get",
            "agent_id":"A1",
            "task_id":"T1",
            "payload":tool_payload,
        }
        sha=hashlib.sha256(
            json.dumps(base,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
        ).hexdigest()
        response={
            "schema":srv.EXTERNAL_RESPONSE_SCHEMA,
            "request_sha256":sha,
            "kind":"http_get",
            "agent_id":"A1",
            "task_id":"T1",
            "status":"ok",
            "result":{"url":"https://example.invalid/data","status":200,"body_sha256":"a"*64,"body_excerpt":"ok"},
        }
        (bridge/(sha+".response.json")).write_text(json.dumps(response))
        broker=srv.ParentBroker(
            repo_root=root,
            external_bridge_dir=str(bridge),
            external_wait_seconds=0,
        )
        out=broker.handle(req("EXTERNAL_TOOL",{
            "tool_kind":"http_get",
            "tool_payload":tool_payload,
        }))
        assert out["status"]==200
        observed=json.loads((bridge/(sha+".request.json")).read_text())
        assert observed["request_sha256"]==sha
        assert observed["agent_id"]=="A1"
        assert observed["task_id"]=="T1"


def test_external_bridge_task_scope_escape_denied():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        outside=root/"elsewhere"
        outside.mkdir()
        broker=srv.ParentBroker(
            repo_root=root,
            external_bridge_dir=str(outside),
        )
        with pytest.raises(srv.ParentBrokerDenied,match="BRIDGE_DIR_IDENTITY_MISMATCH"):
            broker.handle(req("EXTERNAL_TOOL",{
                "tool_kind":"http_get","tool_payload":{}
            }))


def test_unknown_kind_denied():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        broker=srv.ParentBroker(repo_root=root)
        with pytest.raises(srv.ParentBrokerDenied,match="BROKER_KIND_DENIED"):
            broker.handle(req("ARBITRARY_HOST_EFFECT",{}))


def test_admin_payload_tamper_denied_by_existing_plan_hash():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        good=b'{"x":1}\n'
        bad=b'{"x":2}\n'
        plan=admin.build_plan(
            operation="REPLACE",
            destination_class="ASTRA_EVIDENCE_JSON",
            path="canonical/astra_runtime/evidence/T1.json",
            payload=good,
            expected_pre_sha256="ABSENT",
        )
        broker=srv.ParentBroker(repo_root=root)
        with pytest.raises(srv.ParentBrokerDenied,match="PAYLOAD_HASH_MISMATCH"):
            broker.handle(req("DURABLE_ADMIN_WRITE",{
                "plan":plan,
                "payload_b64":base64.b64encode(bad).decode(),
            }))
