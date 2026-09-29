#!/bin/sh
set -eu

trap 'rc=$?; trap - EXIT; echo "PB_CARRIER_TRAP_RC=$rc"; exit 0' EXIT

RUNTIME=/work/canonical/runtime/capability_discovery.py
RUNNER=/work/canonical/experiments/run_batched_executable_evidence_heldout_validation_002.py
MANIFEST=/work/canonical/experiments/BATCHED_EXECUTABLE_EVIDENCE_HELDOUT_VALIDATION_002.json
EXPECTED_RUNTIME=eddddaa84dacda5d679c22d34f101aeb1d431678
EXPECTED_RUNNER=42ddd8958134fb27974346889937434b4477fe03
EXPECTED_MANIFEST=acd44dc94c900a16bd09ec88b0d51025c0cab58b

mkdir -p /work/evidence

echo "PB_CARRIER_START=1"
uname -a
cat /etc/os-release | sed -n '1,4p'
python3 --version

blob_sha() {
  python3 - "$1" <<'PY'
import sys, hashlib
p=sys.argv[1]
b=open(p,"rb").read()
print(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest())
PY
}

RT_ACT=$(blob_sha "$RUNTIME")
RUN_ACT=$(blob_sha "$RUNNER")
MAN_ACT=$(blob_sha "$MANIFEST")
echo "PB_BLOB_RUNTIME=$RT_ACT"
echo "PB_BLOB_RUNNER=$RUN_ACT"
echo "PB_BLOB_MANIFEST=$MAN_ACT"
[ "$RT_ACT" = "$EXPECTED_RUNTIME" ] || { echo "PB_ABORT_RUNTIME_HASH"; exit 31; }
[ "$RUN_ACT" = "$EXPECTED_RUNNER" ] || { echo "PB_ABORT_RUNNER_HASH"; exit 32; }
[ "$MAN_ACT" = "$EXPECTED_MANIFEST" ] || { echo "PB_ABORT_MANIFEST_HASH"; exit 33; }

apt-get update > /work/evidence/apt_update.log 2>&1 || {
  echo "PB_ABORT_APT_UPDATE"
  tail -40 /work/evidence/apt_update.log || true
  exit 41
}
apt-file update > /work/evidence/apt_file_update.log 2>&1 || {
  echo "PB_ABORT_APT_FILE_UPDATE"
  tail -40 /work/evidence/apt_file_update.log || true
  exit 42
}

PKG_COUNT=$(find /var/lib/apt/lists -maxdepth 1 -type f -name "*Packages*" | wc -l | tr -d " ")
CONT_AMD64=$(find /var/lib/apt/lists -maxdepth 1 -type f -name "*Contents-amd64*" | wc -l | tr -d " ")
CONT_ALL=$(find /var/lib/apt/lists -maxdepth 1 -type f -name "*Contents-all*" | wc -l | tr -d " ")
echo "PB_APT_PACKAGES_COUNT=$PKG_COUNT"
echo "PB_CONTENTS_AMD64_COUNT=$CONT_AMD64"
echo "PB_CONTENTS_ALL_COUNT=$CONT_ALL"
[ "$PKG_COUNT" -gt 0 ] || { echo "PB_ABORT_NO_PACKAGES"; exit 43; }
[ "$CONT_AMD64" -gt 0 ] || { echo "PB_ABORT_NO_CONTENTS_AMD64"; exit 44; }
[ "$CONT_ALL" -gt 0 ] || { echo "PB_ABORT_NO_CONTENTS_ALL"; exit 45; }

curl -fsSI --max-time 20 https://manpages.ubuntu.com/ > /work/evidence/manpage_headers.txt || {
  echo "PB_ABORT_MANPAGE_HTTPS"
  exit 46
}
echo "PB_MANPAGE_HTTPS=PASS"

sha256sum "$RUNTIME" "$RUNNER" "$MANIFEST" > /work/evidence/input_sha256.txt
touch /work/evidence/pre_run_marker

START_NS=$(date +%s%N)
set +e
cd /work
timeout 600s python3 canonical/experiments/run_batched_executable_evidence_heldout_validation_002.py > /work/evidence/stdout.txt 2> /work/evidence/stderr.txt
RC=$?
set -e
END_NS=$(date +%s%N)

WALL=$(python3 - "$START_NS" "$END_NS" <<'PY'
import sys
print((int(sys.argv[2])-int(sys.argv[1]))/1e9)
PY
)

printf "%s\n" "$RC" > /work/evidence/exit_code.txt
printf "%s\n" "$WALL" > /work/evidence/wall_seconds.txt
echo "PB_VALIDATOR_EXIT_CODE=$RC"
echo "PB_VALIDATOR_WALL_S=$WALL"
if [ "$RC" -eq 124 ]; then echo "PB_VALIDATOR_TIMEOUT=1"; else echo "PB_VALIDATOR_TIMEOUT=0"; fi

echo "PB_EVIDENCE_SHA256_BEGIN"
sha256sum /work/evidence/stdout.txt /work/evidence/stderr.txt /work/evidence/input_sha256.txt /work/evidence/manpage_headers.txt /work/evidence/exit_code.txt /work/evidence/wall_seconds.txt
find /work -type f -newer /work/evidence/pre_run_marker \
  ! -path "/work/evidence/stdout.txt" \
  ! -path "/work/evidence/stderr.txt" \
  ! -path "/work/evidence/exit_code.txt" \
  ! -path "/work/evidence/wall_seconds.txt" \
  -print0 | xargs -0 -r sha256sum
echo "PB_EVIDENCE_SHA256_END"

python3 - <<'PY'
import json
from pathlib import Path
txt=Path("/work/evidence/stdout.txt").read_text(errors="replace")
obj=None
try:
    obj=json.loads(txt)
except Exception:
    try:
        a=txt.find("{"); b=txt.rfind("}")
        if a>=0 and b>a:
            obj=json.loads(txt[a:b+1])
    except Exception:
        pass
print("PB_RESULT_JSON_PARSE="+("1" if isinstance(obj,(dict,list)) else "0"))
def walk(x,path=""):
    if isinstance(x,dict):
        for k,v in x.items():
            lk=str(k).lower()
            if lk in {"cases","case","examples","oracle_hints","oracle_hint"}:
                continue
            np=(path+"."+str(k)) if path else str(k)
            if isinstance(v,(dict,list)):
                walk(v,np)
            elif any(t in lk for t in ("acceptance_gate_pass","recall","precision","wall","promotion_authorized","execution_count","freshness")):
                print("PB_METRIC "+np+"="+str(v))
walk(obj)
PY

echo "PB_RAW_STDOUT_B64_BEGIN"
base64 -w 120 /work/evidence/stdout.txt
echo
echo "PB_RAW_STDOUT_B64_END"
echo "PB_RAW_STDERR_B64_BEGIN"
base64 -w 120 /work/evidence/stderr.txt
echo
echo "PB_RAW_STDERR_B64_END"
echo "PB_ONE_SHOT_COMPLETE=1"
exit 0
