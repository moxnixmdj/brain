# The weight layer needs a gate too — measured on this tree's only trainable weights

**13 November 2026.** Branch `arena/2ca2d208-brain`, base `8dfc1f46d2`. Authority **NONE**:
producer-run sandbox measurement, `$0`, zero model calls, no capability registered, no family
flipped, `truth.achieved` untouched, no test weakened.

The owner's framing this round: *token-space learning (memory, skills, causal models) is real but it
is only one layer; weight-space learning (fine-tuning, RL, test-time training) is the missing layer;
Option 3 — both — is the complete solution.* That framing is **mostly right**, and the four papers
he cites are real. This round tested the part nobody here had tested: **what our own weight updates
actually do.**

---

## 1. The substrate, and the hole in its receipt

This tree has exactly one weight-space learner: `OnlineParametricPolicyModel` in
`semantic_generalization_engine_v1` — three linear heads (operation / concept / domain) over 128
hashed text features, one gradient step per verified experience. `solve_task` calls it after a
verified answer and keeps the receipt.

The receipt reports `pre_loss`, `post_loss`, `loss_delta`, `||ΔW||₂` — **all measured on the goal it
just trained on.** Nothing in it looks at a second input.

## 2. The measurement

32 goals, labels re-derived by the independent typed parser (`parse_task`) that actually answers
them, one gradient step each, in the same order, exactly as the engine calls it:

```text
python3 canonical/tools/weight_update_interference_measure_20261113_v1.py

stream=32 judge=parse_task
naive : applied=32 receipts_saying_loss_went_down=32 agreement=5/32 broke=3
gated : applied=1 refused=31 agreement=1/32 broke=0 verdicts={'ADMIT': 1, 'REFINE': 31, 'REJECT': 0, 'REFUSED': 0}
```

Read that carefully, because it cuts both ways:

- **32 of 32 updates certified themselves successful.** Every receipt said the loss went down and
  the weights moved.
- The layer ended up agreeing with the tree's own symbolic parser on **5 of 32** goals.
- **3 goals it had predicted correctly became wrong** during the stream.
- The gated arm broke **nothing** — and kept only **1** step, ending at **1 of 32**.

So the gate removes the damage and most of the reach. That is not a win to be advertised; it is the
diagnosis: **one gradient step on one hashed-feature example carries almost no transferable
signal.** The problem is not only that the update was ungated. It is that the *learning signal* is
too thin, and the receipt is structurally unable to reveal either fact.

This is the exact weight-space twin of the token-space hole closed yesterday in
`lesson_admission_gate_v1`: permanence granted by a check that only ever saw the demonstration.

## 3. What shipped

`canonical/swe_kernel/weight_update_admission_v1.py`:

- The candidate step is applied to a **copy** of the heads. The live matrices are fingerprinted
  before and after and are bit-identical on any non-`ADMIT` verdict (tested).
- Agreement with the typed parser is measured on goals that are **not** the training goal, split
  into `ARCHIVE` (already trained on) and `TRANSFER` (not yet seen).
- `ADMIT` = gained ≥1 and lost 0. `REFINE` = no measured gain. `REJECT` = broke a prediction that
  was right. `REFUSED` = no probes / every probe is the training goal / a label the heads cannot
  represent.
- Labels come from `parse_task`, never from the head and never from a stored claim; goals the
  parser cannot type are **named**, not silently dropped.

