"""Root3 zero-ambient-authority carrier probe V1.

Fail-closed substrate probe for
ZERO_AMBIENT_AUTHORITY_PLUS_BROKER_IMPLIES_COMPLETE_MATERIAL_EFFECT_MEDIATION.

This emits zero acceptance/family/capability/ownership credit. It verifies one
specific Docker carrier shape and content-addresses the tested launcher, child,
and image so a later independent receipt can bind exact bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any

SCHEMA = "PROJECT_BRAIN_ROOT3_ZERO_AMBIENT_AUTHORITY_CARRIER_PROBE_V1"
DEFAULT_IMAGE = "busybox:1.36.1"
BROKER_PREFIX = "ROOT3_BROKER_REQUEST "
EXPECTED_REQUEST = {"type": "write_receipt", "payload": "ROOT3_BROKER_OK"}
EXPECTED_CHECKS = {
    "uid_unprivileged",
    "no_new_privileges",
    "capabilities_zero",
    "host_input_read_only",
    "container_root_read_only",
    "scratch_writable",
    "no_sensitive_environment",
    "no_undeclared_inherited_fd",
    "no_block_devices",
    "no_docker_socket",
    "no_default_route",
    "external_network_blocked",
    "host_process_control_blocked",
    "descendant_host_write_blocked",
    "descendant_external_network_blocked",
    "pids_hard_bounded",
    "memory_hard_bounded",
    "cpu_hard_bounded",
    "scratch_hard_bounded",
}

CHILD_SCRIPT = r"""#!/bin/sh
set +e
fail=0

pass_check() { echo "ROOT3_CHECK $1=PASS"; }
fail_check() { echo "ROOT3_CHECK $1=FAIL"; fail=1; }

if [ "$(id -u)" = "65534" ]; then pass_check uid_unprivileged; else fail_check uid_unprivileged; fi

nnp="$(awk '/^NoNewPrivs:/ {print $2}' /proc/self/status 2>/dev/null)"
if [ "$nnp" = "1" ]; then pass_check no_new_privileges; else fail_check no_new_privileges; fi

cap="$(awk '/^CapEff:/ {print $2}' /proc/self/status 2>/dev/null)"
if [ "$cap" = "0000000000000000" ]; then pass_check capabilities_zero; else fail_check capabilities_zero; fi

if (echo BAD >/input/host_sentinel 2>/scratch/write_input.err); then
  fail_check host_input_read_only
else
  pass_check host_input_read_only
fi

if (echo BAD >/etc/root3_escape_test 2>/scratch/write_root.err); then
  fail_check container_root_read_only
else
  pass_check container_root_read_only
fi

if (echo PRIVATE >/scratch/private_state 2>/scratch/write_scratch.err); then
  pass_check scratch_writable
else
  fail_check scratch_writable
fi

if env | grep -Eiq '(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|API[_-]?KEY|ACCESS[_-]?KEY|PRIVATE[_-]?KEY|GITHUB_|AWS_|AZURE_|GOOGLE_)'; then
  fail_check no_sensitive_environment
else
  pass_check no_sensitive_environment
fi

