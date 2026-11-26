# Wave 46 — The Oracle Was Unfalsifiable

**Date:** 2026-11-26 · **Branch:** `arena/fe676c2a-brain` · **Base:** `ac5c1015`

Verification of the 32 "titan" modules claimed by the leapfrog plan (all 32
exist; LOC matches the plan exactly) led to testing the flagship rather than
reading it — `canonical/runtime/futamura_leapfrog_kernel_v1.py`, 3,357 lines, the
`K3 = 0` Futamura kernel that the whole leapfrog thesis rests on. It was broken
in a way that made every result it had ever produced meaningless.

This document records only what was reproduced and measured. No benchmark score
is claimed anywhere in it. §6 is **not** satisfied.

---

## 1. The defect that invalidated the flagship: an oracle that cannot say no

`_eval_candidate_in_process` ran each test case as:

```python
exec(compile(tc, "<futamura_test>", "exec"), ns, ns)
```

A bare expression is **evaluated and then discarded** in `exec` mode. So
`multiply(3, 4) == 12` compiled, evaluated to `False`, and was thrown away.
Nothing raised, therefore the candidate "passed".

Reproduced live before the fix:

```
task:     def multiply(p, q):\n    return p / q
test:     multiply(3, 4) == 12
result:   pass: True   status: SOLVED_AT_RUNG2   patched_source: "return p / q"
reality:  multiply(3, 4) == 0.75, the test demands 12
```

The kernel reported a *verified* solve for source it never tested. Three
separate evaluators shared the defect — `_eval_candidate_in_process`,
`_eval_candidate_in_cow_fork` (which delegates to it), and the line-tracing
runner used by Ochiai localisation. Every Rung 1/2/3 outcome, every compiled
Rung-0 rule, every "verified" receipt descended from it, so the whole cascade
inherited the falsehood.

**Fix.** One shared runner, `_exec_test_case`, that evaluates the case in `eval`
mode and fails on a falsey result, falling back to `exec` only for genuinely
statement-shaped cases (`assert ...`). Both call sites now route through it.

**Evidence it is now falsifiable:**

| check | before | after |
|---|---|---|
| `p / q` under `== 12` | **True** | False |
| `p * q` under `== 12` | True | True |
| five wrong operators (`/ - + // %`) | all True | all False |
| impossible test (`f(1) == 999`) | **True** | False (abstains) |
| `assert`-style case | True | True |

The cascade now returns `ABSTAIN_FAIL_CLOSED__NO_VERIFIED_REPAIR` on the
impossible test instead of inventing a pass.

## 2. The admission gate forbade the repairs it exists to admit

`repair_admission_v1._literals` used `ast.walk`, which descends into a
`JoinedStr`'s children. The `elif isinstance(sub, ast.JoinedStr): continue`
branch only skipped *appending* the `JoinedStr` itself; the walk still yielded
its `Constant` pieces, which were then counted as test **data**.

So a correct formatting repair was refused as `TEST_LITERAL_LEAK`:

```
f'BAD:{name.lower()}'  ->  f'TAG::{name.upper()}'   refused: leaked 'TAG::'
f'score={x + 999}'     ->  f'SCORE[{x:03d}]'        refused: leaked 'SCORE[', ']', '03d'
```

A formatting repair's entire job is to introduce new string constants. The gate
forbade exactly that class, so `route_swe_inverted_microscope` screened **zero**
candidates (`proposals_screened: 0`) and failed closed on a coupled two-file
formatting fix that it had been handed a correct patch for.

**Fix.** Only *direct* `Constant` pieces of a `JoinedStr` are exempt as format
scaffolding. A constant inside a `FormattedValue` is an ordinary expression
literal and stays subject to the leak rule. The data-leak gate is intact:

| candidate | verdict |
|---|---|
| `return 5` | REFUSED `TEST_LITERAL_LEAK` |
| `return 5 if a == 2 else a + b` | REFUSED |
| `return {2: 5, 7: 10}.get(a, a + b)` | REFUSED |
| `f"{5 if a == 2 else a + b}"` (data inside f-string) | REFUSED |
| `return a + b` (operator fix) | admitted |
| `f'TAG::{n.upper()}'` (scaffolding) | admitted |
| `f'SCORE[{x:03d}]'` (numeric padding) | admitted |

`test_frontier_leapfrog_waves15_20_v1` went from 15/16 to **16/16**.

## 3. The model artefact was stale, and the LOC cap was breached

Two currentness defects, both now covered by tests:

- `brain_unified_model_v1.py` had grown to **7,571** lines against the 7,534 cap
  enforced by `test_asymmetric_frontier_leapfrog_v1`. Six private members were
  provably unreachable (zero references anywhere in the repo, including test
  suites) and were removed, plus redundant blank lines: **7,490** lines. This
  was deletion of dead weight, not compression of live code.
