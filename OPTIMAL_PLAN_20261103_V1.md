# The optimal plan — V1, after measuring the headroom instead of arguing it

**2026-11-03.** Supersedes the ranked list in
`INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md` §7, which was written before I
measured two of its own items. Both moved, one of them all the way off the list.

Authority: **NONE**. No capability, ownership, benchmark, terminal or sentience credit follows.
`truth.achieved` stays `false`. Spend $0. Model dependency 0.

---

## 0. The plan in one paragraph

The measured state is: capability that works, behind a door that does not reach it, on a test
suite whose current size nobody has measured since 17 October. So the smartest next move is not
to build anything. It is to **stop the two mechanisms that are quietly losing work** (`drive`
paying twice for memory; a probe that calls a re-created instance "new"), **measure the
denominator you are actually failing against** (the honest suite, 17 days stale), and then
**finish the one integration the tree has twice said is the blocker** — the learner behind the
front door. Three of those four are small. None of them is a new capability. Every one of them
has a success criterion that can be checked without believing me.

---

## 1. The eight measurements that determine the order

All produced today on `73f773d`, this sandbox, disposable state. None is independently verified.

| # | measurement | number |
|---|---|---|
| 1 | Carried lesson gives a **genuine saving** on a genuinely new instance | **1 / 15** |
| 2 | Carried plan, **planned from the carried model and verified**, on a new instance | **7 / 15** (verifies by execution) |
| 3 | Of which the **exact stored plan replays** (`authority = RECALLED_PLAN_…`) | **1 / 7** |
| 4 | Taught one boundary repair → syntactic shapes it reaches | **1 / 5** context-anchored; **5 / 5** with apply-time narrowing under a real suite |
| 5 | A weak verifier receiving a broadened pattern | **0** proposals, and the gate is enforced by `evaluate()`, not by convention |
| 6 | A Python lesson offered to Go / JS / C++ | **0** (`WHERE language=?`) — it is never consulted |
| 7 | Large-`n` behaviours already implemented but broken on `main` | **2** tests, red **before** my change |
| 8 | Honest suite baseline, currently cited | **2026-10-17**, `370005ad`, 11,754 cases / 380 failed — **17 days and ~5,000 commits stale** |

**Measurement 2 is the one that changed the plan.** Yesterday I ranked
`narrow_rule_at_apply_time` (PR-C2) as work to do. It is **already built, already gated, and
already measuring 5/5 with 0 misapplications** (`canonical/tools/pr_c2_apply_time_broadening_
benchmark_v1.py`, `test_optimal_unified_creature_and_prc2_v1.py:51`). What was missing is not
the mechanism. It is that the door never routes to it, and the one structural reason it *can't*
for the case that matters most is measurement 6.

**Measurement 2 is also the most important number in this repository right now.** The stored
lesson can already solve a new instance nearly half the time — **without any new learning, on
the memory that already exists**. `drive` does not do that. It replays exact plans, then throws
the model at a full-budget search. The capability is present; the call order is wrong. That is
the cheapest real gain available, and it costs one function.

---

## 2. The plan

### P1 — Make `drive` plan from the prior before it searches

**Why now.** 1/15 → up to 7/15 genuine savings, on memory the system already has, with no new
module and no new claim. Everything else on this list is more expensive.

**Action.** In `canonical/runtime/transfer_learning_v1.py`, after recall fails:
1. take the best carried model (already done — `prior`);
2. plan `el.shortest_plan({"model": prior, "root": <target's start key>}, is_goal)`;
3. **execute it and observe the goal**. Success → `PASS__PRIOR_PLAN_EXECUTED_GOAL_OBSERVED`,
   *one* trial, and remember it;
4. failure → keep the prior as an exploration **hint** and still reduce the budget spent on the
   unconditional chunks, so a carried model can never cost more than no model.

Also split the authority label in three, so a status string can never again be read as a
speedup: `RECALLED_PLAN_EXECUTED_GOAL_OBSERVED` (exact replay),
`PRIOR_PLAN_EXECUTED_GOAL_OBSERVED` (planned from the carried model), and
`MODEL_LEARNED_…` (searched and learned). Today all three print the same "SOLVED_BY_RECALLED_PLAN".

**Success criterion.** In `transfer_learning_new_instance_probe_20261103.py`:
`warm_genuine_saving_trials_and_acts >= 7/15`, `cold_solved == 15/15` (the cold arm may not
regress), and **no case where warm act calls exceed cold act calls**. The existing 4 tests pin
the current 1/15 as a regression floor; they must be updated *with* the new measurement, in the
open, not loosened.

**Cost.** One function, ~40 lines, plus a test update. **Risk.** A prior plan executed against a
fresh environment has side effects; it must be a resettable environment or explicitly excluded,
and any failure must be reported as an uncertain effect rather than retried. Gate the new path
on `hasattr(env, "reset")`.

**Does not claim.** That a 7/15 becomes a product. Same five constructed families; still no GUI,
still no unbounded computer.

---

### P2 — DONE 2026-11-03 — Re-measure the honest suite, because you do not know your own denominator

