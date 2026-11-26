#!/usr/bin/env bash
# PRODUCER ONLY. Build the public input rooms, run the frozen staged policies,
# and retain even empty or incomplete outputs. No tests/solution from evaluators.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
suite=${1:-}; w=$(realpath -m "${2:?provide a NEW external directory}")
case "$suite" in h51|h51-next|tb|scb) ;; *) echo 'choose h51, h51-next, tb, or scb' >&2; exit 2;; esac
case "$w/" in "$PWD/"*) echo 'external directory required' >&2; exit 2;; esac
mkdir "$w"  # Never inherit an earlier room, capture or teacher.
py=${PYTHON311:-python3.11}; py=$(command -v "$py")
[[ $("$py" -c 'import sys; print(sys.version_info[:2])') = '(3, 11)' ]]
public_blob() {  # pinned public repository, ref, relative path, destination
  mkdir -p "$(dirname "$4")"
  gh api -H 'Accept: application/vnd.github.raw+json' "repos/$1/contents/$3?ref=$2" > "$4"
}
synthetic_base() {  # seed directory, timestamp, commit message, output shallow clone
  git -C "$1" add -A
  GIT_AUTHOR_DATE="$2" GIT_COMMITTER_DATE="$2" git -C "$1" -c user.name=Control -c user.email=control@invalid \
    -c commit.gpgsign=false commit -q --allow-empty -m "$3"
  git clone -q --no-tags --depth=1 "$("$py" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).as_uri())' "$1")" "$4"
}
capture() {  # stem (also output filename), clean shallow base, public instruction, revision flags
  local name=$1 base=$2 goal=$3; shift 3
  "$py" -m canonical.tools.harbor_source_route_control_v1 --base "$base" --instruction "$goal" --venv "$w/venv" "$@" > "$w/$name.json"
}
if [[ $suite = h51 || $suite = h51-next ]]; then
  manifest=canonical/Immediate_Results/source_route_and_acquisition_20261126_v1.json
  pin=$(jq -er .protocol.official_suite_pin "$manifest")
  jq -r '.environments.native[]' "$manifest" > "$w/native.txt"
  "$py" -m venv "$w/venv"; "$w/venv/bin/python" -m pip install --only-binary=:all: --no-deps --index-url https://pypi.org/simple -r "$w/native.txt"
  "$w/venv/bin/python" -c "import site,pathlib; (pathlib.Path(site.getsitepackages()[0])/'receiver-src.pth').write_text('/work/repo/lib\n')"
  tasks='.tasks[]'; revisions=(--revision bee38f70 --revision d17cb7c1)
  if [[ $suite = h51-next ]]; then
    manifest=canonical/verification/SINGLE_EPISODE_INPUTS_20261126.json; tasks='.h51.tasks[]'
    pin=$(jq -er .h51.suite "$manifest"); revisions=(--revision "$(jq -er .h51.producer "$manifest")")
  fi
  while read -r pos base id digest; do
    app="$w/base-$pos"; goal="$w/pos-$pos.md"; git init -q --template= "$app"
    git -C "$app" fetch -q --no-tags --depth=1 https://github.com/ansible/ansible.git "$base"; git -C "$app" checkout -q --detach FETCH_HEAD
    public_blob scaleapi/SWE-bench_Pro-os "$pin" "v2/tasks/$id/instruction.md" "$goal"
    printf '%s  %s\n' "$digest" "$goal" | sha256sum -c -
    capture "pos-$pos" "$app" "$goal" "${revisions[@]}"
  done < <(jq -r "$tasks"'|[.position,.base,.instance_id,.instruction_sha256]|@tsv' "$manifest")
else
  "$py" -m venv --without-pip "$w/venv"  # Original blank/terminal producer, NOT the grader runtime.
  if [[ $suite = tb ]]; then
    pin=4070d6cef56a7d20cb5dc98d5e10ada88a6b9440; repo=harbor-framework/terminal-bench
    for n in music-harmony sound-change-cascade; do
      src="tasks/$n"; seed="$w/seed-$n"; base="$w/base-$n"; git init -q --template= "$seed"
      if [[ $n = music-harmony ]]; then
        date=2026-11-26T20:22:08Z; public_blob "$repo" "$pin" "$src/environment/data/Harmony.pdf" "$seed/Harmony.pdf"
      else
        date=2026-11-26T20:22:10Z
        for f in data/train.tsv engine/{apply.py,example_rules.json}; do public_blob "$repo" "$pin" "$src/environment/$f" "$seed/$f"; done
      fi
      public_blob "$repo" "$pin" "$src/instruction.md" "$w/$n.md"
      synthetic_base "$seed" "$date" 'public environment' "$base"
      capture "$n" "$base" "$w/$n.md" --revision d17cb7c1
    done
  else
    git init -q --template= "$w/seed"; synthetic_base "$w/seed" 2026-11-26T20:10:07Z empty "$w/base"
    for n in cfgpipe circuit_eval; do
      public_blob gabeorlanski/scb-problems 9cd9ca3a51c3d3e2a99d2488a25baf73a2204451 "$n/checkpoint_1.md" "$w/$n.md"
      capture "$n" "$w/base" "$w/$n.md" --revision b10e2cd7
    done
  fi
fi
(cd "$w" && sha256sum -- *.json > capture-sha256.txt)
printf 'Frozen producer outputs (no verdict) in %s\n' "$w"
