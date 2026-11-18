# One demonstration reaches 45.8% of a machine, and the missing 54.2% is not an experience problem

Round 18. Branch `arena/d5aa8d71-brain`, from `5c94fed6`.

## The claim in the prompt, stated so it can be killed

> Instant learning and instant learning in new environments are solved, therefore giving the model the most
> advanced action once — in any coding environment, or on any part of a computer — is a complete solution.

The first clause is true and the tree already measured it. The inference is false, and this round measured the
last unfixed step of the inference rather than arguing about it.

## What is real

**One demonstration does transfer.** `canonical/verification/ONE_DEMONSTRATION_REACH_20261116_V1.json` asks the
tree's own code — 5,513 files, 139,438 name sites — how much of a real machine a single stored demonstration
reaches:

| | |
|---|---|
| sites sampled | **600** |
| reached by the stored demonstration | **275 (45.8%)** |
| site classes it declines | **12** |
| sites damaged | **0** |

So the mechanism is real, permanent, and safe: 45.8% of eligible sites, zero damage. That is exactly what
"learned once, applies forever" buys. It is not 100%, and the 12 declined classes are not accidents of this
implementation — they are sites whose premise the demonstration did not satisfy.

**A single trace does not identify the action.** `ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_MEASURE_20261116_V1`
asked 99 real bugs, measured 51: 43 behaviours were left unseparated by *every* probe available, 8 were split by
a probe, 8 settled by asking one question. When the survivors disagree, one more repetition does not shrink the
set — the tree's own `finite_identifiability` and `epistemic_closure_kernel_v1` compute that, they do not assume it.

**Verification is where the learning signal comes from, and it is bounded by reach.** Rounds 15–17 measured it:
71.4% of the behavioural parts of real fixes are already pinned by the human's suite (round 15), 0 of 8 remaining
parts are recoverable from the tests' own inputs (round 16), and 2 of 8 are reachable by generated inputs (round
17). Round 18 asked what the *strongest model-free mechanism in the field* adds.

## What this round built, and what it measured

Round 17's four failures all compare against structure, not quantity, so mutation has no gradient. The field's
answer is **input-to-state correspondence** (REDQUEEN, NDSS'19; CmpLog in AFL++; Fuzzy-SAT): log the operand
pairs at comparisons the run actually evaluates, and the operand the input does not determine is the value the
check wants. Halo (Oakland'24) turns that into a filter and reaches 43% reachable-input generation against
AFLGo's 5.3%, with no symbolic execution. IDFuzz (USENIX'25) goes further only by training a neural model over
past inputs — the dependency this project refuses.

`canonical/swe_kernel/what_the_condition_wants_v1.py` implements that mechanism at full strength and no further:

    log        every single-operator comparison in the ENCLOSING SCOPE, each side evaluated once
    log        every CALL in boolean position, with its arguments and result (CmpLog hooks strcmp; this hooks
               isinstance, which is the packaging failure's actual gate)
    harvest    the pairs that belong to the comparison that returned FALSE closest to the target
    wanted     the operand the seed does not appear in, at 3-character colouring
    deliver    substituted INTO the seed at the position it occupies -- not swapped for the whole input
    walk       the reached input becomes the next round's seed; progress is DISTANCE to the target, ten rounds
    decide     the same rule as round 17: an assertion only if green on the fix and red on the revert

It is composed with round 17's mutation engine, never reported as its replacement.

## The result, and the four bugs that had to die first

8 unpinned behavioural parts, 17 real fixes, 75 operand pairs logged, and:

| | |
|---|---|
| pinned by mutation (round 17's engine) | **2** |
| pinned by the operand channel | **0** |
| closest the walk came | **9 lines from the target** |
| parts refused because no gate fires on the seed's path | 4 |
| parts with no literal call in the test / part removes code | 2 |

**Certified share unchanged: 0.762.** The channel fires — on real tomli code it passed two gates and reached a
changed line in 26 executions, and on a fixture a call gate re-rolled from a string to a mapping and pinned — and
on the parts that need it, it buys nothing.

Four defects in my own instrument were found and fixed **before** the zero was believed, and each had produced a
plausible false report:

1. **Instrumented only the changed block**, whose comparisons never execute until the block is reached ⇒ 3
   rewritten comparisons, 0 operand pairs. The gates are in the enclosing scope.
2. **Took the deepest logged comparison instead of the one that returned False.** A comparison that succeeded is
   not what stopped the run.
3. **Treated a larger line number as progress.** This file's main parse loop sits at line 733 while the changed
   function is at 109, so the walk was walking *away*; progress is distance to the target.
4. **Compared instrumented line numbers against original ones.** The traced child reports lines of the file it
   imported, so the target never "matched" even when the walk had passed it. The offset is now measured, not
   assumed, and a test pins it.

## Why zero, stated as a mechanism rather than an excuse

A parser does not fail on a magic value; it fails on a **sequence** of structural constraints. Passing one gate
buys one line. Ten rounds of substitution over four shapes cannot assemble a valid TOML document, and the
measurement agrees: 27 operands were logged for the part where the walk got to within 9 lines, and it still could
not cross. The field's own trajectory says the same thing — IDFuzz's advantage comes from a *learned* model of
which input fields matter; Cottontail's from a model solving the structured constraint. Both are inference over
semantics, which this project will not borrow.

So the answer to the prompt is: **wrong as stated, right in what it has already bought.** One demonstration
permanently buys 45.8% of a machine, with zero damage, and that is the strongest single-cheapest gain in this
whole chain. It does not buy the remaining 54.2%, because what is missing there is not an experience of the
action but a *consequence*: which input reaches which line, which assertion separates two behaviours, which
premise a site requires. Three consecutive rounds have now priced the three possible sources of that consequence
— the tests (0 of 8), generated inputs (2 of 8), and the program's own comparisons (0 additional) — and the
residue is reachability reasoning over structure.

## What this does not claim

It does not claim the operand channel is useless: it fires, it is cheap, it is composed, and it is the right
instrument for magic values and type gates. It does not claim the corpus is large: 8 parts of 17 fixes. It does
not claim the certified share moved: it did not. Model calls 0, network calls 0, spend $0; the two pins remain
round 17's, independently reproduced with plain `pytest` in freshly built trees (fixed 2 passed, defective 2
failed).

## What is next, and why it is the only remaining move

The wall is a *format*: the sequence of constraints that makes an input acceptable. The tree already owns the
right object for that under a non-obvious name — `derive`-style structural induction over the artifact's own
literals, and `vocabulary_induction_v1`'s rule that vocabulary is recovered from evidence that FITS and reported
as NO_EVIDENCE otherwise. The next organ is not another fuzzer: it is a **format hypothesis induced from the
parser's own comparisons** — the set of tokens and orderings the program has been observed to demand — used to
generate one document that satisfies the sequence, then verified by the same green-on-fix/red-on-revert rule. If
that fails too, the honest conclusion is that reachability over structure requires a model of the domain, and the
domain's own artifact is where it has to come from.
