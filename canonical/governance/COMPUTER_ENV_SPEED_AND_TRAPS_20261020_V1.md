# computer_env: where the time went, and the traps

Branch `arena/e1e96d1c-brain`. Everything below was measured on this
machine. Rebuilt after a re-clone destroyed four commits and the `/tmp`
backup — **record findings in the repo, not in `/tmp`.**

## 1. Headline numbers

```
cold, "how many unique lines"   355s -> 19.4s    (answer correct: 7)
full suite, cold                631s -> 108s
warm                            0.01s
```

Each step, measured rather than guessed:

```
441s  original
385s  fail-fast on the first probe + per-program budget + counter memory
355s  probe fix   <- also corrected a WRONG answer (14 where 7 was true)
277s  behavioural dedupe of pipeline tails
132s  race: composition alongside the first sweep
 69s  rank candidates by meaning, not by how often they mention the words
 50s  cap the per-head budget inside the pipeline search
 19s  try each program's flags in the order the goal scores them
```

Suite, cold: 631s -> 249s -> 184s -> 158s -> 108s.  Warm: 0.01s.  81 tests.

From the original: **22.7x cold, 5.8x on the suite.**

## 1b. Two numbers that did NOT move, and why that mattered

Not everything measured is an improvement. Two changes were built,
measured, and thrown away; both are recorded here so they are not
rebuilt.

**IDF weighting (rejected).** Generic words flood the ranking: "line"
selects `grep diff objdump nm pr lto-dump`, "unique" selects `busctl`
and the ImageMagick `convert` alongside `sort`. Weighting each word by
how rare it is across the machine's manuals moved `sort` from 60th to
**28th** — and the end-to-end question got no faster at all
(69.2s -> 68.5s), because **rank was not the bottleneck.**

Worse, it moved `wc` *backwards* on the ordinary counting questions
(`lines` 16->19, `words` 3->5, `bytes` 34->51) and the full suite went
**184s -> 346s**. One benchmark question does not outweigh 79.

*Lesson: measure the suite, not the single hard query.*

**But the instinct behind it was right** — it was aimed one level too
high. Ranking *programs* was not the bottleneck; ordering the *flags
inside* one program was. `--unique` is the 46th flag `sort` documents.
See §7c.

*Second lesson: when a ranking change does nothing, the thing being
ranked is probably not what is being waited on.*

**Wave-level early stop (rejected).** Stopping the pair search at the
first wave that finds a working pipeline is correct in principle — a
verified pipeline is the answer, and the remaining candidates cannot
make it more true. Measured, it earned **nothing**: 48.1s and 53.6s
without it, 50.2s with it. The reason is instructive — the winning
pipeline is found *late*, not early, so there is almost nothing left to
skip. Both changes were reverted; only the head budget was kept.

*A change that measures neutral is not a change that is free: it still
has to be tested, and it narrows what the search returns.*

## 2. Profile before you optimise

```
rank candidates      6.6s
find the counters    0.01s     (cached)
PAIR SEARCH        174.50s     <- all of it
```

The expensive thing was never where it looked expensive.

## 3. Four names for one instrument are one instrument

`grep`, `egrep`, `fgrep`, `rgrep` are four executables that count lines
identically. Composing with all four ran the same pipeline four times and
reported it as four programs agreeing.

**Merged by behaviour, not by name**: each tail gets the same bytes; those
that print the same thing are the same tail. `174.5s -> 65.8s`.

> **The inputs must disagree.** On four one-word lines `wc --lines` and
> `wc --words` both print 4. A dedupe tested on one input merged a
> line-counter into a word-counter. Same fault as the probe below.

Fewer survivors is the point: three "agreeing" programs became one,
because the three were one program.

## 4. Stop proving the negative before finding the positive

Composition was a last resort, after all three single-program sweeps
failed. For a pipeline-only question those are three guaranteed failures.

Composition now starts alongside the first sweep. A single program is
still preferred when found — fewer actions, and the cheap sweep gets
first refusal. `277.7s -> 134.5s`.

**The thread must only start when nothing is remembered.** Spawning it on
a warm question set a full composition search running behind an answer
that had already arrived: the suite went to 728s, slower than no race at
all.

## 5. A wrong verdict, reversed

I wrote that the library of every proven argv, re-tested before any
search, "changed nothing" and "has not paid for itself". Measured on
three questions. **Wrong.** Rebuilt without it: 728s. With it: 249s.

Across 76 related questions it is the largest single factor in the
system, and a three-question sample could not see it.

> **A measurement too small to show an effect is not evidence that there
> is none.**

## 6. The trap that keeps recurring

**A test that cannot tell two things apart will call them the same thing.**
It has now appeared three times:

1. the `uniquelines` probe put repeats next to their twins, which is the
   one arrangement `uniq` collapses — the machine answered 14 where 7
   was true, certified by a probe built to catch exactly that;
2. the tail dedupe tested on one input, where `wc -l` and `wc -w` agree;
3. the race test could not distinguish the composition's own candidate
   fetch from a single-program tier (`200 unexpectedly found in [200, 24]`).

