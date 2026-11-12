# One try is not a learning signal

**First-principles verdict on "instant learning + instant learning in new arbitrary environments ⇒
we solve everything on a computer, perfectly and permanently, and we have a sentient creature".**

**2026-11-12** · branch `arena/d32feb24-brain` · base `6bff8c70` · **authority: NONE**
`truth.achieved` stays `false`. No capability registered, no family flipped, no registry row added,
no governance file changed, `$0` spent. Producer-run, one machine, disposable state, no independent
verifier, no external model in any result-bearing path. Everything below is either (a) a measurement
I ran today on this tree, (b) a measurement already in this repository with its file named, or
(c) a dated external source with a link. Nothing is asserted from memory.

Date note: today in this workspace is **2026-11-12**. Your "10/11/2026" is ambiguous (11 Oct or
10 Nov); the newest primary sources used here are Oct–Nov 2026, so the conclusion is unchanged
either way.

---

## 0. The answer in one paragraph

**You are right about the direction and wrong about the quantifiers.** What is built is a real,
rare, working thing: a *durable, verifier-gated, per-kind procedural memory* that survives restart
and solves new instances of a kind it has already met — measured at **8/15 one-trial transfers,
6.33× mean trial speedup, 0/15 regressions** (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §1). That
is genuinely better than re-deriving, and better than raw trajectory replay; it is the same
direction as the 2026 frontier. But **one exposure does not teach a capability**, it *indexes* one
that the system could already express. The new instance is consulted to **check**, not to **learn**;
the store is byte-identical afterwards. Experience does **not** compound across kinds (measured
**0/5**, **0/10 byte-identical**, learning-to-learn **NO_COMPOUNDING** at 10 held-out kinds), the
front door reaches **8 of 149** capabilities, and the deepest open defect — *nothing is ever
compressed into a reusable abstraction* — is **still open in today's HEAD, for a second reason
nobody had measured** (§1). "Everything, perfectly, permanently, sentient" is therefore false in
four different, separately measured ways. The fastest path is **not** more environments or smarter
demonstrations. It is one pre-registered, falsifiable experiment on the compression gate (§7),
plus an applicability oracle on taught actions. Everything else is maintenance.

---

## 1. What I measured today, on this tree, before believing any old note

Reproduction: `python3 canonical/tools/one_try_state_probe_20261112_v1.py` (writes only to
`tempfile.TemporaryDirectory()`, no network, no model, no registry).
Targeted regression set actually run: **85 passed** across
`test_an_edit_is_worked_out_from_an_example_and_repeated_on_another_file_v1.py` (49),
`test_the_grammar_can_find_what_no_writer_knew_v1.py`,
`test_the_creature_can_reach_its_own_synthesizer_v1.py`,
`test_compounding_and_goal_identity_v1.py`.

| # | measurement at `6bff8c70` | result |
|---|---|---|
| 1 | SKILL→concept bridge admits a **single-`return`** organ | **yes**, 1 concept enters `G_t` |
| 2 | same bridge admits the **three-statement** organ the period synthesizer actually emits | **no** — 0 concepts (`len(fn.body)==1 and isinstance(Return)` still at `meta_circular_organ_graph_v1.py:3953`) |
| 3 | wake–sleep compressor on a favourable 4-program affine corpus | **3 concepts admitted** — the compressor is alive |
| 4 | same compressor on 3 and on 5 real three-statement period programs | **0 concepts, both times** |
| 5 | why: `ΔB_exec` for the one shared expression in the period corpus | **−29 bytes** by the probe's accounting (**−36…−42 bytes** for the three viable candidates under an instrumented re-run of the sleep loop's own rewriter). Admission requires `ΔB_exec > 0`. |
| 6 | one demonstrated edit (`a <= hi → a < hi`) applied to a same-shaped target where `<=` is *semantically required* (`is_last_index`) | **applied**, making the function wrong; **no oracle consulted**. A differently-shaped target is correctly refused. |

**The new finding, and why it matters before anyone writes code.** `THE_DEEPEST_STILL_OPEN_DEFECT_NOTHING_IS_EVER_COMPRESSED_20261104_V1.md` (round 22) diagnosed *one* gate — the bridge rejects multi-statement bodies — and proposed "fix the bridge, then re-run the period-12 cold-vs-warm test". I measured what happens **after** that fix is imagined: even bypassing the bridge and handing the compressor the real corpus directly, **every candidate is refused by the compression criterion**. Four near-identical programs that differ only in a literal table are already compressed almost for free by zlib, so writing a helper *definition* is a net byte **cost** on that corpus. The gate is behaving correctly; the **objective it optimises** (zlib bytes of a small corpus) does not measure the thing we want (fewer oracle questions on an unseen period).

