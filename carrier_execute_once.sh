#!/bin/sh
set -eu

CARRIER_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
echo H3_ONE_SHOT_CARRIER_BEGIN=1
echo H3_EXPECTED_MAIN=5fa5571d05c5ed86682921b9226de5b2ebcf73c3

# Preflight is strictly non-spending: it reconstructs exact canonical bytes,
# validates the Debian/Xapian/APT surface, runs focused generic regressions,
# and aborts if either HELDOUT-003 start/result marker already exists.
sh "$CARRIER_DIR/carrier_preflight.sh"

cd /work
START=canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json
RESULT=canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json

test ! -e "$START"
test ! -e "$RESULT"
echo PB003_CARRIER_EXEC_REQUEST=1
echo PB003_SINGLEFLIGHT_ARMED=1

set +e
python3 canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py
RC=$?
set -e

echo PB003_EVALUATOR_EXIT_CODE=$RC
python3 - <<'PY'
import hashlib, pathlib
for label, rel in [
    ("START","canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json"),
    ("RESULT","canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json"),
]:
    p=pathlib.Path(rel)
    if p.is_file():
        raw=p.read_bytes()
        print(f"PB003_{label}_PRESENT=1")
        print(f"PB003_{label}_SHA256={hashlib.sha256(raw).hexdigest()}")
        print(f"PB003_{label}_BYTES={len(raw)}")
    else:
        print(f"PB003_{label}_PRESENT=0")
PY
echo PB003_ONE_SHOT_COMPLETE=1
exit "$RC"
