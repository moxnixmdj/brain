# Reuse-first guided repair: faster search and confined measured execution

2026-10-30. Local development measurements, not independent capability admission.

## Reused mechanisms—not another repair engine

The existing `python_provenance_guided_coupled_repair_v1.py` already connects dynamic failing/passing localization, interprocedural value provenance, bounded AST mutations, two-edit coupled search, source restoration and fresh winner replays. `python_iterative_software_repair_loop_v1.py` separately implements strict-progress multi-round repair. Their 23 existing tests passed before this change (12.09 seconds). These mechanisms were not missing.

This change improves the shared path actually used by `python_repair_measured_acceptance_controller_v1.py` and adds an explicit confined exercise of that existing API.

## Implementation

1. **Parse once per candidate pool.** The coupled kernel previously reparsed and walked an entire source file for each proposed mutation. It now indexes the original AST once and reuses the exact source byte spans. Candidate priority, ordering, replacement bytes and limits are preserved. Replacers receive deep-copied subtrees so they cannot mutate the shared index. No execution result is cached.
2. **Remove the duplicate single-candidate sweep.** Guided search now takes the first passing single candidate during the original sweep instead of testing all singles and then executing them again. If no single passes, the existing pair search and per-single failure evidence remain available. Both fresh winner replays still execute. A replay failure refuses acceptance; no stale success is reused across requests.
3. **Rebase directory test targets correctly.** The measured controller previously rebased only file arguments. A pytest directory argument could keep pointing at the original broken tree during candidate measurement. Existing directories within the source root are now rebased as well. A real execution test distinguishes the broken original from its repaired candidate.
4. **Report pytest test counts.** Measurement previously recognized only unittest's `Ran N tests`. It now recognizes the final pytest summary without double-counting subtests or counting skipped cases as executed primary cases. Multiple unittest suite summaries are summed. Counts remain runner-output observations, not independent attestation.
5. **Reuse the existing namespace intake/bootstrap for measured repair.** Added `qualify_repair()` and `--repair-task-path` to `confined_crossfile_qualification_v1.py`. This mode executes the existing guided repair and measured acceptance controller, reconstructs emitted patches, and runs another whole-project pytest replay. It requires a genuinely failing, executed baseline; refuses test/trace-file patches; checks source and candidate drift; and requires measured/replayed primary test counts to agree. There is no unconfined fallback.
6. **Expose actual search evidence.** Successful measured reports now include search counters, localization-space summary, provenance hypothesis count, and the two real winner-replay results.

The rename/move mode still uses normal-entry `solve()`. The new synthesized-repair mode deliberately uses the **existing measured-controller API**, not an asserted general natural-language route. No capability registry, protected governance file, existing assertion, admission ledger or promotion counter was changed.

## Before/after measurements

Baseline measurements were executed against the then-current source before editing it. After measurements execute the updated source. The benchmark uses fresh temporary projects, real child test commands, identical search bounds and a counter written by the actual test command. It verifies source restoration and both fresh winner replays. No historical source is substituted into tests.

Three runs per case:

| Measurement | Before median | After median | Observation |
|---|---:|---:|---|
| Single-edit guided repair fixture | 821.143 ms | 726.482 ms | 11.53% lower; actual test-command executions 10 → 4 |
| Coupled two-file repair fixture | 1,147.616 ms | 1,030.576 ms | 10.20% lower; actual test-command executions 36 → 20 |
| Candidate pool on pinned Boltons `iterutils.py` | 3,946.950 ms | 74.587 ms | 98.11% lower **for this stage only** |

The before/after repair patches match exactly. The public-source pool's selected edits, ordering, byte offsets, descriptors and replacement bytes match exactly. Differential tests additionally cover strings, nested/async definitions, UTF-8, CRLF, boolean operations and conditions. A real profiler observation checks one source parse for a 100-function pool.

These are small local measurements, not a whole-agent speedup, population benchmark, or evidence of global optimality. Benchmark data/script are in external practice storage under `/home/user/brain-practice/` (`measure_guided.py`, `guided-before.json`, `guided-after.json`, `pool-before.json`, `pool-after.json`).

## Real-code seeded repair—not an upstream bug claim

Public source: https://github.com/mahmoud/boltons at pinned revision `d31d821d56c8f7756af9c30a864077f2e5855321`.

