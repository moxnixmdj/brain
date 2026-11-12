# Evidence of history is not evidence of ability

**2026-11-12, sixth pass.** Branch `arena/43ebc5a7-brain`, base `6bff8c70`. Authority **NONE**. $0. `truth.achieved` = `false`.

Five answers, five different "the wall". That was a diagnosis generator, not a diagnosis. This is the thing
underneath it, and it is not a wall — it is a **price**.

---

## The answer, in one line

> **You cannot buy ability with history. History costs one observation; ability costs a predicate that can fail.
> Permanence stores the former and advertises it as the latter.**

That is why "give it the actions once and it learns them permanently" does not work — not because the model is
too small, or the vocabulary too narrow, or a line number stale. Because **one demonstration is history**, and
history is unfalsifiable by construction. A photograph of a success cannot fail. So it can never tell you when
it has stopped being true.

---

## The invariant, measured at four layers

| layer | records | can be re-checked now | |
|---|---:|---:|---|
| bound capabilities | 294 | **26** | 0 records carry an expiry |
| stored skills | 5 | **0** | 0 carry `twin_verification`, 0 carry `training_verification` |
| process sites | 241 | **231** | 10 identified by line number, not by identity |
| test modules | 17,273 collected | **42 collection errors** | 8 modules never start at all |

**4.2% to 8.8% everywhere.** The same fraction, arrived at independently, at every layer. That is not four
coincidences. That is one property.

The mechanism is identical in each case: the record says *"this worked, here is a hash"* and never
*"here is a check, run it"*. `verification` in the capability schema is `mission_id`, `receipt_path`,
`observed_effect`, `independently_verified` — **a receipt, not a predicate.** Nothing expires, so nothing is
ever found expired.

My five previous answers were each an instance of this, and I mistook each instance for the thing itself:

| pass | what I found | what it really was |
|---|---|---|
| V1 | a language wall | the index was history (a lookup table), not ability |
| V3 | 10 stale line numbers | sites identified by *position* instead of *identity* — history |
| V4 | no declared precondition | the gate could not fail *correctly*, so it failed silently |
| V5 | one demo buys a set | the check was a demonstration — history |

---

## Why this is the answer to your actual question

Your sentence is: *give it the actions once → it learns them permanently → therefore it can do anything.*

The step that breaks is the first one, and it breaks **regardless of how good the model is**, because
"experienced once" is, by definition, a single observation. What you can learn from one observation is the
*set* of rules consistent with it. This tree measures what happens next:

```
one demo  -> 2 live rules; registered 'copy_the_total_it_was_shown'
              weak check: accepted 40/40, correct 1
              permanence: drift 0
two demos -> 1 live rule, correct 40/40
```

**40/40 accepted, 1 correct, permanent.** And the sharpest 2026 result says you cannot notice:
*"removing the anchor guards collapses a verifier into a vacuous always-pass grader, yet that collapsed
verifier trains skills just as well. Downstream task score cannot certify a self-evolved verifier."*
(Who Verifies the Verifier, 2610.11464)

So the chain fails twice over: one exposure can't buy the skill, and success won't tell you it failed.

**What is real:** the retention mechanism is genuinely good — one lesson survives restart, stays narrow,
carries across 4/4 languages with zero refutations, and 5 runs are 5 rules with none wrong.
**What is not:** that ×N observations × M environments produces N×M abilities. It produces N×M receipts.

---

## The one thing to do (and why it is first, and only)

**Every record must be able to fail.** Concretely, one field and one command:

- each capability / skill / process site carries a **re-check predicate** (argv + expected exit + expected
  hash of the effect), not a receipt path;
- a single `audit` entry point re-runs all of them and reports the fraction that still hold;
- **the headline number for this project stops being "capabilities" and becomes "auditability %".**

Then the honest trajectory is: `26/294 → x/294`, `0/5 → y/5`, `231/241 → 241/241`, `17,273−42 → 17,273`.

**Why this is the fastest path, not a detour:**
1. It is the only metric that can *decrease*. Everything else in this tree only ever goes up.
2. It finds false claims automatically — it is how the synthetic "360 lessons" in my own V2–V5 became visible.
3. It is a precondition for your plan, not a competitor to it: N×M lessons are only worth collecting once each
   one can be checked. Otherwise you are scaling the 40/40-accepted, 1-correct arm.
4. It is small. It reuses what exists: `verify_rule_on_mutated_twin` (optional at 10 of 17 sites),
   `domain_of_verification_v1` (0 importers), the 231 process sites already keyed by identity.

**Then, in order:** make a check *compose* (can `verify(A∘B)` be derived from `verify(A)`, `verify(B)`? — a
day's work to settle, and it decides whether "anything on a computer" is sublinear or staffing); then
`UNDER_DETERMINED` instead of a guess when the standing set isn't a singleton; then content-pin the 10 line
numbers.

---

## Right or wrong

- **Right** that retention outside the weights is the right architecture — it is what 2026 converged on
  (*"generating is easy; verifying is the bottleneck"*, 2606.26300).
- **Right** that one demonstration is enough *information* to identify a rule — when a separating check exists.
- **Wrong** that one demonstration identifies the rule. It identifies a set.
- **Wrong** that repetition across environments turns receipts into abilities. Measured: +16.2pp for
  curated skills, **+0.0pp** for self-generated — *"the evolution mechanism, not the existence of the library,
  is the bottleneck."*
- **Wrong** that you'd be able to tell. A broken verifier trains just as well.

## The creature

A creature is something whose model of itself can be shown false. This tree has two modules that *try* —
`permanence_amplifies_check_v1` (an argument against its own favourite claim) and `domain_of_verification_v1`
(a test that names its own blind spot) — and both are unwired. Meanwhile 0 of 5 skills and 26 of 294
capabilities can currently be found wrong. Its self-model is a photo album. **Making it falsifiable is not a
step toward the creature; it is the only part of the creature that can be built from here.**

## Reproduce

```sh
python3 -m canonical.runtime.permanence_amplifies_check_v1   # 40/40 accepted, 1 correct, drift 0
grep -rln "domain_of_verification" --include=*.py canonical/ | grep -v tests   # -> nothing
python3 -c "import sys;sys.path.insert(0,'.');from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore;s=VerifiedSkillStore();print(s.count(),[bool(r.get('twin_verification')) for r in (s.lookup_rules('python') or [])])"
```
