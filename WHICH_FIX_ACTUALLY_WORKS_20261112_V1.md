# Which fix actually works

**2026-11-12.** Base `8238d637`. Branch `arena/4ec3698d-brain`. Answers Problem 2:
*similar task → adapt the knowledge.* Measurement only; **no learner was changed.**

**The short version.** The tree's ranked roadmap of next operators is ordered by *how often a
refusal is asked*. Priced against the corpus score, that order is wrong twice over: the 60-asking
class buys **0.00 pp**, and the class with the biggest headline gain **breaks files**. The cheapest
genuine win is not the biggest refusal class — it is a rename, and it improves both metrics while
adding no wrong change.

---

## 1. What was asked, and what I refused to assume

§8 of `ONE_TRY_COVERS_A_FRACTION_20261112_V1.md` ranks the next operators by asking count:
import-only (60) → call-shape (50) → block-shape (34) → names (22). The counts are honest and the
classes are real. What nobody had done is what this tree's own law demands:

> A census finds symptoms; only a counterfactual finds causes. A blocker is not the first obstacle.
> It is the obstacle whose removal makes the thing work.

So the counterfactual was built first. It touches no organ and changes no number: for each class it
removes exactly that refusal and replays the same one-example askings on the same 89 files of other
people's code, then reports the corpus score rather than the class's own hit rate.

## 2. Finding one: the roadmap counted targets, not opportunities

An "asking" is one example times the other files in the same pull request — usually five. So
"60 askings for import-only" is **12 examples**, each seen five times, and those 12 examples are the
ones the organ **cannot read at all**. Their refusal happens at *learn* time, not apply time.

| class | askings | example itself unreadable | askings an operator can reach |
|---|---|---|---|
| `IMPORT_ONLY_EXAMPLE` | 60 | **60** | **0** |
| `CALL_SHAPE_NOT_SHOWN` | 50 | 0 | 50 |
| `NAME_NOT_AVAILABLE` | 22 | 0 | 22 |
| `BLOCK_SHAPE` | 25 | **25** | **0** |
| `CONFLICTING_CONTEXT` | 15 | **15** | **0** |

Three of the five roadmapped classes are **not operator problems**. No apply-time operator can reach
them, because there is no rule to apply — the demonstration never became one. This is the same
distinction the document already draws everywhere else: *the prior generalises; the example only
selects.* If the algebra cannot express the example, the example teaches nothing, and no amount of
applying makes it teach. `IMPORT_ONLY_EXAMPLE` and `BLOCK_SHAPE` need the **algebra** extended — a
research step, not an operator — and they should not sit at the top of an operator queue.

## 3. Finding two: the ceiling, so no gain can be oversold

The marker that says "this is the demonstrated kind of change" is known for **5 of the 15** pull
requests (the recorded `KINDS` table names a search phrase and a code marker; ten pulls' phrases are
not in it). So the ceiling is stated both ways:

* On the 5 pull requests whose kind is known: **342 of 411** non-import changes sit on a statement
  carrying the demonstrated marker = **83.2%**. That is the best any perfect learner of that kind
  can do there.
* Across all 15: **342 of 1,287 = 26.6%**, because for the other ten pulls the kind cannot be named
  and must be credited zero.

**A perfect learner of exactly the demonstrated kind tops out at 26.6% of the corpus score.** Every
figure below is read against that. Any claim of "half the work from one example" is a claim the
corpus cannot produce.

## 4. Finding three: the four arms, measured

Both scorings are reported because **they disagree in sign**, and quoting one while arguing about
the other is a mistake this tree has already caught once. `strict` counts statements and cannot
credit an import-only change; `marker` counts the per-question answer. Both rest on the same 330
askings from readable examples; the marker columns rest on the 115 askings in the five pulls whose
kind is known, and say nothing about the other ten.

| arm | strict coverage | strict precision | marker same | wrong changes |
|---|---|---|---|---|
| baseline (the organ as it is on `main`) | 0.2082 | 0.9241 | 0.2836 | 14 |
| **call-shape rename** | **0.2300** | **0.9308** | **0.3596** | **14** |
| extend the import the file already has | 0.1305 | 0.8038 | 0.0000 | 41 |
| both, stacked | 0.3131 | 0.8956 | 0.3596 | 47 |

