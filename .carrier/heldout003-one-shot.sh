#!/bin/sh
set -eu

echo PB003_CARRIER_PREFLIGHT_BEGIN=1

git_blob() {
  python3 - "$1" <<'PY'
import hashlib,sys
p=sys.argv[1]
b=open(p,"rb").read()
print(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest())
PY
}

check_blob() {
  p="$1"
  exp="$2"
  label="$3"
  got="$(git_blob "$p")"
  echo "PB003_BLOB_${label}=$got"
  if [ "$got" != "$exp" ]; then
    echo "PB003_ABORT_HASH_${label}=1"
    exit 51
  fi
}

check_blob canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_003.json 6ac72c26dacabf8c14e037a5a983e29d912c17e6 MANIFEST
check_blob canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py ccd27d4dd46366c6fb7560378f6f9182f48fd6ae RUNNER
check_blob canonical/runtime/auto_apt_cli_acquisition.py 0b7c67a2680a3aaa1aa5cf1a8bc8d41d69eee271 AUTO_APT
check_blob canonical/runtime/auto_capability_acquisition.py fc80ede8225cc51dac77be6d41aa2a1c757c6ee8 AUTO_CAP
check_blob canonical/runtime/verify_pending_cli_binding.py 8ec4da92080e885a15266389c0318688e6408d43 VERIFY_PENDING
check_blob canonical/runtime/apt_cli_probe.py 3f3a8f6a0154e1ed3f87fc97b99840598297b119 APT_PROBE
check_blob canonical/runtime/capability_discovery.py b9e7423ab24bf2da98869b02d782e791a779892a DISCOVERY
check_blob canonical/runtime/cli_contract_inference.py 009c3c45040178844d84eaa15b0d47ca2e1f259f CONTRACT
check_blob canonical/runtime/goal_compiler.py 195d5dd5f4fabb8a897fb6407433e691a8fdaf26 GOAL_COMPILER
check_blob canonical/runtime/astra_runtime.py dae3f042da75ec5289063bcf74f913f7f31bebbc ASTRA_RUNTIME
check_blob canonical/runtime/auto_npm_library_acquisition.py b74cdf34a96fc2d591b902e1d582e0381a8a8d08 AUTO_NPM
check_blob canonical/runtime/auto_pypi_library_acquisition.py 6387bd7b8f1dba8bb9f66240e3ebb2627085dd2f AUTO_PYPI
check_blob canonical/runtime/auto_python_source_codec_acquisition.py 65453b2eed5e678def3f0ab1c4d44182fb0b9a78 AUTO_PY_SOURCE
check_blob canonical/runtime/independent_npm_codec_verifier.py 06fe2fbd7d5169e2cf455868747ac7077466c221 NPM_VERIFY
check_blob canonical/runtime/npm_package_utils.py 05fd0591083034df48c3ee426d6b3e11e0183555 NPM_UTILS
check_blob canonical/runtime/bound_capabilities/cli_command.py 6782773801cd8f2258e4368a4debbe6e66c4a393 BOUND_CLI
check_blob canonical/runtime/bound_capabilities/node_library_codec.py 0babcf3adf7762b5e24d9c8be4f8ecb3a7b2e805 BOUND_NODE
check_blob canonical/runtime/bound_capabilities/python_library_codec.py e9b9f5c4991ba1f11b9f377a275b3e17bad22886 BOUND_PYLIB
check_blob canonical/runtime/bound_capabilities/python_source_tree_codec.py 8f452c01b2c88a9bd7663f8dc753b24b2e7f7f05 BOUND_PYSRC

python3 -m py_compile canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py canonical/runtime/*.py canonical/runtime/bound_capabilities/*.py
python3 - <<'PY'
import json
s=json.load(open("canonical/astra_runtime/missions/XAPIAN_APT_E2E_INTEGRATION_HELDOUT_003.json"))
assert s["validation_id"]=="XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003"
assert s["freshness"]["state"]=="UNSPENT"
assert int(s["freshness"]["execution_count"])==0
import xapian
print("PB003_SPEC_FRESH=PASS")
print("PB003_XAPIAN=PASS")
PY

command -v sudo >/dev/null
command -v zbarimg >/dev/null
command -v apt-file >/dev/null

PKG="$(find /var/lib/apt/lists -maxdepth 1 -type f -name '*_Packages*' | wc -l | tr -d ' ')"
TR="$(apt-get indextargets --format '$(FILENAME)' 'Identifier: Translations' 'Language: en' | sed '/^$/d' | wc -l | tr -d ' ')"
AMD="$(find /var/lib/apt/lists -maxdepth 1 -type f -name '*Contents-amd64*' | wc -l | tr -d ' ')"
ALL="$(find /var/lib/apt/lists -maxdepth 1 -type f -name '*Contents-all*' | wc -l | tr -d ' ')"
TAGS="$(apt-cache dumpavail | grep -c '^Tag:' || true)"

echo "PB003_PACKAGES=$PKG"
echo "PB003_TRANSLATION_EN=$TR"
echo "PB003_CONTENTS_AMD64=$AMD"
echo "PB003_CONTENTS_ALL=$ALL"
echo "PB003_TAG_RECORDS=$TAGS"

[ "$PKG" -gt 0 ]
[ "$TR" -gt 0 ]
[ "$AMD" -gt 0 ]
[ "$ALL" -gt 0 ]
[ "$TAGS" -gt 0 ]

python3 canonical/tests/test_auto_apt_cli_provider_neutral_admission.py

START=canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json
RESULT=canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json
[ ! -e "$START" ]
[ ! -e "$RESULT" ]

echo PB003_GATE_STILL_UNSPENT=1
echo PB003_CARRIER_PREFLIGHT_PASS=1
echo PB003_CARRIER_EXEC_REQUEST=1

set +e
python3 canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py
rc=$?
set -e

echo "PB003_EVALUATOR_RC=$rc"
if [ -f "$START" ]; then
  echo PB003_START_BEGIN=1
  cat "$START"
  echo PB003_START_END=1
fi
if [ -f "$RESULT" ]; then
  echo PB003_RESULT_BEGIN=1
  cat "$RESULT"
  echo PB003_RESULT_END=1
fi
echo PB003_CARRIER_COMPLETE=1
exit "$rc"
