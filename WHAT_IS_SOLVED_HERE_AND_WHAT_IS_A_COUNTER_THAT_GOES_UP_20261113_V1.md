# What is solved here, what is a counter that goes up, and what the four sources actually say

**2026-11-13. Branch `arena/c2968b8c-brain`. Base: main `b8c42ebc`. Authority: NONE.**
`truth.achieved` stays `false`. No spend; no model in any result-bearing path.

> The owner asks, for the third time and with a paste from another analyst: *we already solved
> instant learning and instant learning in new environments — doesn't that solve everything, if
> we just give the model the actions and let it experience them once? And isn't this a
> revolutionary way for agents to learn faster? We were trying to make a sentient creature.*

## 0. The answers, in one line each

1. **No, it does not solve everything.** The best held-out number in this repository is 37.52%
   coverage at 76.36% precision on one class; two of eight unseen pull requests sit at zero;
   the other class reaches 34.15% at 60.61% precision with **65 changes the developers did not
   make**. That is a partial transfer on one class, not a solved capability.
2. **No, you cannot "give it the actions once."** Actions are already given: 145 bound
   capabilities, and the operators that do work are measured. What has never existed is the
   *input*: the corpus that would exercise them is empty by construction, and the door refuses
   execution without admitted confinement (19 of 38 realistic advanced-coding goals,
   `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`; 3 of 38 execute).
3. **The pasted analysis is 80% right about the literature and wrong about the inference.**
   All four sources are real (they are checked below, with numbers), but three of them say the
   opposite of what the paste concludes: token-space memory is *not* reliable learning (CL-Bench:
   naive ICL 25.4% gain beats every dedicated memory system), and weight-space consolidation
   requires open weights, gradient steps, and a verifier — none of which this repository is
   allowed to have.
4. **No, nothing here is sentient, and no accumulation mechanism makes it so.** See §6.

## 1. The pasted claims, checked against their own sources

Every citation is real. The numbers and caveats around them change the conclusion.

| claim in the paste | the source, checked | what it actually says | verdict |
|---|---|---|---|
| "Experience Distillation converts transient ICL into permanent weight updates via model-free, one-step distillation" | **arXiv:2607.21051**, *Sample-Efficient Learning from Agent Experience* (Jul 2026) | real method; **retains 64.8–93.4%** of the ICL gain (loses up to a third), beats direct SFT (3.8%) and matches RL with **9.6x fewer environment samples** on 749 SWE tasks. It distils *teacher decisions replayed from a recorded history* into **open weights** | true, and it needs exactly what this repo forbids |
| "5 approaches, weakest to strongest … post-training/RL is the ultimate goal" | **AWS Builder, *Continual Learning* (Jul 2026)** | the spectrum is **persistence/cost**, not capability rank. Its own decision tree: *"Do you run your own model? No → loop engineering + memory (max out scaffold first)"* | misread; the source's advice for our situation is the opposite of "add weights now" |
| "Memory models: token-space memory **is** real learning; the missing layer is weights" | **Letta, *Memory Models: Towards Agents That Learn* (Jun 2026)** | the same post says agents *"do not reliably create durable context"*, warns of **memory rot**, and says the fix is a **memory model trained with memory-native RL** — i.e. more training, not less | half-true; the source calls token-space memory unreliable on its own |
| "ASCENT trains the LLM's weights on its own trajectories during deployment" | **arXiv:2610.05303** (Oct 2026) | real: verify-gated, LoRA fast weights, frozen self as teacher; gains on ALFWorld/WebShop/AppWorld and transfers to held-out scenes. Caveats: needs **open weights and full next-token distributions**; **one verified success does not reveal which turns caused it**; episode time **115 s vs 97 s** | true, and it is a *verifier-gated credit-assignment* result, not a "show it once" result |

The synthesis the paste gets wrong is the hierarchy. Token-space and weight-space are not
"weak learning" and "strong learning"; they are **storage locations**. What decides whether
either learns anything is upstream of both: a **verifier** that says what is right, and a
**distribution** that contains the thing to be learned. CL-Bench (arXiv:2606.05661) measured
this directly: the best of every system it tested reaches **25.4% normalized gain**, naive
in-context learning is the best of them, Mem0 gets 20.2%, ACE 8.6% at $62.8/run, and accumulated
memory frequently *hurts*. Continual-ARC (arXiv:2611.14505) measured the other half: no harness
method gained on unseen tasks; weight training did, and still halved from seen to held-out
(0.57 → 0.29).

## 2. The things in this tree with non-obvious names

The owner is right that the important work exists under non-obvious names. Here is what each
one actually is, and what the record says about it.

