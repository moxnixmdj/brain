#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import root3_parent_driver_registry_v1 as registry
from canonical.runtime import zero_ambient_namespace_brokered_launcher_v2 as brokered

SCHEMA = "PROJECT_BRAIN_ROOT3_PRODUCTION_ASTRA_BROKERED_LAUNCHER_V2"


class ProductionBrokeredLauncherError(RuntimeError):
    pass


def canonical_mission_relative(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    if not value:
        raise ProductionBrokeredLauncherError("MISSION_PATH_REQUIRED")
    if value.startswith("/"):
        candidate = Path(value).resolve()
    else:
        candidate = (REPO_ROOT / value).resolve()
    root = REPO_ROOT.resolve()
    try:
        rel = candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ProductionBrokeredLauncherError("MISSION_PATH_OUTSIDE_REPO") from exc
    if (
        not rel.startswith("canonical/astra_runtime/missions/")
        or not rel.endswith(".json")
        or not candidate.is_file()
    ):
        raise ProductionBrokeredLauncherError("CANONICAL_MISSION_FILE_REQUIRED")
    return rel



def mission_authority_context(mission_rel: str) -> dict[str, str]:
    rel = canonical_mission_relative(mission_rel)
    path = (REPO_ROOT / rel).resolve()
    raw = path.read_bytes()
    try:
        mission = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ProductionBrokeredLauncherError("MISSION_JSON_INVALID") from exc
    if not isinstance(mission, dict):
        raise ProductionBrokeredLauncherError("MISSION_OBJECT_REQUIRED")
    mission_id = mission.get("mission_id")
    if not isinstance(mission_id, str) or not mission_id:
        raise ProductionBrokeredLauncherError("MISSION_ID_REQUIRED")
    return {
        "mission_id": mission_id,
        "mission_sha256": hashlib.sha256(raw).hexdigest(),
        "mission_rel": rel,
    }

def build_child_policy(mission_rel: str) -> dict[str, Any]:
    return {
        "argv": [
            "/usr/bin/python3",
            "/input/canonical/runtime/root3_production_astra_launcher_v1.py",
            "/input/" + mission_rel,
        ],
        "input_dir": str(REPO_ROOT),
        "limits": {
            "pids": 64,
            "memory_mb": 2048,
            "cpu_seconds": 300,
            "wallclock_s": 600,
            "scratch_mb": 512,
            "max_file_mb": 128,
            "nofile": 128,
            "broker_max_bytes": 8_000_000,
        },
    }


def run_mission(mission: str) -> dict[str, Any]:
    rel = canonical_mission_relative(mission)
    authority_context = mission_authority_context(rel)
    policy = build_child_policy(rel)
    result = brokered.run_confined_brokered(
        policy,
        lambda request: registry.dispatch(
            REPO_ROOT,
            request,
            authority_context=authority_context,
        ),
        max_requests=4096,
    )
    return {
        "schema": SCHEMA,
        "mission": rel,
        "mission_id": authority_context["mission_id"],
        "mission_sha256": authority_context["mission_sha256"],
        "namespace": result,
        "production_entry": "BROKERED_NAMESPACE_V2_TO_SUBPROCESS_GUARDED_V1",
        "closed_parent_registry": True,
        "mission_scoped_parent_authority": True,
        "generic_parent_effect_fallback": False,
        "terminal_credit_delta": 0,
    }


def result_exit_code(result: dict[str, Any]) -> int:
    ns = result.get("namespace") or {}
    if ns.get("status") != "CHILD_EXITED":
        return 70
    if ns.get("broker_error") is not None:
        return 71
    rc = ns.get("returncode")
    if not isinstance(rc, int):
        return 72
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mission")
    ns = ap.parse_args(argv)
    return result_exit_code(run_mission(ns.mission))


if __name__ == "__main__":
    raise SystemExit(main())
