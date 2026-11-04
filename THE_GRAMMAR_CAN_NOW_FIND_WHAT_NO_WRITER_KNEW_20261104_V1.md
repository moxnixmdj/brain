# THE GRAMMAR CAN NOW FIND WHAT NO WRITER KNEW

2026-11-04, round 23 result. For `PREREG_THE_GRAMMAR_CAN_ONLY_EXPRESS_WHAT_A_WRITER_KNOWS_20261104_V1.md`.
Base `499f731c1b`. Authority `NONE`. `truth.achieved` false. $0.

Predictions: **P1, P2, P4, P5 PASS. P3 moot** (the writer no longer runs for this class, so there is
nothing for it to improve). Two further findings are recorded below, one of which killed my own P2 as
originally written.

---

## 1. The defect, restated

Previous rounds assumed the problem was that the creature could not *learn*. This round measured the
layer above that, and the answer was worse.

Asked for a period-3 block `[-2, 5, 1]` with growth disabled — no writer, no structure diagnosis —
`_generate_candidate_expressions` returned:

```
general grammar result: NO_CONSISTENT_HYPOTHESIS | ok= False
```

The working program `_block[int(x0) - int(x0/n)*n]` was **not in the reachable expression space**. It
existed only because `synthesize_table_organ` writes it. Handing the grammar a "primitive" organ did not
help either — with a period-3 table registered as a token, period 4 still failed, because a token that
hardcodes a block is a remembered answer, not a composable one.

So the creature's "ability" to handle repeating structure was a code path, and the honest name for that
is static: not a lookup table of answers, but **a grammar that can only express shapes somebody already
wrote a writer for**. Learning over a language that cannot express the answer is not learning.

## 2. What changed

One **parametric node** in the general grammar: `_solve_parametric_table` proposes a table whose period
`k` and entries are *solved from the evidence*, as an ordinary candidate expression. It is not
privileged — it enters the same version space as projections, affine forms and inlined organs, and the
existing loop decides.

Deliberately, it proposes **every** period consistent with the evidence and lets the examples eliminate
the wrong ones, sorted shortest-description first. It never decides; it only puts a hypothesis on the
table (literally) for the version space to judge.

## 3. Measured, through the real path

**Search alone, writers disabled, one rule, no per-period code:**

| structure | examples | status | held-out (60 inputs never shown) | questions |
|---|---|---|---|---|
| period 2 | 3 | DISAMBIGUATED_AND_CRYSTALLIZED | **60/60** | 3 |
| period 3 | 4 | DISAMBIGUATED_AND_CRYSTALLIZED | **60/60** | 3 |
| period 4 | 5 | DISAMBIGUATED_AND_CRYSTALLIZED | **60/60** | 2 |
| period 5 | 6 | DISAMBIGUATED_AND_CRYSTALLIZED | **60/60** | 2 |
| period 7 | 8 | DISAMBIGUATED_AND_CRYSTALLIZED | **60/60** | 2 |

**Through the live executor** (`sovereign_perform` on a booted `Creature`, id `mystery:searched-not-written`):

```
learned_status   DISAMBIGUATED_AND_CRYSTALLIZED   q = 2
learned_organ    parametric_table_3
answers          [7.0, 7.0, -2.0]                 = expected
```

**2 questions, where the writer path spent 14** — 7× cheaper, and now genuinely *searched* rather than
emitted.

**Still refuses** (unchanged): `x*x`, `x^3`, `floor(x/7)` all return
`HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED`.

## 4. Findings that were not in the pre-registration

**(a) My P2 was impossible as written, and the failure was information, not code.** I predicted periods
4, 5 and 7 would be found **from three examples each**. They were not, and the reason is a property of
the world: with samples at x = 1, 2, 3 a period-4 block has one entry that was never observed, so the
period-3 reading fits every observation available. The node correctly proposed period 3. The prediction
was wrong, not the implementation. Restated honestly in the test suite: with three examples a longer
period **must not** be credited, and the creature must not claim it. The fix is more evidence, not more
code.

**(b) Two of my own bugs were caught only because I drove the real path.** The node first used `_a0`
while the wrapper emits `x0`; the candidate was then dead on arrival and the failure looked exactly
like "no structure here". My repair, a `.replace("P", ...)` into a format string, then substituted into
the substitute and corrupted the expression. Both were found by evaluating the emitted source, not by
reading it.

## 5. Honest limits

- **A parametric node is still hand-designed.** This replaces N writers with one grammar rule whose
  parameters are searched. It is strictly less static — one rule for all periods, no per-structure code
  — but it is *not* the creature inventing its own language. Calling this "emergence" would be the same
  overclaim as round 19's, and it is refused here in advance.
- **It covers one structure class**: repeating blocks. It does not make the creature generally capable.
- **Cost floor is real and unchanged.** Identifying an unknown period needs a full observation of the
  block; unseen residues are unknowable. `table_evidence_requirement(P) = 4P` is a constant, and the
  information floor is ~`2P` to confirm a period. The slack is ~2× and is *not* learning.
- **Nothing compounds across work items yet.** That is round 22's finding, still open: the concept
  library receives zero concepts because the bridge admits only single-`return` bodies. With one
  parametric rule there is now something *worth* compressing, which was not true before — but the
  bridge fix is not in this round.
- `truth.achieved` false. `authority: NONE`. $0. No sentience claim. No external models, no neural
  weights, no dynamic code execution in result-bearing modules.

## 6. Receipts

```
canonical/tests/test_the_grammar_can_find_what_no_writer_knew_v1.py   9 passed
round-20 protections (assertions preserved, one reporter-key mismatch fixed)  18 passed
regression set (11 suites)                                          173 passed, 25 subtests
```

Every behavioural claim above comes from `synthesize_or_disambiguate_skill` with `growth_enabled=False`,
or from `sovereign_perform` on a booted `Creature`. None of it comes from calling the writer.
