# The "we already solved instant learning" claim, re-measured

**2026-11-03.** The owner asked: *instant learning + instant learning in new arbitrary
environments is solved — doesn't that mean we have a perfect solution for everything on a
computer? Give the model a try in each new environment or the right actions, and after doing
it once it learns permanently. So we solve everything on a computer, perfectly and
permanently? And we were trying to make a sentient creature — is this true, or are there
things that are wrong? What is real, what is not, and what is smartest to do?*

This is the answer after running the tree, not after reading it. It reverses one headline
number in `INSTANT_LEARNING_SCOPE_20261101_V1.md` and confirms the rest of that document's
verdicts. Every number below was produced by me today on commit `73f773d`, in this sandbox,
with disposable state files. **Authority: NONE.** No capability, ownership, benchmark,
terminal or sentience credit follows. `truth.achieved` stays `false`. Spend $0.

---

## 0. The one-paragraph answer

Half of what you believe is true and is a real, rare achievement: the machine solves a
*named, parameterised kind of environment*, keeps the solution, and reuses it after a restart
— and instant learning of a repository's *operating manual* (how to install, build and run it)
genuinely transfers to repositories never seen before. The other half is not true, and it was
true in the document you were shown because the probe that measured it re-used the same
environment instance and called it "new". Measured properly on genuinely different instances
of the same kind, **the carried lesson saved work in 1 of 15 cases and cost slightly more in
14 of 15.** The lesson transfers as *knowledge* but does not currently transfer as *speed*,
because the warm arm inherits the memory and pays for it twice. And no, doing a thing once on
a computer does not teach "all of those": the measured failure of that idea is neither
statistical nor fixable by repetition — it is representational. What you have is a strong,
honest learning *organ*, not a general solver and not a creature.

---

## 1. What is real (measured today, confirmed)

| Claim | Status | The measurement |
|---|---|---|
| Learning + persistence + restart works | **TRUE** | `transfer_learning_v1.drive` writes an episode store, a fresh process reads it back, a recalled plan is replayed and the goal is observed by executing it. Reproduced. |
| Environment *operation* transfers to unseen environments | **TRUE** | `environment_fit_v1` reads a project's own declarations (CI workflow → `package.json` → `Makefile` → `pyproject`), then ADAPT → PROVISION → FOLLOW. It generalises because *every* project declares how it runs. This is real one-shot transfer, and it is the strongest thing in the tree. |
| A one-shot taught code repair applies to a **renamed, novel instance of the same shape** | **TRUE** | Today: taught `return x <= lo → return x < lo`; applied to `def below(a, b): return a <= b` → `return a < b`. Also to argument-swapped and `and`-embedded variants. No model, no spend. |
| Rules can expire, and survive invalidation with their counterexample | **TRUE** | `rule_expiry_v1` (FRESH/STALE/UNKNOWN), `invalidate()` keeps the rule and the counterexample. `finite_capability_diagnosis` + `rule_scope_learning_v1` (21 tests, all passing today) narrow a rule's **scope** by measurement rather than by assumption. |
| The machine models its own ignorance and ranks it | **TRUE** | `ignorance_ledger_v1`, 13 tests. This is the honest, measurable half of "knows what it doesn't know". |
| The self-model / self-architect loop runs | **TRUE (as a mechanism)** | `test_sentient_cognitive_core_v1` — 13 tests, all passing today, including endogenous self-evolution triggered without an external call, and refusal of test-editing / input-dropping / held-out hardcoding. |

That is not nothing. A system that learns a procedure once, stores it, proves it still
applies, ages it out when the world changes, and knows what it has not learned, is doing the
real thing. It is also **not** what the sentence "we solved instant learning in new arbitrary
environments" claims.

---

## 2. What is not real — the headline number

`INSTANT_LEARNING_SCOPE_20261101_V1.md` §0.7 is the load-bearing evidence for the strongest
claim in the tree:

> "5/5 families, **10/10** new instances solved by recalled plan, several at **1 trial**"

It is reproduced by `transfer_learning_new_environment_probe_20261101.py`, which I ran today
and got exactly its published table. **The probe is honest; its label is wrong.** In four of
its five families, the three "phases" build the *same instance*:

