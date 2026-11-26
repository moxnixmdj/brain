# Frontier leapfrog plan V3 — 2026-11-27

Supersedes V2 (`FRONTIER_LEAPFROG_PLAN_20261126_V2.md`) because V2's Play 1 was killed by its own
ablation: the contract router scored 0.905 recall@5, a topic-only bag of words with the mechanism
removed scored 0.952, and a random five from the topic-sharing pool scored 0.846. Domain-level recall
was measuring the label. **Routing is not yet measured; the label is the bottleneck.** Everything
below is rewritten around that lesson: every play names an *exact* target, an *ablation*, and a
*chance baseline computed from the pool the mechanism actually draws from*.

## The position, measured this round

The promotion ledger (`canonical/verification/PROMOTION_LEDGER_20261127_V1.json`, in the model as
`UnifiedModel.promotion()`), over 849 unique module paths classified into the five functions:

| what is missing | count | share |
|---|---:|---:|
| **nothing — callable and receipted** | **31** | **3.7 %** |
| nothing but a receipt (callable, never proved it ran) | 36 | 4.2 % |
| a receipt (adapter file exists, never ran) | 4 | 0.5 % |
| **a thin adapter (indexed source, no adapter)** | **641** | **75.5 %** |
| **an index entry (invisible to every route)** | **137** | **16.1 %** |

And the runtime's own book: 462 capabilities, 145 bound, **321 receipt-backed and still marked
`RECEIPT_BACKED_PENDING_PROMOTION`**. So the machine is not short of capability, of receipts, or of
code. It is short of *surfaces*: three quarters of the code that implements the five frontier
functions cannot be called by `solve()`.

That is the single most important number in this repository right now, and it is the reason the plan
below contains almost no new capability work.

## What the frontier cannot do, and why we can

1. **OSWorld 2.0: 20.6 % binary** (Opus 4.8, max thinking, 500 steps), 54.8 % partial, ~318 tool
   calls per task, zero above 163 minutes for every model. The paper attributes the failures to lost
   constraints, missed mid-task information, guessing instead of asking, skipped verification and
   hidden state — not to GUI control. **Their per-step verification costs model calls; ours costs a
   function call.**
2. **Harness beats model**: harness-induced variance is reported at 7.8× model-induced variance on a
   SWE-bench subset, 6 of 9 model-pair rankings reverse under a different scaffold, and one adapter
   swap moves Pass@1 from 19.1 % to 73.4 % with weights frozen. **We own our harness and can delete
   parts of it; they sell theirs.**
3. **Skills without verification are worthless**: EvoSkills' one-shot self-generated skills score
   30.7 % against a 30.6 % no-skill baseline, and the 71.1 % appears only after iterative
   verification. Skill-V: acquisition-only 68.8 %, full 95.3 %. **Our receipts are the verification
   loop they are building.**
4. **Memory numbers are not measurements**: Mem0 open-source 32.4 % LongMemEval against the vendor's
   93.4 %, and a 93.4 % → 90.4 % move from changing retrieval depth alone. **We can define memory by
   what removing an item costs, which no vendor can because their item is an embedding.**

## The plays

Each play states: the frontier failure it aims at, the unusual move, the **exact target** (chance
1/N, not domain recall), the first measurable step, and the kill criterion fixed before the run.

### Play 1 — 641 adapters from the AST, verified twice, or none

- **Frontier failure.** Agent S4 lifts a fixed open 27B from 5.6 % to 21.3 % on OSWorld 2.0 by
  evolving its own interfaces; locking the tool layer in SkillSmith costs 6.8 points. Capability
  lives in the interface. We have 641 indexed modules with a contract in their AST and no adapter.
- **Unusual move.** Do not write adapters. Derive each one from the module's own signature and
  docstring-declared contract, execute it twice in a fresh interpreter on a *replayed* input drawn
  from the module's own tests, and keep it only if both runs agree and the effect is observable.
  Idempotence and agreement are the admission test; no model, no hand edit.
- **Exact target.** The module a recorded execution used, one per query, chance 1/849 — the
  scoreboard Play 1 of V2 should have had. Until 100 such pairs exist, the play reports only the
  survival rate and refuses to report reachability.
- **First measurable step.** 50 adapters, chosen deterministically (modules that ship a passing test),
  generated, executed twice, receipts written. Report survival rate and the number of new exact
  targets created.
- **Kill.** Fewer than 40 % survive a second clean run, or the derived adapters fail to produce
  100 exact-target pairs.

### Play 2 — every action carries a checkable expectation, or it is refused

- **Frontier failure.** OSWorld 2.0's failure list is a verification list: skipped checks, lost
  constraints, missed mid-task changes. Their agents cannot afford to check; ours can.
- **Unusual move.** The receipts already carry `action_template.expect` (`field_equals`,
  `field_nonempty`). Make it mandatory: an action whose effect cannot be expressed as a checkable
  expectation on an observable is not offered to the runtime at all. The refusal is the capability.
- **Exact target.** For 100 recorded actions, the post-condition that is true if and only if the
  action achieved its goal, judged by the machine's own reader — chance is "always say verified",
  which scores 1.0 on the true subset and 0.0 on the perturbed one, so the pair is what discriminates.
- **First measurable step.** Audit all 462 capabilities for a checkable `expect`; report the share;
  then perturb 100 of them with a single-fact change and measure detection.
- **Kill.** Fewer than 50 % of capabilities can express a checkable expectation, or detection on the
  perturbed half is below 0.90.

### Play 3 — the knob budget: a part that does not move the metric is deleted