*The refusal-class table in §2 uses a denominator of 1,287 — every target, including those reached
only through an unreadable example — which is why its baseline reads 0.1601. The arms exclude
unreadable examples, so they read 0.2082. Both are in the record. Neither is the wrong one, and
mixing them is how a 5-point gain gets invented.*

**The rename is the only arm that costs nothing.** Strict coverage, strict precision and the marker
share all rise, and wrong changes stay at **14 — exactly the baseline's**. It changes the callee and
leaves every argument alone, so the organ's existing gate is enough to keep it honest.

**Naming the missing name is the trap, and it is the most dangerous one because it has the biggest
number.** It wins the largest single-class gain (**+6.39 pp**) — and loses precision from 0.9241 to
0.8038, adds 41 wrong changes, and drives the marker share to **zero**. The mechanism was worth
finding: the name is missing because the target file genuinely did not have it, so supplying it from
the lesson's own imports is a guess about *this* file. Ranking this class first, which is what
"ranked by askings" does, would have shipped a precision regression dressed as a coverage win.

The stacked arm confirms the trade: +10.5 pp coverage for 47 wrong changes, three times baseline.

## 5. What this changes about the route

**Old order** (§8, by asking count): import-only → call-shape → block-shape → names.

**New order, by measured gain on the scored quantity:**

1. **Call-shape rename** — the only cheap, clearly-positive move: 50 reachable askings, +1.67 pp
   strict, +6.38 pp marker, zero new wrong changes, precision up. Its real price is the **signature
   check**: a rename must confirm the new callee accepts the call, and that resolution is not in the
   record. So every number above is an **upper bound** and the operator must carry the check or it
   will break call sites silently.
2. **Naming a name — buy the mechanism, never the class.** All 22 askings are one shape: the file
   already imports from that module and must have its **existing import line extended**, exactly as
   the people did. That is checkable with no oracle. Bringing a name the file never imported is
   where the precision went and is not admissible. This operator must never be ranked by its raw
   6.39 pp.
3. **Nothing else, until the algebra grows.** Import-only and block-shape are learn-time problems;
   the second demonstration does not touch them either, since it only helps where a rule exists and
   ties. Extending the algebra is a real research step.

Ordering by measured gain instead of asking count reverses steps 1 and 2 and **deletes** steps 3 and
4 from the operator queue. That is the whole answer to "the fastest way".

## 6. What is real and what is not

* **Real:** the refusal classes; the split between learn-time and apply-time refusals; the 26.6%
  ceiling; the precision collapse from naming names; the rename being free. All in the record, all
  pinned by tests.
* **Real, and new:** three of the five roadmapped classes are unreadable-example problems, so the
  roadmap was **mis-priced at the top**, and the biggest single-class gain is a trap.
* **Not real yet:** the rename operator itself. What is measured is its *ceiling*, using the organ's
  own gate with unshown uses left alone. It still needs the signature check before being switched on.
* **Weak, and labelled:** every marker figure rests on 5 of 15 pull requests. They are direction,
  not a distribution.
* **Not claimed:** that Problem 2 is solved. One demonstration tops out at 26.6% however well it is
  applied. What is now known is where the other 73% lives: in examples the algebra cannot read, and
  in changes the demonstrated kind does not name. That is a priced boundary, not an unknown.

## 7. Receipts, and one caveat about the organ

```
python3 canonical/tools/which_fix_moves_generalization_v1.py --pulls /tmp/pulls_v3.json \
        --out canonical/verification/WHICH_FIX_MOVES_GENERALIZATION_20261112_V1.json
pytest -q canonical/tests/test_which_fix_moves_generalization_v1.py   14 passed
corpus: 15 pull requests, 89 files, refetched and hash-verified against the recorded record
model_calls 0, incremental_spend_usd 0, terminal_authority false
```

**Caveat, stated rather than hidden:** the organ on `main` is **`0cca78be`**, not the `0dc8ff2f`
the record was generated with — it was changed by PR #6784 before this measurement. On the current
organ the histogram is `NO_FORM 168, EDITED 90, IMPORT 60, CALL_SHAPE 50, BLOCK 25, NAME 22,
CONFLICT 15, OTHER 10` against the record's `162, 87, 60, 50, 34, 22, 15, 10`. Nine block-shape
refusals became "nothing in the file has the form" and three refusals became edits. The ranking in
§5 is unchanged by that shift, and the record carries `code_sha256` for the organ, both scorers and
the tool so any movement is visible.

Nothing was widened, no tolerance relaxed, `truth.achieved` untouched.
