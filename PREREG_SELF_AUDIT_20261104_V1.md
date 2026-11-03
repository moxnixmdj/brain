# Pre-registration: noticing a failure without being told

**Written before implementing. 2026-11-04 · authority NONE · `truth.achieved` false**

## The gap this closes

Every previous round required someone outside to say "that answer was wrong". The creature could
revise, attribute and retire — but only when told. It could not notice.

The reason it *can* now notice something is a fact nobody supplied: a synthesized body is returned
to the caller, and the creature can inspect what it produced. Observable without any labels:

1. **partiality** — the body raises or returns non-finite on the domain grid for its arity.
2. **branch imbalance** — a conditional whose one arm fires on a tiny fraction of the domain. A
   branch taken on 1 of 30 probes is a special case dressed as a rule.
3. **triviality** — the body ignores a parameter it was given.

Measured already (raw numbers, no audit yet):

| problem | verdict (withheld points) | raises | note |
|---|---|---|---|
| norm_plus_half | OVERFIT | 1/30 | `if not (min(v, l)): ...` — the real work is in a branch that fires on 1 probe |
| norm_times_2 | OVERFIT | 1/30 | same shape |
| plain_norm | OVERFIT | **7/30** | `v/h` without the guard; divides by 0 at h == 0 |
| plus_one | OVERFIT | 0 | a genuinely dead branch |

Monkey-patched `sys.settrace` was used to count reached returns; the real implementation will
instrument by AST rewriting instead, because a global trace hook is a side effect I do not want in a
creature's runtime.

## Predictions (falsifiable, stated before the run)

**A1.** Bodies the audit flags are OVERFIT at a higher rate than bodies it clears. If flagging is
uncorrelated with being wrong, the whole idea fails.

**A2 (honest incompleteness).** Some OVERFIT bodies will NOT be flagged. A body can be wrong with no
observable structural defect. I predict at least one such case exists, and I will report the miss
rather than tune the audit until it catches everything.

**A3 (the cost of false alarms).** No SOLVED body is flagged. If the audit flags correct answers, it
is worse than useless: it would trigger attribution against innocent concepts, which the previous
round specifically fixed.

**A4 (the loop actually turns).** Flag → initiate attribution → a guilty concept is charged → the
next attempt differs. And the control: **without the flag, nothing happens** — no audit is initiated
for a clean body, so the initiator is not simply always-on.

**A5.** The audit must not read the withheld points. It sees the body, its parameters, and the
domain grid only. I am stating this as a prediction because it is the difference between noticing a
failure and being told about one.
