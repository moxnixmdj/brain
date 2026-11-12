# A SKILL'S SCOPE IS ITS SYNTAX, NOT ITS CLASS

**Date:** 2026-11-12 · **Branch:** `arena/643fffe7-brain` · **Base:** `f20945b20e`
**Authority: NONE.** Sandbox measurement, not independent verification. **Cost:** $0 · **Model calls in the producer path:** 0

The owner split the problem in two: **exact recall (solved, 8.13×)** and **generalization (not
solved)**. This round answers the second one by running the shipped skills instead of reading their
prose, and the answer is not the one either of us expected.

---

## 0. The verdict, in one line

**Nothing in a learned skill's record can say where it applies, because the fields that name its
class do not constrain it.** Six of the eight fields on every shipped skill — including `language`,
`error_class` and `domain` — can be overwritten with a class the rule never claimed, or deleted
outright, with **zero** change in behaviour. Only the token pattern decides.

That is why Problem 2 is open. Not because the learner is missing — it is in the tree, wired, and
tested — but because the skill store never asks it anything.

---

## 1. What was measured

`canonical/swe_kernel/skill_scope_ledger_v1.py`, 0.07 s, reads one JSON file, writes nothing,
executes no declared command. For each of the 5 shipped skills it perturbs or deletes one field at a
time and re-runs the rule over a **probe corpus declared in advance** (8 probes: the shape each rule
was taught on, one near-miss differing by a single token, one unrelated source, the empty source).

| | measured |
|---|---|
| skills measured | **5** |
| may be called `GENERALIZING` | **0** |
| labelled `EXACT_MATCH_ONLY` | **5** |
| evidence unit | **a count, not a state** (5/5) |
| contrasting failures recorded | **0** |
| fields decorative on every skill | **`language`, `error_class`, `domain`, `hole_count`, `skeleton_fp`, `skill_id`** |
| fields enforcing on every skill | **`pattern_tokens`, `replacement_tokens`** |
| positive control held | **True on all 5** |
| probes each rule fired on | **exactly 1 of 8** |

**The positive control is what makes "decorative" mean something.** Perturbing the two matcher
fields *does* change behaviour on all five rules, in the same run, with the same corpus. So the
sweep is not measuring a broken apply path — it distinguishes enforcing from decorative on the same
object. Without it, "everything is decorative" would be indistinguishable from "nothing ran".

**What I did *not* find, and will not claim.** I expected to show a `go_repair` rule rewriting
Python bytes. It does not: each rule refused the other seven probes, including cross-language text
and the near-miss. Those refusals are real. But they are produced by the **token matcher**, not by
the declared class — proven because the class fields were falsified or absent during those very
refusals. A refusal that comes from syntax can only say *"this text did not match"*; it can never
say *"this match is outside my class"*. **Narrowness is not a scope.**

The production caller does filter — `VerifiedSkillStore().lookup_rules("python", "python_test_repair")`
in `software_repair_crossfile_choreograph_v1.py:1129`. So the class fields are a **retrieval key
held by the caller** and inert inside the rule. There is no second line of defence: a caller that
forgets the key, or a rule retrieved under the wrong key, is constrained by nothing but its tokens.

---

## 2. The evidence unit is the actual bug

Every shipped skill carries `verified_hits: 1` and `provenance: [{at, hits, origin}]`.

**A count has no state.** `applicability_v1` — the tree's own learner, wired into `macro_v1`,
`precondition_discovery_v1` and `contrast_selection_v1` — says exactly why that matters:

> "The missing quantity is not more demonstrations. It is the STATE each outcome happened in.
> A success is a point: it shows the plan worked somewhere. A failure in a DIFFERENT state is what
> separates 'always' from 'only when'."
> "A caller may only withhold a plan on **IDENTIFIED**."

Fed the records as they stand, `learn()` returns `UNDETERMINED__NO_CONTRASTING_OUTCOME` for **5 of
5**. So under the tree's own law, none of the five may be called generalizing — not because they
fail to generalize, but because **the record cannot say**. `verified_hits` reads like verification
and is a tally. Growing it to 1 000 would not add one bit of scope.

