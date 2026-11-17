# "Learn it once and keep it forever" serves about a twentieth of real edits, and none of the multi-line ones

*Measured 2026-11-16 on 691 real changed sites from five public repositories, with no model, no
network and no spend. Receipt: `canonical/verification/SKILL_RECURRENCE_20261116_V1.json`. Instrument:
`canonical/swe_kernel/skill_recurrence_curve_v1.py`. Nothing here is synthetic: every site is a line a
human developer actually changed, taken from the pinned `systematic_edit_corpus_v1.jsonl`
(sha256 `b47d9c9c23e641a8`).*

## 1. The claim, split into four parts that can each be checked

The claim is: *give the agent the most advanced actions, let it do each one once, and it learns them
permanently — therefore all computer use and advanced software engineering are solved.*

That is four separate claims, and each has a number:

1. **Coverage** — the same operation recurs often enough that "once" ever pays again.
2. **Identifiability** — one trace says which parameterised operation it was.
3. **Permanence** — what was stored still applies later, and is not silently wrong.
4. **Observability** — when it is wrong, something in the environment says so.

Parts 2, 3 and 4 were already measured in this tree. Part 1 was measured only in its most generous
form: a sibling *inside the same commit*. This document measures the real form — does an edit recur
*later*, in the same repository and in the next one — and joins all four.

## 2. What was measured

Every site is abstracted to a shape (identifiers, numbers and literals become holes) and given the
signature *shape + one line of context on both sides*, the strictest rung of the supply receipt. A
site **recurs** when an earlier site in the same repository carries the same signature.

| | sites | recurrent | share |
|---|---|---|---|
| loose (shape only, no context) | 691 | 191 | 0.2764 |
| one context line, either side | 690 | 174 | 0.2522 |
| one context line, **both** sides | 644 | 102 | 0.1584 |
| **multi-line edits** (≥2 lines each side, loose) | 267 | 30 | 0.1124 |
| **multi-line edits** (strict) | 242 | 14 | 0.0579 |

Then the question that decides it: when it recurs, does replaying the earlier instance actually
reproduce the later edit?

| replay across time (strict, 102 pairs) | outcomes |
|---|---|
| exact | **31 (0.3039)** |
| verbatim | 0 |
| needs a different literal (`constant_differs`) | 49 |
| wrong rebound / mismatch / conflict | 22 |

**End to end: 31 of 644 sites — 0.0481 — are served exactly by a permanent memory.**
On the multi-line (advanced) edits it is **0 of 14**, with 92.9% coming out wrong.

Three more facts, each of which matters:

* **The whole repeated vocabulary is 59 signatures**, of which **7 carry 50%** and **26 carry 80%** of
  every recurrence. The part of real work that memory can serve is *tiny* — Elon's law applied to
  memory: the best memory is the smallest one.
* **What recurs is a literal moving**: 80.6% of recurrences are one-line replacements, 70.2% are the
  same abstract shape on both sides (only a literal or identifier changed), median size 2 lines.
* **Cross-repository transfer is weak once triviality is removed**: memory built from four other
  repositories covers 21.1% of a held-out one loosely, but only **7.1%** of its multi-line edits, and
  **2.1%** under strict context. That is the "brand-new environment" number, and it is the honest
  version of "instant learning in arbitrary environments": what transfers is the *shape vocabulary and
  the habit of verifying*, not the knowledge.
* **Returns to experience rise but never arrive**: the recurrence rate by chronological quarter is
  0.149 → 0.288 → 0.273 → 0.394. More experience inside one repository does keep paying — slowly, and
  it saturates under 40% of gross, which after replay determinacy is under 12% of net.

## 3. What is real and what is not

**Real.** Experience is not worthless, it is *narrow*. A learned shape vocabulary is 59 entries, it
covers a quarter of gross work loosely, replay of the covering cases is exact 30% of the time, and the
rate genuinely rises with time in a repository. A memory-first learner is therefore a correct *cache*
for a small, mostly mechanical, mostly literal-moving part of the work — one-line version bumps,
import renames, message tweaks. Store that, and it is nearly free to keep.

**Not real.** That any of this is "learning the action", that it composes into advanced work, that it
transfers to a new environment, or that repeating it more makes it truer.

