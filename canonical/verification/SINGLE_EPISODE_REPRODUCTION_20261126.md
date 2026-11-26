# Reproduce the episode, the refusals, and the calibrated zeroes

Start in a **disposable clone of this branch, with its commit history**. Commands below use a new directory for each output and never retune a producer. Tested on Linux with unprivileged user, network, mount and PID namespaces, `mount`, `chroot`, `setpriv`, `ip`, GNU tar, Git, `curl`, `gh` (repository read), `jq`, Python 3.11.2, and `uv` for installing the non-system interpreters' dependencies. There was no Docker daemon or guest OS evaluation. Network is for acquiring pinned public inputs/dependencies; the agent rooms do not have network. These are reproduction instructions, not independent verification or authority to run untrusted code on a workstation.

[Release pins, instruction digests and package locks](SINGLE_EPISODE_INPUTS_20261126.json) · [recorded repeat checks and failures](../Immediate_Results/single_episode_repeats_20261126_v1.json) · [all HARD-51 grade attempts](../Immediate_Results/hard51_positions7_8_source_controls_20261126_v1.json). Times are wall time, not commitments. Do not copy a teacher from some other public player.

```bash
W=$(mktemp -d); T=canonical/tools; I=canonical/Immediate_Results
# A working Python 3.12.12 and uv must be available on the build host.
PYTHON312=python3.12 UV=uv bash "$T/reproduce_frozen_episode_v1.sh" screen "$W/screen"
bash "$T/reproduce_frozen_episode_v1.sh" cues "$W/cues"
```

