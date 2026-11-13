# "Exact matches only" is false — 95.9% of what one showing recovers was never shown

**2026-11-12.** Base `92e08010`. Branch `arena/5f24577e-brain`.

Problem 2 was written down as a factual claim: *"current state: NOT WORKING — exact matches only."*
That had never been tested. It is tested here, on the recorded corpus, and **it is false.**

---

## 1. The test, and why it had to be built

Every number in this tree measured *how much* one showing recovers. None separated **recovering a
statement the example literally showed** from **recovering a statement it never showed**. That
separation is the whole of Problem 2: the first is lookup, the second is generalizing.

The rule, decided before the organ runs so the organ cannot influence it:

> a change is **SHOWED** when its own old statement text appears in the example's first file;
> otherwise it is **NEVER_SHOWED**.

It is deliberately *not* classified by the change's kind. Using the kind would grade the organ's
answer with the organ's own rule.

## 2. The result

Over the 330 askings (168 dropped as not applicable — see §4):

| | right | missed | share |
|---|---|---|---|
| **SHOWED** — the example literally contained that statement | 16 | 7 | 0.6957 |
| **NEVER_SHOWED** — a statement the example never showed | **370** | 214 | 0.6336 |

**370 of the 386 changes one showing recovers — 95.85% — are on code the example never showed.**
Recovery on never-shown code (63.4%) is statistically indistinguishable from recovery on the exact
statement (69.6%), on 23 samples of the latter.

Exact-match lookup cannot do this. A hash of the demonstrated statement recovers **zero** of those
370. The mechanism is a *rule* applied to different code: different receiver, different arguments,
different surrounding lines, usually a different file and project. **Problem 2's premise is wrong.**

## 3. The second half: what the 36% actually is

On the applicable askings, all **221** missed changes were classified by shape against what the
example demonstrated: **221 of 221 are the same shape as the demonstrated change, and 0 are a
different kind of change.** So the residual is *not* "the developer went and did something else",
which is how it has been described. It is the same change, on the same form, missed.

Attributing every miss to the asking's outcome gives exactly two causes:

| cause | missed changes |
|---|---|
| `NAME_NOT_AVAILABLE` — the new code reads a name the file lacks | 111 |
| the organ edits the file but only some of its places | 110 |

The second is the interesting one, and the tree already names it: a rule learned from one place is
**literal** — it carries the example's own string constants and argument shapes, so a second site
with a different message does not fit. That is not a missing operator. It is the price of one
showing, and it is why the second demonstration exists.

## 4. The number that had been read as a capability

The published `0.2999` mixes two populations. 168 of the 330 askings target a file containing
nothing the example changed; no one-example operator can ever reach them, and they recover `0/680`
— correctly. Excluding them, which is what "adapting a **similar** task" means:

**coverage 0.6359 (386/607), precision 0.9461.** That is the honest figure for Problem 2, and it is
**twice** the number the tree had been quoting.

## 5. One correction to the scoring, made visible rather than quiet

`score` compares changes as text, so it charged the organ a **wrong edit** for writing

```python
from datetime import date, datetime, timedelta, UTC      # the organ
from datetime import UTC, date, datetime, timedelta      # the developer's formatter
```

Both import the same three names from the same module. `equivalent` decides such cases by **parsing
both statements and comparing the import name sets** — not by loosening a threshold, not by a fuzzy
match. Applying the narrow import-extension operator on top, the same run gives:

| | coverage | precision | wrong |
|---|---|---|---|
| strict | 0.3831 | 0.9181 | 36 |
| equivalence-aware | **0.4064** | **0.9739** | **14** |

Every one of those 22 "extra wrong edits" was an import name order. The correction is reported
beside the strict figure, never instead of it.

The operator that produced this is **measured, not shipped**: it extends an import line the file
already has and never adds a module the file does not import. That restriction is what keeps
precision at 0.97 rather than the 0.80 the wide form reached.

## 6. What is real, and what is not

* **Real:** generalization is the mechanism, not lookup — 95.9% of recovered work was never shown.
* **Real:** adaptation is 63.6% where the task is similar, at 94.6% precision.
* **Not real:** "generalization NOT WORKING — exact matches only." Falsified.
* **Not real:** "the residual is the developer doing a different change." It is 0% different-change;
  it is the same change, missed for two named and countable reasons.
* **Not claimed:** that 36% is closed. It is now **221 named changes** with two causes, not a gap.
* **Still the largest unmeasured risk, unchanged by this round:** **no project's own tests have ever
  been run.** Every number above is agreement with what people did, never correctness. I considered
  closing that this round and rejected it on the evidence: most of the files changed are *test files*,
  so a project's suite does not cover them, and 8 of the 15 projects cannot import a single changed
  file in this sandbox (no `numpy`, `cv2`, `PIL`, `dotenv`, `yaml`). Running tests would have produced
  a number about 7 projects and a silent gap about 8 — worse than saying so.

## 7. Receipts

```
python3 canonical/tools/repeated_change_one_example_measure_v1.py --collect /tmp/pulls_v3.json \
        --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json
python3 canonical/tools/generalization_or_lookup_v1.py --pulls /tmp/pulls_v3.json \
        --out canonical/verification/GENERALIZATION_OR_LOOKUP_20261112_V1.json
pytest -q canonical/tests/test_generalization_or_lookup_v1.py    13 passed
corpus 15 pull requests / 89 files, refetched and matching the record
model_calls 0, incremental_spend_usd 0, terminal_authority false
```

No tolerance widened, no organ changed this round, `truth.achieved` untouched, no credit claimed.
