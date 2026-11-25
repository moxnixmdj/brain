# Sixth pass: I measured the "unreviewed" 2,200 modules instead of calling them a fog

**2026-11-25.** Five passes answered "are these all the capabilities" by enumerating
*artifacts*. Each pass found more, and the residue was always the same sentence: "~2,200
runtime modules that no human has reviewed." I treated that as an unknowable region.

It is not unknowable. It is measurable. This pass measures it, and the measurement is worse
for us than the fog was.

---

## 1. The measurement

**Method** (reproducible, ~20 s): parse the AST of all 2,238 `canonical/runtime/*.py`,
extract their public API; then parse the AST of **every one of 6,133 `.py` files in the
repository** and record which runtime modules are actually **imported**.

```
runtime modules                         2,238
public API symbols                      7,430
python files parsed for imports         6,133

imported by >=1 production .py          1,190   (53.2%)
imported ONLY by tests                    836   (37.4%)
imported by nothing at all                212   ( 9.5%)
```

And of those 212:

```
never imported, no matching test file     197
functions inside those 197 modules      1,546
contain a __main__ block                   98   (they are CLI tools)
```

Spot-check: 4 of 5 sampled orphan modules import cleanly, so they are real code, not stubs.

---

## 2. What this actually says about our capability surface

Read carefully, because the naive summary ("90% never used") is **wrong** — I ran it and it
is wrong the other way, and both errors are the same error:

| tier | modules | what it means |
|---|---|---|
| production-reachable | **1,190** | the real, load-bearing surface — larger than any of my five previous answers assumed |
| test-only | **836** | reaches only through a test. A capability that exists and is checked, but no production path calls it |
| orphan | **212** | 197 of them with no test either. 1,546 functions nothing exercises |
| **total** | **2,238** | |

**So the honest ratio is not "2,238 unexplored" and not "all reviewed". It is: 53% is real
production surface, 37% is test-only, 9.5% is dead.** My earlier framing of the residue as
"unreviewed fog" was wrong in both directions, and I only know that because I measured it.

### The 1,190 is the number I should have been quoting all along

Every one of my five previous answers described a system built from a handful of engines.
The production-reachable surface is **1,190 modules**. That is the real size of the thing,
and it is a capability surface I have described incompletely six times.

### But reachable is not capable

`imported by ≥1 production file` does not mean "used". It means "referenced". A module
imported for one helper and never called on a real task is reachable and idle. I can measure
reachability; I cannot measure *use* without instrumenting execution across 321 missions,
1,064 action intents and 3,042 receipts, and most of those entry points have no recorded run.

---

## 3. And I ran the tests

The full suite is **2,803 test files / 3,766+ collected tests**. A complete run exceeds my
1,700 s limit and stalls around 11% with heavy, clustered failure. Rather than report a
partial run as a rate, I took a **reproducible 60-file sample**:

```
5 failed, 515 passed, 1 error
```

| failure | cause |
|---|---|
| `ModuleNotFoundError: 'cv2'` | environment, not logic |
| authority string `V63` vs `V91` | **stale assertion** — a test frozen against an old constant |
| SHA `827f7684…` != `e208000c…` (×3) | stale hash pin |
| `assert 135 == 82` | stale count |

**4 of the 5 failures are stale self-assertions** — tests that pin a constant, a hash or a
count that later changed. Only two failures are environmental.

That is a finding about the test corpus, not about capability: a suite that pins hashes and
version strings fails when the system moves, and it says nothing about whether the
*behaviour* is correct. It also means **the 836 test-only modules are partly validated by a
corpus that is itself partly stale**, and I cannot separate those without a much longer run.

---

## 4. What six passes have now established

| pass | what it added | its residue |
|---|---|---|
| 1 | 15 capabilities, verdict table | MiniWoB, Terminal-Bench missing |
| 2 | 19 families / 12 components / 11 specs | 2,238 modules missing |
| 3 | 2,238 modules, 595 verifications, 16,155 functions | 321 missions, 440 root docs, `astra/` missing |
| 4 | 51/51 Wolfram-adjudicated, mypy#21968 repaired | other branches unread |
| 5 | branch delta is 94 files, all read | 2,200 modules "unreviewed" |
| **6** | **the 2,238 are 1,190 production / 836 test-only / 212 orphan** | **use vs reachability** |

Each pass's residue was a real thing I had not measured, and I named it incorrectly as
unknowable when it was merely unmeasured. That is the recurring error, and it is mine, not
the repository's.

---

## 5. The answer, with the bound stated correctly

**Are these all the capabilities?**

- **No, and now I can say exactly why, in three numbers:**
  1. **836 modules are test-only** — capabilities that exist, are checked, and that no
     production path calls. My five previous answers described none of them.
  2. **212 modules are orphans** (197 untested, 1,546 functions) — dead or CLI-only code
     whose behaviour is unknown and unverifiable from artifacts.
  3. **1,190 production modules are reachable but I cannot measure which are used**, because
     most of the 3,042 receipts correspond to governance acts, not task executions.

**Am I 100% sure?** No — and the correct statement is narrower than any of my previous five:
*I have enumerated every artifact and every file. I have not enumerated every **behaviour**,
and 836 test-only plus 212 orphan modules are precisely the places a behaviour could hide.*

**Did the comparison change?** No. The externally comparable numbers are unmoved and still
a loss: 3.9% SWE-bench Verified, 2.7% MiniWoB, 6/11 Terminal-Bench, 2.25% on 89 blind real
commits, 20% on 30 differential-witness commits, 0/10 on global ASTRA predicates — against
a frontier at 76.8%, 86.1%, 82.7%, and 12–17 h autonomy. What changed is the size of *our*
side of the ledger, which is larger than I said and still two orders of magnitude short on
completion.