Wired in `solve_task`: a **permanent** step (`persist_policy=True`) now goes through the gate with
probes built from prior verified experiences; a **volatile** per-request step
(`persist_policy=False`, the controller's read-only lane) is unchanged, because it is discarded and
grants no permanence. With no prior verified goal the first permanent step is `REFUSED` — one
demonstration is a point, not a weight change.

## 4. The three corrections to the owner's framing

**(a) "Fine-tune on our execution traces" is the version that measurably fails.** Experience
Distillation (arXiv:2607.21051, 23 Jul 2026) retains **≥64.8%** of the in-context gain in weights,
while **direct SFT on the same experience recovers only 3.8%**, and matches an RL baseline with
**≥9.6× fewer** environment samples [1](https://www.alphaxiv.org/abs/2607.21051),
[3](https://pith.science/paper/2607.21051). The difference is not "weights vs no weights"; it is
*what the training target is*: an experience-conditioned teacher's next decision at each recorded
state, not the raw trace.

**(b) Naive online weight updates destabilize the policy — this is published, not a hunch.** ASCENT
(arXiv:2610.05303, 4 Oct 2026) states that directly imitating or reinforcing the tokens of a single
attempt "destabilizes the policy, erodes executable behavior, and lowers task success"; it instead
self-distills verified trajectories from a frozen copy of the initial model into persistent LoRA
fast weights, gaining **>22 points** on ALFWorld/WebShop and transferring to held-out scenes. It
needs full next-token distributions, so it applies to **open-weight** models
[1](https://arxiv.org/abs/2610.05303), [2](https://arxiv.org/html/2610.05303).

**(c) The algorithm decides whether weight learning works at all.** Continual-ARC
(arXiv:2611.14505, 10 Nov 2026) is the strongest evidence *for* the owner's thesis: "**No
harness-based method gains on unseen tasks, whereas weight-based learning shows substantial
gains**", and harness persistence usually loses to a floor that simply caches demonstrations. But
the same paper reports that policy gradient on game outcomes and self-distillation from the
teacher's move **both failed to learn reliably**; what worked was **DAgger** — teacher moves on the
student's own visited states
[1](https://arxiv.org/abs/2611.14505), [3](https://arxiv.org/pdf/2611.14505).

Two more current results that bound the claim:

- **aTTT** (arXiv:2607.03441): the *same* summary text delivered in context scored **49.3%** (below
  the 51.4% no-adaptation baseline) while delivered as a weight update scored **54.3%** — direct
  evidence that the weight layer can carry signal the prompt cannot. But the gains "concentrate
  where models already have task competence", i.e. it **preserves** competence rather than teaching
  new abilities, at 1.9× serving cost [7](https://arxiv.org/pdf/2607.03441).
- **Memory Models** (Letta, 25 Jun 2026) is a position piece, and its conclusion is subtler than
  "add fine-tuning": the weights it wants trained are a **memory model** — a curator optimized by
  meta-RL to write token-space memory that improves *future* tasks, carried across model
  generations [1](https://www.letta.com/blog/towards-agents-that-learn/).

## 5. What this repo measured on real software engineering, this week

From `canonical/verification/CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json`
(real Django test runs on this machine, no model calls): 231 Django tasks, **225 judgeable**, 2422
candidates run, **10 resolving candidates**, **one submission resolves 5 tasks**, and
**43 candidates pass the new tests while breaking an old one**. The whole-suite record then shows 1
of those 5 breaking 8 tests elsewhere.

That is the same shape as the weight measurement: *passing the check you looked at is not the
property you need.* It is also why consolidating this corpus into weights today would industrialize
the error rather than fix it.

## 6. The ordered plan (unchanged in direction, sharper in order)

1. **Gate both layers.** Token-space admission: shipped yesterday. Weight-space admission: shipped
   today. Both refuse rather than guess.
2. **Fix the learning signal, not the layer count.** One-step imitation is measured here to be
   nearly useless. The published mechanisms that work are context-conditioned one-step distillation
   (EPD), frozen-teacher hindsight self-distillation (ASCENT), and DAgger-style teacher correction
   on the student's own states (Continual-ARC). All three need **open weights** and a GPU. This
   sandbox has neither, so that step cannot be executed here — it is named, not faked.
3. **Build the probe corpus first.** Both gates are bounded by the probes supplied. The cheapest
   high-value work is victims-with-specs and reserved no-retrieval probes, not more training.
4. **Then the confined computer-use lane**, with state observation, rollback, and task-specific
   success predicates.

## 7. Test ledger (real counts, including failures)

```text
.venv/bin/python -m pytest -q <10 suites, includes the 15 new weight-admission tests>
196 passed in 16.27s
```

- New `canonical/tests/test_weight_update_admission_v1.py`: **15 tests**, real heads, real parser,
  real temporary state paths. They assert the naive arm really breaks predictions (so the gate
  cannot become decoration), that refusal leaves the matrices bit-identical, that evaluation writes
  no state file, that an admitted step changes both fingerprints, and that the engine refuses a
  permanent step when it has no other verified goal.
- **First run of the 10-suite set: `1 failed, 195 passed in 19.16s`** —
  `test_tier0_compiled_http_skill_recall_stays_under_50ms_across_even_wake_episodes`. It did not
  reproduce on the immediate rerun (196 passed). Load-sensitive; **no assertion relaxed**.
- **Pre-existing failure, attributed by experiment:**
  `test_integrated_autonomous_loop_v1.py::test_cut1_single_front_door_gap_ledger_gui_fallback_and_honest_refusal`
  fails at line 118. With this round's engine edit **stashed**, it still fails (`1 failed, 3 passed`),
  so it is a base-commit failure, not a regression from this work. It is reported, not fixed here.
- `compileall` clean; `git diff --check` clean; unified model **33/33 PASS**; integrity guard
  `--base origin/main` rules=17 violations=0.

## 8. One sentence

The owner is right that both layers are needed and wrong that adding the second layer is the
missing piece: **measured here, 32 self-certifying weight updates bought 5/32 agreement and broke 3
correct predictions, and the gate that stops the damage also refuses 31 of them — because the
signal, not the storage, is what is thin.**