**Screens.** The first command fetches only `environment_files/` from the pinned archive, checks all 50 file contents with the existing tree digest and installs the locked 3.12 toolkit. It runs from a new external CWD with `OperationMode.OFFLINE`. `--previous` points to the [export of the first run's raw segment](../Immediate_Results/public_screen_one_episode_20261126_v1.json); it is a host-side input, not a file in the read-only worker mount. Do **not** omit `--previous` when reproducing the shortened result: omission starts a new acquisition. Primary acquisition/first trial was at `5e77d367`; the reflected comparison at `6f5a04d1`. The original raw teacher SHA-256 uses sorted, compact JSON of the `raw` object, not a hash of the pretty-printed file. The second trial used the original first-trial store's as-of value **only in the evaluator** to reconstruct counterfactual stores after the deletion arm. The policy uses the latest supported program, not that history.

The exported-teacher run should produce 130 rows, 25 fresh starts plus one next level in each of five arms, seed 0, one new worker/scorecard per room. Compare all recorded fields except `wall_seconds`. The two original and clean runs' normalized **entire row-list** digest was `5fc97a251f944625a732efe8520683c31b7fdfc0f68fa725fdeed58196e3ed29`. This checks reported counts, confirmation outcomes, fallback, support and scorecards; it does not assert that unlogged receiver byte streams were hashed. The clean run used a later front-door source file (the cue-origin default changed), so the staged manifests of original and clean runs are **not identical**; the outcome digest is. Preparation actions are on the game scorecard but outside the reported receiver budget. Compare `producer.advanced`, not `scorecard.levels_completed>0` after a warm prefix. For the exact/transposed arms, inspect the already frozen [109 first-run rows](../Immediate_Results/public_screen_transfer_20261126_v1.json).

**Cues.** The evaluator projects *only* cue and trigger texts, deduplicates cues, sorts each bank by its own hash, then starts a fresh read-only producer with the projected packet and separately staged code. Source names/hashes and the empty artifact are in each capture. It freezes all ordered IDs before opening the pair mapping for grading. The budget is five excerpts, shared character cap, no annotated entities, all records have equal time. Full captures: [original](../Immediate_Results/cue_retrieval_base_20261126_v1.json), [origin fix](../Immediate_Results/cue_retrieval_origin_20261126_v1.json), [tie fix](../Immediate_Results/cue_retrieval_ties_20261126_v1.json), [subsequent order-stability fix](../Immediate_Results/cue_retrieval_stable_20261126_v1.json). The priors and criteria weren't fitted to these pairs. Retain per-trigger rank, including `null` for every miss, not just examples of hits.

The first clean run found five changed RRF lists in the primary ties arm; a separate four-arm clean run found zero/one/three/zero changed lists in original/origin/ties/stable. All had the same categorical hit counts. The old float order is not safe to require bit-for-bit on another host. The script **prints** the changes, checks the frozen primary grades, and requires full ordered equality of the stable arm. It does not quietly adopt new predictions. This run does not issue response text or a judge call. The other released LoCoMo dialogue files have QA, evidence, summary/observation fields; they are **not** needed here and should not be mounted.

## HARD-51: two different commands, two different rooms

```bash
# Producer: locked source revision, fresh shallow Ansible bases and public instructions only.
bash "$T/reproduce_witnessed_source_captures_v1.sh" h51-next "$W/producers"
# Grader: opens the already-frozen branch captures, NOT a mutable producer workspace.
PYTHON39_PREFIX=/path/to/relocatable/cpython-3.9.25 UV=uv GRADER_JOBS=3 \
    bash "$T/reproduce_frozen_source_grades_v1.sh" h51-next "$W/grades"
for n in 7 8; do
    jq '{calibrated_reference_nop,rows:[.rows[]|{arm,exit,reward_file,bytes,required,error}]}' "$W/grades/pos-$n.json"
done
```

Python 3.11 `venv` must work with its interpreter inside the private root. `PYTHON39_PREFIX` means a **complete relocatable install prefix**, not just the host's virtualenv symlink. Its `bin/python3.9` must run after mounting the prefix read-only on `/venv`, with `_ssl`, `zlib`, `ctypes` and the usual stdlib. On a build host with the usual CPython build headers one route is to build [CPython v3.9.25](https://github.com/python/cpython/tree/v3.9.25) with `./configure --prefix=/venv --without-ensurepip`, `make -j2`, `make install DESTDIR="$W/py39-install"`; use `PYTHON39_PREFIX="$W/py39-install/venv"`. This session built from that tag and supplied build headers separately. Public PyPI dependency versions are in the lock; no package installation during grading. Do not put a dummy interpreter or a shell that modifies results at the CLI path. The only position-7 console-script adaptation is changing the real pip-installed pytest entrypoint's first line to `#!/venv/bin/python`. The 3.9 grader uses the actual interpreter requested by the released position-8 run script.

Sanity checks: source tree commit and clean status, patch byte length and hash, released verifier file digests, verifier exit, emitted reward, and required case identities mapped to pass/fail/missing. For calibration all required no-op PTP must pass, at least one named FTP must fail and none may be missing/error; all required reference identities must pass. Empty PTP is legal if declared; empty FTP is not. Every arm gets a new writable checkout, log, PID/net/mount namespace; the released verifier and venv are read-only. Neither source-room reward is an official image reward. Position 7 performs 10,638 per-path resets; leave adequate time. `GRADER_JOBS=1` uses less parallel compute. Recorded final 7 used 3 concurrent rooms, final 8 and its repeat used 1. Control fields, not exact seconds, are the comparison. The build helper uses these validated task-specific budgets; the initial 220 s/no-3.9 and misplaced-console-entry runs are deliberately retained as **failed measurements**, not target grades.

## Source and branch checks

```bash
bash "$T/reproduce_nominated_head_controls_v1.sh" "$W/nominated-heads"
jq '.inventory|{listed,distinct_labels,distinct_modules,duplicates}' "$W/nominated-heads/wave.json"
jq '.interrogation|{observed,survivors,heldout}' "$W/nominated-heads/site.json"
```

The #7144 and #6933 probes run on **separate, immutable upstream revisions**. The adapter for #6933 additionally stages just the branch's finite decision-region module; the receipt lists the source hashes. Neither script merges those heads or mounts the study's task grades in a working solver. To repeat the static census, export the three `snapshots[].commit` revisions in [the census](../Immediate_Results/producer_source_census_20261126_v1.json); for a nonlocal revision use codeload, extracting only the three named source subdirectories. For example:

```bash
mapfile -t nominees < <(jq -r '.nominees[]' "$I/producer_source_census_20261126_v1.json")
for label in branch main 7144; do
    pin=$(jq -r --arg l "$label" '.snapshots[]|select(.label==$l).commit' "$I/producer_source_census_20261126_v1.json")
    mkdir "$W/$label"
    if [[ $label = branch ]]; then
        git archive "$pin" canonical/{runtime,swe_kernel,tools} | tar -x -C "$W/$label"
    else
        curl -fsSL "https://codeload.github.com/moxnixmdj/brain/tar.gz/$pin" | tar -xz --strip-components=1 -C "$W/$label" "brain-$pin/canonical/"{runtime,swe_kernel,tools}
    fi
    python3 -B -m canonical.tools.producer_source_census_v1 "$W/$label" "${nominees[@]}" > "$W/census-$label.json"
done
```

## Regression and integrity

Use a disposable clean checkout. For Python/Chromium dependencies (including the shared libraries and the `offline` function that starts a network namespace with loopback only), see [the preceding reproduction guide](WITNESSED_ROUTES_REPRODUCTION_20261126.md#runtime-regression-suite). No pip, git object substitution, fabricated browser or historical file redirection in tests. `check_single_episode_routes_v1.sh` lists the exact overlapping regression groups **once**.

```bash
offline env BRAIN_TEST_CHROME="$EXE" PYTHON="$(command -v python)" bash "$T/check_single_episode_routes_v1.sh" --junitxml="$W/results.xml"
python3 execution_guard/repo_integrity_guard_v1.py --ci --base c5d59dd0cb20cf1d2b4c02136ccd7dd76423e7aa
```

At `a3104279` the checkout ran 355 tests and 18 additional subtests; JUnit reports 373, not 373 distinct top-level tests. Two deprecation warnings, no skips. Earlier: 147 passed / 9 failed / 1 deselected in the first selected mechanism run, 161 passed in the later selection, and two direct census/calibration tests. These counts **overlap**. A legacy test changed a tracked concept-use counter in the throwaway clone; it wasn't used to seed or patch any run. A structurally clean repo, passing tests and a pinned evaluator are useful controls, not a capability or terminal verdict.
