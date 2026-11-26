# Reproduce the witnessed-route experiments

From the repository root. Use **new directories outside Brain** on disposable Linux. Keep the upstream grading trees and online setup on the host. Nothing below is an authorized sandbox for hostile code. Do not give these evaluation artifacts, instructions with answers, or reference solutions to a future producer. Fresh process and fresh checkout do not imply independent review.

## Native source grades and the positive composition control

Prerequisites: user/mount/PID/network namespaces, `bash`, `git`, `gh` (public code), `jq`, `ip`, `setpriv`, `chroot`, Python 3.11 + `venv`. For TB also `uv` (used 0.9.30) and a complete Python **3.12** available under the read-only `/usr` mount, or set `PYTHON312_PREFIX` to a relocatable Python 3.12 install containing `bin/python3`, stdlib and extension modules. The trial used 3.12.12 built from CPython's `v3.12.12` tag. A venv pointing to an interpreter elsewhere in `/tmp` won't work inside chroot. Network is for the build host only. The named producer commits must be present in the checkout's history.

**Produce:** fetch only public base/instruction/environment files, build a clean single-commit shallow receiver and invoke the staged controller in a fresh namespace per arm. The script selects `bee38f70`/`d17cb7c1` for Ansible, `d17cb7c1` for TB and `b10e2cd7` for the blank checkpoints. It writes a SHA-256 manifest even for empty captures. It has no grading path.

```bash
bash canonical/tools/reproduce_witnessed_source_captures_v1.sh h51 /tmp/brain-produce-pro
bash canonical/tools/reproduce_witnessed_source_captures_v1.sh tb  /tmp/brain-produce-tb
bash canonical/tools/reproduce_witnessed_source_captures_v1.sh scb /tmp/brain-produce-scb
```

**Grade:** use *different* fresh directories. For the relocatable TB toolchain installed in this session, prefix the TB command with `UV=/tmp/brain-waves-92aa/tb/tools/bin/uv PYTHON312_PREFIX=/tmp/brain-waves-92aa/tb/pyroot/venv`. Elsewhere use your own matching install; these absolute paths are not repository dependencies.

```bash
bash canonical/tools/reproduce_frozen_source_grades_v1.sh h51 /tmp/brain-check-pro
bash canonical/tools/reproduce_frozen_source_grades_v1.sh tb  /tmp/brain-check-tb
bash canonical/tools/reproduce_frozen_source_grades_v1.sh scb /tmp/brain-check-scb
```

These commands **grade the recorded captures**, not new solver outputs. H51 emits `pos-{5,6}.json` with per-arm required status counts (including `MISSING` if applicable), verifier exit and reward file. TB emits `<room>.json`: real `checks.py` via the released `tests/test.sh`, local locked dependencies, all-pass RewardKit. **Correction:** the initial TB protocol anticipated pytest; this is the suite entrypoint actually measured. A reference gets `/solution` without `/tests`; only its resulting `/app` is copied into a fresh judging room. `pip` in the music oracle is real, offline and already satisfied from the lock. SlopCodeBench emits four JUnit XMLs + exit codes. Require equal case identities within each problem; no global checkpoint grade from individual passed cases. Whether the missing `cfgpipe` program passes one negative test can depend on the executable path, as described in the report. Check ratios and identities, not output hashes containing temporary names or times.

To judge a **newly frozen capture** on the already provisioned grader, substitute it only at the evaluator boundary, for example:

```bash
G=/tmp/brain-check-pro; P=/tmp/brain-produce-pro
id=$(jq -r '.tasks[]|select(.position==5)|.instance_id' canonical/Immediate_Results/source_route_and_acquisition_20261126_v1.json)
python -m canonical.tools.replay_source_verifier_v1 "$G/base-5" "$G/grade/$id" "$G/venv" "$P/pos-5.json" > "$G/new-pos-5.json"
G=/tmp/brain-check-tb; P=/tmp/brain-produce-tb; n=music-harmony
python -m canonical.tools.replay_tb_source_v1 "$G/base-$n" "$G/grade/$n" "$G/venv-$n" "$P/$n.json" > "$G/new-$n.json"
```

