# Which demonstration you give is a decision; the tree has never separated it from the lottery around it

**2026-11-12.** Branch `arena/b8e07941-brain`, base `b52af360`. Authority **NONE** — producer-run
sandbox measurement, `$0`, zero model calls in every result-bearing path, `truth.achieved` stays
`false`, no capability registered, no family flipped.

The owner asked again: *"Why can't we just give our model the most advanced coding actions and let
him experience them once and then he will learn them? After we do this we have the most advanced
coding agent on the planet."* Then: *"give it the smartest actions."*

Nine documents on `main` answer the **count** half of that, and they answer it correctly: one
showing is literal, two showings generalise, a demonstration is a point and not a specification.
This round is about the word **smartest**, which none of them measured, and which turns out to have
a real mechanism behind it and a real ceiling above it.

---

## 1. The thing nobody had asked

The recorded run `REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json` already contained the answer, in a
column nobody read. For each of 15 merged pull requests, every changed file was used in turn as *the*
demonstration and every other file was the work to do. Read the per-file rows and this is what the
same change, on the same task, recovers depending only on **which file was shown**:

```
openimis/openimis-be-core_py#414   [0.00, 0.00, 0.81, 1.00, 1.00, 0.00]   spread 1.00
torproject/stem#155                [0.89, 0.89, 1.00, 0.86, 0.88, 0.89]  spread 0.14
Cytomine-ULiege/...-client#61      [0.92, 0.00, 0.00, 1.00, 0.92, 0.92]   spread 1.00
apache/libcloud#2217               [0.80, 0.00, 0.00, 0.00, 0.80, 0.80]   spread 0.80
```

Median spread across the 15 tasks **0.14**, maximum **1.00**, and in **10 of 15** tasks the choice
changes the outcome at all. The entire "one showing" debate was conducted about tasks where the
demonstration was chosen arbitrarily.

## 2. The decision, made from data available before any outcome

In the real setting there is nothing to compare against — the other files have not been changed yet
— so the only information at choice time is the candidates themselves. One number can be computed
there: **reach**, how many of the other candidate files a candidate's own lesson actually fits, using
the shipped learner's own matcher and no outcome.

| | strict arm (whole file or nothing) | ceiling arm (every try kept) |
|---|---|---|
| correlation of reach with recovered share | **r = 0.88** (n=89) | **r = 0.66** (n=89) |
| changes recovered, choosing by reach | 80 | 103 |
| changes recovered, choosing the best possible | 119 | 141 |
| changes recovered, choosing the worst possible | 0 | 15 |
| of 1674 changes the people made | | |
| largest-file baseline (no reasoning) | 0.344 of best | 0.530 of best |

Both pre-registered predictions held on both arms — written in the tool's docstring before the run,
with the tool's own `prediction_held` field reporting `all(...)` over the two conjuncts separately.

## 3. The correction this round is really about

The first version of this measurement reported "captures 86–91% of the best possible choice". **That
number was partly luck, and the spread between 86% and 91% was entirely luck.**

The choice rule has two parts and only one is a decision. `reach` separates the candidates, and it is
data. The tie-break inside a group — fewest blanks, then the file's path — is **not** data: the path
is whatever `gh` happened to call the file. On these 15 tasks the greatest reach is taken by
**several** candidates in **7 of 10** differing tasks, so the tie-break was doing most of the work,
and four candidate tie-breaks were measured against each other:

```
                                                    strict    ceiling
fewest blanks / path order (current)                0.860     0.911
largest file first                                  0.807     0.899
smallest file first                                 0.749     0.870
fewest rules first                                  0.703     0.842
```

Nothing beats path order, including the specificity rule the tool's own docstring claimed would.
That is the evidence that **a better ordering of the same candidates is not the next lever.**

So the honest reading is now reported next to the flattering one, per task:

