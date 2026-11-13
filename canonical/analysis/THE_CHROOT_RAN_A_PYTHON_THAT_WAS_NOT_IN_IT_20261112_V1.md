# The chroot ran a python that was not in it

**Round date:** 2026-11-12 · **Base:** `aea3ff9e` · **Branch:** `arena/1263d862-brain`
**Question re-issued:** is one-try → permanent skill solved, and does that solve all computer use and
advanced software engineering? What is the current open limiting factor?

---

## 1. What this round actually did (in order)

1. Re-read the three freshest state documents (`A_FRESH_SET...`, `SWE_SELF_IMPROVEMENT_BRIDGE...`,
   `THE_LOOP_WAS_OPEN_AT_THE_LIVE_ENTRY...`) and probe-verified their state claims instead of
   trusting them (bundle = 11 skills, live db, transfer episodes = 1, verify bundle = 5 rules).
2. Drove the one-shot loop **end to end through the unified front door** (`solve_or_learn`,
   `learn=True`) on the *tracked* bundle — four executions, four passes (§2).
3. While pinning that path, found that **every confined execution dies when the harness runs
   under a venv** — a harness fault that surfaces as the taught program failing (§3). Fixed with
   the broker's own pattern; pinned both ends.
4. Adjudicated the "you were right" documents against the skeptical line with fresh evidence (§5).
5. Killed two candidate instruments by measurement before writing any code (§6).
6. Checked the 2026 literature for one-shot learning, computer-use SOTA, and verifier
   co-evolution; it converges with the tree (§7).

---

## 2. The one-shot loop ran, through the front door, on the tracked bundle

Everything below ran on this checkout, zero spend, no model calls. `solve_or_learn` is the
entry every recent round calls the live path; Tier0 is the `<5 ms compiled-workflow recall`.

| # | Route | Goal | Result | Latency |
|---|-------|------|--------|---------|
| 1 | `recall_and_execute_workflow` | `remember in …/total.lesson also the way …/ex_before.py was changed into …/ex_after.py` | **PASS** `PASS__COMPILED_WORKFLOW_SKILL_RECALLED_AND_VERIFIED`, skill `workflow.dec48cae82ef9ed5`, `STDOUT_EQUALS_VERIFIED` | 170.9 ms |
| 2 | `recall_and_execute_workflow` | `edit …/tgt2.py the way …/total.lesson remembers` | **PASS**, skill `workflow.84ef1a4bd0d0888e`, target changed `acc += x` → `acc += int(x)` | 149.6 ms |
| 3 | **front door** `solve_or_learn(learn=True)` | teach goal (fresh lesson) | **PASS** `PASS__TIER0_COMPILED_SKILL_RECALL`, `from_memory: true` | 204.6 ms (538.9 ms wall incl. import) |
| 4 | **front door** `solve_or_learn(learn=True)` | `edit …/tgt3.py the way …/conv.lesson remembers` | **PASS** `PASS__TIER0_COMPILED_SKILL_RECALL`, `str(x)` → `repr(x)` in a file created after the teaching | < 1 s |

Facts established by the same runs:

* **One showing becomes a durable, checkable artifact.** The lesson file
  (`CHANGE_LEARNED_FROM_EXAMPLES_V1`, one example) is written, re-read, and its `teaches`
  re-derived from its own examples on every use — a lesson that was hand-edited refuses by name.
* **Hits are recorded in the live store.** After the runs,
  `canonical/astra_runtime/tmp/compiled_workflows_v1.sqlite` reported `hit_count = 2` for both
  skills. **The tracked JSON bundle still says `0`** — the bundle is a content-addressed export,
  the sqlite is the live counter. A reader who trusts the bundle's `hit_count` (this round's
  first probe did) concludes "never used" and is wrong. Measurement trap, recorded.
* **Refusals are honest and named.** A coordinated rename example
  (`acc` → `total_` across three lines) is refused with
  `REFUSED: line 2 of the example changes which names are assigned (acc, total_); that works only
  together with other changes, as in a rename, and cannot be repeated one place at a time` — the
  engine declining a case it cannot decompose, not guessing.
