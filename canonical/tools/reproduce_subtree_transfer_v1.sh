#!/usr/bin/env bash
# Host-side acquisition/evaluation ONLY. Never put this directory in a task image.
# Requires Git, gh (public blobs), Python 3.11 + venv, Linux user/net namespaces.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
w=$(realpath -m "${1:?specify a NEW scratch directory outside the checkout}")
case "$w/" in "$PWD/"*) echo 'use external scratch' >&2; exit 2;; esac
mkdir "$w"
parent=f25f697a439acc2b0d84aa8f5413330f4e2e75cf
variant=b47c0529e99129d4785fecc2cb39a8ec8b4aa5f8
teacher=05f6fd0df4ecbd104eb7a229f9f185c2484dee69
bases=(dcc5dac1846be3bf6e948a2950b93477b9193076 df29852f3a48160e1a60635692c202531dd8b14a)
checksums=(17b7c1a0dfcacf6d410e536ee9e7604e4924f760f68e5ee561c302907d6c1607 79fef5107aec11deca808c06bf430987b3182d125a10ab81c5a0f6cd9280cb1a)
roots=()
for i in 0 1; do
  sha=${bases[i]}
  curl -fsSL "https://codeload.github.com/ansible/ansible/tar.gz/$sha" -o "$w/$sha.tar.gz"
  printf '%s  %s\n' "${checksums[i]}" "$w/$sha.tar.gz" | sha256sum -c -
  python3 - "$w" "$sha" <<'PY'
import sys, tarfile
from pathlib import Path, PurePosixPath
root, sha = Path(sys.argv[1]), sys.argv[2]
with tarfile.open(root / (sha + '.tar.gz')) as archive:
    for m in archive:
        path = PurePosixPath(m.name)
        if m.isfile() and path.parts[:3] == ('ansible-' + sha, 'lib', 'ansible') and path.suffix == '.py':
            if '..' in path.parts: raise ValueError('unexpected archive path')
            out = root.joinpath(sha, *path.parts[1:])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(archive.extractfile(m).read())
PY
  roots+=(--product-root "$w/$sha/lib/ansible")
done
git init -q --bare "$w/click.git"
git --git-dir="$w/click.git" fetch -q --no-tags --depth=12 https://github.com/pallets/click.git "$parent"
test "$(git --git-dir="$w/click.git" rev-parse 'FETCH_HEAD~10')" = "$variant"
mkdir "$w/variant" "$w/parent"
git --git-dir="$w/click.git" archive "$variant" | tar -x -C "$w/variant"
git --git-dir="$w/click.git" cat-file blob "$parent:src/click/core.py" > "$w/parent/core.py"
unshare -c -n env -i HOME="$w" PATH=/usr/bin:/bin LC_ALL=C.UTF-8 PYTHONDONTWRITEBYTECODE=1 \
  python3 -m canonical.tools.subtree_transfer_probe_v1 --parent "$w/parent/core.py" "${roots[@]}" \
  --product-root "$w/variant/src/click" --product-root "$w/parent" --scratch "$w/frozen" > "$w/probe.json"
# The grader's specification is acquired only after candidates are frozen.
gh api "repos/pallets/click/contents/tests/test_arguments.py?ref=$teacher" --jq .content | base64 -d > "$w/check.py"
python3 -m venv "$w/grader-venv"
py="$w/grader-venv/bin/python"
"$py" -m pip install --index-url https://pypi.org/simple pytest==9.2.0 flit_core==3.12.0
"$py" -m pip install --no-deps --no-index --no-build-isolation "$w/variant"
"$py" -m canonical.tools.grade_frozen_click_transfer_v1 --checkout "$w/variant" --teacher-check "$w/check.py" \
  --frozen "$w/frozen/2" --probe "$w/probe.json" --index 2 --output "$w/checks" > "$w/grading.json"
printf 'Measured results: %s/probe.json and %s/grading.json\n' "$w" "$w"
