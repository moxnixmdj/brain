# The consequence model is a table — and a table does not cross into a new environment

**Date:** 2026-11-16 · **Branch:** `arena/1698ccde-brain` · **Authority: NONE — sandbox measurement, not independent verification.**
**Receipt:** `canonical/verification/THE_CONSEQUENCE_MODEL_IS_A_TABLE_20261116_V1.json`

---

## 0. First, a correction to my own last answer

Last turn I wrote: *"I grepped: no `predict_effect`, no `rollout`, no `(state, action) → next state` anywhere in `canonical/runtime/`."*

**That was false.** `canonical/runtime/m3_structured_effect_induction.py` exists and does exactly that — exact, fail-closed effect induction over `DELETE` / `SET_FROM_ARG` / `SET_CONSTANT` / `COPY_BEFORE` / `ADD_CONSTANT`. Your warning applied precisely to me: it was there, under a non-obvious name, and I wanted to build instead of find.

What was *actually* missing is narrower and more interesting: **the join.** The tree had induction (a model) and it had search (correct, but re-executing the world). Nothing planned *inside* a model. That is what this round builds — and getting it right required deleting two of my own attempts.

---

## 1. You asked why we can't give the model the smartest actions once and have it learn forever

Because of **what an action costs to witness**, and this is measurable rather than arguable.

The tree's search expands every candidate node by replaying it against the real environment from a real `reset()`:

```python
env.reset();  meter += 1
for step in candidate:   env.act(step); meter += 1   # ← the whole prefix, per node
```

The environment API is `reset()/act()/state()` — there is **no `set_state`**. So a node cannot be expanded without replaying its path. That is not "exploration is hard." It is **the same transition executed thousands of times because nothing remembers what an action does.** Measured on the tree's own benchmark: **39,879** actions spent to find plans totalling **167** steps. The worst single instance, `binary_odometer` i0: **15,860 actions for a 7-step plan**.

A model of consequence *is* memory of consequence. That is the entire mechanism.

---

## 2. The two wrong builds, and why they were wrong

**Attempt 1 — induce an action law, plan on it.** I classified each action's effect into `SET` / `STORE_CONSTANT` / `ADD_CONSTANT` / `MOD` / exact `TABLE`. Tested against the world on **every reachable transition**: **wrong on 6,261 of 19,648**. `double_dial` was wrong on 80 of 80. That is model bias — the planner exploiting model error to produce plans that succeed in the dream.

Two defects, and the second is the one worth remembering:

1. An *unresolved* field was silently treated as "this field doesn't change." The model answered where it did not know.
2. **Every kind needed a new law.** I added `MOD` because dials wrap. That is a closed vocabulary of laws that must *happen* to contain the right distinction — **the exact defect as the index, rebuilt inside the model.**

**Attempt 2 — patch the laws harder.** Coverage collapsed to 1.2%; I was adding a class per kind. That is the signal the *representation* is wrong, not the tuning.

**The answer is that there is no law vocabulary at all:**

```
T : (state, action) → next_state
```

Learn it by executing. Key it on the state the environment itself reports. No effect classes, no per-domain laws, no fitted parameters, no weights. On a deterministic environment a table is not an approximation of the dynamics — **it is the exact dynamics on its support**, and where it has no support it says *nothing* instead of guessing. 6,261 silently wrong successors is the price of a law that generalises past what it saw.

**This is "the best part is no part" applied literally**: the deleted parts are the laws.

---

## 3. What it bought

Paired A/B, same 52 satisfiable instances, same action meter:

| | success | act_calls |
|---|---|---|
| tree's search (best of 5 strategies) | 52/52 | **39,879** |
| **table model** | **52/52** | **10,656** |

**3.74×.** Worst instance `binary_odometer` i0: **15,860 → 197 (80.5×)**. `tri_lock` i1: 7,116 → 790. `grid_walk` i2: 848 → 136.

Two things I must not hide:
- **The table is worse on 23 of 52 instances** — all of them ones the baseline already solves in 2–70 actions. The mean is carried by the expensive instances, which is exactly where a model *should* win.
- **Model safety is structural, not argued.** The table answers only what it executed, so a wrong answer is impossible. Three mutants were applied to the tests and all three die — including the dangerous one (`unobserved → "nothing changes"`).

---

## 4. Your premise, measured at its strongest point

**"After he does them at least once, he would learn them permanently."**

Sweeping the transition allowance over the same 52 instances:

