from __future__ import annotations

from types import SimpleNamespace

import pytest

from canonical.runtime import root3_production_astra_brokered_launcher_v2 as m


def test_mission_relative_accepts_only_canonical_mission(monkeypatch,tmp_path):
    root=tmp_path
    mission=root/"canonical/astra_runtime/missions/M1.json"
    mission.parent.mkdir(parents=True)
    mission.write_text('{"mission_id":"M1"}')
    monkeypatch.setattr(m,"REPO_ROOT",root)
    assert m.mission_relative(str(mission))=="canonical/astra_runtime/missions/M1.json"
    assert m.mission_relative("canonical/astra_runtime/missions/M1.json")=="canonical/astra_runtime/missions/M1.json"


def test_mission_relative_rejects_nonmission_json(monkeypatch,tmp_path):
    root=tmp_path
    p=root/"canonical/x.json"
    p.parent.mkdir(parents=True)
    p.write_text("{}")
    monkeypatch.setattr(m,"REPO_ROOT",root)
    with pytest.raises(m.ProductionBrokeredLauncherError,match="MISSION_PATH_NOT_CANONICAL"):
        m.mission_relative(str(p))


def test_run_uses_brokered_namespace_and_does_not_claim_production_rebinding(monkeypatch,tmp_path):
    root=tmp_path
    mission=root/"canonical/astra_runtime/missions/M1.json"
    mission.parent.mkdir(parents=True)
    mission.write_text('{"mission_id":"M1"}')
    monkeypatch.setattr(m,"REPO_ROOT",root)
    seen={}
    monkeypatch.setattr(
        m.launcher,"production_policy",
        lambda repo,rel: seen.setdefault("policy",(repo,rel)) or {"x":1},
    )
    # Above setdefault returns tuple, so use a dedicated replacement.
    def build(repo,rel):
        seen["policy"]=(repo,rel)
        return {"policy":"P"}
    monkeypatch.setattr(m.launcher,"production_policy",build)
    def execute(policy,**kw):
        seen["execute"]=(policy,kw)
        return {"status":"CHILD_EXITED","returncode":0}
    monkeypatch.setattr(m.launcher,"run_brokered",execute)
    monkeypatch.delenv("PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR",raising=False)
    out=m.run(str(mission))
    assert seen["policy"]==(root,"canonical/astra_runtime/missions/M1.json")
    assert seen["execute"][0]=={"policy":"P"}
    assert seen["execute"][1]["repo_root"]==root
    assert out["namespace_result"]["status"]=="CHILD_EXITED"
    assert out["production_rebinding_authority"] is False
    assert out["terminal_credit_delta"]==0


def test_main_fails_if_namespace_did_not_exit_cleanly(monkeypatch,capsys):
    monkeypatch.setattr(
        m,"run",
        lambda mission:{
            "schema":m.SCHEMA,
            "mission":"canonical/astra_runtime/missions/M1.json",
            "namespace_result":{"status":"BROKER_PROTOCOL_ERROR","returncode":1},
            "production_rebinding_authority":False,
            "terminal_credit_delta":0,
        },
    )
    assert m.main(["canonical/astra_runtime/missions/M1.json"])==1
    assert "BROKER_PROTOCOL_ERROR" in capsys.readouterr().out


def test_external_wait_is_bounded(monkeypatch):
    monkeypatch.setenv("PROJECT_BRAIN_EXTERNAL_TOOL_WAIT_SECONDS","301")
    with pytest.raises(m.ProductionBrokeredLauncherError,match="WAIT_SECONDS_INVALID"):
        m.external_wait_seconds()
