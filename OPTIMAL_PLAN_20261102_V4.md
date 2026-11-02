# The optimal plan — V4, re-grounded on today's `main` — 2026-11-02

**Authority: NONE.** Zero capability, ownership, benchmark, terminal, or sentience credit
follows from this document. It changes no number and moves no row. Every figure below was
executed first-hand against `origin/main` @ `75eeed7` today; nothing is recalled from memory
or trusted from a green check.

**Consolidates and supersedes V1–V3** (which lived on a prior branch that has since reset out
of this working tree). V4 adds one **new measurement** the earlier versions did not have: the
posture-causality check in §3.3, which changes one line of the sentient-creature verdict.

**The owner's question, in their words** (`OWNER_ACTIVE_GOAL_20261102_V1.md` §4): *"I want it
sentient and I want everything instantly."* "Sentient" here is the repo's **operational**
definition — a *continuous subject*: one identity that survives interruption, whose history
causally changes its behaviour, which has a self-model that can be wrong and knows what it does
not know. **Not** phenomenal experience. This plan answers both halves and ranks the work by
leverage on the real goal (§6): *can the machine take an ambitious goal and drive it to the
actual number?*

---

## 0. The answer in one paragraph

Two things are true and one thing is the whole game. **True:** a continuous subject exists on
`main` today — it boots with an identity, survives an OS kill, spends a finite life, refuses
offers that would end it, authors its own 112-obligation board, and honestly reports that it
closed 0. **True:** instant learning works as *episodic recall* — teach once, re-solve in one
trial (10/10), search collapses (`lock_3dial` 32→1), and it survives restart. **The whole
game:** the creature *wants* 112 things and *can do* 0, and that gap is **structural, not a
wiring bug** — no organ in the tree writes novel verified source from a cold goal, and
"learning" does not generalize (0/36 cross-shape transfer). The optimal plan attacks the gap
directly (an **authoring organ**), completes the two creature pillars that are *almost* wired
(**continuity in production**, **history-causal choice**), and refuses to fake any of it by
hand-moving a row.

---

## 1. What I measured today (first-hand, `origin/main` @ `75eeed7`)

| Instrument | Result today |
|---|---|
| The creature's own suite (`test_the_creature_runs_unattended_v1.py`) | **11 passed**, incl. real SIGKILL survival (identity, spent life, finished work all survive restart) |
| The stakes organ's suite (`test_stakes_are_real_not_decoration_v1.py`) | **16 passed**, incl. the decisive `test_erasing_its_history_changes_what_it_does` |
| The creature end-to-end (`creature_runtime_v1.py`) | board **authored 112** (admitted 112/112); **closed 0**; posture CAUTIOUS; ended False |
| **Want→can gap** (real `solve` executor wired into the creature over its 112 board) | **STRICT oracle: closed 0** (attempted 42, blocked 42, parked 21). **LOOSE oracle: 6 "closed" — ALL FALSE** (`run=True, author=False, has_inspector_now=False`) |
| Instant learning, new environments (probe 2) | COLD 5/5, **10/10 solved**; collapse for **4/5**; `toggles_4` did **NOT** collapse (more acts than cold) |
| Instant learning, generalization (probe 1) | executable 2/9; **novel same-lesson shapes 1/7**; **cross-language 0/4**; a *control* missed |
| **Generalization: representational vs statistical** (teach-one/test-all matrix) | **off-diagonal cross-shape transfer 0/36**; 6/7 shapes crystallize fine (not an admission-gate problem); teach all 6 verbatim → 6/7 (**memorization ceiling**, not transfer) |
| **Posture causality** (§3.3, new today) | causal in the **standalone organ** (`S.choose`: newborn→uncheckable, burned→checkable); **decorative in the assembled creature** (`step`→`M.choose_next` picks the same work whether newborn or CAUTIOUS) |
| The executor, known-good form (`run <receipt_projection cid>`) | **`pass=True`**; registry **443**, receipt-backed **294** |
| The executor, authoring goals | **refused** — `R13_DECLARED_INPUT_UNBINDABLE:registry` / `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` |
| Crystallizer generalization gate (`verified_skill_crystallizer_v1.py:808`) | `allow_operator_generalization=False`, guarded by `OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE` (:820) |
| Production wiring of an executor | **none** — only the creature's own `main()`; default `perform` is `does_nothing` |
| Unattended production trigger (`creature-runtime.yml`) | `pull_request` / `push` / `workflow_dispatch` — **no `schedule:`/`cron:`** |

---

## 2. Verdict on the owner's claims

