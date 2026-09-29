FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /work

RUN set -eu;     rm -f /etc/apt/apt.conf.d/docker-no-languages;     apt-get update -qq;     apt-get install -y -qq --no-install-recommends       python3 python3-pytest python3-xapian sudo apt-file zbar-tools ca-certificates >/tmp/h3-install.log 2>&1;     apt-file update >/tmp/h3-apt-file.log 2>&1

COPY . /work

RUN set -eu;     python3 - <<'PY'
import hashlib, pathlib, sys
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
def blob_sha(p):
    raw = pathlib.Path(p).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
for path, exp in expected.items():
    got = blob_sha(path)
    print(f"H3_BLOB={path}={got}={'PASS' if got == exp else 'FAIL'}")
    if got != exp:
        sys.exit(51)
print("H3_EXACT_BYTES_PASS=1")
PY

RUN set -eu;     python3 -m py_compile       canonical/runtime/capability_discovery.py       canonical/runtime/auto_capability_acquisition.py       canonical/runtime/apt_cli_probe.py       canonical/runtime/cli_contract_inference.py       canonical/runtime/verify_pending_cli_binding.py       canonical/runtime/auto_apt_cli_acquisition.py       canonical/experiments/run_xapian_apt_e2e_integration_heldout_003.py;     python3 canonical/tests/test_auto_apt_cli_provider_neutral_admission.py;     python3 - <<'PY'
import xapian
print("H3_XAPIAN_IMPORT_PASS=1")
PY

RUN set -eu;     PKG="$(find /var/lib/apt/lists -maxdepth 1 -type f -name '*_Packages*' | wc -l | tr -d ' ')";     TR="$(find /var/lib/apt/lists -maxdepth 1 -type f -name '*Translation-en*' | wc -l | tr -d ' ')";     AMD="$(find /var/lib/apt/lists -maxdepth 1 -type f | grep -c 'Contents-amd64' || true)";     ALL="$(find /var/lib/apt/lists -maxdepth 1 -type f | grep -c 'Contents-all' || true)";     TAGS="$(apt-cache dumpavail | grep -c '^Tag:' || true)";     echo "H3_PACKAGES=$PKG";     echo "H3_TRANSLATION_EN=$TR";     echo "H3_CONTENTS_AMD64=$AMD";     echo "H3_CONTENTS_ALL=$ALL";     echo "H3_TAG_RECORDS=$TAGS";     test "$PKG" -ge 1;     test "$TR" -ge 1;     test "$AMD" -ge 1;     test "$ALL" -ge 1;     test "$TAGS" -ge 1;     command -v sudo >/dev/null;     command -v zbarimg >/dev/null;     test ! -e canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__EXECUTION_START.json;     test ! -e canonical/astra_runtime/evidence/XAPIAN-APT-E2E-INTEGRATION-HELDOUT-003__RESULT.json;     echo H3_BUILD_PREFLIGHT_PASS=1

CMD ["/bin/sh", "-lc", "echo H3_CARRIER_READY=1"]
