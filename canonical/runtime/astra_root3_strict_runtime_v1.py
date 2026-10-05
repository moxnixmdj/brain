"""Production ASTRA launcher that installs Root3 before ASTRA import."""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from canonical.runtime import root3_strict_current_bootstrap_v3 as bootstrap
from canonical.runtime import root3_two_class_attempt_authorizer_v2 as authorizer

SCHEMA = "PROJECT_BRAIN_ASTRA_ROOT3_STRICT_RUNTIME_V1"
REPO_ROOT = Path(__file__).resolve().parents[2]
MISSION_ROOT = (REPO_ROOT / "canonical/astra_runtime/missions").resolve()


class ProductionBootstrapError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mission")
    ns = ap.parse_args(argv)

    raw_mission = Path(ns.mission)
    mission_abs = (
        raw_mission.resolve()
        if raw_mission.is_absolute()
        else (REPO_ROOT / raw_mission).resolve()
    )
    try:
        mission_abs.relative_to(MISSION_ROOT)
    except ValueError as exc:
        raise ProductionBootstrapError(
            "MISSION_PATH_OUTSIDE_CANONICAL_RUNTIME"
        ) from exc
    if mission_abs.suffix != ".json":
        raise ProductionBootstrapError("MISSION_MUST_BE_JSON")
    mission = mission_abs.relative_to(REPO_ROOT)

    status = bootstrap.install_current(
        authorizer.authorize,
        authority_id=authorizer.AUTHORITY_ID,
    )
    if (
        status.get("run_guard_active") is not True
        or status.get("popen_guard_active") is not True
    ):
        raise ProductionBootstrapError("ROOT3_GUARD_NOT_ACTIVE_BEFORE_ASTRA_IMPORT")

    # This import is intentionally after Root3 installation. Moving it above
    # install_current is a production-security regression and is tested.
    astra = importlib.import_module("canonical.runtime.astra_runtime")

    old_argv = sys.argv
    try:
        sys.argv = [str(Path(astra.__file__).resolve()), str(mission)]
        result = astra.main()
    finally:
        sys.argv = old_argv
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
