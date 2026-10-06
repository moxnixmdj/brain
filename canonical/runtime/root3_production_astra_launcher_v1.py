#!/usr/bin/env python3
"""Production ASTRA launcher with Root3 subprocess mediation installed first.

This launcher is the credited production seam for the shared ASTRA runtime.
It installs the independently verified Root3 two-class attempt authority before
importing ASTRA, so subprocess.run/Popen are fail-closed process-wide before
any ASTRA mission step can execute. No authority is added for the other effect
classes.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import root3_strict_current_bootstrap_v2 as bootstrap
from canonical.runtime import root3_two_class_attempt_authorizer_v1 as attempt_authorizer

SCHEMA = "PROJECT_BRAIN_ROOT3_PRODUCTION_ASTRA_LAUNCHER_V1"
ASTRA_MODULE = "canonical.runtime.astra_runtime"


class ProductionBootstrapError(RuntimeError):
    pass


def install_root3_before_astra_import() -> dict[str, Any]:
    status = bootstrap.install_current(
        attempt_authorizer.authorize,
        authority_id=attempt_authorizer.AUTHORITY_ID,
    )
    if status.get("run_guard_active") is not True:
        raise ProductionBootstrapError("ROOT3_SUBPROCESS_RUN_GUARD_NOT_ACTIVE")
    if status.get("popen_guard_active") is not True:
        raise ProductionBootstrapError("ROOT3_SUBPROCESS_POPEN_GUARD_NOT_ACTIVE")
    return status


def load_astra_after_root3_install() -> Any:
    install_root3_before_astra_import()
    astra = importlib.import_module(ASTRA_MODULE)
    status = bootstrap.mediator.status()
    if status.get("run_guard_active") is not True:
        raise ProductionBootstrapError("ROOT3_RUN_GUARD_LOST_AFTER_ASTRA_IMPORT")
    if status.get("popen_guard_active") is not True:
        raise ProductionBootstrapError("ROOT3_POPEN_GUARD_LOST_AFTER_ASTRA_IMPORT")
    return astra


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mission")
    ns = ap.parse_args(argv)

    astra = load_astra_after_root3_install()
    old_argv = sys.argv
    try:
        sys.argv = [str(astra.__file__), ns.mission]
        result = astra.main()
    finally:
        sys.argv = old_argv
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
