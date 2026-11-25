# Two rows neither engine has ever seen: both fail, honestly

**Measured 2026-11-24.** Receipt: `THE_UNSEEN_ROWS_FAILED_20261124_V1.json`.
Corpus: `canonical/corpus/the_six_the_prompt_named_20261124_V1.json`.

## Why these rows

The incoming plan named six commits as its Step-1 targets
(`click@c53d373`, `05f6fd0`, `fc518e4`, `ac0e297`, `werkzeug@884437ae`,
`werkzeug@051fd663`). All six exist in the clones and are real commits. None of them is
in the 45-commit corpus, so testing them is a genuine held-out check rather than a
re-run of known-good rows.

Two of the six are attemptable by the union driver as it stands. They are a fair test
and not a soft one: both are **boolean-logic** repairs, which is the class the
guard-probe engine was built for and the class it wins on this corpus.

- `werkzeug@884437ae` — "fix boolean logic for external url". Changes the guard at
  `src/werkzeug/routing/map.py` from
  `not force_external and (dom or host) and (...)` to
  `not force_external and (not (dom or host) or ...)` — a de Morgan restructuring.
- `werkzeug@051fd663` — "fix trailing whitespace in WWW-Authenticate bearer". Adds
  `if not self.parameters: return self.type.title()` to
  `src/werkzeug/datastructures/auth.py`.

## Result

```
[1/2] werkzeug 884437ae -> NO_SEPARATING_RULE
[2/2] werkzeug 051fd663 -> NO_SEPARATING_RULE
0/2 verified
```

Both engines agree there is no separating rule. That is a **null result on unseen rows**
and it is reported as one: the 41.5% union does not transfer for free to these two.

## What it took to make the test valid at all, and a gap in my own environment doc

The first attempt returned `NO_PASSING_TEST` on both rows, which looks like an engine
verdict and is not one. The cause was a missing dependency: `tests/test_routing.py`
cannot import at that commit without `markupsafe`, so pytest produced a collection error
and zero verdicts.

`THE_ENVIRONMENT_THAT_MAKES_THESE_NUMBERS_REPRODUCIBLE_V1.md` lists `pretend`,
`pytest-asyncio` and `hypothesis` but **not** `markupsafe`. Any future session that
rebuilds the venv and runs a werkzeug row at this era will get `NO_PASSING_TEST` and may
misread it as an engine limitation. That is now recorded here, and the environment doc is
corrected in the same commit.

The general lesson is the one this build keeps relearning in different clothes: a stage
name that means "the harness did not produce evidence" must never be quoted as a fact
about the engine's ability. `NO_PASSING_TEST` and `NO_ORACLE` are instrumentation
verdicts; `NO_SEPARATING_RULE` is an engine verdict. Only the second one is about the
engine, and only after the first is ruled out.

## What this does to the plan

It removes the two cheapest rows the incoming plan named as Step-1 targets. The other
four are larger than one line and outside the corpus's single-line schema:

| commit | source change | attemptable by the current driver? |
|---|---|---|
| `click@c53d373` | 23 lines in `core.py` | no — multi-line |
| `click@05f6fd0` | 20 lines in `core.py` | no — multi-line |
| `click@fc518e4` | 76 lines in `core.py` | no — multi-line, own test file of 179 lines |
| `click@ac0e297` | 38 lines in `testing.py` | no — multi-line |

So the honest position on the plan's Step 1 is: two of its six named rows are measured
and fail, and the remaining four are outside the generator's current shape entirely. That
does not make the plan wrong; it means its cheapest examples do not support it, and the
multi-line case is the next real question rather than an already-answered one.