bad_fd=0
for fdpath in /proc/$$/fd/*; do
  fd="${fdpath##*/}"
  case "$fd" in
    0|1|2) ;;
    *)
      target="$(readlink "$fdpath" 2>/dev/null)"
      case "$target" in
        /input/*) ;;
        *) bad_fd=1 ;;
      esac
      ;;
  esac
done
if [ "$bad_fd" -eq 0 ]; then pass_check no_undeclared_inherited_fd; else fail_check no_undeclared_inherited_fd; fi

if find /dev -type b -print 2>/dev/null | grep -q .; then
  fail_check no_block_devices
else
  pass_check no_block_devices
fi

if [ -e /var/run/docker.sock ] || [ -e /run/docker.sock ]; then
  fail_check no_docker_socket
else
  pass_check no_docker_socket
fi

if awk 'NR>1 && $2=="00000000" {found=1} END {exit(found?0:1)}' /proc/net/route 2>/dev/null; then
  fail_check no_default_route
else
  pass_check no_default_route
fi

if wget -q -T 2 -O /scratch/net_probe http://1.1.1.1/ >/dev/null 2>&1; then
  fail_check external_network_blocked
else
  pass_check external_network_blocked
fi

if kill -0 "$ROOT3_HOST_PID" 2>/dev/null; then
  fail_check host_process_control_blocked
else
  pass_check host_process_control_blocked
fi

if /bin/sh -c 'echo BAD >/input/host_sentinel' >/dev/null 2>&1; then
  fail_check descendant_host_write_blocked
else
  pass_check descendant_host_write_blocked
fi

if /bin/sh -c 'wget -q -T 2 -O /scratch/nested_net http://1.1.1.1/' >/dev/null 2>&1; then
  fail_check descendant_external_network_blocked
else
  pass_check descendant_external_network_blocked
fi

pids_max="$(cat /sys/fs/cgroup/pids.max 2>/dev/null)"
case "$pids_max" in
  ''|max) fail_check pids_hard_bounded ;;
  *) if [ "$pids_max" -le 32 ] 2>/dev/null; then pass_check pids_hard_bounded; else fail_check pids_hard_bounded; fi ;;
esac

mem_max="$(cat /sys/fs/cgroup/memory.max 2>/dev/null)"
case "$mem_max" in
  ''|max) fail_check memory_hard_bounded ;;
  *) if [ "$mem_max" -le 134217728 ] 2>/dev/null; then pass_check memory_hard_bounded; else fail_check memory_hard_bounded; fi ;;
esac

cpu_max="$(cat /sys/fs/cgroup/cpu.max 2>/dev/null)"
cpu_quota="$(echo "$cpu_max" | awk '{print $1}')"
case "$cpu_quota" in
  ''|max) fail_check cpu_hard_bounded ;;
  *) pass_check cpu_hard_bounded ;;
esac

scratch_kb="$(df -Pk /scratch 2>/dev/null | awk 'NR==2 {print $2}')"
case "$scratch_kb" in
  '') fail_check scratch_hard_bounded ;;
  *) if [ "$scratch_kb" -le 17408 ] 2>/dev/null; then pass_check scratch_hard_bounded; else fail_check scratch_hard_bounded; fi ;;
esac

echo 'ROOT3_BROKER_REQUEST {"type":"write_receipt","payload":"ROOT3_BROKER_OK"}'
exit "$fail"
"""


class ProbeError(RuntimeError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def _parse_checks(stdout: str) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for line in stdout.splitlines():
        if not line.startswith("ROOT3_CHECK "):
            continue
        payload = line[len("ROOT3_CHECK "):]
        if "=" not in payload:
            raise ProbeError("MALFORMED_CHECK_LINE")
        name, status = payload.split("=", 1)
        if name in checks:
            raise ProbeError("DUPLICATE_CHECK:" + name)
        if status not in {"PASS", "FAIL"}:
            raise ProbeError("INVALID_CHECK_STATUS:" + name)
        checks[name] = status == "PASS"
    missing = sorted(EXPECTED_CHECKS - set(checks))
    extra = sorted(set(checks) - EXPECTED_CHECKS)
    if missing:
        raise ProbeError("MISSING_CHECKS:" + ",".join(missing))
    if extra:
        raise ProbeError("UNKNOWN_CHECKS:" + ",".join(extra))
    return checks


def _parse_broker_request(stdout: str) -> dict[str, str]:
    lines = [x for x in stdout.splitlines() if x.startswith(BROKER_PREFIX)]
    if len(lines) != 1:
        raise ProbeError(f"BROKER_REQUEST_COUNT:{len(lines)}")
    raw = lines[0][len(BROKER_PREFIX):]
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProbeError("BROKER_REQUEST_INVALID_JSON") from exc
    if request != EXPECTED_REQUEST:
        raise ProbeError("BROKER_REQUEST_NOT_EXACTLY_ALLOWED")
    return request


def _broker_commit(stdout: str, target: pathlib.Path) -> dict[str, Any]:
    request = _parse_broker_request(stdout)
    if target.exists():
        raise ProbeError("BROKER_TARGET_PREEXISTS")
    body = {
        "schema": "PROJECT_BRAIN_ROOT3_TYPED_EFFECT_BROKER_COMMIT_V1",
        "status": "ALLOW",
        "request": request,
        "guard": {
            "exact_type": EXPECTED_REQUEST["type"],
            "exact_payload": EXPECTED_REQUEST["payload"],
            "unknown_or_error_commits_nothing": True,
        },
    }
    encoded = (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
    tmp = target.with_suffix(".tmp")
    tmp.write_bytes(encoded)
    os.replace(tmp, target)
    return {
        "path": str(target),
        "sha256": _sha256_bytes(encoded),
        "size_bytes": len(encoded),
    }


def _assert_broker_fail_closed(tmp: pathlib.Path) -> None:
    target = tmp / "negative_broker_commit.json"
    bad = [
        "",
        BROKER_PREFIX + "{}",
        BROKER_PREFIX + '{"type":"write_receipt","payload":"BAD"}',
        BROKER_PREFIX + '{"type":"unknown","payload":"ROOT3_BROKER_OK"}',
        BROKER_PREFIX + json.dumps(EXPECTED_REQUEST) + "\n" + BROKER_PREFIX + json.dumps(EXPECTED_REQUEST),
    ]
    for case in bad:
        try:
            _broker_commit(case, target)
        except ProbeError:
            pass
        else:
            raise ProbeError("BROKER_FAIL_CLOSED_NEGATIVE_CANARY_ACCEPTED")
        if target.exists():
            raise ProbeError("BROKER_FAIL_CLOSED_NEGATIVE_CANARY_COMMITTED")


def probe(image: str, output: pathlib.Path) -> dict[str, Any]:
    errors: list[str] = []
    docker = shutil.which("docker")
    if not docker:
        raise ProbeError("DOCKER_NOT_FOUND")

    version = _run([docker, "version", "--format", "{{json .}}"], timeout=30)
    if version.returncode != 0:
        raise ProbeError("DOCKER_UNAVAILABLE:" + version.stderr.strip()[:500])

    pull = _run([docker, "pull", image], timeout=180)
    if pull.returncode != 0:
        raise ProbeError("IMAGE_PULL_FAILED:" + pull.stderr.strip()[:500])

    inspect = _run([docker, "image", "inspect", image, "--format", "{{json .}}"], timeout=30)
    if inspect.returncode != 0:
        raise ProbeError("IMAGE_INSPECT_FAILED:" + inspect.stderr.strip()[:500])
    try:
        image_info = json.loads(inspect.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError("IMAGE_INSPECT_JSON_INVALID") from exc

    with tempfile.TemporaryDirectory(prefix="root3-zero-ambient-") as td:
        tmp = pathlib.Path(td)
        input_dir = tmp / "input"
        input_dir.mkdir()
        sentinel = input_dir / "host_sentinel"
        sentinel.write_text("UNCHANGED\n", encoding="utf-8")
        child = input_dir / "child_probe.sh"
        child.write_text(CHILD_SCRIPT, encoding="utf-8")
        child.chmod(0o644)
        broker_target = tmp / "broker_commit.json"

        _assert_broker_fail_closed(tmp)

        launch_args = [
            "run",
            "--rm",
            "--network", "none",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--pids-limit", "32",
            "--memory", "128m",
            "--cpus", "1.0",
            "--ipc", "none",
            "--user", "65534:65534",
            "--tmpfs", "/scratch:rw,nosuid,nodev,noexec,size=16m,mode=1777",
            "--mount", f"type=bind,src={input_dir},dst=/input,readonly",
            "--env", "PATH=/bin:/usr/bin",
            "--env", f"ROOT3_HOST_PID={os.getpid()}",
            image,
            "/bin/sh", "/input/child_probe.sh",
        ]
        launch_policy_json = json.dumps(launch_args[:-3], separators=(",", ":"), ensure_ascii=True)
        run = _run([docker, *launch_args], timeout=30)

        if sentinel.read_text(encoding="utf-8") != "UNCHANGED\n":
            errors.append("HOST_SENTINEL_MUTATED")

        try:
            checks = _parse_checks(run.stdout)
        except ProbeError as exc:
            checks = {}
            errors.append(str(exc))

        for name, passed in sorted(checks.items()):
            if not passed:
                errors.append("CHECK_FAILED:" + name)

        if run.returncode != 0:
            errors.append("CHILD_NONZERO_EXIT:" + str(run.returncode))

        broker_receipt: dict[str, Any] | None = None
        if not errors:
            try:
                broker_receipt = _broker_commit(run.stdout, broker_target)
            except ProbeError as exc:
                errors.append(str(exc))

        if broker_receipt is None and broker_target.exists():
            errors.append("BROKER_COMMITTED_WITHOUT_VALIDATED_ALLOW")

        this_file = pathlib.Path(__file__).resolve()
        receipt = {
            "schema": SCHEMA,
            "status": "PASS__ZERO_AMBIENT_AUTHORITY_CARRIER_CANDIDATE" if not errors else "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "carrier": {
                "kind": "DOCKER_LINUX_CONTAINER",
                "image_request": image,
                "image_id": image_info.get("Id"),
                "repo_digests": image_info.get("RepoDigests") or [],
                "docker_version_json": version.stdout.strip(),
            },
            "content_addressing": {
                "probe_sha256": _sha256_file(this_file),
                "child_probe_sha256": _sha256_bytes(CHILD_SCRIPT.encode()),
                "launch_policy_sha256": _sha256_bytes(launch_policy_json.encode()),
            },
            "launch_policy": {
                "network": "none",
                "rootfs_read_only": True,
                "cap_drop": "ALL",
                "no_new_privileges": True,
                "pids_limit": 32,
                "memory_limit_bytes": 134217728,
                "cpus": 1.0,
                "ipc": "none",
                "uid_gid": "65534:65534",
                "private_scratch": "tmpfs_16MiB_noexec_nosuid_nodev",
                "host_input_mount": "read_only",
                "host_write_mounts": 0,
                "docker_socket_mounted": False,
            },
            "checks": checks,
            "host_wallclock_timeout_seconds": 30,
            "host_sentinel_unchanged": sentinel.read_text(encoding="utf-8") == "UNCHANGED\n",
            "broker_fail_closed_negative_canaries": True,
            "broker_commit": broker_receipt,
            "theorem_premise_effect": {
                "zero_ambient_authority_cut_empirically_exercised": not errors,
                "single_typed_broker_positive_path_exercised": broker_receipt is not None,
                "descendant_authority_widening_negative_canaries_passed": bool(
                    checks.get("descendant_host_write_blocked")
                    and checks.get("descendant_external_network_blocked")
                ),
                "exact_bytes_bound": True,
                "independent_workflow_receipt_still_required": True,
            },
            "hard_nonclaims": [
                "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
                "NO_CLAIM_ALL_LINUX_DOCKER_HOSTS_SHARE_THIS_CONFIGURATION",
                "NO_GUARD_SEMANTIC_SOUNDNESS_CLAIM_BEYOND_THE_EXACT_TYPED_BROKER_CANARY",
                "NO_TERMINAL_SUCCESS_NONINFERIORITY_CLAIM",
                "NO_FRESH_REALITY_OR_PROMOTION_AUTHORITY_FROM_THIS_PROBE",
            ],
            "accounting": {
                "incremental_spend_usd": 0,
                "terminal_cases_consumed": 0,
                "acceptance_credit_delta": 0,
                "family_credit_delta": 0,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            },
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", default="root3_zero_ambient_authority_carrier_probe_v1_receipt.json")
    args = parser.parse_args()
    output = pathlib.Path(args.output).resolve()

    try:
        receipt = probe(args.image, output)
    except Exception as exc:
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "accounting": {
                "incremental_spend_usd": 0,
                "terminal_cases_consumed": 0,
                "acceptance_credit_delta": 0,
                "family_credit_delta": 0,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            },
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if str(receipt.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
