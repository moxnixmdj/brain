# All the problems — the definitive inventory

**Branch `arena/4ca3a720-brain`, 2026-10-28.** Every number is measured on this branch. Instruments
are in the repository and re-runnable; commands at the bottom.

Nine families. Two of them were silent — they redefined other numbers rather than announcing
themselves — and both are fixed in this PR. The rest are ordered by what they cost the machine's
ability to *be* a software engineer.

| # | family | measured size | cost | status |
|---|---|---|---|---|
| 1 | **The toolchain isn't in the repository** | clean image **14/22**, with it **22/22** | 8 capabilities vanish; an *absent* capability reports as a *broken* one | **fixed** |
| 2 | **A capability can kill its caller** | **16 of 16** exiting adapters killed the process | no verdict, no culprit, no retry — one bad request ends the agent | **fixed** |
| 3 | **The door lies** | **18 of 43** absent-act requests get a credible artifact + PASS | the caller builds on work that never happened | measured, mechanism named, fix ordered |
| 4 | **38 missing verbs** | 38 acts, 13 areas | the actual frontier of "most advanced engineer" | inventoried |
| 5 | **The registry is inflated** | 313 of 419 entries unroutable | 4× overstatement of capability | quantified |
| 6 | **False keywords** | ≥ 1 measured (`blame`) | turns a missing act into a wrong answer | fix = declaration |
| 7 | **Refusals name nothing** | **0 of 23** refusals name the missing act | caller can't tell "build this" from "this is broken" | measured |
| 8 | **Capability is concentrated where the leverage isn't** | see map below: git ops **2**, refactoring **4**, patch synthesis **2** | the machine is deep at auditing/repairing and thin at *moving* software | map measured |
| 9 | **The measuring instruments rot** | typed sweep crashed on its first capability; a probe reported 16/16 dead as 16/16 fine | a broken instrument reports *zero problems*, which is worse than a red one | 2 fixed, rest re-runnable |

---

## 1. The toolchain isn't in the repository (fixed)

A verified capability is an **adapter plus the tool the adapter calls**. Only the first half was
declared: `source.module` is prose (`"mypy"` in one entry, `"python stdlib ast/pytest + git"` in
another) and `declared_dependency_executables` is **empty for all 419** verified entries.

Same commit, same code, same 22-task probe:

| interpreter | bind | select | pass |
|---|---|---|---|
| clean `python3` | 22/22 | 19/22 | **14/22** |
| with the declared toolchain | 22/22 | **22/22** | **22/22** |

Attributed **by measurement** (block the module with an import hook, re-run the probe), never by
reading source. Highest blast radius is `pytest` — not a linter but the **oracle**: without it the
full test gate, the coverage gate and both refactors that re-run the suite are gone, so "repaired"
is unmeasurable.

Fixed by `canonical/runtime/TOOLCHAIN_DECLARATION_V1.json` + `execution_guard/toolchain_preflight_v1.py`
(`--check` / `--bootstrap` / `--attribute`), strict on version because drift is exactly what turned
22/22 into 14/22 with nobody editing a line.

---

## 2. A capability can kill its caller (fixed)

19 bound adapters report failure by ending the interpreter:

```python
raise SystemExit(json.dumps({"error": True, "capability": ..., "reason": "ISSUE_SCHEMA_MISSING:issue_id"}))
```

`SystemExit` is a `BaseException`, so the `except Exception` in `_execute_locally` never saw it.
`execution_guard/adapter_failure_law_probe_v1.py` runs each such capability with the least-informed
request a caller can make (`{}`), **one subprocess per capability** — the thing under test is
process death, so it cannot be observed from inside the process that would die:

| | verdict |
|---|---|
| before the guard | **16 of 16 PROCESS_KILLED** — no verdict, no caller, no diagnosis |
| after the guard | **16 of 16 TYPED_REFUSAL** — the adapter's own reason, delivered |

The exit payload was always the right diagnosis; it just had no way to be heard. The guard converts
`SystemExit` into the same closed failure every other refusal uses, so the caller learns
`ISSUE_SCHEMA_MISSING:issue_id` instead of learning nothing because it is gone.

---

## 3. The door lies — 18 of 43

`execution_guard/hardcore_se_missing_verb_probe_v1.py`: 43 ordinary-English sentences, one per
absent act, through the live door against a real two-commit repository.

| verdict | count |
|---|---|
| **SILENTLY_WRONG** — ran, wrote a credible artifact, door said PASS | **18** |
| HONEST_REFUSAL | 23 |
| WRONG_TOOL — ran, wrong capability, failed | 2 |
| answered by a capability that does not own the act | **36 / 43** |

**Mechanism:** `F3_ARTIFACT_WRITERS_PREFERRED` prefers whatever can write the promised file. When no
capability performs the act, a generic writer sharing one *medium* word (`python`, `source`) answers,
keeps the artifact promise, and the act never happens.

