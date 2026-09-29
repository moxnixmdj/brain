#!/bin/sh
set -eu
echo H3_PREFLIGHT_BEGIN=1
export DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8
rm -rf /work
mkdir -p /work
CARRIER_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rm -f /etc/apt/apt.conf.d/docker-no-languages || true
apt-get update -qq
apt-get install -y -qq --no-install-recommends python3 python3-xapian sudo apt-file zbar-tools ca-certificates >/tmp/h3_install.log 2>&1
apt-file update >/tmp/h3_aptfile.log 2>&1
python3 "$CARRIER_DIR/carrier_payload_1.py"
python3 "$CARRIER_DIR/carrier_payload_2.py"
python3 "$CARRIER_DIR/carrier_payload_3.py"
cd /work
python3 -m py_compile canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py canonical/runtime/*.py canonical/runtime/bound_capabilities/*.py
sudo -n true
python3 - <<'PY'
import xapian,sys
sys.path.insert(0,"canonical/runtime")
import auto_apt_cli_acquisition,capability_discovery,apt_cli_probe,cli_contract_inference,verify_pending_cli_binding
print("H3_IMPORTS_PASS=1")
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
test "$PKG" -ge 1
test "$TR" -ge 1
test "$AMD" -ge 1
test "$ALL" -ge 1
test "$TAGS" -ge 1
python3 canonical/tests/test_auto_apt_cli_provider_neutral_admission.py
test ! -e canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json
test ! -e canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json
echo H3_GATE_UNSPENT=1
echo H3_PREFLIGHT_PASS=1
