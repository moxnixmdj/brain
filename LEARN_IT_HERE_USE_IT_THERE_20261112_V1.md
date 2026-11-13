# Learn it here, use it there: what cross-environment transfer actually costs

**2026-11-12.** Authority **NONE** — producer-run, `$0`, zero model calls, `truth.achieved` stays
`false`, no capability registered, no family flipped.

The owner's plan, in the exact words it keeps being given in:

> "just give our model a try in all those new coding environments ... after he does them at least
> once, he would learn all of those permanently ... We can also use this to do anything on a computer
> just once and he learns all of this also permanently."

That is a claim about **new environments**, and until this round every measurement in this tree taught
and applied *inside one pull request* — choosing the demonstration and the target from the same
repository. That is the easiest case that exists. This round measured the claim as made.

---

## 1. What was measured

12 merged pull requests covering **6 kinds of change × 2 repositories each**, chosen so that the kind
of change is held fixed and the repository is not:

| kind of change | repository A | repository B |
|---|---|---|
| an old name of a test method | openimis/openimis-be-core_py#414 | scoursen/django-softdelete#114 |
| a thread method renamed | CCSI-Toolset/FOQUS#1002 | avocado-framework/avocado-vt#2887 |
| an old name of a logging method | FZJ-IEK3-VSA/ActivityAssure#2 | cta-observatory/pyirf#289 |
| an old name of a test method, second | Azure/azure-cli-extensions#8010 | torproject/stem#155 |
| text put together another way | jodal/comics#652 | wolfSSL/wolfcrypt-py#120 |
| a library taken out | learning-unlimited/django-argcache#5 | ArduPilot/MAVProxy#1623 |

The lesson is learned from **only** repository A's changed files and applied to **only** repository
B's. Repository B contributes no demonstration at all. 176 askings, every changed file of A used as
*the* demonstration in turn.

## 2. The result, and why the mean is not it

| arm | coverage of the people's work | changes made | right | **wrong** | precision |
|---|---:|---:|---:|---:|---:|
| literal (the changed text must already be there) | 0.004 | 4 | 4 | 0 | 1.000 |
| **the shipped learner, one demonstration in a new repo** | **0.573** | 30 | 562 | **0** | **1.000** |
| the shipped learner, three demonstrations | **0.845** | 53 | 828 | **0** | **1.000** |
| every rung of the ladder, widest first | 0.030 | 39 | 29 | **71** | 0.290 |

That 0.573 looks like a headline. **It is not, and this is the most important table in this document:**

| kind of change | one demonstration | three demonstrations |
|---|---:|---:|
| an old name of a test method | 537 right (0.706) | 757 right (**0.995**) |
| a thread method renamed | 15 right (0.349) | 43 right (**1.000**) |
| an old name of a test method, second | 10 right (0.147) | 28 right (0.412) |
| **an old name of a logging method** | **0** | **0** |
| **text put together another way** | **0** | **0** |
| **a library taken out** | **0** | **0** |

**537 of the 562 correct changes come from one kind of change.** Half the kinds transfer perfectly,
three transfer *exactly nothing*, and **three demonstrations do not move the ones that fail.**

## 3. Where the wall is, in the learner's own words

The three stuck kinds refuse every single asking, and the reason is the same sentence each time:

```
refused: nothing in the file has the form the example changed (logging.warn -> logging.warning)
refused: nothing in the file has the form the example changed (... % pub_date)
refused: the two example files hold the same code, apart from import lines that were added or removed
```

This is the cleanest statement of Problem 2 this tree has produced:

> **The unit of generalisation is the *form* of a change, not the kind of a change, and forms do not
> travel between codebases.**

`logging.warn → logging.warning` is one kind of change and two different forms: a call with
`self.serialize(...)` under it in one project, a bare statement in another. The narrow learner's rule
is pinned to *the expression it was shown*, so it finds nothing to do in the second repository and
refuses. That refusal is **correct and safe** — zero wrong changes — but it means "learn it once in a
new environment" is not achievable by showing the learner a codebase.

## 4. It is not the check, and this is the part the previous round got wrong

The last round on this question concluded:

> "What is missing is standing up a project's checks — its dependencies and its test entry point — for
> each new environment."

Its own record says that step recovers nothing. `GENERALIZATION_RUNG_GRADIENT_20261112_V1.json`
gates the wide rung by the project's tests and gets **`share_of_the_work: 0.000`** — 132 checks asked,
**0** edits accepted, because the wide rung covers 4.8% of the work and is 45% wrong, so an oracle can
only delete it. The arm that carries the coverage (`exact`) reports **`check_asked: 0`** and
**`wrong: 0`**. A check converts a wrong change into a refusal; on the arm that matters there is no
wrong change to convert.

