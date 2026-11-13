# Problem 2 is two questions, and one of them is already 64% solved

**2026-11-12.** Base `aea7d0ce`. Branch `arena/3dff4ec0-brain`.

Priced, not counted. Three findings, and the first one is a bug that was writing broken code.

---

## 1. A fix that was silently breaking code — now refused

`expression_operator_pack_v1` learned **any** single-attribute rename whose arguments were
untouched, and called it "safe without an oracle". It rewrites

```python
yaml.load(h, Loader=yaml.FullLoader)   ->   yaml.safe_load(h, Loader=yaml.FullLoader)
```

which cannot run: `safe_load` takes no `Loader`. `assertEquals -> assertEqual` and
`yaml.load -> safe_load` have **the same shape** — one attribute renamed, arguments untouched,
neither a re-export. This tree already proved that no structural reading separates them, and the
organ already refuses `yaml.load` for exactly this reason. The pack's docstring stated the
inference that was measured false ("the arguments are not touched, so the number of arguments is not
evidence against the rename" — true for a kept alias, false for a different function).

It now asks `kept_under_an_old_name_v1.alias_of`, the same closed documented list the organ uses,
and refuses every pair that is not on it. Three tests added, including the `yaml.load` one that was
missing. **This was the only thing standing between a "second operator" and broken code.**

## 2. What that second operator is actually worth: +0.39 pp, not +7.35 pp

The pack's recorded `+7.35 pp` was measured against organ `0cca78be` — the organ *before* the
kept-alias exemption landed. Re-measured on today's organ, same 330 askings, same scoring:

| | strict coverage | precision | wrong changes | edits made |
|---|---|---|---|---|
| organ alone | 0.2999 | 0.9461 | 14 | 408 |
| organ + sound pack | **0.3038** | **0.9467** | **14** | 413 |

So the headline gain had **already been paid for**. All five remaining askings are
`logger.warn -> logger.warning`. What looked like a new operator was, to within 0.4 pp, a
re-derivation of work already merged — and the unsound residue was the only genuinely new part.
**A gain measured against a stale baseline is not a gain.** That is the mistake this round existed
to catch, and it was sitting in the tree as a pinned fixture.

## 3. The number that answers the owner's question

The published `0.2999` is a **dilution**, not a capability. Split the same 330 askings by the organ's
own refusal ("nothing in the file has the form the example changed") — a rule that needs no extra
table, so it covers all 15 pull requests and all 89 files:

| | askings | changes recovered | share |
|---|---|---|---|
| **applicable** — the demonstrated form occurs in the target | 162 | **386/607** | **0.6359** |
| not applicable — nothing of that form in the file | 168 | 0/680 | 0.0000 |
| all askings (the published figure) | 330 | 386/1287 | 0.2999 |

**When the demonstrated form is present, one showing adapts and repeats correctly 63.6% of the
time.** The other 168 askings cannot be touched by *any* one-example operator, because the thing the
example changed is not in the file — that is the task being different, not the learner failing.

Per task, on the five whose kind the marker table names: `torproject/stem` 0.900,
`RedHatInsights/advisor-backend` 0.909, `openimis` 0.480, `testing-cabal/testtools` 0.107,
`automagician` 0.000 — on 3 changes.

So the honest state of Problem 2:

* **~64% solved** where the task is genuinely similar. This is not exact-match lookup: the target is
  a different file, a different project, different surrounding code, often a different call shape.
* **The remaining 36% is 107 named changes** that sit on the demonstrated form and are still missed.
  That is the real frontier, and it is countable rather than vague.
* **`0.2999` understates it by 34 points** because the denominator mixes "the task is similar" with
  "the task is different". Both numbers are real; quoting only one is how a 64% mechanism gets sold
  as a 30% one, or a 30% one as complete.

## 4. What is real and what is not

**§7 of `WHICH_FIX_ACTUALLY_WORKS_20261112_V1.md` said "not claimed: Problem 2 is solved". That was
too pessimistic on the applicable subset and too optimistic on the headline, in the same sentence.**
Both halves are corrected here, by regrouping the same run, not by re-running anything.

* **Real:** generalization to a *similar* task is 63.6% where applicable, at 94.6% precision, with a
  different file and different surrounding code. Exact-match lookup cannot do this at all.
* **Real, and new:** a pinned fixture in this tree claimed +7.35 pp that was really +0.39 pp, and an
  operator described as "safe without an oracle" was writing `yaml.safe_load(h, Loader=...)`.
* **Not real:** "instant learning in new arbitrary environments is solved perfectly". It is 63.6%
  where the form appears, and 0% — correctly, necessarily — where it does not.
* **Still the ceiling:** a perfect learner of the demonstrated kind cannot exceed what the
  demonstrated kind names. That bound is structural and no operator removes it.

## 5. What is smartest next, in order

1. **The 107 missed changes on applicable files** — now a fixed, countable target with a named
   denominator, instead of a percentage arguing with itself.
2. **A settlement check** (the projects' own tests). Nothing here has ever run one, so *agreement
   with the people* has never been turned into *correctness*. That is the single largest unmeasured
   risk in every number above.
3. **Nothing else.** The import-only and block-shape classes remain learn-time problems with zero
   reachable askings; the f-string operator is measured at **−0.195 precision** and must stay behind
   a test, never a stored lesson.

## Receipts

```
python3 canonical/tools/repeated_change_one_example_measure_v1.py --collect /tmp/pulls_v3.json \
        --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json
pytest -q canonical/tests/test_expression_operator_pack_v1.py        13 passed (was 11, +3 added)
organ 7737d8f1, pack patched this turn, model_calls 0, incremental_spend_usd 0
```

No tolerance widened, no `truth.achieved` touched, no credit claimed.

---

## 6. Addendum, same turn: my own fix was incomplete in exactly the same way

The exemption I shipped last round refuses a *rename between two documented aliases*. But the organ
learns `logger.warn("a specific message") -> logger.warning("a specific message")` as a rule that
**bakes the example's string constant into the pattern**, so it matches only that one message. The
alias exemption never fires, because the rule is not a bare rename — it carries a constant.

`automagician#55` is the case, and it shows both ways this bites:

* its target `test/test_database.py` does not contain `logger.warn(` at all, so refusing is correct
  there and no operator helps;
* but the same example also rewrites the message text (`deperciated` -> `deprecated`), so it is a
  *tangled* demonstration — the tree's documented class — and no amount of call-shape work recovers
  the sites it does contain.

So the honest statement is narrower than "the alias operator is done": **a kept alias is exempt only
when the example shows the rename and nothing else.** When the example also changes a constant
inside the call, the rule is about that constant, and the alias exemption correctly stays out of it.
That is a real limit, it is now named, and it is the reason five askings remain rather than zero.
