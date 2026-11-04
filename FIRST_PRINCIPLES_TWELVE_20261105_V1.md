# First principles, pass twelve — the creature was deaf, and hearing did not make it smart

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. What eleven passes got wrong about themselves

Pass nine concluded: *"the failure-reason channel is abandoned — the text exists in the child's sink
but there is no verified surface to read it."* That was wrong, and it was wrong in the exact way
this project has been wrong eleven times: I diagnosed a **producer** and never measured the **path**.

The surface was there. The child formats the unittest traceback into its own sink — it has always
known why a candidate failed — and then exits with a bare integer. The daemon turns that integer into
`TEST_FAILED`. So a wrong answer, a `TypeError`, an infinite loop and a zero-assertion test all arrive
identical. Measured on one world:

    candidate 0 ('return a - b') -> TEST_FAILED
    candidate 1 ('return a / b') -> TEST_FAILED
    candidate 2 ('return a + b') -> TEST_FAILED

Three different worlds of wrong, three identical rows. **The creature was not missing a memory. It
was missing its senses.**

## 2. The fix, and why it costs less than doing nothing

Candidates now speak over the pipe they already owned (`r_eof`/`w_eof`), so no new syscall and no new
privilege:

    SEEN [{"at": "f(7, 2) == 9", "seen": ["14",  "9"]}]   <- what the wrong code returned
    SEEN [{"at": "f(7, 2) == 9", "seen": ["5",   "9"]}]
    SEEN [{"at": "f(7, 2) == 9", "seen": ["3.5", "9"]}]

The assert is *wrapped*, not replaced, so the test expression and the verdict are untouched and the
re-raise preserves the traceback; operands are evaluated only on failure, so a passing candidate pays
nothing for being observed.

Getting the cost to zero took four of my own mistakes, each caught by measurement rather than review:

| attempt | result |
|---|---|
| probes on every candidate | +18% per candidate |
| right idea, cache keyed on staged path | no change — the path is new every batch |
| cache across candidates | **impossible** — every candidate is a fork; a write in a fork never returns |
| build the test's code object in the PARENT before fork | **−11%** per candidate (2.16 ms vs 2.40 ms) |

So observation is not a tax. The screen is now *faster* than the code it replaced, because the parent
compiles the test once instead of every child rebuilding an identical code object.

One more of my own bugs, caught by the gate rather than by me: an instrumentation predicate keyed on
`assert` statements alone skipped the counter for unittest-style tests, and the correct candidate was
reported as having executed zero assertions. The predicate must agree exactly with what the counter
rewards. Fixed; 19-failure gate back to parity.

## 3. Does hearing make it smart? No. Measured, and it does not.

This is the part worth the pass. Having given it senses, I tested whether the reason reduces search,
by ranking candidates with `|returned − expected|` — the obvious, cheap, plausible heuristic. On six
board shapes with the operator-family generator:

| shape | candidates | blind order | reason-ranked order | verdict |
|---|---|---|---|---|
| binop | 5 | 0 | 4 | **worse by 4** |
| cmp_gte | 5 | 0 | 0 | same |
| mul | 5 | 1 | 4 | **worse by 3** |
| mod | 5 | 4 | 4 | same |
| augassign | 5 | 0 | 4 | **worse by 4** |
| whileacc | 15 | 0 | 13 | **worse by 13** |

**Worse in four of six, often far worse.** The reason is not subtle: the true fix is usually the
*first* perturbation from the original (one operator changed), while proximity-sorting prefers
candidates that returned values close to the expected one — an accidental near-miss. Numeric distance
in output space is not structural distance in program space, and treating it as if it were is exactly
the sort of plausible shortcut that has been quietly wrong in this project before.

So the honest statement of pass twelve is:

> The creature can now see what it did wrong. It does not yet know what that means, and the first
> obvious way to use the sight made it worse.

That is a smaller claim than "intelligence", and it is the true one. It does not make the pass
worthless: an agent that cannot distinguish a hang from a wrong answer from a crash cannot learn
anything, and now it can, at negative cost. But senses are not judgement, and the measurement says so
in a table.

## 4. What a real use would have to look like

If proximity is wrong, what is right? The reason carries the **shape** of the failure, not just a
value: `AssertionError: 8 != 7` after `add(4, 3)` is a value wrong by 1; a `TypeError` is a signature
error, not a value error; `WALLCLOCK_EXCEEDED` is a termination error; `NameError: x` is a binding
error. Those four classes demand mutually exclusive next actions, and *that* distinction is what the
channel now makes available. Nothing in the system currently consumes it.

**S8, stated so it can fail.** Classify each failure by kind (value / binding / signature /
termination), and let the class select the producer family rather than all of them racing: value
errors get operator and constant edits, binding errors get guard/definition synthesis, termination
errors get loop-bound edits. Measure probes-to-fix on the twelve-shape screen against today's
race-everything order. If class-routing does not beat blind ordering, the diagnosis was wrong and the
channel stays a reporting feature — which is still worth its negative cost, but must never be
described as intelligence.

## 5. Standing bar

Different at the end than at the start: the screen itself is different, its costs are lower, and it
now reports what it observed instead of an integer. That is a change in the creature's **senses**, not
its **mind**. Pass eleven found the abstraction step; pass twelve found that having a fact available
and being able to use it are different problems, and that I had been silently assuming the first
implies the second.
