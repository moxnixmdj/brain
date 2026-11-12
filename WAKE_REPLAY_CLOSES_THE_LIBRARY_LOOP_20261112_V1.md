# WAKE REPLAY CLOSES THE LIBRARY LOOP — measured

**2026-11-12.** Round 24. Base `6469dbb` (Round 23 merged). Authority `NONE`. `truth.achieved`
stays `false`. $0 incremental spend. Zero model dependency (pure stdlib AST work).

Round 23 measured the compounding half (cold 59 → armed 35 questions on a never-seen period-12)
but left the loop open at the program layer: the wake pass (`rewrite_source_with_concepts`)
handled single-expression concepts only and **silently skipped statement-function abstractions —
the only entries the library admits by compression**. Admission without replay is an append-only
log, not a memory. This round closes that loop and measures it.

---

## 1. The prediction, written before the confirmatory run

> After periods 3, 5 and 7 are solved through the growth loop and their corpus has compressed
> into one admitted abstraction, a NEVER-seen period-12 organ — synthesized through the COLD
> path with a fresh library, so it owes the library nothing — is rewritten by the wake pass into
> a form that CALLS the admitted abstraction, preserving behaviour on held-out inputs and
> strictly reducing description length.

A cache cannot satisfy this either: the period-12 block was never met by the library; what it
contributes is the shared shape. What the measurement decides is whether the library's content
is **usable**, not merely stored.

## 2. The measurement

| | |
|---|---|
| cold period-12 organ (fresh library, no license) | `def run(x0): _block=(12 values); _n=len(_block); return _block[floor-index]` — **179 bytes** |
| after wake replay through the admitted abstraction | `def run(x0): return c_x_f20826eafd77((12 values), x0)` — **112 bytes** |
| description-length reduction | **67 bytes, 37% smaller** (computed by `description_bytes`, never asserted) |
| behaviour | preserved on **500+ held-out inputs** (−500..−1, 60, 61, 137, 500) — the probe grid inside the engine plus the test's own held-out set |
| correctness of the cold organ itself | 0 failures on the same held-out set — the replay changed cost, not correctness |

The instance's own data (its 12 block values) is still stated once — that is this instance's
irreducible content. What is no longer re-emitted per organ is the shared **structure** (the
modular-indexing machinery), which now comes from the library. That is DreamCoder's replay step,
measured in this tree.

## 3. Exploration findings (measured first, reported honestly)

The round began with the generalization question from Round 23's `next_step`. Two cheap
explorations, both negative, both now pinned by tests:

1. **Ramp bodies do not compress.** `x - floor(x/p)*p` at periods 3/7/11: the abstraction's
   definition costs more than the call sites save (`NOT_COMPRESSIVE`). The family is already
   minimal — there is nothing for a library to buy.
2. **World-model organs do not lift.** Their dict-table bodies are outside the lifter's
   plain-single-function scope (`NO_SHAPE`).

So the honest generalization answer, as of this round: **the table family is the only
compressive corpus the current writer emits.** The mechanism did not generalize for free —
which is exactly the fact a "second family" round would have needed before spending on new
family recognition. The negatives are pinned so no later session can claim generalization
without new machinery.

## 4. What was built

**`compression_gain_v1.rewrite_source_with_abstractions`** — the replay engine:
- shape-matched (the target's lifted shape must EQUAL the abstraction's, argument names included);
- **the checked artifact IS the returned artifact** — the function that lands is parsed from the
  exact string whose behaviour and bytes were just measured. The first draft built the AST
  separately with parameter-name references instead of inlined constants: it verified one program
  and returned another. That defect class (verify X, ship Y) is the same one as reporting a cost
  that omits the questions you asked, and the fix is the same: one source of truth;
- fail-closed: any probe disagreement, any exception, any non-shrinking rewrite refuses the WHOLE
  rewrite — never a partial or decorated result;
- the engine refuses multi-argument functions (the probe grid is single-argument) rather than
  pretending to verify them.

**`concept_library_v1.rewrite_source_with_concepts`** — both early-exit paths now fall through to
the abstraction replay, so a library whose real content is statement-function abstractions can be
replayed. The positive expression path is untouched (pinned by the creature suite, which passes).

**`lift_shape`** now returns `param_values_src` as a list — `call_args_src` cannot be split back
apart (a tuple parameter contains commas), and a caller reassembling arguments from a joined
string would silently corrupt any constant that is itself a tuple.

## 5. What this changes about the honest answers

- The library loop is now **compress → admit → license → replay**, all measured, all in-tree,
  all $0, all model-free. Before this round the last arrow did not exist for the only content
  the library actually admits.
- "Learn it once, get it permanently" now has a third measured leg: the learned form is not just
  recalled (instant transfer, Round 22) and not just cheaper to re-derive (Round 23) — it is
  **refactored into** future programs automatically (this round).
- Still true, unchanged: one family; cross-kind compounding remains the pinned negative;
  `truth.achieved` is false; no family flipped; no capability class claimed. The replay is a
  reliability/efficiency gain on the existing crystallization capability.

## 6. Honest limits

- The replay rewrites organs whose shape the lifter can see. Organs with dict tables, multiple
  functions, or multi-argument signatures are out of scope and refused (measured refusals, not
  silent skips).
- The 37% byte reduction is measured on this corpus; corpora of already-minimal programs (ramps)
  legitimately do not replay, and the engine refuses them rather than decorating.
- One machine, producer-run, disposable state. The forged-entry guard was tested against a
  deliberately wrong abstraction (off-by-one modulus), which the probe grid caught — one
  adversarial case, not a proof.
- The expression-concept wake path was not modified, but the dispatch change adds a fallback in
  two `return None` paths; the full creature suite passes.

## 7. Next round this points at

1. **Replay inside crystallization**: the growth path should prefer emitting
   `abstraction(this_instance's_data)` when a licensed abstraction covers the family — turning
   the replay from a post-pass into the writer itself (bytes on every future organ, not just
   replayed ones).
2. **A lifter for dict-table bodies** (world models): the second-family question, revisited with
   machinery that can see the corpus the first exploration could not.
3. **Admitted abstractions as search primitives in the synthesizer grammar** (`callable_map`
   already renders them callable) — the remaining open arrow from Round 23's note.
