# One experience is enough — if you can still refuse, and if it reaches the weights

**2026-11-12.** Base `b86e1823`. Branch `arena/4e471e35-brain`. Round 14.

Thirteen rounds measured this tree. This round measures the tree against the state of the art, because
the tree's laws should not be a house style — if they are right, 2026 says so; if 2026 says something
better, the tree is wrong.

It does both. Two of my claims were too strong, and one sentence I have repeated is wrong for the
reason that matters.

## 1. The 2026 record, in six lines

| | finding | source |
|---|---|---|
| **E1** | **Forgetting is not the problem.** On a 200-instance stream of one-pass episodes, "no method forgot measurably" | Continual-ARC, arXiv:2611.14505 |
| **E2** | **A harness gains nothing on unseen tasks; weights do.** "No harness-based method gains on unseen tasks, whereas weight-based learning shows substantial gains" | same |
| **E3** | **Generalisation is about half of memorisation** even where it works: `S_held = 0.29 [0.23, 0.35]` against `S_seen = 0.57 [0.48, 0.67]` | same |
| **E4** | **One verified attempt per task *can* become permanent**, but imitating or reinforcing that single attempt directly "destabilizes the policy"; self-distilling it from a frozen copy gains >22 points exact success | ASCENT, arXiv:2610.05303 |
| **E5** | **Unfiltered self-updates damage the model**: +3.01 nats on 125M, +6.00 on 760M; a settlement buffer that admits an update only if it improves an external check admitted 78.8% and netted +0.0534 nats | arXiv:2610.05076 |
| **E6** | **"Verifier outside the loop, held-out check, revertible ledger"** is the consensus architecture, not a peculiarity of this repo | arXiv:2607.13070, arXiv:2607.00871, arXiv:2606.26300 |

## 2. Where I was wrong

**I said a single experience cannot become permanent.** That is true of *harness memory* and false of
*weights*. ASCENT (E4) executes each task once, keeps the verified trajectory, and makes it a
persistent weight update — and it works, on ALFWorld, WebShop and AppWorld, at several model scales.
Continual-ARC (E1) adds the part that matters most for the owner's phrasing: across a hundred-plus
rounds **nothing forgot measurably**. Permanence is not the hard part. It was never the hard part.

The condition ASCENT puts on it is the interesting part: not imitation of the attempt, but
**self-distillation with hindsight** from a frozen copy, gated on the verification result. Directly
imitating or reinforcing the one attempt *degrades* the policy.

**And I have been pricing the wrong thing.** I kept saying "one lesson buys a binding". The sharper
statement, which the benchmark makes and this tree's own measurements echo, is:

> **Experience buys permanence almost for free. It does not buy generalisation, and generalisation is
> what the owner wants.**

## 3. Where the tree is right, and how exactly it is right

The tree's whole discipline — `output_verified`, measure-then-commit, a predicate that must be able to
refuse, verification by someone else — is E5 and E6, invented independently and, in this repo, applied
to *code* rather than to weights. That is not a coincidence and it is not fashion. Every serious 2026
system that lets an agent change itself routes the change through a check it cannot see or edit, and
keeps a ledger it can revert. The dangerous number in that literature is the one this repo has spent
eleven rounds on: a self-approved "pass" that means nothing.

Round 13's measurement is the harness-side shadow of E2. Showed a code change once, the learner wrote a
rule about `product == None` and refused the same defect under three other names; showed it twice, it
wrote `?1 == None` and edited all four. That is "the harness stores what it saw" at the scale of one
rule, and E2 says storing is where the gain stops on unseen tasks.

## 4. The measured gap, as a number

```
0 of 145 registered capabilities update weights
```

(`round_14_claims_ledger_20261112.py`; the scan reads every field of every record and looks for
`lora|fine-?tun|weight[ _-]?update|fast weights|gradient step|distill`.)

That zero is not an accident of authoring. It follows from a standing law: **no model in a
Brain-credited producer path.** The law is right — E5 is exactly what happens when the thing that
produces is the thing that grades. But the law also entails that this tree can only ever be a
**harness**, and Continual-ARC is the first benchmark to put harness and weights on one score, and its
verdict on the harness column is "no measurable gain on unseen tasks, and often less than a cache of
the demonstrations themselves".

So the limiting factor is now named precisely, and it is not learning theory:

> **The tree cannot generalise because it has no channel into the weights, and the channel is what the
> 2026 evidence says generalises.**

## 5. What that changes about the plan

Kill these — they are now measurably dead, not merely argued against:

* **"Give it one pass in every new environment."** Harness persistence on unseen tasks: no measurable
  gain (E2), and often below a demonstration cache. Environment breadth multiplies bindings, and
  bindings are not what is missing.
* **"Show it once and it has learned it."** It learns *the example*. Round 13: 1 of 4. E2 says the same
  thing about libraries of examples.
* **"One demonstration is the acceptance test."** E5's +3 to +6 nats is what an unadmitted update does
  to a model, and eleven rounds of this repo are what a self-approved pass does to a gate.

Build these, in this order:

1. **Keep the verifier exactly where it is.** Code that can refuse, on a check the producer cannot
   edit, with a ledger that reverts. That is E5, E6 and eleven rounds of this repo agreeing. It is the
   one part of this project that is ahead of the frontier rather than behind it.
2. **Then open a student channel — separately.** A weight-updating copy trained offline from the
   *verified receipts this repo already emits*, self-distilled with hindsight (E4), admitted only when
   a held-out check improves (E5), and **never** in a credited producer path and never a grader. The
   law stays: truth is code. The student is a consumer of truth, which is what a model is allowed to
   be — and it is the only configuration in the 2026 record that moved the held-out column.
3. **Choose the second demonstration adversarially**, for what it leaves alone. Round 13's `Loader=`
   case is that lesson in one file.

## 6. On "a sentient creature"

Nothing measured here bears on it, in either direction, and this round changes nothing about that. What
the record does support is narrower and, for the stated goal, more useful: a system whose experience
becomes permanent without being trusted is not closer to a creature, it is closer to a confident
liar. The property that 2026 keeps rediscovering — an external check the system cannot satisfy by
believing itself — is the same property that makes an agent worth deploying and the same one eleven
rounds of this repo were spent repairing. Sentience is not on the path. Verification is.

## 7. Receipts

```
python3 round_14_claims_ledger_20261112.py
python3 -m pytest -q canonical/tests/test_round_14_claims_ledger_v1.py       7 passed

tree claims holding      7 / 7
external claims linked   6 / 6   (linkage only)
```

The ledger re-runs the tree-side evidence each time it is read, and refuses any claim that carries
neither an executable predicate nor a complete citation. Its own limits are printed with the result:
linkage is not truth, and a tree predicate checks the tree, not the world.

## 8. Non-claims

External claims are recorded, not re-derived: a reviewer still reads the papers. Continual-ARC and
ASCENT are someone else's measurements on other systems, quoted for what they say and not as results
about this repo. No capability registered, no file written at runtime, no benchmark or acceptance
credit, `truth.achieved` false, $0, zero model dependency.