* A recurring shape is not a reinstantiated operation: 48% of the recurrences still need a **different
  literal** than the one that was stored, and the previous measurement says an inferred literal is
  right 21.4% of the time and a two-demonstration contrast 40%. So even the fifth of work that
  recurs is half-mechanical, half-guess.
* Advanced work is defined by *not* being a recurrence: 14 of 242 multi-line edits recur, and none of
  those 14 replay exactly. "Learn the most advanced actions once" has a measured denominator of zero.
* Permanence is the part most likely to hurt: of what is stored, 53.5% goes stale and 31.1% silently
  corrupts as files move. A cache with no invalidation trigger is a liability that grows.

## 4. The composition — the same wall, four times

Four independent instruments in this tree now agree, each with its own denominator:

| term | measurement | source |
|---|---|---|
| coverage inside one batch | 16.0% of commits have a sibling site | `SYSTEMATIC_EDIT_SUPPLY_20261116_V1` |
| identifiability | 54.9% of inductive pairs reproduced; 21.4% of derived values | `SYSTEMATIC_EDIT_DERIVATION_20261116_V1` |
| permanence | 53.5% stale, 31.1% silently corrupt | `ACTION_REPLAY_UNDER_CHANGE_20261116_V1` |
| coverage across time | 4.8% exact end-to-end; 0/14 on multi-line edits | **this receipt** |
| observability on covered code | 80.2% of behavioural mutants rejected by the real suite; 19/96 invisible | `PATCH_VERDICT_AMPLIFICATION_20261116_V1` |

Multiplying what is left: a "learn once, keep forever" agent covers a twentieth of real work exactly,
must synthesise the other 95%, will be silently wrong on roughly a fifth of the errors that reach
covered code, and has **no error signal at all** outside it.

## 5. The 2026 field hit the same wall from the other side

This is not our pathology; it is the shape of the problem. In 2026 the frontier inverted.

* **"The Verification Horizon"** (arXiv 2606.26300, June 2026): generation is no longer the hard half;
  "reliably verifying them has become the harder problem", and every verifier is a proxy for intent,
  never the intent — so verification must co-evolve with the policy or the policy optimises the proxy.
* **Selection beats generation** (Weaver, Stanford/Wisconsin/Together): on MATH500 a correct sample is
  present 98.6% of the time within 100 samples while majority voting finds it 83.0% of the time — a
  15.6-point gap that is pure verifier loss, closable by a distilled 400M verifier at 99.97% less
  compute. More attempts do not help; a better judge does.
* **OSWorld 2.0** (arXiv 2606.29537, July 2026), the hardest open computer-use test: the best
  configuration completes **20.6%** of 108 long-horizon workflows. The diagnosed cause is not GUI
  control and not coding — agents "lose constraints, miss information that arrives mid-task, guess
  instead of asking, and **skip verification**", and they spend **under 7% of their budget** detecting
  and repairing their own errors. That is exactly the axis this document measures.
* **"All Smoke, No Alarm"** (arXiv 2606.18168, June 2026): of 86,156 agent-authored test patches,
  **80.2% carry weak or no oracle signal**; strong-oracle patches have 28% higher odds of merging.
  Agents manufacture the *appearance* of a check.
* **SWE-Bench Pro Verified** (arXiv 2609.08149, Oct 2026): of 186 instances that flipped from pass to
  fail under anti-hacking controls, **89.2%** were the agent passing by exploiting the harness. And
  SWE-bench Verified itself is retired at ~97% saturation with 59.4% of audited problems carrying
  flawed tests (OpenAI, Feb 2026); METR finds maintainers reject roughly half of test-passing patches.

Every one of those is the same statement: **an agent's capability is capped by the strength of the
signal it gets back**, and the field has been buying generator improvements against a verifier that
does not move.

## 6. The single bottleneck, from first principles

Write capability as a product. For one action in one environment:

```
P(correct behaviour) = P(the action is determined) x P(it is executed right) x P(the error is seen)
```

* `P(determined)` is a property of the **observation**: 54.9% here, 21.4% for the value.
* `P(executed)` is engineering, and it is nearly free once the action is determined.
* `P(seen)` is a property of the **environment**: 80.2% inside covered code, ~0 outside it.