So dependency installation is real, expensive, worth building — and **not this round's rate limit.**
A check cannot create a form the learner does not have.

## 5. What this means for the plan, claim by claim

| the owner's claim | verdict, measured |
|---|---|
| exact recall is solved | **TRUE**, precision 1.000, 0 wrong in every arm this round |
| one showing generalises | **TRUE within a repository** (0.529 → 0.548 reproduced here), and safe |
| "a try in new coding environments" teaches it | **HALF TRUE.** 3 of 6 kinds transfer at up to 0.995 with zero errors; 3 of 6 at exactly 0.000 |
| more demonstrations fix the failures | **FALSE.** 3 showings lift the working kinds to ~1.0 and leave the broken ones at 0 |
| a check in each new environment is the missing piece | **FALSE as the next step.** It was measured at 0.000 and cannot manufacture an absent form |
| so we can do anything on a computer once and keep it | **FALSE.** Nothing here executed a computer action; and for coding, the half that fails is the half with unfamiliar forms |
| sentient creature | nothing in this round measures it, and this round is about forms, not feeling |

## 6. The smartest next action, with the alternatives killed first

**Killed on this round's own evidence:** show more demonstrations (0.000 → 0.000 on three kinds);
widen the ladder (0.290 precision, 71 wrong changes); install dependencies (0.000 coverage upstream);
give it a bigger action library (the library grows in the direction the wide rung already fails).

The one lever the data points at, stated as a falsifiable mechanism rather than a wish:

> **Learn the *operator* that carries a form across binders, not the form.** The three stuck kinds fail
> for three different reasons that are all the same problem one level down:
> a *name* (`logging.warn`) is the same token in both repositories and should transfer;
> an *f-string* needs the surrounding binder re-derived, which is a shape operation;
> an *import removal* is refused by the learner's own rule.
> Each is one operator. The tree has already priced one: a reducer for a word problem cost **one
> lesson, two files, about ten lines of code**, and then answered 5 of 5 held-out instances.

The measurement that would settle it, and it is cheap: add the **name-kind operator** only (rename a
qualified name everywhere it is called, independent of the arguments under it), then re-run this exact
tool on these exact 12 pairs. If the logging kind moves off zero, the wall is per-kind operators and
they are worth buying one at a time. If it does not, the wall is that the target's *use sites* are not
recognisable from the demonstration at all, and the next question is about retrieval, not operators.

Until that run exists, the honest statement of the plan is: **the mechanism is real, precise, and
carries about half the work inside a codebase; across codebases it carries the half whose change has a
travel-able form and refuses the rest — safely — and no amount of showing it more of either fixes the
other half.**

## 7. Receipts

```
python3 canonical/tools/across_environments_v1.py --collect /tmp/pulls_gx.json --from-record /tmp/pulls_g.json
python3 canonical/tools/across_environments_v1.py --pulls /tmp/pulls_gx.json \
    --out canonical/verification/ACROSS_ENVIRONMENTS_20261112_V1.json
```

`canonical/tests/test_across_environments_v1.py` — **17 tests**. Record:
`canonical/verification/ACROSS_ENVIRONMENTS_20261112_V1.json`.

## 8. What this round got wrong

1. **`three_showings` was passed only `demonstrations[0]`**, making it byte-identical to `exact` and
   producing a "P3 failed" that was a property of my code, not of transfer. Caught by noticing that
   two arms produced *identical* totals, which is never true of two different arms. Fixed, and pinned
   by `test_three_showings_really_shows_three`.
2. **Both arms used only the teacher's first changed file**, so the figure depended on which file the
   corpus happened to list first. Fixed to average over demonstrations, as the recorded 0.529 did.
3. **Refusals were truncated at the first colon**, so the record collapsed 96 distinct sentences into
   the word "refused" — the record could not explain itself. The sentences are what named the wall in
   §3. Fixed and pinned.
4. **P1 failed and is recorded as failed.** I predicted cross-repository transfer would be *worse*
   than within-repository. It was slightly *better* (0.573 vs 0.548). The reason is not that transfer
   is easy: it is that the cross-repository pairs dropped one hard kind of change relative to the
   within-repository task set. **The prediction was wrong for a reason that does not rescue the plan**,
   and both numbers are printed so that neither can be quoted alone.
5. **My first shipped record contained the pre-fix refusals**, because I edited the tool after
   generating the record and did not regenerate it. The tests caught it; the record was rebuilt.
