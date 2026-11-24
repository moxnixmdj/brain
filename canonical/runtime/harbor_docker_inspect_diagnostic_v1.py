"""Conservative, non-authorizing diagnostic for a Docker inspect document.

This is a static filter, NOT a Harbor boundary check. Its caller supplies the
JSON and expected identifiers; either may be forged. It does not bind Docker's
container to Harbor's exec target, verify the daemon, source contents, future
configuration, process quiescence, or perform a packet capture. Even an empty
failure list never authorizes a solver, artifact, or benchmark. Production
Harbor admission remains closed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_HARBOR_DOCKER_INSPECT_DIAGNOSTIC_V1"
_ID = re.compile(r"[0-9a-f]{64}\Z")
_MAX_BYTES = 2_000_000


def diagnose(inspect: Any, *, expected_id: str, expected_brain_source: str) -> dict[str, Any]:
    """Filter a narrow no-network/no-host-writes Docker configuration.

    This intentionally refuses additional mounts, devices and GPUs, even where
    some might be safe. Docker isolation still depends on the actual daemon,
    kernel, lifecycle, and Harbor identity, none of which are validated here.
    """
    failures: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            failures.append(code)

    if isinstance(inspect, list) and len(inspect) == 1:
        inspect = inspect[0]
    if not isinstance(inspect, dict):
        inspect = {}
        failures.append("INSPECT_NOT_SINGLE_OBJECT")
    host = inspect.get("HostConfig")
    state = inspect.get("State")
    network = inspect.get("NetworkSettings")
    mounts = inspect.get("Mounts")
    if not isinstance(host, dict):
        failures.append("HOST_CONFIG_MISSING")
        host = {}
    if not isinstance(state, dict):
        failures.append("STATE_MISSING")
        state = {}
    if not isinstance(network, dict):
        failures.append("NETWORK_SETTINGS_MISSING")
        network = {}
    if not isinstance(mounts, list):
        failures.append("MOUNTS_INVALID")
        mounts = []

    require(isinstance(expected_id, str) and bool(_ID.fullmatch(expected_id)), "EXPECTED_ID_INVALID")
    require(isinstance(inspect.get("Id"), str) and inspect.get("Id") == expected_id,
            "CONTAINER_ID_MISMATCH")
    require(state.get("Running") is True, "CONTAINER_NOT_RUNNING")
    pid = state.get("Pid")
    require(type(pid) is int and pid > 0, "CONTAINER_PID_INVALID")
    require(host.get("Privileged") is False, "PRIVILEGED_OR_UNKNOWN")
    require(host.get("NetworkMode") == "none", "NETWORK_MODE_NOT_NONE")
    for field in ("PidMode", "IpcMode", "UTSMode", "UsernsMode", "CgroupnsMode"):
        require(field in host and host[field] in ("", "private"), field.upper() + "_NOT_PRIVATE")

    dropped = host.get("CapDrop")
    added = host.get("CapAdd")
    require(isinstance(dropped, list) and any(isinstance(x, str) and x.upper() == "ALL" for x in dropped),
            "ALL_CAPABILITIES_NOT_DROPPED")
    require("CapAdd" in host and (added is None or added == []), "ADDED_CAPABILITIES_PRESENT_OR_UNKNOWN")
    security = host.get("SecurityOpt")
    require(isinstance(security, list) and "no-new-privileges:true" in security,
            "NO_NEW_PRIVILEGES_NOT_DECLARED")
    require(isinstance(security, list) and all(x == "no-new-privileges:true" for x in security),
            "UNREVIEWED_SECURITY_OPTION")
    for field in ("Devices", "DeviceRequests", "DeviceCgroupRules"):
        require(field in host and host[field] in (None, []), field.upper() + "_PRESENT_OR_UNKNOWN")
    require(host.get("PublishAllPorts") is False, "PUBLISH_ALL_PORTS_PRESENT_OR_UNKNOWN")
    require("PortBindings" in host and host["PortBindings"] in (None, {}), "PORT_BINDINGS_PRESENT_OR_UNKNOWN")

    nets = network.get("Networks")
    nets_ok = isinstance(nets, dict) and set(nets).issubset({"none"})
    if nets_ok:
        for entry in nets.values():
            if not isinstance(entry, dict) or any(entry.get(k) not in (None, "", 0)
                    for k in ("IPAddress", "GlobalIPv6Address", "Gateway", "IPv6Gateway", "IPPrefixLen", "GlobalIPv6PrefixLen")):
                nets_ok = False
    require(nets_ok, "NETWORK_ATTACHMENT_PRESENT_OR_UNKNOWN")

    source_ok = (isinstance(expected_brain_source, str) and expected_brain_source.startswith("/")
                 and "\x00" not in expected_brain_source
                 and os.path.normpath(expected_brain_source) == expected_brain_source
                 and expected_brain_source != "/")
    require(source_ok, "EXPECTED_BRAIN_SOURCE_INVALID")
    mount_ok = (len(mounts) == 1 and isinstance(mounts[0], dict)
                and mounts[0].get("Type") == "bind" and mounts[0].get("RW") is False
                and mounts[0].get("Source") == expected_brain_source
                and mounts[0].get("Destination") == "/opt/brain-ro")
    require(mount_ok, "BRAIN_READ_ONLY_MOUNT_OR_EXTRA_MOUNTS")

    return {
        "schema": SCHEMA,
        "status": "STATIC_CHECKS_PASSED__NOT_AUTHORIZED" if not failures else "REFUSED__STATIC_CHECKS_FAILED",
        "static_filter_passed": not failures,
        "failures": failures,
        "authority": "NONE__UNTRUSTED_POINT_IN_TIME_DOCUMENT",
        "execution_authorized": False,
        "container_boundary_verified": False,
        "egress_verified": False,
        "read_only_staging_verified": False,
        "harbor_exec_target_bound": False,
        "patch_emitted": False,
        "external_verifier_invoked": False,
        "limitations": [
            "inspect JSON and expected identifiers are caller supplied and unauthenticated",
            "no binding to Harbor exec or verification that configuration remains unchanged",
            "no source tree sealing, packet capture, process quiescence, or patch verification",
            "only one read-only bind and no devices are accepted; GPU tasks are excluded",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container-id", required=True, help="full 64-character Docker container ID")
    parser.add_argument("--brain-source", required=True, help="absolute expected bind source on Docker host")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            raise ValueError("INSPECT_TOO_LARGE")
        doc = json.loads(raw)
    except (OSError, ValueError, UnicodeError):
        doc = None
    print(json.dumps(diagnose(doc, expected_id=args.container_id,
                              expected_brain_source=args.brain_source), indent=2, sort_keys=True))
    # It is deliberately not a shell admission check, including for a perfect
    # static match: no caller may equate exit status 0 with execution authority.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
