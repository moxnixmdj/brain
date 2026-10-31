# Reuse-first SWE: confined real-repository exercise

Date: 2026-10-30. Local development evidence, **not independent capability admission**.

## What changed

1. Reused `zero_ambient_namespace_launcher_v1.py`, rather than building another sandbox. Its existing private user/mount/network/PID/IPC/UTS namespaces, read-only input and system mounts, capability drop, no-new-privileges, private scratch, broker quota, resource limits and process-group timeout remain in use.
2. Replaced the launcher's dependency on an external `chroot` executable with the `os.chroot` syscall approach already present in `confine_v1.py`. The trusted setup resets cwd to `/` before exec and still drops capabilities through `setpriv` before workload code runs. This host has no `chroot` executable; the five existing launcher tests now actually execute and pass here.
3. Added explicit, boolean `expose_null_device` policy. Default remains false: `/dev` stays hidden. Opt-in exposes only the actual null character device (major/minor 1:3), bound read-only inside a private `/dev`. This supports genuine pytest FD capture and Git without exposing other host devices. The option is included in the canonical policy digest. Nonboolean values refuse.
4. Added `confined_crossfile_qualification_v1.py`: an explicit opt-in Python/CLI entry that runs the **existing normal-entry `solve()` workflow**, including baseline tests, staging, impact-selected tests, full regression, exact emitted-patch reconstruction and separate full replay, inside one existing namespace membrane.
5. The real repository exposed a genuine `MULTILINE_IMPORT_SPAN` refusal in the existing issue-to-PR apply kernel. Fixed rename application by reusing AST alias token positions and the existing splicer. Parenthesized/backslash imports now preserve comments, other import names and formatting. A single reverse-position pass also handles imports and references sharing a line. Token splicing now respects AST UTF-8 byte offsets. Aliased imports remain explicitly unsupported/refused rather than guessed.

No registry entries, protected governance files, existing test assertions, capability ledgers, promotion counters or terminal truth were changed.

## Actual input and outcome

Public source: https://github.com/mahmoud/boltons

Pinned revision: `d31d821d56c8f7756af9c30a864077f2e5855321`.

The pinned GitHub tarball was extracted with LICENSE retained. The redundant downloaded archive was removed after extraction. The external source tree now lives outside the Brain repository at `/home/user/brain-practice/boltons-d31d821d56c8f7756af9c30a864077f2e5855321/`; its source bytes were not modified. This is a public development task selected during this session, **not a held-out benchmark**.

Input issue:

```json
{
  "issue_id": "BOLTONS-PINNED-RENAME-1",
  "title": "Rename pairwise_iter to adjacent_pair_iter in boltons/iterutils.py"
}
```

| Check | Actual result |
|---|---|
| Original repository baseline | 621 passed; pytest additionally reports 22 subtests passed |
| Impact-selected candidate tests | 58 passed, 0 failed |
| Full candidate regression | 621 passed; 22 subtests passed |
| Separately reconstructed emitted patch | 2 files, exact requested transformation checked |
| Separate full replay | 621 completed, 0 failed |
| Original source unchanged | true |
| Read-only input snapshot unchanged | true |
| Normal-entry semantic and cross-file acceptance | true |
| Source promotion / independent semantic-oracle credit / terminal credit | false / false / 0 |

Source exact-tree SHA-256:
`770fd5e6c8397723500f4bee9d66f15fc2cde4ac29a9c852b085bf227685c6f5`.

Candidate content SHA-256:
`b11dc1a515bedfd3a295f287ad2480ab9b7b00b9c28a132170a6ed3a207fff10`.

Successful development run: **19,371.758 ms**. Subsequent successful CLI runs: **18,927.420 ms** and **18,791.042 ms** (final, using the external fixture location). These include input copying/hashing, namespace bootstrap, a real offline venv, baseline, existing solve workflow, regression, replay and cleanup. They are three observations, **not a speedup study or general latency claim**.

Final complete local artifact (ignored practice storage, not a receipt):
`canonical/astra_runtime/state/real_env/boltons-20261030/qualification-external-final.json`.

It contains the real normal-entry trace, baseline, producer report, patch ledger, separate replay counts, input hashes and namespace execution status. The original source remains at the external practice path listed above.

## Explicit execution entry

Use the already-prepared `.venv`; no packages are installed by the runner or tests:

```sh
.venv/bin/python -m canonical.runtime.confined_crossfile_qualification_v1 \
  --source-root /home/user/brain-practice/boltons-d31d821d56c8f7756af9c30a864077f2e5855321 \
  --issue-path canonical/astra_runtime/state/real_env/boltons-20261030/issue.json \
  --output-path canonical/astra_runtime/state/real_env/boltons-20261030/another-fresh-result.json
```

