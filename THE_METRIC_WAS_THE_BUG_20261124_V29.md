# THE METRIC WAS THE BUG — a guard that polices this project's own receipts
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. No model call, no stored parameter.

---

## 1. Why a guard, not a fifth apology

Four measured misreads in eight rounds, all one shape:

| round | the number | what it actually was |
|---|---|---|
| V21 | coverage as a **mean of ratios** | hid runs that predicted nothing |
| V23 | a selection objective | disagreed with the price table printed beside it |
| V27 | a pass/fail comparator | pytest's summary **line**, carrying a wall clock |
| V28 | accuracy **0.7857** on held-out functions | the majority class, flagged nothing |

Each was caught by hand, afterwards, by noticing a number that looked too good. That is luck applied four
times, not a method. The instruments were the defect, so the next thing built is an instrument that polices
instruments.

## 2. What it found in my own receipts, on its first run

```
receipts examined        2,986
receipts policed            33   (the ones carrying a `verdicts` block — i.e. making claims)
clean                       16
flagged                     17
```

| rule | fired | the historical misread it encodes |
|---|---|---|
| `MAJORITY_CLASS_WITHOUT_BASELINE` | 16 | V25, V28 |
| `ACCURACY_WITHOUT_SENSITIVITY` | 16 | V28 (a rule that flags nothing scores well) |
| `RATIO_WITHOUT_DENOMINATOR` | 3 | V21 (a mean of ratios hides empty runs) |
| `TIMING_IN_COMPARATOR` | 0 | V27 — already fixed, and it stays caught |
| `INSTRUMENT_WITHOUT_COST` | 0 | standing §2 discipline, already obeyed repo-wide |

**Seventeen of my own receipts were making claims without the comparator that would prove the claim is not
a base-rate artefact.** Sixteen of those predate this round. That is not a technicality: it is the exact
hole the four misreads fell through, present in the majority of my claim-bearing artifacts.

## 3. A ledger, not a waiver

The guard is not allowed to be a linter you route around. Every flagged receipt is either **resolved in an
explicit ledger** — naming what was missing, whether it is material, and why the conclusion does not depend
on it — or it fails the run.

- **resolved:** 17 · **unresolved:** 0 · **material: 1**
- The one material finding is honest and unflattering: `PRICE_A_REFUSAL_ON_REAL_CODE_..._V2.json` (V24)
  reports **0.9796 across-codebase accuracy with no base-rate comparator**. Its within-group 0.9896 is a
  comparator of sorts, but not the one that matters. So V24's headline is marked **PARTLY** supported and
  that receipt's four existing caveats are now joined by a fifth.
- The rest are marked NO with a specific reason each — e.g. V27's arms are compared as *bit-identical
  output* against arm A, which is a stronger control than any accuracy baseline; V22's claim is that cost
  moves 5.9% across a 100× price sweep, which is not an accuracy claim at all.
- `DOES_SYNTAX_PREDICT_OUTCOME_..._V1.json` (V25) fires on the rule but not on the intent: its sensitivity
  is present as `failures_spoken_about: 0 of 42`. The finding is recorded as a **rule limitation** rather
  than patched away — the honest fix is naming the field correctly in future receipts, not loosening the
  rule so it stops seeing myself.

Nothing in that ledger is waived: the exit code is driven by `unresolved`, and a test asserts that list is
empty. An unresolved finding fails the build.

## 4. Verified / unverified / failed

**Verified by execution:** 2,986 receipts examined, 33 policed, 17 flagged, 4 distinct rules, 17 resolved
with 1 marked material, 0 unresolved, exit 0 through the ledger path and exit 1 with `--warn` off on any
unresolved finding. 5 new tests, including one that feeds the guard a knowingly-bad receipt and requires it
to fail. 19 tests pass together with the V26/V27/V28 suites.

**Failed, mine, this round:** the first version of the rule set accepted a bare `base_rate` key as a
class baseline, which would have let 16 receipts through — the same leniency that produced V25 and V28. Tightened
before shipping; the count above is from the strict rule.

**Unverified:** that these 17 findings are all of them. The rules read receipt *shape*; a receipt that names
its fields correctly but compares the wrong things still passes. The ledger reduces the chance of a fifth
hand-caught misread; it does not eliminate it, and saying otherwise would be the same overclaim the guard
exists to catch.

**Not producible:** any benchmark row. `docker: command not found`. No claim about SWE-bench Pro,
Terminal-Bench 4.0 or OSWorld 2.0 is made here, and no frontier comparison is drawn.

## 5. Tests and cost

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 0.36 s
19 passed (V26 + V27 + V28 + this guard)
```

## 6. What this changes about the project's own story

Eight rounds of results now carry a machine-checkable honesty layer. The scorecard from V28 stands as stated
— behaviour is earned and binds, shape is portable and useless, prediction has failed twice — but every
future receipt that reports an accuracy must now also report the class baseline and its sensitivity, or the
repo's own guard fails it.

That is the first time in this project that a defect I found by hand has been converted into something that
cannot be repeated without tripping an alarm. It is worth more than another experiment, because the last
four experiments each produced a number I then had to disbelieve.
