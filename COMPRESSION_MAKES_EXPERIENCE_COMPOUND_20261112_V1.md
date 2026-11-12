# COMPRESSION MAKES EXPERIENCE COMPOUND — measured

**2026-11-12.** Round 23. Base `6bff8c7` (main). Authority `NONE`. `truth.achieved` stays `false`.
$0 incremental spend. Zero model dependency in every result-bearing path (pure stdlib AST work).

This round took the one move the round-22 document ranked first: make the abstraction bridge
admit real programs, admit abstractions only by computed compression gain, and then re-run the
measurement that had been failing — with a prediction a cache cannot satisfy.

---

## 1. The prediction, written before the measurement

> After periods 3, 5 and 7 have been solved through the growth loop and their corpus has
> compressed into one abstraction, a **never-seen period-12** structure must cost **strictly
> fewer** oracle questions than it costs cold. A cache cannot pass this: nothing about period 12
> was ever stored. What transfers is the family abstraction.

Pre-registered in conversation before the first armed run, and pinned as
`test_a_never_seen_period_12_costs_fewer_questions_with_the_library_than_cold`.

## 2. The measurement

| arm | questions | evidence collected | held-out failures (57 probes) |
|---|---|---|---|
| cold period-12 (fresh, empty library) | **59** | 48 | 0 |
| library-armed period-12 (abstraction from solved 3/5/7) | **35** | 24 | 0 |

**Armed is strictly cheaper: 59 → 35, 41% fewer oracle questions, half the evidence.** Both organs
verified correct on 57 held-out inputs (negative x, far positive x) that neither run ever asked.

Instrument calibration — the build arm reproduces the round-22 cold numbers **exactly**:

| structure | round-22 doc | this round |
|---|---|---|
| period-3 cold | 14 questions | 14 |
| period-5 cold | 24 questions | 24 |
| period-7 cold | 34 questions | 34 |

Same instrument, same numbers, so the comparison above is against the same ruler that measured
"five environments taught nothing." Pinned by `test_the_build_arm_reproduces_the_historical_cold_costs`.

## 3. What was built

**`canonical/swe_kernel/compression_gain_v1.py`** — the compression layer, on the same load-bearing
idea as DreamCoder/Stitch/LILO: compress the corpus of solved programs into shared abstractions;
admit an abstraction ONLY when rewriting strictly reduces description length; let admitted
abstractions change what future evidence must pay.

- **Shape lifting**: scalar constants become parameters; a tuple of constants becomes ONE block
  parameter (this is what makes period-3 and period-7 the same shape — the block, not its
  elements, is the parameter; signed literals count as literals because `-2.0` parses as
  `USub(Constant)` and the sign is printing, not structure).
- **Admission is measured, three ways**: ≥ 2 real sites; strictly positive gain in description
  length (`description_bytes` — canonical uncompressed AST text); every rewritten site reproduces
  its original program's outputs on a probe grid. Anything else is refused WITH ITS REASON —
  a refusal that cannot say why cannot be learned from.
- **The currency is uncompressed AST text, and the docstring says why**: zlib (`executable_ast_bytes`)
  re-derives shared structure for free, so a corpus measured under zlib is already the corpus
  after the abstraction did its work — a currency in which the mechanism being admitted can never
  measure a gain is not a measurement, it is a veto. Pinned by `test_gain_is_computed_from_description_length_not_asserted`.

**The bridge** (`_skill_organ_to_concept_entry`) — round 22's two defects, fixed and pinned:
- multi-statement bodies (the induced period tables: `Assign, Assign, Return`) now bridge as
  statement-function entries — round 22 measured this exact shape silently rejected;
- `mdl_gain_bytes` and `corpus_sites` are **computed** from compressing the organ against the
  library's memory of solved programs. The old `max(1, code_bytes)` / `corpus_sites=1` numbers were
  fabrication. A singleton now carries gain **0** — and `from_dict` no longer upgrades a stored 0
  back to 1 on reload (`or 1` was quietly re-fabricating the number every load).

**The corpus is the library**: compression runs over the renderings of `G_t`'s stored programs plus
the incoming organ. `G_t` is the accumulator that survives fresh graphs; counting graph-local copies
on top of their own stored entries would fabricate sites. Admitted abstractions stay out of the
corpus they are re-admitted over.

**The licensed evidence policy** (`licensed_table_policy` + the growth loop): a policy exists only
when the library holds an abstraction that is family-`periodic_table` (recognised from the
structure — modular indexing in the subscript — never from a name), sites ≥ 2, gain > 0, verified
hits ≥ 1. It licenses ONE thing: the evidence requirement for a new family member is **two cycles**
instead of the cold **four**. The acquire-time verification at 2p and 3p is not waived; the policy
moves where evidence is collected, never whether it is verified.

## 4. Where the mechanism actually bites (the defect the first draft missed)

The first draft put the licensed early-stop in the collection loop. The trace showed both arms
exit that loop at 15 points — the one-time budget escalation caps it at 12 questions — and the
**top-up block** after it is where the evidence bill is really sized. The licensed factor now
sizes THAT requirement. Without this, the armed run re-collected to four cycles and measured
59 = 59: the failure mode of wiring a prior into a place the budget never reaches. Recorded
because "the prior must be wired where the money is spent" is a reusable lesson.

## 5. What this changes about the honest answers

- Round 22's `concepts now=0` after three structures — the deepest measured defect — is now
  **concepts=1, sites=3, gain=67 bytes, family recognised from structure**. The library accumulates.
- "Nothing transfers across kinds" was true **for the instruments that existed**. It is now
  conditional: transfer across instances of a family **measures at 41% cost reduction**, through a
  mechanism that is not a cache (the instance was never met; the abstraction was).
- The honest claim has narrow quantifiers: ONE family (periodic-table lookup, structurally
  recognised), ONE corpus kind (template-emitted table organs), ONE licensed relaxation (4→2
  cycles). Nothing here claims cross-family transfer, GUI transfer, or weight-level learning.

## 6. Explicitly not claimed / honest limits

- `truth.achieved` stays false. No capability family flipped. This is a
  reliability/efficiency gain on an existing capability (cheaper induction, same correctness),
  verified on held-out probes by the world's answers, not a new capability class.
- Two sites on this corpus do NOT compress (measured −13 bytes): the abstraction pays for itself
  from the third site. That is a property of the currency, not a knob.
- The disambiguation front door sometimes crystallises an equivalent program in a different shape
  (measured: period-3 as an inline-tuple expression, at 2 questions). Shape lifting cannot unify
  those forms; the build arm therefore uses the growth loop, which emits table organs. Stated in
  the test, not hidden.
- One machine, producer-run, no independent verifier, disposable state.
- The 2-cycle policy is licensed by a measured prior and still verified at 2p/3p + held-out; its
  residual risk (a non-periodic function agreeing on two cycles) is priced by the prior and was
  not observed in 57 held-out probes. A counterexample would falsify the policy, not the law.

## 7. The next round this points at

1. **A second family.** The licensing rule is family-generic; only `periodic_table` is
   structurally recognised. One more family (e.g. affine-with-parameter blocks) would test whether
   the MECHANISM generalises or the round was a one-family trick.
2. **Wire admitted abstractions into the synthesizer's grammar** (`callable_map` already renders
   them callable): the abstraction should be a search primitive, not only an evidence-policy
   license.
3. **Cross-kind compounding, again, with the real mechanism** — the P4 prediction from round 22
   (period-12 after 3/5/7) is now PASSED; the same cache-proof discipline applied to the
   learning-to-learn benchmark is the remaining measured negative.