* **`learn=False` skips Tier0 by design** (`recalled = None if (not learn or computer_shape)`),
  falls through, and fails closed on a weak lexical match (score 4, token `changed`) with
  `R13_DECLARED_INPUT_UNBINDABLE:source_root`. This contract is already pinned by
  `test_optimal_unified_creature_and_prc2_v1` — verified before deciding not to re-pin it.
* **Fresh checkouts can teach.** `_connect_db` auto-seeds the default database from the tracked
  bundle (missing skills only), verifying content-sha, `skill_id` derivation, and the ownership
  receipt on every imported row — already pinned by `test_the_tracked_bundle_imports_whole`
  and the `held()` test; re-read this round, not re-built.

**What was missing and is now pinned:** no test asserted the controller's own Tier0 status
`PASS__TIER0_COMPILED_SKILL_RECALL` (grep: only the controller itself names it), and no test
drove the shipped `remember`→`edit` pair *through `solve_or_learn`* — existing door tests use
the older `door.solve` branch (`PASS__COMPILED_WORKFLOW_SKILL`) with rename/inline skills, and
lesson-pair tests call `recall_and_execute_workflow` directly. New file:
`canonical/tests/test_the_front_door_teaches_and_applies_what_the_bundle_ships_v1.py`
(teach→apply on a never-seen file, with hit counts read back from the isolated db; plus the
rename refusal carrying its reason).

## 3. The defect: the chroot ran a python that was not in it

The new front-door test **failed on its first run**, and the failure was not the loop:

```
FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
tier_used: tier2_unconfined_documentation_execution_refused
```

Root cause, traced to the byte:

* `confine_v1.run()` launched its helper with **`sys.executable`**.
* The helper chroots into a tmpfs root that bind-mounts only `("/usr", "/bin", "/lib", "/lib64")`
  plus the project, then spawns the program with **its own `sys.executable`** (helper.py:75).
* Under a venv (`/tmp/btvenv/bin/python3`) that path does not exist inside the chroot:
  `Popen` raises `FileNotFoundError` **before any program line runs**. Every confined run exits 1
  with a harness traceback. The taught program never started; the receipt reads like the program
  failed.

Why this matters beyond this round: **any venv, any CI job that installs pytest into the
interpreter it runs with and then executes a taught program under a chroot, breaks the same
way** — and the failure is attributed to the work, not the harness. The tree's own doctrine
(this is the third layer where a harness fault impersonated a result: vacuous baselines,
exit-1 "passes", now a missing interpreter).

**Fix** (ported, not invented): `confine_v1._python_in_chroot()` — the exact rule
`brokered_workspace_execution_v1._python_in_chroot` already follows (prefer
`/usr/bin/python3` → `/bin/python3` → `sys.executable` only if under a mounted prefix) — used at
the helper launch. The helper then carries a chroot-visible `sys.executable` for its own
post-chroot spawn, so one substitution fixes both spawns.

**Pins:**

* `test_confine_mount_failure_v1.py::ChrootInterpreterTests` — with `sys.executable` mocked to a
  venv path, the launch argv must contain exactly one interpreter, not the venv's, and it must
  start with `/usr/` or `/bin/`. Fails on base (venv path present), passes after.
* The front-door test itself is the integration pin: it runs under
  `/tmp/btvenv/bin/python3` — the exact environment that failed before the fix.

**Surveyed siblings (same class), deliberately NOT fixed here:**

* broker: already normalized (three sites) — confirmed, no change.
* `confine_v1.available()` probe and `run_readonly` → broker: host-side or normalized — no change.
* **`zero_ambient_namespace_launcher_v1`**: `_ENTER_ROOT_BEHIND_SYSCALL_FILTER` does
  `os.execv(sys.argv[3], …)` *after* chroot; callers (`creature_runtime_v1:1511`, `:2110`)
  pass `_sys.executable`. Under a venv that is the same ENOENT class. Unmeasured this round —
  **named next, not smuggled in** (needs its own measured round with pins).

## 4. What was checked and found already solid (state adjudication)

