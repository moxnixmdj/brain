# The failing run is the index

*2026-11-18 · measurement: `canonical/verification/THE_FAILING_RUN_IS_THE_INDEX_20261118_V1.json`
· answer in full: `INSTANT_LEARNING_IS_RETENTION_NOT_IDENTIFICATION_20261118_V1.md` (repository root)*

## The claim being answered

> "We solved instant learning and instant learning in new environments. Give it the actions once and it owns
> them permanently — so everything on a computer is solved."

## Retention versus identification

Two functions are hidden in that sentence. **Retention** asks how cheaply competence survives a new
environment, and it is solved: `O(machines × adaptation) + O(requests)`, crossover at the second or third
request. **Identification** asks which action is the right one, and nothing in this tree or in the 2026
literature makes one observation sufficient: one demonstration is the maximum-variance estimator, and a
single trace is consistent with exponentially many hypotheses. One-shot learning is sound exactly when an
exact verifier stands at the moment of capture — tests, exit codes, state checks — and a coin flip made
permanent when the verifier is a glance.

**The 2026 computer-use evidence says computer use fails on the identification axis, not the action axis.**
OSWorld 2.0 (arXiv 2606.29537) reports a best of 20.6% binary completion and decomposes the failures:
final-state exactness **84–95%**, premature stop 75–83%, GUI grounding 20–61% — *"the failure is not a
missing click; it is stale grounding."* The action vocabulary is the part that already works.

## The build: blame the value the failure carries

`canonical/tools/the_failing_run_names_the_expression_v1.py` traces the failing test with `sys.settrace`,
records the value of every pure expression in the file, and walks one causal chain:

```
the failure quotes a string  ->  the string's source is an f-string
                             ->  its argument evaluated to X on that line
                             ->  the guard above it let X through
                             ->  the fix excludes X there
```

`click@1b0e19f505`, unattended: the failure quotes `" (env var: 'None')"`, the argument `self.envvar` was
`None` on line 2680, the guard `self.show_envvar` is on 2679, and candidate 0 is
`self.show_envvar and self.envvar is not None` — **the human's fix, derived at rank 0**, with 2 of 119
tests surviving (the suite cannot separate `and X` from `and X is not None` because no test tries an
empty-string envvar). Five candidates were evaluated; the text-proximity pool needed 400 to place the same
fix at rank 1, and only because the blamed value happened to be printed one line below the guard.

## What went wrong in the last round, and is corrected here

That round reported "10 of 29 commits have no oracle: the post-fix tests pass on the parent". Most of those
suites **never ran**: `requests` and `httpx` conftests import urllib3/trustme/uvicorn/trio, tqdm sets
`filterwarnings = error` so a pytest-asyncio warning became an INTERNALERROR, and a changed line that is one
entry of a dict literal parsed as nothing. An empty verdict map was being read as a passing suite. It is now
`SUITE_DID_NOT_RUN`, with the output kept, and three tests pin it.

## Where the mechanism stops, stated as the next target

11 of 29 commits return `NO_BLAME`: the failure carries no value the run produced, because the fix is a
transformation (`.split(b"?")[0]`), a type test (`isinstance(...)`) or a data constant. 2 have a blamed
value with no guard above it. That boundary is the next build: close the chain on the other observable
channels — exception type and message, exit code, unformatted stdout — and then on the final-state check of
a computer-use task, which is exactly the 84–95% failure bucket OSWorld 2.0 measures.

**Falsifier.** On the same population the blame index must identify at least as many commits as the
proximity index and at a lower evaluated-candidate cost (5 versus 32–400). If proximity matches it, the
index is not the bottleneck and this file is superseded, not patched.
