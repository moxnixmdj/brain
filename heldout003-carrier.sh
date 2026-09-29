#!/bin/sh
set -eu

cd /work
echo "PB003_CARRIER_BOOT=1"

for cmd in python3 apt-cache apt-file sudo zbarimg; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "PB003_PREFLIGHT_FAIL=missing:$cmd"; exit 91; }
done

python3 - <<'PY'
from __future__ import annotations
import hashlib
import json
from pathlib import Path

root = Path("/work")
expected = {
    "canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_003.json": "6ac72c26dacabf8c14e037a5a983e29d912c17e6",
    "canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py": "ccd27d4dd46366c6fb7560378f6f9182f48fd6ae",
    "canonical/runtime/capability_discovery.py": "b9e7423ab24bf2da98869b02d782e791a779892a",
    "canonical/runtime/auto_capability_acquisition.py": "fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
    "canonical/runtime/apt_cli_probe.py": "3f3a8f6a0154e1ed3f87fc97b99840598297b119",
    "canonical/runtime/cli_contract_inference.py": "009c3c45040178844d84eaa15b0d47ca2e1f259f",
    "canonical/runtime/verify_pending_cli_binding.py": "8ec4da92080e885a15266389c0318688e6408d43",
    "canonical/runtime/auto_apt_cli_acquisition.py": "0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
}

def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

for rel, want in expected.items():
    got = blob_sha(root / rel)
    if got != want:
        raise SystemExit(f"PB003_PREFLIGHT_FAIL=blob:{rel}:{got}:{want}")

spec_path = root / "canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_003.json"
spec = json.loads(spec_path.read_text(encoding="utf-8"))
fresh = spec.get("freshness") or {}
if fresh.get("state") != "UNSPENT" or int(fresh.get("execution_count") or 0) != 0:
    raise SystemExit("PB003_PREFLIGHT_FAIL=heldout_not_fresh")

evid = root / "canonical/astra_runtime/evidence"
for name in [
    "XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json",
    "XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json",
]:
    if (evid / name).exists():
        raise SystemExit(f"PB003_PREFLIGHT_FAIL=preexisting:{name}")

try:
    import xapian  # noqa: F401
except Exception as exc:
    raise SystemExit(f"PB003_PREFLIGHT_FAIL=xapian:{type(exc).__name__}:{exc}")

lists = Path("/var/lib/apt/lists")
translations = [p for p in lists.glob("*Translation-en*") if p.is_file()]
contents = [p for p in lists.glob("*Contents*") if p.is_file()]
aptfile = Path("/var/cache/apt/apt-file")
if aptfile.exists():
    contents.extend(p for p in aptfile.rglob("*Contents*") if p.is_file())

names = [p.name for p in contents]
if not translations:
    raise SystemExit("PB003_PREFLIGHT_FAIL=translation_en_missing")
if not any("Contents-all" in n for n in names):
    raise SystemExit("PB003_PREFLIGHT_FAIL=contents_all_missing")
if not any(("Contents-amd64" in n or "Contents-" in n and "all" not in n) for n in names):
    raise SystemExit("PB003_PREFLIGHT_FAIL=contents_arch_missing")

print("PB003_BLOB_PREFLIGHT_PASS=1")
print(f"PB003_TRANSLATION_EN_COUNT={len(translations)}")
print(f"PB003_CONTENTS_INDEX_COUNT={len(contents)}")
PY

apt-cache pkgnames | sed -n '1p' | grep -q . || { echo "PB003_PREFLIGHT_FAIL=apt_catalog_empty"; exit 92; }

echo "PB003_PREFLIGHT_PASS=1"
echo "PB003_CARRIER_EXEC_REQUEST=1"
exec python3 canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py
