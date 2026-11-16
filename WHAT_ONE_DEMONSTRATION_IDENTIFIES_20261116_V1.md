# What one demonstration identifies

*Answer to: "we already solved instant learning — so give the model the most advanced actions once,
and it has them permanently, everywhere. Am I right or wrong?"*

Measured on this repository's own code, no model in the loop (0 model calls, $0):
`canonical/swe_kernel/one_demonstration_identifies_v1.py`,
receipt `canonical/verification/ONE_DEMONSTRATION_IDENTIFIES_20261116_V1.json`.

---

## 1. The one-line answer

A demonstration is a **point**. What it licenses is not the operation but a *set* of candidate
applicability conditions, and one point is consistent with almost all of them. Measured here: after
one demonstration the honest answer is "it applies everywhere", which is wrong on **297 of 319**
held-out sites. Two **chosen** observations turn that into a condition with **precision 1.000 and 0
dangerous errors**, at **recall 0.455** — and the remaining 55% cannot be predicted from any of the
ten observables at all, because 18 real sites are identical to the applicable ones in every one of
them and still refuse. The residue is decided by the operation's own **proof**, not by memory.

So: right that one exposure can be turned into something durable and free; **wrong** that exposure
is where the durability comes from. The two chosen observations did the work, and the proof is what
makes the answer safe.

## 2. The experiment

The operation is the bundle's own `inline` skill — a real learned action with a stated four-condition
premise. The sites are **479 real sites** in this repository (a deterministic stride over every name
bound in a top-level function, 5,532 files scanned). The oracle is the skill itself, executed at the
site in an isolated copy of the file and judged by the tree's independent verdict: the file changed,
the sentence matched, everything outside the named function byte-identical. So "applicable" is a
fact about the code, not a label anyone wrote.

The facts are ten **observables** read straight from the AST — plain binding, set once, read once,
next statement in the same block, first computed, computed once, not in a loop, no nested
rebinding, not a parameter, assignment alone with no comment. Never executed, never a verdict.

| arm | what it is allowed to use | held-out precision | dangerous errors | recall |
|---|---|---|---|---|
| **one demonstration** | one applicable site | **0.069** | **297 of 319** | 1.000 |
| **two chosen observations** | max-information-gain sites (`contrast_selection_v1`) | **1.000** | **0** | 0.455 |
| **random observations** | same budget, arbitrary sites | identified a condition in **0 of 12** sequences | — | — |
| **vocabulary check** | all 479 observations | separation **impossible**: 18 sites share every fact and differ | — | — |

The learned condition after two chosen observations is `use.first_computed ∧ use.read_once`. That is
not a coincidence and not a fitted coincidence: those are exactly the two conditions the skill
itself proves per site, and the contrast selector found them by choosing the sites that split the
surviving hypotheses most evenly — not by seeing more sites.

## 3. What each arm actually says

**One demonstration is not a small amount of knowledge. It is zero knowledge with a confident
face.** `applicability_v1.learn` refuses to invent a requirement from a single success
(`UNDETERMINED__NO_CONTRASTING_OUTCOME`, 0 survivors) and that refusal is correct: the only
requirement consistent with one success is the empty conjunction, which admits everything. Acting on
it means acting on 319 sites of which 297 were not eligible. The failure is not imprecision; it is
that the direction of the error is the dangerous one.

**Choosing is the mechanism, repeating is not.** All twelve random sequences failed to identify a
requirement at all; the chosen sequence needed two observations. This is the same asymmetry the tree
measured earlier at the requirement level (one success identifies 0 of 200 requirements; chosen
contrasts identify 25/25 in a mean of 2.76 demonstrations) — now reproduced on real code with a real
oracle and a real operation.

**The tail is not a fact, it is a proof.** Eighteen sites agree with the applicable sites on every
one of the ten observables and still refuse. The skill's own reason for each of them is a refinement
of one condition — "the first thing the next statement computes, **exactly once**" — that a static
fact vocabulary cannot see, because deciding it means *constructing the rewritten program and
comparing it with the original*. So the certificate is not a hole in the sensor that a better sensor
would close cheaply: for this operation the deciding observable **is the proof**, and the proof costs
a rewrite plus an AST comparison (~55 ms, measured), not a fact lookup.

