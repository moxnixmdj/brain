# The promotion plan: the frontier's open problems are functions we already implement and cannot reach

**Schema:** `BRAIN_FRONTIER_PLAN_V2` · **Date:** 2026-11-26 ·
**Predecessor:** `FRONTIER_LEAPFROG_PLAN_20261125_V1.md` (PR #7095) — six plays, three measured
(`LEAPFROG_PLAY_EVIDENCE_20261125_V1.md`, PRs #7096 / #7098) · **Authority:** NONE ·
**Model calls:** 0 · **Research digest:** `canonical/research_sources/FRONTIER_RESEARCH_20261126_V2.md`

---

## 0. The measurement that reorganises everything

The standing hypothesis was: *we solved the frontier's problems under non-obvious names, and the
capabilities are hidden.* That hypothesis is now partly measured, and it is only **half** true.
`canonical/tools/domain_atlas_v1.py` classified every module in the tree by what it *does*
(weighted evidence over stem, docstring, and the names of what it defines; frontier vocabulary and
this repository's vocabulary in one table), then asked the shipped model whether it can reach them.

| domain (frontier function) | candidates | indexed as source | **executable surface** | wholly invisible | source recall (frontier phrasing) | **route recall (own vocabulary)** |
|---|---:|---:|---:|---:|---:|---:|
| instant learning | 173 | 141 | 65 (37.6 %) | 1 | 1.00 (13.0× chance) | **0.00** |
| continual learning | 28 | 17 | 8 (28.6 %) | 2 | 0.33 (26.6×) | 0.33 |
| memory | 184 | 162 | 49 (26.6 %) | 1 | 0.67 (8.2×) | 0.33 |
| computer use | 145 | 117 | 24 (16.6 %) | 2 | 0.67 (10.4×) | 0.33 |
| coding agents | 287 | 209 | 101 (35.2 %) | 4 | 1.00 (7.8×) | 1.00 |
| verification / abstention | 321 | 261 | 53 (16.5 %) | 13 | 0.67 (4.7×) | 0.33 |
| world model | 122 | 98 | 37 (30.3 %) | 5 | 1.00 (18.5×) | **0.00** |
| **total** | **1,260** | **1,005** | **337 (26.7 %)** | **28 (2.2 %)** | **0.76 mean** | **0.33 mean** |

Read it in three sentences:

1. **Discovery is not the bottleneck.** 1,260 domain-candidates exist; 1,005 are already in the
   model's source index; only 2.2 % are invisible to every route the model has.
2. **Executability is the bottleneck.** Three quarters of the machinery the model can *name* is
   not a surface the runtime can *call* (26.7 % executable; computer use and verification are
   both under 17 %).
3. **Routing is the wall.** Navigation finds the function (mean recall 0.76, 4.7–26.6× chance).
   `route()` — the thing `solve()` actually uses — reaches it **one time in three**, and for the
   two domains that matter most for leapfrogging (**instant learning**, **world model**) it
   reaches it **never**, in the repository's own vocabulary.

So the machine owns the frontier's five open problems as *code*, indexes them as *text*, executes
a quarter of them as *surfaces*, and routes to a third of them as *capabilities*. Every claim in
this plan is downstream of closing that ladder, and nothing in it requires a model call.

## 1. Thesis

> The frontier is trying to make a frozen model *learn*. We should make an explicit machine
> *reachable*. Their five open problems — instant learning, continual learning, memory that
> survives its own update, long-horizon computer use, knowing when not to act — are five
> functions this repository already implements. Nobody can copy our position quickly, because
> the moat is not the code: it is that every execution here produces a receipt that a *different
> identity* re-runs, so our labels for "did this work" are produced by execution, not by a judge.

Three moves follow, and they are unusual in the specific sense that they are cheap for us and
expensive for everyone else:

- **Labels from execution, not from a model.** Routing, memory value, and law selection can all be
  scored by running the thing and reading the receipt. That is OATS's outcome signal without a
  serving-time model, and it is `DreamCoder`'s corpus signal without a synthesis search.
- **Abstention as a product, not an apology.** A public paired benchmark (AgentAbstain) says the
  best frontier agent gets 59.5 % of act/abstain pairs right, that abstention is largely
  independent of task skill, and that "post-hoc abstention" is a named failure. We already refuse
  fail-closed; what we lack is the *paired set* and the *typed reasons*.
- **A deterministic compiled identity.** `BRAIN_UNIFIED_MODEL_V1.json` is digest-addressed and
  rebuilt from the tree; 38/38 checks. No frontier lab ships an agent whose entire contents can be
  hashed and re-derived by a third party. That is the substrate for every claim below.

## 2. What V1 got right and what it missed

V1 named the right *directions* and three of its plays have now been measured: flat law-store
lookup holds (5.0 dict probes per query at 1 → 5,000 laws; 363.6× vs linear at 5,000); the refusal
census **failed its own kill criterion** (12.96 % refusals, only 40 % typed); the mutation gate
scored **0.463** against a 0.8 threshold, with the finding that the oracle itself is not
deterministic (four runs: 0.463 / 0.483 / 0.517 / 0.537).

V1's blind spot was structural: it treated the plays as *new machinery to build*. The atlas shows
that roughly three quarters of the machinery already exists, unexecutable, and that the model
cannot route to the domain it is best at. **V2 is a promotion plan, not a construction plan.**

---

## 3. The plays

Every play states: the frontier's measured failure (cited), what we already own (paths), the
unusual move, the first measurable step (runnable offline, zero model calls), and the kill
criterion. A play that cannot name its kill criterion is not in this document.

### Play 1 — Route by contract, not by vocabulary

**Frontier failure.** Tool/model routing is treated as a solved-shaped retrieval problem at cloud
scale — 98.2 % Recall@15 over 3,616 tools with hybrid dense+BM25 (arXiv 2607.15593), 82.9 %
routing accuracy with a 66 M classifier (Switchcraft, arXiv 2605.07112) — yet every one of those
systems is judged against a label it helped produce, and the referees say so. Our own number is
worse and cleaner: **0.33 mean route recall, 0.00 for instant learning and world model.**

**What we own.** 449 capabilities with declared `input_names` / `output_fields` / `triggers`; 337
executable surfaces with AST-derived contracts; 1,005 indexed modules; a router with an IDF
postings index and an identity channel.

**The unusual move.** Score the *ask against the contract*, not the words against the id. A goal
that names an effect ("learn from one demonstration") should match a module whose declared
outputs are the artifacts that effect produces. Set-level coverage (HYSET-style) instead of
per-item cosine; refusal when the top-k disagree about required inputs.

**First measurable step.** Rebuild the route index over the atlas's 1,260 candidates with
contract fields as first-class terms, and re-run the 42 fixed queries (7 domains × 3 frontier + 3
native phrasings, written before the experiment, in the atlas). Report recall@5 with chance
baselines already implemented. Target: **≥ 0.80 mean, no domain at 0.00.**

**Kill.** If contract-first routing does not beat 0.33 by 20 points at equal or lower index size,
the bottleneck was not vocabulary and this play is dead.

### Play 2 — Executability is the promotion, not the discovery

**Frontier failure.** The frontier's answer to "our agent has skills" is a harness that grows
prompts and tool lists; nothing in the literature offers a *checkable* promotion path from "a file
exists" to "the runtime may call it". Where promotion is discussed it is a human sign-off.

**What we own.** 2,242 indexed modules; 628 harvested surfaces; a receipt lane; a two-identity
admission workflow (producer receipt, independent OIDC re-run); `harvest_hidden_capabilities_v1`
already derives invocation shape from AST.

**The unusual move.** Derive the missing contract from the AST — inputs from the signature,
outputs from the return type and docstring, failure modes from raises — synthesise a `run(args,
root)` adapter, and admit it only if a smoke test it writes for itself passes *twice from a clean
process*. Promotion is the ladder, never a declaration: `DISCOVERED → EXECUTABLE → RECEIPTED →
RE-RUN BY A DIFFERENT IDENTITY → ROUTED`.

**First measurable step.** For the 24 computer-use and 53 verification candidates that are
indexed but not executable, generate adapters and measure: adapters generated, import-clean,
smoke-passing, receipt written. Target: raise ≥ 60 % of domain candidates to executable with a
receipt, with zero adapters admitted on a single green run.

**Kill.** If fewer than 40 % of derived adapters pass their own smoke test on a second clean run,
auto-promotion is fake and this play is dead.

### Play 3 — Abstention with a receipt

**Frontier failure.** AgentAbstain: 263 paired tasks, 42 sandboxes, best of 17 frontier models
**59.5 % paired accuracy**; mean act 80.6 % vs abstain 59.1 %; ability largely independent of task
skill; post-hoc abstention documented. FixedBench: on tasks that need *no* change, frontier coding
agents propose unwanted changes in **35–65 %** of cases; "verify-then-abstain" lifting abstention to
80.5 / 88.5 % but creating over-abstention.

**What we own.** 991 refusals in 4,674 receipts, 40 % typed (`refusal_ledger_v1`); fail-closed
gates (`live_brain_route_admission_v1`, `binding_pin_is_current_v1`); a vocabulary that names
missing artifacts (`REFUSED__THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT`).

**The unusual move.** Our refusals are *checkable by construction*: a refusal can name the artifact
it wants, and `manufacture_what_the_refusal_asks_for_v1` can produce it. So the paired set is
manufacturable — perturb one fact in the environment (a value, a pin, a path, a tool) and the
should-act twin becomes a should-abstain twin, with no human labelling.

**First measurable step.** Generate 100 pairs from our own receipts by single-fact perturbation;
score act accuracy, abstain accuracy, paired accuracy, and the share of refusals that name a
checkable artifact. Target: **≥ 0.80 paired, ≥ 0.90 typed reasons** (against the published 0.595
frontier ceiling).

**Kill.** If paired accuracy is below 0.60, or if a single-fact perturbation changes more than one
decision in the trace (i.e. the pairs are not clean), the benchmark measures nothing and the play
is dead.

### Play 4 — Learning is a store transaction

**Frontier failure.** *Are Self-Evolving Agents Continual Learners?* — plasticity bought with
stability, retrieval collision, "incomplete continual learners". The 2026 survey's summary is
blunter: nothing solved publicly, only frozen-model dossier stacks shipped. In-weight editing
forgets after 100–1,400 edits (ROME/MEMIT).

**What we own.** `metamorphic_oracle_v1` (9 laws that *fire* on a program pair);
`rule_scope_learning_v1` (a law with a scope); `rule_expiry_v1` (a law with a lifetime);
`sentient_cognitive_core_v1.sleep_consolidate`; `compress_by_anti_unification`; the flat law store
measured last round (5 dict probes per query, independent of size).

**The unusual move.** An episode is not "experience to embed"; it is a **transaction**:
`observe → candidate law → fire the oracle on held-out pairs → if it fires and the scope is
determined, commit law+scope+expiry → else refuse with the missing discriminator named`. Commit is
serialised through the flat store, so the learning event is a diffable object with a digest — and
every commit is followed by a **retention replay** of the previous N laws, which is the stability
control the literature says everyone gets wrong.

**First measurable step.** 40 repo episodes (a commit pair with a failing-then-passing test).
Report: laws induced, laws that fire on held-out pairs, abstentions with a named discriminator,
forward transfer (next episode solved with fewer probes), backward retention (previous laws still
firing after each commit). Target: retention ≥ 0.95, transfer > 0.

**Kill.** If retention drops below 0.95, or induced laws fire on held-out pairs less than half the
time, we are producing noise with a receipt and the play is dead.

### Play 5 — Memory must pay rent

**Frontier failure.** Memory is scored by recall, not by consequence: vendor 93.4 % vs independent
32–49 % on LongMemEval; ForgetEval shows intent-aware deletion at 4.4–7.0 % for a leading graph
memory; MCCL states the correct criterion — "whether it improves future actions".

**What we own.** Receipts with outcomes; `capability_selection_retrieval_v1`; the chunk archive;
the refusal ledger (which tells us *why* an item was needed).

**The unusual move.** Every stored item carries the outcome of the episodes in which it was
retrieved, and the runtime can be run with that item **ablated**. Causal contribution = success
rate with item − success rate without it, measured on the same task sample. Items with
non-positive contribution are evicted *with a receipt that says which episodes convicted them* —
a deletion control plane that most of the field scores near zero on.

**First measurable step.** 60 tasks × 30 stored items, A/B per item: report median causal lift,
share of items with negative lift, and eviction precision. Target: median lift > 0 and ≥ 20 % of
items evicted as non-paying.

**Kill.** If the A/B is not reproducible across two independent task samples (sign flips), the
measurement is noise and the play is dead.

### Play 6 — The world model is our verifier

**Frontier failure.** OSWorld 2.0: best agent 20.6 % binary / 54.8 % partial on workflows where a
human needs 1.6 h and Opus 4.7 takes 318 tool calls; past ~163 minutes of human time,
completion is zero. Every serious fix is a learned world model (CUWM, latent world-action,
MPPI branches) and every one of them needs training.

**What we own.** A deterministic program-execution oracle, 9 metamorphic laws, a mutation harness
(0.463 discriminating today), and a law store whose effects we can *compute*.

**The unusual move.** Predict the consequence of a patch **without pixels and without a learned
model**: from the diff, name the laws that will break, run only those, and measure the prediction
against the full suite. That is a world model whose "next state" is the set of violated invariants
— auditable, deterministic, and free.

**First measurable step.** 50 real patches from repo history: predict violated laws from the diff;
compute precision/recall against the full-suite outcome; report tests saved. Target: precision
≥ 0.70 at ≥ 3× fewer executions.

**Kill.** If precision is below 0.50, the diff does not determine the consequence and this play is
dead (it would only be a slower test runner).

---

## 4. Sequence

1. **Play 1 first** (days, cheapest): it is the only play that changes what every other play can
   reach, and its measurement harness already exists in `domain_atlas_v1.reachability()`.
2. **Play 2 next**: executability gates plays 3–6 (each needs surfaces to run).
3. **Play 3 and Play 5 in parallel**: both are censuses over receipts we already have, and both
   produce public numbers against published baselines (0.595 paired; 4.4–7.0 % deletion control).
4. **Play 4 last of the learning plays**, because it needs the oracle determinism fix that Play 6
   exposed (our suites flip colour between runs).
5. **Play 6 runs whenever Play 4 stalls**: it is the cheapest counterfactual engine we own.

## 5. What we refuse

- **No weight training, no LoRA, no fast weights.** The literature's own summary is that
  in-weight editing forgets after hundreds of edits; we would be paying for a worse oracle.
- **No vector-store memory.** The independent numbers are the argument: 32–49 % independent vs
  93.4 % vendor on the same benchmark, and the benchmark's own designer says the scores are not
  comparable across readers.
- **No benchmark we cannot name and cannot run.** Every play above names its set and its metric.
- **No capability claim without an independent re-run.** Promotion ends at a second identity, not
  at our own green test.

## 6. Non-claims

- The atlas is a lexical instrument over docstrings and symbol names. A high score means the
  module's own text says it does this work; it does not mean the work is correct.
- The 0.33 route recall is measured on 42 hand-written queries (3 per phrasing per domain). It is a
  probe with a chance baseline, not a benchmark.
- Recall figures move when the atlas or the compiler changes; each is quoted with the run that
  produced it (`DOMAIN_ATLAS_V1.json`, digest `3ce88ca8…` model).
- No frontier number in this document was produced by us; all are marked in the digest as V/B/U.

## 7. Falsifiers

This plan is wrong if any of these happen:

1. Contract-first routing lands at or below 0.53 mean recall@5 (a 20-point gain is the stated bar).
2. Fewer than 40 % of AST-derived adapters survive a second clean smoke run.
3. Paired abstention accuracy comes in under 0.60 — i.e. no better than the frontier's 59.5 %.
4. Retention replay after commits drops below 0.95, meaning our store has the same interference
   the frontier has.
5. Causal-lift A/B sign-flips between two task samples.

Any one of those kills its play. The point of writing them first is that we cannot move the bar
afterwards.