| artifact | what it does | evidence | verdict |
|---|---|---|---|
| `canonical/swe_kernel/taught_actions/*` (8 modules) | derives an edit from one before/after example, applies it by AST | in-sample 56.87%; held-out 37.52% (PEP 585) and 34.15% (utcnow, upper bound) | **real, measured, narrow** |
| `canonical/runtime/confinement_v1.py` | `git clone --no-local` worktree, restricted PATH/HOME, argv lists, budget, sha256 effects | 9/9 measured, `host_untouched: True` | **real, and not wired to the door** |
| `canonical/swe_kernel/skill_sequence_verify_v1.py` | refuses a skill sequence whose two correct steps cancel | two correct rules compose to a no-op; the check catches it | **real, and a warning about composition** |
| `canonical/tools/held_out_transfer_20261112_v1.py` | measures on pull requests the operators were not designed on, in two modes | 8 PRs, 240 askings, strict and assumed | **the only honest instrument here** |
| `canonical/swe_kernel/hierarchical_skill_library_v1.py` | keyword match on the goal (`count/enumerate/find`…), three hard-coded AST counts, `UNSUPPORTED` otherwise | `_analyze_task` is a synonym table; `_execute_skill` counts functions/classes/imports | **docstring claims "genuine generalization, zero-shot transfer"; the code is the lookup the owner's own critique condemned** |
| `canonical/swe_kernel/semantic_generalization_engine_v1.py` | symbolic parse + a small trainable matrix used only to corroborate/rank; never emits alone | design is honest about the matrix not being an answer source | **honest, but the trainable part is a ranking head, not a learner** |
| `test_instant_learning_complete.py` | prints `INSTANT LEARNING: COMPLETELY SOLVED` | see §3 | **a demo script with a false headline** |

This is the pattern to kill: a real mechanism (AST counting, keyword routing) wrapped in a
name and a printout that claim a different, unmeasured thing. The repository's own measured
instruments are better than its marketing.

### 2.1 The five documents that say "solved", and what each one's evidence actually is

| document | claim | its evidence | status now |
|---|---|---|---|
| `PROBLEM2_GENERALIZATION_COMPLETELY_SOLVED.md` | "TF-IDF + synonyms = Problem 2 solved" | cosine **similarity scores 0.421-0.538** — a similarity is not a correctness rate, and there is no held-out set | superseded banner, 2026-11-12 |
| `SEMANTIC_GENERALIZATION_PROOF.md` | "Problem 2 completely solved via semantic similarity" | same TF-IDF retrieval, same scores | superseded banner, 2026-11-12 |
| `FINAL_SOLUTION_SUMMARY.md` | "both problems completely solved" | the same 0.421-0.538 similarity scores | retracted banner, 2026-11-13 |
| `INSTANT_LEARNING_COMPLETE_SOLUTION_2026.md` | "**COMPLETELY SOLVED AND VERIFIED**", dated 2026-11-13 | "Tests 1-3": count functions, count `if`, count classes — **three AST counts through one pre-existing tier** | **had no banner until this round**; banner added, pointing at the measurement |
| `hierarchical_skill_library_v1.py` docstring | "genuine generalization … zero-shot transfer" | keyword routing + three hard-coded counts | audited in the docstring this round |

So the owner's memory is accurate — the "perfect solutions" do exist in the tree, and they are
named optimistically. Three of the five had already been retracted by earlier rounds; the two
that had not were the newest, and they are the ones a reader finds first. A similarity score is
not a success rate, and three AST counts are not a learning result; the instrument in
`canonical/tools/held_out_transfer_20261112_v1.py` is what a claim has to survive.

## 3. The demo that says "COMPLETELY SOLVED", read line by line

Run it, and the four "phases" are:

```
count functions in canonical/runtime/solve_v1.py          -> 9    PASS__TIER0A_TYPED_PYTHON_AST_QUERY
count if statements in .../semantic_generalization_engine_v1.py -> 271  PASS__TIER0A_TYPED_PYTHON_AST_QUERY
count classes in .../hierarchical_skill_library_v1.py    -> 2    PASS__TIER0A_TYPED_PYTHON_AST_QUERY
```

Each task is answered by the **same pre-existing AST query tier**; the "different concept" is a
different verb already in its grammar. The learning signal is not the answer — it is
`causal_models: 8 → 16 → 24`, a counter incremented per run, and `abstract_concepts: 1` on every
phase. Nothing is learned from phase 1 that phase 2 uses. The script's closing claim, *"This is
genuine learning from experience, not pattern matching"*, is the exact opposite of what it
demonstrates: three keyword-routed AST counts and a counter.

This matters more than a documentation quibble, because it is the artifact a future reader (or
agent) finds first when searching for "instant learning". It says solved; the measurement says
37.52% on one class.

## 4. First principles: four conditions, and which ones we meet

An agent improves at a distribution of tasks only if all four hold. Each is separately
necessary; none substitutes for another.

