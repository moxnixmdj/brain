# Pre-registration — what happens when the answer is impossible

**2026-11-04 · before implementation · authority NONE**

## Why this and not more plumbing

The interrogation loop terminates with `2.0 * probe[0]` hard-coded in the benchmark. The creature's
question is real; the answer is supplied by something that already knows the truth. Wiring that to a
callable is ten lines and proves nothing.

What a real observation surface does that a friendly harness never does: **it can return a value no
admissible body predicts.** Every mechanism built so far assumes an answer shaves the admissible set
down. None of them says what happens when the answer annihilates it.

That is the missing capability on the table (`notice a *false* answer`), and it is the one place
where "my evidence is thin" and "my idea is wrong" must not be the same report.

## Predictions

| id | prediction | how it is scored |
|---|---|---|
| **R1** | With a truthful oracle the loop reaches `DETERMINED` in **one** question, same as the harness path. | trajectory length and final status |
| **R2** | An answer that no admissible body reproduces empties the set and is reported **`REFUTED`** — not `UNRESOLVED`, not `PROVISIONAL`, and it does **not** fall back to the cheapest body. | status string and `chosen is None` |
| **R3** | `UNRESOLVED` and `REFUTED` stay distinguishable: zero bodies *from the start* means the grammar never fit (extend the grammar); zero bodies *after* an answer means a previously-sufficient idea was contradicted (repair the idea). | two different statuses on two different inputs |
| **R4** | The creature can name **which observation to doubt**: dropping each example in turn and re-enumerating yields a set of suspects; answers whose removal restores admissibility are suspects. | suspect set contains the injected bad answer |
| **R5** | With only four examples the drop-one test is **not decisive** — more than one example will be droppable, and the module reports a **set**, not a single culprit. Picking one would be a guess dressed as diagnosis. *This is the prediction I expect to be least comfortable and most likely to fail; if it fails, the mechanism is better than predicted and I will say so.* | `len(suspects) > 1` |

Non-predictions: I do not predict it can repair the grammar (next round), pick the true observation
among suspects (that needs a second, independent surface), or that `REFUTED` means anything is
*false* — only that the creature's descriptions and its observation cannot both be true.

## Stop condition

If R2 fails because the code cannot represent "the set is empty for a reason", the defect is in
`demand_evidence`'s vocabulary, not in this module, and the fix belongs there.
