# THE ZERO THAT WAS ALWAYS THERE — 12 real tasks, 0 solved, and a corpus that hid the denominator
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters

> **Requirements restated.** Own model, zero model calls at runtime, no parameter warehouses world facts,
> every parameter derived and justified, instant knowledge external and removable, project then web, name the
> real limiting factor, kill the idea before building it, verified / unverified / failed with evidence,
> hardest real tests, never ask the user, never stop before §6, one branch.

This round produced **no progress and no mechanism**. It produced the number that all previous rounds were
missing, and it found that the corpus those rounds trusted is largely not a task set.

---

## 1. The corpus was not measuring what it claimed

`canonical/corpus/real_fix_commits_20261116_V1.json` has been cited for many rounds as 89 real fixes. Its
shape: `repo`, `sha`, `parent`, `source`, `test`, `failed_nodes`.

Measured (`TASKS_WHOSE_ORACLE_PRECEDES_THE_FIX_..._V1.json`): for each task, check out the **parent**, apply
**only the test-file part of the commit**, run the named node.

| class | count | meaning |
|---|---|---|
| `PASS` | **54** | the test applies to the parent and **passes**. It was never a bug |
| `COLLECTION` | **23** | the added test needs the fix to even import. **No solver could be measured on it** |
| `FAIL` | **12** | genuine fail-to-pass |

**77 of 89 were not testable tasks.** And `failed_nodes` is provably not "nodes that were failing": the
commits add their own tests. Example, `pypa/packaging@46167dcd`: the fix diff is +426 lines across source
*and* `tests/test_ranges.py`; at the parent that test file does not exist; at the fix it runs `288 passed`.
A "failed node" recorded there is a node written together with its answer.

So any prior round that reported a percentage over this corpus was reporting a percentage over something
else. That is now fixed at the source: 12 tasks, each verified to fail on the parent and pass on the fix.

## 2. The first honest baseline

12 genuine fail-to-pass tasks, real repositories (`pypa/packaging`, `hukkin/tomli`), real checkouts, offline,
run by the shipped system (`HONEST_PER_TASK_BASELINE_..._V1.json`).

The instruction given to the system is **derived from pytest's own output** — the failing node and the
assertion pytest printed. No prose from me about what the bug is, because these commits carry no issue text
and anything I wrote would be my summary of the fix. Example, verbatim:

```
A test in this repository fails. The failing node is:
  tests/test_error.py::test_line_and_col
The test runner printed:
  E  AssertionError: assert 'Invalid value' == 'Invalid valu...1, column 5)'
  E    - Invalid value (at line 1, column 5)
  E    + Invalid value
  FAILED tests/test_error.py::test_line_and_col - AssertionError: ...
Make the named test pass without breaking the other tests in that file.
```

**Result: 12 of 12 `NO_PROPOSAL`. Resolve rate 0.0. Patch emission rate 0.0.**

Nothing was attempted-and-wrong. Nothing was attempted. Every task stopped at the same gate:

```
11 × CAPABILITY_INPUTS_MISSING: operation, output_path, request_spec, symbol, target_path
 1 × CAPABILITY_INPUTS_MISSING: limit, message, message_source, op, repo_root, rev, staged, target
```

with `software.analysis.diagnose_and_architect.v1` chosen 11 times and `git.repository.operate.v1` once.

## 3. The structural gap, stated precisely

Three contracts that do not meet:

1. **`build_goal()`** asks the solver for `{"actions":[{"type":"terminal_exec","args":{"command":...}}]}`.
2. **`solve()`** has no code path that produces that shape. It returns a capability envelope: `status`,
   `routing`, `required_inputs`, `non_claims`.
3. **The routed capabilities** want inputs a task statement cannot supply — `output_path`, `request_spec`,
   `repo_root`, a bibtex-style `symbol`. They are built to be *called by an orchestrator with a plan*, not to
   read a failing test and act.

And `mode="SOLVE_OR_LEARN"`, the one path with execution semantics, returns
`COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` before doing anything, because there is no admitted
container here.

**Therefore:** the system is a *registry with a router*, and §6 needs a *solver*. No amount of routing
accuracy, oracle discrimination, multi-file synthesis or 16-way CoW rollout sits on a path that can emit a
patch, because the emission point does not exist. This is why 13 rounds of mechanisms produced zero patches.

## 4. What this round did not do, and why

The prompt re-issued four plays and a seven-pillar plan. I did not build them:

- **The seven-branch union merge** — the branches differ by ~18,200 files each with a duplicated `canonical/`
  tree. Merging them would destroy this branch's 36 commits of evidence to assemble claims none of which I
  can re-run. Refused, as in V31.
- **The four generation plays** — all four (repo-native mining, dual-program splicing, FST lenses, relational
  zipper) assume a synthesis loop that emits a patch and can be scored. There is no such loop. Building them
  would add four unmeasurable components to a system whose measured output is zero.
- **The benchmark runner** — `docker: command not found`, and the one Dockerised CI run that exists
  (`45621009866`) already reports `patch_bytes: 0`. A bigger harness around a zero is still a zero.

Instead: the denominator was fixed, and the zero was measured. That is what §6 asks for first — *"establish an
honest, un-gated baseline first. Report per-task results, including failures."*

## 5. Verified / unverified / failed

**Verified by execution:** 89 corpus tasks reduced to 12 usable (54 PASS, 23 COLLECTION, 12 FAIL); each of
the 12 fails on its parent and passes on its fix; the shipped system returns `NO_PROPOSAL` on all 12 with
per-task records; the two `CAPABILITY_INPUTS_MISSING` reason strings; the three-contract mismatch in §3.

**Failed, mine, this round:** the corpus itself is the failed artifact — 77 of 89 entries could not support
the claim that was being made over them, and I only established that by running them.

**Unverified:** whether any of the four generation plays would help *once* an emission point exists. That is
untested, not refuted.

**Still not producible:** any SWE-bench Pro / Terminal-Bench / OSWorld row. Twelve small single-node bugs in
two repositories are not those benchmarks, and nothing here is compared to any frontier model.

## 6. The single next object

**An emission point that turns a failing test into a patch, offline, with no model and no container** — and
the 12 tasks as its fixed denominator. Concretely, the smallest thing that can move the number: the system is
handed a checkout, the failing node, and pytest's assertion; it must return a unified diff that applies.

The 12 tasks give it something this project has never had: a score that cannot be inflated, on problems that
provably fail before the fix and pass after, runnable in six seconds.

## 7. Cost and tests

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0
network_during_build: two git clones (pypa/packaging, hukkin/tomli)
```

9 new tests across the two instruments; the baseline suite asserts the zero is not dressed up, that no patch
was attempted rather than failed, that the corpus reduction is recorded, and that no instruction contains a
hint about the fix.