A separate external practice copy was created at `/home/user/brain-practice/boltons-seeded-pairwise`. The pristine source remained unchanged. One deliberate fault was seeded:

```diff
-    return windowed(src, 2, fill=end)
+    return windowed(src, 3, fill=end)
```

Two explicit trace scripts exercise failing and passing boundary behavior. They guide localization; the existing upstream pytest suite—not those scripts alone—is the candidate oracle. The input specifies only the test-pass objective and bounded search settings, not the desired patch.

Final confined CLI run:

- Baseline: **621 completed, 1 failed**.
- Guided frontier: **16 items in 1 file**, compared with 156 items across 12 files in its existing lexical control calculation. This is search-space accounting, not a measured 156-item control execution.
- Four single candidates executed; no pair search needed; one provenance hypothesis recorded.
- Both fresh winner replays passed.
- Measured candidate: **621 tests, return code 0**, Python parse measurement true.
- Separately reconstructed patch replay: **621 completed, 0 failed**.
- Repaired file SHA-256 exactly equals the pristine upstream implementation:
  `8f62bb690159f7d88eb3bbf38caa15df7d0495b4022ba175fc716629c1495241`.
- Seeded input source and read-only intake snapshot unchanged after execution.
- Final complete exercise: **44,139.878 ms**. The earlier development run took 41,481.374 ms; there is no before/after whole-repository repair speedup claim.
- Source promotion false; independent semantic-oracle credit false; terminal credit zero.

Final ignored local artifact:
`canonical/astra_runtime/state/real_env/boltons-20261030/seeded-repair-final.json`.

This is a controlled seeded fault in a known public repository, **not** an independently assigned, held-out task or discovery of an upstream defect.

## Invocation

```sh
.venv/bin/python -m canonical.runtime.confined_crossfile_qualification_v1 \
  --source-root /home/user/brain-practice/boltons-seeded-pairwise \
  --repair-task-path /home/user/brain-practice/boltons-repair-task.json \
  --output-path canonical/astra_runtime/state/real_env/boltons-20261030/another-fresh-repair.json
```

The task JSON supports only `task_text`, `test_paths` (relative Python trace suites), and optional bounded `search_limits`. Unsupported fields, unsafe paths, missing trace files, duplicate paths, noninteger/invalid limits and empty objectives refuse. Whole-project pytest is fixed by the runner; callers cannot substitute a no-op test command. A root carrier must explicitly supply a valid nonroot host UID/GID.

## Tests and limitations

New focused coverage: `test_repair_search_reuse_v1.py` (18 cases) and `test_confined_measured_repair_v1.py` (15 cases): **33 passed in 34.87 seconds**. Tests include real single/coupled synthesis in namespaces, source restoration, positive interprocedural provenance, directory-target realization, count handling, replay-sensitive failure, residual requirements, already-passing-baseline refusal and invalid input refusal. Existing test assertions were not weakened.

The existing kernel/controller selection also passed **35 tests in 16.59 seconds** during development. Final expanded 34-file selection: **522 passed, 13 failed, 4 warnings, 2 subtests passed in 196.37 seconds**, exit 1. Log: `/tmp/brain-guided-reuse-final.txt`. The failure identities are the same ten route/parity/consult/naming failures and three registry-expectation mismatches recorded in the previous expanded run. This is not a full-suite run.

Inherited boundaries remain: bounded Python mutation grammar, no general causal correctness proof, no adversarially trusted result broker, writable private runtime copies, opt-in rather than default confinement, per-process limits rather than aggregate cgroup accounting, and no source promotion. Summary-derived measurement counts are not tamper-proof; the new exercise also checks actual replay JUnit counts. No full-suite, CI, general intelligence, general synthesis completeness, or independent capability verification is claimed.

Final repository integrity guard against base `c79a8f544fe47b1d7250b1c64889b958237db4f3`: **17 rules, 0 violations, PASS**. Log: `/tmp/brain-guided-reuse-integrity.txt`. `git diff --check` is clean. No commit or push was performed.

## Follow-on integration (separate fresh measurements)

The opt-in iterative→guided measured-controller portfolio, its real confined
three-edit exercise, explicit scheduling overhead and current regression
limitations are documented in
[SWE_MEASURED_REPAIR_PORTFOLIO_20261030.md](SWE_MEASURED_REPAIR_PORTFOLIO_20261030.md).
The earlier measurements above are historical, not reruns in that cycle.