```
lock_3dial      seed0=(0,0,0)   seed1=(0,0,0)   seed2=(0,0,0)    IDENTICAL
accum_word      seed0=''        seed1=''        seed2=''         IDENTICAL
grid_reach      seed0=(0,0)     seed1=(0,0)     seed2=(0,0)      IDENTICAL
modulo_counter  seed0=0         seed1=0         seed2=0          IDENTICAL
toggles_4       distinct (start bits come from `seed`)
```

The goal predicates are identical too. So "FIRST (new instance)" in that table means *the
same instance, called for the second time*. The 1-trial rows are real measurements of
**exact-episode replay** — the stored plan was found, replayed, and the goal observed. That is
a genuine ability. It is not transfer, and it is the one ability a lookup table also has.

### The corrected measurement

`transfer_learning_new_instance_probe_20261103.py` (new, with
`canonical/tests/test_transfer_new_instance_probe_20261103.py`, 4 tests passing). Five
families × three seeds. For each: teach on a **source** instance, then hand an identical
**target** instance to two arms that differ only in whether the source lesson is available.

- **COLD** — empty store, recall off.
- **WARM** — store seeded by the source lesson, recall on.
- Source and target differ in a parameter the family really varies (dial sizes, target
  values, start state, modulus), and the probe **fails closed** if any pair is not distinct or
  if a goal is already true at reset.

| | result |
|---|---|
| cases | 15 |
| source ≠ target instance | **15/15** |
| TEACH solved / COLD solved / WARM solved | 15 / 15 / 15 |
| WARM finished with fewer trials than COLD | **1/15** |
| WARM with a genuine saving (fewer trials **and** no more environment calls) | **1/15** |
| WARM reached the goal on the first trial | **1/15** |
| median trial speedup | **1.00×** |
| median act-call speedup | **0.977×** |
| total act calls, COLD vs WARM | **3027 vs 3028** |

The single win is `grid_reach` seed 1: 8 trials → 1 trial, 76 act calls → 20. That is a real
pure-recall replay on a target whose optimal plan is a prefix of what was stored. It is the
exception, and I am not going to dress 1/15 as 10/10.

### Why it costs more instead of less

Three mechanisms, each visible in the code:

1. **The prior is injected but the budget is not reduced.** `drive` passes the carried
   transition model to `environment_learning_v1.learn_model(..., prior=model)` and still burns
   the same chunked trial budget. The prior changes *which* states get explored, not *how many*
   trials are allowed.
2. **Recall spends before it saves.** The tried-and-reached-plan loop replays up to three
   stored plans through `env.act()` *before* the search starts. On a target the plans do not
   fit, that is a pure loss — visible as WARM > COLD in 14/15 act-call columns.
3. **All 15 warm cases ended under `MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED`** — including
   the 14 that are no faster. `drive` labels *any* run finishing via the carried model
   `PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN` with `transferred=True`. Read the status string
   alone and 15/15 look like transfer. They are not; the speedup columns are the finding, and
   that is why I print authority and both counters.

The corresponding honest benchmark already exists in the tree
(`canonical/tools/changed_state_transfer_benchmark_v1.py`, with a test) and I ran it too: 10
target cases, 10 cold solved, 10 warm solved, and **`direct_plan_replays: 1`** — with the same
all-1.00× trial ratios and 0.94–0.98× act ratios. The tree's own instrument has been telling
the truth. The prose in `INSTANT_LEARNING_SCOPE` §0.7 did not pick it up.

---

## 3. What is not real — the code-repair side

Taught one repair in a fresh store, then applied the stored rule to eight sources carrying the
same operator bug:

| source | result |
|---|---|
| same shape, renamed + different expression | **MATCHED** → `return a < b` |
| same shape, arguments swapped | **MATCHED** |
| `and`-embedded (`a <= b and b <= c`) | **MATCHED** → `a < b` (**correct for this case only by luck — see below**) |
| `if x <= hi:` | NO MATCH |
| `while i <= hi:` | NO MATCH |
| `[x for x in xs if x <= hi]` | NO MATCH |
| `1 if x <= hi else 0` | NO MATCH |
| `y = x <= hi` | NO MATCH |

