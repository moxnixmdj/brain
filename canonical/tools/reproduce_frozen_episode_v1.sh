#!/usr/bin/env bash
# Same-session replay, never request a new demonstration or give a producer the grade.
set -euo pipefail
repo=$(git rev-parse --show-toplevel); cd "$repo"; mode=${1:?choose screen or cues}
w=$(realpath -m "${2:?new external directory required}"); case "$w/" in "$repo/"*) exit 2;; esac
mkdir "$w"; I=$repo/canonical/Immediate_Results; pins=$repo/canonical/verification/SINGLE_EPISODE_INPUTS_20261126.json
case "$mode" in
screen)
  src=$(jq -r .arc.environment_repository "$pins"); rev=$(jq -r .arc.rev "$pins")
  # Only the 50 environment files. Do not stage somebody else's player or replay.
  curl -fsSL "https://codeload.github.com/$src/tar.gz/$rev" | tar -xz --strip-components=1 -C "$w" --wildcards "${src##*/}-$rev/environment_files/*"
  py=${PYTHON312:-python3.12}; [[ $($py -c 'import platform;print(platform.python_version())') = 3.12.12 ]]
  "$py" -m venv --without-pip "$w/env"; jq -r '.arc.requirements[]' "$pins" > "$w/requirements.txt"
  "${UV:-uv}" pip install --python "$w/env/bin/python" --no-deps --only-binary=:all: --index-url https://pypi.org/simple -r "$w/requirements.txt"
  (cd "$w"; unshare -crn env -i HOME="$w" LC_ALL=C.UTF-8 PATH=/usr/sbin:/usr/bin:/bin PYTHONPATH="$repo" PYTHONDONTWRITEBYTECODE=1 \
     "$w/env/bin/python" -m canonical.tools.frame_program_trial_v1 "$w/environment_files" "$w/results" \
      --previous "$I/public_screen_one_episode_20261126_v1.json")
  python3 - "$I/public_screen_sleep_20261126_v1.json" "$w/results/result.json" <<'PY'
import json, sys
a,b=[json.load(open(f)) for f in sys.argv[1:]]
assert a['one_teacher']==b['one_teacher'] and a['env_tree_sha256']==b['env_tree_sha256']
def evidence(x): return [{k:v for k,v in r.items() if k!='wall_seconds'} for r in x['rows']]
if evidence(a)!=evidence(b):sys.exit('Observed per-room divergence: retain and inspect both results')
print(f"Same observations, actions, resets, support and scorecard totals for {len(b['rows'])} rooms")
PY
  ;;
cues)
  src=$(jq -r .locomo.repo "$pins"); rev=$(jq -r .locomo.rev "$pins"); f="$w/released.json"
  gh api -H 'Accept: application/vnd.github.raw+json' "repos/$src/contents/data/locomo_plus.json?ref=$rev" > "$f"
  printf '%s  %s\n' "$(jq -r .locomo.raw_sha256 "$pins")" "$f" | sha256sum -c -
  run() { python3 -B -m canonical.tools.cue_contrast_v1 "$@"; }
  run project "$f" "$w/input.json"; printf '%s  %s\n' "$(jq -r .locomo.projected_sha256 "$pins")" "$w/input.json" | sha256sum -c -
  for arm in base origin ties stable; do
    pred=$I/cue_retrieval_${arm}_20261126_v1.json
    run capture "$w/input.json" "$w/$arm.json" "$(jq -r .producer_revision "$pred")"
  done
  run grade "$f" "$w/grades.json" "$w"/{base,origin,ties,stable}.json
  python3 - "$I" "$w" <<'PY'
import json,sys
from pathlib import Path
i,w=map(Path,sys.argv[1:])
bad=False
old=json.loads((i/'cue_retrieval_grades_20261126_v1.json').read_bytes())['grades']
new=json.loads((w/'grades.json').read_bytes())['grades']
for n,arm in enumerate(('base','origin','ties','stable')):
    a,b=[json.loads(p.read_bytes()) for p in (i/f'cue_retrieval_{arm}_20261126_v1.json',w/f'{arm}.json')]
    ap,bp=a.pop('predictions'),b.pop('predictions'); ap.pop('seconds');bp.pop('seconds')
    ids_a,ids_b=ap.pop('rrf'),bp.pop('rrf')
    diffs=sum(ids_a[q]!=ids_b.get(q) for q in ids_a)
    if a!=b or ap!=bp or ids_a.keys()!=ids_b.keys():bad=True
    # Historical floating sums are not byte-stable. Preserve all differences;
    # stable, added *after* that finding, must reproduce every ordered ID.
    print(f'{arm}: {diffs} differing top-five lists; counts {new[n]["modes"]["rrf"]["total_at1_at5"]["all"]}')
    if arm=='stable' and diffs:bad=True
    if n < len(old) and old[n]['modes']!=new[n]['modes']:
        print('Historical individual grade difference:',arm);bad=True
if bad:sys.exit('Divergence: retain all captures and grades for inspection')
PY
  ;;
*) echo 'choose screen or cues' >&2; exit 2;;
esac
