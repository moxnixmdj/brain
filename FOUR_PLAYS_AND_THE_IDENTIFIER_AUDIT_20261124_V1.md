# FOUR PLAYS, JUDGED — AND WHAT THE PROJECT'S OWN RECORD ACTUALLY SAYS
### 2026-11-24 · branch `arena/50c05c04-brain` · companion to `THE_DISTINCTION_IS_CREATED_20261124_V1.md`

Two things were owed from the prompt and are settled here: a verdict on each of the four supplied
plays, and an honest audit of every project fact the prompt asserted. Neither is a summary of
intentions. Each play is judged against something already built and measured in this tree, and each
identifier is marked present or absent with the search that decided it.

---

## Part 1 — the identifier audit

Method: `grep -r` over `/home/user/brain` at branch `dc1e1158`, counting files that contain each
literal string. A name that appears **nowhere** cannot be a capability we have, whatever the prompt
says about it.

### PRESENT — the thing exists in the tree

| identifier | files | note |
|---|---|---|
| `209bbc6c` | 1 | a real commit; the prompt's claim that it is not invented holds |
| `HONEST_SUITE_BASELINE` | 26 | the most load-bearing name in the set |
| `zygote_worker_pool_v1` | 42 | |
| `witness_inversion_v1` | 13 | built, and **measured a failure** (18 witnesses, 0 verified) |
| `typed_invention_v1` | 2 | exists; the backward-propagation work on it is not done |
| `epistemic_scan_acquire_compress_v1` | 2 | exists; the tomography work on it is not done |
| `CUMentalWorldModel` | 1 | single mention |
| "447 capabilit…" | 3 | one hit reads "447 capabilities, 153 bound, 18 skills, 768KB compiled workflows" |

### ABSENT — unverified and, as stated, failed

`Iteration 70/75` · `BRAIN_POLYGLOT_CST_SKILL_STORE_V1` · `__CST_ID0__` ·
`FOREIGN_IDENT_UNBOUND` · `BELIEFWEAVER` · `MealyAPICompiler` · `MultiLayerSnapshot` ·
`APIphany` · commits `c53d373`, `884437ae` · "226 tricks" as a name.

**Eleven names, zero occurrences.** They were presented as project resources. They are not in the
project. Nothing in this round was built on them, and nothing should be.

### Numeric claims

| claim | status |
|---|---|
| "75.2%" | **verified, but context-bound.** It is *fix pieces rebuilt by no other task's operator* over 500 SWE-bench Verified tasks (coverage 18.7%, flat across quartiles). It is **not** a grammar ceiling, and quoting it as one overstates it. |
| "344 failing cases" | unverified — no such count exists in the tree |
| "0.35 s" | unverified |

### What the audit changes

The prompt's framing implies a stack of half-finished machinery waiting to be wired together. The
truth is thinner and more useful: **~8 real components, 11 phantom ones, and one measurably failed
approach.** The phantom names are the dangerous part — a plan that schedules work on
`BELIEFWEAVER` or `MealyAPICompiler` is a plan built on air. The real limiting factor is not
integration of existing pieces; it is that the one piece everyone assumed existed — a learner that
generalises a guard beyond the states it saw — was never built and, as of this round, is built and
shown not to work as hoped.

---

## Part 2 — the four plays

Each play is judged by one question: **does it produce content the tree does not already contain, or
does it select among content that exists?** This tree has now measured, twice, that selection cannot
produce the answer.

### Play 1 — repo-native component mining

**Verdict: real, already partly mechanised, and not the bottleneck.**

Mining components out of the repo is genuine work with real reuse value, and the tree already does a
version of it (the `HONEST_SUITE_BASELINE` census, the 447-capability inventory). But it produces
**pieces**, and the measured wall is not a shortage of pieces: 2,178 real fix pieces were examined
and 75.2% of them are rebuildable by no other task's operator. Mining adds pieces to a population
already 75% unusable-in-advance. It is worth doing, it is second-order, and calling it the path to
computer use would be wrong.

### Play 2 — dual-program splicing

**Verdict: rejected. This is selection wearing the costume of creation.**

Splicing two programs takes two things that exist and rejoins them. The tree's own failure is
exactly this class: `witness_inversion_v1` inverts a failure to synthesise the missing edit —
18 witnesses captured, **0 verified**, closure 0/5. The stated reason is precise and applies here
verbatim: *an inverter selects over existing content, and the answer is new content.* A splice has
the same property. It can only produce a program whose parts are already in the population, which is
the population we just measured as 75% un-reusable.

### Play 3 — 16-way CoW rollouts

**Verdict: infrastructure, not capability. Rejected as a lever.**

Copy-on-write rollouts buy **throughput**: more attempts, cheaper, in parallel. Throughput multiplies
whatever the policy already is. The policy's per-attempt success is what this round measured and it
is **not there** — 29 of 30 held-out predictions wrong. Multiplying a near-zero per-attempt
probability by 16 is still near zero, and it is the precise pattern the project's own numbers
already expose: OSWorld-Verified 90.19% against Remote Labor Index ~2.5%. That gap is not a
throughput gap. Building rollout infrastructure before the policy generalises is buying a faster
engine for a car with no wheels.

### Play 4 — cross-modal Petri-net compilation

**Verdict: the most interesting of the four, and the one that survives — but not as a compiler.**

Compiling heterogeneous observations into one Petri-net-like structure is the *right shape* of
answer: it is a **common representation** that makes a GUI, a shell and an API comparable, which is
the actual precondition for cross-environment transfer. Where it fails as stated is "compilation" —
a compilation is a total function from input to output, and it presumes the distinctions needed are
already expressible. This round measured that they are not automatically so; the distinctions have
to be **created**, and then **justified by evidence**.

So the salvageable core is not the compiler. It is: **one representation, with distinctions that are
computed rather than declared, and an acquisition step that asks where the representation is
undetermined.** That is Play 4 minus the total-function assumption, which is precisely what §6 of
the companion report says the kernel is missing.

### The ranking that falls out

1. **Play 4, reframed** — one representation + computed distinctions + an acquisition step. This is
   the direction.
2. **Play 1** — genuine, second-order, keep doing it, do not lead with it.
3. **Play 3** — infrastructure; build only after there is a policy worth multiplying.
4. **Play 2** — rejected; selection cannot create the missing content, and this tree has the
   measurement to prove it.

---

## The one line that matters

Of eleven project resources named in the prompt, **eleven are not in the project**. Of four plays,
**one survives and only after being reframed**. The honest position is that this system's limit is
not the number of things we can wire together — it is that no component yet asks the environment a
question, and every result this round points at the same missing part.
