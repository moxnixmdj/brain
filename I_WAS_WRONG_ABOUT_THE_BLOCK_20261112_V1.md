# I was wrong about the block. The lane was open, and the result replicates.

**2026-11-12.** Authority **NONE** (producer-run measurement in this sandbox). `truth.achieved` = `false`.

Last pass I reported the re-run as impossible — `NO_BROWSER_BINARY`, `MISSING_SHARED_LIBRARIES`,
`NO_ROOT_TO_INSTALL_THEM` — and put a `feasibility()` in the repository that says so. All three
observations were true. **The conclusion was false, and the tool is now wrong on `main`.** This
pass corrects it and runs the measurement.

---

## 1. What I got wrong

I checked for a system chromium binary. There isn't one. I checked for `libnspr4.so`. Absent. I
concluded: needs root.

What I did not check: the package I had already installed ships the libraries.

```
node_modules/@sparticuz/chromium/bin/al2023.tar.br
  -> decompress -> lib/libnspr4.so, libnss3.so, libnssutil3.so, libfreebl3.so,
                   libsoftokn3.so, libplc4.so, libplds4.so, libexpat.so.1, libfreeblpriv3.so
```

And `miniwob_chromium_bridge_v1.mjs:377-381` already inflates that archive and sets
`LD_LIBRARY_PATH` itself:

```python
const libs = path.join(await chromium.inflate(path.join(bin, 'al2023.tar.br')), 'lib');
LD_LIBRARY_PATH: [libs, os.tmpdir(), process.env.LD_LIBRARY_PATH || ''].filter(Boolean).join(':')
```

I tested *my own launch script* and reported the bridge blocked. The bridge never had the problem.

**This is the fifth time in this session the same defect has appeared**, and every time it has
been mine: a check that inspects its subject instead of exercising it reports a false negative.
`verified_hits` counted approvals. Receipts named programs nobody resolved. A refuted rule kept
firing. An uninstalled parser looked like a failed learner. And now a feasibility probe that
looked for a browser instead of loading a page.

So `feasibility()` no longer inspects anything. It **runs the bridge** and asks whether a page
loaded:

```
{'can_rerun_on_fresh_seeds': True, 'status': 'RUNNABLE', 'blocked_by': [],
 'probe': {'loaded': True, 'browser': 'HeadlessChrome/153.0.8010.0'}}
```

## 2. The measurement, on instances that did not exist before

Seeds **1080–1089**. Runs 3 and 4 used 1000–1039, run 5 used 1060–1079, the pilot used
1040–1059. Nobody had scored these. 50 pages (the first 50 by name), 10 instances each, real
mouse, the page's full reward the only judge, `HeadlessChrome/153.0.8010.0` — the same build as
the recorded run. 33 of 50 pages produced a first success.

Where replaying the demonstration is not enough:

| arm | fresh seeds 1080–1089 | recorded V5 (1060–1079) | delta |
|---|---|---|---|
| **version_space** (ONE success) | **0.688** | 0.655 | +0.033 |
| verbatim (replay) | 0.152 | 0.140 | +0.012 |
| version_space_blind | 0.216 | 0.181 | +0.035 |
| random | 0.120 | 0.066 | +0.054 |

Pages at ≥90%: 21 for one success, 8 for replay, 8 for random.

**Every arm within 5.4 points, and all four orderings identical:**

```
version_space > verbatim            ✓ both runs
version_space > random              ✓ both runs
version_space > version_space_blind ✓ both runs
verbatim > random                   ✓ both runs
```

That is a replication, not a re-read. The recorded 65.5% was produced on a machine I do not have;
the 68.8% beside it was produced here, on instances nobody had used.

## 3. What this does and does not settle

**Settles:** the ordering of the ladder is real. One generalised success beats replaying it, beats
a blind press, and beats the same skill denied the instruction — on fresh instances, in a
different process, on a smaller task set. The effect is not an artifact of the original run's
seed choice.

**Does not settle:** the headline number (50 pages ≠ 130; the arm rates are not comparable across
task sets, which is why `replication_check()` compares orderings only and `newest()` still quotes
the full run). And nothing here adds capability: the same arms ran, on the same mechanisms. The
17 pages with no first success are still 17 pages with no first success.

## 4. Shipped

- `feasibility()` **probes** — runs the bridge, loads `click-test`, reports the browser. Returns
  BLOCKED with a named cause only if the load genuinely fails.
- `canonical/verification/MINIWOB_REPLICATION_20261112_V1.json` — the run, with `read_this_first`
  stating that only ordering may be compared and what it does not show.
- `replication_check()` — compares the newest replication to the newest full run and returns
  `ordering_reproduces: True/False`, so a future pass cannot quietly quote the headline while the
  ordering has broken.
- The 9th audit layer now prints both lines: `rerun: RUNNABLE` and
  `replication: ordering reproduces on 50 pages, seeds 1080+`.

18 + 17 + 18 tests green. Guard PASS.

---

## Answers

**Does one demonstration become a skill?** Yes, and now independently: **0.688 vs 0.152** on
instances that did not exist when the learner was written.

**Is it permanent?** No. 0 of the generalising tasks survive an instruction change; practice is
still worth about +8 points; 17 of 50 pages never produced a first success at all.

**Is the block real?** No. I said the lane was closed. It was open, and the only thing closed was
my check. That is worth stating plainly because it is the sixth artifact in a row where the
measurement, not the mechanism, was the defect — and the one thing that would have caught it is
the rule I keep failing: **exercise the subject, do not inspect it.**

**Smartest next move, now executable rather than hypothetical:** the lane is open, so this is no
longer a proposal. Run the pristine learner on all 130 pages at seeds 1100+, then add the hand
extensions the run's `not_done` names — drag-to-a-point, inner scroll, drag sequences, multi-word
typing — and re-measure on the same fresh instances. That is a pre-registered number against a
baseline I can now reproduce in this sandbox.
