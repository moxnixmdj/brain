#!/usr/bin/env bash
# GRADER ONLY. Reviewed sources, Linux user/mount/PID/network namespaces; never run a solver here.
# Usage: bash ...sh h51|tb|scb NEW_EXTERNAL_DIRECTORY. See WITNESSED_ROUTES_REPRODUCTION.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
suite=${1:?choose h51, h51-next, tb, or scb}; w=$(realpath -m "${2:?provide a new directory outside the checkout}")
case "$w/" in "$PWD/"*) echo 'external directory required' >&2; exit 2;; esac
mkdir "$w"; I="$PWD/canonical/Immediate_Results"; py=${PYTHON311:-python3.11}; py=$(command -v "$py")
[[ $($py -c 'import sys;print(sys.version_info[:2])') = '(3, 11)' ]]
blob() { # repository, commit, relative path in upstream repository, local destination
  mkdir -p "$(dirname "$4")"; gh api -H 'Accept: application/vnd.github.raw+json' "repos/$1/contents/$3?ref=$2" > "$4";
}
# Only task data from a pinned public release; never follow links/submodules.
tree() { gh api "repos/$1/git/trees/$2?recursive=1" | jq -r 'if .truncated then error("truncated tree") else .tree[] | select(.type=="blob" and (.mode=="100644" or .mode=="100755")) | .path end'; }
result() { printf '%s/%s_20261126_v1.json\n' "$I" "$1"; }
case "$suite" in
h51|h51-next)
  prov=$(result source_route_and_acquisition); pin=$(jq -r .protocol.official_suite_pin "$prov"); repo=scaleapi/SWE-bench_Pro-os
  jq -r '.environments.native[]' "$prov" > "$w/requirements.txt"
  "$py" -m venv "$w/venv"; "$w/venv/bin/python" -m pip install --only-binary=:all: --no-deps --index-url https://pypi.org/simple -r "$w/requirements.txt"
  "$w/venv/bin/python" -c "import site,pathlib; (pathlib.Path(site.getsitepackages()[0])/'receiver-src.pth').write_text('/work/repo/lib\n')"
  rows='.tasks[]'
  if [[ $suite = h51-next ]]; then
    prov=$PWD/canonical/verification/SINGLE_EPISODE_INPUTS_20261126.json
    pin=$(jq -er .h51.suite "$prov"); rows='.h51.tasks[]'
    # The release invokes the real pytest console script by name at position 7.
    # Relocate its pip-generated interpreter path, never edit the upstream runner.
    sed -i '1c#!/venv/bin/python' "$w/venv/bin/pytest"
    # Python 3.9 must work relocated to /venv in the private verifier root.
    # Provide a clean CPython prefix; the 3.11 grader cannot run this release's 3.9 units.
    cp -a "${PYTHON39_PREFIX:?need relocatable CPython 3.9.25 prefix}" "$w/py39"
    [[ $("$w/py39/bin/python3.9" -c 'import platform;print(platform.python_version())') = 3.9.25 ]]
    ln -sf python3.9 "$w/py39/bin/python"; ln -sf python3.9 "$w/py39/bin/python3"
    jq -r '.h51.grade8_packages[]' "$prov" > "$w/grade39.txt"
    "${UV:-uv}" pip install --no-deps --only-binary=:all: --index-url https://pypi.org/simple --python "$w/py39/bin/python3.9" -r "$w/grade39.txt"
  fi
  while read -r pos base id; do
    app="$w/base-$pos"; task="$w/grade/$id"; git init -q --template= "$app"
    git -C "$app" fetch -q --no-tags --depth=1 https://github.com/ansible/ansible.git "$base"; git -C "$app" checkout -q --detach FETCH_HEAD
    for file in tests/{test.sh,config.json,test_patch.patch,parser.py,run_script.sh} solution/gold_patch.diff; do blob "$repo" "$pin" "v2/tasks/$id/$file" "$task/$file"; done
    venv="$w/venv"; seconds=220
    case "$pos" in 7) seconds=1200;; 8) venv="$w/py39"; seconds=600;; esac
    "$py" -m canonical.tools.replay_source_verifier_v1 "$app" "$task" "$venv" "$(result hard51_pos${pos}_source_predictions)" --verifier-timeout "$seconds" --jobs "${GRADER_JOBS:-1}" > "$w/pos-$pos.json"
  done < <(jq -r "$rows"'|[.position,.base,.instance_id]|@tsv' "$prov")
  ;;
