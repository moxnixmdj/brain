#!/bin/bash
set -euo pipefail
cd /work

echo H3_CARRIER_BOOT=1
echo H3_CANONICAL_BASE=5fa5571d05c5ed86682921b9226de5b2ebcf73c3

python3 - <<'PY'
import hashlib, pathlib, sys
expected = {
 "canonical/runtime/auto_apt_cli_acquisition.py":"0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271",
 "canonical/runtime/capability_discovery.py":"b9e7423ab24bf2da98869b02d782e791a779892a",
 "canonical/runtime/auto_capability_acquisition.py":"fc80ede8225cc51dac77be6d41aa2a1c757c6ee8",
 "canonical/runtime/apt_cli_probe.py":"3f3a8f6a0154e1ed3f87fc97b99840598297b119",
 "canonical/runtime/cli_contract_inference.py":"009c3c45040178844d84eaa15b0d47ca2e1f259f",
 "canonical/runtime/verify_pending_cli_binding.py":"8ec4da92080e885a15266389c0318688e6408d43",
 "canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_003.json":"6ac72c26dacabf8c14e037a5a983e29d912c17e6",
 "canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py":"ccd27d4dd46366c6fb7560378f6f9182f48fd6ae",
}
for rel, exp in expected.items():
    raw=pathlib.Path(rel).read_bytes()
    got=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    print(f"H3_BLOB {rel} {got} {'PASS' if got==exp else 'FAIL'}")
    if got != exp:
        sys.exit(81)
start=pathlib.Path("canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json")
result=pathlib.Path("canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json")
if start.exists() or result.exists():
    print("H3_FRESHNESS_FAIL=PREEXISTING_MARKER")
    sys.exit(82)
print("H3_BLOBS_PASS=1")
print("H3_GATE_UNSPENT_LOCAL=1")
PY

python3 -m py_compile canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py canonical/runtime/*.py canonical/runtime/bound_capabilities/*.py
python3 - <<'PY'
import xapian
print("H3_XAPIAN_IMPORT=PASS")
PY

PKG=$(find /var/lib/apt/lists -maxdepth 1 -type f -name "*_Packages*" | wc -l | tr -d " ")
TR=$(find /var/lib/apt/lists -maxdepth 1 -type f -name "*Translation-en*" | wc -l | tr -d " ")
AMD=$(find /var/lib/apt/lists -maxdepth 1 -type f | grep -c "Contents-amd64" || true)
ALL=$(find /var/lib/apt/lists -maxdepth 1 -type f | grep -c "Contents-all" || true)
TAGS=$(apt-cache dumpavail | grep -c "^Tag:" || true)
echo H3_PACKAGES=$PKG
echo H3_TRANSLATION_EN=$TR
echo H3_CONTENTS_AMD64=$AMD
echo H3_CONTENTS_ALL=$ALL
echo H3_TAG_RECORDS=$TAGS
command -v sudo >/dev/null
command -v zbarimg >/dev/null
test "$PKG" -ge 1
test "$TR" -ge 1
test "$AMD" -ge 1
test "$ALL" -ge 1
test "$TAGS" -ge 1

python3 canonical/tests/test_auto_apt_cli_provider_neutral_admission.py

echo H3_PREFLIGHT_PASS=1
echo H3_HELDOUT_003_EXECUTION_START=1
START_NS=$(date +%s%N)
set +e
timeout 195s python3 canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py >/tmp/h3.out 2>/tmp/h3.err
RC=$?
set -e
END_NS=$(date +%s%N)
WALL=$(python3 -c "print(($END_NS-$START_NS)/1000000000.0)")
if [ "$RC" -eq 124 ]; then TO=1; else TO=0; fi
OUTSHA=$(sha256sum /tmp/h3.out | awk '{print $1}')
ERRSHA=$(sha256sum /tmp/h3.err | awk '{print $1}')
echo H3_RUNNER_EXIT_CODE=$RC
echo H3_WRAPPER_WALL_S=$WALL
echo H3_WRAPPER_TIMEOUT=$TO
echo H3_STDOUT_SHA256=$OUTSHA
echo H3_STDERR_SHA256=$ERRSHA
echo H3_STDOUT_BEGIN=1
cat /tmp/h3.out
echo H3_STDOUT_END=1
if [ -s /tmp/h3.err ]; then
  echo H3_STDERR_BEGIN=1
  cat /tmp/h3.err
  echo H3_STDERR_END=1
fi
if [ -f canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json ]; then
  echo H3_RESULT_FILE_BEGIN=1
  cat canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json
  echo H3_RESULT_FILE_END=1
else
  echo H3_RESULT_FILE_MISSING=1
fi
echo H3_ONE_SHOT_COMPLETE=1
exit 0
