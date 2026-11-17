# The single bottleneck

*2026-11-16. Written against the receipts in this tree, not against intuition. Every number below is
reproducible with the commands at the end; none of it costs a model call.*

AUTHORITY: NONE. This is a producer-run analysis. It claims no external credit.

---

## 1. The claim, taken literally

> "Give the model the smartest actions once and it keeps them permanently. That solves all computer use and
> all advanced software engineering."

For that to be true, four things have to hold at once. Each is measurable, and each has been measured.

| # | What must hold | Measured | Receipt |
|---|---|---|---|
| 1 | The demonstration must **determine** the action | **0.5469** | `SYSTEMATIC_EDIT_SUPPLY_20261116_V1` |
| 2 | The consequence must be **seen**, so right can be told from wrong | **0.5445** | `ORACLE_DENSITY_20261116_V1` |
| 3 | The situation must **recur** — and recur exactly, and not silently corrupt | **0.1584 / 0.0481 / 0.3114** | `SKILL_RECURRENCE`, `ACTION_REPLAY_UNDER_CHANGE` |
| 4 | When nothing was recorded, something else must still see the error | **0.5** | `COMPUTER_USE_CHECK_DENSITY_20261116_V1` |

Operating point: `0.5469 × 0.5445 = 0.2978`. Value-bearing work: `0.1167`. That is the honest size of
"learn it once and keep it", before any question of intelligence.

The user's own critique maps onto these rows exactly, which is why it is right:

- **Identifiability** is rows 1–2. One trace is consistent with exponentially many hypotheses *unless the
  observation separates them*. Determinacy is not a property of the inducer alone; it is a property of the
  inducer plus what the trace can distinguish.
- **Vocabulary insufficiency** is row 2. `INSUFFICIENCY_CERTIFICATE_20261113_V1` says repetition cannot
  separate success from failure when the causal observable is missing. Correct — and note the phrasing: the
  observable is *missing*, which makes it an absence, not an impossibility.
- **Synthesis–verification asymmetry** is rows 3–4. Replay covers ~2.2% of SWE-bench Verified; real work
  composes new edits that were never recorded, and with nothing recorded only a crash and a no-op are
  visible.

So: one-shot experience is a **multiplier**, and a real one — but it multiplies three other quantities, two
of which it does not touch. Perfecting it would still leave the majority of real work outside it. Not
because memory is weak, but because **forgetting is not what is failing.**

## 2. The bottleneck

Not induction quality. Not parameter count. Not retrieval. Not data.

> **The consequence of an action is absent from the agent's observation.**

Everything else in this tree is downstream of that sentence. The evidence is a single controlled comparison
on a real machine (`COMPUTER_USE_CHECK_DENSITY_20261116_V1`): 34 mechanically derived wrong shell actions
over 9 real transformations, real programs on a real disk, real reset.

| Observation available to the agent | Wrong actions caught |
|---|---|
| full state (names, sizes, content) **+ a recorded consequence** | **1.0000** (34/34) |
| names and sizes + recorded consequence | 0.9706 (33/34) |
| names only + recorded consequence | 0.7647 (26/34) — **23.5% invisible** |
| anything at all, **no recorded consequence** (novel work) | **0.5000** (17/34) |

Read the last row again. Without a consequence to compare against, a wrong result that *looks like a
result* is invisible — half the failure modes are only crashes and no-ops. And read the first row: with the
consequence present, the check is not 80% good, it is **complete**, because a wrong action that leaves the
state identical did not miss the goal.

That is the asymmetry that decides the question. The oracle problem is not "how do we write better tests".
It is "**can the agent see what it did**". Where it can, checking is exact and free. Where it cannot, no
amount of experience helps, because the experience was never observed.

This also explains the external record instead of contradicting it:

- 80.2% of agent-written test patches are weak or absent oracle signals — agents manufacture the
  *appearance* of a check because the real one (the consequence) was never in view.
- OSWorld 2.0: the best agent spends **under 7% of its budget** detecting and repairing its own errors, and
  fails by skipping verification. Not a capability gap: an observation gap.
- Every fixed verifier is a proxy for intent, and no proxy survives a stronger generator.

## 3. The fix, and why it is not "add a verifier"

If the oracle is an observation, then the oracle can be **synthesised** as one, and its quality is decidable
before it is trusted. `DISTINGUISHING_PROJECTION_20261116_V1` does that. Given an action and the space of
ways it can be wrong, search the features of the state for the smallest set that passes *two* tests:

- **Separation** — every wrong action leaves a projection different from the right action's.
- **Stability** — running the right action again reproduces the projection.

Both are necessary and they disagree, which is the whole point:

