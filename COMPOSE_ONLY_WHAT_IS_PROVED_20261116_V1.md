# Compose only what is proved — 16 November 2026

**Authority: NONE.** Producer-run sandbox measurement on branch `arena/c7439a6e-brain`,
base `57a83e9e`. No capability registered, no family flipped, no weight touched,
`truth.achieved` unchanged. Independent verification is open. `$0`, no model, no network.

Receipts, every count folded from raw rows:
`COMPOSE_ONLY_WHAT_IS_PROVED_20261116_V1.json` (this run, twice — byte-identical box
tables under a pinned hash seed),
`canonical/swe_kernel/proved_composition_v1.py` (the rule),
`canonical/tests/test_proved_composition_v1.py` (16 green).

---

## The claim on trial

> Instant learning and instant learning in new environments are solved. Give the model
> the smartest actions, show each once, it keeps them forever — therefore all computer
> use and the most advanced software engineering are solved.

Asked of this project now for the ninth time. The direction is right; every "therefore"
is false. Five transitions hide in that sentence, each with a measured number:

| # | transition | measured | where |
|---|---|---|---|
| 1 | act at all — a first success exists | **55 of 92** held-out MiniWoB++ pages | `MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json` |
| 2 | one success ⇒ a rule for the next instance | **60.0%** vs 15.0% cache | `OPEN_BENCHMARK_ONE_SUCCESS_GENERALISATION_20261114_V1.json` |
| 3 | permanent storage ⇒ correct knowledge | ungated lesson **breaks a correct program**; gated one refused | `test_lesson_admission_gate_v1.py` |
| 4 | N verified skills ⇒ a verified sequence | two correct skills cancel (**no-op**), and — measured here — only **31 of 80** two-step attempts on this repository compose end-to-end | `SKILLS_DONT_COMPOSE_20261112_V1.md`, this receipt |
| 5 | a learned procedure ⇒ any computer use | best 2026 agent **20.6%** strict / 54.8% partial on 108 long-horizon tasks; near-zero beyond 2 hours | OSWorld 2.0, arXiv:2606.29537 |

Step 2 is real and large. Steps 1, 3, 4 and 5 are why "therefore" fails: a chain of five
factors multiplies, and a 0 in any position is a 0 at the end.

## What was built — the rule the receipts kept naming

`skill_sequence_verify_v1` answered half the defect (2026-11-12): it reads the TEXT of a
sequence after the fact and names no-ops and reverts. It cannot answer the question that
decides whether a sequence may run at all:

> does the second operation's premise still hold in the world the first one left?

`canonical/swe_kernel/proved_composition_v1.py` is the affirmative rule — the module
`WHAT_ONE_DEMONSTRATION_REACHES_20261116_V1.md` §6.4 named as next ("compose only what
is proved … its own reach measurement"). Five checks per step, in order, on the world
after the previous effects:

1. **PREMISE** evaluated on the current state — dead premise refuses **before
   execution** (apply is never called; the test asserts `applied: False`).
2. **APPLY** — no change is refused (`STEP_DID_NOTHING`).
3. **HISTORY** — returning to a state the text has already been in is refused, named
   by the step it went back to.
4. **PROOF** — the step's own proof predicate must hold on the state it produced.
5. **SURVIVAL** — every earlier step's proof is re-checked after this effect.

A proof is a caller-supplied predicate; the organ enforces that proofs are required and
re-checked, and says so honestly — it cannot make a weak predicate strong. The tree's
own judge is what the measurement passes. Crystallized rules are holed (`?id0`), so
`rule_op`'s step proof is "this apply's output, re-parsed" and its survival claim is the
durable one: the taught pattern can no longer fire anywhere, and the state still parses.

## The measurement — two proved operations, this repository's own code

Protocol (deterministic, seeded, re-executed twice to identical boxes): stride over the
**9,290 premise-holding sites** in 5,563 files (the universe where step one is allowed
to fire; the all-sites scan count is in the receipt so the conditioning is visible).
Step one is one of the tree's own learned skills (`inline`, `rename` — the same bundle
the reach instrument uses); step two is (a) the same logical target under the other
family, premise **re-read from the world step one left**, or (b) another variable of
the same function whose premise still holds. Every attempt is judged by the five-check
rule, and every PASS is re-judged independently (both witnesses + both filesystem
checks on the final file).

| number | value |
|---|---|
| sampled premise-holding sites | 72 (36 `inline`, 36 `rename`) |
| step one proved | `inline` **22/36**, `rename` **35/36** |
| second-step attempts | 80 |
| attempts where every premise held | 58 |
| **COMPOSED_VERIFIED** | **31** |
| PREMISE_DIED (refused before execution, requirement named) | 22 |
| B_REFUSED (premise held, stored step declined) | 27 |
| NO_SECOND_CANDIDATE | 34 |
| A_NOT_PROVED | 15 |
| **reach_compose** (composed / all attempts) | **0.3875** |
| **reach_where_premises_held** | **0.5345** |
| **DAMAGED** | **0** |