| | strict | ceiling |
|---|---|---|
| tasks where the greatest reach is **unique** — the rule really decided | 3 | 3 |
| capture there | **1.00** | **0.95** |
| tasks where the greatest reach is **tied** — the rule did not decide | 7 | 7 |
| honest expectation there (the tie's mean, not its best) | 0.73 | 0.85 |
| honest capture over all differing tasks | 0.81 | 0.88 |
| the path-tie-broken figure, not earned | 0.86 | 0.91 |

**Where the rule decides, it is right every time. Where it is silent, a coin is still being flipped,
and the honest number for those tasks is the coin's average, not its best face.**

## 4. What this says about the owner's plan, precisely

* **"Give it the smartest actions and it learns them"** — the action was never the bottleneck. This
  measures the choice of *example*, and the choice is worth up to 100 percentage points within one
  task. Choosing well is free: it needs no extra demonstration, no extra model, and no new learner.
  It is one scoring rule over the candidates the environment already contains.
* **"Once and permanently"** — unchanged by this round, and the count answer stands. Reach is not a
  substitute for a second showing; it is what you compute when you have decided to give only one.
* **"So we have the most advanced coding agent on the planet"** — no. This is 15 tasks of one kind of
  change, agreement with other people, and no test of any of the 15 projects was run. Agreement is
  not correctness, and the strict arm's 0.81 is what happens with **no** check at all.
* **Sentient creature** — nothing here measures it, and the closest proxy this round produces is a
  system that knows *which of the things it could be shown would teach it the most*. That is a real
  self-model of its own ignorance, and it is silent on 7 of 10 tasks. Both halves of that sentence
  are the point.

## 5. Reproduce

```
python3 canonical/tools/repeated_change_one_example_measure_v1.py \
    --collect /tmp/pulls_v2.json \
    --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json   # 58 s, hashes checked

python3 canonical/tools/demonstration_choice_measure_v1.py --pulls /tmp/pulls_v2.json \
    --arm strict --out canonical/verification/DEMONSTRATION_CHOICE_STRICT_20261112_V1.json
python3 canonical/tools/demonstration_choice_measure_v1.py --pulls /tmp/pulls_v2.json \
    --arm every_try_kept --out canonical/verification/DEMONSTRATION_CHOICE_CEILING_20261112_V1.json
```

`.github/workflows/repo-integrity-guard.yml` PASS (17 rules, 0 violations); orientation `verify` ok;
load-bearing admission PASS; `canonical/tests/test_demonstration_choice_measure_v1.py` **14 passed**.

## 6. Instrument honesty, including where this round was wrong

1. **My first run used the wrong arm.** The recorded run 6 is the *ceiling* arm; I ran the strict arm
   and got `stem#155` at 0.00 against the record's 0.89. The corpus was not wrong and the learner was
   not wrong: I had called a different entry point. Before any new number was trusted, the tool was
   required to reproduce the recorded run — **16 of 17 candidate rows exact**. The one difference is
   a later fix to the learner on `main` (`#6749`), named rather than absorbed.
2. **The learner changed under the measurement**, as it did during the original run: today's file is
   `1c1141dd…`, the record's is `0dc8ff2f…`. Both records carry the organ's sha256 so the drift is
   visible.
3. **The reported capture changed after the pilot failed.** The pilot (3 tasks, strict arm) failed the
   80% conjunct. Switching arms afterwards is legitimate only because the ceiling arm is the arm the
   recorded run used and the reason is stated; both arms are now reported so the choice cannot be
   used to pick a winner.
4. **A "perfect" 86% was reported and then demoted in the same session**, because the tie-break that
   produced it is not data. The demotion and the four tie-breaks that failed to beat it are in §3.
5. **A two-file fixture could not show a tie with different outcomes**; that test now runs against
   the recorded corpus and skips, loudly, when the case is absent.

## 7. What is next, ranked by measured value

1. **A tie-break that is data**: ask for a second probe demonstration chosen by the same version-space
   logic `select_probe` already implements — which of the tied candidates, if shown, would separate
   them fastest. This is the only lever the four failed tie-breaks point at.
2. **Run the projects' own tests** after each repeated change, which converts agreement with people
   into correctness and would cost minutes per candidate. Without it, every number above is a proxy.
3. **Report the strict arm as the default number.** The ceiling arm assumes a check settles every try;
   with no check at all the honest figure is 0.81, not 0.88.