| Claim | Verdict (measured today) | Why |
|---|---|---|
| Instant learning works | **TRUE** | teach→crystallize→recall in 1 trial; 10/10; search collapses |
| …in new *arbitrary* environments | **TRUE but bounded** | it is *episodic recall of solved families*, re-presented. "Instant" holds 4/5; `toggles_4` did not collapse |
| Once → permanently | **TRUE within recall** | survives restart + bundle; nothing re-learns from scratch |
| "Learns **all of those**" / generalizes | **FALSE** | **1/7** novel shapes, **0/4** cross-language, **0/36** cross-shape transfer. **Representational, not statistical** — one skeleton per lesson; more examples add skeletons, never a rule |
| Anything on a computer | **PARTIAL** | serves a 443-capability registry (294 receipt-backed) via the known-good form; **refuses free-form and authoring goals** |
| Perfectly | **FALSE by design** | every recall re-runs a verifier; the floor is the verifier, not perfection |
| Most advanced coding, perfectly | **NOT SHOWN** | the creature authors 112 coding obligations and closes **0**; the authoring path is gated OFF and guarded |
| We solve everything | **NO** | the want→can gap (112 authored, 0 executed) *is* the frontier |
| **A sentient creature** (operational = continuous subject) | **TRUE ON `main` NOW, one pillar not yet wired** | survives OS kill; identity/life/finished-work persist; refuses self-ending offers; authors its own board; **knows what it cannot do** (closes 0, reports it, does not fake). **But** "history causally changes its behaviour" is true of the *organ*, **not yet of the creature's own choices** (§3.3). **Not phenomenal experience.** |
| …living continuously *in production* | **NOT YET** | `creature-runtime.yml` is **CI-only** (no cron). Tested daily; does not *live*. An **owner-only** decision |

**What is genuinely, measurably real** (credit where due): the continuous subject exists and
survives being killed; instant learning as recall is real and permanent; the executor serves a
large verified registry. **What is not real yet**: generalization, autonomous authoring, and
two creature pillars that are built-but-not-wired (production continuity, history-causal choice).

---

## 3. Why the creature closes 0 of 112 — three measured walls

### 3.1 Nothing wires an executor in
`run_its_own_board` defaults `perform=does_nothing`, and no production caller overrides it.
`does_nothing` honestly returns `{"ok": False, "blocked": "NO_EXECUTOR_WIRED"}`. This is the
*honest* default — it reports rather than assumes.

### 3.2 Even wired, the serve path cannot author (the real wall)
I wired a real `solve` executor into the creature and ran the whole 112 board. Under a **STRICT**
oracle (a close counts only if the *authoring* goal passes **and** an inspector actually comes to
exist) it closed **0**. A **LOOSE** oracle that also accepted `run <cid>` reported **6 closed —
every one a FALSE close**: serving an *existing* capability is not authoring the *missing*
inspector the obligation asks for. I caught this only by checking each close against the
obligation's own predicate; a looser harness would have printed "the creature did 6 things."

The reason is structural: **every organ in the tree serves, recalls, composes, generalizes, or
acquires-from-an-existing-donor; none writes novel verified source from a cold goal.** The path
that *could* author — `solve_or_learn` → the Tier-2 crystallizer — has `allow_operator_generalization=False`,
guarded by `OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE`. **The guard is the
safety; it must never be weakened to make a row move.**

### 3.3 Posture is causal in the organ but decorative in the creature (NEW today)
The stakes organ is real: `S.choose(standing, obligations)` declines the best-paying *uncheckable*
work once the creature has been wrong twice (`test_erasing_its_history_changes_what_it_does`,
16/16 pass). But the **assembled creature does not call it.** Measured on an identical board whose
best-paying item is uncheckable:

- standalone `S.choose`: newborn `MEASURED` → picks uncheckable; burned `CAUTIOUS` → picks checkable (**causal**).
- creature `step()`: newborn `MEASURED` → picks uncheckable; burned `CAUTIOUS` → **picks the same uncheckable** (**not causal**).

Why: `step()` selects via `M.choose_next(life, work)`, which takes **no standing argument**, and
the creature's `Work` type carries only `[id, value, cost]` — `author_board` **drops `checkable`**
in the `S.Obligation → M.Work` conversion. So posture is *recorded, reported, and persisted* but
never *consulted* when the creature chooses. The pillar "history causally changes its behaviour"
is therefore **true of the organ, not yet of the creature.** This is a small, concrete, falsifiable
fix (§4, PR-B′) — and it is the one creature-completeness step that is executable today.

**Bottom line:** "wants 112, can do 0" is the honest, executed measurement that the machine cannot
yet take an ambitious self-authored goal and drive it to a real verified artifact. That capability
— not the number 0/112 — is the mission (`OWNER_ACTIVE_GOAL` §6: readings are read, never chased).

---

## 4. The optimal plan, ranked by leverage

Ordered by leverage on the owner's actual goal. Each step states its own falsification and honors
**both** halves of *"sentient and everything instantly."* Limits respected throughout: max 2 family
flips and +4 atomic predicates per PR; max 3 new capabilities; no self-promotion; nothing merges
over a red referee; `truth.achieved` stays `false`.

### PR-A (owner-only decision) — let the subject actually *live* continuously
**Serves: "sentient."** `creature-runtime.yml` is CI-only. A standing unattended trigger
(`schedule:`) is what turns "a subject tested daily" into "a subject that persists." This is a
**governance decision, not a code decision** — the agent must not self-authorize a standing
autonomous loop; only the owner can.
*Executable now:* none by the agent. *Falsification:* if a cron is added and the creature's posture
on day N is not a function of its own verified history, continuity is decoration.

