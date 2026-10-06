from __future__ import annotations

import hashlib
import json
import pathlib
import socket
import threading
from types import SimpleNamespace

from canonical.runtime import root3_broker_rpc_v1 as rpc
from canonical.runtime import root3_confined_astra_entry_v1 as entry
from canonical.runtime import root3_parent_broker_server_v1 as server
from canonical.runtime import root3_typed_durable_admin_write_v1 as admin


class Blocker(RuntimeError):
    pass


def test_astra_admin_commit_crosses_fd_and_commits_only_parent_side(tmp_path):
    (tmp_path/"canonical/astra_runtime/state").mkdir(parents=True)
    (tmp_path/"canonical/astra_runtime/evidence").mkdir(parents=True)
    (tmp_path/"canonical/same_identity_worker/external_tool_bridge/T1").mkdir(parents=True)

    parent,child=socket.socketpair()
    broker=server.ParentBroker(
        repo_root=tmp_path,
        expected_agent_id="A1",
        expected_task_id="T1",
        mission_id="M1",
        information_context={"test":True},
    )
    state={}
    def serve():
        try:
            state["summary"]=rpc.serve_socket(parent,broker.handle)
        finally:
            parent.close()
    th=threading.Thread(target=serve)
    th.start()

    def expected_pre(p):
        p=pathlib.Path(p)
        return "ABSENT" if not p.exists() else hashlib.sha256(p.read_bytes()).hexdigest()

    astra=SimpleNamespace(
        ROOT=tmp_path,
        Blocker=Blocker,
        _authorize_external_information=lambda kind,payload:{"pass":True},
        _load_runtime_helper=lambda name:admin,
        _admin_expected_prestate=expected_pre,
        _typed_admin_commit=lambda *a,**k:(_ for _ in ()).throw(AssertionError("LOCAL_COMMIT_USED")),
        _external_tool_bridge=lambda *a,**k:(_ for _ in ()).throw(AssertionError("LOCAL_BRIDGE_USED")),
    )
    try:
        entry.install_effect_transport(
            astra,fd=child.fileno(),agent_id="A1",task_id="T1"
        )
        payload=(
            json.dumps({
                "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1",
                "mission_id":"M1",
                "status":"RUNNING",
            },sort_keys=True)+"\n"
        ).encode()
        target=tmp_path/"canonical/astra_runtime/state/M1.json"
        receipt=astra._typed_admin_commit(
            target,payload,"ASTRA_STATE_JSON","REPLACE"
        )
        assert receipt["status"]=="COMMITTED"
        assert target.read_bytes()==payload
        assert broker.summary()["kinds"]==["DURABLE_ADMIN_WRITE","PING"]
        assert broker.summary()["request_count"]==2
    finally:
        child.close()
    th.join(timeout=2)
    assert state["summary"]["request_count"]==2
