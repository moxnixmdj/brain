# Searched by content, not by name. The premise is proven — and it kills my own best bet.

**2026-11-24 · `arena/283e85a5-brain`**

You told me twice to look under unfamiliar names. My previous searches used *my*
vocabulary — `verification`, `memory`, `computer_use`, `coding`. Those are my words, not the
repo's. So I stopped searching names and started searching **what each module says it does**:
2,248 modules indexed, 1,821 docstrings parsed, cross-referenced against the 1,636-module
orphan list.

**The result is a set of modules whose entire purpose is to settle a question — and the
question you asked is one of them.**

---

## 1. What I found, in the order it hurts

### `learn_or_read_v1` — 153 lines — **ORPHANED**

> *"WHEN YOU MUST LEARN, AND WHEN LEARNING CAN ONLY HURT. The owner asks, again: 'after he
> does them at least once, he would learn all of those permanently — so we solve everything
> on a computer?'"*

It answers, with a measurement on **130 real MiniWoB pages, same seed, same budget**:

| arm | result |
|---|---|
| zero experience, **reads the instruction** | **66/130 — 51%** |
| explore-to-one-success, then generalise | 78/130 — 60% (demonstrable pages only) |

Then the intersection, which is the actual finding:

| | count |
|---|---|
| pages where exploration found a success | 78 |
| …of those, **reading already wins** | **57 (73%)** |
| …where reading loses | 21 |
| pages exploration **never** reached | 52 |
| …**won by reading alone** | **9** |

> *"On 57 of 78 demonstrable pages, learning has nothing to add. The instruction already
> determines the action; acquiring a policy there is work whose only effect is to make the
> machine depend on a stored procedure instead of reading the page."*
>
> *"Nine pages are won from the instruction that exploration never demonstrated… on these
> pages there is no try to learn from, and the sentence suffices."*

Its conclusion is a **decidable pre-action rule with no threshold and no state**:

> learn a policy **only** where reading the instruction fails to determine the action;
> read the page everywhere else, and **never** replace the reading with the stored procedure.

### `what_one_experience_buys_v1` — 203 lines — **ORPHANED**

> *"ONE EXPERIENCE BUYS ONE BIT OF IDENTIFICATION. THE PRICE OF A TASK DOES NOT FALL."*

Measured 2026-11-16 over 78 tasks / 175 recorded steps, from the V5 receipt:

| | |
|---|---|
| descriptions still fitting a step | min 1 · **median 51** · max 255 |
| **mean bits to identify one step** | **5.43** |
| **steps needing more than one bit** | **174 of 175 (99.4%)** |
| reuse across steps | 149 descriptions → 96 distinct (**1.55×**) |
| **does the vocabulary saturate?** | **no** — first 39 tasks = 43 descriptions, last 39 = 53 *more* |
| **cost per task** | **flat at 1.23 new descriptions** |

> *"The reuse is real and it is worth 1.55×, and 1.55× is not a mechanism that compounds to
> zero. **The unit of permanent memory is one bit, a page needs about six of them, and most of
> those bits are private to the shape of that page.**"*

**This is the answer to the central question of the mission, it was measured three months of
work ago, and nothing can reach it.**

### `does_experience_compound_v1` — 307 lines — **ORPHANED**

> *"Does one experience make the next task cheaper? Measured, in bits, across a real run."*

A third module on the same question. Three modules answering the question you keep asking,
all unreachable.

### `capability_forge_v1` — 822 lines — **reachable, but starved**

Its own words: *"Seventy-four capabilities, every one written by hand. What is learned is the
choice among them, and that is not what was asked for… A CAPABILITY IS A HYPOTHESIS THAT
SURVIVED ATTEMPTS TO KILL IT."*

Five admission tests: contract inferred by AST (not authored), runs on ≥2 real inputs,
deterministic, artifact re-read and hashed, **and it can be killed — a corrupted input must be
refused.**

**I ran it on 12 dormant modules. 0 admitted, 12 refused.** And the reasons are structural,
not about the modules:

