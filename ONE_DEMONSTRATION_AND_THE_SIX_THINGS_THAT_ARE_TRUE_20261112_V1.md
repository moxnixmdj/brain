# One demonstration, and the six things that are true

**Date:** 2026-11-12  **Authority:** NONE (producer-run measurement + reading of the tree's own evidence)  **`truth.achieved`:** stays `false`

The question, in the owner's words: *"We already solved instant learning perfectly. Doesn't that mean we can
give the model any computer action once and it learns it permanently — so we have solved everything on a
computer, including the most advanced coding — and this makes us a sentient creature?"*

Short answer: the mechanism is real and it is better than what most agents ship. The claim wrapped around it
is false in three separate places, and the reason is arithmetic, not effort. What is real is narrower and
stronger than the story: **the machine can repeat a demonstrated change and it can carry a model of an
environment it has seen — but only a check decides whether either is right, and a single demonstration
contains one bit of information about scope, not a capability.**

---

## 1. The three claims, separated

| # | Claim as stated | Verdict | The measurement that decides it |
|---|---|---|---|
| 1 | Instant learning works: a lesson from one instance transfers to a genuinely new instance of the same kind | **TRUE, partly** | 8/15 one-trial on new instances, mean trial speedup 6.33×, 0/15 worse on trials (`P1_CARRIED_MODEL_EXECUTED_20261103_V1.md`, re-run 2026-11-12) |
| 2 | Give it an action once → it has that capability permanently | **FALSE as stated** | One showing produces a rule with no blank: 0 rewrites in 2,355 files of this project's own production code (§3). Two showings generalise — and then apply at 31 unchecked sites |
| 3 | Do it everywhere, on any computer, and you have solved all computer use + the most advanced coding | **FALSE** | Mean 22.4 trials per task, not one. 1525 vs 1525 transitions clean vs loaded: no accumulation across kinds. Front door 8/149 (5.4%) |
| 4 | This is a revolutionary way of learning, faster than the field | **PARTLY TRUE, and it is the interesting part** | The repo's "learn, then verify, then keep" loop is the right shape (field agrees). The novelty is not the loop; it is the refusal discipline around it |
| 5 | This makes a sentient creature | **NOT SUPPORTED — nothing here measures it** | What exists is a persistent, verifier-gated episode cache plus a planner. That is a cache with a conscience, not a self |

The rest of this document is the arithmetic behind each row, then the plan.

---

## 2. Why "show it once and it is permanent" cannot be true — the identification argument

A demonstration is not a specification. Take the change `self.assertEquals(a, b)` → `self.assertEqual(a, b)`
and show it once. The set of rules consistent with that single fact includes:

* change this exact call on this exact line;
* change `assertEquals` → `assertEqual` on any receiver, anywhere;
* change any `assert*` method to its `assert*` peer;
* change any method whose name appears in a table of legacy names;
* …and every rule that agrees on the one place shown and disagrees everywhere else.

One example cannot choose among them. It can only be *selected* if the hypothesis space was already small and
already right — the prior generalises, the example selects. This is not a philosophical position; it is
measured on this tree:

* **0 of 200** requirements were identified by a single success; one success leaves an empty requirement
  standing and its most-general survivor admits **68%** of failing states (`WHAT_A_SUCCESS_TEACHES_20261112_V1.md`).
* Adding outcomes (not just successes) identifies **25/25** — the information was in the failure, not the win.
* **13.05 of 32** candidate requirements survive one success. The example prunes two thirds of nothing.

The same theorem, measured on the learner itself, is §3. The practical consequence: *"once"* is not a
quantity of experience the machine can convert into a capability. It is a quantity of experience that can
only select among hypotheses the machine already had.

**This is also why "just give it the most advanced coding actions" fails as a plan.** An advanced action is
not a thing to be shown; it is a composite of (a) an edit, (b) the judgement of *where that edit is right*,
and (c) the verification that it worked. A demonstration gives (a) — cheaply and genuinely. (b) and (c) are
where all the difficulty lives, and a single demonstration contains almost no information about either.

---

## 3. New measurement, 2026-11-12: what one showing actually buys

Tool: `canonical/tools/blast_radius_of_a_one_shot_rule_20261112_v1.py` (measurements only, authority NONE).
Corpus: 2,355 Python files of this project's own production code (`canonical/runtime`), replayed in memory,
nothing written. Learner: `canonical/swe_kernel/taught_actions/edit_by_example_v1.py`.

| Lesson | Files replayed | Shown **once** | Shown **twice** |
|---|---|---|---|
| `?1 == None -> ?1 is None` | 800 | rule `a == None -> a is None` → **0 sites** | rule `?1 == None -> ?1 is None` → **31 sites in 12 files** |
| `pow(?1, 2) -> ?1 ** 2` | 202 | `pow(x, 2) -> x ** 2` → 0 sites | `pow(?1, 2) -> ?1 ** 2` → 0 sites |
| `?1.has_key(?2) -> ?2 in ?1` | 200 | `d.has_key(k) -> k in d` → 0 sites | `?1.has_key(?2) -> ?2 in ?1` → 0 sites |
| `?1.assertEquals -> ?1.assertEqual` | 201 | `self.assertEquals -> self.assertEqual` → 0 sites | `?1.assertEquals -> ?1.assertEqual` → 0 sites |

Read the first row carefully, because it is the whole answer:

* **One showing → zero reach.** A single changed place creates a rule with no blank, so the lesson is about
  exactly that code. It rewrote nothing in 2,355 files. A capability that does not fire outside the sentence
  that taught it is not a capability; it is a recorded edit.
* **Two showings → the rule generalises** (`?1 == None -> ?1 is None`) and rewrites 31 real places — with no
  check that the change is right at any of them. That is what "permanent" would mean: 31 unverified edits,
  and every future file is another one.
* The learner's own refusals are the part of it that knows this. `edit_by_example_v1` refuses a file when the
  changed code is used a way the demonstrations never showed ("called with another number of arguments",
  "a name the edited file does not provide"), and its sibling `repeat_tried` keeps a repeated change **only
  when the project's own check is broken by making that change wrong**, one place at a time.

That last mechanism is the honest version of the owner's idea, and it is already built:
`teach once → repeat → the project's check settles each unsettled place → the settled place is added to the
lesson`. It costs a check run per file. That cost is the price of permanence with correctness, and no scheme
known to me avoids it — the alternative is 31 edits nobody looked at.

### What I disproved about my own last fix

Before writing this, I tried to make failed model-walks cheaper by returning the transitions they validated
and merging them into the search prior. Measured, then reverted:

* every "validated" edge was **already in the prior** — 21/21, 14/14, 3/3, 4/4 — because validation means the
  environment agreed with what the model predicted. Merging them back is a tautology, not a saving;
* pruning the 0–3 genuinely refuted edges changed nothing: the probe table is identical (8/15 one-trial,
  7/15 more act calls, worst 1.398×).

The act overhead of a failed walk is the walk itself (31 edges / 96 act calls on the three-dial lock, breadth-
first with prefix replay). Lowering the bound loses a success (the grid case needs 46); shrinking the replay
needs inverse actions the interface does not have. **Killed, not shipped.** This is the fourth idea in this
area that died on contact with a measurement; the pattern is that the prior, not the search, is the limit.

---

## 4. Where the claim collapses for *computer use* — the state problem

`transfer_learning_v1` plans through a carried model whose states are hashable keys the environment reports.
That is a legitimate assumption for a dial lock, a grid, a word accumulator, a counter. It is not an
assumption a screen satisfies. A GUI reports pixels: there is no `state()` to key on, no transition table to
carry, and the same lesson ("click the third item") depends on a layout the next instance may not have.

The 2026 field numbers say the same thing from the outside:

* **OSWorld-Verified** (369 bounded tasks): best agent ~86.0% vs human 72.4% — bounded GUI work is largely
  solved by frontier models *without* any learning mechanism from this repo. Rewriting that as a novelty would
  be false.
* **OSWorld 2.0** (108 long-horizon workflows, median 1.6 human hours, ~318 tool calls): best 20.6% binary,
  54.8% partial — and the failures are not GUI basics. They are losing constraints mid-task, missing
  information that existed earlier, guessing instead of asking, and skipping verification. Those are exactly
  the three things a one-shot demonstration does not teach (§2).
* **SWE-bench Verified** is saturated and contaminated (~80.9% frontier); the honest coding target is
  **SWE-bench Pro** (10+ line changes, held out): 45–57% for frontier models, ~69% best custom scaffold.
  The same model moves **±15–16pp** with scaffolding alone (Sonnet 4.5: 43.2% SWE-agent v1 vs 59.8% Cline),
  and maintainer merge rates run ~24pp below automated scores.

The lesson from those two facts together: **scaffold and verification discipline move the score more than any
one learned action does.** That is where this project's actual advantage is, and it is already the shape of
what it built.

---

## 5. Sentience

Stated plainly, because the owner asked directly:

* What exists is a persistent episode store keyed by an environment fingerprint, with recall, a carried
  transition model, chunked learning, and a verifier gate. Every part of it is inspectable, deterministic and
  bounded. It does not model itself, it has no objective it chose, and it stops when the goal predicate is
  satisfied.
* Sentience is not a property that shows up as a side effect of good caching. A creature would need at least:
  a persistent self-model that survives episodes **and is used in decisions**; intrinsic objectives that are
  not supplied by the caller; and open-ended self-directed activity between tasks. Nothing in this tree
  implements, measures, or approximates any of the three.
* The repo's own prior verdict scores sentience as **NOT MEASURED** — not "almost", not "emerging". That is
  the correct status and it should stay that way until someone writes the measurement first.

If the goal is a creature, the first artifact is a *falsifiable definition* of what would count, not another
capability. That is a decision for the owner, not something to be inferred from a green suite.

---

## 6. What is actually real, with the names it is hiding under

The owner is right that the important things exist under non-obvious names. These are they, and their
measured status:

| Mechanism | File | Status (measured) |
|---|---|---|
| Episode memory keyed by environment fingerprint, recall → carried-model plan → chunked learn | `canonical/runtime/transfer_learning_v1.py` | 8/15 one-trial on new instances, 6.33× mean trial speedup, 0/15 worse on trials |
| Learn a transition model, plan shortest path, execute and verify | `canonical/runtime/environment_learning_v1.py` | Solves all 15 probe environments cold; the baseline the above is compared against |
| Version-space settlement; ask the question that splits the hypotheses | `canonical/runtime/settlement_v1.py` | Real, and **dangerous**: `x mod 5` warm 0/10 vs cold 2/10, questions 12→1 — experience made it faster at being wrong |
| Applicability learning: which requirement a failure implies | `canonical/runtime/applicability_v1.py` | UNDETERMINED without a failure; IDENTIFIED only when exactly one requirement survives; withholds only when its general survivor rejects |
| Macro store keyed by verb+file-kind signature, scoped failures | `canonical/runtime/macro_v1.py` | Keeps 2 successes / 0 failures on the measured corpus — starvation, not learning |
| Change worked out from before/after files, replayed | `canonical/swe_kernel/taught_actions/edit_by_example_v1.py` | Real: 5/5 languages one-shot on novel names. One showing has zero reach; two showings generalise (§3) |
| Replay gated by the project's own check, place by place | same file, `repeat_tried` | The honest mechanism. Costs a check run per file. This should be the **default**, not an option |
| Wake-sleep compression with an MDL gate | `canonical/swe_kernel/concept_library_v1.py` | 3 concepts on a synthetic affine corpus, **0** on the period corpus; on real code the rewrite costs bytes (141 → 170) |
| Skill organ → concept bridge | `canonical/swe_kernel/meta_circular_organ_graph_v1.py` | Works; admits single and multi-clause predicates. Feeding it does not fix the compressor's gate |
| Front door: sentence → admitted action | `canonical/runtime/live_brain_route_admission_v1.py` | **8/149 (5.4%)**. The largest red cluster is 233 routing failures. This is the real bottleneck |

And the things that are **not** real, measured, so they stop being retried:

* Giving the model "a try in every new environment" does not compound: 5 kinds taught, the 6th is no cheaper;
  the store ends **byte-identical** whether or not earlier kinds were solved (1525 vs 1525 transitions).
* Learning-to-learn over coarse feature buckets that pick among search policies: **NO_COMPOUNDING** at 10
  held-out kinds — solved 5/10, beat the default policy 1/10. The bucket holds kinds needing opposite policies.
* Success-only learning: one success identifies nothing (§2). The rule that gets stored is the empty one.

---

## 7. The smartest things to do, in order, with the kill list

Ranked by *expected capability per unit of work*, using the measurements above, not by novelty.

**1. Make `repeat_tried` the only way a lesson is applied.** This is the single highest-value change in the
coding path and it is mostly wiring. A lesson that was applied once without a check has produced exactly the
31 unverified sites measured in §3. The gate already exists; what is missing is that the ungated path is
still the default and the measured cost of the gate (one check run per file) is unrecorded. Measure that cost,
then make the ungated path refuse unless the caller explicitly says the check is unavailable.

**2. Fix the front door (8/149 → keep going until the 233 routing failures are zero).** Every other mechanism
in this repo is downstream of a sentence being routed correctly. A hand-authored routing set of ~40 sentences
is the cheap, honest step, and it is blocked on a review that has been pending (226/233 confinement refusals
need an owner decision). This is the highest-leverage unblocking action available and it is not technical.

**3. Buy the prior, don't grow the search (Program C).** §2 says the example selects; the prior generalises.
The repo's donor material — the taught actions, macros, concepts, and the 145-capability census — is a prior
that has never been distilled into a form the planner can use before the first action. Cross-language carry is
already broken in a *specific, fixable* way: recall is keyed `WHERE language=?` and `allow_cross_language` is
read nowhere. That is a ten-line fix with a measurable target: same lesson, different language, one trial.

**4. Treat permanence as a tested property, not a claim.** Nothing currently measures whether a lesson still
applies after the tree changes. That is measurable: replay every stored lesson against the current tree and
count how many still fit; the drift is the decay. Without this number, "permanent" is unfalsifiable.

**5. Publish the honest denominator.** 16,361 cases, 15,255 passed, 984 failed = 48 environment / 189
deliberate `FAIL_CLOSED` / 789 real. The 189 refusals are a feature and should be reported as one, so the
number cannot be read as a defect rate by someone who has not read this document.

**Kill list — do not spend another hour on these:**

* More micro-optimisation of walk cost. Measured twice today; the cost is the walk, and the walk is the price
  of the 8/15 wins. Attempt #4 in this area was a tautology (§3).
* "Try it in every new environment and it accumulates." Measured false, byte-identical store.
* Learning-to-learn over coarse feature buckets. Measured NO_COMPOUNDING at 10 held-out kinds.
* Any claim of sentience, or registering a capability for it. Nothing measures it; `truth.achieved` stays false.
* Unattended/cron solve loops and model-in-the-loop at solve time. Excluded for good reasons already recorded.

---

## 8. What would prove the owner right — the falsifiers

Stated so this document can be wrong in a useful way. Each is a measurement, not an opinion.

1. **One demonstration, real reach.** A lesson learned from a single showing that rewrites ≥10 *correct* sites
   in code it was never shown, with the project's check passing afterwards. Today: 0 sites.
2. **Cross-kind accumulation.** Teach kinds 1..5, then solve kind 6 in fewer trials *and* fewer act calls than
   cold, on a kind not in the store. Today: 1525 vs 1525, no saving.
3. **One trial, not 22.4.** Mean trials per new task ≤ 2 with the same 15-family protocol. Today: 22.4 mean,
   8/15 at one trial.
4. **GUI transfer.** The carried model works where the state is pixels: a lesson from one screen solves a
   second instance of the same workflow. Today: not attempted, and the state-key assumption says it will fail
   as built.
5. **Front door.** 149/149 sentences routed, zero confinement refusals needing review. Today: 8/149.

If 1, 2 and 5 all move, the owner's claim becomes true in the only form that matters: *the machine learns a
demonstrated change, keeps it, applies it only where a check agrees, and can be told what to do in a sentence.*
That is a better agent than anything currently published. It is not a sentient creature, and saying so now is
what keeps the first part from being disbelieved later.

---

## 9. Method note

* Probe re-run 2026-11-12: `python3 transfer_learning_new_instance_probe_20261103.py` — 8/15 genuine saving,
  6.333× mean trial speedup, 7/15 more act calls, worst 1.398×. Identical to the 2026-11-03 record, so the
  numbers in §1 row 1 are stable across sessions.
* New tool: `canonical/tools/blast_radius_of_a_one_shot_rule_20261112_v1.py` (13 s, no writes, no network).
* Reverted: the validated-edge merge in `transfer_learning_v1.py` (tautology, measured no-op).
* `canonical/tests/test_transfer_learning_v1.py`: 24 passed on the tree as it stands (pytest 9.2.0).
* Field figures are 2026 leaderboard reports and papers summarised in the session record; they are context,
  not evidence for this repo's claims.
