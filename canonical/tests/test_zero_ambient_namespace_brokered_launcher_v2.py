from __future__ import annotations

import pathlib

import pytest

from canonical.runtime import zero_ambient_namespace_brokered_launcher_v2 as m


def repo(tmp_path:pathlib.Path):
    (tmp_path/"canonical/astra_runtime/missions").mkdir(parents=True)
    (tmp_path/"canonical/astra_runtime/tmp").mkdir(parents=True)
    (tmp_path/"canonical/runtime").mkdir(parents=True)
    mission=tmp_path/"canonical/astra_runtime/missions/M1.json"
    mission.write_text('{"mission_id":"M1"}\n',encoding="utf-8")
    return mission


def test_production_policy_uses_confined_entry_and_repo_root(tmp_path,monkeypatch):
    repo(tmp_path)
    monkeypatch.setattr(m,"_nonroot_identity",lambda:(1234,1234))
    p=m.production_policy(tmp_path,"canonical/astra_runtime/missions/M1.json")
    assert p["input_dir"]==str(tmp_path.resolve())
    assert p["argv"]==[
        "/usr/bin/python3","-I",
        "/input/canonical/runtime/root3_confined_astra_entry_v1.py",
        "/input/canonical/astra_runtime/missions/M1.json",
    ]
    assert p["host_uid"]==p["host_gid"]==1234


def test_setup_makes_repo_readonly_then_overlays_only_runtime_tmp():
    s=m._SETUP
    ro='mount -o remount,bind,ro "$ROOT/input"'
    tmp='mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/input/canonical/astra_runtime/tmp"'
    assert ro in s
    assert tmp in s
    assert s.index(ro)<s.index(tmp)
    assert 'astra_runtime/state"' not in s
    assert 'astra_runtime/evidence"' not in s
    assert 'astra_runtime/artifacts"' not in s


def test_production_policy_rejects_escape(tmp_path,monkeypatch):
    repo(tmp_path)
    outside=tmp_path.parent/"outside.json"
    outside.write_text("{}")
    monkeypatch.setattr(m,"_nonroot_identity",lambda:(1234,1234))
    with pytest.raises((m.BrokeredNamespaceError,FileNotFoundError)):
        m.production_policy(tmp_path,"../outside.json")


class FakeProc:
    pid=12345
    def wait(self,timeout=None):
        return 0


def test_mocked_launcher_advertises_only_two_material_effect_classes(tmp_path,monkeypatch):
    repo(tmp_path)
    monkeypatch.setattr(m,"_nonroot_identity",lambda:(1234,1234))
    p=m.production_policy(tmp_path,"canonical/astra_runtime/missions/M1.json")
    monkeypatch.setattr(
        m,"_required_primitives",
        lambda:{
            "unshare":"/usr/bin/unshare","mount":"/usr/bin/mount",
            "chroot":"/usr/sbin/chroot","setpriv":"/usr/bin/setpriv",
            "ip":"/usr/bin/ip","bash":"/usr/bin/bash","env":"/usr/bin/env",
        },
    )
    monkeypatch.setattr(m.os,"chown",lambda *a,**k:None)
    monkeypatch.setattr(m.subprocess,"Popen",lambda *a,**k:FakeProc())
    out=m.run_brokered(p,repo_root=tmp_path)
    assert out["status"]=="CHILD_EXITED"
    assert out["material_effect_classes"]==["EXTERNAL_TOOL","DURABLE_ADMIN_WRITE"]
    assert out["artifact_persistence_authority"] is False
    assert out["broker_summary"]["request_count"]==0
    assert out["terminal_credit_delta"]==0
