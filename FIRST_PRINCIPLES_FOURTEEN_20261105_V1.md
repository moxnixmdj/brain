# First principles, pass fourteen — S9: one shape, and the pipe that was cutting the evidence

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. What S9 asked and what it got

S9: build a `SIGNATURE` producer and see whether it beats the current total of *zero candidates*.
Result, creature against creature on three arity worlds:

| world | BEFORE | AFTER |
|---|---|---|
| `extra_arg` (call passes one too many) | unchanged | **REPAIRED** |
| `surplus` (call passes one too many, defaulted) | **REPAIRED** | REPAIRED |
| `missing_arg` (call passes one too few, nothing in scope) | unchanged | unchanged |

**The gain is exactly one shape.** One of the three "after" repairs was already happening before the
producer existed, so counting it would have doubled the result. Two directions are produced — default
the absent parameter at the definition, or drop the surplus argument at the call site — and both are
screened by execution like every other candidate.

## 2. The bigger finding: the evidence was being cut in half

Chasing why other worlds declined turned up a defect upstream of every producer, and it explains a
family of earlier failures rather than a single one.

`_run_py_test_file` returned the **last 600 characters** of a failing run. pytest prints the true
message in the traceback:

    E   TypeError: total() takes 1 positional argument but 2 were given

and then a **truncated** copy in its short summary:

    FAILED tests/test_m.py::test_owed - TypeError: total() takes 1 positional arg...

A 600-character tail keeps the truncated one and drops the true one. So `arity_mismatch` — and the
binding producer, and anything else reading failure text — was matching against a message that had
been physically severed. **The producers were not blind. They were being shown half a sentence and
correctly declining.**

The fix lifts the exception lines out wherever they sit, ahead of the tail, at 2400 characters. That
is one pass over text already in memory, no new I/O.

This is the third pass in a row where the defect was in the *channel*, not the *reasoning*: pass
twelve found candidates failing with no reason at all, and this one found the reason arriving
amputated. There is a pattern worth naming — **this system's bottleneck has been what it can hear,
not what it can think** — and it took three passes because each time I looked at the producer.

## 3. Two declines that are correct, and why they matter more than the win

- **Unknown arity.** `missing N required positional argument` says how many are absent but not how
  many the definition takes. `takes` is carried as `-1`, never guessed as `0`. With `0`, the
  surplus branch computes `given - 0` and strips *every* argument at the call site — a
  plausible-looking edit that inverts the actual defect. I found this by running it: the tool
  produced `add()` for a call that was one argument *short*.
- **No value in scope.** `add(a, b)` called as `add(a)` from `f(a)` stays unrepaired, because `b` has
  no source in `f`'s parameters. The branch that could fill it (c) is written, fires, and declines.
  Filling it with a literal would produce a passing test and a wrong program.

A producer that declines for the right reason is worth more than one that repairs for the wrong one,
because the second kind passes the gate and pollutes everything downstream.

## 4. A measurement lesson I had to learn three times in one pass

Three separate A/B results in this pass were **wrong before they were right**, all three my harness:

1. `TemporaryDirectory` deleted the workspace before the file was read, so every world compared
   equal to itself and reported "unchanged".
2. `from pkg.m import {fn}` with `fn = "f(3)"` produced `import f(3)` — a `SyntaxError` world, so
   every signature candidate declined and I briefly believed the producer was broken.
3. Reading output through a context manager, then re-reading after `rmtree`.

Each was caught only by re-running the same code a second way and refusing to accept a result that
contradicted the other. **A harness is a measuring instrument, and an uncalibrated instrument gives
numbers indistinguishable from findings.** The discipline that actually worked was: never accept a
result that surprises you until a second, structurally different script agrees.

## 5. Scoreboard

| kind | pass 13 | pass 14 |
|---|---|---|
| VALUE | 7/8 | 7/8 |
| TERMINATION | 1/1 | 1/1 |
| BINDING | 1/1 | 1/1 |
| **SIGNATURE** | **0/1** | **1/1** (one shape, two declines) |
| SYNTAX | 0/1 | **0/1** |

One hole left, and it is the hardest: `SYNTAX` — a file that does not parse, where no behavioural
screen is available until it does, so the oracle that has verified every repair in this project
cannot run at all.

## 6. Next falsifier

**S10.** Build a `SYNTAX` producer with no executable oracle: parse-error-guided repair (insert the
missing `:`/bracket, close the unterminated string), verified by **`ast.parse` succeeding and the
owed test then passing** — i.e. the candidate must clear both, and a candidate that merely parses is
not a repair. Measure on five syntax worlds against today's zero. The interesting failure mode to
watch for is reporting a parse-only fix as a repair, which is exactly the kind of widening this
project's laws forbid.

## 7. Standing bar

Different at the end than the start: one more class of broken world repairs itself, and — more
consequentially — every producer in the system now receives the failure message intact instead of
truncated. That second change was not the thing I set out to build. It was found by insisting that a
decline explain itself.
