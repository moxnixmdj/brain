from __future__ import annotations

import base64
import json
import pathlib

import pytest

from canonical.runtime import root3_admin_persistence_driver_v1 as driver
from canonical.runtime import root3_typed_durable_admin_write_v1 as admin


def root(tmp_path:pathlib.Path):
    (tmp_path/"canonical/astra_runtime/state").mkdir(parents=True)
    (tmp_path/"canonical/astra_runtime/evidence").mkdir(parents=True)
    return tmp_path


def state_payload(mission="M1"):
    return (
        json.dumps({
            "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1",
            "mission_id":mission,
            "status":"RUNNING",
        },sort_keys=True)+"\n"
    ).encode()


def test_admin_driver_commits_existing_typed_plan(tmp_path):
    repo=root(tmp_path)
    payload=state_payload()
    plan=admin.build_plan(
        operation="REPLACE",
        destination_class="ASTRA_STATE_JSON",
        path="canonical/astra_runtime/state/M1.json",
        payload=payload,
        expected_pre_sha256="ABSENT",
    )
    out=driver.execute(
        repo_root=repo,
        mission_id="M1",
        plan=plan,
        payload_b64=base64.b64encode(payload).decode(),
    )
    assert out["status"]=="COMMITTED"
    assert out["mission_id"]=="M1"
    assert (repo/"canonical/astra_runtime/state/M1.json").read_bytes()==payload


def test_admin_driver_rejects_payload_tamper(tmp_path):
    repo=root(tmp_path)
    good=state_payload()
    bad=state_payload("M2")
    plan=admin.build_plan(
        operation="REPLACE",
        destination_class="ASTRA_STATE_JSON",
        path="canonical/astra_runtime/state/M1.json",
        payload=good,
        expected_pre_sha256="ABSENT",
    )
    with pytest.raises(driver.AdminPersistenceDenied):
        driver.execute(
            repo_root=repo,
            mission_id="M1",
            plan=plan,
            payload_b64=base64.b64encode(bad).decode(),
        )


def test_admin_driver_denies_other_mission_state(tmp_path):
    repo=root(tmp_path)
    payload=state_payload()
    plan=admin.build_plan(
        operation="REPLACE",
        destination_class="ASTRA_STATE_JSON",
        path="canonical/astra_runtime/state/OTHER.json",
        payload=payload,
        expected_pre_sha256="ABSENT",
    )
    with pytest.raises(driver.AdminPersistenceDenied,match="STATE_PATH_NOT_CURRENT_MISSION"):
        driver.execute(
            repo_root=repo,
            mission_id="M1",
            plan=plan,
            payload_b64=base64.b64encode(payload).decode(),
        )


def test_admin_driver_denies_other_mission_evidence(tmp_path):
    repo=root(tmp_path)
    payload=b'{"schema":"PROJECT_BRAIN_TEST_EVIDENCE_V1"}\n'
    plan=admin.build_plan(
        operation="REPLACE",
        destination_class="ASTRA_EVIDENCE_JSON",
        path="canonical/astra_runtime/evidence/OTHER__TEST.json",
        payload=payload,
        expected_pre_sha256="ABSENT",
    )
    with pytest.raises(driver.AdminPersistenceDenied,match="EVIDENCE_PATH_NOT_CURRENT_MISSION"):
        driver.execute(
            repo_root=repo,
            mission_id="M1",
            plan=plan,
            payload_b64=base64.b64encode(payload).decode(),
        )


def test_state_payload_mission_binding_is_checked(tmp_path):
    repo=root(tmp_path)
    payload=state_payload("M2")
    plan=admin.build_plan(
        operation="REPLACE",
        destination_class="ASTRA_STATE_JSON",
        path="canonical/astra_runtime/state/M1.json",
        payload=payload,
        expected_pre_sha256="ABSENT",
    )
    with pytest.raises(driver.AdminPersistenceDenied,match="STATE_PAYLOAD_MISSION_BINDING_INVALID"):
        driver.execute(
            repo_root=repo,
            mission_id="M1",
            plan=plan,
            payload_b64=base64.b64encode(payload).decode(),
        )
