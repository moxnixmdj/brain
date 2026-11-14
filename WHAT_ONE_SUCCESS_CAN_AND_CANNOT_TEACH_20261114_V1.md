# What one success can and cannot teach — 14 November 2026

Authority: **NONE**. Producer-run sandbox measurement and repair on branch `arena/b64c7c36-brain`,
base `cfb7947011d4f060d15b0165b8a679bff61bc0b0`. No capability registered, no family flipped, no
weight updated, `truth.achieved` unchanged. Independent verification is open.

## 1. The claim under test

> "Instant learning and instant learning in new arbitrary environments are already solved perfectly.
> So show the agent any action once and it knows it permanently — therefore all computer use and the
> most advanced software engineering are solved."

The direction is real. The word **once** is false, and this repository already proved it false.

## 2. The capability evidence: a real open benchmark, held out, no model

Synthetic probes cannot settle a capability claim. This one was run on **MiniWoB++**
(Farama-Foundation, MIT, upstream `33c3b4ddef8c6eb67c57a29663d844b1eda7e614`, 130 real task pages),
on the **held-out split** — the 92 tasks that were *not* looked at while the arms were built. The
judge is each page's own reward. The solver is this repository's own code:
`producer_cognition_model_dependency_count = 0`, external model calls 0, spend $0.

Protocol: find one success on one instance by the system's own exploration, then get one try on each
of 20 **unseen** instances of the same task.

```text
92 held-out tasks
  demonstrated even once          40
  never demonstrated              52   (36 no first success, 11 page does not run, 5 unstable seed)
  fixed replay already solves      5
  tasks that NEED generalisation  35   <- the only ones that test the claim
```

Mean success rate **on the tasks where replay is not enough** (800 episodes per arm):

