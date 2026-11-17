# The Ceiling of "Learn It Once"

**`THE_CEILING_OF_LEARN_ONCE_20261116_V1`** · 2026-11-16 · branch `arena/e93c5f9e-brain`

## Your question, answered with a number instead of an opinion

> *"Give the model the most advanced actions, let it experience each once, and it learns them
> permanently — therefore all computer use and advanced software engineering are solved. Am I right
> or wrong?"*

**Right about acquisition. Wrong about yield. And the gap is not learning speed.**

For the first time I have multiplied the measured parts instead of arguing about them. The result:

> **One-experience permanent memory serves 4.814% of real edits end to end — one in twenty-one.
> On multi-line edits, the advanced part, it is 0 of 14.**

## The product, and where every term comes from

All three terms were measured on real repositories, on main, before this session. Nothing here is
re-estimated, and none of it is synthetic.

| term | value | receipt |
|---|---|---|
| recurrence (strict, both context sides) | 102/644 | `LEARN_ONCE_KEEP_FOREVER…` |
| replay determinacy across time | 31/102 | `LEARN_ONCE_KEEP_FOREVER…` |
| **→ end to end** | **31/644 = 4.814%** | **one in 20.8** |
| multi-line edits served exactly | **0/14** | `LEARN_ONCE_KEEP_FOREVER…` |
| cross-repository, multi-line, strict | 2.1% | `LEARN_ONCE_KEEP_FOREVER…` |

The ceiling is a **product of exact fractions**, not prose. That matters: if anyone later raises
recurrence, the ceiling rises by exactly that factor and these tests fail loudly. A claim you can
falsify is worth more than a claim you can only agree with.

## The three things I checked myself this session

**1. Acquisition is solved — exactly, not approximately.** The shipped figures (4 demonstrations for
the git task, 1 for the premise task) came from a *greedy* cover, which is only an upper bound. I ran
the tree's exact cover solver and then an independent exhaustive search: **no smaller cover exists**
for either. Four experiences licence every distinguishable situation; one does for the premise task.
**The number of experiences needed was never the open question.** It has an exact answer and it is
small.

**2. Verified skills still do not compose.** I reproduced this live on the tree's own store: two
rules, each **crystallized: True** on its own demonstration, applied in order, return the text
unchanged — verdict `FAIL`, reason `STEP_REVERTED_EARLIER_STATE:step2`, **net change: none**. Every
local check passes both steps. A local check cannot see a global revert.

This is the finding that actually kills the framing. Real coding is a **sequence**, and "N verified
skills" is not evidence about a sequence of two.

**3. The premise/sense work from last session stands** — one tool call makes the agent's decision
fully decidable, where the shipped sense read eleven and was still insufficient for the premise task.

## So: what is wrong, and what is real

**Real, and genuinely rare:**

- **Acquisition is solved and bounded.** Exact minimum demonstration counts, no smaller cover.
- **Precision is achievable.** One-authority on 691 real sites; the premise is priced at one call.
- **Verification discipline exists** where nearly nobody has it — a refuse-capable verifier on every
  path, 296 independently attested reproductions.
- **There is a real fast path.** Verbatim and literal-moving edits — one-line version bumps, import
  renames, message tweaks — are served essentially for free. The recurring vocabulary is **59
  signatures, 7 of which carry 50%** of all recurrence.

**Not real, and each with a number:**

- *"Learn each once → everything is solved."* Serves **4.81%** end to end; **0 of 14** multi-line
  edits; **2.1%** cross-repository. Memory is a **cache for the repeated part**, and advanced
  engineering is defined by the *novel* part.
- *"Learning faster is the lever."* **No.** Learning rate multiplies a term that is already small.
  Making acquisition infinitely fast leaves the yield unchanged at 4.81%, because that fraction is a
  property of **the work**, not of the learner. **The answer to the bottleneck question is NO.**
- *"More experience closes the gap."* The undecidable set is invariant to experience. Recurrence does
  rise with time in one repository (0.149 → 0.394 by quarter) but saturates **under 40% of gross**,
  which after replay determinacy is well under 12% of net.
- *Sentience.* Not measured, not supported, not required. The only proxy — does experience change
  competence on new problems — is negative.

## The single bottleneck

Not learning speed. Two walls, and they are different walls:

> **1. Real work is mostly not repetition.** 84–88% of commits contain no sibling at all, and the
> 59-signature vocabulary is tiny. You cannot memorise your way through novel work.
>
> **2. Correctness of a sequence is not implied by correctness of its steps.** Two individually
> verified skills compose to a no-op and every local check passes. This is a *global* property that
> no amount of per-step verification can establish.

The second is the more important one, because it is the one the field is also hitting — 80.2% of
86,156 agent-authored test patches carry weak or absent oracle signals, and self-improvement is
"gated by the same bottleneck: the verifier."

## What is actually missing, stated once

The tree splits real work three ways, and the third way has never been measured:

| | share | what it needs |
|---|---|---|
| **MEMORISE** | 31/644 ≈ 4.8% | a lookup and a postcondition check |
| **SYNTHESISE** | the rest | compose a new edit, check it mechanically |
| **REFUSE** | **unmeasured** | the honest answer where no check exists |

**The least honest number in this tree is the REFUSE share.** We do not know how much real work has
no mechanical postcondition — and that number decides whether an agent can be trusted at all, because
where no check exists the only correct output is a refusal, and an agent that never refuses is an
agent that is silently wrong at a rate nobody has measured.

## What I am not going to claim

- That this measures your idea's *potential*. It measures its **yield on the work that exists today**,
  which is the only thing that can be measured.
- That 4.81% is permanent. Recurrence rises with time in a repository and a good cache earns its
  keep. It is a real and cheap win — for the part it covers.
- That the ceiling is a verdict on the whole program. **The memorise fraction is not where the
  capability lives.** It is where the *cheap* capability lives.

## Reproduce

```bash
python3 canonical/swe_kernel/the_ceiling_of_learn_once_v1.py \
        canonical/verification/THE_CEILING_OF_LEARN_ONCE_20261116_V1.json
/tmp/v4/bin/python -m pytest canonical/tests/test_the_ceiling_of_learn_once_v1.py -q   # 14 passed
```

## Instrument limits — stated plainly

- **Every term is cited, not re-measured.** The only things executed here are the composition
  defect (live, on the tree's own store) and the arithmetic. Terms come from three merged receipts
  measured on 691 real sites, 245 sibling pairs, and a real `git` environment.
- **The corpus is five Python repositories.** It is not all software engineering, and it is not a GUI.
- **31/644 is one corpus's end-to-end rate**, not a law of nature.
- **The REFUSE share is unmeasured**, and is labelled as the least honest number here rather than
  quietly folded into "synthesise".
- **No capability credit, no benchmark rank, no independent verification.** Authority
  `NONE__PRODUCER_RUN`. $0, zero model calls.
- **A bug I caught in my own receipt:** `str(Fraction(0, 14))` renders as `"0"`, silently dropping
  the denominator — so a "0 of 14" term would read back as a bare zero. The exact ratio is now
  carried as numerator/denominator so the 14 survives.