Three fixes were built and measured. The act-admission rule (the winner must itself name the
sentence's head verb) takes hollow passes **18 → 6** with reachability still 22/22, but takes the
goal-compiler suites from **17 failing / 149 passing** to **27 / 139** — rejected, not tuned. The
correct fix is a **declared act vocabulary per capability** (verb + object), checked at registration.

---

## 4. The 38 missing verbs

| area | missing |
|---|---|
| **version control** (11) | status, log, diff, commit, branch/checkout, revert, bisect, blame, stash, rebase, cherry-pick; merge-conflict resolution |
| **debugging** (2) | interactive debug; crash reproduction + minimisation |
| **measurement** (5) | coverage *of a tree*, memory/leak, cyclomatic complexity, duplication, dead code |
| **testing** (3) | fuzzing, differential testing, flakiness detection |
| **verification** (1) | invariant inference |
| **supply chain** (5) | add/upgrade dependency, vulnerability audit, secret scan, license, SBOM |
| **hygiene** (2) | lint and format **as acts** (only diff gates exist) |
| **build & release** (4) | build/package, schema migration, changelog, CI config |
| **runtime quality** (5) | async/concurrency, exception handling, SQL injection, path traversal, resource leak |
| **robustness** (2) | retry/idempotency, observability |
| **refactoring** (1) | move / split / inline (rename + extract are the whole surface) |
| **docs** (1) | docstrings / API docs |
| **architecture** (1) | API compatibility / semver |
| **packaging** (1) | container image |

---

## 5–7. Registry shape and its two honesty defects

- **313 of 419** verified entries declare **zero inputs** → they can never be selected from a
  request; **106 of 419 are routable**. The most ambitious names in the registry
  (`software.hardcore.swe.supercomposer.v1` and siblings) are among the unreachable.
- **False keywords** (≥ 1 measured): a keyword is a claim, and nothing validates it against the
  adapter. `blame` is declared by `python.source.change_impact.testselect.v1`, which does not blame.
- **Refusals name nothing** (0 of 23): the honest half of the machine is mute. The refusal object
  already carries a `detail`; it never names the act the brain lacks.

---

## 8. Capability is concentrated where the leverage isn't

Verified / routable capabilities by area:

| area | verified | routable |
|---|---|---|
| repair | 9 | **9** |
| static analysis (`source.audit`) | 12 | 6 |
| test synthesis | 9 | 7 |
| review / diff gates | 9 | 7 |
| contract checking | 8 | 1 |
| acceptance measurement | 8 | 2 |
| issue → PR | 7 | 2 |
| symbol index / resolve | 5 | 2 |
| fault localisation | 4 | 2 |
| **refactoring** | **4** | 3 |
| **patch synthesis** | 2 | 2 |
| **repo / git operations** | **2** | 2 |

The machine is deepest where a human reviewer would work (audit, repair, gate) and thinnest where a
human engineer spends their day (moving code: git, refactor, synthesize). That is the shape of the
gap to "most advanced software engineer" — not a lack of cleverness, a lack of *hands*.

---

## 9. The measuring instruments rot

Two were found dead in this unit alone, and both failed **silently**:

- `execution_guard/typed_capability_sweep_v1.py` imported a fixture from `live_solver_families_v6`
  after it moved to `…_v6_coupled`, so it raised `AttributeError` on the first python-source
  capability and **had not completed a run since the families were split**. A sweep that crashes is
  not a sweep that reports zero.
- `adapter_failure_law_probe_v1`'s first version caught `BaseException` in its child and read the
  adapter's own stdout JSON as its verdict, so it reported **16/16 fine** while 16/16 were dying.
  Fixed: the child catches `Exception` only, and its verdict carries a `PROBE_VERDICT` prefix.

Both are now guarded by tests (`canonical/tests/test_a_capability_may_not_kill_the_process_that_called_it_v1.py`,
`…test_the_toolchain_the_capabilities_call_is_declared_and_checked_v1.py`), including a test that the
probe *can* see a kill — an instrument whose failure mode is "reports nothing" must be tested against
the failure it is supposed to detect.

---

## What is *not* a problem

- **Reachability on the 22 hardcore-SE tasks: 22/22 bind, 22/22 select, 22/22 pass**, zero
  `shell.command.run` fallbacks, zero hollow passes — with the toolchain installed.
- **The 22 adapters themselves**: they execute against real repositories and are judged on the
  artifact they write.
- **Composition**: multi-step requests plan into a DAG and execute (verified to 10 steps).

---

## Order of work

1. **Keep the software present** — preflight before any capability claim. *(done)*
2. **Keep the caller alive** — no capability may end the process; every failure is a verdict. *(done)*
3. **Make the registry say what it performs and what it needs**, machine-checkably: an `acts`
   vocabulary (verb + object) and a resolved dependency block per entry. This closes families 3, 6
   and 7 by construction and makes both the hollow pass and the false keyword impossible.
4. **Version control (11 acts)** — the machine cannot inspect or move its own work; everything else
   in software engineering assumes that layer.
5. **Supply chain (5) + measurement (5)** — vulnerability audit, secret scan, license, SBOM, then
   coverage/memory/complexity/duplication/dead code.
6. **Refactoring beyond rename/extract** — move, inline, split, change signature.
7. **Fuzzing, differential testing, flakiness** — these buy *finding* defects, the only way quality
   improves without a human in the loop.
8. **A gate expectation model** — a reviewer that can only report PASS is not a reviewer.

---

## Reproduce every number

```bash
python3 execution_guard/toolchain_preflight_v1.py                        # 1: FAIL_CLOSED on a clean image
python3 execution_guard/toolchain_preflight_v1.py --bootstrap            #    then PASS 8/8
python3 execution_guard/adapter_failure_law_probe_v1.py --json /tmp/f.json  # 2: 16/16 typed (was 16/16 killed)
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py              # 3: 18 / 23 / 2
python3 execution_guard/hardcore_se_reachability_v1.py                    #    22/22 with the toolchain, 14/22 without
```

Tiers A–D: `HARDCORE_SE_PROBLEM_INVENTORY_20261028_V3.md`, `…_V4.md`, `…_V5.md`.
