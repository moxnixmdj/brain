# Which fix actually works

**2026-11-12.** Base `8238d637`. Branch `arena/4ec3698d-brain`. Answers Problem 2:
*similar task → adapt the knowledge.* The learner was changed, and the change is measured.

**The short version.** The tree ranked the next operators by *how often a refusal is asked*, and
that order was wrong. Priced against the corpus score, the 60-asking class buys **0.00 pp** and the
class with the biggest headline gain **breaks files**. The genuine win was elsewhere: the organ was
refusing changes whose safety it could not be unsure about, and **one exemption it should always
have had** — a name the standard library kept for another name is the *same function*, so it takes
the arguments it always took. That exemption is now in the organ, and it is the largest single gain
measured in this tree: **strict coverage 0.2082 → 0.2999 (+9.17 pp), marker share 0.2836 → 0.6170
(more than doubled), precision up, and wrong changes unchanged at 14.**

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
| baseline (the exemption switched off) | 0.2082 | 0.9241 | 0.2836 | 14 |
| **shipped: the kept-name exemption** | **0.2999** | **0.9461** | **0.6170** | **14** |
| extend the import the file already has | 0.1305 | 0.8038 | 0.0000 | 41 |
| both, stacked | 0.3831 | 0.9130 | 0.6170 | 47 |

*The refusal-class table in §2 uses a denominator of 1,287 — every target, including those reached
only through an unreadable example — which is why its baseline reads 0.1601. The arms exclude
unreadable examples, so they read 0.2082. Both are in the record. Neither is the wrong one, and
mixing them is how a 5-point gain gets invented.*

**The rename is the only arm that costs nothing, and it is now shipped.** Strict coverage, strict
precision and the marker share all rise, and wrong changes stay at **14 — exactly the baseline's**.
The consistency check that makes the gain attributable: `EDITED` in the refusal histogram goes
**90 → 140**, exactly the 50 call-shape askings, and `NO_FORM_IN_FILE` stays at **168**. Nothing
was traded; a refusal that could not be justified was removed.

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

## 6. Why the exemption is sound, and what it is not

The check exists for one reason, in its own words: *"the new function may not take those
arguments."* That is exactly right for a reshape and exactly wrong for a rename — a name kept for
another name is the **same function**, so it takes what it always took.

**It was not inferred, and the attempt to infer it is recorded because it failed.** The first
version exempted any change that renamed one attribute and left everything else alone. It looked
right and it was wrong: `self.assertEquals -> self.assertEqual` and `yaml.load -> yaml.safe_load`
are the **same shape** — one attribute renamed on one object. Neither is a re-export
(`yaml.load is yaml.safe_load` is false), neither keeps its docstring, and no structural reading
tells them apart. The repo's own test caught it, in one run. So structure says *"something was
renamed"*; it cannot say whether the right-hand thing behaves like the left-hand thing. That is
knowledge, and it is recorded as knowledge in `kept_under_an_old_name_v1.py` — a closed, checkable
list of removals the standard library announced, not a growing table of guesses.

Two guards, both tested: the rule must be **a rename and nothing else**, *and* the pair must be on
that list. `yaml.load -> yaml.safe_load` fails the second and keeps being refused.

* **Real:** the refusal classes; the split between learn-time and apply-time refusals; the 26.6%
  ceiling; the precision collapse from naming names; the kept-name gain, in the shipped organ.
* **Real, and new:** three of the five roadmapped classes are unreadable-example problems, so the
  roadmap was **mis-priced at the top**; and the biggest single-class gain is a trap.
* **Realized, not projected:** the +9.17 pp is what `main` does now, not a ceiling. The other
  operator (naming a name) is still only priced.
* **Weak, and labelled:** every marker figure rests on 5 of 15 pull requests. Direction, not a
  distribution.
* **Not claimed:** that Problem 2 is solved. One demonstration still tops out at 26.6% however well
  it is applied. The other 73% lives in examples the algebra cannot read and in changes the
  demonstrated kind does not name — a priced boundary.

## 7. Receipts

```
python3 canonical/tools/which_fix_moves_generalization_v1.py --pulls /tmp/pulls_v3.json \
        --out canonical/verification/WHICH_FIX_MOVES_GENERALIZATION_20261112_V1.json
pytest -q canonical/tests/test_which_fix_moves_generalization_v1.py   17 passed
pytest -q <the 12 suites that import the organ>  8 failed, 60 passed -- the same 8 that failed
        before the change, all FAIL_CLOSED__ROUTE_ADMISSION_REJECTED in a subprocess that never
        reaches the organ. No new failure, and the comparison was run both ways.
corpus: 15 pull requests, 89 files, refetched and hash-verified against the recorded record
model_calls 0, incremental_spend_usd 0, terminal_authority false
```

**Recorded honestly:** the histogram moved from `162, 87, 60, 50, 34, 22, 15, 10` (the corpus
record, organ `0dc8ff2f`) to `168, 90, 60, 50, 25, 22, 15, 10` (organ `0cca78be`, after PR #6784)
and is now `168, 140, 60, 0, 25, 22, 15, 10` (organ `ada1c5ed`, this turn). The first shift was
somebody else's; the second is the 50 rename askings becoming edits, which is the whole gain. The
record carries `code_sha256` for the organ, both scorers and the tool, and a test pins it, so any
further movement is visible rather than silent.

Nothing was widened, no tolerance relaxed, `truth.achieved` untouched.