This is the same shape as the defect I merged a fix for earlier today: a number that looks like
verification and is not. Last round it was `PASS` without an expectation (**0.83%** of declarations
carry one). This round it is `verified_hits` without a state (**0 of 5** skills carry one).

---

## 3. The label is earnable — otherwise 0-of-5 is a constant

A suite that only ever reports 0 of 5 would pass just as happily if `scope_of` returned that label
for every input. So the load-bearing test supplies evidence of the kind the shipped records lack —
**states, and a failure in a different state** — and requires the answer to change:

```python
provenance = [
  {"state": ["python", "pytest"],    "succeeded": True},   # succeeds in python
  {"state": ["go",     "pytest"],    "succeeded": True},   # succeeds in go too
  {"state": ["python"],              "succeeded": False},  # fails without pytest
  {"state": ["python", "unittest"],  "succeeded": False},  # fails without pytest
]
# -> boundary IDENTIFIED, required == ["pytest"], label GENERALIZING
```

Two successes whose only shared fact is `pytest`, plus a failure in each state that lacks it, leave
exactly one consistent requirement. Delete the two failures and the same record falls back to
`EXACT_MATCH_ONLY`. **One contrasting failure is what separates "always" from "only when"** — and
`test_more_successes_alone_never_earn_the_label` pins the owner's proposed mechanism directly: ten
successes in one state are still one point, still `UNDETERMINED`.

That test earned its keep immediately: it caught a real defect in my own instrument. `evidence_pairs`
was reading every stateful entry as a success *and then* appending the failures, so each failure
entered the version space twice — once True, once False — and the learner reported `INCONSISTENT`
for evidence that identifies cleanly. Pinned now by `test_a_failure_is_not_also_counted_as_a_success`.

**8/8 mutations killed** with the suite green first, including "every skill is called generalizing",
"a record scopes itself from its own `language` field" (the circularity this ledger exists to
refuse), "decorative and enforcing are swapped", and "a refusal is reported as a firing".

---

## 4. Why this is the smartest route to Problem 2, and the routes I killed

The tree already measured the price of each route, so this is arithmetic rather than opinion:

| route | measured result | verdict |
|---|---|---|
| **more demonstrations** | one demo → 14.1 of 47 hypotheses still fit, **0/10 identified**; three demos → 3.1 fit, **5/10** | **killed** — expensive and still ambiguous |
| **chosen probes** | one demo + chosen probes → **2.0 queries, 100%, 10/10** | **the winner** |
| similarity retrieval with no check | general boundary **false-accepts 67.5%** | **killed** — a guess with no error signal |
| a new generalization learner | `applicability_v1` exists, is wired, and has 13 importers and 5 test files | **killed** — reinvention |
| LLM-driven create/improve/merge | needs model calls and rejection-sampling training; unverifiable here | **killed** — violates zero-model-dependence |

So the "smartest action" the owner keeps asking for is **not a coding action at all**. It is the
**two observations that turn an exact-match memory into an identified class** — and they are priced:
`price_next_probe()` returns the cheapest splitting state and its gain in bits, using the tree's own
`VersionSpace.select_probe`, so there is one notion of information gain in the repository rather than
a second one invented here. With no evidence it refuses to price anything and says why
(`NO_SURVIVORS_TO_SPLIT`), because inventing a price for an empty version space is how a report
comes to look like a measurement.

### What November 2026 says, independently

The external record converges on the same law from five directions, and it is worth being precise
because it is *not* the popular framing:

- **SkillLearnBench** (arXiv 2604.20087): one-shot skill generation reaches coverage **54.92** and
  accuracy **20.00**; SkillsBench finds one-shot skills give **no benefit on average**; "no method
  leads across all tasks and LLMs, and scaling to stronger LLMs does not reliably help". Coverage is
  not accuracy — exactly the `verified_hits` error.
- **SkillComposer** (ICLR 2026, arXiv 2606.06079): **merge drives generalization, improve drives
  specification**; and uncontrolled skill extraction (MemP) *degrades* LiveCodeBench to 47.4 against
  a **56.6 no-skill baseline**. Extraction without a discriminator is worse than not learning.