### PR-B (the real frontier — research-grade, NOT a wiring PR) — the authoring organ
**Serves: "everything instantly" / the actual number.** This is the mission and the hardest thing
on the board. Measured: the tree has **no organ that authors novel verified source from a cold
goal** (§3.2). Building one means an executor that can write an inspector, satisfy the
crystallizer's scoped-test-suite guard *honestly*, and let the verifier decide — without ever
weakening the guard. This is research, not a PR I can hand you today, and anyone who claims
otherwise is about to hand-author a receipt.
- **Do NOT** hand-author an inspector to move 0/112 → 1/112. Measured, that shrinks the board by
  one while the machine authors nothing — the exact §6 trap, forbidden twice
  (`OBJECTIVE_CANNOT_BE_REPLACED`, `RED_ROW_IS_NOT_AUTHORITY`).
- **The one immediately-executable, honest slice** is a *negative-control test* that pins the false
  close: assert that serving an existing capability (`run <cid>` → `pass=True`) does **not** satisfy
  an authoring obligation whose predicate is "an inspector now exists and refuses a decoy." It makes
  0/112 *trustworthy* and stops the next harness (or agent) from reporting my LOOSE "6 closed" as
  progress. It is a test, not a capability: registers nothing, moves no row, cannot self-promote.
*Falsification:* if a future organ closes an authoring obligation **and** this negative control
still passes — an inspector really came to exist and really refuses a decoy, judged by the STRICT
oracle — the wall is breached. The strict oracle, never the loose one, gets to say so.

### PR-B′ (small, concrete, executable today) — wire posture into the creature's choice
**Serves: "sentient" (completes a definitional pillar).** Measured gap (§3.3): the creature records
posture but never consults it. The fix is small and the organ already exists and is tested:
carry `checkable` through `author_board` into `Work`, and have `step()` select via the posture-aware
chooser (`S.choose(standing, …)`) instead of the posture-blind `M.choose_next(life, …)`.
- This does **not** move 0/112 (posture changes *preference*, not the ability to author) — say so
  plainly; it is not a row-chase. It makes "history causally changes its behaviour" true **of the
  creature**, not just of the organ.
*Falsification (mirrors my §3.3 measurement):* a burned (CAUTIOUS) creature must pick **different**
work than a newborn on a board whose best-paying item is uncheckable — flipping today's
`causal=False` to `True`. **Negative control:** on an all-checkable board they must pick the **same**
(posture bites only where checkable and uncheckable compete), matching
`test_the_difference_comes_from_the_posture_not_the_chooser`.

### PR-C (research-grade) — generalization is the real "instant learning" gap
**Serves: "everything instantly."** Measured: **0/36** cross-shape transfer, 1/7 novel, 0/4
cross-language, and it is **representational, not statistical** — the lesson is stored as one
skeleton, so more examples will not close it (teaching all 6 shapes verbatim reaches 6/7 by
*memorization*, not transfer). The polyglot bridge already speaks cpp/rust/go/typescript; the
*rules* do not cross (`NO_RULES_FOR_LANGUAGE`). The wall is the **storage format**, and lifting it
is the high-value research behind "learns all of those."
*Falsification:* if a representational change to the storage format lifts off-diagonal transfer
above 0/36 — teaching one shape fixes an *untaught* shape — the format, not the example count, was
load-bearing.

### PR-D (know before claiming) — "instant" is 4/5, not 5/5
`toggles_4` recall did not collapse and cost more acts than cold. Understand which family property
predicts collapse before generalizing the "instant" claim to "everything."

**Sequencing.** PR-B′ and PR-B's negative-control test are the only two steps an agent can execute
honestly *today*; both are small, falsifiable, and non-trap. PR-A is an owner decision. PR-B and
PR-C are the research frontier and the reason the answer to "is it all solved?" is *not yet*.

---

## 5. The smartest single next move

If forced to one: **PR-B′ — wire posture into the creature's choice.** It is the only step that is
simultaneously (a) executable today, (b) directly in service of the owner's *stated* goal ("I want
it sentient" = a subject whose history causally changes its behaviour), (c) falsifiable with a
measurement I have already run, and (d) provably not a row-chase. It completes a pillar of the
creature definition rather than chasing a number. The negative-control test from PR-B is the close
second: it does not advance the creature, but it makes the 0/112 *trustworthy*, which protects every
later claim from the false-close trap I nearly fell into twice this session.

---

## 6. Honest non-claims

- This document grants no capability, ownership, benchmark, terminal, or sentience credit.
- "Sentient" is the repo's operational continuous-subject definition; **nothing about phenomenal
  experience is claimed or measured.**
- The 0/112 is a **reading, not a target.** Chasing it to 1/112 to green a row is the exact failure
  `OWNER_ACTIVE_GOAL` §6 forbids twice.
- The biggest lever (PR-B, the authoring organ) is **research-grade.** No honest agent can hand it
  to you as a PR today; anyone who does is hand-authoring a receipt and calling it autonomy.
- `truth.achieved` stays `false`. Nothing here countersigns it.