- **7 of 12: `NO_ENTRYPOINT`** — the forge only admits modules exposing `run(args, root)`.
  Anything with a different signature is invisible to it.
- 3 failed on missing environment preconditions (browser URL, OCR language scope).
- 1: `NameError: name 'canonical' is not defined` — a load-path bug.
- 1: `VACUOUS__FOUND_NOTHING`.

**Third wiring gap found.** The mechanism for turning orphans into capabilities exists, is
reachable, is well-designed, and can only see a fraction of the modules it was written to
convert.

---

## 2. The research converged on the same conclusions independently

This is the part that makes the premise defensible rather than hopeful. I did not fit our
modules to the literature; I searched the literature for the questions our modules answer.

| our orphaned/reachable module | what it concluded | independent 2026 source that concluded the same |
|---|---|---|
| `learn_or_read_v1` | learning displaces correct reading; decide **before** acting | **The Regression Tax** (arXiv 2607.22520, 5,832 runs): 553 gains vs **324 regressions = 59% cancelled**; **grounding displacement** is **72.8%** of OfficeQA-Pro regressions; *"the best-performing skills win primarily by regressing less"* |
| `learn_or_read_v1` (the 9 pages) | reading wins where exploration can't reach | same paper: failures concentrate at **grounding**, not method; *"existing skills over-emphasize procedural guidance — the stage least often responsible for failure"* |
| `what_one_experience_buys_v1` | abstraction matters; raw instances don't compound | **When Continual Learning Moves to Memory** (2604.27003): *"abstract procedural memories transfer more reliably than detailed trajectories"*, *"negative transfer disproportionately harms hard cases"* |
| `applicability_v1` *(reachable)* | *"Learn WHEN a remembered plan applies, from outcomes"* | **MCMA** (ACL 2026 Findings, 2601.07470): *"treats memory abstraction as a **learnable cognitive skill** rather than a fixed design choice"* — hierarchical levels, **selective reuse** |
| `learn_or_read_v1` refusing to store | silence/not-learning as a first-class action | **Meta proactive memory agent** (Jul 2026): *"what actually matters isn't remembering more, it's **knowing when to speak up**"* — **+8.3 pts Terminal-Bench**; silence as explicit action |
| `transition_system_identity_v1` — 269 L — **ORPHANED** | *"Are two environments the same machine? An exact decision procedure, plus the transfer it permits."* | **BIFROST** (2607.01410) & GBSM: cross-domain **bisimulation** for zero-shot transfer. Ours is the *exact* decision procedure they approximate with a learned metric |
| `capability_forge_v1` | *"a capability is a hypothesis that survived attempts to kill it"* | **VerIbmc** (2606.16886): symbolic phase solved **75 problems with no LLM call at all**; +36 for the weakest model |

### And the sharpest one

**Meta needed Claude Opus 4.6 as a trained "memory steward" to buy +8.3 points on
Terminal-Bench** by learning when to stay silent. **`learn_or_read_v1` buys the same effect
with a decidable predicate, no parameters, no state, and no model calls.** A trained model
to learn what a two-line test can decide.

That is the entire strategic position: **the frontier is spending inference to learn things
that are decidable.** That is where we can be ahead, and it is the only place.

---

## 3. My previous BET 2 is dead. Replaced.

I proposed: *"make the store's retrieval key the precondition signature so it compounds."*

**`what_one_experience_buys_v1` measured that this does not work.** Reuse is 1.55×, the
vocabulary does **not** saturate, and cost per task stays **flat at 1.23**. A better key
lowers the *price* of a description already paid for; it does not lower the *number* a new
task needs. **My bet was aimed at a mechanism that was measured to be 1.55× and no more.**

The replacement is not a better store. It is **a decision about whether to store at all.**

---

## 4. The plan, corrected

### BET 1 (new, #1) — Ship the read-or-learn decision as a measured capability

**Why it can win:** the frontier's own best result here (+8.3 pts) required a frontier model
as a memory steward. Ours is a predicate. If it holds, it is the same effect at **zero
inference cost**, which nothing in the literature does.