That is the vocabulary-insufficiency objection, measured rather than asserted: no number of
repetitions separates those 18 sites, because they are the same point to the representation and
different worlds to the operation.

## 4. The three objections, each answered with a number

| objection | answer on this code |
|---|---|
| **Identifiability**: one trace is consistent with exponentially many hypotheses | one demonstration leaves **0 licensed requirements** and the maximally general one; 297/319 held out would be acted on wrongly |
| **Vocabulary insufficiency** | **18 sites**, identical in all ten observables, opposite outcomes; the missing observable is the operation's own proof |
| **Synthesis–verification asymmetry** | replay reaches the part of the space its premise covers (measured previously: 5.3% inline, 86.3% rename); the rest needs composition, and composition needs the same per-step proof |

## 5. What this means for the plan, and what the weights are for

"Give the model the most advanced actions and let it experience them once" produces, at best, a
**predictor with recall 0.455** — and a predictor is only safe when its precision is 1.0 and it is
used as a **veto**, not as a licence. The correct arrangement, and the fastest one, is:

1. **predict** (cheap, learned from a handful of chosen observations, precision first): "is this site
   even a candidate?"
2. **prove** (per site, exact, ~55 ms, $0): construct the rewrite and check it means the same thing;
3. **act** only if the proof holds; otherwise **withhold and say why**.

That ordering buys the speed of learning without buying its unsafety: the predictor saves the proof
wherever it can certify positively, and the proof covers 100% of what is actually done. Nothing here needs a model, and the whole loop — sites, facts, oracle,
contrast selection, certificate — is arithmetic and execution.

The weights, under your rule that "the best part is no part" and that no parameter may be a knowledge
house, carry three things and nothing else: **which observation to ask for next** (the tree already
computes this exactly, with rationals and no floats), **which observable is missing** when the
certificate fires (the certificate names the seam), and **the predictor's features**. Each of those
is a decision, and each decision can be scored against a measured boundary. Knowledge stays in the
instant-knowledge source; skills stay in the store with their conditions; proofs stay proofs.

## 6. Am I right or wrong

**Right:** instant capture is real and cheap; a learned action can be kept forever at $0; and the
right way to grow it is *choosing* observations rather than accumulating experiences.

**Wrong:** that one experience is enough to apply an action anywhere, and that computer use is solved
by handing over the most advanced actions. One experience licenses nothing (precision 0.069). Two
well-chosen experiences license a condition that is exact but partial (1.000 / 0.455). And a real
share of the world is provably outside any static description of the action (18 of 479 sites) — for
those, only the proof decides, every single time.

**The bottleneck, stated once:** not experience, not memory, not the model — **the observable the
decision needs**. Growing capability means growing the vocabulary of observables (including proofs
as observables) and choosing the cheapest one that decides. Everything else is bookkeeping.

## 7. The smartest next moves, each falsifiable

1. **Ship the veto.** Use the learned condition only to skip proofs it can certify, never to license
   an action the proof has not checked. Falsifier: any damaged site in a run using the veto.
2. **Close the certificate loop.** When `separation_report` names blocking sites, add the observable
   that distinguishes them — for the 18 here, that observable is the rewrite equality itself — and
   re-measure recall. Falsifier: recall does not rise, or dangerous errors appear.
3. **Run the same three-arm protocol on composition.** The honest test of the whole thesis is a
   two-step task where step two's premise depends on step one's effect. If chosen contrasts identify
   the composition as cleanly as they identify a single condition, the programme scales; if they do
   not, that is the real frontier and it should be measured before anything is built on top.
4. **Do not build:** more demonstrations of the same operation; a similarity-based licence to act; a
   knowledge house in the weights. Each of those spends effort without moving precision, recall, or
   the certificate.