| Feature | Separates | Stable | Verdict |
|---|---|---|---|
| content | 34/34 | 9/9 | **admitted** |
| size | 33/34 | 9/9 | insufficient |
| name | 26/34 | 9/9 | 23.5% blind |
| mode | 26/34 | 9/9 | insufficient |
| mtime | — | 1/9 | **rejected** |

Separation alone admits a timestamp. A timestamp separates everything and would condemn every correct
replay as a failure — a machine for false alarms. Stability alone admits a name listing — a machine for
silent acceptance. The two-sided test is the whole of the design, and it is what the field replaces with
intuition, which is why the field has verifiers that pass and patches that are rejected.

Synthesised minimum: **one feature, in 9 of 9 tasks.** Content. Computable from any OS, zero parameters,
zero model calls, no new memory store, no component to maintain — *the best part is no part*. The oracle
costs one hash.

In the law's terms this is what makes the only controllable term movable: density `0.6788 → 1.0` is not a
research aspiration, it is a projection choice, and the ladder says that is `0.2978 → 0.4387` with **no
better model**. It also makes identifiability *decidable* rather than a worry: two hypotheses are
distinguished iff some admissible projection separates them, and the missing causal observable of the
insufficiency certificate is exactly a projection feature — found by search over a finite set, not by luck.

## 4. What this does not do

Stated plainly, because a fix that hides its boundary is the failure mode it was built against.

1. **It certifies fidelity, not correctness.** The differential asks "did this action produce the
   consequence that was recorded", not "was the recorded consequence the right goal". A wrong first
   demonstration is certified forever, faithfully, with a hash. This is the same disease as the 0.3114
   silent-corruption rate, one level up, and no observation model can cure it: only an external reference —
   a person, or a specification — can. That boundary is real and it is not moved here.
2. **It identifies errors inside the declared hypothesis space.** Outside it, nothing. Growing the space is
   measurable work; assuming it is complete is the mistake. (Same discipline as the certificate.)
3. **A GUI is unmeasured.** Pixels and DOM are a projection somebody else chose. The synthesis applies
   unchanged — OCR text, widget tree, focus, geometry — but this tree has a receipt for a shell, not for a
   desktop. Claiming otherwise would be the self-congratulation this project keeps naming.
4. **One action is not a workflow.** OSWorld tasks average 27.25 checkpoints and 1.6 human hours; an error
   can hide *between* two locally-correct actions. Composition is where the next receipt goes.
5. **Determinacy is not fixed by any of this.** With a perfect oracle the ceiling is still `0.5469`: you
   cannot read off an edit that the demonstration does not determine. The observation raises the ceiling on
   *being right*; it cannot raise the ceiling on *being determined*.

## 5. The answer

"Give the model the smartest action once and it keeps it" is true for the narrow class where the
consequence is observable, the premise recurs, and the demonstration determined the action — roughly
`0.2978` of real work at today's observation, and `0.4387` at full observation, and it is a **multiplier**,
not a solution. What fails is not memory. It is that the agent did not see what it did, so it could not
tell a success from a plausible failure, and kept the wrong one.

The complete solution is therefore not a larger store of actions. It is an agent that **manufactures its
own oracle per action** — an observation chosen so that being wrong is visible — and then, because being
wrong is visible the first time, checks, repairs, and only then keeps. Memory is what happens *after* the
consequence is in view. That ordering is the bottleneck, and it is one sentence: **make the consequence
visible, and checking stops being a research problem.**

---

## Reproduce

```
python3 canonical/swe_kernel/computer_use_check_density_v1.py \
  --json canonical/verification/COMPUTER_USE_CHECK_DENSITY_20261116_V1.json
python3 canonical/swe_kernel/distinguishing_projection_v1.py \
  --json canonical/verification/DISTINGUISHING_PROJECTION_20261116_V1.json
python3 canonical/swe_kernel/capability_law_v1.py \
  --json canonical/verification/CAPABILITY_LAW_20261116_V1.json
python3 -m pytest canonical/tests/test_computer_use_check_density_v1.py \
  canonical/tests/test_distinguishing_projection_v1.py canonical/tests/test_capability_law_v1.py -q
```

## Falsifiers

This argument dies if any of the following is shown:

1. A class of real actions whose wrongness is invisible under **every** stable projection — then the
   bottleneck is not observation but the absence of an external reference, and the claim above is too
   generous.
2. A projection that separates every wrong action yet admits a wrong *goal*: it would prove correctness is
   cheaper than this, i.e. that a consequence differential is sufficient for intent. It is not, and if it
   were, §4.1 is wrong.
3. Density failing to track the projection on a GUI workload: the mechanism would be shell-specific.
4. A case where a coarser projection checks better than a finer one on the same hypothesis space — the
   two-sided criterion would then be mis-specified.
