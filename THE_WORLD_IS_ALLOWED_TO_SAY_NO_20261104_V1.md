# The World Is Allowed to Say No

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

Last round the creature learned to ask a question. The answer was written `2.0 * probe[0]` in the
benchmark — the harness already knew it. A loop that can only ever be confirmed is not an
interrogation; it is a rehearsal.

This round the oracle is a real callable, and one of them lies.

---

## 1. Two states that were one state

When the admissible set is empty, `demand_evidence` said `UNRESOLVED`. That is correct for exactly
one of two situations:

- the grammar **never fit** the data — nothing has been contradicted, something has not been
  described yet;
- the grammar **fit, and then an observation destroyed it** — the model was sufficient and is now
  wrong.

These call for opposite repairs. Treating the first as the second throws away working ideas;
treating the second as the first keeps broken ones. The distinction is **historical** — it is a fact
about what the creature used to believe — so it cannot be read off the current example set. An empty
set looks the same whether it was never filled or was just emptied.

A module that forgot to carry that history would reproduce the exact defect it was built to fix.
And the first draft did:

```
lying oracle -> UNRESOLVED after 1 question(s), 0 explanation(s)   <- wrong
```

The refutation was detected, written into the trajectory, and then discarded by the summary line —
which asked the last `demand_evidence` call for its status. Fixed by carrying the fact forward and
reporting it:

```
lying oracle -> REFUTED after 1 question(s), 0 explanation(s)
   step 0  PROVISIONAL programs=12 explanations=3
   step 1  REFUTED     programs= 0   asked at [-3.5] -> saw 99.0, model said -7.0
```

`REFUTED` never hands back a body. Falling back to the cheapest survivor is the original defect in a
different hat. **9/9 findings as pre-registered** (`PREREG_OBSERVATION_REFUTATION_20261104_V1.md`),
including the one I said I expected to fail.

---

## 2. Building the oracle found two bugs in the synthesizer

Neither was reachable from the benchmark, because the benchmark never asked a question whose answer
was impossible.

**Stale collection.** `collect_admissible` cleared its handoff at the END of the call. One arm — the
1-level piecewise split — returned a body instead of recording it, so a collecting call could exit
early and `last_admissible_bodies()` would then report *the previous call's* bodies. Measured:

```
demand_evidence(2x examples)          -> PROVISIONAL  12 admissible
demand_evidence(2x examples + (0,5))  -> PROVISIONAL  12 admissible   <- stale
```

The second question admits **nothing**. It answered with the first question's answer.

**Bodies that were not Python.** That same arm passed a complete statement block into a recorder
that wrapped its argument in `return`, producing `return if x <= 0:` — fifty of them, all
uncompilable, all recorded as admissible. Then the grouping saw fifty identical signatures
(`<does not compile>`) and reported **one explanation → DETERMINED**. Confidence produced entirely
by garbage: not a wrong answer, but a wrong *certainty*, which is worse.

Both are the same shape as the errors that have recurred all session: a measurement instrument that
silently substitutes one thing for another — the previous call for this one, a statement for an
expression. Both were found by handing the machinery an input it had never been given, not by
re-reading it.

---

## 3. Who is to blame, and why the answer should make you uneasy

Drop each observation in turn and re-enumerate. Every removal that restores admissibility is a
suspect:

```
blame: 4 suspect(s), decisive=False -> 4 observations can each be blamed
   candidate 0: [[1], 2.0]      (without it: 14 programs)
   candidate 1: [[2], 4.0]      (without it: 14 programs)
   candidate 2: [[3], 6.0]      (without it: 14 programs)
   candidate 3: [[-3.5], 99.0]  (without it: 12 programs)   <- restores the prior exactly
```

Four suspects, and naming one would be a guess. But there is a sharper question: which removal
returns the model to **exactly** the size it had before? Only the last one. That is a real signal —
and it is also a weapon aimed at the truth.

Take a world that is genuinely piecewise: `2x` above zero, `99` below. Feed the creature three
points that all sit on one branch, then one true point from the other. Nothing is lying. The
diagnosis is identical:

```
restorers: [3]   -> "delete the fourth observation and your model is consistent again"
```

The cheapest repair is to discard the only evidence that the world changes. The mechanism cannot
tell a broken sensor from a regime change, and **it has a systematic preference for believing its
current model**. This is not a bug to be patched later; it is the confirmation bias that any
minimal-repair diagnosis carries, and the only honest move is to have it in the report.

What does help, without an oracle: add a second observation from the unexplained regime and the
"delete one" repair stops working —

```
one dissent : restorers = [3]
two dissent : restorers = []      the contradiction is no longer localised
```

That is the difference between *one reading went wrong* and *my description of the world is wrong*,
and drop-one alone can see it.

---

## 4. What changed in capability

Before: report that the evidence is insufficient. Ask where the explanations disagree.
Now: **drive that question through something that can refuse**, and keep "contradicted" separate
from "not yet described" — with the observer's own prediction shown beside what it saw.

`2x from 3 points` is unchanged: 12 programs → 3 explanations → one answer → `DETERMINED`.
The new path is what happens when the answer is not in the language.

**Non-claims.** No sentience. `REFUTED` does not mean an observation is false — it means the
observation and the descriptions cannot both be true, and this module cannot say which to give up.
Repair is not attempted. The oracle in these measurements is a Python lambda standing in for a
world; it is *callable* rather than hard-coded, which is a smaller step than it looks. Grouping
remains bounded by the probe range. `truth.achieved` stays false. $0.

---

## 5. Ranked next moves

1. **Repair instead of delete.** When two dissents rule out the cheap repair, the grammar needs a
   branch it does not have. That is composition, and it is now motivated by a measured failure
   rather than an intuition about generality.
2. **Make ambiguity a refusal by default** in the synthesizer rather than a report alongside the
   answer it already gave.
3. **A second, independent surface.** Drop-one can name suspects; only something that observes the
   same quantity another way can choose among them.
4. Domain tracking; canonicalising the `2/(1/x)` vs `2//(1/x)` split; the front door.
