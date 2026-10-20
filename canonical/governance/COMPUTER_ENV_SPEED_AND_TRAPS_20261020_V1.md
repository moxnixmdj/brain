# computer_env: where the time went, and the traps

Branch `arena/e1e96d1c-brain`. Everything below was measured on this
machine. Rebuilt after a re-clone destroyed four commits and the `/tmp`
backup — **record findings in the repo, not in `/tmp`.**

## 1. Headline numbers

```
cold, "how many unique lines"   355s -> 132.4s   (answer correct: 7)
full suite, cold                631s -> 249s
warm                            0.01s
```

Each step, measured rather than guessed:

```
441s  original
385s  fail-fast on the first probe + per-program budget + counter memory
355s  probe fix   <- also corrected a WRONG answer (14 where 7 was true)
277s  behavioural dedupe of pipeline tails
132s  race: composition alongside the first sweep
```

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

## 8. Still wrong

- **132s cold is not instant.** Reuse is 0.01s; a genuinely new kind of
  question still costs real discovery. No evidence → no learning.
- Latent defect: a tier that finds survivors which then disagree on the
  real file leaves `survivors` non-empty, so **composition is skipped
  entirely** (the `if not survivors:` guard).
- `awk`/`sed`-class answers unreached; filename gate.
- No path from this repo to a dollar; no host that runs when neither of
  us is typing.

## 9. Commands

```bash
python3 -m unittest canonical.tests.test_computer_env_v1      # 76 tests, ~250s cold
rm -f /tmp/brain_query_probe_v1.json /tmp/brain_known_shapes_v1.json   # before cold runs
```

Sabotage discipline that caught real bugs: reverting the probe fix fails
2 tests with `'14' != '7'`; deferring composition to the last tier fails
the race test; merging `wc -l` into `wc -w` fails `TailTests`.
