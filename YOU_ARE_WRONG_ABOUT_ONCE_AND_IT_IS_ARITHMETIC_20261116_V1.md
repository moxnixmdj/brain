# You are wrong about "once" — and the reason is one line of arithmetic

**Date:** 2026-11-16 · **Branch:** `arena/a561d504-brain` · **Base:** `8ff59e0d`
**Authority:** `NONE__PRODUCER_RUN`. Producer-run, this machine, $0, zero model dependency.

---

## The claim under test

> *"We already solved instant learning and instant learning in new arbitrary environments. Just give our model the most advanced actions, let it experience each once, and it learns them permanently. So we solve everything on a computer."*

**You are right about the mechanism and wrong about the word "once".** Instant learning is real and it is measured. What is not real is that one experience *identifies* a rule, or that identification completes at all. The gap is not effort, not scale, and not enough environments. It is arithmetic, and it is 5.55 bits wide.

---

## 1. Research exhaustion first — this was already answered in your own tree

I did not build first. Your project already contains the answer, under names that are not "instant learning":

| non-obvious name | what it already established |
|---|---|
| `INSTANT_LEARNING_AUDIT_20261112_V1.md` §5 | *"The example selects; the prior and the questions do the generalizing."* |
| `one_shot_identifiability_probe_20261112.py` | one demonstration: 14.1/47 survivors, 0/10 identified |
| `instant_learning_boundary_probe_v1.py` | a carried model is a table keyed on state **names** |
| `what_a_success_teaches_20261112.py` | one success identifies an applicability requirement **0/200**; chosen failures **25/25 in 2.76 demos** |
| `repair_version_space_selection_v1.py` | on 19 HumanEvalFix bugs, **5/16** were wrong for a reason **no question can fix** |
| `contrast_selection_v1.py` | *"further identical points are the same point"* |
| `demonstration_version_space_v1.py` | every description consistent with a success, enumerated and pruned |

So the honest first move was **run it, not rebuild it.** I re-ran two instruments on this base. Both reproduce.

```
after ONE demonstration:   14.1 of 47 programs fit; leader right 10%;   0/10 identified
after THREE:                3.1 fit;               leader right 80%;   5/10 identified
one demo + chosen probes:   2.0 queries;           leader right 100%;  10/10 settled
one demo, narrow prior:                            leader right 100%

"The example does not change between those last two lines. Only the space does."
```

And the computer-use number, re-run here:

| arm | warm cheaper | warm dearer | CARRIED_MODEL survived |
|---|---:|---:|---:|
| state names **as-is** | 8/10 | 2/10 | **7/10** |
| state names **renamed** | 1/10 | **9/10** | **0/10** |

The learned model carried a **table keyed on state names**. Rename the states — the same task, a different spelling — and 7/10 wins become 0/10, with warm runs now *worse than cold*. Nothing about the dynamics changed. Only the name did.

---

## 2. The law, derived not asserted

Learning from experience is only ever removing hypotheses. So the state of knowledge is one number, and every lever is a subtraction from it:

```
bits_after = log2( |H| / |G| )  −  I(E)  −  Σ I(q)  −  I(interface)

|H|          the hypothesis space
|G|          the invariance group: how many spellings one behaviour has
I(E)         what ONE demonstration removes
I(q)         what one chosen question removes
I(interface) what a declared interface ENTAILS, with no observation
```

Learning is finished exactly at 0. On your own 47-program space, computed:

```
bits_before                     5.5546      log2(47)
bits_after_one                  3.8176      one demonstration does NOT finish it
bits per further demonstration  1.0927
bits per chosen question        1.9088      14.1 -> 1 survivor in 2.0 queries
──────────────────────────────────────────
A QUESTION IS WORTH 1.747× A DEMONSTRATION at equal interaction cost.
Demos needed to finish by experience alone: 3.49   ·   Queries measured: 2.00
```

**That ratio is the whole answer to "why can't we just let it experience once."** A demonstration is one answer from the world. A question is chosen to cut the surviving set in half. At the same price — one interaction — half a set beats one point, every time.

### The ceiling, and the one that is not binding

One demonstration removes at most `log2(|Y|)` bits, where `|Y|` is the world's distinct-answer count. Here `log2(176) = 7.46 > 5.55`, so **that ceiling is not what binds.** What binds is that a single point genuinely only partitions a little: the best point removes 3.63 bits and leaves 14.1 hypotheses. **Naming the wrong ceiling would have been a false diagnosis, and the honest one is narrower.**

---

## 3. The measurement that kills the intuitive design rule

If you had told me "pick the demonstration whose answer is richest," I would have said yes. It is **false**, and this is the sharpest number here:

| demonstration at | distinct answers it produces | bits it teaches | share of the whole space |
|---|---:|---:|---:|
| x = 0 | **5** | **3.6293** | **65.3 %** |
| x = 30 | **36** | 0.6035 | 10.9 % |

The point with **36 different answers buys 0.60 bits.** The point with **5 answers buys 65% of the entire hypothesis space.** Ranked across all 37 points, answer-variety and information agree on **2 of 37**.

**Variety of answers is not information about the hypothesis.** What matters is whether the answer *partitions* the hypotheses. So you cannot find a good demonstration by looking at how interesting its output is — and you cannot find it at all until the space is written down. That is why `demonstration_version_space_v1.py` exists and why the space, not the data, is the asset.

---

## 4. Your three blockers, and which one is actually load-bearing

