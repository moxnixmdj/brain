# The probe was certifying a tool that answers a different question

Committed `c2c6a8fe`. Findings from measuring, 2026-10-20.

## 1. The wrong answer, and why the check missed it

The machine answered **14 where the truth was 7**, with three independent
programs agreeing. It had found `uniq | grep -c ''`.

`uniq` collapses **neighbours**. It does not count different lines; it counts
**runs**. The probe built to catch that mistake did not catch it, because the
probe put every repeat next to its twin:

```
row 0
row 0
row 1
row 1
```

That is the one arrangement `uniq` is built for. On it, the wrong tool prints
`n` and is indistinguishable from the right one.

Fix: repeats go at **opposite ends** of the file. Measured on the new probe:

| program | prints | truth is 7 |
|---|---|---|
| `uniq` | 14 | rejected |
| `sort` | 14 | rejected |
| `cat` | 14 | rejected |
| `sort --unique` | **7** | accepted |

## 2. The test could not see it either

`PipelineTests`' fixture was `kind0,kind0,kind0,kind1,kind1,kind1,...` —
**all repeats adjacent**, the single file on which `uniq` happens to be right.

**Reverting the fix with that fixture left all 7 tests green.**

The fixture now keeps its repeats apart (`names + names[3:] + names[:3]`,
14 lines / 7 distinct / no two neighbours equal) and **asserts** that it does.
Reverting the fix now fails 2 tests with `'14' != '7'`.

> A fixture that cannot tell the wrong answer from the right one is not
> testing anything.

## 3. Finding `sort --unique` needed one more fix

The pipeline search offered its first stage only the flags the question's
words suggested. `--unique` is not a flag the sentence "how many unique
lines" knows how to suggest — the same lesson as `--count` being the **65th**
flag grep documents.

Measured: `sort` has 7 narrow shapes (all useless) and 105 wide ones, and
`-u`/`--unique` appear **only** in the wide set. **Wide is a strict superset
of narrow** for every program checked (`sort`, `uniq`, `cat`, `head`, `tr`),
so asking for the whole manual gives nothing up.

## 4. Where the time actually went

Measured on this machine, "how many unique lines", cold:

```
tier  24:  100.5s   (24 candidates, 0 survivors)
tier  96:  115.4s   (96 candidates, 0 survivors)
tier 200:  125.6s   (200 candidates, 0 survivors)
                    -> 341.5s proving a negative, then thrown away
```

**The cost is not per-program.** 10 programs took 98.6s and 24 took 99.9s —
one **straggler** sets the pace for the whole wave. Serial total was 510.9s;
wall clock was ~70s, i.e. everybody waiting.

```
 69.3s  docker-entrypoint.sh   a shell wrapper, not a tool
 68.9s  node                   slow-starting runtime
 68.7s  nodejs
 27.7s  ld
 19.6s  grep                   <= a real answer
```

Two dead ends were setting the pace for the entire search.

After:

```
single-program tiers   341.5s -> 164.9s
finding the counters    99.0s ->  59.2s
```

Three changes:

- **A program that misses the first probe no longer gets the second.** Most
  shapes are wrong; proving a wrong shape wrong twice instead of once costs a
  run on every shape of every program on the machine.
- **`_PROGRAM_BUDGET = 20.0`, `_WIDE_BUDGET = 45.0`.** A program that has not
  shown it can count in that long is not worth more time when hundreds of
  others are still untried. The wide pass gets more, because it exists to
  reach deep flags.
- **`_known_counters`** — which commands count lines is a fact about the
  machine, not about the question. Cached under key `-2`, capped at 4:
  composing with thirty counters is not thirty times better, it is thirty
  times slower.

## 5. Still open

- **Cold is still ~385s.** ~165s of that is the three single-program tiers
  proving a negative that is then discarded, for a question only a pipeline
  can answer. The intended fix is to **race** composition against the
  cheapest tier instead of running it only after all three fail: you do not
  need to prove a negative before finding a positive.
- Latent defect, seen at the `if not survivors:` guard: if a tier finds
  survivors that then fail to agree on the real file, `survivors` is
  non-empty and **composition is skipped entirely**.
- `awk`/`sed`-class answers still unreached; filename gate; no path from
  this repo to a dollar; no host that runs when neither of us is typing.

## 6. Regression runner

```
python3 -m unittest canonical.tests.test_computer_env_v1      # 72 tests, 631s cold
python3 -m unittest canonical.tests.test_computer_env_v1.PipelineTests
```

`rm -f /tmp/brain_query_probe_v1.json` before any cold measurement — a stale
entry here has masked an entire round of work more than once.

Pristine copies for sabotage: `/tmp/cev_good8.py` (at `c2c6a8fe`).
