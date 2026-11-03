# Pre-registration: count explanations, not programs

**Written before implementing. 2026-11-04 · authority NONE · `truth.achieved` false**

## The defect

`demand_evidence` reported 12 admissible bodies for the three examples of `2x` and marked the answer
PROVISIONAL. But 10 of those 12 are **the same function spelled differently** — measured:

| group | members | example |
|---|---|---|
| A | 10 | `(x / 1) + x`, `(x / 1) * 2`, `(x * 2) / 1`, `2 * (x / 1)`, ... |
| B | 1 | `2 / (1 / x)` |
| C | 1 | `2 // (1 / x)` |

So the honest headline was never "12 explanations". It was "3 explanations, one of which is written
ten ways". The module conflated *how many programs fit* with *how many ideas fit*, and the PROVISIONAL
label was therefore too pessimistic in one sense (10 of 12 are the same choice) and too vague in
another (it did not say how many genuinely different answers there were).

## The change

Group admissible bodies by their **behavioural signature**: the values they produce over a probe
range. Members of a group are counted as one explanation. Report `explanations` alongside
`admissible`.

## Predictions (falsifiable, stated before the run)

**X1.** Programs 12 collapse to 3 explanations on the `2x` case, and the collapse is by behaviour,
not by string similarity.

**X2.** After one answer is supplied (the existing interrogation step), explanations fall from 3 to
1 — because the single disagreement witness inside group A is what separated B and C. If explanations
do not reach 1 there, the grouping is wrong or the ambiguity is real; either way I predict it
reaches 1 and will report it if it does not.

**X3 (the load-bearing one).** Grouping must be certified, not assumed. A claimed grouping of 10 is
only honest if the 10 agree on the probe range AND I say the range bounds the claim. I predict I can
construct a pair that agrees on every probed integer and differs at a fraction, so the grouping must
carry the probe range in the report.

**X4 (the counter-risk).** Grouping could hide a genuine difference by probing too narrowly. I
predict this benchmark cannot rule that out in general — only exhibit that the range is stated.

**X5.** Simplical cost should be applied to the GROUP, not the program: the cheapest member
represents its group. Previously the tie-break compared 12 programs; after grouping it compares 3
ideas, so a tie is a tie between ideas and means something.