Both reach numbers are reported the way the reach instrument established: the first says
how far two proved operations get on this repository as it stands; the second says what
the rule does inside the world it is allowed to touch. Two runs under
`PYTHONHASHSEED=0` produced byte-identical box tables (the unseeded runs shifted a box
or two — the stored steps iterate hash containers; the seed is pinned in `measure`).

**What the box table says:** among attempts that got past every premise gate and every
proof, **not one damaged the world, not one sequence reverted, not one proof died
silently** — and 31 two-step compositions were verified end to end. Where sequences die,
they die at a named place: the premise re-read after an effect (22), or the stored step
itself declining with its premise satisfied (27), or there being no second candidate at
all (34). The mechanics of composition are no longer the wall; the *premise boundary*
and the *proposal* are.

## The single bottleneck, reconciled

The nine measurements of this claim factor one equation:

```
separation = (the space contains the truth) × (an observation separates) × (a verifier reads it)
```

- **space wrong** ⇒ no question helps (7/23 tasks; the hand-listed edit basis made
  `^=`→`&=` unreachable at any budget — `THE_EDIT_SPACE_IS_THE_PROGRAM_NOT_A_LIST_20261116_V1.md`);
- **observation missing** ⇒ a correct answer is literally unaskable
  (18/479 fault sites identical in all ten observables — `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`);
- **verifier absent** ⇒ a passing test certifies nothing
  (80.2% of 86,156 agent-written test patches carry weak or no oracle —
  *All Smoke, No Alarm*, arXiv:2606.18168).

Each of today's notes measured one factor and named a different "single bottleneck"
(edit space, verifier, observable, separation, proof, proposal). They are not competing
answers; they are factors of the same product, and the binding term is now per-task
measurable (one question: CONTRADICTION / UNSEPARATED / INSUFFICIENT —
`identification_cost_in_a_real_space_v1.py`).

**The honest single bottleneck for the stated goal** — all computer use + advanced SWE —
is the **affirmative organ**: synthesize and compose behaviors the system was never
shown, each step proved by an oracle it did not write, with premises that survive
effects. Everything the project has already built is the *refusal* half (select,
certificate, scope, gate, withhold, decline). This pass ships the first half of the
affirmative half: composition under proof. The remaining halves are the proposal
generator pointed at the 46/100 bugs where no candidate passes, and the per-step
verifier for horizons of hundreds of steps.

## What the field measures, November 2026 (nothing here is holy)

- **Composition is the open frontier everywhere**: SkillHorizon (arXiv:2610.14966) —
  local-goal completion falls **90.4% → 46.8%** as composed workload grows; *Diagnosing
  Semantic Handoff Failures* (arXiv:2607.06256) — the same skills reach **77–100% from
  clean snapshots and stall when chained**, because no one checks next-skill readiness;
  CompoSkill (arXiv:2608.16246) — individually certified skills compose into attack
  chains. The rule this pass ships is exactly the missing check, in the tree's own idiom.
- **One-shot skill generation is dead as a strategy**: SkillsBench finds no benefit on
  average; SkillLearnBench (arXiv:2604.20087) finds no continual method leads across
  tasks. What works at the text level is bounded, gated editing — SkillOpt (arXiv:
  2605.23904, +23.5 points, 1–4 accepted edits under held-out gates) — which is the
  same shape as this project's admission gate, minus proofs.
- **Verification is the systemic wall**: OSWorld 2.0's own failure analysis puts
  "skipping verification" at the centre; more budget buys partial progress, not strict
  completion (54.8% partial vs 20.6% strict); *All Smoke, No Alarm* measures the oracle
  crisis at scale (strong oracles raise merge odds OR 1.28).
- **SWE honest numbers** (contamination-adjusted): SWE-rebench ~65.3%, SWE-bench Pro
  ~61.5%, Verified ~24% leakage (BenchJack); single-patch SWE-bench is overoptimistic
  (SWE-EVO).

## What this does NOT solve — stated so nobody can read this receipt as more than it is

1. **Proposal.** Step one still declines 15/72 in-premise attempts; 34 attempts had no
   second candidate; the 46/100 bugs whose passing behavior is a composition outside
   every current basis are untouched by this pass. The generator, not the chooser.
2. **Reach is not coverage.** 0.3875 composed / 0.5345 inside premise means two thirds
   of two-step attempts still die somewhere. The box table says where; it does not
   make the wall disappear.
3. **Computer use.** Nothing here runs a GUI. The horizon problem (318 tool calls,
   per-step independent observation) is addressed only in its two-step code form.
4. **Sentience.** The checkable proxy — does experience change competence on a new
   problem — remains measured negative on the strict reading; what is real is
   knows-what-it-doesn't-know plus 0 damaged across every box.

## The smartest next moves, in order (from the receipts, not from taste)

1. Point the composition-aware generator at the 46 where no candidate passes —
   multi-position and insertion compositions are the rungs with no template form yet.
2. Ship the veto (predictor as a skip-decision, not a claim) — precision 1.000 on
   question-settled cases makes learning at recall safe.
3. Run the binding-term instrument first on every unsolved task: one question says
   whether to grow the space, ask the observation, or build the verifier — so effort
   never lands on the wrong factor.
4. Parameters for proposal last: solved-class certainty never scales; weights are the
   composition engine, but only once the proof-side measurements demand them.