**1 of 5 syntactic shapes, matching the published 2/5 (really 1/5) in `OPTIMAL_PLAN_20261102_V6.md`.**
The stored pattern is `[kw return][ws][hole][ws][op <=][ws][hole]` — `return` is baked into the
pattern, so the lesson reaches only the position it was taught in. The repository already knows
this and already has the fix (`narrow_rule_at_apply_time`, PR-C2, gated on
`TEST_SUITE` verification because a bare `<=` pattern also rewrites *correct* code: 8/9 bare
match, 3 of 4 correct sources silently corrupted with a weak verifier). **That gate is the
right design and it is not the same thing as "he learns all of those."**

Also visible: the `bool and` row rewrote `a <= b and b <= c` into `a < b and b <= c` and
returned a result. That is correct here, and it is exactly the class of change that a weak
caller verifier would happily accept on a source where it is wrong. The rule is a proposal, and
only a real verifier decides.

And the measured reason repetition cannot fix this, from the same document: 1 example → 6/7,
2 → 6/7, 3 → 6/7. Teaching the missed case directly still leaves `derive_operator_swap`
returning `None`. **The failure is representational, not statistical.** Doing a thing three
times does not widen the hypothesis space; only a person authoring a broader
representation does that.

---

## 4. "Anything on a computer, once" — where that actually stops

`INSTANT_LEARNING_SCOPE` states it correctly and I am not going to soften it:

- The structured half runs for real: real filesystem, real `pytest`, real `git`, real `ffmpeg`
  encodes re-measured by `ffprobe`, a GUI loop that closes end to end against a virtual
  1920×1080 desktop.
- What remains is one sentence: *pyautogui driving a real OS was never the part that was
  measured*, and `host_app_ops` still needs the VM's `libreoffice_calc`.
- The real boundary is **observation, not learning**: a compact hashable `state()` transfers in
  one trial; pixels do not. The recipe layer that would make pixels comparable is
  documented-but-not-implemented. My own probe is built on compact `state()` — which is why it
  can say something precise about the mechanism and nothing at all about a desktop.
- The advanced census is **42 served / 7 refused**, each refusal naming its own cause, and 4 of
  those 7 are priced as *fixture* defects by the tree's own classifier — so "fixing" them would
  move a count, not a capability.

A system that is 42/49 on a self-authored capability inventory, whose own benchmark says 1/10
targets transfer with a speedup, is not a system that does anything on a computer. It is a
system with real organs and an honest gap list.

---

## 5. The routing problem, which is the actual blocker

This is the part that matters most and gets the least attention. Learning something is not the
same as the system reaching for it:

- `INSTANT_LEARNING_SCOPE` §2.2: **443 rows, 11 reached.** A lesson can be learned, stored,
  verified — and the front door still does not route to it.
- `COMPUTER_CREATURE_LOOP_PROBE_20261102.md`: a gzip learning probe that works on the direct
  route **fails closed through the unified front door**. The stated blockers are an execution
  isolation boundary, a true learning-disabled control, and legitimate independent verification.
- `CODING_CREATURE_LOOP_PROBE_20261102.md`: the raw-goal repair path refuses before execution
  with `BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT`. The learner is not connected to
  the front door for repair.
- `UNIFIED_LEARNING_MEMORY_POLICY_AUDIT_20261102.md`: `learn=False` is **not** a learning-off
  switch — five named nested paths still read or write retained state. So the A/B measurement
  you would need in order to *prove* a learning gain cannot currently be run cleanly at the
  front door.

Read that together: **the strongest measured learning in this tree lives behind side doors, and
the front door is where the unmeasured parts are.** That is why every big number is a
mechanism proof and none is a product claim.

---

## 6. On the creature

Two different sentences are being run together, and separating them is most of the answer.

- **"The machine has a self-model, a causal world model, memory that changes its choices, and a
  loop that retries after failure without being asked."** True, backed by 13 passing tests
  today, and genuinely unusual. That is the measurable half, and it is real.
