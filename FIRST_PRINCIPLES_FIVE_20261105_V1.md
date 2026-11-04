# First principles, fifth pass — the creature has exactly one job, and it is not doing work

**2026-11-04.** Fifth time. The previous four answers were, in order: a refutation, a repair, a
bigger repair, and a budget fix. All four were about the *quality* of the creature's learning. None
asked what the creature is actually **paid to do**. This one does, and the answer is one sentence.

Authority **NONE**. Spend $0. `truth.achieved` false. No code changed.

---

## 0. The measurement that reframes everything

I instrumented every work item the creature performs across a full fed-budget life (20 sessions,
life 480, 202 work items):

| work kind performed | count |
|---|---|
| `inspector_onboarding` | **202** |
| `func_evolve` | 0 |
| `repair:` | 0 |
| `chase:` | 0 |
| `open_gap:` | 0 |
| **distinct kinds** | **1** |

**The creature has exactly one kind of work: acquiring a verifier for a capability.** It has never
repaired a bug, landed a patch, run a numeric chase, or closed a gap — not rarely, *never*, across
every run in this entire session.

The reason is structural, not a bug. `heterogeneous_world_proposals` can author four kinds of work,
and three of them require the **caller** to supply `failing_tests`, `numeric_chases`, or `open_gaps`.
`run_sovereign_board` passes none of them. And the only production caller of that runner is the test
suite — no operator path feeds it real inputs either.

So the loop is closed in the wrong place:

> The creature verifies capabilities it will never use, on a board built from an empty input set,
> and reports that as productivity. 202 work items of a single kind is not a creature; it is a
> capability-matrix crawler with a life bar.

## 1. Three more instruments of exclusion, each measured

Once you know the creature only does onboarding, the question becomes: **which capabilities can it
even consider?** Three independent filters, and they compose badly.

**Filter 1 — `difficulty` sorts the wrong way.** In `external_hard_slice_v1`:

```python
return (0 if not self.has_inspector else 1, -rate, self.attempts)
```

`has_inspector` leads, ascending, so **every capability that already has a verifier ranks last.** A
155-capability registry with 43 already-inspected and a 112-row slice therefore selects *exactly the
43 uninspected ones that are left* — the consideration set provably excludes everything that already
works. (I widened the slice to 155 to test it; the outcome was identical. `run_sovereign_board`
re-adds every already-inspected id to the "inspected" set, so onboarding them produces nothing
whether they are on the board or not.)

**Filter 2 — the cut is static and permanent.** `_extract_capability_feature_flags` is a pure
function of host and registry. 103 of 155 are refused, and no session can change that. Measured:
READY = 52 at birth and 52 at death.

**Filter 3 — two failures, then never again.** `max_attempts=2`, and a settled pass is never
re-attempted. 89 capabilities parked, 0 reopened. Measured over 202 work items.

Composed: **52 reachable, of which 23 can pass, of which every pass is never revisited.** That is the
entire life of the organism, and it is why 300 extra life units bought calibration and zero
capability.

## 2. My worst error of the session, named plainly

For four turns I described this as a *learning* problem and hunted for the missing adaptive organ.
The correct description was available from the first measurement: **the creature was not doing work.**
It was acquiring permissions. Everything I built — the diet fix, the static-guess fix, the life grant
— made the permission-acquisition loop more honest and better fed.

The thing that would make it a creature is not an organ. It is **supplying it with work**:

```
failing tests the repo actually has   (pytest failures with file + test id)
numeric chases it actually cannot hit
gaps the tree actually declares
```

`heterogeneous_world_proposals` already accepts all three. Nothing passes them. That is the whole gap
between "202 onboarding cycles" and "repaired 6 bugs it had never seen."

And with real work, the failure has somewhere to go: a repaired bug changes a test from failing to
passing, and **that is a capability the creature did not have at the start of the session** — the
first time the axis-B question would even be meaningful.

## 3. What I am not going to claim

Fixing the consideration order (`difficulty`) is tempting and I am not recommending it first. The
measurement says it is worth **nothing** on its own: widening the slice from 112 to 155 changed
nothing (23 closed, 89 parked, in both). A cleverer ranking cannot manufacture work that does not
exist. Ranking is a distraction from the input problem, and I have spent four turns being distracted
by exactly this kind of local defect.

Equally: none of this says the creature is incapable. When it is handed a task it can onboard, it
succeeds at 22 of 202 attempts and reports honestly when it cannot — 180 refusals with specific
reasons. It is competent at the one job it has. The job is just too small to be a life.

## 4. The next step, and its falsifier

**Feed it real work.** Wire the creature's own failure intake — the repo's actual test results — into
`failing_tests` (and a declared gap set into `open_gaps`) so that the board is no longer a
single-kind crawler. Nothing about the acceptance path changes; the creature still has to prove a fix
with an independent oracle.

Falsifier, stated before measurement:

> If the board, fed with real failing tests, still produces only `inspector_onboarding` items, then
> the input was never the constraint and the proposal inside `heterogeneous_world_proposals` is dead
> code. If it produces `repair` items but they all fail, the constraint is the repair path. If some
> succeed, the creature has acquired a capability it did not start with, and *that* is the first
> result in this entire line of work that bears on "sentient-like" rather than "well-instrumented".

The third outcome is the only one that answers the owner's question, which is exactly why it must be
measured rather than assumed.

## 5. Non-claims

One host, one board composition, 202 work items over 20 sessions; "never" means across every run
recorded in this session and in the fed-budget sweeps, not a proof of unreachability. The claim that
no production caller supplies real work rests on a grep for `run_sovereign_board(` outside tests,
which returned nothing — that is evidence, not exhaustive proof, and other entry points
(`run_awake_creature_pulse`, `run_unattended_inspector_investigation`) were not separately traced for
work-supplying inputs. The `difficulty` ordering finding is real and measured; the claim that it is
*unimportant* rests on one 112-vs-155 comparison run. No repository change was made for this document.