**What to do:**
1. Promote `learn_or_read_v1` and `what_one_experience_buys_v1` into the declaration registry
   (both currently orphaned).
2. Wire `decide()` **in front of** the store's write path: if `READ`, forbid the write.
3. Measure on the 130 MiniWoB pages we already have receipts for, **as an ablation**: store-on
   vs store-gated-by-`decide()`. The prediction is +2 to +4 points *and* a 59%-of-errors
   reduction in exactly the grounding-displacement class the Regression Tax paper names.

**Falsifier:** if gating does not beat ungated by **≥2 points** on the 57 pages where reading
already wins, the module is wrong and should be retired. **This is a one-week test that either
validates our most important orphan or kills it.**

### BET 2 (replaces mine) — Exact bisimulation instead of learned bisimulation

`transition_system_identity_v1` (269 L, orphaned) is an **exact decision procedure** for
"are two environments the same machine". BIFROST and GBSM learn a *metric approximation* to
the same thing, with an encoder and a policy. Ours is a decision procedure with a proof.

**Unusual and testable:** on our existing MiniWoB runs we have per-page transition traces.
Compute the exact bisimulation quotient between page families and ask whether the quotient
predicts the 69 "carried by another task's skill" cases from the store experiment. **If the
quotient partitions those 69 cases better than goal-text similarity, we have an exact
replacement for a learned metric.**

**Falsifier:** if the quotient does not beat goal-text similarity on held-out pages, drop it.

### BET 3 — Teach the forge to see partial contracts

The forge is right to demand a killable hypothesis. It is wrong to demand one signature.
Extend `contract_of` to infer entry points from any callable with inferable parameters
(`ast` already does the real work), then re-run the 12 that were refused: the 7
`NO_ENTRYPOINT` refusals are the ones to watch. **Prediction: ≥4 of 12 admitted.** If it
admits things that cannot be killed, the forge's premise is broken and we learn that.

### BET 4 (unchanged) — Second localiser organ + test-import closure

Rank-1 file is 42.8% vs SOTA 81.3% combined; Agentless's own ablation shows combining two
organs beats either by ~3 pts (78.7 prompting alone / 67.7 embedding alone / **81.3 combined**).
Adding the failing test's **import closure** is a third signal I have not seen in the
literature. Target >65% rank-1; falsified below 50%.

### BET 5 (unchanged) — Zero-execution verification

Dockerless (2026) reports **62.0/50.0/35.2%** resolve on Verified/Multilingual/Pro *without
executing*. We hold **17 caught pass-and-are-wrong** repairs — a ready-made adversarial set.

---

## 5. What the census says about the plan, in one number

**1,636 of 2,247 runtime modules cannot be reached.** Of the modules whose docstrings *settle a
question*, 10 of 20 are orphaned. Of the modules that state a measured benchmark figure, the
two most important are orphaned.

So the answer to "how do we get ahead" is not "invent something new." It is:

> **The questions that decide the strategy have already been answered and measured in this
> repository. They are behind a wall of 1,636 unreachable files, three of which are wiring bugs
> rather than research problems.**

Every one of those three wiring bugs is a few files wide:
1. a 7-file list that should be a 723-file graph (**fixed this session, and it turned a red test green**);
2. a self-play module holding the operator-swap table that the repair chain never calls (**identified**);
3. a forge that can only see one function signature (**identified, with a fix proposed above**).

---

## 6. Honest limits of this document

- The 2026 papers cited are recent and some are preprints; I have quoted their reported
  numbers, not reproduced them.
- `learn_or_read_v1`'s 130-page measurement is a producer-run local result, not a leaderboard.
  Its own docstring says so and refuses to be a threshold tuned on its own test set. I am
  treating it as a hypothesis to falsify, which is what its author built it for.
- **I have not measured the gating ablation.** BET 1 is a prediction with a named falsifier,
  not a result.
- The 0/51 hard51 number remains unexplained until hard51 is re-run; no Docker here.

**The one-sentence plan:** stop building mechanisms, start running the verdict modules —
beginning with the one that says, with numbers, whether learning should happen at all.
