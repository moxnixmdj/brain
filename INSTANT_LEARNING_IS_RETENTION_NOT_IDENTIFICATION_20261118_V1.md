# Instant learning is retention, not identification

*2026-11-18 · measurement: `canonical/verification/THE_FAILING_RUN_IS_THE_INDEX_20261118_V1.json`
· tool: `canonical/tools/the_failing_run_names_the_expression_v1.py`
· population: 29 real fix commits and 241 real single-line edits in `requests`, `click`, `tqdm`, `httpx`,
oracle = each project's own tests; no QuixBugs, no synthetic corpus, no model, no network at run time*

## The claim, and the one word in it that is doing the work

> "We solved instant learning and instant learning in new environments. Give the model the actions once,
> let it experience each once, and it owns them permanently. So everything on a computer is solved."

Two different functions are hiding in that sentence, and they are not the same function.

| | **retention** | **identification** |
|---|---|---|
| question | given a demonstration, how cheaply does competence survive a new environment? | given a problem, which action is the right one? |
| what it consumes | one trace, one success | evidence that separates the answer from every other answer |
| law | `O(machines × adaptation) + O(requests)`; crossover at the 2nd–3rd request — **measured, solved, keep it** | nothing in this tree, and nothing in the 2026 literature, makes one observation sufficient |
| failure mode | forgetting, cost | confidently wrong, permanently |

Instant learning is a theorem about **retention**. It says nothing about whether the demonstration was the
right one — and one demonstration is the **maximum-variance estimator**: with one sample there is no
averaging, so whatever the trace happened to show becomes permanent. One-shot learning is sound exactly
when a verifier stands at the moment of capture and refuses the wrong sample. Where the verifier is the
project's own tests, an exit code, or a state check, one-shot is sound. Where the verifier is a human
glance or a judge model, one-shot learning is a coin flip made permanent.

So the honest answer is not "instant learning is weak". It is: **instant learning is the right operator
applied to the wrong axis.** Everything that remains unsolved — in coding and in computer use — is on the
identification axis, and identification is not bought with repetitions, because repetitions of a sample
that cannot separate the hypotheses cannot separate them.

## Why one demonstration is not enough: three measured reasons

