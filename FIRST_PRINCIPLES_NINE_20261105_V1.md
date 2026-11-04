# First principles, pass nine — it learns what it can already do

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

Pass eight concluded: *budgets measured, not authored*. Taken literally, that means auditing every
authored number. This pass did that for the candidate caps, and found the caps are not the cost.
What it found instead is a sharper fact about the creature.

## 1. The candidate caps are not what costs time (measured, not argued)

| question | measurement | conclusion |
|---|---|---|
| where does the passing candidate live? | first-passing index ∈ {1,2,4,4,4}, max 4 over every solved world | the cap of **36 is 9x larger than anything ever needed** |
| what does one extra candidate cost? | 36 distinct candidates 0.066 s, 1 candidate 0.005 s → **1.8 ms marginal** | cutting 36→12 saves ~43 ms |
| does a duplicate candidate cost anything? | 36 identical candidates 0.287 s vs 36 distinct 0.066 s | re-screening the same bytes is 4x worse than 36 distinct — a dedup, not a cap, is what matters |

43 ms is the same order as the producer-order saving I measured and discarded in pass eight. Both
are real, both are small, and neither is where a repair spends its second.

## 2. The bootstrap is closed, and this is the important finding

A creature can only crystallize from a **success**. It succeeds on what the inline synthesizers
already solve. Those lessons are then worthless (inline solves them anyway). The shapes it cannot
solve never produce a learnable success. That loop is closed — so I tested the only two ways out.

**(a) Transfer to a nearby shape.** Teach on `return a - b`, then ask for shapes differing by one
structural element:

| target shape | cold | warm |
|---|---|---|
| same shape | fix | fix |
| + try/except wrapper | fix | fix |
| + class method | fix | fix |
| + while accumulation | fix | fix |
| + augmented assignment | **fail** | **fail** |

No transfer. Every nearby shape is solved inline anyway, so the lesson has nothing to add; the one
shape inline cannot solve does not accept the lesson.

**(b) Bootstrap without help.** Ten-shape battery, no teaching at all:

    solved inline from nothing: 6/10   (cmp, zero-guard, while, nested, try, comprehension)
    unsolved:                   4/10   (augassign, boolop, list-index)
    memory adds:                0 shapes    (because it has learned nothing)

The only positive transfer measured anywhere in this work required an **external teacher** placing
a rule before the run started (S5, augassign). Self-taught rules: inert (S6).

**Conclusion.** The creature learns what it can already do. That is not a bug in memory; it is
what a learn-from-success loop does when search is weak. Memory cannot bootstrap capability here,
because capability has to exist before there is anything to remember.

## 3. What was tried and abandoned this pass

Two real gaps named and both abandoned rather than shipped half-tested:

- **The failure reason is discarded.** Every failing candidate reports the bare string
  `TEST_FAILED`. A near miss (`assert 5 == 9`) is indistinguishable from a syntax error, and the
  zygote already collects the text in a `sink` and throws it away. I implemented a bounded
  `WHY:` channel over the existing per-candidate pipe and could not get it to emit in this
  sandbox — the child is a string-templated process whose stderr is not surfaced, so I had no
  way to see why. Reverted. The gap is real and recorded here; shipping an unverified version of
  it would have been the fourth instrument error of this session rather than a fix.
- **The self-crystallization run in this session went through `AWAKE_CONFINED_MULTIFILE_REPAIR`,
  not the daemon's own crystallize call** (0 calls to `crystallize_code_fix` in the plain path).
  Where a repair becomes a lesson is still not pinned down.

## 4. The honest state after nine passes

| claim | status |
|---|---|
| retention persists and recall hits | **true** |
| memory repairs a shape search cannot, when taught first | **true (1 of 9 shapes)** |
| the acceptance gate was discarding honest repairs (7 shapes) | **true, fixed** |
| per-candidate budget was 452x the honest median | **true, fixed (half the wall time)** |
| the creature learns without a teacher | **writes the memory, cannot spend it** |
| the creature becomes different by learning | **no** |
| transfer between shapes | **only with an external teacher** |
| bootstrap (weak search → capability) | **does not exist here** |

## 5. Therefore the next change cannot be another memory improvement

Every remaining memory idea improves a path whose value is bounded by search it cannot bootstrap.
The measured statement is: **this creature's capability ceiling is its synthesizer set, not its
memory.** So the only work that can raise the ceiling is making the synthesizers better or making
the search able to build new ones — and the second of those is exactly what "learn from a near
miss" (the discarded `WHY` channel) would enable.

That makes the `WHY` channel the highest-value open defect, and it needs a debugging surface I did
not have here: either a way to see the zygote child's stderr, or moving the child script from a
string template into an importable module so its failures are visible to a test.