| arm | success | tasks at 100% | tasks at 0% |
|---|---|---|---|
| random | 8.1% | 2 | 16 |
| verbatim — what a cache does | 15.0% | 5 | 11 |
| existing compiler (this repo's own) | 18.9% | 7 | 19 |
| **version_space — one success** | **60.0%** | **20** | **1** |
| blind control (cannot read the instruction) | 20.0% | 5 | 7 |
| **version_space + 3 practice instances** | **66.1%** | **21** | 2 |

**What this proves.** The mechanism is real and large: one success generalises to unseen instances
**4× better than a cache** and **3.2× better than the repo's own previous generaliser**, with no
model and no spend. The blind control collapses to 20%, so most of the gain is genuine grounding in
the instruction, not memorised clicking.

**What it disproves.** "Solved perfectly / permanently / anything on a computer" is false. One success
yields **60%**, not 100%. **52 of 92** tasks could not be demonstrated even once. And three extra
instances buy only **+6.1 points** — exposure alone has sharply diminishing returns, exactly as the
information argument predicts.

Receipt: `canonical/verification/OPEN_BENCHMARK_ONE_SUCCESS_GENERALISATION_20261114_V1.json`.
This is **not a leaderboard entry**: the demonstration is found by exploration against the page's
own reward, which a leaderboard agent is not given. Substrate limit: jsdom has no layout, so 11 pages
did not run and geometry-dependent tasks are not faithfully represented.

## 3. The information-theoretic bound (a synthetic instrument, and labelled as one)

The instrument below is **exhaustive but synthetic** — it enumerates hidden requirements over
constructed fact sets. It is a mathematical bound on what any learner can infer, **not** capability
evidence. The capability evidence is the open benchmark in §2. Run on this tree (zero model, $0):

```text
A. ONE SUCCESS  (200 exact cases)
   hypotheses still consistent          13.05 of 32
   bits left unresolved                 3.40
   cases identified by one success      0 / 200
   most GENERAL survivor says 'applicable' where it FAILS   68% of states
   most SPECIFIC survivor says 'inapplicable' where it WORKS 21% of states
   every case leaves a survivor that is wrong somewhere     200 / 200

B. SAME LEARNER, OUTCOMES INCLUDE FAILURES + CHOSEN CONTRASTS  (25 cases)
   identified exactly                   25 / 25
   mean demonstrations                  2.76
   worst case                           4
   concluded a WRONG requirement        0

C. WHAT THE MACHINE ACTUALLY RECORDS
   macros stored                        3
   successes / failures recorded        3 / 0
```

This is not an opinion about the design. It is the repository's own exhaustive instrument.

**Why one success cannot be enough, from first principles.** A demonstration is one point. The skill
is a *rule*, and many rules pass through one point. The instrument counts them: 13.05 of 32 survive.
Nothing in the demonstration distinguishes them, so choosing one is a guess. The guess is not even
close: the general reading is wrong on 68% of states, the specific reading on 21%. Replay works on
the demonstrated instance because it is a cache; it fails on the next instance because the rule was
never identified.

The repo states this in its own code. `demonstration_version_space_v1`: *"Either may be right; from
one success neither can be known to be."* `contrast_selection_v1`: *"the first experience is a point,
and further identical points are the same point."*

**The real optimum is not "once". It is ~2.76 well-chosen experiences.** That is not a compromise;
it is the information-theoretic floor made practical. You cannot beat the bits — 3.40 bits of
ambiguity do not vanish because a demonstration was vivid. You *can* stop wasting experiences:
repeating a success in the state it already worked in has exactly zero information gain. Choosing
the contrast kills the most survivors per attempt. That is the fastest possible route, and it is
already implemented here.

## 4. The single bottleneck, located

Not storage. Not retrieval. Not model size.

**The live loop was throwing away the state each outcome happened in — the only thing that carries
identifying information.**

`macro_v1.record(...)` and `macro_v1.note_failure(...)` both accept `context`, and
`applicability_v1.learn` identifies a requirement from `(state, outcome)` pairs. But:

| live call site | passed the state? |
|---|---|
| `chain_v1.py:246` | yes — `context=preconditions` |
| `live_brain_route_admission_v1.py` (front door) | **no** |
| `closed_loop_autonomous_controller_v1.py` (confined trajectory) | **no** |
| `forged_binding_and_macro_spine_v1.record_verified_chain_macro` | **no — dropped it entirely** |

`record(context=None)` writes **no evidence row at all**. So the live store held 3 successes, 0
failures, and no states — permanently `UNDETERMINED`. The machinery for the 25/25 regime existed and
worked; the live loop fed it the 0/200 regime. That is why "it did it once" never became "it knows
where it applies".

This is the highest-leverage defect available: it is upstream of every learner, every skill library,
and every future weight update, because all of them consume this evidence.

## 5. What was changed

No new organ. One information loss deleted, and existing organs connected. ("The best part is no
part.")

1. `record_verified_chain_macro(..., context=None)` forwards the state to `macro_v1.record`.
   Omitted → exactly the previous behaviour, so no caller is forced to change.
2. The front door snapshots the pre-state **before the first side effect**, using
   `chain_v1.precondition_context` — the sanctioned probe organ that deliberately refuses the effects
   the plan itself produces. Using post-state would teach the circular rule *"this plan requires what
   it creates"*, which looks perfectly identified and then withholds the plan everywhere.
3. The confined-trajectory controller does the same.
4. Both outcomes now carry the state: success into `record`, failure into `note_failure`.
5. New `verified_chain_learning_receipt` surfaces, read-only, what the evidence licenses and which
   reachable state would teach the most (`macro_v1.next_contrast`). A caller that only sees
   `recorded: true` cannot tell "reusable anywhere" from "scope still unknown".

### Measured after the change, through the live front door

Real compound goal, real execution, isolated store:

```text
status:                 PASS__COMPOUND_SWE_MULTI_STEP_VERIFIED
preconditions_observed: ['python.source.file.available', 'python.test.corpus.available']
evidence rows:          1  (was 0)
applicability:          UNDETERMINED__NO_CONTRASTING_OUTCOME
reason:                 NO_FAILURE__NECESSITY_IS_ONLY_REFUTED_BY_FAILURE
next_contrast:          NO_REACHABLE_STATE_SPLITS_THE_SURVIVORS
discriminating_facts:   ['python.source.file.available', 'python.test.corpus.available']
```

The door now says the true sentence: *"I did this once; I do not yet know where it applies; here is
exactly what would have to differ to find out."* Before, it said `recorded: true` and nothing else.

## 6. What is real, and what is not

**Real, and measured on held-out open tasks with no model (§2):** one success generalises to unseen
instances at **60%** where a cache gets **15%** and the previous compiler **18.9%**; 20 of 40
demonstrated tasks reach 100% on unseen instances; the blind control falls to 20%, so the gain is
grounding, not memorised clicking. Also real: exact-information-gain contrast selection; JIT external
knowledge with no parameters; an admission gate that rejects a lesson which breaks a correct program.

**Not real:** "once ⇒ permanent correct generalisation" — it is 60%, and **52 of 92** held-out tasks
could not be demonstrated even once; "any computer task" (no admitted general effect carrier is wired
to the door); a sentience result; independent verification of this change.

**Also not evidence:** the eight plumbing tests in this PR. Their fact names are invented. They prove
a value is forwarded, nothing about capability. They are labelled as such in the file itself.

**Sentience.** Nothing here measures it. Modules named `sentient_*` are names, not evidence. The
honest claim is about identification, verification and authority — not experience.

## 7. Why this is the advanced answer, not the incremental one

The ordinary answer is "collect more demonstrations" or "fine-tune on the successes". Both are
strictly worse: repetition in the same state has provably zero gain (0/200), and training on
unidentified successes stores the 68%-wrong general reading as if it were knowledge.

The advanced answer is to treat learning as **experiment design**: keep the whole version space,
report the ambiguity honestly, and spend the next experience where it is guaranteed to eliminate the
most hypotheses. That converts an unbounded "keep showing it things" into a bounded, measurable
2–4 chosen contrasts. It is faster *and* it is the only version that can know when it is done.

This matches where the frontier landed in 2026, and the agreement is corroboration, not authority:
FGSE gates committed lessons on transfer + falsification + archived regression; SkillOpt accepts only
edits that improve a held-out split (1–4 accepted edits, ties rejected); Skill-V makes skills
falsifiable contracts; Veritas and VerifierBench make the point that most real tasks arrive **without
a verifier**, which is the same bottleneck seen from the other side.

## 8. Weights, and "every bit must be calculated"

This result gives that instruction an operational meaning. A parameter is justified only by evidence
that **identifies** it. An unidentified survivor is not knowledge; it is one of 13 readings that
happen to fit. Storing it in weights is exactly the "knowledge house" the owner rejects — and it is
worse than storing nothing, because the general survivor is wrong on 68% of states.

So the order is forced, and it is the same order the memory path needs:

```text
outcome + state -> chosen contrasts -> identified requirement -> admitted artifact
-> only then consolidation into weights, from identified evidence only
```

Parameters then carry *procedure and composition*, not facts; facts stay in instant external
knowledge. That is the resource-efficient design, and it is not a compromise against the weights
approach — it is the condition under which weights are worth their compute.

## 9. Honest limits of this change

- The failure side is only recorded when the plan was **recalled** and then failed inside the
  transactional DAG. A goal refused by an earlier guard never reaches the recorder. Measured: deleting
  the source file produced `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` on a different route and wrote no
  evidence row. That is a real remaining seam, reported not hidden.
- `precondition_context` returns `None` when the probes cannot decide a fact. Then behaviour is
  exactly as before — fail-open, no invented discriminator.
- One pre-existing failure reproduced at base in the affected set:
  `test_incremental_semantic_graph_and_swe_upgrades_v1::test_navigation_and_complexity_deliver_answers`
  (confinement refusal on "Show me the definition of Derived"). Not caused by this change, not fixed.

## 10. Test ledger — real counts

```text
New seam suite (canonical/tests/test_an_outcome_keeps_the_state_it_happened_in_v1.py)
  with the fix                       -> 8 passed
  with the defect re-introduced
  (context dropped in the wrapper)   -> 3 failed, 5 passed
  against the base wrapper           -> collection error (helper absent)

Affected set: new suite + chosen-contrast + skill-scope-acquisition
              + redundant-literals + incremental-semantic-graph/SWE upgrades
  this tree -> 1 failed, 71 passed
  base      -> the same single failure, reproduced
```

The falsification run matters more than the pass count: removing only the context forwarding makes
three tests fail, so they test the defect rather than the shape of the code.

## 10b. The next bottleneck was tested, and the smart-sounding answer lost

Ranked item 2 above said: let a scheduler seek the discriminating instance instead of accepting
whatever arrives. The 2026 literature agrees unanimously — greedy-minimax / query-by-committee over
the surviving version space is the known-optimal way to choose (Socrates, PLDI 2026; FlashProg;
SampleSy/SmartLabel; Tong & Koller). It was built and measured on the same real held-out split,
same 92 tasks, same 20 scored episodes, same action budget, 0 model calls, $0.

**It bought nothing.**

| policy | demonstrations spent | overall | where replay is not enough |
|---|---|---|---|
| one success only | 0 extra | 0.6500 | 0.6000 |
| accept 3, arrival order | 120 | **0.7038** | **0.6614** |
| choose 3 of 9 by committee disagreement | 120 + 360 page reads | 0.6987 | 0.6557 |
| decline instances the committee agrees on | 55 | 0.6588 | 0.6100 |

Choosing tied accepting: two tasks better, two worse, a 0.5-point difference for 360 extra page
reads. And the aggressive version — the one the theory recommends, refusing to pay for an instance
that cannot eliminate a hypothesis — was **worse than doing nothing smart at all**, while spending
54% fewer demonstrations.

**Why the theory failed here is the useful part.** A committee cannot vote on a hypothesis none of
its members holds. Query-by-committee measures disagreement *among the survivors*; it is blind to
the case where every survivor is wrong. That case is the largest information gain available, and
only trying the instance reveals it. Every single task the declining policy lost was a task where
accepting tried a unanimous instance, failed, explored, and **discovered a new way of asking**
(`click-dialog-2` 1.00 -> 0.15, `generate-number` 0.65 -> 0.15, `login-user-popup` 0.85 -> 0.45).
The fix was to let disagreement **rank** instances and never **veto** them.

Two smaller findings, both negative and both checked:

- **Which single demonstration you find did not matter** at equal scoring. A five-episode probe
  looked like a 0.35 -> 1.00 jump on `identify-shape` under the guided hand search. At the same
  twenty scored episodes the guided and blind searches score identically on `identify-shape`
  (0.35), `click-menu-2` (0.30) and `click-widget` (0.65). The apparent gain was an episode-count
  confound and is not claimed.
- **The four untouched arms reproduced the merged receipt to four decimal places** in both runs
  (0.1525 / 0.2562 / 0.2900 / 0.6500). The instrument is not drifting.

**Where the ceiling actually is.** 52 of the 92 held-out tasks are never demonstrated even once:
36 with no first success found, 11 pages that do not run under jsdom, 5 that change under the same
seed. No policy about how many demonstrations to take, or which ones, can reach a task that never
produced a first success. Of the 36, only 13 spent the whole 1500-action budget; the median spend
was 565 and the minimum was **1**. `chase-circle` asks the agent to keep the mouse inside a moving
circle; the blind search offers it one click, tries it, and reports
`FAIL_CLOSED__REACHABLE_SPACE_EXHAUSTED_GOAL_ABSENT`. The hand that could hover exists in the
instrument (`HAND_TIER` adds 7 actions there, 21 on `drag-box`, 14 on `highlight-text`) and the
learner can already represent every one of those actions — but the blind ladder does not include
it, by design, and the guided search that does use it did not finish the split in session.

So the honest ranking changes: **coverage, not selection, is the binding constraint.** The next
capability is getting a first success at all on the 39% of tasks that never produce one, on a
substrate with real geometry. That is a perception-and-action problem, not a learning-from-success
problem, and it is not solved by anything in this document.

One real correctness defect was fixed along the way: an explorer whose action vocabulary offers
nothing at all used to report the closed verdict `REACHABLE_SPACE_EXHAUSTED_GOAL_ABSENT`. Trying
nothing does not prove absence. It now reports `OPEN__NOTHING_OFFERED_BY_THIS_ACTION_VOCABULARY`.
This is honest, tested, and falsifiable — and it changed **none** of the 92 verdicts, because those
pages all offer at least one action. It is recorded as a truthfulness fix, not a capability gain.

Receipt: `canonical/verification/CHOOSING_WHAT_TO_LEARN_FROM_MEASURED_20261114_V1.json`.

## 11. Ranked next work

1. **Get a first success on the tasks that never produce one.** 36 of 92 held-out tasks, and the
   median give-up is 565 of 1500 actions. This is now the largest single pool of unrealised
   capability, and it needs a substrate with real geometry (chromium) plus a search that uses the
   whole hand. Selection among instances is measured and does not reach it.
2. **Record the failure side at the earlier refusals.** A refused attempt is evidence about that
   state. Until then the door can only learn scope from failures that occur after recall.
3. **Owner decision on confinement/effect adoption.** Still the gate on "anything on a computer".
4. **Only then weight consolidation**, from identified, admitted, contrastive evidence.

Demoted: choosing which instances to learn from. It was item 2 and it is now measured at a tie.
The `version_space_active` arm stays in the instrument as the control that refutes it, off by
default, so the next person does not have to take this on trust.

## 12. Sources used for ranking, not authority

- FGSE — arXiv:2611.14326 (10 Nov 2026): commit only on transfer + falsification + archived regression.
- Veritas — arXiv:2611.13336 (9 Nov 2026): most real tasks arrive without a verifier; generating one
  is the bottleneck.
- VerifierBench — arXiv:2610.28679: generated verifiers reject invalid solutions far more reliably
  than they accept valid ones.
- SkillOpt — arXiv:2605.23904: held-out acceptance gate; 1–4 accepted edits; ties rejected.
- Skill-V — arXiv:2610.11781: skills as versioned falsifiable contracts; non-regression gate.
- SkillOps — arXiv:2605.13716: library-level technical debt; maintenance becomes load-bearing at scale.

## 13. Stop condition

Stop here. The information loss is closed and tested; the door reports its own ignorance precisely;
no capability, family, terminal or weight credit is claimed.
