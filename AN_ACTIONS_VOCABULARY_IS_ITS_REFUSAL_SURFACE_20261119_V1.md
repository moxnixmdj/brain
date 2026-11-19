# Why "let it experience each action once" cannot work — and what does

**Receipt:** `canonical/verification/AN_ACTIONS_VOCABULARY_IS_ITS_REFUSAL_SURFACE_20261119_V1.json` · 5 of 6 gates MET, one honestly NOT MET · 1.2 s, 8 real binaries, 98 executions, 160 unexecuted joint states, **0 model calls, 0 parameters, 0 network**.

## The claim under test

> Instant learning is solved perfectly. So give the model the most advanced actions, let it experience each **once**, and it has that capability permanently.

Half of this is true, and the half that is false is the half the whole plan rests on.

**True:** identification is solved. Given a fact vocabulary and a handful of executions, the rule that decides when an action applies is pinned exactly, with no parameters, no training, no model calls. That is measured, repeatedly, in this tree.

**False:** that one experience is enough. Measured here on eight real binaries, one successful experience is not *undecided* on states it never saw — it is **wrong on 123 of 160**. It answers confidently, because every property that happened to be false in the lucky success is thereafter believed irrelevant. That is the precise mechanism, and it is why "show it once" produces an agent that is confidently wrong in new environments rather than one that asks.

**And the reason it is false is not the one every prior round assumed.** It is not coverage. Coverage is what you buy *after* you know what to measure. The wall is one layer deeper:

> **the fact vocabulary is an input everywhere — and a vocabulary that is given cannot be trusted to contain the thing that actually decided the outcome.**

## The single bottleneck

Every action-model-learning paper, and every module in this repo, begins from an "already-declared decision-basis atom". Soundness theorems (N-SAM, LOCM, the ICAPS 2026 numeric models) are conditional on *complete traces*, which their own authors call unverifiable; predicates learned from traces alone verify at **0% (Grid) and 4% (Sokoban)** out of distribution. This tree's own certificate says the same thing in its own language: 31 facts, 8,388,608 candidate conjunctions, cap 12 — the basis is the wall.

So the bottleneck, stated so it can be attacked: **where does the vocabulary come from, without a human writing it per action and without assuming the trace is complete?**

## The answer this round measures

A program can only refuse on a condition it *checks*. When it refuses, it says which. Therefore:

> one controlled violation per candidate property enumerates the conditions a program actually has — and the **smallest set of those refusals that explains every refusal and no success** is the precondition.

Eight binaries, one generic mutation library (ten single-property perturbations applied to each path the action mentions), **one execution per property, 98 executions total**. What comes back is not a learned approximation, it is each tool's own check list:

| action | executions | conditions the refusals select |
|---|---|---|
| `tar -xzf` | 9 | gzip magic, gzip truncation, ENOENT/ENOTDIR/EACCES/ELOOP/EISDIR — **six, and *not* "is a tar archive"** |
| `gzip -dk` | 9 | the same six over one path |
| `ln -s` | 18 | EEXIST, ENOENT, ENOTDIR |
| `mkdir` | 9 | EEXIST, ENOENT, ENOTDIR |
| `cp` | 18 | seven, and it separates *source* failures from *destination* failures |
| `chmod 600` | 9 | ENOENT, ELOOP |
| `head -n 1` | 9 | ENOENT, EACCES, ELOOP, EISDIR |
| `rm -f` | 9 | **one** — EISDIR. Silence is its own answer. |

Then the test that matters: **160 joint states that were never executed** — two and three simultaneous violations, off the axis the surface was enumerated on. The rule learned from refusals predicts **160 of 160 exactly, 0 wrong, 0 false accepts**. The refused states were 527,360 candidate combinations; 98 executions bought all of them.

### The structural confirmation of last round

`tar -xzf` does **not** refuse a gzip whose payload is not an archive. So that condition is absent from tar's refusal surface, therefore absent from its learned precondition — which is exactly why the earlier "unsound column" was never unsound. This round does not argue it; the method reproduces it.

## The negative result, kept

I predicted that the message's *grain* would be load-bearing: that ignoring the words and naming one property inside an ambiguous class would buy false accepts. **It did not.** With an exact minimum-cardinality cover, item granularity is not worse: 0 false accepts, 0 wrong, same 160 states. K4 is recorded **NOT MET**.

What survives, and it is the whole gain: the words decide *which generic properties are conditions at all*. Their grain changes no prediction on this pool. A round that reported K4 as green would be lying about a measurement that took one extra comparison to make.

## The three objections, answered structurally

**(a) Identifiability.** A trace is passive and consistent with exponentially many hypotheses. A refusal is an *intervention*: a controlled single-property counterfactual, one at a time. That is why the learned rule has zero false accepts on states it never saw — the hypothesis is pinned by construction, not by luck of sampling.

**(b) Vocabulary insufficiency.** The certificate's wall is dissolved rather than climbed: the vocabulary is no longer an input. A finite generic perturbation library generates candidates; the tools themselves select which are conditions. The causal observable cannot be missing from the representation, because in this construction **the observable is the refusal**.

**(c) Synthesis–verification asymmetry.** Untouched by this round, and it remains the next wall. Knowing when an action applies is not knowing what it does. Effects need a delta sensor, and composition needs verification — and a composed step's refusal surface is at least the union of its parts', which is the only reason composition is tractable at all.

## What is real, and what is not

- **Real:** exact, non-parametric preconditions for real tools, derived from their own refusals, linear in the vocabulary and constant in the state space. This is the mechanism by which an agent can enter an arbitrary environment and learn an action's applicability *permanently*, in one pass over its properties.
- **Not real:** "experience once". One success is worse than no experience, because it manufactures confident wrongness. The unit of experience is **one violation per property**, not one success per action.
- **Not claimed:** sentience. This is a computable precondition. A creature would need it, and it does not constitute one.
- **Not yet:** effects, composition, and everything about code as opposed to the shell. The same construction should apply — a compiler's diagnostics, a test runner's failures and a type checker's errors are refusal surfaces with the same property — but that is the next round's job, not this receipt's claim.

## Next

The remaining distance between "knows when it can act" and "can do anything on a computer" is one layer: **the effect**. Precondition is now derivable from refusal. The effect is derivable from the delta the action leaves behind, and the composition of two actions is verifiable exactly when each part's surface contains the other's precondition. That, not more coverage, is the next thing to build.
