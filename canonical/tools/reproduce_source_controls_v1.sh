#!/usr/bin/env bash
# Host only. Linux user/mount/PID/net namespaces, Git, gh, Python 3.11 + venv, jq.
# No verifier access. Keep checkouts, environments and task text outside Brain.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
w=$(realpath -m "${1:?specify a NEW external scratch directory}")
case "$w/" in "$PWD/"*) exit 2;; esac
mkdir "$w"
r=canonical/Immediate_Results/source_route_and_acquisition_20261126_v1.json
pin=$(jq -r '.protocol.official_suite_pin' "$r")
for env in base native; do
  jq -r --arg env "$env" '.environments[$env][]' "$r" > "$w/$env.txt"
  python3 -m venv "$w/$env-venv"
  py="$w/$env-venv/bin/python"
  "$py" -m pip install --only-binary=:all: --no-deps --index-url https://pypi.org/simple -r "$w/$env.txt"
  "$py" -c "import site,pathlib; (pathlib.Path(site.getsitepackages()[0])/'receiver-src.pth').write_text('/work/repo/lib\n')"
done
while read -r pos base id digest; do
  repo="$w/$base"; goal="$w/$id.md"
  git init -q --template= "$repo"
  git -C "$repo" fetch -q --depth=1 --no-tags https://github.com/ansible/ansible.git "$base"
  git -C "$repo" checkout -q --detach FETCH_HEAD
  gh api "repos/scaleapi/SWE-bench_Pro-os/contents/v2/tasks/$id/instruction.md?ref=$pin" --jq .content | base64 -d > "$goal"
  printf '%s  %s\n' "$digest" "$goal" | sha256sum -c -
  args=(--base "$repo" --instruction "$goal")
  for env in base native; do
    revs=(c5d59dd0 2aa1c30c)
    if [ "$env" = native ]; then revs=(2aa1c30c bbb51d91); fi
    python3 -m canonical.tools.harbor_source_route_control_v1 "${args[@]}" --venv "$w/$env-venv" \
      --revision "${revs[0]}" --revision "${revs[1]}" > "$w/route-$pos-$env.json"
    python3 -m canonical.tools.measure_native_probe_acquisition_v1 "${args[@]}" --venv "$w/$env-venv" \
      > "$w/acquisition-$pos-$env.json"
  done
done < <(jq -r '.tasks[] | [.position,.base,.instance_id,.instruction_sha256] | @tsv' "$r")
printf 'Source-only measurements: %s/{route,acquisition}-*.json\n' "$w"
