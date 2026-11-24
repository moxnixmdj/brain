#!/usr/bin/env bash
# Standalone Docker diagnostic smoke. No Harbor task, solver, verifier, patch,
# or benchmark. It does not qualify the container boundary for real work.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
command -v docker >/dev/null
command -v python3 >/dev/null
command -v realpath >/dev/null
docker info >/dev/null

scratch="$(mktemp -d)"
container_id=""
cleanup() {
  if [[ -n "$container_id" ]]; then
    docker rm -f "$container_id" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$scratch"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

chmod 0755 "$scratch"
printf 'read-only diagnostic fixture\n' > "$scratch/sentinel"
chmod 0666 "$scratch/sentinel"
source_path="$(realpath "$scratch")"
# Docker may pull this public image during setup. The diagnostic reports the
# resolved image ID; an unpinned tag is not a reproducible benchmark image.
container_id="$(docker run --detach --rm --network none --ipc private \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --mount "type=bind,source=$source_path,target=/opt/brain-ro,readonly" \
  python:3.11-alpine sleep 180)"
full_id="$(docker inspect --format '{{.Id}}' "$container_id")"
printf 'Docker image ID: '
docker inspect --format '{{.Image}}' "$full_id"

# Attempt as UID 0 against a world-writable file: mode bits alone do not make
# this read-only. A successful write or a non-EROFS error is a failed smoke.
docker exec --user 0 "$full_id" python3 -c '
import errno
from pathlib import Path
p = Path("/opt/brain-ro/sentinel")
assert p.read_bytes() == b"read-only diagnostic fixture\n"
try:
    p.write_bytes(b"unexpected write")
except OSError as exc:
    if exc.errno != errno.EROFS:
        raise
    print("READ_ONLY_BIND_WRITE_REFUSED_EROFS")
else:
    raise SystemExit("READ_ONLY_BIND_WRITE_UNEXPECTEDLY_SUCCEEDED")
'

# Inspect output remains in the pipe: Docker inspect may contain secrets and
# must not be written to a world-readable file. The tool intentionally exits
# 2 even on a static match; interpret JSON, never treat it as authorization.
set +e
docker inspect "$full_id" | python3 -m canonical.runtime.harbor_docker_inspect_diagnostic_v1 \
  --container-id "$full_id" --brain-source "$source_path" > "$scratch/diagnostic.json"
pipe_status=("${PIPESTATUS[@]}")
set -e
cat "$scratch/diagnostic.json"
if [[ "${pipe_status[0]}" != 0 || "${pipe_status[1]}" != 2 ]]; then
  echo 'DOCKER_INSPECTION_OR_DIAGNOSTIC_FAILED' >&2
  exit 1
fi
python3 - "$scratch/diagnostic.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as fh:
    result = json.load(fh)
if not result.get('static_filter_passed') or result.get('execution_authorized') is not False:
    raise SystemExit('STATIC_CHECK_NOT_MET')
print('SMOKE_ONLY__NO_HARBOR_OR_SOLVER_OR_VERIFIER_EXECUTED')
PY
