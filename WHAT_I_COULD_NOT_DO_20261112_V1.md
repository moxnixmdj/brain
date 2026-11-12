# What I could not do, and the predictor that turned out backwards

**2026-11-12.** Authority **NONE**. `truth.achieved` = `false`.

Two things happened this pass. I could not run the experiment I said was the smartest next
move, and I have to say so plainly. And while checking whether I could, I found that the
explanation everyone would reach for is measurably wrong.

---

## 1. The re-run is blocked, and I am not going to fake it

Last pass I said: *extend the hand and re-measure on fresh seeds.* First question this pass was
whether that can happen here at all.

```
  re-run on fresh seeds here: BLOCKED
    NO_BROWSER_BINARY
    MISSING_SHARED_LIBRARIES: libnspr4.so, libnss3.so
    NO_ROOT_TO_INSTALL_THEM
```

What I did get working and then lost:

```
  npm install puppeteer-core @sparticuz/chromium   -> ok
  await chromium.executablePath()                  -> /tmp/chromium
  launch                                           -> "error while loading shared libraries: libnspr4.so"
  apt-get install libnspr4 ...                     -> "Could not open lock file ... are you root?"
```

The chromium bridge presses at element boxes, so drag, hit-testing and scroll **need real
layout**. The jsdom substrate has none, and the run's own `not_done` says the open failures are
exactly drag-to-a-point, inner scrolling and multi-drag. Measuring those without a browser would
be measuring my own simulator, which is the failure I have spent six passes documenting.

So `feasibility()` is now part of the record. **A blocked re-run is not a re-run**, and the tool
that reports the ladder may not be cited as freshly confirmed. The last thing this project needs
is a seventh pass in which an unmeasured thing is described as measured.

## 2. The predictor I expected, and the one that is real

The recorded run stores, for every step of every learned skill, `descriptions_left`: how many
element descriptions are still consistent with the single demonstration it saw.

The intuitive story writes itself: **a demonstration that leaves 200 descriptions open should
transfer worse than one that leaves 2.** I expected to confirm it and then target it.

On the 78 pages that have a learned skill with recorded steps:

```
  median descriptions still open per step      50  (range 2 .. 192)
  openness ~ success                           r = +0.175
  least open third: success 0.608
  most  open third: success 0.840
```

**The wrong sign.** More open, better result. Controlling for how hard the first success was to
find, the effect collapses:

```
  openness ~ success, controlling for cost     r = +0.116
  first-success cost ~ success                 r = -0.214
  VERDICT: NO_EFFECT
```

### Why, mechanistically

Loose descriptions cluster on **one-step natural-language** pages, where the version space
searches the loose wording and finds the target anyway:

| page | descriptions open | success |
|---|---|---|
| click-collapsible-2 | 192 | 1.00 |
| click-dialog | 162 | 1.00 |
| unicode-test | 135 | 1.00 |
| drag-items-grid | 22 | **0.00** |
| phone-book | 21 | **0.10** |

The tight ones are multi-step spatial tasks where nothing works, so the *openness* was never the
cause — it was a marker of task type. And the predictor that does survive is blunt and load-
bearing: **whether a demonstration could be found at all.** 52 of 130 pages produced no first
success, and among those that did, the harder the first success was to find, the worse the
skill transferred.

## 3. Why this matters more than it looks

If I had asserted the intuitive story — and I was one paragraph away from doing it — the next
pass would have spent its time building a "reduce ambiguity" mechanism. That is not the
bottleneck. The bottleneck is that **the hand cannot do enough to produce a demonstration in the
first place**, which is what the run's own `not_done` says and what `r = -0.21` on cost
measures.

The general lesson, which is now the fourth time this session has produced it: **the thing that
looks like a property of the learned artifact keeps turning out to be a property of the
environment that produced it.** Ambiguity was task type. `verified_hits` was caller approvals.
67 receipts were unlocatable programs. A failed transfer was an uninstalled parser.

## 4. What I shipped

`canonical/tools/what_a_demonstration_leaves_open_v1.py`

- reads the newest recorded run and joins `descriptions_left` to per-page success;
- computes the raw correlation **and the partial correlation controlling for first-success
  cost**, and returns `CONFOUNDED_BY_FIRST_SUCCESS_COST` / `NO_EFFECT` / `SURVIVES_THE_CONFOUND`
  as a verdict rather than leaving the reader to eyeball two numbers;
- `feasibility()` reports whether a fresh-seed re-run is possible *in this environment*, naming
  the missing pieces;
- refuses to describe a blocked re-run as a confirmation.

16 tests, including `test_the_judge_names_the_confound_instead_of_hiding_it` and
`test_this_environment_reports_blocked_with_a_reason`, so the sandbox's own limitation is pinned
rather than remembered.

It is the 9th layer of `auditability_report_v1` and the only one that reports a **rejected
explanation**.

---

## Answers, stated plainly

**Is one demonstration enough to learn something permanently?** No — 0 of the generalising tasks
survive an instruction change, and practice is still worth +8.5 points. Unchanged from last pass.

**Is the transfer real?** Yes, 65.5% vs 14.0% on unseen instances. Unchanged.

**What actually limits it?** Not ambiguity of the demonstration — measured and rejected. **The
reach of the hand**, which decides whether a demonstration exists at all: no first success on 52
of 130 pages, and success falls as the cost of finding the first success rises.

**What is the smartest thing to do, given I cannot re-run here?** One of two, in this order:

1. **Get a browser into the lane.** The measurement is the product; right now the only runs on
   file were produced somewhere else. A container with chromium plus the 130 pages turns every
   future claim here into something re-runnable, and it is an afternoon of work, not a research
   program.
2. **Then, and only then, extend the hand** — drag-to-a-point, inner scroll, drag sequences,
   multi-word typing — and re-measure the same board on fresh seeds. That is a pre-registered
   number against a known baseline, which is more than any other option on the table.

Anything else I could do here — another gate, another document, another correlation on the same
78 rows — cannot change what this system can do.