- **Frontier failure.** The harness is the dominant variable (7.8× the model's) and induces a 40×
  spread in tokens per solved task. Nobody measures their own knobs; every knob is a part.
- **Unusual move.** Enumerate the runtime's own behavioural knobs — env vars, CLI flags, module-level
  constants that change behaviour — and require each to move the exact-target metric by ≥5 % at equal
  or lower step latency. Knobs that do not are deleted, with the measurement as the receipt.
- **Exact target.** Same exact-target set as Play 1; a knob is scored by the delta it produces.
- **First measurable step.** Inventory the knobs and count them; measure the five most-cited ones.
- **Kill.** If the inventory exceeds 40 knobs and fewer than five move the metric, delete the rest in
  one round and report the deletion as the play's result.

### Play 4 — memory pays rent, and rent is measured by deletion

- **Frontier failure.** Vendor memory scores 93.4 % where the same open-source edition scores 32.4 %;
  the spread between vendors is a reader/judge artefact; supersession survival is 4.4–7.0 % for the
  leading temporal graph in an independent forgetting suite.
- **Unusual move.** Every stored item carries the decision it would change. Each round, a 5 % sample
  is removed and the decisions are replayed. If removal changes nothing, the item is deleted
  permanently. Store size becomes an output, not a target.
- **Exact target.** A decision reached with the item present, and the same decision replayed with it
  absent; the item is credited only if it flips at least one. Chance is the flip rate of removing a
  random *unrelated* item, measured in the same pass.
- **First measurable step.** Run the removal test on 200 stored items and report the inert share.
- **Kill.** Inert share ≥30 %, or the flip rate cannot be separated from the unrelated-item control.

### Play 5 — backward transfer on promoted capabilities, with rollback

- **Frontier failure.** Continual RL still forgets (CPO cuts forgetting 13.7 % but does not remove
  it); PATH-Bench shows transfer does not imply retention; Skill-V's acquisition-only arm *loses*
  6.6 points against a static library.
- **Unusual move.** Our learning is code, so forgetting is a test that stops passing. Freeze a probe
  set of 100 smoke tests over promoted adapters; after every promotion round, re-run all of them and
  roll back any round that drops the pass rate by more than 2 points. Report forward transfer,
  backward transfer and forgetting exactly as PATH-Bench defines them, at zero model cost.
- **Exact target.** Each probe is a test with a binary outcome, so chance is the flake rate measured
  by running the set twice before any promotion.
- **First measurable step.** Freeze the probe set and measure its flake rate.
- **Kill.** Any round that regresses without rollback, or a probe flake rate above 2 %.

### Play 6 — speed is a gate, not a metric

- **Frontier failure.** Latency compounds in a loop: a 4× faster step is 4× throughput, and the
  harness alone moves tokens per solved task 40×. OSWorld 2.0 costs $3.87K per full run.
- **Unusual move.** Every play reports p50/p95 step latency and *tokens per solved task* (zero by
  construction for us). Any change that raises p95 step latency by ≥10 % must show ≥10 % exact-target
  capability in the same measurement, or it is reverted before it is merged.
- **First measurable step.** Instrument the runtime's own step boundary once, and report the number
  for the three heaviest paths (`route`, `find_source`, `solve`).
- **Kill.** Not applicable — this play is a gate. Its failure mode is being ignored, which is why it
  is written as a merge condition rather than a goal.

## Composition — what already exists and is not to be rebuilt

| existing artifact | what it supplies | which play consumes it |
|---|---|---|
| `DOMAIN_ATLAS_V1.json` + `UnifiedModel.anatomy()` | where the five functions live, 849 rows | 1, 3 |
| `PROMOTION_LEDGER_20261127_V1.json` + `UnifiedModel.promotion()` | why each module is not callable | 1, 5 |
| `CAPABILITY_RECEIPT_PROJECTION_V1.json` (321 receipted) | the verification loop EvoSkills had to build | 2, 4 |
| `BOUND_CAPABILITY_REGISTRY_V1.json` (145 bound) | the promotion surface | 1, 5 |
| `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.json` (4,621 distinct CLI options in 47 s) | the action vocabulary for shell-shaped computer use | 2 |
| `THE_BRANCH_IS_THE_MODEL_20261128_V1.json` (one copy + one execution per edge) | prediction by execution, not by model | 2, 4 |
| `WHAT_A_DECISION_COSTS_20261127_V1.json` (trial-then-know 0.925 at 52 executions vs 160) | the cost model for "check or guess" | 2, 6 |
| `swe_kernel/` (201 modules, 124 paired) | real repositories and real judges | 1, 5 |

## What this plan refuses

- **No model calls at runtime**, no embeddings, no vendor memory, no benchmark headline on a
  contaminated set (SWE-bench Verified is excluded by name).
- **No new organ unless it deletes one.** The promotion ledger is a join over five artifacts, not a
  sixth artifact; the anatomy block is a projection, not a store.
- **No recall claim without its chance baseline**, and no chance baseline drawn from a different pool
  than the mechanism. That is the clause that killed V2's Play 1, and it stays.
- **No claim that a module works because it is indexed, promoted or receipted.** A receipt is one
  observed effect; the ledger says so in its own `claim_limit`.

## Immediate order of work

1. Play 1 step 1 (50 AST-derived adapters, twice) — the largest single deficit, and the only play
   that changes the number 3.7 %.
2. Play 2 audit (462 capabilities vs checkable expectations) — it is a read, and it gates Play 4.
3. Play 5 probe freeze — it must exist before any promotion round, or the first promotion is
   unmeasurable.
4. Play 3 inventory and Play 6 instrumentation — cheap, and they police everything after.
5. Play 4 removal test — last, because it needs the exact-target set that Play 1 creates.

Every step above is executable in this repository today, by local code, with zero model calls and
zero network calls, and each one states what would make it wrong before it is run.