Each time the fix was the same: **choose inputs that discriminate.**

## 7. Other traps worth remembering

- **One straggler sets the pace for the whole wave.** 10 programs took
  98.6s, 24 took 99.9s — `docker-entrypoint.sh` burning 69s and `node`
  69s while `grep`, a real answer, needed 20. Serial work was 510s; wall
  clock was the straggler.
- **A test that supplies the candidate list is not testing discovery.**
- **A cache consulted under the wrong key returns a confident wrong
  answer** (answered 15 where 7 was true).
- **Do not rank 200 candidates to use the top 100.**
- `rm -f /tmp/brain_query_probe_v1.json` before every cold measurement.

## 7b. The order of a program's flags decides what a deadline can reach

`sort` documents 52 flags and `--unique` is the **46th** of them, in the
order whoever wrote the manual chose to list them. That order has
nothing to do with what was asked.

The pipeline search gives each candidate head a wall-clock budget. In
the manual's order, a head spent its entire budget trying 45 flags that
cannot possibly answer "how many unique lines", and never reached the
one that does. Measured:

```
budget  2.0s  -> 'sort' NOT FOUND
budget  4.0s  -> 'sort' NOT FOUND
budget  8.0s  -> found, 34.8s
budget 20.0s  -> found, 51.8s
```

So the budget had to be 12s — and **every dead head paid all twelve
seconds**, because a head that cannot count burns its whole budget
before it is known to be dead. With a hundred of them, that budget *is*
the search.

The signal that ranks **programs** for a goal also ranks their
**flags**: `flags_for_goal('sort', 'how many unique lines')` returns
`['--debug', '--unique', ...]`. Offering the wide flag list in that
order is a reordering, not a filter — every flag is still tried, only
sooner or later. `--unique` moves from shape 92 to shape 2.

That inverts the budget. The winner is reached in two shapes instead of
ninety-two, so the clock only has to be long enough for the heads that
will never work:

```
 1.0s 14.4s | 1.5s 14.4s | 2.0s 12.6s | 2.5s 14.4s | 3.0s 16.3s
 4.0s 19.6s | 8.0s 28.8s | 12.0s 41.3s
```

The pipeline search: **39.3s -> 12.6s**. End to end: **50.2s -> 19.4s**.

Two seconds is the peak *and* the floor. Below it nothing is bought:
the deadline is only checked **between** shapes, so a head already
inside a subprocess run finishes it either way. This is why the budget
cannot simply be cut — it has to be cut *and* the work reordered, and
the reordering is what makes the cut survivable.

`_PIPE_HEAD_BUDGET = 2.0`. The head records the budget it was actually
given, so a caller asking for a minute a head can be shown to get two.

Two sabotages caught: removing the reordering fails
`test_the_flag_that_answers_is_offered_before_the_45_that_cannot` with
`94 not less than 47`; removing the cap fails the budget test with
`60.0 not less than or equal to 4.0`.

## 7c. Why ranking programs did nothing and ordering flags did everything

The machine has 2 cores and the search runs 24 workers — 12x
oversubscription. That is deliberate, and it is why the wall-clock
budget behaves the way it does: a head's budget is measured in
*seconds*, not in work, so oversubscription lets a hundred dead heads
each burn their budget simultaneously instead of one after another.

It also means the algebra is unforgiving:

```
time to answer = (heads / workers) x budget
budget needed  = work the winner must reach / (cores / workers)
```

Multiply them and `workers` cancels. **No choice of worker count is
faster.** The only two things that reduce the time are fewer heads, and
less work per head before the winner is reached.

- *Fewer heads* = better ranking of programs. Tried (IDF, §1b): moved
  `sort` 60th -> 28th, changed nothing end to end, and hurt the suite.
- *Less work per head* = better ordering of flags. **3.1x.**

The second lever was the one that mattered, and it was invisible until
the budget sweep showed `sort` being lost at 4s while needing 0.22s.
*A tool that is lost at 4 seconds but needs a quarter of one is not
slow; it is looking in the wrong order.*

## 8. Still wrong

- **19s cold is not instant.** Reuse is 0.01s; a genuinely new kind of
  question still costs real discovery. No evidence → no learning.
- Latent defect: a tier that finds survivors which then disagree on the
  real file leaves `survivors` non-empty, so **composition is skipped
  entirely** (the `if not survivors:` guard).
- `awk`/`sed`-class answers unreached; filename gate.
- No path from this repo to a dollar; no host that runs when neither of
  us is typing.

## 9. Commands

```bash
python3 -m unittest canonical.tests.test_computer_env_v1      # 81 tests, ~110s cold
rm -f /tmp/brain_query_probe_v1.json /tmp/brain_known_shapes_v1.json   # before cold runs
```

Sabotage discipline that caught real bugs: reverting the probe fix fails
2 tests with `'14' != '7'`; deferring composition to the last tier fails
the race test; merging `wc -l` into `wc -w` fails `TailTests`.