For SCB the grader script has a deliberate **empty-patch-only** shortcut and checks that exact digest and base. Do not use it to claim a grade on a changed product. The historical paired acquisition controls and old routes can be reprovisioned separately with `reproduce_source_controls_v1.sh NEW_DIR`.

The deliberately solvable **engineering control** uses the earlier base Python dependencies but no demonstration or gold expression in the staged mount:

```bash
V=$(mktemp -d)/base-venv
python3.11 -m venv "$V"
jq -r '.environments.base[]' canonical/Immediate_Results/source_route_and_acquisition_20261126_v1.json > "$V/requirements.txt"
"$V/bin/python" -m pip install --index-url https://pypi.org/simple --no-deps --only-binary=:all: -r "$V/requirements.txt"
python -m canonical.tools.probe_staged_composition_v1 /tmp/brain-composed "$V"
```

## Browser interventions and grading

Node 22.22.3, experimental Chromium headless shell 158.0.0 (Linux x64), npm on the **build** host. Only the four demo directories and their public dependencies belong in the local web root; do not serve a directory holding grading data. The client receives no page implementation, prompt corpus, grade metadata or gold calls through its decision API. Trusted program/input separation, not adversarial file-access confinement. The CDP bridge and Chrome run inside a loopback-only namespace. No externally accessible server.

```bash
set -euo pipefail
B=$PWD; W=$(mktemp -d); U=$W/up; G=$W/judge; P=$W/pages; E=$W/browser
pin=f3faa835f3fdeab42e41b055209d6954b192f653
mkdir -p "$U" "$G" "$P" "$E" "$W/one" "$W/two"
curl -fsSL "https://codeload.github.com/GoogleChromeLabs/webmcp-tools/tar.gz/$pin" | tar xz -C "$U" --strip-components=1
mkdir "$P/demos"; cp -r "$U"/demos/{doors,pizza-maker,french-bistro,pixel-art-studio,shared} "$P/demos/"
cp -r "$U/webmcp-evals" "$G/"
(cd "$P/demos/pixel-art-studio" && npm ci --registry=https://registry.npmjs.org && npm run build)
(cd "$E" && npm install --registry=https://registry.npmjs.org @sparticuz/chromium@158.0.0 && node --input-type=module -e 'import c from "@sparticuz/chromium"; console.log(await c.executablePath())' > exe)
EXE=$(tail -1 "$E/exe"); mkdir -p "$E/libs"
node -e 'const fs=require("node:fs"),z=require("node:zlib");process.stdout.write(z.brotliDecompressSync(fs.readFileSync(process.argv[1])))' "$E/node_modules/@sparticuz/chromium/bin/al2023.tar.br" | tar x -C "$E/libs"
code=(canonical/{runtime,tools,swe_kernel,unified_model})
git archive b10e2cd7 "${code[@]}" | tar x -C "$W/one"; git archive 731530b5 "${code[@]}" | tar x -C "$W/two"
```

The bridge uses Node’s built-in WebSocket and expects `node` under `/usr/local/bin:/usr/bin:/bin`. The full model artifact is present for this route; unlike cold Harbor this is **not** an audited minimal mount. Extract only the text of single-message user goals into the producer inputs. The first selection is indices `[0,8)` per suite (or all if shorter); follow-up is the remaining Doors and Pixel Art indices. Don't use the upstream smoke test as a solver: it executes expected calls.