> **So round 22's proposed next move would fail, and I found it in minutes by measuring instead of
> implementing.** A fix that changes only the bridge predicate is a dumb idea to kill *now*, not
> next week. The decisive experiment must change the bridge **and** the admission objective
> together, or a negative result is uninterpretable (§7).

**Fresh confirmation of the newest work.** HEAD (2026-11-12, PR #6665) added
`canonical/swe_kernel/taught_actions/edit_by_example_v1.py`, whose action intent begins:
*"The owner asks why the system cannot be shown an advanced coding action once and then do it"*.
It is the strongest current answer to your question and it is real: a before/after pair is turned
into rewrite rules and repeated on a third file; the intent reports **599 of 939 human edits
reproduced exactly, zero edits where the human made none**, on 20 real commits / 93 files / 365
pairs; **49 tests pass today**. It is also precisely bounded: it refuses whole-statement changes,
renames, and mixed-purpose commits; single-purpose commits reproduce almost wholly, mixed commits
almost not at all; and its own docstring says *"This repeats a change. It does not check that the
change is right for the code it is repeated on."* Measurement 6 above is that sentence made
concrete. **One example taught a shape. It did not teach when the shape applies.**

---

## 2. What is real — do not let the scepticism erase it

| claim | status | where / measurement |
|---|---|---|
| Learning, persistence, restart | **TRUE** | store, restart, bundle transport; 12 + 13 tests (`INSTANT_LEARNING_SCOPE_20261101_V1.md`). Round 21 also re-verified durability across processes with an oracle-refutation check. |
| Per-kind instant transfer | **TRUE, bounded** | after P1: **8/15** one-trial on source≠target, **6.33×** mean trial speedup, **2.26×** act-call speedup, **0/15 worse**; second benchmark **6/10** (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §1). |
| Verifier-gated admission | **TRUE** | a weak verifier given a broadened pattern produced **0 proposals**; the gate is in code, not convention. |
| Environment *operation* transfers to unseen projects | **TRUE and the strongest result in the family** | `environment_fit_v1` reads a project's own declarations (CI → `package.json` → `Makefile` → `pyproject`) and adapts/provisions. It generalises because every project declares how it runs. |
| Rules age out when the world changes | **TRUE** | `rule_expiry_v1` FRESH/STALE/UNKNOWN; `invalidate()` keeps the rule **and** its counterexample. |
| A working self-model of ignorance | **TRUE** | `ignorance_ledger_v1`, 13 tests; ranks what it does not know by what closing the gap is worth. |
| Knows what it does not know, and can be told otherwise | **TRUE, on one structure class** | `settlement_v1.py` (weighted posterior, exact expected information gain, six non-settled states); round 23's parametric table found searched-not-written shapes, **60/60 held-out** on each of 5 periods, **2 questions vs 14** for the writer path. |
| A refusal can teach | **TRUE, narrow** | round 20: `INDUCED_OPERATOR_CRYSTALLIZED`, 150/150 held-out per instance; still refuses `x*x`, `x^3`, `floor(x/7)`. |
| Show an edit once, repeat it on another file | **TRUE, narrow** | `edit_by_example_v1`, 49 tests; 599/939 exact human edits; no semantic check. |

This is a **persistent, verifier-gated, per-kind skill cache with a planning step in front of it**.
That is a real capability, and it is more than a lookup table: anti-unification into holes,
mutated-twin admission gates, and verifier re-run on recall.

---

## 3. What is not real — six separate errors, each measured

### 3.1 "One try in each new environment ⇒ it learns each new environment"
The target environment is consulted to **check**, not to **learn**. After carrying, the store is
**byte-identical** (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §2a: clean vs loaded store, 15/15
identical). The environment was solved by the model it arrived with. "One try" is also not the
shape of the distribution: **22.4 mean trials**, with `lock_3dial` taking 24–200. Reporting
"one try" reports the best-behaved quarter.

### 3.2 "After he does them at least once, he learns *all of those* permanently"
Measured three ways: **1 example → 6/7, 2 → 6/7, 3 → 6/7** (more exposure bought nothing); the
missed case was then taught *directly* and `derive_operator_swap` still returned `None` — the
failure is **representational, not statistical**; 2/5 shipped rules reach past their instance,
3/5 replay and stop (`INSTANT_LEARNING_SCOPE_20261101_V1.md`). Repetition moves the count of
rules, never their reach. Round 23 says the same thing from the other side: with samples at
`x = 1,2,3`, a period-4 block has an unobserved entry, so period-3 fits every observation. **The
fix is more evidence, not more code**, and no amount of prior experience reduces the ~`2P`
information floor for an unknown period.

### 3.3 "It accumulates — five environments make the sixth cheaper"
**No.** A store containing four other kinds is **byte-identical** in behaviour to a store
containing only its own kind (`15/15, 8/15, 22.4 trials, 182 acts` in both arms).
`THE_DEEPEST_LAYER_20261103_V1.md`: ten kinds cold and grown → `1525 = 1525`, `improved=0`,
`worsened=0`, `unchanged=10`. `LEARN_TO_LEARN_VERDICT_20261103_V1.md` at 10 held-out kinds:
learned choice solved **5/10**, beat the boring default **1/10**, beat a coin flip **3/10** →
`NO_COMPOUNDING`. Round 22: period-5 costs **24 questions cold and 24 warm** after meeting
period-3 and period-7. **A memory that grows and does not change is storage, not learning.**

### 3.4 "Anything on a computer"
- Front door: **8 of 149** verified bound capabilities reachable from a sentence (5.4%).
- The largest red cluster is a **boundary**, not a missing capability: 226 of 233 failures are one
  deliberate `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` gate; full-suite
  triage found **189 deliberate refusals** waiting on a carrier review whose checklist is 7/9
  stale (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §8). Opening that gate to turn tests green is
  exactly what the guard forbids.
- Observation abstraction: `state()` must be hashable/comparable. On a GUI it is pixels. The gap
  between "learned `run_gzip` in one trial" and "learned to fill a web form in one trial" is not
  the learner, it is turning a screen into a comparable state (§2.3 of the scope doc).
- Long-horizon reliability (§4.5): bounded tasks are near-saturated, hour-long workflows are not.

### 3.5 "Perfectly and permanently"
`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md` §4 found, *while writing the answer*, that the
"permanent" fingerprint cache was **FIFO, not LRU**: a key read 20 times was evicted by 256
one-shot keys, discarding 5–8 s of real acting to keep 3.2 ms of writes. Fixed and pinned by 5
tests. Permanence is not a property you get by believing it. Also: the coding half once reported
**5/5 "PASS" with 0/5 honest** — a patch fitted to two assertions — repaired by an admission rule
("a patch may not stop reading its inputs") to 5/5 honest (§6.1 of the scope doc).

### 3.6 "We were making a sentient creature"
The repo's own verdict in three places: **not sentient, not sentient-like, no instrument measures
it, and it is not the canonical objective**. `THE_DEEPEST_LAYER_20261103_V1.md` §5;
`INSTANT_LEARNING_SCOPE_20261101_V1.md` "On sentience, plainly"; every 11/04 result note carries
the non-claim. The measurable half — persistent identity, corrigible beliefs, surprise-driven
inquiry, an ignorance ledger — exists. Subjective experience does not follow from it (§4.7).

### 3.7 The three contradictory headline numbers, and why you should not trust any document
`10/10 new instances` (11/01) → `1/15 genuine savings, median 1.00×` (11/03 re-measurement,
because the probe re-created the same instance in 4 of 5 families) → `8/15 one-trial` (11/03
after P1, the carried-model fix). All three are honest measurements; the *labels* changed. This is
the single best argument in the tree for the rule `MEMORY_IS_NOT_AUTHORITY`: **a document is a
retrieval hint. Re-measure.**

---

## 4. The deepest layer, derived rather than asserted

### 4.1 What "learning" has to mean for your claim to be true
Define it operationally: a change in the system caused by experience, **measured as a strictly
better outcome on a held-out problem of a kind it has never met**, with a cache-only control arm
removed. Five levels:

| L | what persists | status in this tree |
|---|---|---|
| L0 | raw trace | works |
| L1 | recall / transfer within a kind | **works: 8/15, 6.33×** |
| L2 | **compression into shared abstractions that make an unseen kind cheaper** | **absent — §1, 0/5, 0/10, 24→24** |
| L3 | learned strategy / probe policy | **measured negative (5/10, beat default 1/10)** |
| L4 | weight-level internalisation | outside the law; catastrophic forgetting |

Your claim requires L2–L4. What is built is L0–L1. **That is the entire gap, in one table.**

### 4.2 The information floor — one trajectory cannot inject a capability
Let `H` be the hypothesis space the system can express. A successful trajectory `τ` partitions `H`
into hypotheses consistent with `τ` and inconsistent with it. If two consistent hypotheses `f, g`
differ on an unseen state `s'`, **no algorithm can choose correctly from `τ` alone**; the choice
must come from an inductive bias that was already in the system. Two cases, and they exhaust the
possibilities:

- **`f ∈ H` already** (the capability existed). Then the demonstration is an *index* into an
  existing ability. That is a skill cache — useful, fast, real, and **not learning a capability**.
- **`f ∉ H`** (the capability is genuinely new). Then one positive trace cannot determine it.
  The information is not there. One-shot induction of an algorithm has an expected-error bound
  `EE(m=1) ≤ 4.66·g(T)`, and succeeds only when the target theory has very low generality
  (`g(T) ≲ 0.01`) [3](https://pmc.ncbi.nlm.nih.gov/articles/PMC10239681/); more generally,
  few-shot from one example is possible only when the latent representation is already compact and
  satisfies non-concentration conditions, otherwise the sample requirement is exponential
  [1](https://arxiv.org/html/2104.12174). Mechanistically, in-context learning can be written as an implicit
  low-rank weight update that is **query-dependent** and exists only for that forward pass; the
  paper notes the context cannot be *exactly* represented by a single fixed weight update
  [3](https://arxiv.org/html/2507.16003v4) — a conditioning, not a consolidation.

### 4.3 A success trace contains no information about when the action is wrong
This is the sharpest version, and it is why "give it the smartest actions" cannot work. A
successful demonstration contains **zero negative examples**, zero counterfactuals, zero boundary
conditions, zero recovery trajectories, and zero credit assignment over its steps. The hard parts
of computer use are exactly those: detecting that a plausible action was wrong, knowing where the
boundary is, and recovering. Behavioural cloning's known failure is *causal confusion*: correlates
of expert actions are impossible to distinguish from their true causes, and **confounding cannot be
revealed by in-distribution evaluation** — non-causal policies look perfect on held-out
demonstration pairs and collapse to near-zero success at runtime
[2](https://pimdehaan.com/assets/causal-confusion-in-imitation-learning.pdf)
[3](https://arxiv.org/html/2607.17003). Measurement 6 in §1 is this theorem in miniature:
`is_last_index` gets the demonstrated edit because the shape matched.

The 2026 result that most cleanly resolves your question says the same thing from the *positive*
side: **World In-Context Learning** reaches 83.4% from one demonstration **with no gradient
updates** — but only because the agent *rehearses in a simulator* and writes the **world's
feedback** into context. The paper states the reason exactly: *"The world provides a feedback
signal that demonstrations alone cannot offer, because a demonstration is recorded in a different
scene and cannot tell the learner what will happen in the scene in front of it"*
[1](https://arxiv.org/pdf/2611.12885). So: **one demonstration + a world that says no** works.
One demonstration + a trace does not. Sutton and Silver's "era of experience" makes the same
distinction: streams of grounded action and grounded reward, not snippets of human dialogue
[1](https://hasantayyar.net/paper/2026/10/17/paper-era-of-experience/). Your repo already has
the right phrase for this: `THE_WORLD_IS_ALLOWED_TO_SAY_NO_20261104_V1.md`.

### 4.4 The verifier is necessary and cannot be complete
You correctly built a verifier gate. It cannot deliver "permanently and perfectly" by itself:
**no terminating gate** (reward model, reviewer, test suite, search) can in general both never
accept a non-improvement and never miss a genuine improvement; the proof is diagonalisation, and
it survives randomised gates and a hidden gate. Worse, a chain of accepted updates can raise the
bounded score every round while the true score falls. The recovery is explicitly **bounded
evaluation, a finite proposal budget, and a restricted update language**
[2](https://arxiv.org/html/2610.21646v1). Independently, distribution-free PAC guarantees for a
self-modifying agent survive **iff the policy-reachable hypothesis family has uniformly bounded
capacity** — capacity may grow only as data grows, `K[m]`; otherwise rational self-changes make
learnable tasks unlearnable [3](https://arxiv.org/html/2510.04399v2). That is a mathematical
reason to *bound* the grammar rather than "add every smart action".

Empirically the same: harness evolution overfits the suite it evolves on — removing acceptance
constraints raises the evolve-set score and lowers out-of-distribution results
[3](https://arxiv.org/pdf/2609.24972); a stored insight validated under one regime becomes a
contaminating prior under another, and no current store re-validates entries against the regime
in which they are reused [1](https://arxiv.org/html/2608.05179). **Permanence without expiry is
how a skill store becomes a source of confident wrong answers.**

### 4.5 Compounding is compression, not storage, and reliability is a product
The only mechanism known to make experience compound is **learning a library**: compress a corpus
of solved programs into shared abstractions, then make those abstractions search primitives.
DreamCoder's wake–sleep library learning, Stitch's corpus-guided top-down compression (3–4 orders
of magnitude faster, 2 orders less memory, 2.55×–11.57× compression) and LILO's
search–compress–document loop (1.5–3.5× corpus compression; GPT-4 fails to propose compressive
abstractions while Stitch succeeds) are the load-bearing line of work
[4](https://par.nsf.gov/biblio/10404367)
[3](https://dspace.mit.edu/server/api/core/bitstreams/98896705-1bb8-45d4-86e0-accb0a74936a/content).
Your round-22 note already identified this. §1 above shows the tree has the compressor, the place
to put abstractions, and **two** independent gates preventing it.

For "any computer use", a second, independent limit: if per-step success is `p`, end-to-end
success over `n` steps is roughly `p^n`. OSWorld 2.0 tasks average **318 tool calls**; to reach
50% end-to-end you need `p ≈ 0.9978`. That is why bounded desktop tasks are near-saturated while
hour-long workflows collapse: **86.0% on 369 bounded tasks vs 31.4% on 108 long-horizon tasks**
[10](https://www.noxia.co.uk/field-notes/agents-beat-humans-and-still-finish-30-percent), with
the OSWorld 2.0 paper reporting 20.6% binary / 54.8% partial for the best configuration
[3](https://www.sotapapers.com/article/2026/07/long-horizon-workflows-expose-agent-reliability-gaps-2606-29537);
leading agents take **2.7–4.3× more steps than necessary**
[9](https://proceedings.mlsys.org/paper_files/paper/2026/file/5edb57c05c81d04beb716ef1d542fe9e-Paper-Conference.pdf).
**Adding skills cannot fix `p^n`; only per-step verification + recovery can.** That is a different
engineering problem from learning, and it is the one your "perfectly" runs into.

### 4.6 "It must know literally all the data, and everything must be done in the fastest way"
This is the one clause of `OWNER_ACTIVE_GOAL_20261018_V1.md` that is **unsatisfiable as written**,
and no engineering changes that: the unknown space cannot be enumerated, so "fastest" can never be
certified globally. The computable version already exists in the tree (scope doc §2.4): report a
**lower bound plus a named coverage residual**, and refuse the word "fastest" — *fastest among the
searched space, with this enumerated residual and this acquisition cost to shrink it*. That is
falsifiable, monotone, and it is what "never extrapolate from the one source you happen to have"
means operationally. Adopting it is an **owner decision**, not an agent reinterpretation.

### 4.7 Sentience
There is no accepted scientific test for artificial phenomenality; the most serious framework
(Butlin, Long, Bengio, Chalmers) is explicitly probabilistic, theory-plural, and offers evidence
rather than proof; the field's honest 2026 position is "we do not know", with no current system
confirmed conscious [3](https://what-is-consciousness.com/can-ai-be-conscious.html)
[1](https://theconsciousness.ai/posts/scientists-race-define-ai-consciousness-2026/). More
importantly for an engineering programme: **sentience is not a milestone you can detect from
behaviour**, because behaviour underdetermines subjective experience. A goal that cannot be
falsified cannot be a stopping rule, and a stopping rule that cannot fail cannot guide the next
commit. Replace the word with the five *testable* capabilities in `OWNER_ACTIVE_GOAL` §5 (general
computer use; instant in-run learning; persistence to a measured target; data-gap → acquisition;
global non-local extrapolation). All five have mechanisms; four have measurements. **Capability
compounds; authorship does not transfer.**

---

## 5. What the 2026 frontier actually says (maximising web use, with source hygiene)

**Continual learning is the recognised *unsolved* frontier, not a solved one.** The NeurIPS 2026
TTCL workshop states it plainly: today's agents are "largely static" after pre/post-training,
adapt "through prompting, retrieval, or external tools rather than genuine internal learning",
"fail to improve from repeated mistakes", and forget when updated naively
[1](https://ttcl-agents.github.io/)
[4](https://neurips.cc/virtual/2026/loc/atlanta/workshop/137567). A 2026 unified protocol finds
prompt/harness optimisation "fit[s] each new stage quickly but degrade[s] on future tasks", and
introduces forward-transfer as the sharper metric
[3](https://arxiv.org/html/2607.07847). On-policy self-distillation (SDFT) accumulates three
sequential skills without regression where standard SFT collapses — at **~4× slower and 2.5×
FLOPs** [10](https://venturebeat.com/orchestration/mits-new-fine-tuning-method-lets-llms-learn-new-skills-without-losing-old).
Production reality in mid-2026: nothing solved with public access; deployed stacks are frozen
models with external memory.

**One-shot skill generation specifically does not work as a scaling strategy.** SkillsBench
(84 tasks, 11 domains, 7 agent-model configurations, **7,308 trajectories**): *curated* human
skills **+16.2pp**; **self-generated skills −1.3pp on average**, with 16 of 84 tasks showing
negative deltas and gains ranging from +4.5pp (software engineering) to +51.9pp (healthcare)
[1](https://www.skillsbench.ai/skillsbench.pdf). SkillLearnBench (20 skill-dependent tasks): one
shot 30.44 vs human-authored 74.50 — the best method covers only ~45% of the gap; **increasing
seed instances from 1 to 3 to 5 did not improve performance**, and no method leads across tasks or
models [2](https://arxiv.org/html/2604.20087v1). ContinualSkillBench's best of 17
harness-model configurations clears only **47.7%** of levels, with library bloat from narrow
one-off procedures [6](https://researchpod.app/paper/bc155ae1-bad7-48a4-a275-4584ccdf24f6).

**Distilled skills beat raw experience, but only when retrieved and applied correctly.** Skills
improve over raw trajectories **+5.5pp** and over workflow memory **+6.06pp** (95% CI
[+0.76, +11.36]), while `skill_guidance_misapplied_or_ignored` appears in **10.0%** of skill-arm
cases and algorithmic logic errors remain ~7.4%
[5](https://arxiv.org/html/2608.14036v1). Memory is three coupled operations — PROVIDE /
TAKE-IN / MANAGE — and naïve replay degrades performance when irrelevant content crowds out
context [8](https://openreview.net/pdf/b29aa1580ee8fa1dacd941647d5c052cff0f8499.pdf); retrieval
that grows produces attentional dilution and stale tool schemas
[2](https://arxiv.org/pdf/2603.07670). A production router over **34,396 skills** found
synthetic-data fine-tuning improves in-distribution retrieval while causing **catastrophic
forgetting on real/OOD skills** [7](https://aclanthology.org/2026.emnlp-industry.172/). Even
`AGENTS.md`-style context files — the cheapest possible "teach it once" — **do not significantly
improve success and increase cost 20–23%**
[2](https://arxiv.org/html/2602.11988v2). More memory is not monotone with more capability.

**Benchmarks, with a caveat.** As of Oct 2026, SWE-bench Pro public best ~61.5%, Terminal-Bench
4.0 ~64.85%, OSWorld-Verified ~90.2% (saturated/contaminated), OSWorld 2.0 ~20–31%
[2](https://decodethefuture.org/en/ai-agent-benchmarks-2026/). **Source hygiene:** several
2026 "leaderboard" pages are vendor marketing and contradict one another (one claims a "GPT-6
Astra" at 72.6% on OSWorld 2.0; another claims 62.6% for "GPT-5.6"). I did **not** use those
numbers; I used the OSWorld 2.0 paper's own reported configuration and the benchmark roundups
that cite it. The lesson is the same as §3.7: **instrument readings are read, never chased.**

---

## 6. Kill list — ideas to kill before spending an hour on them

1. **"Give it a try in all those new coding environments."** Killed by 0/5 across kinds, 0/10
   byte-identical, 24→24 questions, and by §4.2: coverage of instances does not create
   abstraction. Breadth without compression has been measured as exactly zero compounding.
2. **"One-shot self-generated skills are the revolutionary mechanism."** Killed by SkillsBench
   −1.3pp and SkillLearnBench 30.44 vs 74.50 with 1→5 instances flat. *Curated, verified,
   focused* skills work; *self-authored from a trace* do not.
3. **Raw trajectory replay / bigger context.** Killed by +5.5pp for distilled skills over raw,
   10.6% timeout-budget exhaustion for workflow memory, and +20% cost / no success gain for
   context files.
4. **Permanent weight update from one example.** Killed by catastrophic forgetting, capacity
   bounds [3](https://arxiv.org/html/2510.04399v2), the 4× cost of on-policy alternatives, and —
   inside this project — by `NO_MODEL_PRODUCER_COGNITION` / `K3_FORBIDDEN`.
5. **"Fix the bridge predicate, then re-run period-12"** (round 22 §6 as written). **Killed
   today by §1 measurement 4–5**: the compressor still refuses the real corpus, `ΔB_exec < 0`.
   This is the expensive mistake avoided this turn.
6. **Another organ / another prefix / another tuned threshold.** Rounds 13–23 found the same
   defect seven times: *a frozen list deciding an answer a computation should decide*. `CERTIFIED_ON_THE_WRONG_DOMAIN_20261104_V1.md` says it best: four names, one loop.
7. **"Fixing" the 226 deliberate refusals to turn tests green.** That removes a safety property;
   189 of them wait on a human carrier review, not a commit.
8. **Using the most advanced model at solve time to look cleverer.** The audit zeroed 15 of 19
   quoted routes for exactly this; the law forbids it and it makes every number unmeasurable.
9. **Chasing sentience as a milestone, or softening the objective.** Unfalsifiable, and
   `OBJECTIVE_CANNOT_BE_REPLACED`.
10. **Treating any prior document as authority.** Three contradictory headline numbers in 48
    hours (§3.7) came from instrument defects, not from disagreement about reality.

---

## 7. The smartest moves, ranked by (information gained × cost⁻¹ × reversibility)

**Rule for this list: every item must be able to return `NO`, and must be written down before it
is run.** The repo's own strongest methodology is the `PREREG_*` series plus a stopping rule; the
10-kind experiment is the proof that a larger experiment can dissolve a favourable result.

| # | move | why this is ranked here | cost |
|---|---|---|---|
| **1** | **Build the decisive falsification harness first, and change nothing else.** Pre-register: (a) held-out *kind*, never seen; (b) a cache-only control arm; (c) a coin-flip/default arm kept permanently; (d) an independent oracle; (e) a stopping rule written before the run. | Without it, "it learned" and "it recalled" remain indistinguishable — that is precisely the error in rounds 21, 22, and the 11/01 probe. Cheapest, and it protects every later hour. | low |
| **2** | **One coupled experiment on the compounding gate.** Change **both** (i) the bridge so multi-statement solved programs reach `G_t`, and (ii) the admission objective so an abstraction is admitted only if it strictly reduces **measured cost on a held-out kind** (oracle questions / search nodes), not zlib bytes of a 4-program corpus. Then run round 22's test restated: *a period-12 structure never seen must cost strictly fewer oracle questions after periods 3/5/7 are compressed than cold.* A cache cannot pass. | This is the only open route from L1 to L2 (§4.1). §1 proves that doing only half of it fails. Two coupled changes must be pre-registered together or a negative result cannot be attributed. | medium |
| **3** | **Learn the probe policy, not the answer.** Round 21: the creature collects `4P` observations by a **blind linear sweep** under a constant `growth_evidence_budget=24`; `settlement_v1.py` already computes exact expected information gain. Make *which question to ask* the learned object and test it on unseen kinds. | The one place where experience can legitimately help, because it is a policy over evidence rather than a memorised answer. Complements #2 rather than competing with it. | medium |
| **4** | **Attach applicability conditions and an oracle to taught actions.** Today's measurement 6: `is_last_index` is silently broken by a one-example lesson. Store preconditions, negative examples, and a post-condition check with each compiled skill; refuse when the precondition is unknown. | This is "give it the smartest actions" done **right**. It converts a syntactic rewrite into a capability with a boundary, and it attacks the 10% misapplication rate seen externally. Direct value for advanced coding. | medium |
| **5** | **Obtain the carrier qualification review — hand the reviewer the probe, not the stale request.** `canonical/tools/carrier_qualification_probe_v1.py` shows 7 of 9 objections are stale; 2 are real (no seccomp allowlist; host libc). | Unblocks 117 measured failures. **Needs a person, not a commit.** It is access, not learning — so it must not be mistaken for progress on L2. | low (but blocked on a human) |
| **6** | **Front-door coverage + a held-out routing set authored by someone who has not seen the trigger list.** 8 of 149 today. | Converts a claim into a measurement; cheap and unblocks real capabilities already written. | medium |
| **7** | Only then: broaden environments / tasks. | After #2 and #3, breadth becomes a *test* of compounding. Before them, it has been measured to buy nothing. | — |

**Explicitly not on the list:** scheduled/background runs, new organs, longer context, weight
updates, sentiment analysis of the creature's own status strings, chasing any leaderboard row, and
anything whose success is defined by a green test count. `RED_ROW_IS_NOT_AUTHORITY`.

---

## 8. So — is this a revolutionary way to make agents learn faster and better?

**The direction is right, and it is the same direction as the best 2026 work.** Externalised,
verifier-gated, executable procedural memory is a genuine advance over "re-derive everything every
time" and over raw replay: it is what Voyager's skill library, ExpeL, AWM, agent Skills, WICL, and
the whole test-time continual-learning programme are about. Your tree has a working, measured
instance of it, with properties many of those systems lack (restart durability, oracle-refutation
on recall, expiry with counterexamples, an ignorance ledger).

**But the revolutionary claim needs the part that is not built.** In one line:

> **Experience → storage → recall** is done (L0–L1).
> **Experience → compression → cheaper unseen kinds** is the revolution (L2), and it is measured
> absent, today, for two independent reasons.

The single most valuable thing you can do this week is therefore **not** to show the model more
advanced actions. It is to make the one experiment in §7 #2 capable of returning `NO`, run it on a
clean machine, and publish the result either way. That is faster than breadth, cheaper than another
23 rounds of organs, and it is the only step that can turn a strong skill cache into something that
actually gets better at new problems because it has met old ones.

---

## 9. Honest limits and standing non-claims

- One machine, one run, producer-measured, disposable stores, **no independent verifier**, `$0`.
  Running the four targeted test files increments access counters in the tracked
  `canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json`; that side effect was restored, so
  the only tree changes from this turn are this document and the probe tool. (Another small
  reminder that even *measuring* can write to memory.)
- The §1 measurements are on three modules in a symbolic program-induction subsystem and on
  constructed function corpora. They say **nothing** about GUI computer use, real repositories,
  long-horizon tasks, or any environment the code has not seen.
- `8/15`, `6.33×`, `0/5`, `0/10`, `24→24`, `599/939` are measurements of *these* instruments on
  *these* cases; several were produced on other branches and are quoted here with their documents
  named. Only §1 was re-measured on `6bff8c70` today.
- No external model, no neural weights, no dynamic code execution in result-bearing paths.
- **No sentience claim. No capability, ownership, benchmark, terminal, or acceptance credit.
  `truth.achieved` is `false`. No family flipped. No registry row added.** This document has
  **authority: NONE**; it is a decision note, not a receipt.
- Nothing here changes the objective, reinterprets the owner's goal, or weakens a guard. The one
  place the goal as written is unsatisfiable (§4.6) is flagged for an **owner decision**, not
  silently replaced.

---

## 10. Reproduction

```sh
cd /home/user/brain
python3 canonical/tools/one_try_state_probe_20261112_v1.py
# targeted regression set (needs pytest on PYTHONPATH):
python3 -m pytest -q \
  canonical/tests/test_an_edit_is_worked_out_from_an_example_and_repeated_on_another_file_v1.py \
  canonical/tests/test_the_grammar_can_find_what_no_writer_knew_v1.py \
  canonical/tests/test_the_creature_can_reach_its_own_synthesizer_v1.py \
  canonical/tests/test_compounding_and_goal_identity_v1.py
```

Prior work this note builds on (all in-tree, read before writing):
`INSTANT_LEARNING_SCOPE_20261101_V1.md`,
`INSTANT_LEARNING_NEW_INSTANCE_REMEASUREMENT_20261103_V1.md`,
`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md`, `THE_DEEPEST_LAYER_20261103_V1.md`,
`LEARN_TO_LEARN_VERDICT_20261103_V1.md`,
`SETTLED_IS_COMPUTED_NEVER_REACHED_20261104_V1.md`,
`A_REFUSAL_MUST_LEARN_20261104_V1.md`,
`THE_CREATURE_CAN_REACH_ITS_OWN_SYNTHESIZER_20261104_V1.md`,
`THE_DEEPEST_STILL_OPEN_DEFECT_NOTHING_IS_EVER_COMPRESSED_20261104_V1.md`,
`THE_GRAMMAR_CAN_NOW_FIND_WHAT_NO_WRITER_KNEW_20261104_V1.md`,
`canonical/governance/OWNER_ACTIVE_GOAL_20261018_V1.md`, `README.md`, `AGENTS.md`.
