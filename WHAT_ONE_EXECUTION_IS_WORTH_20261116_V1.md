# What one execution is worth

*2026-11-16. Seven real actions, real programs, real state variants. AUTHORITY: NONE — producer-run measurement.*

---

## 1. The claim, split so it can be tested

> "We solved instant learning. So give the model the smartest actions, let it do each one once, and it knows
> them for ever. Then we have the most advanced coding agent, and we can do anything on a computer."

That is three separate assertions, and they fail or hold separately:

| # | assertion | status |
|---|---|-|
| 1 | one execution teaches the action | **half true** — it eliminates readings; it does not pick one |
| 2 | what it teaches stays true | **true only where the survivors agree on every state the work can reach** |
| 3 | therefore all computer use is solved | **false** — and the gap is measurable, not philosophical |

The tree already measured the coding half of #1. `IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1`: after one
published example, a real bug's candidate space still holds a **median of 1037 programs (max 16,480)**, about
10.0 bits of information; **4 of 23** tasks are identified; the minimax question order needs 13 questions
against 105 for corpus order and 99.8 for random; and **7 of 23 are not identified even after every example**,
because the right behaviour is not in the space at all. A GUI measurement (`demonstration_version_space_v1`)
reports **13.05 of 32** descriptions surviving one demonstration.

The frontier's answer to the same problem is to not compute any of this. **Tycho** (ARC-AGI-3,
arXiv 2607.28287) says it outright: *"Tycho does not maintain an explicit version space"* — the policy records
competing hypotheses in notes and **picks one**. And knowing when not to act is measurably unsolved:
**AgentAbstain** (arXiv 2607.10059) finds the best of 17 frontier models at **59.5%** paired accuracy, with act
accuracy exceeding abstain accuracy by **21 points**.

## 2. What was missing, and is now measured

The computer-use half had no measurement, and — more importantly — the *decision* the claim needs did not exist:
given the survivors of one execution, is one execution enough? That is decidable, and this is the whole answer:

```
survivors agree on every state the work can reach   -> one execution was enough
survivors split on some reachable state             -> here is the cheapest execution that settles it
no survivor predicts what happened                  -> refuse; never memorise the observation
```

Seven real actions, a stated grammar of **343 readings per action** over the directory state, one real
execution first, real programs, independent goal commands:

| action | survivors after 1 | spent | verdict | permanence |
|---|---|---|---|---|
| `sort -o out.dat payload.dat` | **2** | 1 | SAFE_FOR_THIS_TASK_ONLY | **TASK_SCOPED** |
| `sort -u -o out.dat payload.dat` | **2** | 1 | SAFE_FOR_THIS_TASK_ONLY | **TASK_SCOPED** |
| `cp src.dat out.dat` | 5 | 3 | IDENTIFIED | PERMANENT |
| `head -c 8 payload.dat > out.dat` | 1 | 1 | IDENTIFIED | PERMANENT |
| `tac payload.dat > out.dat` | 1 | 1 | IDENTIFIED | PERMANENT |
| `sha256sum payload.dat > out.dat` | 1 | 1 | IDENTIFIED | PERMANENT |
| `sort -R payload.dat -o out.dat` | 7 → **contradiction** | 2 | VOCABULARY_INSUFFICIENT | **REFUSED** |

The two readings that survive `sort` on a duplicate-free list are exactly:

```
sort:payload.dat>out.dat
sort_unique:payload.dat>out.dat
```

**`sort` and `sort -u` are the same action on a list with no duplicates.** The one-shot learner keeps the first
survivor, is right on every state the task reaches, and is wrong the first time a duplicate appears — 5 further
states across 2 actions in this measurement. That is the entire answer to "he does it once and knows it
permanently": **it worked, and "permanently" is the part that is false.**

Three more things fell out of the measurement and none of them is decoration:

- **Repeating the same execution never helped.** 0 of 7 actions changed verdict. Doing it twice is informationally
  identical to doing it once — the second run is a column already spent. So "let him experience it once" and
  "let him experience it a hundred times" are the same amount of evidence, and the only thing that buys knowledge
  is a *different* state.