**Closed.** `P2_HONEST_SUITE_MEASURED_20261103_V1.md`, commit `252d05f`. Measured 16,361 cases
(15,255 passed / 984 failed); split into 48 environment, 642 regressions, 336 standing debt;
substrate restored 1/10 -> 9/10 (which removed 25 failures legitimately). The largest cluster,
233 failures in one file, is a **front-door** defect with the capability already working —
which is measurement 2's argument for P3, now with a count. `AGENTS.md` still cites the stale
baseline; the corrected text is staged for the owner at
`canonical/verification/proposed/AGENTS_MD_HONEST_BASELINE_PROPOSAL_20261103.md` because that
file is a protected path.

**Why now.** `AGENTS.md` says the 344-failure baseline *is* the backlog, "reduce it by fixing
runtime code". The cited document is from **2026-10-17**, 380 failures, and the tree has taken
~5,000 commits since. Two red tests I hit today
(`test_optimal_unified_creature_and_prc2_v1.py`, large-`n` cross-language narrowing) are
**pre-existing on `main` and were never on that list** — which is evidence the backlog is both
larger and differently shaped than the number everyone is quoting.

**Action.** Run the suite with no conftest and no pins, feed the junit XML to
`execution_guard/honest_suite_baseline_v1.py`, write a new `HONEST_SUITE_BASELINE_20261103_V1`.
Report the number including failures, per `AGENTS.md`. Do **not** touch the harness.

**Success criterion.** A dated baseline at or near the current HEAD, with a failure-bucket
breakdown, and a one-screen list of the *stopping* reasons (import error → currentness drift →
assertion), so the next session starts from fact.

**Cost.** Machine time, $0. **Risk.** ~30 min of wall clock and the temptation to "fix" tests
while measuring. Measure first, fix in separate PRs.

**Does not claim.** Any capability. It is a denominator.

---

### P3 — Give the front door a route to the learner, scoped to what is already verified

**Why now.** This is the only item that changes what a *user* experiences, and two predecessor
probes independently name it as the blocker (`COMPUTER_CREATURE_LOOP_PROBE_20261102.md`,
`CODING_CREATURE_LOOP_PROBE_20261102.md`). Today: gzip learning works on the direct route and
**fails closed at the unified front door**; the repair route refuses before execution with
`BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT`.

**Action.** Take the **one** verified-bound route (`python.software.repair.apply.verified.v1`)
and make the front door reach the retained learner **inside** PR-C2's existing `TEST_SUITE` gate
— not around it. Concretely, in this order:
1. add the missing `retained_learning` input to the frozen bound-action template through the
   legitimate admission process (it is currently dropped silently, which is why a real
   admission would still not connect the loop);
2. route only when `required_verification_kind == 'TEST_SUITE'` **and** a real
   `ProjectTestOracle` is supplied — the same gate that already measured 0 weak-verifier
   proposals;
3. keep the fail-closed behaviour everywhere else, and make each refusal name its cause.

**Success criterion.** One held-out task, three fresh processes: teach → restart → recall, all
three with an external byte-level audit, `edited_tests=[]`, and a *negative* control (learning
off) that must **fail** to solve it on the first trial. If the negative control also solves it,
the test measured nothing.

**Cost.** The expensive one: it needs an independent verifier (a different person or an
independent carrier) for the receipt, per `AGENTS.md` rule 4. **If that cannot be obtained, stop
at step 1 and say so** — do not fabricate the verifier, and do not merge the route.

**Does not claim.** General routing. 8 of 149 verified rows served by the SWE census remains
true, and §2.2 of `INSTANT_LEARNING_SCOPE` is right that the routing claim is a *hypothesis*
until held-out sentences exist that are authored from something other than a row's own triggers.

---

### P4 — Build the routing instrument before touching routing again

**Why now.** Everything in P3 and in §2.2 is blocked on the same missing artefact: **a held-out
sentence set that is not derived from the rows' own triggers.** Without it, any routing change is
measured by keyword matching — the exact self-contamination that produced a false 9/9 earlier in
this work. The 294 `RECEIPT_BACKED_PENDING_PROMOTION` rows are evidence records, not routable
capability; the honest denominator is **149**, and 8 of those serve the whole SWE census.

**Action.** Author (person, not generator) ~40 natural-language sentences for a declared subset
of the 149, with the contamination control stated up front: a sentence may not reuse any token
from the target row's `id`, `provides` or `triggers`. Freeze it. Report routing recall/precision
against it **before** changing any ranking code.

**Success criterion.** A frozen file, a stated control, and a number for the *current* tree.
Whatever that number is, it becomes the baseline P3 and any future router must beat.

**Cost.** An hour of careful writing, and it cannot be automated — `provides` contains only the
id for most rows, so mechanical paraphrase returns nothing usable (measured: 0/40).

---

### P5 — Cross-language carry: one bounded bet, or explicitly defer

