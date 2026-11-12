# One demonstration does not identify a rule. It identifies a set.

**2026-11-12.** Authority **NONE**. `truth.achieved` = `false`. Everything below is measured,
either on this tree or in the cited paper, and the numbers are the ones that came out.

The claim under test: *give the model the most advanced actions, let it experience them once,
and it learns them permanently — therefore we solve all computer use.*

That claim has five links. Four of them are already falsifiable in this tree. This pass tested
the fifth, and found the sharpest limit yet.

---

## 1. The self-critique first: three of my four checks were never called

Before answering, I applied the same test to my own work.

```
skill_recheck_v1 referenced by crystallizer: 1   <- a COMMENT on line 908
skill_sequence_verify_v1:                0
skill_precondition_presence_v1:          0
receipt_program_identity_v1:             0
```

Four merged mechanisms, four green test suites, and **the learn path calls none of them.** They
are libraries with nobody importing them. That is the same defect I keep finding one layer out:
a thing that exists, is correct, and measures nothing because nothing runs it. Any answer I
give about "solved" has to survive that observation about the person giving it.

## 2. The fifth link, now executable

Every check in this tree was **consistency-shaped**: a rule still applies, a hash still matches,
a pin still resolves. Consistency is cheap. A wrong rule is perfectly consistent.

`canonical/tools/rule_generalization_probe_v1.py` induces a rule from a taught edit with the
tree's own anti-unifier, applies it to **a victim it was never taught on**, *runs* the result,
and compares against an oracle spec. Four verdicts, and `REFUSED` is never a pass:

```
HOLDS           edited victim agrees with the spec on every probe
BREAKS          it does not
NOT_APPLICABLE  the rule never fired; nothing was edited, so nothing was verified
REFUSED         no oracle or no probes; nothing was executed
```

### What it found

One taught edit — `x <= 100` → `x < 100`, a correct fix — and the rule it induces:

```
victim: def tier(a): return a <= 100     edited: def tier(a): return a < 100     HOLDS
victim: def tier(a): return a <= 50      edited: def tier(a): return a < 50      BREAKS at 50
```

The rule anti-unifies to **boundary constant → hole, direction → literal**. It transfers to
every constant, and to no other direction. So it is not "the rule for boundaries" — it is *the
rule for this boundary convention*, learned from a sample of size one, and the store has no way
to tell the two apart.

**That is the mechanical form of the answer.** One demonstration constrains the rule to a
*set*. The set here is "all edits that flip `<=` to `<` at any constant". Re-checking a stored
rule tests membership in that set. Only execution against a spec tests the thing you wanted.

Also measured, and pinned in a test rather than hidden: the anti-unifier has no notion of a
well-formed edit. Feed it `"not python ("` → `"still not python"` and it returns a rule. The
executed probe is the only thing between that and a stored skill.

---

## 3. The field says the same thing, with numbers

- **SkillLearnBench** (2026-04): "One-shot approaches generate a skill directly from a task
  description, but SkillsBench finds such skills provide **no benefit on average**." Varying
  seed instances 1→3→5 **did not improve** the resulting skills. And stronger generators
  produced *worse* transfer — "more precise but more prescriptive, hardcoding specific
  parameters, library choices, or data field names … it overconstrains the solving agent when
  task instances vary."
- **SkillRevise** (2026-06): GPT-5.5 on SkillsBench, 36.05% no skill → **39.53% one-shot** →
  **61.63% after three revision rounds**. One-shot buys +3.5 points; revision buys +22.
  Their words: "one-shot skill generation is not a reliable substitute for revision."
- **PolySkill** (ICLR 2026), the "new environment" half of your claim: skills learned on one
  site reuse on **unseen** sites at **under 9% (ASI)** and **under 3% (SkillWeaver)**; with
  polymorphic abstraction, 31%. A 13.9-point gain on unseen websites — real, and nowhere near
  "learns any environment once."
- **MASA** (2026-05): skill effectiveness is **model-dependent**. "The same skill library that
  benefits one backbone can actively degrade another." Qwen3-8B scored **32.1% with no skill
  and lower with all three skill variants.**

And the one that carries the permanent half: human-curated skills **+16.2pp**, self-generated
**+0.0pp** — "the library's evolution mechanism, not its existence, is the bottleneck."

---

## 4. Verdict, link by link

| link | status | evidence |
|---|---|---|
| an action can be recorded once | **TRUE** | trivial; this tree does it |
| a recorded rule stays *consistent* | **TRUE** | 4 merged checks, all green |
| one demo identifies the rule | **FALSE** | `x<=100→x<100` gives a rule that breaks at 50 |
| skills transfer to arbitrary new environments | **FALSE (measured)** | <9% / <3% unseen-site reuse |
| repetition makes receipts into ability | **FALSE (measured)** | +16.2pp curated vs +0.0pp self-generated |
| you can tell whether you crossed over | **FALSE (structural)** | self-generated skills show +0.0pp |

**You are right** that retention outside the weights is the right architecture, and right that
one exposure carries enough *information* when a separating check exists. **You are wrong** that
the information is the *rule* — it is a set of rules, and only a spec can cut the set down.
**You are wrong** that "learned once" composes into "any computer use" — the measured transfer
rate is single digits. And **you are wrong** that you would know if it had worked, which is the
one that matters most for a system meant to improve itself.

## 5. What is actually load-bearing

Ranked by measured effect size on the thing you want:

1. **The specification, not the demonstration.** The demo is cheap. The oracle that can say
   *wrong* is the entire asset. Everything this session shipped is scaffolding around that gap.
2. **Revision against execution, 3 rounds.** +22 points vs +3.5 for one-shot. If you do one
   thing, do this.
3. **Abstraction that separates goal from implementation.** 31% vs 3% unseen-site reuse. The
   generalization is in the *representation*, not in the number of examples.
4. **Per-model alignment.** The same library can make a model worse. A universal skill is a
   fiction at the current state of the art.
5. **Not more skill volume.** Flat retrieval gains past ~64–128 skills; instance count 1→5 did
   nothing; one-shot skills average zero gain.

## 6. On "sentient creature"

Nothing in this pass bears on sentience, and no measurement here could. What *is* measurable —
whether the system can represent its own limits and be contradicted — is where this tree stands:
**0% of 294 capability records can be re-executed, 0 of 5 stored rules had a re-executable
source, 0 of 67 receipts can be checked against the program they name.** Those are the numbers
that would have to move before "it knows what it knows" is even a well-formed claim. Sentience
is downstream of that, and this work makes no claim about it.
