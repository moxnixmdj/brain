# A refused receipt is still marked verified

**2026-11-12.** Base `3243ab0c`. Branch `arena/eb986bc7-brain`. Round 11.

This closes the last of the nine gates. Seven rounds ago, nine repair-family capabilities were found
accepting on `output_verified` — "a file was written" — while the honest answer sat in `pass`. Eight
were repointed with executed evidence. The ninth, `python.task.acceptance.measured.objective.v1`,
was left alone because it consumes a content-addressed measurement receipt, and I refused to
fabricate one.

It turned out the receipt did not need fabricating. The tree has a producer.

## What was run

`python.repository.acceptance.measure.v1` measured a real fixture — a module, a passing test, a
source tree — and emitted a content-addressed receipt. That receipt was handed to the consumer
twice:

- **genuine** — untouched;
- **refused** — one measurement value altered by one, so the consumer's payload hash no longer
  matches and it says so.

```
  genuine receipt
    producer said           True  PASS__CONTENT_ADDRESSED_REPOSITORY_MEASUREMENT
    consumer said           pass=False  OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS
    wrote the answer        output_verified=True
    legacy predicate        accepts=True   live registry accepts=False   outcome predicate accepts=False

  altered receipt
    producer said           True  PASS__CONTENT_ADDRESSED_REPOSITORY_MEASUREMENT
    consumer said           pass=False  FAIL_CLOSED
    wrote the answer        output_verified=True
    legacy predicate        accepts=True   live registry accepts=False   outcome predicate accepts=False
```

**The legacy predicate accepted a genuine pass and a refused receipt, and could not tell them
apart.** That is the entire case, and it needed no argument.

Authority **NONE**. Both capabilities ran in-process against a temporary fixture. Nothing was written
into the repository, no receipt is committed, $0, zero model dependency.

## What changed

```diff
   "expect": {
-    "field": "output_verified",
+    "field": "pass",
     "type": "field_equals",
     "value": true
   }
```

Registry-wide: `output_verified` **91 → 90**, `pass` **17 → 18**. `DEFINITE_DEBT` — the pinned list
of capabilities that compute an outcome while registering a transport field — is now **empty**, and
the nine that were in it are kept by name in `REPOINTED_ON_20261112` so that a drift back is named
rather than merely counted.

## Why the honest answer is False in both cases, and why that is correct

This is the part worth reading carefully, because a reader could mistake it for the gate malfunctioning.

*Genuine receipt, `OPEN__SEMANTIC_ACCEPTANCE_RESIDUALS`.* The tests passed and the measurement is
sound, but the task sentence — "make the tests in test_calc.py pass" — carries obligations the
acceptance compiler cannot turn into objective routes. The module is explicit that measurement
binding does not create missing task semantics. So the run does not accept. Correct.

*Altered receipt, `FAIL_CLOSED`.* The payload hash does not match; the consumer refuses to read it at
all. Correct.

Neither is a success, and a gate that says yes to either is not a gate. Before this round, that is
exactly what the registry said to both.

## What this does not establish

The consumer has now been executed on a receipt it accepted as *well-formed* and on one it refused.
It has **not** been observed returning `pass: True`, because every task sentence tried so far leaves
semantic residuals, and inventing a task sentence designed to clear them would be exactly the kind of
dressing-up this series exists to catch. So the evidence here is one-sided in a specific and stated
way: it shows the new predicate rejects what the old one wrongly accepted, not that it accepts a
genuine success. Round 6's `_check_expect` test covers the accept direction for the other eight; this
one does not yet have that coverage, and the honest labelling is *repointed on rejection evidence*.

Finding that task text — one whose obligations compile objectively and clear — is the next concrete
task, and it is a better one than another census.

## Where the series stands

| round | finding |
|---|---|
| 2 | one demonstration carries a procedure (14.1/47) but identifies it badly (10%, 0/10 exact) |
| 3 | 41% one-shot safe is a **receipt-existence** figure, not a gate-quality figure |
| 5–7 | nine gates answered "was a file written"; eight repointed, executed |
| 8 | one lesson teaches a **word**, generalising to 12 unseen requests, 0 wrong |
| 9 | twelve lessons buy nothing; **sixteen lines** buy the operator |
| 10 | one demonstration prunes **1 of 34** programs; a three-assertion suite prunes 28 |
| 11 | the ninth gate accepted a **refused receipt**; repointed; debt list empty |

## Receipts

```
python3 a_refused_receipt_is_still_marked_verified_probe_20261112.py
python3 -m pytest -q canonical/tests/test_a_refused_receipt_is_still_marked_verified_v1.py \
                    canonical/tests/test_gate_accepts_a_failed_repair_v1.py        18 passed
```

## Non-claims

Two cases, one fixture, one producer, one consumer. No `pass: True` was observed from this capability
(audit it: every task sentence tried leaves semantic residuals). No capability added, no adapter
changed, `truth.achieved` false, $0, zero model dependency.
