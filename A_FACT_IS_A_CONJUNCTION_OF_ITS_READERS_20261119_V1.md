# A fact is a conjunction of its readers — and that is not enough to make it right

**Receipt:** `canonical/verification/A_FACT_IS_A_CONJUNCTION_OF_ITS_READERS_20261119_V1.json` · 6 of 6 gates MET · 7.7 s, 37 states, 17 facts, 34 readers, 9 actions, zero model calls, zero parameters, zero network.

## The move this round tried, and the reason it was wrong

The last round ended with three actions abstaining and one name attached to the blame: `tar_x`, said to abstain because its column `btgz_valid` was unsound. The evidence was that `tar -tzf` exits 0 on a gzip whose payload is garbage, so the column calls a non-archive valid.

The obvious repair is the one this round first wrote: read every fact twice, with two *different* implementations, and keep a fact only when both readers agree. The literature supports the shape — source diversity, surface the conflict, never average it away.

It is the wrong repair, and the measurement says so in one line:

```
tar -xzf on the garbage state: True
  tar_x   primary 0.923 -> conjunction 0.846
consensus worse on: ['tar_x']   columns that do not conform: []
```

## What actually happened

GNU tar treats a gzip whose payload is not an archive as an **empty archive and exits zero**. So `tar -xzf` succeeds on the garbage state. The shell reader (`tar -tzf`) and the action agree perfectly; the independent stdlib reader (`tarfile`, plus a third reading that inflates the member and shows the payload is text) is right about the *world* and wrong about the *action*.

So the column was never unsound. It conforms to its action on all 37 states. The conjunction removed exactly one fact at exactly one state — the only state where the two readers differ — and in doing so turned one correct prediction into an error:

| | primary | conjunction |
|---|---|---|
| `tar_x` | 0.923 | 0.846 |
| `ln_link` | 0.923 | 0.923 |
| `mkdir_nodir_sub` | 0.846 | 0.846 |
| columns conforming to their action | 9 / 9 | 8 / 9 |

And the abstention the previous round blamed on soundness was, like the other two, **coverage**. All three had one cause, not two. That also retires the previous intent's written stop condition — *"a soundness pre-check must reject `tar -tzf`"* — which would have deleted a correct column on a presupposition.

## The law

> A fact is a prediction of the action it gates, not a description of the world. Its correctness is conformance to that action's outcome, and no amount of reader agreement can override the outcome.

Two independent readers still earn their keep, because they are **free**: 34 readings across 37 states changed not one byte and added not one world trial. What they buy is *discovery* — without the second reader nobody would know the file is not an archive, and nobody would learn that the action is more permissive than its name suggests. What they do not buy is a verdict. A vote among readers is a description of the world; the plan has to survive an action.

This is also how it is done at the frontier: an agent that runs a command and reads its exit status, its stderr and its diff is doing conformance, not consensus — and when its own checks and its tools disagree, the run wins. The multi-reader machinery in the literature is for *escalating* a conflict to a decision, never for overwriting an outcome that already executed.

## What this changes in the thesis

The single bottleneck is unchanged, and sharper: with no unsound columns left, the remaining loss is entirely **which state to execute next**. The failure mode is abstention on off-sample states, and it is fixed by buying coverage — one well-chosen variation at a time — not by adding readers to the sensor.

Two rules now stand where one did:

1. **Read twice, free.** Two independent implementations of every fact, always. Divergence is information and costs nothing.
2. **Never arbitrate with the readers.** Collapse to the safe side only for hypotheses that have not run; once the action runs, the outcome is the arbiter, and a fact that disagrees with a succeeded action is wrong even if the whole world agrees with it.

## Limits

Two readers from one producer do not exclude a shared misunderstanding. Conformance is measured on 37 states: a permissive action and a permissive check can agree everywhere measured and still diverge off-sample. The facts themselves are hand-written; this round audits the arbitration rule, not the choice of facts. One machine, one operator, nine actions, and no claim of independent verification.