```bash
python - "$G/webmcp-evals/examples" "$W" <<'PY'
import json,sys
from pathlib import Path
src,w=map(Path,sys.argv[1:]); first={}; follow=[]
for s in ('doors','pizza-maker','french-bistro','pixel-art-studio'):
    rows=json.loads((src/s/'evals.json').read_text()); goals=[]
    for r in rows:
        ms=r['messages']; goals.append(ms[0]['content'] if len(ms)==1 and ms[0]['role']=='user' else None)
    first[s]=goals[:8]
    if s in ('doors','pixel-art-studio'):follow += [dict(suite=s,index=i,goal=goals[i]) for i in range(8,len(goals))]
(w/'prompts.json').write_text(json.dumps(first));(w/'follow.json').write_text(json.dumps(follow))
PY
offline() { unshare -Urn bash -ec 'ip link set lo up; exec env -i HOME=/tmp LC_ALL=C.UTF-8 PATH="$1" LD_LIBRARY_PATH="$2" PYTHONDONTWRITEBYTECODE=1 "${@:3}"' _ "$PATH" "$E/libs/lib" "$@"; }
offline python "$W/one/canonical/tools/live_interface_trial_v1.py" "$W/prompts.json" "$P" "$EXE" "$W/first.json"
for arm in original scoped; do
  flags=(--checkout "$W/two"); [[ $arm != original ]] || flags=(--checkout "$W/one" --original)
  offline python "$B/canonical/tools/live_interface_followup_v1.py" "${flags[@]}" "$W/follow.json" "$P" "$EXE" "$W/$arm.json"
done
jq -s '{rows:(.[0]+.[1])}' "$W/original.json" "$W/scoped.json" > "$W/pair.json"
sha256sum "$W/first.json" "$W/pair.json" # freeze before grading
(cd "$G" && npm install --registry=https://registry.npmjs.org @types/node@22.19.3)
J=$G/webmcp-evals; "$P/demos/pixel-art-studio/node_modules/.bin/tsc" --target ES2022 --module commonjs --esModuleInterop --skipLibCheck --types node --typeRoots "$G/node_modules/@types" --outDir "$J/js" "$J/src/utils.ts"
# Compile output is CommonJS; avoid interpreting it under a parent's module-type setting.
printf '{"type":"commonjs"}\n' > "$J/js/package.json"
node canonical/tools/grade_live_interface_trial_v1.cjs "$W/first.json" "$J" > "$W/first.grade.json"
node canonical/tools/grade_live_interface_trial_v1.cjs "$W/pair.json" "$J" > "$W/pair.grade.json"
offline python -m canonical.tools.grade_frozen_door_effects_v1 "$W/pair.json" "$P" "$EXE" > "$W/effects.json"
```

The pinned demo suites contain 14, 9, 2 and 17 cases, respectively. The first selection is 26 cases total; follow-up adds 6 Doors and 9 Pixel Art cases, not the ninth pizza case. Origin ports, timing, profiles, latency-sensitive navigation and hashes that include origins need not match. Do not call an interrupted invocation a mismatch. The effect grader can also use the committed follow-up predictions instead of `$W/pair.json`. Its settled readout repeats *observation*, never the action. It grades all 6 Doors follow-ups, not the 9 Pixel Art questions or the 104 original rows.

## Dialogue slice

