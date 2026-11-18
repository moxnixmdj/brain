# Recognition is the bottleneck: you cannot search for what you cannot accept

*`canonical/tools/the_assertion_is_the_demand_v1.py` · `--audit` · 16 tests · receipt `canonical/verification/RECOGNITION_IS_THE_BOTTLENECK_20261121_V1.json` · 30 real commits · 0 parameters*

---

## The order of operations was wrong

The instrument searches a closure for an expression that satisfies the demand of a failing test, then verifies with the corpus's own suite. Fine. But before any of that there is a cheaper question that was never asked:

> **Does the instrument accept the human's own fix?**

Last round's receipt said 1 of 14. That number was printed and not explained. An instrument that refuses the truth 13 times out of 14 cannot be trusted to reject a lie — every "no candidate" it reports is contaminated by its own reader. So this round asks the question first and names every refusal.

## The audit

`--audit` evaluates the human's replacement at every recorded frame of the failing test and classifies the outcome:

| verdict | meaning |
|---|---|
| `ADMISSIBLE` | the instrument would have accepted the true fix |
| `REFUSED` | the expression cannot be evaluated at the site at all, and the reason is named |
| `VALUE_DIFFERS` | it evaluates, and produces something the reader believes is not the demanded value |
| `THE_SITE_NEVER_RAN_IN_THE_FAILING_TEST` | there is nothing to evaluate against |

**Run on 30 real commits, before the corrections: 1 ADMISSIBLE · 4 REFUSED · 6 VALUE_DIFFERS · 3 SITE_NEVER_RAN.**

Two of the four refusals were one word long and decisive:

```
NAME_NOT_IN_FRAME: name '_SkipClose' is not defined
REFUSED: AttributeError
```

The fix references a name **the parent commit does not have**. `_SkipClose` is a class the same commit introduces two hundred lines away; the attribute is added by the same commit. These are composite edits wearing a one-line site — and they were being counted in the denominator of "single-expression replacements". The census was wrong, not the reader.

Of the six `VALUE_DIFFERS`, three were the reader accusing the truth with a demand it should never have accepted:

```
demanded: "assert 'line one\nline two\n\n' == 'line one\n\n + where ..."
demanded: "assert not AssertionError('assert Sentinel.UNSET is not Sentinel.UNSET')"
```

That is pytest's **rendering** of a failure, not a value the site owes. The instrument had a guard of exactly this shape on the candidate side (`plausible()`) and none on the demand side.

## The two corrections

1. **A rendered assertion is not a demand.** `is_prose_demand()` refuses any demand that begins with `assert `, contains ` + where `, `\n + ` or `<Result`. On this corpus **14 demand strings were refused**, and the rows they belonged to were re-reported honestly as `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` instead of as a wrong answer by the human.
2. **A fix that introduces its own names is not an expression replacement.** When the audit refuses with `NAME_NOT_IN_FRAME` or `AttributeError`, the row is reclassified `EXCLUDED__THE_FIX_INTRODUCES_A_NAME` — out of the denominator, named, not counted as a miss.

## After

| stage | rows |
|---|---|
| not a single-expression replacement | 15 |
| **the fix introduces a name** (census corrected) | **2** |
| **no relation between the demand and the site** (prose refused) | **6** |
| demand known, nothing produced it | 5 |
| the site never ran in the failing test | 1 |
| **verified: whole file green, patch = the human's own fix** | **1** |

Whole sweep: **71.9 s**, `parameters_stored: 0`, 0 model calls.

Audited rows: **1 ADMISSIBLE · 3 VALUE_DIFFERS · 2 REFUSED · 2 SITE_NEVER_RAN**. The accusations against the truth fell from 6 to 3, and each survivor is named:

- `91de59c6c8` — `demanded=[0] produced=[True]`: a **mis-attributed demand**, read from an assertion in the test that the site has nothing to do with. This is the residual defect and the next one to kill.
- `13105a64f2`, `a150ff749a` — the demand is an exception **message**, which is a legitimate value but a string the site does not produce; these rows are honestly unreachable for this reader.

## The law

> **You cannot search for what you cannot accept.** Recognition comes before search, and search before verification. An instrument that cannot recognise the truth does not have a recall problem — it has no idea what it is looking for.

This is the same shape as the external 2026 evidence, from the other end: Skill-Pro's ablation shows that removing the verifier gate makes the agent reuse plausible, wrong skills; and the ACL 2026 memory study finds that *strict evaluators* are what make experience worth storing, while unfiltered addition performs below a no-memory baseline. In every case the gate decides, not the store.

## What is not claimed

That the 5 `NO_VALUE_MATCHES` rows are impossible — they are a fact about this closure. That the 2 excluded rows are failures — they are outside the instrument's scope and are censused. That 1 admissible row is a ceiling — it is what this reader can recognise on this corpus, and the audit exists precisely so the next round can move it with a named cause instead of a hope.

## Reproduction

```
/tmp/venv/bin/python canonical/tools/the_assertion_is_the_demand_v1.py \
  --commits /tmp/corpus/c30.json --audit --survivors-cap 8 --verifications 8 \
  --receipt canonical/verification/RECOGNITION_IS_THE_BOTTLENECK_20261121_V1.json
/tmp/venv/bin/python -m pytest canonical/tests/test_the_assertion_is_the_demand_v1.py -q    # 16 passed
```

Authority NONE. Producer-run. 0 parameters, 0 model calls, 0 network calls at run time.
