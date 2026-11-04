# First principles, pass nineteen — why one authored table per failure class was the wrong shape

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

You asked whether this is the smartest approach, from first principles. It was not, and the thing I was
proudest of was the clearest example of the problem.

## 1. The fault in what I built

Nineteen passes produced four authored tables and one learning mechanism. The tables were the flaw you
named: one hand-written rule list per failure class, me deciding in advance which rewrites exist. But
`learned_edit_habits_v1`, the mechanism I presented as the answer, **inherited the same fault in a
subtler place**:

| property of a habit edge | consequence |
|---|---|
| it stores `(old_token, new_token)` | it records *what worked*, never *why* |
| it needs a prior success | a cold creature learns nothing |
| one example teaches one edit | closure needs a chain of two to infer anything |
| it applies only to a token already seen | it cannot generalise to a new symbol |
| it has no semantics | it proposed an edit that passed by accident (`9 // 2 == 4`), and only the generalisation gate stopped it |

A habit is a lookup table that fills itself in. That is better than a table I fill in, but it is the
same shape, and it has exactly the same blind spot: **it cannot reason about a failure it has not
already survived once.**

## 2. The deeper layer: what the creature already receives

The screen already reports, for every failing assertion, what it saw:

    E   assert 5 == 3.5
    E    +  where 5 = f(7, 2)

Arguments `(7, 2)`, produced `5`, owed `3.5`. That is a **measurement**, and a measurement can be
*explained*: there exists a function of those arguments that yields the owed value. So the creature no
longer stores edits. It stores interpretations, and it derives the edit from the explanation:

    which operator in the language turns (7, 2) into 3.5?  ->  `/`  ->  rewrite the line to `a / b`

Nothing in that inference is authored. The operator vocabulary is enumerated reflectively from Python's
own `operator` module; I never wrote a list of rewrites. The one human input is a *lexicon* saying what
`+` is called (`add`), which asserts no rewrite and cannot make a wrong one.

Three consequences, each removing one row of that table:

- **Cold start.** No prior success needed. This is the first producer in the series that works on a
  creature that has never repaired anything.
- **Cross-token generalisation.** The hypothesis is about an operator, and operators mean the same
  thing wherever they are written.
- **Constants are impossible.** A constant is not a function of the arguments, so it is never a
  hypothesis. The accident that the generalisation gate caught in pass eighteen is now excluded
  *upstream* of the gate.

## 3. Measured

One world per process. Every authored producer silenced, habits empty, no stored data. The silencer
was itself wrong before today (see §4).

| world | interpretive ON | OFF (control) |
|---|---|---|
| `a - b` -> `a / b` | SOLVED | FAILED |
| `a - b` -> `a * b` | SOLVED | FAILED |
| `a + b` -> `a ** b` | SOLVED | FAILED |
| `a * b` -> `a - b` | SOLVED | FAILED |
| `a % b` -> `a // b` | SOLVED | FAILED |
| `a < b` -> `a >= b` (predicate) | SOLVED | FAILED |
| `a + a` -> `a + b` (operand) | SOLVED | FAILED |
| string concat world | not interpretable | FAILED |
| index off-by-one | not interpretable | FAILED |
| owed value no operator produces | refused | FAILED |

**8 solved cold, 0 in control.** And across processes: taught that `-` can mean `/` on `f`, a later
process repairs `x - y` -> `x / y` on a differently named `g` from storage alone.

## 4. Two defects in the instrument, found only because the control was finally honest

The control initially matched the active column exactly. Chasing that produced two findings, both of
which change earlier conclusions:

1. **`_perturb` rejected correct repairs.** The generalisation probe added a *uniform* +7 to every
   numeric argument, so both arguments moved together and every difference-based function was invariant.
   `a - b`, `a // b` and `a % b` were reported `OUTPUT_IGNORES_INPUTS` and discarded. Offsets now vary
   by argument position and round. This gate has been silently under-counting honest repairs.
2. **A fifth authored table was never silenced.** `python_test_guided_patch_search_v1._candidate_specs`
   lives in `bound_capabilities`, not in `swe_kernel`, and ships `_BINOP_SWAPS` plus literal
   substitution. Every "all authored producers silenced" measurement before today was incomplete.

And my own silencer was wrong twice more: it patched names the loop imports *inside* the function
(no-ops), and it disabled the interpretive *factory* while leaving the instance's methods live — so the
first "control" was running the mechanism it was meant to exclude.

## 5. What is still authored, said plainly

The lexicon maps symbols to `operator` names. It contains `+ - * / // % ** << >> & | ^ < > <= >= == !=`.
It says what an operator is *called*. It cannot say what an operator should *become* — that comes from
the measurement. But it does bound the mechanism to operators Python names:

- string concatenation through `+` is interpretable in principle and failed here; the world I wrote was
  unsatisfiable (`('x', 'y')` has no binary operator yielding `'xyxy'`), so this is untested, not refuted
- indexing, slicing and attribute errors are **outside** the mechanism entirely: no argument tuple and
  no binary operator describes `a[0]` should be `a[1]`
- anything non-arithmetic that is not a comparison is out of reach

So the honest scope is: **binary operators and repeated operands, derived from measurement, with no
prior success required.** Everything outside that still falls to the authored tables, and a cold
creature facing a binding or syntax error still repairs nothing.

## 6. Why this is the right direction and not the end

The shape changed, and the shape was the problem. A table encodes *my* conclusions; a habit encodes a
*conclusion without its reason*; this encodes a *reason*, which is the only one of the three that can
be applied to a case nobody anticipated. The remaining work is the same move repeated in domains where
the measurement is not a number: an `IndexError` names the index that failed, a `KeyError` names the
key, a `NameError` names the identifier — each is a measurement with a free parameter, and each is
currently served by a hand-written rule I wrote instead.

Next falsifier: **S18.** Pick one of those (index is the cleanest), and require the creature to derive
the off-by-one from the raised index rather than from a rule, cold, with the syntax and binding tables
silenced. Prediction to falsify: the same interpreter shape will not carry over, because `a[0]` has no
argument tuple, and I will have to invent a *second* kind of explanation — at which point the question
is whether one mechanism can hold two kinds or whether I am back to one table per class wearing a
costume.