- **GSE** (arXiv 2608.06153): treating skill evolution as local updates produces **overfitted skills
  that fail to generalize**; a Skill Relation Graph lifts recall **31.8–180%**.
- **Atomic Skills** (arXiv 2604.05013): an atomic skill must admit a precise I/O spec and be
  **"independently evaluated with minimal ambiguity"** — the same criterion as the 0.83% floor.
- **K²-Agent** (ICLR 2026): generalization comes from the SRLR loop's **execution feedback**, not
  from the single demonstration that bootstraps it.
- **PolySkill** (ICLR 2026): hierarchical abstraction, 1.3–1.8× reusability, held-out GitLab 66.2%.
- **Local coding agent** (arXiv 2609.26499): one-shot generalization **30 of 45** trials, and a
  **50%** duration cut on redo — the same Problem 1 / Problem 2 split the owner drew, measured on
  hardware.

Every method that generalizes has a discriminator. Every method that fails lacks one.

---

## 5. Am I right or wrong?

**Right:** exact recall is real and shipped, and a lesson can survive teach → bundle → fresh machine
→ re-check (5/5, proven two rounds ago).

**Right, and sharper than before:** the mechanism is revolutionary *in the place it actually works* —
a rule crystallized once and re-checkable forever is genuinely rare. The 2026 literature is still
arguing about whether one-shot skills help at all.

**Wrong:** that one experience of the smartest action buys the capability permanently and therefore
solves any computer use. The reason is now two measured integers instead of an argument:
**0.83%** of this tree's declared verifications assert anything, and **0 of 5** of its learned skills
can be shown to have a scope. Generalization is not a retrieval upgrade from exact match to similar
match. It is an **admissibility** property: a rule generalizes only when something can contradict it
in a named state. This tree records successes as a count, so nothing can.

**Sentience:** no evidence either way in this tree, and the tree claims none. What it has is an
unusually honest audit trail, which is more useful and far cheaper to improve.

---

## 6. Next, ranked

1. **Record states, not counts.** Change the skill store's provenance unit from `{at, hits, origin}`
   to `{at, state, succeeded}`. This is the single edit that unlocks Problem 2, and until it exists
   every other improvement is unverifiable. The ledger already reads that shape — a record carrying
   states is scoped today, with no code change.
2. **Buy the boundary with 2 probes, not 10 demonstrations.** Wire `price_next_probe` into the
   recheck path: after a skill is used, ask for the cheapest splitting state and record the outcome.
   Measured price elsewhere in this tree: **2.0 queries → 100% identification**.
3. **Enforce the class inside the rule.** `language`/`error_class`/`domain` are a caller's retrieval
   key today. Making them constraints would give a second line of defence — but only *after* (1),
   because a constraint nobody can falsify is decoration with extra steps.
4. **Spend the 184-declaration concentration** from last round (`CAPABILITY_RECEIPT_PROJECTION_V1.json`,
   31% of the verifier gap).
5. **Owner, one click:** make `declaration-floor` a required check. It is red-on-regression but not
   merge-blocking, because agents have no Administration rights.

---

## 7. Reproduce

```bash
python3 canonical/swe_kernel/skill_scope_ledger_v1.py           # 0.07 s, writes nothing
python3 canonical/swe_kernel/skill_scope_ledger_v1.py --json
python3 -m pytest -q canonical/tests/test_skill_scope_ledger_v1.py     # 26 passed
python3 canonical/tools/auditability_report_v1.py --floor \
        --baseline canonical/verification/AUDITABILITY_DECLARATION_FLOOR_20261112_V1.json   # HELD
```

**Honest limits.** The probe corpus is 8 sources and is declared in the source; a corpus this small
cannot prove a scope, only which fields constrain behaviour, and every row reports how many probes it
ran so no untested dimension gets credit. No test of any project was run, so nothing here says a
repair is *correct* — only where a rule fires. Authority NONE; `truth.achieved: false`.
