# ENTRIES THAT ARE ABOUT BEHAVIOUR — 49 contrasts earned by running the code, 22 of them preconditions
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. What changed and why this object instead of another feature

Five rounds established that the vocabulary is **portable and vacuous**: syntax crosses a codebase boundary
at 0.9796 accuracy (V24), and collapses to the base rate when pointed at an outcome — accuracy 1.0000 that
equals "always pass" at the same coverage, with **zero failures predicted** (V25). More static features
cannot fix that, and any feature close enough to predict a test outcome becomes the outcome, which is the
leak this project has now committed and caught twice.

So this round stops describing code and starts **recording what it did**:

```
call f(x = A)   →  observe the result
call f(x = B)   →  observe the result, x differing in exactly one argument
if the two results differ:
    entry = (function, argument, position, WITNESS = (A, B), EFFECT = (result_A, result_B))
```

That is a precondition-effect record that could not have been written without executing the function. It is
inspectable, removable, replayable, and falsifiable.

## 2. The harvest

| | |
|---|---|
| files examined | 135 (`canonical/swe_kernel/*.py`) |
| refused before import (no `__main__` guard) | 59 |
| importable | 61 |
| functions inspected | 591 |
| **single-argument contrasts kept** | **49** |
| dropped because the effect did not differ | **0** |
| **of which one side raises** | **22** |

Sample:

```
action_replay_under_change_v1::first_changed_index   'before'   '' vs 'a'    None      vs 0
argument_construction_v1::measure                    'limit'    0  vs 1      dict      vs TypeError
causal_dependency_repair_v1::read_set_argv           'command'  '' vs 'a'    set()     vs TypeError
```

**22 of 49 are exception contrasts**, and that is the most informative category in the whole project so far:
an argument that changes *whether the call raises at all* is a precondition, discovered by execution. This
is the first evidence here that is about behaviour rather than shape, and it arrived at zero cost — no
probes, no questions, no model call, just running the code that was already in front of it.

## 3. An integrity bug I caused and had to fix

The first harvest **imported the modules**, which executed their `main()` at import time. My run printed
other tools' results into its own output — 191 changed sites, a `call_sites: 0` report — and one module
called `sys.exit(2)` from argparse, killing the parent. Two of my own results were contaminated by code I
did not write, in a project whose central rule is that outputs must be its own.

Three fixes, in order of how much they mattered:
1. **Refuse modules without an `if __name__ == "__main__":` guard** — 59 of 135 files, so this halved the
   corpus, which is the correct trade.
2. **Probe each file in a subprocess**, so import-time prints, argparse exits and subprocess spawns can
   neither reach the output nor abort the run. `redirect_stdout` was not enough; fd-level redirection was
   not enough; process isolation was.
3. `--out` became optional for the internal probe path, because the subprocess invocation was dying on a
   required argument that only the parent run needs.

## 4. What these entries are, and are not

**Are:** earned (each one required executing the function twice, on two inputs, twice each, to prove
determinism), replayable (the witness is concrete, so re-running reproduces or falsifies), inspectable (six
fields), removable (delete the record), and zero-model.

**Are not:** causal claims about a function's internals; general (each is one argument position at one pair
of values); evidence that anything predicts a *task* outcome. 49 entries from 591 functions is sparse, and
sparse for a reason worth naming: the ladder has 3–4 values per type, so a contrast is only found when the
first differing pair on that argument changes the result.

**The replay test is the point.** A test re-runs two recorded entries and asserts the recorded effect still
holds. If the underlying code changes, the entry fails — which is exactly the property no syntactic feature
in this project has ever had.

## 5. Where this sits against the mission

The prompt's §9.2 asks for a store of "preconditions and effects ... with a re-validation probe". This round
is the smallest honest instance of that, built from the only raw material that is unambiguously ours: code
we can execute. It does not solve computer use, and it does not attempt SWE-bench.

The standing measurement across the last six rounds, in one table:

| result | status |
|---|---|
| lifting moves coverage 0.126 → ~0.70 on ten machine worlds | verified, then shown to be scope-limited |
| vocabulary transfers across codebases, stated over syntax | verified (0.9796 vs 0.9896) |
| vocabulary predicts test outcome | **failed** — equals "always pass" at equal coverage, 0 failures predicted |
| cross-machine law transfer (either lifted or not) | **failed** |
| guards, saturating question supply, accuracy-gated stopping | **failed** (three rounds) |
| behavioural entries earned by execution | **verified** — 49, 22 with raise contrasts, replayable |
| any benchmark row | **not producible** (`docker: command not found`, logged once) |

## 6. Verified / unverified / failed

**Verified by execution:** 49 earned entries with observed differences; 22 exception contrasts; determinism
checked per call pair; two entries replayed and matched by test; 59 unsafe modules refused before import.

**Failed, mine, this round:** the in-process import design, which contaminated output and aborted a run;
two shell-level fixes that looked right and did not work before process isolation did.

**Unverified:** whether a store of such entries supports any downstream task. I have not used them for
anything yet, and I will not claim that a 49-entry store is useful until a task consumes it and something
measurable changes.

**Not publishable:** any benchmark row — `docker: command not found`. Nothing here is a claim about
SWE-bench Pro, Terminal-Bench 4.0, or OSWorld 2.0, and no comparison to any frontier model is made.

## 7. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 51.3 s · 135 files
```

4 new tests, including a replay test that will fail if the recorded behaviour stops being true. Guard PASS
(17 rules).

## 8. Next

The entries exist and nothing consumes them. The next instrument has to make one of them **earn its place**
by changing a prediction: take a function with a recorded contrast, find its call sites in this repo's own
tests, and ask whether knowing the contrast predicts which existing test exercises which branch. If it
does not, the store is a museum and this report says so.