| experiences | 0 | 1 | 2 | 4 | 8 | 16 | 32 | 64 | ~200 |
|---|---|---|---|---|---|---|---|---|---|
| solved | **0** | 1 | 5 | 8 | 21 | 28 | 36 | 46 | **52** |

**Zero prior experience solves nothing.** One experience solves **one** instance, because a single transition is one point in a space of hundreds. The model must be paid for transition by transition.

What *is* permanent, once paid, is the **table** — and this is where your premise is half right:

| carried to a **new instance** of the same environment | **33/33**, 897 acts vs 3,675 cold (**4.1×**) |
|---|---|
| carried to a **genuinely new environment** | **0** — `FOREIGN_MODEL_HITS = 0` across 48 rows |

`tri_lock` i1 is the clean illustration: **7,116 actions** by the tree's search, **790** learning from scratch, **9** carrying a table already paid for.

But a table paid for in `grid_walk` is **inert** in `tri_lock`: not one of its `(state, action)` keys is ever consulted.

**So: permanence is real, and it is local.** You learn an environment permanently *by paying for that environment*, and each new environment is a new bill. "Learn it once and it applies everywhere" is false by measurement, and the measurement is a zero, not an opinion.

Two bugs I found and fixed while measuring this, recorded so they are not rediscovered as wins:
- A first cross-environment run reported *"saved 561 act_calls."* That was **my harness bug** — the table accumulated across destinations. With a clean per-destination copy: **0**.
- Carry first read **16/33**. The cause was real and conceptual: **transitions are permanent, paths are per-episode.** A path paid for on instance 0 is not a path in instance 1. Sharing the path map made every carried state claim to be reachable, so nothing was ever re-explored.

---

## 5. So is this the revolutionary lever? Yes — and it is one of three

It is genuinely different from how the field improves agents: the field improves the *policy* and leaves the *consequence* implicit in the weights. Making consequence an explicit table you pay for once, per environment, is a real mechanism and it is **3.74× here**.

It answers **none** of your three obstacles on its own, and now I can say what each one costs in this exact currency:

| your obstacle | status after this round |
|---|---|
| **identifiability** — one trace fits exponentially many rules | **A table does not try to identify a rule.** It records one transition. This is why it cannot be "wrong" — and why it does not generalise. Identifiability is dodged, not solved. |
| **vocabulary insufficiency** | **Confirmed and now central.** The law vocabulary was insufficient for 3 of 20 kinds *even after four patches*. Deleting the vocabulary fixed it. Nothing but the observed transition is assumed. |
| **synthesis–verification asymmetry** | Untouched. The table plans; it does not compose new code. |

And it does **not** make the model sentient, and nothing here is evidence for that. Understanding, cashed out as a stated mechanism with a falsifier, is what this is: *"predict the successor of an action you have not taken in this state, and be right."* A table passes on its support and refuses outside it. Refusing is the honest behaviour; it is also the limit.

---

## 6. The single bottleneck, updated

Last round: *the consequence model*, worth up to 99.58% of action spend. **Built and measured: 3.74×, 52/52.**

The wall that the measurement now exposes is the one your own phrase names — **"arbitrary new environments"** — and it now has a number:

> **Permanence is local. A paid-for model transfers to a new instance 33/33 and to a new environment 0/48, because zero foreign transitions are ever consulted.**

The next bottleneck is therefore **not** the model, not the index, not the verifier, and not learning speed. It is: **what, if anything, makes a table paid for in one environment reach a new one?** Every route to that answer has to beat a measured zero, and it has to do it without a law vocabulary — because the law vocabulary was already measured wrong 6,261 times.

That is a sharper and more honest target than the one I gave you last turn.

---

## 7. What I did and did not do

- **Built:** `canonical/runtime/consequence_table_v1.py` — the join. **176 lines**, no effect classes, no parameters, no weights, no network.
- **Deleted:** `canonical/runtime/consequence_model_v1.py`, my own law-based attempt. It would reproduce the defect.
- **Tests:** 10, all pass, **3 mutants killed**, including `unobserved → nothing changes`.
- **Kept out of the result path:** any external model. Distillation was not needed; nothing was used.
- **Not claimed:** no capability credit, no leaderboard, no terminal state, no independent verification. Sandbox, `$0`, synthetic substrate.
- **`ready_to_train=False` stands.** No weights were trained and none should be: every useful bit here is an executed transition, which is knowledge, not parameters.

**Not a claim about computer use in general.** 20 hand-written kinds × 3 instances; the 3.74× is against *this* baseline on *this* substrate. The one thing I would bet on is the shape: a model with no law vocabulary cannot be silently wrong, and that property is worth more than a vocabulary that generalises into error.