- **"The model is sentient."** Not measured, not measurable with anything in this tree, and
  not required by the objective. Nothing in the tree measures it; every receipt carries the
  non-claim. Asserting it would put every real number above at risk, because the laws in this
  repository exist precisely to stop an unmeasurable claim from being spent as evidence.

The objective is
`BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`,
open-ended. It does not need sentience to be true. What it needs is that the organs are wired
to the door and that the numbers hold on instances nobody tuned them on.

One thing worth flagging plainly, as a defect rather than a philosophy: the 2026-11-03 modules
are named `sentient_cognitive_core_v1`, `SovereignZeroLLMPlanner`, and the commit is titled
"endogenous self-evolution". `AGENTS.md` rule 5 bans exactly this vocabulary, and the guard
enforces it (`GRANDIOSE` regex: `singularit|omega|ultimate|supreme|sovereign|transcend|apex|…`)
— but only against **new capability registry ids**, not against module or commit names, so
these passed. The guard is right and its scope is narrower than the rule it implements. A
mechanism called "sovereign" invites exactly the claim the tests cannot support.

---

## 7. What is smartest to do, ranked by measured value

1. **Fix the warm/cold economics before claiming any transfer gain.** Cheap measures exist:
   (a) don't replay stored plans against a target you have not matched; (b) reduce the trial
   budget when a prior model is supplied rather than injecting it into a full search;
   (c) make `drive` report a distinct authority for "prior model used as a hint" versus
   "recalled plan replayed", so a status string can never again be read as a speedup.
   Success criterion, already written into the new probe and its test: **more than 1 of 15
   cases showing a genuine saving, with the cold arm still solving all 15.**
2. **Use the tree's own honest instrument, and make the prose use it.**
   `changed_state_transfer_benchmark_v1` already reports `direct_plan_replays: 1`. §0.7 of
   `INSTANT_LEARNING_SCOPE` should be corrected to say *exact-episode replay on a re-created
   instance*, and the corrected new-instance number adopted in its place. This is a
   documentation correction with a measurement behind it, not a new capability.
3. **Wire the learner to the front door, or stop measuring the learner.** The gap is routing
   (443 rows / 11 reached) plus the missing isolation boundary and true learning-off control.
   Until those exist, every additional learning mechanism increases the distance between what
   is built and what the product can do.
4. **Widen the apply-site pattern, gated on verifier strength** — the PR-C2 work already
   specified in `OPTIMAL_PLAN_20261102_V6.md`: broaden at *apply* time only, admit broad
   patterns only under `TEST_SUITE`, keep the stored pattern context-anchored. Measured
   baseline to beat: recall 2/5 → 5/5 at 0 misapplications with a sound verifier, 3 with a weak
   one. The negative control (a `CALLER_PREDICATE` caller must never receive the broad pattern)
   is the test that keeps the gate from being decoration.
5. **Attack the representation problem with route (c), not with repetition.** More examples do
   not help (1/2/3 examples all 6/7). The lawful route under
   `FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10` is a donor model used in a
   bounded *acquisition* phase, then deleted, with donor-deletion proof, frozen held-out
   qualification, and causal ownership by ablation. Repetition is measuring the wrong thing
   forever.
6. **Leave sentience alone as a word.** Keep building the five behaviours in
   `OWNER_ACTIVE_GOAL_20261018_V1.md` §5 and keep every receipt carrying the non-claim. Rename
   the grandiose module names when next touched; they cost nothing to fix and they invite the
   one claim the tree cannot back.

**What not to do:** don't take "give it a try in every environment and it learns all of it" as
a plan. It is the strategy that produced 0-of-112 on the creature's own board while the
mechanisms underneath kept passing their tests. Breadth of environments multiplies the number
of narrow lessons; it does not widen any single one.

---

## 8. Standing non-claims

Nothing here moves `0/112`, flips a family, registers a capability, or claims sentience in any
sense. The new probe and its four tests are a producer-run measurement in five constructed
environments and say nothing about GUI use, unbounded computer use, or a 10-million-line
repository. `truth.achieved` remains `false`. The repository integrity guard reports
`rules=17 violations=0` with these two files added, and the probe's own test asserts that it
never reads or writes a caller's store.