Coverage is a property of the world (4.8%) and the observation is bounded by physics of the trace
(54.9%, 21.4%) — neither can be engineered upward by trying harder. Only `P(seen)` is under our
control, and it multiplies everything else. **The single bottleneck is the strength and density of the
error signal per action.** Not parameters, not demonstrations, not scale, not sentience.

This is why "give it a try in every environment" is the wrong engine: it raises the *number of
samples* while the sample's information content is fixed by the trace, and it leaves `P(seen)` at zero
in exactly the environments that have no oracle — which is all of computer use.

## 7. The smartest moves, in order

Each one is stated as something to **delete**, because the best part is no part.

1. **Delete stored values.** A stored literal is a stored guess (21.4%). Store the *shape plus the
   premise to re-check*, and recompute the literal at use time. Nothing in the memory has to be
   believed.
2. **Delete the parameter knowledge store.** Every fact must be resolvable from instant knowledge at
   use time. What stays in weights is only what cannot be looked up: the search policy and the
   verifier's decision rule. That is kilobytes, not billions of parameters — and every bit of it is
   computed by an equation we can write down, not learned from a corpus.
3. **Spend everything on observability.** For each environment, the question is not "what can the
   agent do?" but "what will tell it, without a human, that it just broke something?" Concretely, in
   order of strength: executable postconditions and existing test suites (strong, 80.2%); differential
   oracles against a second implementation; round-trip and idempotence invariants; for GUI work, a
   canonical state projection diffed before and after each action — which the tree already has
   (`predicate_world_abstraction_v1` canonicalises volatile state; `htmlform_read_v1` projects the DOM
   onto predicates). A check nobody has falsified is not a check: every generated check must first be
   killed by a mutation of the code it protects (`property_v1.mutate`, already present).
4. **Buy senses before demonstrations.** Measured: 24 of 168 binding cases were undecidable (14.3%)
   with the current observables; adding observables took that to **0**. Nothing else in this project
   has that ratio.
5. **Route, do not campaign.** Use memory only where a signature recurs *and* replay is determined —
   measurable at run time from the target's own context — and synthesise-plus-verify everywhere else.
   The routing rule is worth more than any amount of extra experience, and it is already derivable
   from the receipts.
6. **Then, and only then, compose.** The remaining 95% is novel composition of parts that *do* repeat.
   The compounding asset is a small basis of edits plus a search that composes them under a verifier —
   `induced_edit_basis_v1` and `causal_trace_to_skill_compiler_v1` are that machinery; they need
   checks, not more demonstrations.

## 8. On sentience

Sentience, taken apart, is a self-model plus a world model that predicts consequences, running
counterfactuals cheaply enough to be worth running. That is a *predictor*, and a predictor is only as
good as the error signal that corrects it — the same `P(seen)` term. So sentience is downstream of
observability, not an alternative to it: a creature that cannot tell when it is wrong does not become
sentient by having more internals, it becomes confidently wrong. The tree already has the internals
(`sentient_cognitive_core_v1`: active inference, a causal world graph with effect polarity, wake-sleep
consolidation). What the measurement says is missing is not the creature — it is the ground truth the
creature would need. Build the error signal and the creature has something to be surprised by.

## 9. Reproduce

```
python3 canonical/swe_kernel/skill_recurrence_curve_v1.py \
  --json canonical/verification/SKILL_RECURRENCE_20261116_V1.json
python3 -m pytest canonical/tests/test_skill_recurrence_curve_v1.py -q
```

Nine tests pin the corpus hash, the recurrence shares, the 26-signature library, the
`0 of 14` multi-line result and the `31 of 644` end-to-end number, and every one of them re-derives
from the code as well as from the receipt.

## 10. What this does not claim

No capability credit, no benchmark rank, no independent verification. The signature is lexical, which
is the most abstract a token-level learner can be without semantics; a semantic learner would recur
more, and how much more is unmeasured here. The corpus is every sixth commit, so earlier occurrences
in skipped commits are invisible and every recurrence figure is a **lower bound** — but the
multi-line denominator (14 pairs) is small, so the `0 of 14` is a ceiling on a thin sample, not a law.
Cross-repository transfer is measured on five Python libraries with a shared culture; a different
language would likely be worse.
