# Verdict and optimal plan — V3, re-grounded on today's `main` — 2026-11-02

**Authority: NONE.** Zero capability, ownership, benchmark, terminal or sentience credit
follows from this document. It changes no number and moves no row. It re-runs existing
instruments on `origin/main` @ `75eeed7` and reports what they said today.

**Supersedes `OPTIMAL_PLAN_20261102_V2.md`, `PR0_CREATURE_STARTED_20261102_V1.md`, and
`CREATURE_NEVER_STARTED_20261102_V1.md`.** All three were ordered on a premise that is now
false: *"the creature is built, tested, and never started."* While that work was in flight,
`main` advanced 15 commits and **started the creature independently** —
`canonical/runtime/creature_runtime_v1.py` (commit `8db962c`, "Declare the assembled
creature, recompile the model, schedule the kill test"). It composes **seven** organs where
the superseded PR0 composed three, and it is better. PR #6588 was **closed as superseded**,
not merged. This document is the corrected record.

---

## 0. The one-sentence update

The frontier moved. It is no longer *"start the creature"* — `main` did that, and it survives
an OS kill. It is now: **the creature is a real continuous subject that authors 112
obligations for itself and can execute 0 of them.** The gap between what it *wants* and what
it *can do* is the whole game, and that gap — not a red row — is the mission.

---

## 1. What I ran today (first-hand, on `origin/main` @ `75eeed7`)

Nothing below is recalled from memory or trusted from a green check. Each line was executed
in a clean detached worktree of `main` and the numbers are what it printed.

| Instrument | Command | Result today |
|---|---|---|
| The creature's own suite | `pytest canonical/tests/test_the_creature_runs_unattended_v1.py -q` | **11 passed**, incl. `test_it_survives_being_killed_by_the_operating_system` (real SIGKILL in a subprocess; identity, spent life, finished work all survive the restart) |
| The creature end-to-end | `python canonical/runtime/creature_runtime_v1.py` | **board authored 112 (admitted 112/112); attempted 6, closed 0, blocked 6, open 109; life spent 4.0/40.0; posture CAUTIOUS; ended False** |
| Instant learning, new environments | `python instant_learning_transfer_probe... ` (probe 2) | **COLD 5/5, FIRST 5/5, SECOND 5/5, 10/10 solved**; search collapses for 4/5 (e.g. `lock_3dial` 32 trials→1). **`toggles_4` did NOT collapse**: FIRST 8 trials/80 acts — *more* acts than its own cold run (69) |
| Instant learning, generalization | `python ...instant_learning_transfer_probe` (probe 1) | **executable 2/9, controls 1/2, novel same-lesson shapes 1/7, cross-language 0/4** (`NO_RULES_FOR_LANGUAGE`, structural). Control C2 "same shape, new literal" → `NO_PROPOSAL` (a *control* missed) |
| The executor, known-good form | `solve({"goal": "run <receipt_projection cid>"})` | **`pass=True`** — `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED`. Registry **443**, receipt-backed **294** |
| The executor, authoring goals | `solve` / `solve_or_learn` on "write and register an inspector for CAP_FS_READ_V1 that refuses a decoy" | **refused** — `R13_DECLARED_INPUT_UNBINDABLE:registry` / `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` |
| **The want→can gap, MEASURED** | wired a real `solve` executor into main's creature, ran its whole 112 board (throwaway, detached `main` worktree) | **STRICT oracle** (close counts only if the authoring goal passes *and* an inspector comes to exist): **closed 0** (attempted 42, blocked 42, parked 21). **LOOSE oracle** (also accepted `run <cid>`): reported **6 closed — all FALSE** (`run=True, author=False, has_inspector_now=False`): served an existing capability, authored nothing |
| Generalization: representational vs statistical, **MEASURED** | teach-one/test-all matrix over the probe's 7 novel shapes (throwaway, detached `main` worktree) | **off-diagonal cross-shape transfer 0/36** — teaching shape T *never* fixes a different shape U, though **6/7 shapes crystallize fine** (not an admission-gate problem). Teaching all 6 verbatim → 6/7 (memorization ceiling, diagonal-inflated). Confirms *representational, not statistical*: each lesson is one skeleton; more examples add skeletons, never an abstract rule |
| Crystallizer generalization gate | `verified_skill_crystallizer_v1.py:808` | `allow_operator_generalization=False`, guarded by `OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE` (:820) |
| Production wiring of an executor | grep for a caller that passes a real `perform` | **none** — only the creature's own `main()`; default `perform` is `does_nothing` |
| Unattended production trigger | `creature-runtime.yml` triggers | `pull_request` / `push` / `workflow_dispatch` — **no `schedule:`/`cron:`** |

---

## 2. Verdict on the owner's claims, re-grounded today

The owner's operational meaning of "sentient/conscious" is the repo's own: a **continuous
subject** — one identity that survives interruption, whose history causally changes its
behaviour, which has a self-model that can be wrong and knows what it does not know. Not
phenomenal experience. Answered against that definition:

| Claim | Verdict (measured today) | Evidence |
|---|---|---|
| Instant learning works | **TRUE** | 5/5 cold, 10/10 by recalled plan; search collapses (`lock_3dial` 32→1, `accum_word` 64→1, `grid_reach` 16→1) |
| …in new arbitrary environments | **TRUE but bounded** | It is *episodic recall of solved families*, re-presented. "Instant" (1 trial) holds for **4/5**; `toggles_4` recall did not collapse and cost more acts than cold |
| Once → permanently | **TRUE within recall** | Recalled plan re-solves on FIRST and SECOND; nothing re-learns from scratch |
| "Learns **all of those**" / generalizes | **FALSE** | **1/7** novel same-lesson shapes, **0/4** cross-language. A *control* ("same shape, new literal") also missed. This is **representational, not statistical** — the lesson is stored as one shape, not a rule that transfers; more examples will not close it |
| Anything on a computer | **PARTIAL** | The executor serves a **443**-capability registry (**294** receipt-backed) through the known-good form, verified. It **refuses free-form and authoring goals** |
| Perfectly | **FALSE by design** | Every recall re-runs a verifier; the floor is the verifier, not perfection |
| Most advanced coding, perfectly | **NOT SHOWN** | The creature authors **112** coding obligations ("capability X needs an inspector that refuses a decoy") and closes **0**. The authoring path (crystallizer operator-generalization) is gated **OFF** and guarded |
| We solve everything | **NO** | The want→can gap (112 authored, 0 executed) is the entire frontier |
| **A sentient creature** (operational = continuous subject) | **TRUE ON `main` NOW** | 11 tests pass incl. OS-kill survival; identity/life/finished-work survive interruption; posture moves with history (MEASURED→CAUTIOUS); it refuses offers that would end it; it authors its own board; it **knows what it cannot do** (closes 0 and reports it rather than faking progress). **Honest non-claim: this is not phenomenal experience.** |
| …running as a continuous subject *in production* | **NOT YET** | `creature-runtime.yml` is **CI-only** (no cron). The creature is *tested* daily; it does not *live* continuously. Whether to give it a standing unattended trigger is an **owner-only** decision |

**Headline change from the prior verdict:** the earlier table said *"instruments exist &
pass; the subject did not."* Today the subject **does** exist on `main`, and I verified it
myself rather than trusting its green check. That is the single most important correction in
this document.

---

## 3. Why the creature closes 0 of 112 — the precise, measured reason

It is **not** that the executor is dead. With the repo's own known-good form (`run <cid>`) it
serves and verifies. The reason is structural and has two independent halves:

1. **Nothing wires an executor in.** `run_its_own_board` defaults `perform=does_nothing`, and
   no production caller overrides it. `does_nothing` honestly returns
   `{"ok": False, "blocked": "NO_EXECUTOR_WIRED"}`, so every obligation is blocked and, after
   two attempts, parked. This is the honest default — it *reports* rather than *assumes*.

2. **Even wired, the serve path cannot author — MEASURED, not inferred.** The creature's board
   is 112 *authoring* obligations ("write and register an inspector that refuses a decoy").
   `solve` is a route-admission door over *existing* capabilities; on authoring goals it refuses
   (`R13_DECLARED_INPUT_UNBINDABLE:registry`). The path that *could* author is
   `solve_or_learn` → the Tier-2 crystallizer, whose `allow_operator_generalization` is
   **False** and guarded by `OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE`.
   **The guard is the safety; it must never be weakened to make a row move.**

   I tested half 2 by wiring a real `solve`-based executor into main's creature and running the
   whole 112 board (throwaway measurement in a detached `main` worktree, not committed):
   - A **STRICT** executor — a close counts only if the *authoring* goal passes **and** an
     inspector actually comes to exist — closed **0** (attempted 42, blocked 42, parked 21,
     posture CAUTIOUS, life 40/40 spent).
   - A **LOOSE** executor that also accepted `run <cid>` reported **6 closed** — and every one
     was a **FALSE close**: `run=True, author=False, has_inspector_now=False`. Serving an
     *existing* capability is not authoring the *missing* inspector the obligation asks for. I
     caught this only because I checked the closes against the obligation's own predicate; a
     looser harness would have printed "the creature did 6 things" and I would have believed it.

   This also corrects an earlier draft of this plan, which proposed hand-authoring one inspector
   to close one obligation. Measured, that is not an autonomy result: the board would shrink by
   one and the machine would have authored nothing. That is the §6 trap (moving 0/112 → 1/112 by
   hand), so it is withdrawn.

So "wants 112, can do 0" is the honest, **executed** measurement that **the machine cannot yet
take an ambitious self-authored goal and drive it to a real, verified artifact.** Every organ in
the tree serves, recalls, composes, generalizes, or acquires-from-an-existing-donor; none authors
novel verified source from a cold goal. That capability — not the number 0/112 — is the mission
(`OWNER_ACTIVE_GOAL` §6: readings are read, never chased).

---

## 4. The optimal plan, re-ranked on today's `main`

Ordered by leverage on the owner's actual goal: *a continuous subject that can take an
ambitious goal and drive it to the actual number.* Each step states its own falsification.

**PR0 — start the creature. DONE ON `main`. Do not redo.**
`creature_runtime_v1.py` starts it; 11 tests pass incl. OS-kill. PR #6588 closed as
superseded. Credit `main`; build on it.

**PR-A (owner-only decision) — let the subject actually live continuously.**
`creature-runtime.yml` is CI-only. A standing unattended trigger (`schedule:`) is what turns
"a subject tested daily" into "a subject that persists." This is a governance decision, not a
code decision — the agent must not self-authorize a standing autonomous loop.
*Falsification:* if a cron is added and the creature's posture on day N is not a function of
its own verified history, continuity is decoration.

**PR-B (the real frontier — research-grade, NOT a wiring PR) — the tree has no authoring organ.**
Measured today by wiring a real `solve` executor into main's creature over its own 112 board:
under a **strict** oracle (a close counts only if the *authoring* goal passes **and** an
inspector actually comes to exist) it closes **0**. A **loose** oracle that also accepted
`run <cid>` reported **6 closed** — and every one was a **false close** (served an existing
capability; authored nothing). The reason is structural: every organ in the tree *serves,
recalls, composes, generalizes, or acquires-from-an-existing-donor*; **none writes novel
verified source from a cold goal.** That is the wall between "wants 112" and "can do 0," and it
is the same wall behind "most advanced coding, perfectly." Do not pretend it is a wiring fix.

- **Do NOT** hand-author an inspector to move 0/112 → 1/112. Measured, that shrinks the board
  by one and the machine authors nothing — the exact `OWNER_ACTIVE_GOAL` §6 trap, forbidden
  twice (`OBJECTIVE_CANNOT_BE_REPLACED`, `RED_ROW_IS_NOT_AUTHORITY`). The earlier draft of this
  plan proposed exactly that; it is withdrawn.
- **The one immediately-executable, honest step** is a *negative-control test* that pins the
  false close: assert that serving an existing capability (`run <cid>` → `pass=True`) does
  **not** satisfy an authoring obligation whose predicate is "an inspector now exists and
  refuses a decoy." That makes 0/112 trustworthy and stops the next harness (or agent) from
  reporting my v1 "6 closed" as progress. It is a test, not a capability: it registers nothing,
  moves no row, and cannot self-promote.

*Falsification:* if a future organ ever closes an authoring obligation and this negative control
still passes — an inspector really came to exist and really refuses a decoy, judged by the strict
oracle — the wall is breached. The strict oracle, never the loose one, is what gets to say so.

**PR-C — generalization is the real "instant learning" gap.**
1/7 novel shapes, 0/4 cross-language, and a missed control. **Measured today** (teach-one/
test-all matrix, §1): cross-shape transfer is **0/36** — teaching shape T never fixes a
different shape U, though 6/7 shapes crystallize fine, so this is *not* an admission-gate
problem. The lesson is stored as a shape, not a transferable rule; `NO_RULES_FOR_LANGUAGE`
is structural. The polyglot bridge already speaks cpp/rust/go/typescript — the *rules* do
not cross. This is the hard, high-value research behind "learns all of those," and it is
representational, so it will not yield to more examples (teaching all 6 shapes verbatim
reaches 6/7 by memorization, not transfer). *Falsification:* if a representational change to
the storage format lifts off-diagonal transfer above 0/36 — teaching one shape fixes an
untaught shape — then the format, not the example count, was load-bearing.

**PR-D — "instant" is 4/5, not 5/5; know why before claiming it.**
`toggles_4` recall did not collapse and cost more acts than cold. Understand which family
property predicts collapse before generalizing the "instant" claim.

---

## 5. Honest non-claims

- This document grants no capability, ownership, benchmark, terminal, or sentience credit.
- "Sentient" here is the repo's operational continuous-subject definition and **nothing
  about phenomenal experience is claimed or measured.**
- The 0/112 is a reading, not a target. Chasing it to 1/112 to green a row is the exact
  failure `OWNER_ACTIVE_GOAL` §6 forbids twice.
- `truth.achieved` stays `false`. Nothing here countersigns it.