- The committed artefact `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`
  was compiled *before* this branch's own edits, so `open_model().digest`
  disagreed with a fresh `compile_model()`. A digest is a claim about a specific
  tree; this one referred to a tree that no longer existed.
  `test_six_moves_leapfrog_v1` was failing on exactly this. Regenerated;
  `compile_model()` and `delta_compile_model()` now agree byte-for-byte, and the
  served artefact matches both.

**Lesson recorded:** every source edit invalidates the artefact. Regeneration is
part of the edit, not a follow-up.

## 4. What the repaired kernel actually does

With a falsifiable oracle, the Futamura payoff could finally be measured. One
taught experience, then held-out tasks never seen:

```
teach:    def add(a, b): return a - b      test: add(2, 3) == 5
          -> SOLVED_AT_RUNG2_AND_COMPILED_TO_RUNG0, 1 rule learned

held-out                                  rung   verified   time
  def plus(x, y):  return x - y            R0     yes        0.31 ms
  def add(p, q):   return p - q            R0     yes        0.22 ms
  def concat(s, t): return s - t           R0     yes        0.51 ms
  def total(a, b, c): return a - b - c     R0     yes        1.02 ms
```

**4/4 at Rung 0 — zero synthesis, sub-millisecond**, after a single experience.
The `str` case matters: the same law transferred to a different operand type.

Getting the fourth case required three real fixes, each found by a
counter-example rather than by reading:

1. **Rung 0 was not a fixpoint.** It applied one rewrite and gave up. `a - b - c`
   needs the law twice (`a + b - c`, then `a + b + c`).
2. **Verifying every intermediate state made chaining impossible.** A
   partially-applied law is *supposed* to still fail. Correct algorithm: a
   bounded breadth-first search over rewrite *sequences*, verified only at the
   end of each sequence (`RUNG0_MAX_REWRITES = 6`, `RUNG0_MAX_STATES = 48`).
3. **The rule could not be found, nor the slot bound.** `_preorder_signature` is
   exact, so `Name - Name` never matched a `BinOp` operand; and the `__V` slot
   refused to bind anything but a bare `ast.Name`. Fixed with a coarse
   `(kind, operator)` bucket index for *lookup* and a widened binding *domain* —
   `_match_template` still decides what matches, and the suite oracle still
   verifies the final state, so both changes can only add reachable candidates,
   never accept an unverified one.

The widened binding domain was checked for poisoning: after learning, the
kernel still abstains on `f(1) == 999` and on `add(2, 3) == 99`.

## 5. Regression status

Every suite below is green on this branch. Base-vs-branch comparison was run in
a separate worktree at `ac5c1015`; the suites that still fail do so identically
at base, so nothing here is a regression introduced by this work.

| suite | result |
|---|---|
| `test_wave46_falsifiable_oracle_and_admission_v1` | **21/21 OK** (new) |
| `test_six_moves_leapfrog_v1` | 6/6 OK (was 1F) |
| `test_frontier_leapfrog_waves15_20_v1` | 16/16 OK (was 1F) |
| `test_frontier_leapfrog_waves21_24_v1` | 9/9 OK (was 1F) |
| `test_asymmetric_frontier_leapfrog_v1` | 8/8 OK (was 1F) |
| `test_frontier_leapfrog_wave2_k3_zero_v1` | 5/5 OK |
| `test_frontier_leapfrog_wave37/38/39` | OK |
| `test_frontier_leapfrog_waves21_25_v1` | 10/10 OK |
| `test_unfamiliar_six_moves_leapfrog_v1` | 7/7 OK |
| `test_canonical_swe_spine_v1` | 8/8 OK |
| `test_wave45_honest_oracle_and_skill_transfer_v1` | 16/16 OK |
| `test_curriculum_v1` | 19/28 — pre-existing (network / unadmitted `shell.command.run`) |
| `test_composer_route_v1` | 17/27 — pre-existing, identical at base |
| `test_a_proposer_is_not_a_repair_v1` | 4/7 — pre-existing, identical at base |

## 6. Honest limits — what this does *not* show

- **No benchmark number.** SWE-bench Pro V2, Terminal-Bench 4.0 and OSWorld 2.1
  remain unrun; `docker` is absent from this sandbox. The 1,026 failing cases in
  `HONEST_SUITE_BASELINE_20261103_V1.json` were **not** repaired here.
- **The transfer is operator-level, not comprehension.** Replaying
  `x - y -> x + y` on renamed functions is a compiled law doing its job. It is
  not evidence of understanding the code's purpose, and §9.5 requires calling
  that out rather than dressing it up.
- **The learned rules come from a proposer, not from the system.** Rung 2 finds
  the fix inside a fixed operator-alternative grammar
  (`_BINOP_REPAIR_ALTS`). On tasks outside that grammar the kernel still fails
  closed — correctly, but it fails.
- **Chaining is bounded.** Six rewrites, 48 states. Deeper compositions fall
  through to synthesis or abstain.
- **§6 remains unmet.** Hard-51: 0/51. Real-code repair: 0/1 verified.

## 7. Next bottleneck

