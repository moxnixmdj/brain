#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

REPO_ROOT=pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0,str(REPO_ROOT))

from canonical.runtime import zero_ambient_namespace_brokered_launcher_v2 as launcher

SCHEMA="PROJECT_BRAIN_ROOT3_PRODUCTION_ASTRA_BROKERED_LAUNCHER_V2"

class ProductionBrokeredLauncherError(RuntimeError):
    pass

def mission_relative(raw:str)->str:
    value=str(raw or "").strip().replace("\\","/")
    if not value:
        raise ProductionBrokeredLauncherError("MISSION_REQUIRED")
    p=pathlib.Path(value)
    if not p.is_absolute():
        p=REPO_ROOT/p
    p=p.resolve(strict=True)
    root=REPO_ROOT.resolve(strict=True)
    if p==root or root not in p.parents:
        raise ProductionBrokeredLauncherError("MISSION_OUTSIDE_REPOSITORY")
    rel=p.relative_to(root).as_posix()
    if not rel.startswith("canonical/astra_runtime/missions/") or not rel.endswith(".json"):
        raise ProductionBrokeredLauncherError("MISSION_PATH_NOT_CANONICAL")
    return rel

def external_wait_seconds()->float:
    raw=str(os.environ.get("PROJECT_BRAIN_EXTERNAL_TOOL_WAIT_SECONDS") or "0").strip()
    try:
        value=float(raw)
    except ValueError as exc:
        raise ProductionBrokeredLauncherError("EXTERNAL_TOOL_WAIT_SECONDS_INVALID") from exc
    if value<0 or value>300:
        raise ProductionBrokeredLauncherError("EXTERNAL_TOOL_WAIT_SECONDS_INVALID")
    return value

def run(mission:str)->dict[str,Any]:
    rel=mission_relative(mission)
    policy=launcher.production_policy(REPO_ROOT,rel)
    bridge=os.environ.get("PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR")
    result=launcher.run_brokered(
        policy,
        repo_root=REPO_ROOT,
        external_bridge_dir=bridge,
        external_wait_seconds=external_wait_seconds(),
    )
    return {
        "schema":SCHEMA,
        "mission":rel,
        "namespace_result":result,
        "production_rebinding_authority":False,
        "terminal_credit_delta":0,
    }

def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("mission")
    ns=ap.parse_args(argv)
    result=run(ns.mission)
    print(json.dumps(result,sort_keys=True))
    inner=result["namespace_result"]
    if inner.get("status")!="CHILD_EXITED":
        return 1
    return int(inner.get("returncode") or 0)

if __name__=="__main__":
    raise SystemExit(main())
