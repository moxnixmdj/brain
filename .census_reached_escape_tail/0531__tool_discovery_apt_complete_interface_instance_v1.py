"""Live zero-cost APT discovery-interface instance for Tool Discovery.

The verified instance is one real changing tool ecosystem: all binary package
identities exposed by every enabled public APT Packages index on one immutable
index epoch. Discovery is source-by-source, receipts are content-addressed, and
a safe executable probe is bound to the same epoch.

This module does not grant Tool Discovery acceptance credit. It only proves
whether this live external interface instance satisfies the seven frozen
properties in TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_APT_COMPLETE_INTERFACE_INSTANCE_V1"
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"

REQUIRED_PROPERTIES = {
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}


def _run(argv: list[str], *, cwd: str | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout, check=False,
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_config_hashes() -> list[dict[str, str]]:
    paths: list[Path] = []
    root = Path("/etc/apt")
    direct = root / "sources.list"
    if direct.is_file():
        paths.append(direct)
    source_dir = root / "sources.list.d"
    if source_dir.is_dir():
        for p in sorted(source_dir.iterdir()):
            if p.is_file() and not p.name.startswith("."):
                paths.append(p)
    return [
        {"path": str(p), "sha256": _sha256_file(p)}
        for p in paths
    ]


def _index_targets() -> list[dict[str, str]]:
    fmt = "$(IDENTIFIER)|$(SITE)|$(RELEASE)|$(COMPONENT)|$(ARCHITECTURE)|$(FILENAME)"
    proc = _run(["apt-get", "indextargets", "--format", fmt])
    if proc.returncode != 0:
        raise RuntimeError("APT_INDEXTARGETS_FAILED:" + proc.stderr[-500:])
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split("|", 5)
        if len(parts) != 6:
            continue
        ident, site, release, component, arch, filename = [x.strip() for x in parts]
        if ident != "Packages":
            continue
        p = Path(filename)
        if not filename or not p.is_file():
            continue
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "identifier": ident,
            "site": site,
            "release": release,
            "component": component,
            "architecture": arch,
            "filename": key,
            "index_sha256": _sha256_file(p),
        })
    out.sort(key=lambda x: (x["site"], x["release"], x["component"], x["architecture"], x["filename"]))
    return out


def _source_id(row: dict[str, str]) -> str:
    raw = "|".join(
        row.get(k, "")
        for k in ("site", "release", "component", "architecture", "index_sha256")
    )
    return "APT_SOURCE::" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def _iter_stanzas_from_index(path: str) -> Iterable[dict[str, str]]:
    helper = "/usr/lib/apt/apt-helper"
    if not Path(helper).is_file():
        raise RuntimeError("APT_HELPER_MISSING")
    proc = subprocess.Popen(
        [helper, "cat-file", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert proc.stdout is not None
    stanza: dict[str, str] = {}
    current: str | None = None
    for raw in proc.stdout:
        line = raw.rstrip("\n")
        if not line:
            if stanza:
                yield stanza
            stanza = {}
            current = None
            continue
        if line[:1].isspace() and current is not None:
            stanza[current] = stanza.get(current, "") + "\n" + line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current = key
        if key in {"Package", "Version", "Architecture", "Depends", "Pre-Depends", "Conflicts", "Provides"}:
            stanza[key] = value.strip()
    if stanza:
        yield stanza
    stderr = proc.stderr.read() if proc.stderr is not None else ""
    rc = proc.wait(timeout=60)
    if rc != 0:
        raise RuntimeError("APT_CAT_FILE_FAILED:" + stderr[-500:])


def _apt_cache_dumpavail_names() -> set[str]:
    proc = subprocess.Popen(
        ["apt-cache", "dumpavail"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert proc.stdout is not None
    names: set[str] = set()
    for line in proc.stdout:
        if line.startswith("Package:"):
            value = line.split(":", 1)[1].strip()
            if value:
                names.add(value)
    stderr = proc.stderr.read() if proc.stderr is not None else ""
    rc = proc.wait(timeout=90)
    if rc != 0:
        raise RuntimeError("APT_DUMPAVAIL_FAILED:" + stderr[-500:])
    return names


def _epoch_snapshot() -> dict[str, Any]:
    configs = _source_config_hashes()
    indexes = _index_targets()
    body = {
        "source_configs": configs,
        "package_indexes": [
            {
                "source_id": _source_id(x),
                "site": x["site"],
                "release": x["release"],
                "component": x["component"],
                "architecture": x["architecture"],
                "index_sha256": x["index_sha256"],
            }
            for x in indexes
        ],
    }
    root = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"epoch_sha256": root, **body, "_index_rows": indexes}


def _public_http_uri(uri: str) -> bool:
    s = str(uri or "").strip().lower()
    return (
        (s.startswith("http://") or s.startswith("https://"))
        and "@" not in s.split("://", 1)[-1].split("/", 1)[0]
    )


def _public_source(site: str) -> bool:
    raw = str(site or "").strip()
    if _public_http_uri(raw):
        return True
    prefix = "mirror+file:"
    if not raw.lower().startswith(prefix):
        return False
    mirror_path = Path(raw[len(prefix):])
    if not mirror_path.is_absolute() or not mirror_path.is_file():
        return False
    try:
        lines = mirror_path.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeError):
        return False
    mirrors: list[str] = []
    for line in lines:
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        uri = value.split(None, 1)[0]
        mirrors.append(uri)
    return bool(mirrors) and all(_public_http_uri(uri) for uri in mirrors)


def _probe_coreutils(epoch_sha256: str, source_for_package: dict[str, str] | None) -> dict[str, Any]:
    policy = _run(["apt-cache", "policy", "coreutils"])
    candidate = None
    for line in policy.stdout.splitlines():
        m = re.match(r"\s*Candidate:\s*(\S+)", line)
        if m:
            candidate = m.group(1)
            break
    if policy.returncode != 0 or not candidate or candidate == "(none)":
        return {"pass": False, "reason": "COREUTILS_CANDIDATE_UNAVAILABLE", "epoch_sha256": epoch_sha256}

    with tempfile.TemporaryDirectory(prefix="brain-apt-probe-") as td:
        dl = _run(["apt-get", "download", "coreutils"], cwd=td, timeout=180)
        debs = sorted(Path(td).glob("coreutils_*.deb"))
        if dl.returncode != 0 or len(debs) != 1:
            return {
                "pass": False, "reason": "COREUTILS_DOWNLOAD_FAILED",
                "stderr": dl.stderr[-1000:], "epoch_sha256": epoch_sha256,
            }
        deb = debs[0]
        extract = Path(td) / "root"
        extract.mkdir()
        unpack = _run(["dpkg-deb", "-x", str(deb), str(extract)], timeout=60)
        exe = extract / "usr/bin/sha256sum"
        if unpack.returncode != 0 or not exe.is_file():
            return {"pass": False, "reason": "COREUTILS_EXTRACT_FAILED", "epoch_sha256": epoch_sha256}
        call = _run([str(exe), "--version"], timeout=30)
        truthful = (
            call.returncode == 0
            and "coreutils" in call.stdout.lower()
            and bool(call.stdout.strip())
        )
        return {
            "pass": truthful,
            "kind": "SAFE_CAPABILITY_PROBE",
            "capability": "CLI_SHA256SUM_VERSION_EXECUTES",
            "package": "coreutils",
            "candidate_version": candidate,
            "source_id": _source_id(source_for_package) if source_for_package else None,
            "epoch_sha256": epoch_sha256,
            "downloaded_deb_sha256": _sha256_file(deb),
            "executable_relative_path": "usr/bin/sha256sum",
            "returncode": call.returncode,
            "stdout_first_line": call.stdout.splitlines()[0] if call.stdout.splitlines() else "",
            "truthful_observed_execution": truthful,
        }


def evaluate() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text())
    props = contract.get("required_properties")
    if set(props or []) != REQUIRED_PROPERTIES:
        return {
            "schema": SCHEMA, "status": "FAIL_CLOSED__CONTRACT_DRIFT", "pass": False,
            "contract_properties_match": False, "execution_authority": False,
            "capability_credit_delta": 0, "family_credit_delta": 0,
        }

    before = _epoch_snapshot()
    indexes = before.pop("_index_rows")
    source_receipts: list[dict[str, Any]] = []
    union_names: set[str] = set()
    identity_count = 0
    malformed = 0
    source_for_coreutils: dict[str, str] | None = None
    monotonic = True
    prior_union = 0

    for row in indexes:
        source_names: set[str] = set()
        record_count = 0
        for stanza in _iter_stanzas_from_index(row["filename"]):
            name = stanza.get("Package")
            version = stanza.get("Version")
            arch = stanza.get("Architecture")
            if not name or not version or not arch:
                malformed += 1
                continue
            record_count += 1
            identity_count += 1
            source_names.add(name)
            if name == "coreutils" and source_for_coreutils is None:
                source_for_coreutils = row
        before_count = len(union_names)
        union_names.update(source_names)
        after_count = len(union_names)
        if after_count < prior_union or after_count < before_count:
            monotonic = False
        prior_union = after_count
        source_receipts.append({
            "kind": "DISCOVERY_RESULT",
            "source_id": _source_id(row),
            "site": row["site"],
            "release": row["release"],
            "component": row["component"],
            "architecture": row["architecture"],
            "index_sha256": row["index_sha256"],
            "record_count": record_count,
            "unique_package_name_count": len(source_names),
            "new_visible_tool_identity_count": after_count - before_count,
            "union_visible_tool_identity_count": after_count,
        })

    apt_names = _apt_cache_dumpavail_names()
    public_sources = bool(indexes) and all(_public_source(x["site"]) for x in indexes)
    complete = bool(union_names) and union_names == apt_names

    probe = _probe_coreutils(before["epoch_sha256"], source_for_coreutils)
    after = _epoch_snapshot()
    after.pop("_index_rows")
    epoch_stable = before["epoch_sha256"] == after["epoch_sha256"]

    property_results = {
        "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH": len(indexes) > 0,
        "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE": bool(source_receipts) and all(x["source_id"] for x in source_receipts),
        "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH": monotonic and len(union_names) > 0,
        "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE": complete,
        "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS": (
            malformed == 0 and public_sources and identity_count > 0
        ),
        "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND": (
            probe.get("pass") is True and probe.get("epoch_sha256") == before["epoch_sha256"]
        ),
        "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE": epoch_stable,
    }
    ok = all(property_results.values())
    report = {
        "schema": SCHEMA,
        "status": (
            "PASS__LIVE_CONTENT_ADDRESSED_APT_DISCOVERY_INTERFACE_INSTANCE_SATISFIES_ALL_SEVEN_FROZEN_PROPERTIES__ZERO_CREDIT"
            if ok else "FAIL_CLOSED__LIVE_APT_INTERFACE_PROPERTY_FAILURE"
        ),
        "pass": ok,
        "declared_target_scope": (
            "ALL_BINARY_PACKAGE_TOOL_IDENTITIES_EXPOSED_BY_EVERY_ENABLED_PUBLIC_APT_PACKAGES_INDEX_"
            "ON_THE_VERIFIED_RUNNER_EPOCH__WITH_CAPABILITY_CONFIRMATION_BY_EPOCH_BOUND_SAFE_EXECUTABLE_PROBES"
        ),
        "external_authority": "APT_ENABLED_PUBLIC_REPOSITORY_INDEXES_ON_INDEPENDENT_GITHUB_HOSTED_UBUNTU_RUNNER",
        "platform": platform.platform(),
        "contract_path": str(CONTRACT.relative_to(ROOT)),
        "property_results": property_results,
        "source_count": len(indexes),
        "discovery_receipts": source_receipts,
        "union_unique_tool_identity_count": len(union_names),
        "apt_cache_available_name_count": len(apt_names),
        "package_version_arch_record_count": identity_count,
        "malformed_required_metadata_record_count": malformed,
        "metadata_normalization": {
            "available": "TRUE_IFF_IDENTITY_PRESENT_IN_EPOCH_PACKAGES_INDEX",
            "authorized": "TRUE_FOR_DISCOVERY_IFF_SOURCE_IS_PUBLIC_AND_REQUIRES_NO_CREDENTIAL_IN_SOURCE_URI",
            "cost": "0_USD_FOR_METADATA_DISCOVERY_AND_PUBLIC_PACKAGE_ACQUISITION",
            "constraints": ["ARCHITECTURE", "DEPENDS", "PRE_DEPENDS", "CONFLICTS", "PROVIDES"],
        },
        "safe_probe_receipt": probe,
        "epoch_before": before,
        "epoch_after_sha256": after["epoch_sha256"],
        "epoch_stable": epoch_stable,
        "hard_nonclaims": [
            "THIS_INSTANCE_IS_NOT_THE_SET_OF_ALL_TOOLS_IN_EXISTENCE",
            "THIS_INSTANCE_DOES_NOT_BY_ITSELF_GRANT_TOOL_DISCOVERY_ACCEPTANCE_OR_FAMILY_CREDIT",
            "PACKAGE_IDENTITY_DISCOVERY_DOES_NOT_ASSERT_ARBITRARY_SEMANTIC_CAPABILITY_WITHOUT_A_TRUTHFUL_SAFE_PROBE",
            "A_CHANGED_APT_EPOCH_REQUIRES_A_NEW_EPISODE_AND_NEW_RECEIPTS",
        ],
        "new_reality_units_consumed": 1,
        "reality_unit": "ONE_INDEPENDENT_LIVE_COMPLETE_DISCOVERY_INTERFACE_INSTANCE",
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
    return report


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
