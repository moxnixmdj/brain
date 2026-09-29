#!/bin/sh
set -eu

cd /brain

echo PB_HELDOUT003_CARRIER_PREFLIGHT_START=1
echo PB_HELDOUT003_BASE_MAIN=5fa5571d05c5ed86682921b9226de5b2ebcf73c3

command -v apt-cache >/dev/null
command -v apt-file >/dev/null
command -v sudo >/dev/null
command -v zbarimg >/dev/null
python3 -c 'import xapian'

ARCH="$(dpkg --print-architecture)"
TR="$(apt-get indextargets --format '$(FILENAME)' 'Identifier: Translations' 'Language: en' | sed '/^$/d' | wc -l | tr -d ' ')"
CA="$(find /var/lib/apt/lists -maxdepth 1 -type f -name "*Contents-${ARCH}*" | wc -l | tr -d ' ')"
ALL="$(find /var/lib/apt/lists -maxdepth 1 -type f -name '*Contents-all*' | wc -l | tr -d ' ')"
TAGS="$(apt-cache dumpavail | awk '/^Tag:/{n++} END{print n+0}')"
echo PB_HELDOUT003_TRANSLATION_EN_COUNT="$TR"
echo PB_HELDOUT003_CONTENTS_ARCH_COUNT="$CA"
echo PB_HELDOUT003_CONTENTS_ALL_COUNT="$ALL"
echo PB_HELDOUT003_TAG_RECORDS="$TAGS"
[ "$TR" -gt 0 ]
[ "$CA" -gt 0 ]
[ "$ALL" -gt 0 ]
[ "$TAGS" -gt 0 ]

python3 - <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path("/brain")

expected = {
    "canonical/runtime/capability_discovery.py": "b9e7423ab24bf2da98869b02d782e791a779892a",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/apt_cli_probe.py": "3f3a8f6a0154e1ed3f87fc97b99840598297b119",
    "canonical/runtime/cli_contract_inference.py": "009c3c45040178844d84eaa15b0d47ca2e1f259f",
    "canonical/runtime/verify_pending_cli_binding.py": "8ec4da92080e885a15266389c0318688e6408d43",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
    "canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_003.json": "6ac72c26dacabf8c14e037a5a983e29d912c17e6",
    "canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py": "ccd27d4dd46366c6fb7560378f6f9182f48fd6ae",
}

def blob_sha(path: pathlib.Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

for rel, exp in expected.items():
    got = blob_sha(root / rel)
    print(f"PB_HELDOUT003_BLOB={rel}={got}={'PASS' if got == exp else 'FAIL'}", flush=True)
    if got != exp:
        raise SystemExit(71)

spec_path = root / "canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_003.json"
spec = json.loads(spec_path.read_text(encoding="utf-8"))
fresh = spec.get("freshness") or {}
if fresh.get("state") != "UNSPENT" or int(fresh.get("execution_count") or 0) != 0:
    print("PB_HELDOUT003_PREFLIGHT_FAIL=SPEC_NOT_FRESH", flush=True)
    raise SystemExit(72)

evid = root / "canonical/astra_runtime/evidence"
for name in (
    "XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json",
    "XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json",
):
    if (evid / name).exists():
        print(f"PB_HELDOUT003_PREFLIGHT_FAIL=PREEXISTING_{name}", flush=True)
        raise SystemExit(73)

if not pathlib.Path("/etc/debian_version").exists():
    print("PB_HELDOUT003_PREFLIGHT_FAIL=NOT_DEBIAN_FAMILY", flush=True)
    raise SystemExit(74)

print("PB_HELDOUT003_CARRIER_PREFLIGHT=PASS", flush=True)
PY

echo PB_HELDOUT003_EXECUTION_ARMED=1
exec python3 canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py
