import hashlib
import json
import pathlib

import pytest

from canonical.runtime import external_tool_relay as relay


def _request(agent="SUPERWORKER-UNIFIED-1", task="SI-REAL-UBJSON-SNAPSHOT-001"):
    value = {
        "schema": relay.REQUEST_SCHEMA,
        "kind": "urlopen",
        "agent_id": agent,
        "task_id": task,
        "payload": {
            "url": "https://registry.npmjs.org/-/v1/search?text=ubj&size=40",
            "method": "GET",
            "headers": {"User-Agent": "ProjectBrain-test"},
            "timeout_s": 20,
            "data_b64": None,
        },
    }
    canonical = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    value["request_sha256"] = hashlib.sha256(canonical).hexdigest()
    return value


def test_services_hash_and_identity_bound_request(tmp_path):
    req = _request()
    p = tmp_path / (req["request_sha256"] + ".request.json")
    p.write_text(json.dumps(req), encoding="utf-8")

    def fake_fetch(payload, allowed_hosts, max_body_bytes):
        assert payload["url"].startswith("https://registry.npmjs.org/")
        assert allowed_hosts == {"registry.npmjs.org"}
        assert max_body_bytes == 1234
        return {
            "status": 200,
            "final_url": payload["url"],
            "headers": {"content-type": "application/json"},
            "body_b64": "e30=",
        }

    out = relay.service_request(
        p,
        allowed_hosts={"registry.npmjs.org"},
        agent_id="SUPERWORKER-UNIFIED-1",
        task_id="SI-REAL-UBJSON-SNAPSHOT-001",
        max_body_bytes=1234,
        fetcher=fake_fetch,
    )
    assert out["status"] == "RESPONDED"
    response = json.loads(
        (tmp_path / (req["request_sha256"] + ".response.json")).read_text()
    )
    assert response["request_sha256"] == req["request_sha256"]
    assert response["agent_id"] == req["agent_id"]
    assert response["task_id"] == req["task_id"]
    assert response["status"] == "ok"


def test_rejects_hash_tamper(tmp_path):
    req = _request()
    req["payload"]["url"] = "https://registry.npmjs.org/tampered"
    p = tmp_path / (req["request_sha256"] + ".request.json")
    p.write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(relay.RelayError, match="REQUEST_HASH_MISMATCH"):
        relay.service_request(
            p,
            allowed_hosts={"registry.npmjs.org"},
            agent_id=req["agent_id"],
            task_id=req["task_id"],
            max_body_bytes=1234,
            fetcher=lambda *args: {},
        )


def test_rejects_identity_mismatch(tmp_path):
    req = _request()
    p = tmp_path / (req["request_sha256"] + ".request.json")
    p.write_text(json.dumps(req), encoding="utf-8")
    with pytest.raises(relay.RelayError, match="REQUEST_IDENTITY_MISMATCH"):
        relay.service_request(
            p,
            allowed_hosts={"registry.npmjs.org"},
            agent_id="OTHER",
            task_id=req["task_id"],
            max_body_bytes=1234,
            fetcher=lambda *args: {},
        )