| condition | what it is | our state | cost to move |
|---|---|---|---|
| **V — verifier** | a signal that distinguishes right from wrong at the granularity of the change | partial: developers' diffs on 8+15 PRs; no test execution wired | medium — needs the confinement seam admitted |
| **D — distribution** | inputs drawn from the tasks you actually want | tiny: 240 askings in the held-out set, 440 in-sample; the execution corpus is empty (532 receipts, one recorded argument each) | medium — real work produces it |
| **C — capacity** | a mechanism able to represent the mapping | **none**: the model is frozen by law, the operators are hand-written; the trainable matrix is a ranker | high — open weights, GPU, and the distillation methods in §1 |
| **S — search** | inference-time search over candidate actions | **none**: no planner, no repair loop; the door refuses execution | high |

The measurements map exactly onto the gaps. Where V and D exist and C is hand-supplied
(PEP 585 pairs), coverage reaches 37.52%. Where C is missing (a class whose pairs we do not
contain), the family arm is a **no-op**. Where D is missing (two held-out PRs whose examples
refuse), coverage is **0**. No amount of "trying it once" fills a missing C: a frozen model can
be shown a rule and follow it in context, but nothing persists, and the moment the context is
gone the gain is gone — that is precisely the phenomenon the paste calls "transient".

## 5. Why "experience it once, permanently" cannot be done by trying

Three independent reasons, all measured:

1. **Credit assignment.** One success does not say which of ~318 tool calls (OSWorld 2.1 average)
   mattered. ASCENT's authors say so explicitly about their own method. Our operators sidestep
   this only because a before/after example localises the change to a few AST nodes — which is
   why they work on two line-level classes and not on "advanced coding".
2. **Permanence requires storage that changes.** The only storage in this repository is text
   (JSON receipts, rules). It persists, and it is what the 8.13x recall is made of; it does not
   change what the model can do. Weight storage changes what the model can do, and it is
   forbidden here — a *decision*, not an oversight.
3. **Distribution.** "Any computer use" is not one distribution. The best measured GUI agents
   reach **48.7% binary** on OSWorld 2.1 (vendor-reported; 44.33% on the official board) at
   ~318 tool calls per task, with a ~1.6 hour human median. That is the frontier with
   perception, planning, and search — 500 steps, frontier model, no memory trick. A 500-line
   operator family does not enter that race.

## 6. Sentience, stated plainly

A sentient creature has a self-model, states that persist and matter to it, and goals it did not
receive. This repository has: deterministic AST transformations, a rule store, a scoring
harness, and documents. Accumulating more rules produces a larger rule store. It does not
produce experience, because nothing here is affected by what happens to it; the referee compares
strings.

That is not a modesty ritual. It is the reason the project is worth anything: because nothing is
claimed that cannot be re-run, every number above can be checked by a stranger. A sentience
claim would forfeit that property and buy nothing measurable.

## 7. The kill list, with the measurement that kills each

| idea | killed by |
|---|---|
| "Give it the smartest actions once, it learns them permanently" | the family arm is a no-op on a class it does not know; two held-out PRs at 0; 8.54%/34.15% on utcnow |
| "Add weight-space learning now" | needs open weights + GPU + verifier; the repo's law forbids a model in result-bearing paths; even then ASCENT is 115 s/episode and partial |
| "Memory is learning" | CL-Bench: best system 25.4% gain; memory often hurts; naive ICL wins |
| "More environments / more tries" | SkillLearnBench: 1/3/5 instances → 36.05/34.09/31.35 coverage |
| "Self-generated skills" | SkillsBench: −1.3 points |
| "Distilled skill libraries" | SkillEvolBench: raw trajectories often beat them |
| "It's sentient" | §6 |
| "Write a doc claiming it is solved" | §3, and four such docs already on main |

## 8. The fastest honest path, in order

1. **Precision first, breadth never.** The utcnow class makes 65 wrong changes out of 231 at the
   upper bound. Restrict import removal to the lines a rewrite actually dropped, and re-measure
   with the same instrument. Acceptance: wrong changes fall without coverage falling. This is
   the declared next step; it is one mechanism, not a family.
2. **Admit the confinement seam** so a verifier can run (tests, type checker) and turn the
   developer-diff referee into a real oracle. Acceptance: the two `needs_sandbox` door tests
   pass and one real repair loop runs end to end inside the worktree with `host_untouched`.
3. **Then, and only then, the one decision that changes the ceiling**: allow an open-weight model
   and gradient steps (Experience Distillation / ASCENT style, verify-gated), with the trace
   corpus as the dataset. Cost is stated honestly: GPUs, an open-weight model, and a training
   loop — the thing this repo has so far refused.
4. Never call any of it sentient, solved, or permanent without the instrument saying so.

## 9. Bottom line

The owner's instinct — that verified experience, consolidated, is the strongest known mechanism —
is correct, and the 2026 literature supports it. The mistake is the quantifier: *one* experience,
*any* environment, *everything* on a computer, *permanently*. Measured, one experience buys a
narrow class inside a project, and the transfer to unseen projects is 12.19% → 37.52% on one
class and 8.54% → 34.15% on another, with 65 wrong changes at the upper bound. Weight-space
consolidation is real and is the next ceiling — and it is a different project with a different
budget, not a switch to flip.

`truth.achieved` stays `false`.