**1. The observable has to exist before repetition can help.** Carried and re-measured here: when the
causal observable (an executed function, a callee's signature, the value that went wrong) is missing from
the representation, repeating the same trial cannot separate success from failure. This project already
holds the certificate for that (`INSUFFICIENCY_CERTIFICATE_20261113_V1`).

**2. One trace fits exponentially many hypotheses.** This is the version-space result: a single
input–output example leaves a candidate set that is exponential in program size, and the way out is not
more examples of the same kind, it is a **distinguishing query** — an input on which two surviving
hypotheses disagree, resolved by an intervention. That is a different operator from retention, and this
tree already has it (`how_many_hypotheses_survive_an_observation_v1`, `the_experiment_that_identifies_v1`).

**3. For 84.6% of real coding fixes, the answer is not in the thing being looked at.** Measured last
round on 136 real single-expression edits: 115 *replace* the site's expression outright, 17 widen it, 4
narrow it; a pool rooted at the site and ordered by text proximity contains the human fix for **5.9%**.
Showing the agent "the fix once" does not even define what to show, because the fix's material is not in
the site — and the same holds on the computer-use side below.

## What the 2026 evidence says about computer use

The frontier's own failure analysis is not about action vocabulary.

**OSWorld 2.0** (arXiv 2606.29537, 2026) — 108 long-horizon tasks, 500-step budget: the best configuration
reaches **20.6% binary completion** (54.8% partial). The decomposition of *why* is the load-bearing part:

| failure mode | share of tasks |
|---|---|
| final-state exactness failure | **84.3% – 95.4%** |
| premature stop / false done | 75.0% – 83.3% |
| GUI grounding issue | 20.4% – 61.1% |
| strategy: did not finish | the rest |

The paper's own sentence: *"The failure is not a missing click; it is stale grounding."* Agents know how
to click, type and navigate — the action vocabulary is small and already learned. They fail because the
**final state is wrong and they cannot tell**, which is a verification failure, and because the screen they
are reasoning about is stale, which is a grounding failure. Both are identification. Showing the agent
each action once teaches the part that already works.

For coding, the 2026 repair literature has converged on the same realisation from the other side: DynaFix,
DAIRA and Kumushi all move to execution-level dynamic information — traces, variable states, crash paths —
because static context and shallow test feedback do not identify a fault. Every one of them feeds that
trace to a model. Ours derives the patch from it with no model at all.

## The single bottleneck

> **The index. Where do candidate actions come from — and the only index that is causal is the failing
> execution's own values.**

Not vocabulary (77.4% of real code edits are already writable). Not grammar (9.1%). Not statement form
(7.5%). Not pool size (median rank 22 once writable). Not experience (≈2.2% repeat coverage). The last
round left one falsifier: material nominated by the provenance of a value in the failing run must beat
text proximity. This round builds that index and measures it.

## The build: blame the value the failure carries

`canonical/tools/the_failing_run_names_the_expression_v1.py` runs the failing test under a tracer that
records the value of every pure expression in the file (`sys.settrace`, `linecache`, no instrumentation
of the project), and then walks one causal chain:

```
the failure quotes a string   ->   the string's source is an f-string
                              ->   the f-string's argument evaluated to X on that line
                              ->   the guard that let X through is the site
                              ->   the fix excludes X there
```

On `click@1b0e19f505`, unattended:

| step | what the run produced |
|---|---|
| failing test | `tests/test_options.py::test_missing_envvar` |
| the failure quotes | `" (env var: 'None')"` |
| that string's argument | `self.envvar` = `None` (line 2680, `NoneType`) |
| the guard above it | `self.show_envvar` (line 2679) |
| candidate 0 | `(self.show_envvar) and (self.envvar) is not None` — **the human's fix, rank 0** |
| verdict | 2 of 119 tests survive; the human fix is one of them |

The human fix was not compared against the diff, the name table, the file's attributes, or the function's
identity. It was **derived** from the failure, at rank 0, in 3.4 s. The proximity pool reached the same
fix at rank 1 only because `self.envvar` happened to be printed one line below the guard; move that print
forty lines away and proximity loses it while the trace still has it.

The two survivors are still two: `and X` and `and X is not None` are indistinguishable to 119 tests that
never try an empty-string envvar. That is a limit of the oracle, reported as such.

## Head to head, on the same 29 commits, same oracle, same sandbox

| | blame index (this round) | proximity index (last round) |
|---|---|---|
| commits it could propose anything for | 4 | 14 |
| human fix at rank | **0** | 1 (and 396 for the next one) |
| evaluated candidates per site | **5** | 32 executed, 400 in the pool |
| wall clock, 29 commits | **80.1 s** | 265.7 s |
| where it stops | `NO_BLAME` 14: the failure carries no value the run produced | `FIX_LINE_DOES_NOT_PARSE` 6, `FIX_IS_NOT_A_SINGLE_EXPRESSION` 5 |
| oracle absent | 4 `NO_ORACLE`, 4 `SUITE_DID_NOT_RUN` | 2 `NO_ORACLE`, 2 `SUITE_DID_NOT_RUN` |

Neither index closes the other's gap, and the receipt says so: blame is precise and cheap where the failure
carries a produced value (rank 0, five candidates), proximity is broad and blind (fourteen sites, one fix
found by adjacency, one buried at rank 396). The next mechanism has to take blame's precision to
proximity's coverage — that is the `NO_BLAME` boundary below, not a bigger pool.

One more honest data point from the same table: `httpx@e63b6594` has a **single** surviving candidate under
blame and the human fix is not among the five that were offered — the suite said "this is the fix" about
something that is not. That is an identifiability failure in the other direction and it is recorded, not
smoothed.

## What the same operator is, on a computer

Nothing about the chain above is specific to Python. The operator is:

> observe the wrong value in the observable; walk back through the recorded producers of that value;
> emit the minimal intervention that excludes it; re-run and check the observable.

- **coding**: observable = test result and message; producers = the file's executed expressions.
- **computer use**: observable = the final-state check the benchmark already runs (that is the 84–95%
  failure bucket); producers = the UI state and the values the agent read and wrote; intervention = the
  action that changes that state.

This is why the answer to "can we just show it each action once?" is no, and why the answer to "what
should we build?" is not a bigger action library: **the index is the whole product.** A computer-use
agent that indexes its actions by the wrong value it just observed is the same program as this repairer,
with a screen instead of a test file.

## What would falsify this, stated before the next build

On the same population, run the blame index and the proximity index head to head and require:
blame must identify at least as many commits **and** at a lower evaluated-candidate cost (blame evaluates
5 candidates per site against proximity's 32–400). If proximity matches it, the index is not the
bottleneck and this file is superseded, not patched.

## What is not claimed

Most real commits in the sweep produce `NO_BLAME`: their failure carries no produced value, because the
fix is a transformation (`.split(b"?")[0]`), a type test (`isinstance(...)`), or a data constant. That is
the next mechanism's target and it is stated, not hidden. Of the 29 commits, 8 could not run their suite
at all under this sandbox's dependency set and are reported as `SUITE_DID_NOT_RUN` — never as passes.
Everything here is a producer-run sandbox measurement; independent reproduction remains open.