Stage the exact HEAMS fixture on the host, not as a file seen by the reader. Use commit `1d709be7` for historical predictions (subsequent atomicity/cutoff fixes didn't retroactively grade the old output). Reuse the same sanitized `offline` function or use `unshare -c -n env -i PATH=/usr/bin:/bin HOME=/tmp LC_ALL=C.UTF-8` for each Python stage.

```bash
ref=c09771f7978646e90580d974e90d92574eeba66e
f=python_package/tests/fixtures/smoke_e2e/erasability_editability/smoke.json
gh api -H 'Accept: application/vnd.github.raw+json' "repos/milatechtransfer/heams/contents/$f?ref=$ref" > "$W/episode.json"
mkdir "$W/dialogue"; git archive 1d709be7 canonical | tar x -C "$W/dialogue"
D="$W/dialogue/canonical/tools/dialogue_slice_v1.py"
python "$D" split "$W/episode.json" | offline python "$D" predict "$W/new-memory" > "$W/answers.jsonl"
sha256sum "$W/answers.jsonl"
python canonical/tools/dialogue_slice_v1.py grade "$W/episode.json" "$W/answers.jsonl" > "$W/grades.json"
```

With the authors’ original flat data provisioned by an authorized evaluator, the same splitter can stream it instead of the fixture. Keep gold fields and future dialogue upstream of the pipe. The exact-string grader remains nonofficial on either file. No official MEME judge invoked. The authors' full timed episodes and semantic grading would be a different run.

## Calling the full runtime versus scoring it

`open_model().solve_swe_repo_native(path, test_targets=..., candidate_files=..., repair_store=external_path)` returns the native result inside `swe_result`. Use a disposable project. The [restart/forget test](../tests/test_witnessed_native_route_v1.py) includes an executable teacher and renamed receiver, checks which template actually won, and reruns without it. The staged Harbor path above does **not** call this method. `Creature.revision_memory('ingest_turn', role='user', text=..., turn=..., source=...)` and `revision_memory('answer_question', question=..., valid_at=..., known_at=...)` address the creature's own SQLite file. Direct model calls take the file path before the operation. The [browser control](../tests/test_contrast_and_browser_boundary_v1.py) constructs a fresh `GuiRoom` and calls both front doors with a live origin; a tool fixture or JavaScript string returned by a planner is not a drop-in substitute.

To reproduce the fixed-index measurement, without modifying the index:

```bash
offline python - <<'PYATLAS'
from pathlib import Path
import json
from canonical.tools.domain_atlas_v1 import reachability
root=Path.cwd(); a=json.loads((root/'canonical/unified_model/DOMAIN_ATLAS_V1.json').read_text())
rows=[r for domain in reachability(a,root,5).values() for r in domain['rows']]
for k in ('frontier','native'):
    subset=[r for r in rows if r['kind']==k]
    print(k, sum(r['source_hit'] for r in subset), sum(r['route_hit'] for r in subset), len(subset))
PYATLAS
```

These outputs (source hit / route hit / questions) are not task grades. To rebuild instead, pass an **absolute external path** to `python -m canonical.tools.domain_atlas_v1 --top-k 5 --out /tmp/fresh-brain-atlas.json`; omitting `--out` would rewrite the shipped index. The module scan count is revision-specific.

## Runtime regression suite

Use a clean disposable clone of the branch at `3b8cdeb1`, not a worktree with learned state to preserve. One legacy test path increments a tracked concept use counter in its copy. No generated state was carried into the deliverable. Use the installed Chromium/`offline` function above, Python 3.11.2, pytest 9.2.0, tree-sitter 0.20.4, tree-sitter-languages 1.10.2 and z3-solver 4.15.4.0. Without `BRAIN_TEST_CHROME`, the live browser test **skips**.

```bash
files=(canonical/tests/test_{boundary_evidence,subtree_witness_replay,petri_cow_unified_architecture,petri_cow_splicing_engine,v4_subtree_fuzzer_harbor,causal_swe_repair,harbor_epistemic_agent,harbor_experimental_vm,harbor_cold_smoke,harbor_pro_git_capture,harbor_pro_patch_handoff,harbor_process_cleanup_worker,unified_epistemic_portfolio,zero_knowledge_cua_kernel,witnessed_native_route,witnessed_revision_history,contrast_and_browser_boundary,frontier_leapfrog_waves21_25,frontier_leapfrog_wave39,unified_frontier_spines,repair_input_dependency_gate,finite_minimax_decision_region,induced_edit_basis,arm_learned_from_its_own_verified_repairs,domain_atlas}_v1.py)
offline env BRAIN_TEST_CHROME="$EXE" python -m pytest -q "${files[@]}"
python3 execution_guard/repo_integrity_guard_v1.py --ci --base c5d59dd0cb20cf1d2b4c02136ccd7dd76423e7aa
```

**Locked-image handoff (not run here):** on an authorized Actions connection and Docker runner the prespecified smoke invocation is `gh workflow run frontier_smoke_eval.yml --ref arena/92aa8a9e-brain -f task_offset=4 -f task_limit=2`. Check the actual trial artifacts, frozen patch digests, fresh-image replay and emitted rewards. A green workflow by itself or an unaccepted dispatch is not a grade. This covers the selected Pro/TB smoke tasks, **not** OSWorld; the latter requires its own pinned release, authorized task/assets and provider.
