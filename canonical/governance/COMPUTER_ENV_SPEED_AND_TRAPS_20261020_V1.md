# computer_env: where the time went, and the traps

Branch `arena/e1e96d1c-brain`. Everything below was measured on this
machine. Rebuilt after a re-clone destroyed four commits and the `/tmp`
backup — **record findings in the repo, not in `/tmp`.**

## 1. Headline numbers

```
cold, "how many unique lines"   355s -> 50s      (answer correct: 7)
full suite, cold                631s -> 158s
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
```

Suite, cold: 631s -> 249s -> 184s -> 158s.  Warm: 0.01s.  80 tests.

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

## 7b. Giving up on one program is not giving up

Composition was guarded by `if not survivors`. Survivors are commands
that tracked the probe — not commands that answered. When programs
tracked the probe and then disagreed on the real file, `survivors` was
non-empty, the guard failed, and **composition was never attempted**. The
machine refused questions it could have answered by joining two programs,
and reported the refusal as though it had tried everything.

Now attempted whenever nothing produced an answer. Test:
`2 not found in [1] : composition was never attempted`.

## 7c. Read the flag's name, and stop counting matches

`sort` documents `--unique` as *"output only the first of an equal run"*
— containing neither "unique" nor "line". Scoring descriptions only,
`sort` ranked **91st of 241** for "how many unique lines" and the one
flag that answers was never offered.

A flag NAMED after what the goal asked for is the strongest signal on
the machine. Flag names now score above descriptions that merely contain
the word.

Then counting had to stop: ranking by **how many** flags matched rewards
a program for repeating the words. `cat` says "lines" in three
descriptions and outranked `sort`, which says it once and works.

```
sort   91 -> 60      uniq  31 -> 7
wc    not in 120 -> 75      cat  2 -> 13
cold  132.4s -> 69.2s
```

## 7b. The budget that was right for one sweep is wrong for the other

The pipeline search inherited `_PROGRAM_BUDGET = 20.0`. That number was
tuned for a different shape of problem: in the single-program sweep one
straggler stalls one wave of programs that all finished minutes ago, so
the budget has to be generous enough for the slowest *useful* program on
the machine.

Inside the pipeline search the arithmetic is different. A whole wave
finishes in the time one straggler was being allowed, so the head budget
sets the pace for **every** wave.

```
sort alone, any budget   0.22s       four dead heads   0.89s
compose  10 heads  21.04s  no hit
compose  30 heads  20.86s  hit ['sort | wc']
compose 100 heads  56.34s  hit ['sort | wc']   <- 70 heads wasted
budget sweep:  2.0s -> no hit | 4.0s -> no hit | 8.0s -> hit | 20.0s -> hit
```

The floor is measured and it is not free to go lower. `sort` needs 0.22s
alone but about **5s once 24 heads compete for the same cores**; at a 2s
or 4s budget the pipeline is not found at all. `8.0s` finds it, `12.0s`
finds it, `20.0s` finds it a quarter of a minute later.

`_PIPE_HEAD_BUDGET = 12.0` — the cheapest number that keeps the answer.
End to end: `60.8s / 69.2s` -> `48.1s / 53.6s` (~22%), same answer.

The head records the budget it was actually given, so a caller asking
for a minute a head can be shown to get twelve. Removing the cap fails
the new test with `60.0 not less than or equal to 12.0`; dropping the
constant to 4.0 fails it with `4.0 not greater than or equal to 8.0`.

## 8. Still wrong

- **50s cold is not instant.** Reuse is 0.01s; a genuinely new kind of
  question still costs real discovery. No evidence → no learning.
- Latent defect: a tier that finds survivors which then disagree on the
  real file leaves `survivors` non-empty, so **composition is skipped
  entirely** (the `if not survivors:` guard).
- `awk`/`sed`-class answers unreached; filename gate.
- No path from this repo to a dollar; no host that runs when neither of
  us is typing.

## 9. Commands

```bash
python3 -m unittest canonical.tests.test_computer_env_v1      # 80 tests, ~160s cold
rm -f /tmp/brain_query_probe_v1.json /tmp/brain_known_shapes_v1.json   # before cold runs
```

Sabotage discipline that caught real bugs: reverting the probe fix fails
2 tests with `'14' != '7'`; deferring composition to the last tier fails
the race test; merging `wc -l` into `wc -w` fails `TailTests`.