You named identifiability, vocabulary insufficiency, and the synthesis–verification asymmetry. The law orders them.

**Identifiability — the first bottleneck, and it is closed on the GUI side, open on the code side.**
`demonstration_version_space_v1.py` already enumerates every description consistent with a success and prunes with each new one. It is the right mechanism and it works where the space is small. It cannot work where the space is syntax: I checked whether the tree's own 47-program space has the α-renaming problem — **47 entries, 47 distinct functions, |G| = 1.** So the invariance lever is worth *nothing* there, and the space is already exact. That is a `best part is no part` result: the lever you would expect to pull has no part to pull.

**Vocabulary insufficiency — this is the load-bearing one, and `enter-time` is its clean exhibit.**
A `<input type="time">` rejects `1:13 PM` — the instruction's own string — along with `1:13PM`, `01:13 PM`, and `13:13:00`, and accepts only `13:13`. That string is on **neither the page nor the instruction**. It is a rewrite that lives in the world. No amount of experience *on that page* produces it, because the answer is not in the observation. **This is the "NO question can fix it" box** — `repair_version_space_selection_v1` measured it directly: 5/16 HumanEvalFix bugs were wrong because the generator never proposed the right behaviour.

**Synthesis–verification asymmetry — real, and not a vocabulary problem.**
5/16 of those bugs were *unfixable by any question*, but 4/16 were selection failures where the right answer **was already in the candidate set** and the tests could not see it: a chosen question settled **4/4**, and majority vote among candidates picked the **wrong** one 3 times in 5. So the asymmetry has two halves with two different cures, and conflating them is the error to avoid.

---

## 5. Where your "give it the most advanced actions" idea is exactly right

Not a courtesy — a measured result. `repair_version_space_selection_v1` shows the right answer **was already in the candidate set** in 4/16 cases, invisible to the tests. **Selection, not synthesis, was the blocker there**, and a chosen question closed it 4/4. So the most advanced actions are not the lever; the **candidate set that contains the right behaviour** is, and the questions that reveal which one it is. Your instinct about advanced actions is right in a different place than you put it: the actions set the **space**. The questions do the learning.

**And "the smartest actions" has a second, measured form.** Remember the state-name result: the model that won 8/10 was not wrong about the world, it was **keyed on a spelling**. The advanced action is the one whose *effect is name-invariant* — that is the same law as your code-side α-canonicalisation, and it is the one lever that costs **one canonicalisation function** and no further interaction.

---

## 6. Sentience: honestly, what is measured

**Nothing measures sentience here, and no result in this tree is evidence for it.** What is measured is bounded mechanism: verified plan retention, per-environment dynamics, contradiction repair, refusal of unsafe routes. Those are real and worth having.

The discipline that matters is the one already written into the audit: **keep consciousness separate from capability, and never let a module name stand in for experience.** A creature that learns instantly is not thereby sentient, and a system that conflates the two will optimise the wrong number. The measured claim is narrower and stronger: **the mechanism you built is real, and it is a mechanism.**

---

## 7. The single bottleneck

> **A demonstration is one answer. The hypothesis space is what turns answers into knowledge — and the space is authored by us, not learned from the world.**

Everything in §2 is a consequence. Coverage, identification and interface are not three co-equal levers: **the prior is the only term not billed per interaction.** Look at the probe's last two lines again — the same example, 10% accuracy in one space and 100% in another. The example never changed. The space did.

So the highest-leverage thing is not more environments, more actions, or more experience. It is **writing down the space before you spend an interaction**, because that is the only lever that does not cost a try.

**This is also the answer for your model, and it is why "the best part is no part" is load-bearing here.** A parameter that stores spellings is a parameter that fails the rename. Every bit of knowledge in weights must be *name-invariant* or it is a lookup wearing a model's clothes — which is precisely what the 8/10 → 1/10 result measures. Instant-knowledge channel for the spellings; weights for only what survives the quotient.

---

## 8. What I did not do, and why that was right

I did **not** build a new learning mechanism, a new store, or a new probe suite. Three were already there and better than what I would have written in a session. I added **one** equation that ties them together, because the audit gave three levers and a list is not a law — it cannot tell you which lever to pull first or when one is empty.

I also did **not** claim the `log2(|Y|)` ceiling binds. It does not. Claiming it would have been the comfortable answer and a wrong one.

## 9. Non-claims

- Constructed spaces, one machine, producer-run. Not arbitrary coding, not GUI, not unbounded computer use.
- The 1.747× ratio is space-specific. The **direction** (a chosen question beats a demonstration at equal cost) is a theorem about entropy; the **magnitude** is a measurement of this space.
- `|G| = 1` for the one-shot space is a property of a hand-authored space. Any space enumerated by syntax will have `|G| > 1`, and the correction is the point of §2, not a remark.
- No capability, benchmark, ownership, terminal or sentience credit follows. `truth.achieved` is false.

## 10. Reproduce

```bash
python3 one_shot_identifiability_probe_20261112.py --json /tmp/oneshot.json
python3 canonical/tools/instant_learning_boundary_probe_v1.py > /tmp/boundary.json
python3 canonical/tools/the_four_levers_of_learning_from_experience_v1.py \
        canonical/verification/THE_FOUR_LEVERS_OF_LEARNING_FROM_EXPERIENCE_20261116_V1.json
python3 -m pytest canonical/tests/test_the_four_levers_of_learning_from_experience_v1.py -q   # 13 passed
```
