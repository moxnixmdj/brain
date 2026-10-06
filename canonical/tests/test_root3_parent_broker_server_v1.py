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


def req(kind,payload,agent="A1",task="T1"):
    return rpc.build_request(
        kind=kind,agent_id=agent,task_id=task,payload=payload
    )


def broker(root,**kw):
    return srv.ParentBroker(
        repo_root=root,
        expected_agent_id="A1",
        expected_task_id="T1",
        mission_id="M1",
        information_context={"test":True},
        **kw,
    )


def state_payload(status="RUNNING"):
    return (
        json.dumps({
            "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1",
            "mission_id":"M1",
            "status":status,
        },sort_keys=True)+"\n"
    ).encode()


def test_ping():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        assert broker(root).handle(req("PING",{}))=={"pong":True}


def test_request_identity_must_match_parent_binding():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        b=broker(root)
        with pytest.raises(srv.ParentBrokerDenied,match="AGENT_IDENTITY_MISMATCH"):
            b.handle(req("PING",{},agent="OTHER"))
        with pytest.raises(srv.ParentBrokerDenied,match="TASK_IDENTITY_MISMATCH"):
            b.handle(req("PING",{},task="OTHER"))


def test_durable_admin_write_uses_existing_typed_commit():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        payload=state_payload()
        plan=admin.build_plan(
            operation="REPLACE",
            destination_class="ASTRA_STATE_JSON",
            path="canonical/astra_runtime/state/M1.json",
            payload=payload,
            expected_pre_sha256="ABSENT",
        )
        out=broker(root).handle(req("DURABLE_ADMIN_WRITE",{
            "plan":plan,
            "payload_b64":base64.b64encode(payload).decode(),
        }))
        assert out["status"]=="COMMITTED"
        assert (root/"canonical/astra_runtime/state/M1.json").read_bytes()==payload


def test_durable_admin_cannot_target_other_mission():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        payload=state_payload()
        plan=admin.build_plan(
            operation="REPLACE",
            destination_class="ASTRA_STATE_JSON",
            path="canonical/astra_runtime/state/OTHER.json",
            payload=payload,
            expected_pre_sha256="ABSENT",
        )
        with pytest.raises(srv.ParentBrokerDenied,match="STATE_PATH_NOT_CURRENT_MISSION"):
            broker(root).handle(req("DURABLE_ADMIN_WRITE",{
                "plan":plan,
                "payload_b64":base64.b64encode(payload).decode(),
            }))


def test_durable_admin_wrong_prestate_denied():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        target=root/"canonical/astra_runtime/state/M1.json"
        target.write_bytes(state_payload("OLD"))
        payload=state_payload()
        plan=admin.build_plan(
            operation="REPLACE",
            destination_class="ASTRA_STATE_JSON",
            path="canonical/astra_runtime/state/M1.json",
            payload=payload,
            expected_pre_sha256="ABSENT",
        )
        with pytest.raises(srv.ParentBrokerDenied,match="PRESTATE_MISMATCH"):
            broker(root).handle(req("DURABLE_ADMIN_WRITE",{
                "plan":plan,
                "payload_b64":base64.b64encode(payload).decode(),
            }))


def _allow_external(monkeypatch):
    monkeypatch.setattr(
        srv.continuous_obs,
        "authorize_information_action",
        lambda context,action,root:{
            "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_INFORMATION_ADMISSION_V1",
            "pass":True,
            "errors":[],
            "action":dict(action),
            "mode":"OPEN_DISCOVERY",
            "checked_at_utc":"2026-10-07T00:00:00+00:00",
        },
    )


def test_external_tool_relay_preserves_existing_request_contract(monkeypatch):
    _allow_external(monkeypatch)
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
        b=broker(
            root,
            external_bridge_dir=str(bridge),
            external_wait_seconds=0,
        )
        out=b.handle(req("EXTERNAL_TOOL",{
            "tool_kind":"http_get",
            "tool_payload":tool_payload,
        }))
        assert out["status"]==200
        observed=json.loads((bridge/(sha+".request.json")).read_text())
        assert observed["request_sha256"]==sha
        assert observed["agent_id"]=="A1"
        assert observed["task_id"]=="T1"
        admission=root/"canonical/astra_runtime/evidence/M1__ROOT3_PARENT_INFORMATION_ADMISSION.jsonl"
        assert admission.is_file()
        line=json.loads(admission.read_text().splitlines()[-1])
        assert line["pass"] is True
        assert line["broker_authority"]=="PARENT_INDEPENDENT_CONTINUOUS_OBS"


def test_forged_direct_external_request_is_reauthorized_and_denied(monkeypatch):
    monkeypatch.setattr(
        srv.continuous_obs,
        "authorize_information_action",
        lambda context,action,root:{
            "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_INFORMATION_ADMISSION_V1",
            "pass":False,
            "errors":["EXTERNAL_INFORMATION_FORBIDDEN"],
            "action":dict(action),
            "mode":"NO_EXTERNAL_INFORMATION",
            "checked_at_utc":"2026-10-07T00:00:00+00:00",
        },
    )
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        bridge=root/"canonical/same_identity_worker/external_tool_bridge/T1"
        b=broker(root,external_bridge_dir=str(bridge))
        with pytest.raises(srv.ParentBrokerDenied,match="PARENT_INFORMATION_AUTHORIZATION_DENIED"):
            b.handle(req("EXTERNAL_TOOL",{
                "tool_kind":"http_get",
                "tool_payload":{"url":"https://forbidden.invalid"},
            }))
        assert list(bridge.glob("*.request.json"))==[]
        admission=root/"canonical/astra_runtime/evidence/M1__ROOT3_PARENT_INFORMATION_ADMISSION.jsonl"
        verdict=json.loads(admission.read_text().splitlines()[-1])
        assert verdict["pass"] is False


def test_external_bridge_task_scope_escape_denied(monkeypatch):
    _allow_external(monkeypatch)
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        outside=root/"elsewhere"
        outside.mkdir()
        b=broker(root,external_bridge_dir=str(outside))
        with pytest.raises(srv.ParentBrokerDenied,match="BRIDGE_DIR_IDENTITY_MISMATCH"):
            b.handle(req("EXTERNAL_TOOL",{
                "tool_kind":"http_get","tool_payload":{}
            }))


def test_unknown_kind_denied():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        with pytest.raises(srv.ParentBrokerDenied,match="BROKER_KIND_DENIED"):
            broker(root).handle(req("ARBITRARY_HOST_EFFECT",{}))


def test_admin_payload_tamper_denied_by_existing_plan_hash():
    with tempfile.TemporaryDirectory() as td:
        root=mkrepo(pathlib.Path(td))
        good=b'{"schema":"PROJECT_BRAIN_TEST_EVIDENCE_V1","x":1}\n'
        bad=b'{"schema":"PROJECT_BRAIN_TEST_EVIDENCE_V1","x":2}\n'
        plan=admin.build_plan(
            operation="REPLACE",
            destination_class="ASTRA_EVIDENCE_JSON",
            path="canonical/astra_runtime/evidence/M1__TEST.json",
            payload=good,
            expected_pre_sha256="ABSENT",
        )
        with pytest.raises(srv.ParentBrokerDenied,match="PAYLOAD_HASH_MISMATCH"):
            broker(root).handle(req("DURABLE_ADMIN_WRITE",{
                "plan":plan,
                "payload_b64":base64.b64encode(bad).decode(),
            }))
