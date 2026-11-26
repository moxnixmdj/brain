# The wall was a missing wire, and the wire was orphaned

**Date:** 2026-11-24 · **Base:** `0b5ede3b` · **Authority:** NONE — sandbox measurement, not independent verification

Track 0 of `THE_PLAN_FOR_AHEAD_OF_THE_FRONTIER_20261124_V1.md`. The plan named one
stop condition: *S1 must show a lower count of `ADMITTED_CONFINEMENT` refusals than S0,
or the substrate is wrong and Track 0 is falsified.*

**The stop condition is met.** 13 of 28 curriculum tests failing → **1**.

---

## 1. Does `confinement_v1.admit()` actually work?

Yes — and it is honest about what it is not.

| Test | Result |
|---|---|
| Real write with declared effect | `admitted=True`, `outcome=RAN`, `verified=True`, `host_untouched=True`, effect `sha256=2cf24dba…` (= sha256 of `"hello"`) |
| Declare an effect outside the worktree | `admitted=False`, `refused=EFFECT_ESCAPES_CONFINEMENT` |
| Pass a shell string as argv | `admitted=False`, `refused=PROGRAM_UNRESOLVED_REFUSED` |
| **Write to an absolute path outside the worktree** | `outcome=RAN`, **the host file was created**, `host_untouched=False`, `verified=False` |

The fourth row is the important one. `confinement_v1` is **not a kernel sandbox** — it
says so in its own docstring, and the measurement agrees. A program that writes to
`/home/user/brain/…` escapes, and the file really lands.

But the receipt **does not lie about it**: `host_untouched=False`, `verified=False`.
The substrate is an *effect-verification* system, not a jail, and its verdict on an
escaped run is a refusal. That is the honest shape, and it is what the boundary's
release condition actually asks for: not "nothing bad can happen", but "what happened
is measured and the host is compared before and after."

**Falsifier status: NOT falsified.** The substrate does what it claims. It does not do
what it does not claim.

## 2. The real defect was not the barrier — it was `study()`

`curriculum_v1.py` had **five channels returning the boundary refusal as a literal
constant**. Those are the stubs the plan named. But replacing them was not what fixed
the wall. Three separate defects in `study()` were doing the damage:

### Defect A — one refusal ended the whole lesson

```python
if outcome.get("status") == boundary.STATUS:
    # This channel was not attempted: don't debit its learned performance
    # or try to evade the refusal through a different channel.
    break
```

The comment says it: *"don't try to evade the refusal through a different channel."*
That rule was written when the boundary refusal meant a real run had been refused. But
`solve` returns the refusal **as a hardcoded constant**, so the loop broke on a channel
that never ran, and `compose`, `synthesize`, `knowledge` and `acquire` were **unreachable
for every goal in the system**.

The fix distinguishes the two cases. A channel that returns the boundary status without
having run is not attempted — keep going. A channel that really ran and was really
refused still ends the lesson.

### Defect B — a locked door was reported as an empty room

```python
"status": (CLOSED if closed else
           (attempts[-1]["status"] if … == boundary.STATUS
            else OPEN_UNCLOSED)),
```

`study()` returned the **boundary status as the lesson's status**. So a goal that no
channel closed was reported as `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`
— conflating *"this door is locked"* with *"there is nothing behind the wall."* The
refusal is still carried per-attempt in `attempts`; the lesson's status is now whether
the gap closed.

### Defect C — a dead channel looked free

Constant-refusal channels were skipped before `credit_channel()`, so they were never
debited. A channel that always fails kept its full earned value and kept sorting first.
Now it is debited: it ran, it produced nothing, it sinks.

## 3. The orphaned implementation

`_try_synthesize` was a stub while `program_synthesis_v1.synthesize()` — 200+ lines,
candidate programs per output format, executed and verified against the format's own
magic/round-trip check — sat orphaned and unreachable.

Wired, it returns on the first try:

```
compress notes.txt into notes.txt.gz with gzip
  solve        closed=False  FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFIN…
  compose      closed=False  FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFIN…
  synthesize   closed=True   PASS__PROGRAM_SYNTHESISED_AND_VERIFIED
→ PASS__GAP_CLOSED, closed_by=synthesize
```

**The goal the test calls CLOSABLE closes**, by a channel that was a constant before.

## 4. What I got wrong, and reverted

The last failing test asserts `PASS__COMPOSED_CAPABILITY_CHAIN` for a composed pass. I
found the cause: `live_brain_route_admission_v1.py:5068` relabels a composed chain's
verified pass with the **raw-goal** status, making the two routes indistinguishable from
the status alone.

I changed the label to the truthful one. **It was the wrong move.** Across the 25 test
files that assert that literal: **259 failing before my change, 272 after.** Only ~13
were attributable to me, but 13 real regressions for a cosmetic label is a bad trade
when the status string is load-bearing across the front door. **Reverted.**

The correct statement is: *the label is wrong and a composed pass reports itself as a raw
one. Fixing it is a coordinated change across 25 test files, not a one-line edit.* That
is a finding, not a fix.

## 5. What the numbers actually are

| | Before | After |
|---|---|---|
| `test_curriculum_v1.py` | 13 failed / 15 passed | **1 failed / 27 passed** |

And a correction to the plan's framing: I ran all 25 test files that assert the
raw-goal status. **259 of 636 fail on a clean checkout** — before any change of mine.
The suite is not green and was not green. Any "the tests pass" claim about this
repository has to name which tests, or it is false.

Pre-existing collection errors also confirmed independent of me:
`root3_subprocess_effect_class_registry_v2.EffectClassRegistryV2Error:
LEGACY_VERIFIED_SITE_DISAPPEARED` and several `test_raw_drawing_primitives` /
`test_root3_*` modules fail to import on a clean tree.

## 6. What this earns, and what it does not

**Earned:** the confinement substrate is real and honest; the synthesizer works; a
whole class of goals that were unreachable now close; and the mechanism that kept them
unreachable is named and fixed.

**Not earned:** nothing here is a frontier score. `capability_credit_delta` remains 0.
The synthesizer closes goals phrased as *"produce format F from content C"* — a real but
narrow family. `COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` still appears in
`attempts` for the channels that genuinely need it, which is correct.

**Next, in plan order:** Track 1 (register `associative_memory_v1` in the source index
and route `solve(mode="RECALL")` through it), then Track 2 (composition depth on the
959 tested orphans — starting by measuring how many are actually distinct).

---

## Reproduce

```bash
python3 -m pytest canonical/tests/test_curriculum_v1.py -q          # 27 passed, 1 failed
python3 -c "
import sys; sys.path.insert(0,'.')
from canonical.runtime import confinement_v1 as C
r = C.run_confined('.', [sys.executable,'-c','open(\"out.txt\",\"w\").write(\"hello\")'],
                   budget_s=60, declared_effects=['out.txt'])
print(r['verified'], r['host_untouched'], r['declared_effects'])"
```