- **One execution can look perfect and be a lie.** `sort -R` on a single-line file is indistinguishable from a
  copy: 7 readings survive, the agent appears to have learned something. The second execution — a state the
  discriminator chose *before* seeing its outcome — contradicts every reading, and the answer is **refuse**, not
  a memorised guess. The vocabulary has no word for "random", and the system says so instead of picking.
- **The discriminator can only choose among the states you generate.** `cp src.dat out.dat` needed a state that
  varies the *source*; with only single-line sources, `copy`, `sort`, `reverse` and `sort -u` are genuinely
  indistinguishable, and the verdict "behaviourally identical" was right about the states and wrong about the
  world. That is a real limit and it is now stated in the law, not hidden.

## 3. Why this is better than the way agents learn now — precisely

Not because it learns faster. Because of **what unit it keeps**.

A trajectory-based or skill-based agent keeps *one* description of what happened, chosen silently. This keeps
**the set of descriptions that the observation did not rule out**, plus a three-way decision rule computed over
it: act when every survivor agrees, spend one execution when they split, refuse when none fits.

That is strictly more information for the same number of executions, it costs no parameters — the set is
regenerated from the state and the grammar, and the grammar is arithmetic, not weights — and it makes the
agent's ignorance an object it can reason about instead of a silence. Under "the best part is no part", this is
the rare case where *less* storage is *more* knowledge: one survivor is a guess; the survivor set is a
certificate of what is still unknown.

And it closes the loop with everything else measured here: contracts acquired from one execution
(0.5000 → 1.0000 on unseen bindings, zero false alarms), facts kept honest across a sequence (detected 3/3,
cause two steps before the symptom), work repaired from a dependency discovered by intervention (goal 3/3,
8 steps instead of 14) — all of which assume the contract is *right*. This is the piece that tells you **when
it is not yet right**, before you spend the second execution.

## 4. So are we done? No — and here is exactly what is left

Learning is no longer the bottleneck, and that is real. What the claim leaves out is that learning was never
the only cost. Three questions remain, and they are now the only ones:

1. **The vocabulary.** A sufficiency verdict is relative to a stated grammar. When no reading fits — `sort -R`,
   a network call, a GUI whose only observable is pixels — the honest answer is *refuse*, and it is measured
   here: 1 of 7 actions, and 7 of 23 real bugs in the coding space, where the right behaviour is not in the
   space at all. **A behaviour outside the grammar cannot be learned by any number of executions.** That is the
   synthesis wall, and no learning speed crosses it.
2. **The state set.** A verdict is relative to the states you generated. Two readings that differ only on a
   state nobody generated stay conflated, and the agent is confident and wrong. Generating the right candidate
   states is itself a capability, and it is not this receipt.
3. **The check.** Everything here assumes you can tell what happened. On a shell that is a hash of the
   directory; on a GUI it is a projection; on a remote service it is a response. The measurement of *which
   observation separates the ways an action can be wrong* exists here (`distinguishing_projection_v1`,
   separation + stability), but its ceiling on a pixel-only surface is not measured — and it is where "any
   computer use" actually lives.

So the honest sentence is: **give the agent the actions and it learns each one as far as one execution can
identify it, permanently where that is provable, and it now knows which of the two it has.** The remaining
bottleneck is not learning. It is **producing a hypothesis that is not in the vocabulary** — synthesis — and
the second is **choosing the observation** that makes an environment identifiable at all.

## 5. Sentience

Not measurable here, and not needed for any of the above. What *is* measurable, and what this module is a small
instance of, is the difference between a system that pattern-matches and one that can be **wrong on purpose**:
this one computes what its own knowledge fails to determine, and says `REFUSE` rather than guessing. That is
the only sense of "understanding" that has an experiment attached, and it is the sense I will keep building on.

---

*Receipt: `canonical/verification/DEMONSTRATION_SUFFICIENCY_20261116_V1.json`. Code:
`canonical/swe_kernel/demonstration_sufficiency_v1.py` (bridging the tree's own `finite_identifiability`
kernel — reused, not rebuilt). Tests: `canonical/tests/test_demonstration_sufficiency_v1.py` (11 live + pinned).
Law: `CAPABILITY_LAW_20261116_V1.json`, `demonstration` block, sha-pinned. `p_correct` unchanged at 0.2978;
what changed is that a learned contract now carries a certificate of what it does not know.*