**Why now.** Measured today: a Python lesson is **invisible** to Go/JS/C++ (`WHERE language=?` —
never consulted, not refused). `allow_cross_language` exists in the signature and cannot help,
because the row is filtered before the flag is read. Yet the lesson itself — "`<=` → `<` at a
boundary" — is language-independent, and the crystallizer already carries a multi-language
keyword set.

**Action — the cheap version, and it is genuinely cheap.** Make `language` a *ranking* input
rather than a *filter*: `WHERE domain='swe_code_repair' ORDER BY (language=?) DESC, verified_hits
DESC`. A rule from another language then becomes a **proposal that must survive the caller's
verifier**, which is exactly the architecture the tree already trusts (broad retrieve, verify
narrow). Add the negative control: a Go caller with a weak verifier must receive **0** foreign
proposals.

**Success criterion.** Taught in Python, applied and verified in Go on a held-out instance; and
0 foreign proposals under `CALLER_PREDICATE`. If the second number is not 0, the change is unsafe
and must be reverted, not tuned.

**Cost.** Small. **Risk.** This is the one item where a widening could regress the 0-misapplication
result. That is why the negative control is the primary criterion, not the positive one.

**Defer instead if** P1's criterion is not met — a system that cannot use memory it already has
does not need more memory.

---

## 3. What is deliberately not on this list

- **"Give it a try in every new environment."** Measured false as a strategy: no probe in this
  tree transfers to a genuinely new instance faster than no memory at all (1/15), and no evidence
  anywhere says the *transfer* rate rises with the corpus. Breadth multiplies; it does not
  generalise. This plan spent a whole measurement cycle earning that sentence.
- **Cron / unattended running.** Running something unattended that closes 0/112 accumulates
  honest failure faster. Nothing here changes what it would close.
- **New capabilities, new organs, new registrations.** At most 3 per PR by law; the binding
  constraint is not supply. `test_sentient_cognitive_core_v1` passes 13/13 today and it did not
  move a single product number.
- **Model-in-the-loop at solve time.** Prohibited under
  `FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10`, and renaming it does not
  change its class. Not priced, because it is not available at any price.
- **Sentience, as a claim or as a target.** No instrument measures it; the objective does not
  require it; asserting it would discount every real number above.

---

## 4. The one plausible path to a big jump, stated honestly

The real frontier is named precisely in `INSTANT_LEARNING_SCOPE` and I will not pretend a
different one exists: **the machine authors a lesson's scope, but a person authors the hypothesis
space.** `rule_scope_learning_v1` narrowed 7/7 within a space *I* wrote; making `a < b or a == b`
representable as `a <= b` required a human to see it.

The lawful attack is route (c) of the internalization lock: a donor model in a **bounded
acquisition phase** that produces a Brain-owned mechanism, then is **deleted**, with
donor-deletion proof, frozen held-out qualification, and causal ownership by ablation (all 12
conditions). That is the only permitted way to widen the hypothesis space without model
dependence at solve time — and it is a multi-session project, not a step in a plan.

**Do not start it until P3 is done or definitively blocked.** Widening the space inside a
system whose door does not route to its own lessons would produce a beautifully general learner
that nothing calls — which is exactly the failure mode `select_probe` had (present, correct,
tested, and called by nothing).

---

## 5. Order, in one line each

1. **P1** stop paying twice for memory — one function, measured floor 1/15 → target 7/15.
2. **P2** re-measure the honest suite — you cannot reduce a backlog you have not counted since 17 Oct.
3. **P4** freeze a held-out routing sentence set — an hour of writing that unblocks P3 and every future router.
4. **P3** connect the front door to the learner, inside the existing `TEST_SUITE` gate — needs an independent verifier or it stops.
5. **P5** cross-language ranking, negative control first — or defer behind P1.

P1 and P2 can run in the same session and are the only two that are both cheap and certain.
P3 is the only one that changes what a user sees. P4 is the only one that stops future
measurements from lying.

---

## 5b. P1 and P2, closed — the delta in numbers

| measurement | before | after |
|---|---|---|
| carried model, genuine saving on a new instance | 1/15 | **8/15** |
| carried model, one trial | 1/15 | **8/15** |
| worse on trials | — | **0/15** |
| second benchmark, one trial | 0/10 | **6/10** |
| honest suite cases / failed | 11,754 / 380 (17 days stale) | **16,361 / 984** |
| failure split | unknown | 48 environment / 642 regressions / 336 debt |
| substrate modules present | 1/10 | **9/10** |
| fingerprint cache policy | FIFO — lost keys read 20x | **LRU, pinned by 5 tests** |

The fourth line of the backlog split is the one that changed the plan: **642 failures are
regressions against a tree that was clean four weeks ago**, not standing debt, and 233 of them
are a single door defect whose capability already works.

## 6. Standing non-claims

Nothing here moves `0/112`, flips a family, registers a capability, or claims sentience. The
numbers in §1 are a single-machine producer-run measurement of five constructed environments and
a partially-read test suite; they are not independent verification. The 7/15 in P1's criterion is
a *target*, not a result — it is the ceiling measured by planning from the existing model before
any code changes, and the plan does not claim it will be reached. `truth.achieved` remains
`false`.
