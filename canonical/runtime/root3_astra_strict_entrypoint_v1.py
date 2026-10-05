"""Strict Root3 entrypoint for ASTRA.

Installs the current fail-closed subprocess bootstrap before importing ASTRA.
Only the independently closed read-only subprocess class is executable; every
other declared subprocess effect class remains denied until separately verified.
"""
from __future__ import annotations

from canonical.runtime import root3_strict_current_bootstrap_v1 as bootstrap
from canonical.runtime import root3_read_only_process_authorizer_v1 as read_only_authority

SCHEMA = "PROJECT_BRAIN_ROOT3_ASTRA_STRICT_ENTRYPOINT_V1"


def _load_astra_main():
    from canonical.runtime import astra_runtime
    return astra_runtime.main


def run() -> int:
    authorizer = read_only_authority.make_authorizer()
    installed = bootstrap.install_current(
        authorizer,
        authority_id=read_only_authority.POLICY_ID,
    )
    if installed.get("status") != "INSTALLED_FAIL_CLOSED":
        raise RuntimeError("ROOT3_STRICT_BOOTSTRAP_INSTALL_FAILED")
    astra_main = _load_astra_main()
    return int(astra_main())


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