The single limiting factor is now stated precisely: **the Rung-0 rule store is
in-memory and per-process.** `FutamuraSelfCompilingCascade.__init__` builds an
empty `_rung0_by_key`; `shared_futamura_cascade()` returns a process-wide
singleton. A law learned in one run is gone in the next, so "compile once, replay
forever" is true only within a single process — which is exactly the claim the
leapfrog thesis is built on. Persisting the rule store with provenance and
re-validation, then measuring replay on a *fresh interpreter*, is the next
honest step, and it is a prerequisite for any transfer measurement that means
anything.

---

# Wave 46b/46c — Compile Once, Replay Forever (and stop replaying bad laws)

## 8. The bottleneck I named was real

`§7` predicted that the law store was per-process, making "compile once, replay
forever" false outside one interpreter. Measured:

```
P1: taught `x - y -> x + y`  -> 1 rule, process exits
P2: fresh interpreter        -> 0 rules, re-spends Rung 2 synthesis
```

So the flagship's central claim held only within a session. Fixed by persisting
the law store to `canonical/astra_runtime/state/futamura_rung0_laws_v1.json`
(`BRAIN_FUTAMURA_STORE` overrides the path), written atomically on compile.

After: a fresh interpreter hydrates the law and solves a renamed task at **Rung
0** with zero synthesis.

Guards that make this honest rather than merely persistent:

| condition | behaviour |
|---|---|
| store absent | zero laws, no crash |
| store corrupt JSON | zero laws, no crash |
| template unparseable | that law dropped, others kept |
| plausible but **wrong** law | oracle still decides; it cannot produce a pass |
| human deletes a law | next process simply does not have it |

The last two rows matter: persistence supplies *hypotheses*, the oracle supplies
*truth*, and a human can remove knowledge from the store with no retraining —
which is the §2 removability test made executable.

## 9. Laws that keep failing now retire

`failures` was incremented on every replay miss and **nothing ever read it**. A
wrong law was re-armed in every future process, and every later task paid for its
failed screening. Retirement existed only inside `wake_sleep_consolidate`, which
a compile-once/replay-forever path never calls.

`_record_rule_outcome` now retires a law at ≥3 observations with a success rate
below 25%, removes it from both lookup indexes, and persists it **flagged** — not
dropped, because a law that silently vanishes is re-learned from the same
evidence next time. Hydration skips retired laws, so retirement survives the
process. A single failure is explicitly tested not to retire anything.

Measured: a seeded `x - y -> x * y` law failed 3 times, was quarantined, and a
fresh process carried the retirement over while the correct law learned
alongside it stayed active. The bad law never produced a pass.

## 10. The benchmark I wrote was inflated by half

First run of the transfer benchmark reported **8/8**. Checking each row's input
state showed **4 of the 8 already passed on their input** — including three
"held-out" tasks and one "teaching" task. Those rows could not fail, so they
measured nothing; the real figure was 4/4, not 8/8.

Rebuilt with a falsifying precondition. Every row asserts it starts red, and the
suite asserts that two known-green variants *are* green and excludes them:

```
taught 3 verified-failing experiences -> 3 laws

held-out task    base   rung  verified   time
renamed fn       False  0     yes        0.20 ms
new consts       False  0     yes        0.16 ms
compound 2-op    False  0     yes        0.50 ms
str operand      False  0     yes        0.16 ms
mul variant      False  0     yes        0.16 ms
nested sub       True   --    excluded (already green)
bool 3op         True   ---   excluded (already green)

GENUINE transfer: 5/5 at Rung 0, zero synthesis, 1.2 ms total
```

Two honest observations that keep this in proportion:

- `str operand` (`s - t` -> `s + t` for strings) is one line, not a hard
  problem. It shows the law is operand-agnostic, nothing more.
- The `adult(a)` / `threshold` pair taught nothing because the input already
  passed, yet Rung 2 appended `COMPILED_TO_RUNG0` without a rule appearing
  (`laws 2->2`). That receipt is inconsistent with the rule count and is **not
  explained** here; it is recorded as an open defect rather than assumed benign.

## 11. Status after this wave

`test_wave46_falsifiable_oracle_and_admission_v1` — **33/33**. Seven-suite sweep
green, run twice non-consecutively to rule out order dependence. All changes
pushed: `b33c71cb`, `b8ab774f`, `f85718f4`.

**Still not claimed:** no SWE-bench Pro V2 / Terminal-Bench 4.0 / OSWorld 2.1
number (`docker` absent). The 1,026 baseline failures were not repaired. Hard-51:
0/51. §6 unmet.

**Next bottleneck, stated before testing it:** the written store is
operator-level only — `_BINOP_REPAIR_ALTS`, `_CMP_REPAIR_ALTS`,
`_BOOLOP_REPAIR_ALTS` define a fixed grammar of alternative operators. Transfer
is therefore bounded by that grammar, and "5/5" says the *compilation* machinery
works, not that the system can repair an arbitrary real bug. The next honest step
is measuring the fraction of the repo's 1,026 recorded failures whose fix is even
expressible in that grammar — if that fraction is small, no amount of persistence
or retirement matters, and the grammar is the real limiting factor.
