from __future__ import annotations

import os
import socket
import threading

import pytest

from canonical.runtime import root3_broker_rpc_v1 as rpc


def pair():
    return socket.socketpair()


def test_roundtrip_binds_request_and_response():
    parent,child=pair()
    seen={}
    def server():
        seen.update(rpc.serve_socket(parent,lambda req:{"echo":req["payload"],"kind":req["kind"]}))
        parent.close()
    th=threading.Thread(target=server)
    th.start()
    try:
        out=rpc.call_fd(
            child.fileno(),
            kind="PING",
            agent_id="A1",
            task_id="T1",
            payload={"x":1},
        )
        assert out=={"echo":{"x":1},"kind":"PING"}
    finally:
        child.close()
    th.join(timeout=2)
    assert seen["request_count"]==1


def test_response_binding_mismatch_rejected():
    parent,child=pair()
    def server():
        req=rpc._recv(parent)
        checked=rpc.validate_request(req)
        bad=rpc.build_response(checked,status="ok",result={"ok":True})
        bad["task_id"]="OTHER"
        # Recompute hash so only binding fails.
        core={k:bad[k] for k in bad if k!="response_sha256"}
        bad["response_sha256"]=rpc._sha(core)
        rpc._send(parent,bad)
        parent.close()
    th=threading.Thread(target=server)
    th.start()
    with pytest.raises(rpc.BrokerProtocolError,match="RESPONSE_BINDING_MISMATCH:task_id"):
        rpc.call_fd(
            child.fileno(),kind="PING",agent_id="A1",task_id="T1",payload={}
        )
    child.close(); th.join(timeout=2)


def test_truncated_frame_rejected():
    parent,child=pair()
    try:
        child.sendall((20).to_bytes(4,"big")+b"{}")
        child.close()
        with pytest.raises(rpc.BrokerProtocolError,match="FRAME_TRUNCATED"):
            rpc._recv(parent)
    finally:
        parent.close()


def test_oversized_frame_rejected_before_body():
    parent,child=pair()
    try:
        child.sendall((rpc.MAX_FRAME+1).to_bytes(4,"big"))
        with pytest.raises(rpc.BrokerProtocolError,match="FRAME_SIZE_INVALID"):
            rpc._recv(parent)
    finally:
        child.close(); parent.close()


def test_request_tamper_rejected():
    req=rpc.build_request(kind="X",agent_id="A",task_id="T",payload={"v":1})
    req["payload"]["v"]=2
    with pytest.raises(rpc.BrokerProtocolError,match="REQUEST_HASH_MISMATCH"):
        rpc.validate_request(req)


def test_handler_error_returns_fail_closed_error():
    parent,child=pair()
    def server():
        rpc.serve_socket(parent,lambda req:(_ for _ in ()).throw(ValueError("nope")))
        parent.close()
    th=threading.Thread(target=server)
    th.start()
    with pytest.raises(rpc.BrokerProtocolError,match="BROKER_REQUEST_FAILED:ValueError:nope"):
        rpc.call_fd(
            child.fileno(),kind="X",agent_id="A",task_id="T",payload={}
        )
    child.close(); th.join(timeout=2)


def test_sequential_calls_share_same_fd_safely():
    parent,child=pair()
    def server():
        rpc.serve_socket(parent,lambda req:{"n":req["payload"]["n"]+1})
        parent.close()
    th=threading.Thread(target=server)
    th.start()
    try:
        for i in range(5):
            out=rpc.call_fd(
                child.fileno(),kind="INC",agent_id="A",task_id="T",payload={"n":i}
            )
            assert out["n"]==i+1
    finally:
        child.close()
    th.join(timeout=2)
