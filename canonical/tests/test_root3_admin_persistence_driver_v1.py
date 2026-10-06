from __future__ import annotations

import base64
import pathlib
import tempfile

import pytest

from canonical.runtime import root3_admin_persistence_driver_v1 as driver
from canonical.runtime import root3_typed_durable_admin_write_v1 as admin


def root(tmp_path:pathlib.Path):
    (tmp_path/"canonical/astra_runtime/state").mkdir(parents=True)
    (tmp_path/"canonical/astra_runtime/evidence").mkdir(parents=True)
    return tmp_path


def test_admin_driver_commits_existing_typed_plan(tmp_path):
    repo=root(tmp_path)
    payload=b'{"x":1}\n'
    plan=admin.build_plan(
        operation="REPLACE",
        destination_class="ASTRA_STATE_JSON",
        path="canonical/astra_runtime/state/T1.json",
        payload=payload,
        expected_pre_sha256="ABSENT",
    )
    out=driver.execute(
        repo_root=repo,
        plan=plan,
        payload_b64=base64.b64encode(payload).decode(),
    )
    assert out["status"]=="COMMITTED"
    assert out["receipt"]["status"]=="COMMITTED"
    assert (repo/"canonical/astra_runtime/state/T1.json").read_bytes()==payload


def test_admin_driver_rejects_payload_tamper(tmp_path):
    repo=root(tmp_path)
    good=b'{"x":1}\n'; bad=b'{"x":2}\n'
    plan=admin.build_plan(
        operation="REPLACE",
        destination_class="ASTRA_STATE_JSON",
        path="canonical/astra_runtime/state/T1.json",
        payload=good,
        expected_pre_sha256="ABSENT",
    )
    with pytest.raises(driver.AdminPersistenceDenied,match="PAYLOAD_HASH_MISMATCH"):
        driver.execute(
            repo_root=repo,
            plan=plan,
            payload_b64=base64.b64encode(bad).decode(),
        )


def test_admin_driver_has_no_arbitrary_path_authority(tmp_path):
    repo=root(tmp_path)
    payload=b'{"x":1}\n'
    bad_plan={
        "schema":admin.PLAN_SCHEMA,
        "operation":"REPLACE",
        "destination_class":"ASTRA_STATE_JSON",
        "path":"outside.json",
        "payload_sha256":"0"*64,
        "payload_bytes":len(payload),
        "expected_pre_sha256":"ABSENT",
        "plan_sha256":"0"*64,
    }
    with pytest.raises(driver.AdminPersistenceDenied,match="PATH_NOT_ALLOWED"):
        driver.execute(
            repo_root=repo,
            plan=bad_plan,
            payload_b64=base64.b64encode(payload).decode(),
        )