tb)
  repo=harbor-framework/terminal-bench; pin=4070d6cef56a7d20cb5dc98d5e10ada88a6b9440; uv=${UV:-uv}
  tree "$repo" "$pin" > "$w/tree.txt"
  for n in music-harmony sound-change-cascade; do
    app="$w/base-$n"; task="$w/grade/$n"; venv="$w/venv-$n"; pred=$(result "tb41_${n//-/_}_source_predictions")
    git init -q --template= "$app"
    if [[ $n = music-harmony ]]; then date=2026-11-26T20:22:08Z; blob "$repo" "$pin" "tasks/$n/environment/data/Harmony.pdf" "$app/Harmony.pdf"
    else date=2026-11-26T20:22:10Z; for f in data/train.tsv engine/{apply.py,example_rules.json}; do blob "$repo" "$pin" "tasks/$n/environment/$f" "$app/$f"; done; fi
    git -C "$app" add -A
    # Match the synthetic base *object*, including the original commit clock.
    GIT_AUTHOR_DATE=$date GIT_COMMITTER_DATE=$date git -C "$app" -c user.name=Control -c user.email=control@invalid -c commit.gpgsign=false commit -qm 'public environment'
    [[ $(git -C "$app" rev-parse HEAD) = $(jq -r '.rows[0].measurement.base' "$pred") ]]
    while read -r f; do blob "$repo" "$pin" "$f" "$task/${f#tasks/$n/}"; done < <(grep -E "^tasks/$n/(solution|tests)/" "$w/tree.txt")
    if [[ -n ${PYTHON312_PREFIX:-} ]]; then cp -a "$PYTHON312_PREFIX" "$venv"  # relocatable CPython install
    else "${PYTHON312:-python3.12}" -m venv --copies --without-pip "$venv"; fi
    (cd "$task/tests" && "$uv" export --frozen --no-dev --no-emit-project --no-header --format requirements-txt) > "$w/$n.txt"
    "$uv" pip install --python "$venv/bin/python3" --index-url https://pypi.org/simple --require-hashes -r "$w/$n.txt"
    if [[ $n = music-harmony ]]; then
      "$uv" pip install --python "$venv/bin/python3" --index-url https://pypi.org/simple pip==25.3
      # Relocate the real pip CLI's interpreter to its in-grader path. The oracle may
      # only check an ALREADY installed package; source_verifier_root forbids index access.
      sed -i '1c#!/venv/bin/python3' "$venv/bin/pip"
    fi
    "$py" -m canonical.tools.replay_tb_source_v1 "$app" "$task" "$venv" "$pred" > "$w/$n.json"
  done
  ;;
scb)
  repo=gabeorlanski/scb-problems; pin=9cd9ca3a51c3d3e2a99d2488a25baf73a2204451
  tree "$repo" "$pin" > "$w/tree.txt"; "$py" -m venv "$w/env"; p="$w/env/bin/python"
  "$p" -m pip install --index-url https://pypi.org/simple --only-binary=:all: --no-deps pytest==9.2.0 iniconfig==2.3.1 packaging==26.4 pluggy==1.7.0 Pygments==2.21.0
  for n in cfgpipe circuit_eval; do
    pred=$(result "scbench_${n}_cp1_cold"); entry=cfgpipe.py; [[ $n != circuit_eval ]] || entry=circopt.py
    # This evaluator shortcut is only valid for the recorded clean EMPTY captures.
    jq -e '.rows|length==1 and (.[0]|.launcher.returncode==0 and .measurement.capture_exit==0 and .measurement.patch_bytes==0 and .measurement.patch_sha256=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" and .measurement.base=="f63176b7989985c3dc60211d6bbd3f07ac66e167")' "$pred" >/dev/null
    while read -r f; do blob "$repo" "$pin" "$n/tests/$f" "$w/$n.tests/$f"; done < <(jq -r --arg n "$n" '.rows[] | select(.suite==$n) | .public_tests|keys[]' "$(result scbench_cp1_source_grades)")
    while read -r f; do blob "$repo" "$pin" "$f" "$w/$n.reference/${f#$n/solutions/checkpoint_1/}"; done < <(grep "^$n/solutions/checkpoint_1/" "$w/tree.txt")
    mkdir "$w/$n.cold"; for arm in cold reference; do
      ep=$("$py" -c 'import shlex,sys;print(shlex.join(sys.argv[1:]))' "$p" "$w/$n.$arm/$entry")
      rc=0; (cd "$w"; unshare -Urn bash -ec 'ip link set lo up; exec env -i HOME=/tmp LC_ALL=C.UTF-8 PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 "$@"' _ "$p" -m pytest -q --tb=no -p no:cacheprovider --rootdir="$w" --entrypoint="$ep" --checkpoint=checkpoint_1 --junitxml="$w/$n.$arm.xml" "$w/$n.tests/test_checkpoint_1.py") || rc=$?
      printf '%s\n' "$rc" > "$w/$n.$arm.exit" # a reference error is never a candidate failure
    done
  done
  ;;
*) echo 'choose h51, h51-next, tb, or scb' >&2; exit 2;;
esac
printf 'Native source measurements in %s (not an official image grade).\n' "$w"
