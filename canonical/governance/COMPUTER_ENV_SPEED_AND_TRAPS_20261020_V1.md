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

### What it costs now, per question (cold, same machine, 2 cores)

```
count the lines in data.txt         2.63s   15   one program
how many words in data.txt          3.75s   30   one program
how many unique lines in data.txt  19.20s    7   no single program can
```

The first question asked pays 6.6s once to read every manual on the
machine; after that it is cached on disk. So a question one program can
answer costs about 3s, and a question that needs a program the machine
has never composed before costs about 13s of search plus that one-off
discovery. Warm — the same question again, or one it has generalised to
— is 0.01s.

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
- **The machine litters.** Five zero-byte files named `gz1702314`,
  `gz1830081`, `gz2118275`, `gz2432223`, `gz2483866` appeared in the
  repository root during a measurement run. Not reproduced since: not
  from `programs_for_goal` (ran it in an empty directory, nothing
  left), not from the gzip tests (same). The one place that runs
  programs in the caller's directory rather than a scratch one is
  `help_text`, which passes `os.getcwd()` when it asks for `--help` —
  the likely culprit, but **unproven**, so it was not "fixed" on a
  guess and no test was written, because a test that cannot fail when
  the bug is present is worse than no test. Reproduce first.
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

## 9. The questions the machine refuses without looking

`_PROBE_KINDS` is a hand-written table of six question kinds. "how many
unique words" is not in it, so the machine answered it with nothing
instantly, having never looked at a single program -- not a wrong
answer, not a slow one, just absence. Measured:

```
count the lines in data.txt         1.8s   15
how many words in data.txt          3.8s   30
how many unique lines in data.txt  19.4s    7
how many unique words in data.txt   0.00s  None   <- refused, instantly
```

The table is two axes written out by hand: what a file is measured IN
(`lines`, `words`, `bytes`, `characters`) crossed with what is asked
ABOUT it (plain count, `unique`, `with`). "unique words" is
`words x unique` -- a cell nobody typed.

**Built, measured, and reverted.** Crossing the axes generates ten kinds
instead of six, and turns the refusal into an attempt. The attempt then
cost **190-286 seconds and still failed**. That is worse than refusing,
so it was reverted and is recorded here instead.

### What survived the revert

**Breadth and depth are the same budget.** The machine has 2 cores and
every head fights for them, so what a search costs is

```
wall clock ~= (number of heads x CPU depth reached) / cores
```

One hundred heads each reaching 0.17 CPU-seconds and two dozen each
reaching 1.3 cost about the same. The proof is the same question asked
two ways: "how many words contain ERROR" -- answerable only by
`grep --only-matching` -- was **found in 2s with five candidates and not
found at all with a hundred**, at any budget. It was never a budget
problem.

**A 2s head budget only finds flags the GOAL names.** Those are tried
first (`sort --unique` is shape 2, not the 46th), so 2s reaches them. It
does not reach a flag the goal does not name: `grep --only-matching` is
about twenty shapes deep, and a shallow search walks straight past the
only program that answers.

**Searching shallow-then-deep fixes the isolated search.** Rounds of
`(100 heads, 2s)` then `(24 heads, 16s)` -- shallow across many, deep
across few -- finds `grep --only-matching ERROR | egrep -c` with a full
hundred candidates, in **27.9s**. That is the shape of the fix.

### What is still wrong, and is the next thing to attack

The full `answer_query` path still refuses it, and costs **225s** where
the isolated pair search costs 28s. An 8x gap between the search and the
path that calls it is not a tuning problem, and it is the thing to find
next: fix that and the crossed axes can be switched on.

`uniquewords` needs three stages (`tr | sort -u | wc -l`) and the
machine composes two, so it will stay unanswered until composition is
recursive.