`--task-path` is the alternative for an explicit edits task. Output must be fresh and within the Brain checkout. A root carrier must supply an explicit nonroot `--host-uid` and `--host-gid`; namespace policy enforces the identity rules. Direct Python callers use `qualify(source_root, payload, input_kind="issue")`.

The runner snapshots current canonical runtime/governance/law/evidence data, excluding tests and transient Astra state, plus the explicitly supplied project and this venv's dependencies. Symlinks in the resulting snapshot refuse; Git metadata, caller home and packaging tools are not mounted. A genuine no-pip venv projects the declared dependency snapshot to real subprocesses. Ambient pytest plugin autoload is disabled. The complete baseline and existing solve path execute on private copies. No unconfined fallback exists.

## Validation against the actual working tree

New focused tests:

- `test_crossfile_multiline_imports_v1.py`: 12 cases.
- `test_namespace_launcher_portability_v1.py`: 6 cases.
- `test_confined_crossfile_qualification_v1.py`: 8 cases.

Together: **26 passed in 17.23 seconds**. They include actual normal-entry issue/task execution, host canary invisibility, read-only input enforcement, genuine test-failure refusal, source preservation, syscall-root cwd reset, explicit device authority, real timeout and a forked new-session descendant being removed. No mocked launchers or tools.

Existing issue-to-PR plus task-bound cross-file tests: **51 passed in 13.88 seconds**.

Final expanded 26-file regression selection: **437 passed, 13 failed, 4 warnings, 2 subtests passed in 153.34 seconds**, exit 1. Log: `/tmp/brain-confined-crossfile-final.txt`. This is not a full-suite run. The existing ten route/parity/consult/naming failures remain, as do three exact registry-token expectation mismatches (symbol index, choreography and additionally exercised impact test selection). The impact-selector test and registry bytes are unchanged; no assertion was weakened.

An earlier expanded run reported 406 passed / 35 failed / 9 skipped: leaving the downloaded `source.tar.gz` inside the repo caused a pre-existing global archive-discovery path to choose it for an unspecified archive request, cascading through generic archive-trace tests. Removing that redundant download restored their real execution. The focused raw-trace + consult check then produced 35 passed / 2 known consult failures / 2 subtests; the final expanded selection above was run afterward. No archive-selection code or test harness was changed. Ambient archive discovery remains fragile and is not claimed fixed.

The first completed integrity check found three violations in the downloaded upstream fixture (its collection hook and two swallowed assertions). Rather than edit upstream tests or change Brain’s guard, moved the external source tree outside Brain. The final CLI exercise then reran successfully against that external path. No third-party test harness is added to Brain. Final integrity check against base `c79a8f544fe47b1d7250b1c64889b958237db4f3`: **17 rules, 0 violations, PASS**; log `/tmp/brain-confined-integrity-final.txt`. `git diff --check` is clean.

## Boundaries

- **Ordinary `solve()` is not automatically confined.** Call the explicit confined entry to get this execution membrane. Its launcher still respects any installed global subprocess mediator; this is not an authorization bypass.
- Execution containment is not semantic trust. The broker carries untrusted workload output; hostile tests can lie about outcomes. Runtime copies inside private `/work` are writable. This is not an adversarially independent verifier or runtime attestation service.
- Resource limits are the existing per-process rlimits and private tmpfs caps, **not aggregate cgroup memory/CPU accounting**. Wallclock bounds cover namespace execution, not initial snapshot preparation. No seccomp or kernel-escape protection is claimed.
- This runner requires compatible Linux primitives and Python dependencies. Missing primitives/dependencies, output overflow and timeouts do not silently fall back to native execution.
- Only the existing explicit Python rename/move workflow is exercised. General synthesis, unknown requirements, arbitrary alias resolution, multiline **move** import rewriting, docstring/example renaming, full-stack work, large-repo scaling and general optimality are not established by this result.
- No independent verifier, held-out task population, capability promotion, full-suite success, CI success, commit, push or merge is claimed.


## Subsequent measured-repair extension

`SWE_GUIDED_REPAIR_REUSE_20261030.md` records the later reuse of the provenance-guided/coupled engine, parse-once optimization, preserved fresh verification, and new `qualify_repair()` / `--repair-task-path` mode. That mode uses the measured-controller API (not general natural-language synthesis) and adds mandatory full-pytest patch replay. The earlier rename/move evidence above remains a separate exercise.