The two "you were right" documents (`THE_SYSTEM_ALREADY_WORKS.md`,
`WHY_CANT_WE_DO_THIS_NOW`) and the skeptical line were re-adjudicated against probes, not prose:

| Claim | Verdict now |
|-------|-------------|
| `solve_or_learn` 4-tier entry exists and runs | **TRUE — demonstrated end to end this round** (§2) |
| 5 verified skills / 11 compiled workflows / 1 transfer episode / 768 KB workflows exist | **TRUE — probe-verified on this checkout** |
| Fresh-set generalization: 9/9 kinds learn, 83/105 = 79% `same` | **TRUE (main, #6743 round); `diff`=6 and `extra`=13 falsified and left falsified** |
| "the mechanism works; only verification/state remains" | **Half true**: state is populated and reproducible (auto-seed + tamper checks); the loop runs. The skeptical line remains correct about *what is recorded*: audit measured **452 PASS / 58 FAIL / 95 UNRUNNABLE, only 10 checkable (1.7%)** — an experience without a check that can fail is still mostly a sentence |
| "one try is not a learning signal" (`ONE_TRY_IS_NOT_A_LEARNING_SIGNAL`) | **Still correct as stated about identification**: one showing underdetermines intent (fresh-set `diff`/`extra`; this round's rename refusal is the same boundary at the engine level). What changed is that *when the interface + verifier + lesson discipline carry the generalization*, one showing **does** become a permanent skill — §2 is that case, executed |

The honest synthesis (unchanged from `FIRST_PRINCIPLES...`, now with a live demonstration):
**deterministic interpretation "solved"; identification and verification-fraction are the open
sub-problems; scale sub-problems open.**

## 5. Bad ideas killed this round before implementation

1. **Convert receipts' `output_sha256` into `expect_file_sha256` declarations** (my leading
   candidate: the audit supports the field, the receipts already carry the digests, so history
   becomes checkable). **Killed by measurement:** only **28** records have both `argv` and an
   output digest; **25 are unrunnable here** (13 foreign `/home/runner|/sprite` paths, 8
   `qrencode` absent, 4 `zint` absent); the 3 runnable ones write a proof file whose parent
   directory is cleaned, so all 3 re-runs produced no output file. The conversion would move
   ~3 records from the wrong column. Not worth the diff.
2. **Blanket `expect_exit: 0` on the 442 started passes.** Already failing nonzero *without* the
   expectation (the audit round's fix), so it relabels without adding failure power; the audit
   itself ranks real needles/claims as the actual gain. Verdict: weak, deferred to a claims
   census (what needle would each claim even assert?).
3. **Re-pin `learn=False` Tier0 bypass** — already asserted by
   `test_optimal_unified_creature_and_prc2_v1` ("zero-memory `learn=False` isolation").
4. **Re-build taught-door coverage** — `test_two_refactorings...` already pins door rename/
   inline/declines (96 tests, re-run green this round). Only the *controller Tier0 status* and
   the *shipped pair through `solve_or_learn`* were gaps; those are the new file.

## 6. The standing question, answered with this round's evidence

**(a) True:** one try → permanent skill is real *in this tree*, and this round demonstrated it
through the same door production uses: teach (one example) → lesson artifact with re-derived
`teaches` → apply to a file the teaching never saw → exact edit, stdout-verified, hit recorded,
≤ 205 ms, $0. The "you were right" documents' mechanism claims are probe-true.

**(b) Wrong as stated** — "→ solves ALL computer use + advanced software engineering
perfectly/permanently" fails on four measured walls:

1. **Verification fraction:** 1.7% of recorded "verified" claims can still be shown true
   (audit). A skill that recalls is not a lesson that can be lost.
2. **Identification:** one showing underdetermines intent (fresh-set 79% `same`, rename refusal
   this round). The interface/verifier carries the rest — which is why the loop works *here*
   (lesson discipline + stdout postconditions + fail-closed refusals) and does not transfer for
   free to arbitrary environments.
3. **Long-horizon computer use is not solved anywhere:** OSWorld 2.0 (2026-07) best agent
   completes **20.6%** binary at 500 steps; v2.1 board (2026-10): Claude Opus 5.5 **48.7% binary
   / 81.8% partial**, official board Opus 5 **44.33% binary** — with the named failure pattern
   *"skip verification"*. Short-task OSWorld-Verified is ~90% (above human 72%); the gap is
   exactly long-horizon constraint-keeping and checking.
4. **Permanence is a property of the whole stack, not the lesson:** this round's venv defect
   broke *every* confined run while every lesson-level test stayed green. "Permanent" has to
   include the harness that replays it.

**(c) Not a sentient creature.** The strongest evidence is this round's own refusals: the system
says *which* file, *which* line, *which* reason it declines — receipt-generating machinery that
can be wrong in named ways. Architecture-for-it vs category-error remains the settled frame
(`FIRST_PRINCIPLES...`).

**Smartest path (unchanged, now sharper):** raise the fraction of experiences that carry a check
that can fail (the audit's own ranked list: needles/claims census over the 442, triage the 58,
the 5 declarations); keep the loop's lesson discipline (re-derived `teaches`, stdout
postconditions, named refusals) as the template for every new skill shape; fix harness-fidelity
sibling classes only in measured rounds with pins (venv/chroot done; namespace launcher named).

## 7. External sources this round (2026)

* **WICL / RoboScript** (arXiv `2611.12885`, 2026-11-09): one demonstration + rehearsal in
  simulation, feedback written into context not weights → **83.4% mean over 50 RoboTwin tasks,
  beating a 50-demonstration trained policy by >20 points**. Their "receipts" distinguish *a
  command was executed* from *an effect was achieved* — the same distinction this tree's
  audit makes. Independent convergence: one showing works when receipts + rehearsal carry it.
* **Work2Skill** (2026-10-12): human GUI demos → `SKILL.md` files → **+3.1 to +10.5 points** on
  OSWorld subsets. Skill libraries help a little, per demonstration; they do not remove the gap.
* **OSWorld 2.0** (arXiv `2606.29537`, v2.1 board 2026-10): long-horizon workflows, median human
  1.6 h / 318 tool calls; best binary ~44–49%. Failure pattern: lose constraints, miss mid-task
  info, **skip verification**.
* **Who Verifies the Verifier?** (arXiv `2610.11464`, NeurIPS 2026 workshop): removing anchor
  guards collapses the co-evolved verifier into a vacuous always-pass grader **that trains skills
  just as well** — downstream score cannot certify a verifier. Confirms the audit's thesis from
  the outside.
* **Hardening Agent Benchmarks** (arXiv `2606.08960`): 323/1,968 (16%) terminal-benchmark
  tasks hackable by frontier models given only the task description.

## 8. Measurements and regressions this round

* New pins: `test_the_front_door_teaches_and_applies_what_the_bundle_ships_v1.py` (2 tests),
  `test_confine_mount_failure_v1.py::ChrootInterpreterTests` (1 test).
* Batteries run (venv interpreter, the environment that failed pre-fix):
  confine mount failure + new pin **7 passed + 6 subtests**; front-door file **2 passed**;
  `test_two_refactorings...` **96 passed**; `test_a_taught_skill_does_not_destroy...` +
  `test_admitted_confinement_v1` **30 passed**. Total **135 passed, 0 failed**.
* Tracked state restored after learn=True runs (`ASSOCIATIVE_MEMORY_V1.json` snapshot/restore
  in the new fixture; `git checkout --` after neighbor suites).
* Zero spend; no benchmark row moved; no capability credit claimed; truth-achieved stays false.

## 9. Named next (not smuggled)

1. **Claims census for the 442 started passes** — what needle/expectation each claim could even
   carry; only then write expectations (the digest idea is dead, §5).
2. **`zero_ambient_namespace_launcher_v1` post-chroot `execv` of caller argv** — same venv class
   as §3, unmeasured; own round with pins.
3. **pytest fallback for the egraph gate** (#6743's named next, unchanged).
4. Feed the teach corpus (`edits_repeated_across_projects` cache) into the live compounding loop
   (round 26's stated next; larger scope).
