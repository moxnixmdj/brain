# Am I right or wrong? — the answer, measured

**Date:** 2026-11-12 · **Base:** `2f8ef387` · **Cost:** $0 · zero model calls
**Question:** *"Instant learning + instant learning in new arbitrary environments — we already solved
those perfectly. Doesn't this mean this is a perfect solution for all the problems… Can't we just give
our model the most advanced coding actions and let him experience them once and then he will learn them?"*

---

## 1. The verdict, stated plainly

**You are right about the mechanism and wrong about the magnitude — and the error is load-bearing.**

Right: experience-once → permanent procedure **is** a real, viable, state-of-the-art approach. It is
what Voyager does, and it is still the reference point in 2026. You did not invent a fantasy. You built a
real thing.

Wrong: that it is **sufficient**. A learned procedure is a **memory**, and memory alone cannot tell you
which memory applies. That gap is not a bug in your design — it is the central unsolved problem in the
entire field in 2026, and this round **measured it inside your own system**, on a task a human would call
trivial.

And the sharper thing your diagnosis got exactly right:

> *"Our 'semantic generalization' can only handle tasks with very similar wording."*

Yes. And it is worse than "very similar wording" — it is **word-set overlap**, which is blind to the one
word that carries the meaning. Demonstrations in §3.

---

## 2. What "learning" in this system actually is

Three facts, from reading the code, not guessing:

**Fact 1 — The act path has no model in it.** 2,192 modules under `canonical/runtime`. The routing,
binding and execution path (`grounded_action_v1` → `goal_compiler` → `world_binding_v1` → adapter) imports
**no model client at all**. Every `openai` / `anthropic` / `litellm` reference in the tree lives in
*vendored donor code* (`canonical/capabilities/internalized/…/stirrup/`), not in the path that acts.

**Fact 2 — `procedure_memory_v1.signature()` is a bag of stemmed words.**

```python
def signature(text):
    words = sorted(set(content_words(text)))     # <-- a SET of words
    pair  = direction(text)                      # (verb, src, tgt) if the sentence states a conversion
    return "+".join(words) + (f" >>{verb}:{src}->{tgt}" if pair else "")
```

`learn()` keys the memory on that string. `recall()` ranks by Jaccard over it.

**Fact 3 — Paths are stripped out before signing.** `_PATH_WITH_DIR.sub(" ", …)`. So **the file a task is
about is not part of the memory key.**

---

## 3. The measurement that settles it

Fixture: `canonical/runtime/world_binding_v1.py` — **28 functions, 97 if-statements, 1029 lines**.
Accuracy ground-truthed with `ast`, not estimated.

```
count the {if statements | functions | lines | classes
           | imports | comments | todos | characters} in <file>
```

| asked | answer returned | truth | reported |
|---|---|---|---|
| if statements | 28 | **97** | `VERIFIED_ACTION` |
| functions | 28 | 28 | `VERIFIED_ACTION` |
| lines | 28 | **1029** | `VERIFIED_ACTION` |
| classes | 28 | ok | `VERIFIED_ACTION` |
| imports / comments / todos / characters | 28 | **wrong** | `VERIFIED_ACTION` |

And the cleanest single case:

```
count the lines in README.md      ->  VERIFIED_ACTION, answered 51684
README.md actually has              223 lines
```

**Eight questions. One answer. Every one "verified".** The capability matched on the word **"count"** and
never once looked at what was being counted. `selected_because: GOAL_WORD_AGREEMENT`.

Nothing in that chain lied. The adapter counts defs and classes and reported 28 truthfully. The verifier
re-ran it and it agreed. The row's postcondition — *an answer was produced* — was met. **The failure is a
missing comparison between what was asked and what the row can do**, and that is precisely the thing a
procedure library cannot supply for itself.

### The same blindness in the learning layer

Learn one procedure, then ask for a *different file*:

```
learn("count the if statements in world_binding_v1.py")
recall("count the if statements in composer_route_v1.py")   ->  similarity 1.000
learned signature:  count+if+py+statement        (identical for BOTH files)
```

Because paths are stripped, **two different files are the same memory**. And the ranking is *inverted*:

| sentence | similarity |
|---|---|
| correct paraphrase | 0.429 |
| **"add** an if statement" (a *mutation*, not a count) | **0.600** |
| **different file** | **1.000** |

A request to **modify** code scores *higher* than the correct paraphrase of a request to **count** it.
This is not a tuning problem. There is no representation in which "add" and "count" are different
operations and "file A" and "file B" are different objects.

---

## 4. What the field says in 2026 — you are not behind, you are at the frontier's edge

Every source below was fetched this session.

- **Retrieval-Augmented LLM Agents: Learning to Learn from Experience** (EMNLP 2026) — the finding that
  matters: agents fine-tuned on easy tasks suffer **generalization collapse** on hard ones; they "memorize
  specific action sequences rather than learning the underlying logic." Retrieval *plus* training beats
  retrieval alone. → **Experience retrieval is a foundation, not a solution.** [1]
- **SkillRevise** (2026) — one-shot generated skills: **36.05% → 39.53%**. Three rounds of execution-grounded
  revision: **61.63%**. *"One-shot skill generation is not a reliable substitute for revision."* → **One
  experience is not enough by a factor of ~22 points.** [2]
- **Library Drift** (2026) — LLM-authored skills **+0.0pp**; human-curated **+16.2pp**. Unbounded
  self-authoring does not compound. → Autonomy without a verifier in the loop yields nothing.
- **Demystifying Agent Skills** (8,135 trials) — retrieval precision collapses **29.6% → 3.3%** as the
  pool grows; *retrieval, not authoring, is the bottleneck.* An agent need not invoke the correct skill to
  succeed. → The library is not the hard part. The **lookup** is.
- **Agent Skills research summary** (2026) — names your exact failure: *"two skills with similar
  descriptions start triggering interchangeably… the output looks reasonable BUT the wrong skill ran."*
  → That is `count the lines` returning 28, described from the outside. [3]
- **Voyager** (2023, still the reference) — its skill library is indexed by **embedding of a description**
  and retrieved by **semantic similarity**, and its own paper reports stronger generalization *because the
  LLM writes and revises code with execution feedback*, not because the library is self-sufficient.

**The convergence is unanimous:** procedural memory is real and works; **one-shot is not enough**;
**retrieval is the bottleneck**; and every working system keeps a **model** in the loop to judge
applicability. The 2026 position is *retrieval-aware training*, not *memory instead of reasoning*.

---

## 5. So — "can't we just let it experience each action once?"

**Not yet, and the reason is precise.** In this system the missing piece is not experience. It is that
**nothing can decide which experience applies.** Give it a thousand perfect procedures and the current
lookup will:
- treat two different files as one memory (`similarity 1.000`),
- rank a **mutation** above a **count** (`0.600` vs `0.429`),
- and certify an answer to a different question as `VERIFIED_ACTION` (8 for 8).

More experience makes those errors **more** likely, not less — because a bigger library is a bigger set of
similar-looking wrong answers. The research above measures exactly this: precision falling to **3.3%**.

> **You do not have a learning problem. You have a decision problem wearing learning's clothes.**

---

## 6. What I changed this round (not advice — landed)

**1. A stated shell command now reaches the shell** (PR #6813, merged `a89c5bb5`).
`shell.command.run` required nothing, scored **highest of all candidates (20.0)**, and was refused on
**every** command sentence behind four defects in series. Two more appeared once commands ran: `cat a > b`
printed both files and reported success; `ls | head -2` was answered by **bisecting repository history**.
All closed. Six tasks refused last round now work.

**2. A count of the wrong thing is now refused, not certified** (this PR).
`world_probe_v1.entity_contradiction` — a row declares the entities it can count, and a counting question
it cannot answer is **refused instead of answered wrongly**.

```
before:  functions 28 ✓   if statements 28 ✗   lines 28 ✗   README lines 51684 ✗   (all VERIFIED)
after:   functions 28 ✓   classes 28 ✓         if statements REFUSED   lines REFUSED   imports REFUSED
```

It is deliberately **not** a question-answering engine. It adds no counting. It moves the machine from
**confidently wrong** to **honestly unable** — the only honest improvement available while the decision
layer is a word-set.

The expressibility baseline moved **15 → 14** and is *documented as a correction*, not bent: the
fifteenth "success" was the README false pass. Over the 22 touched test files the failure set is back to
its **exact baseline of 6, with zero new failures**.

---

## 7. The smartest thing to do next — in order

**1. Put a model in the decision loop, narrowly.** Not to replace the deterministic path — to answer the
one question it cannot: *does this procedure apply to this request?* That is a single yes/no classification
with the retrieved procedure and the sentence in view. Everything downstream stays verifiable, so a wrong
model answer costs a **failed verification, not a wrong answer**. This is the highest-leverage change
available and it is the one the 2026 literature unanimously supports.

**2. Stop stripping paths from the memory key.** A procedure about file A is not a procedure about file B.
This is a one-line fix with an outsized effect, and §3 shows today's behaviour is worse than random
(different file = **1.000**).

**3. Make `VERIFIED_ACTION` require an effect about the named object.** `returncode == 0` and "an answer
was produced" are not answers. `UNJUDGED` already exists in the code and is unused. This is the check that
would have caught 51,684 for a 223-line file automatically.

**4. Only then scale the library.** Retrieval precision falls to 3.3% as pools grow. Growing the library
before fixing the lookup guarantees the failure gets worse.

---

## 8. On "sentient creature"

Nothing in two rounds of measurement found a mechanism that *produces* an action. Every improvement came
from **removing an obstacle between a decision and an effect**, or from **refusing to lie**.

> A sentient creature that cannot move its hand is not less sentient. It is a creature that cannot move
> its hand. The fix is not more sentience — it is connecting the nerve.

The honest position: this is a **deterministic execution substrate with a word-overlap lookup**, and that
substrate is genuinely good — verifiable, $0, reproducible, and now able to run stated commands and refuse
unanswerable questions. It is not a learner in the sense the claim needs, because **learning requires
deciding what was learned**. That is the missing organ, and it is one narrow model call wide.

---

## References

[1] Ferraz et al., *Retrieval-Augmented LLM Agents: Learning to Learn from Experience*, EMNLP 2026 —
https://aclanthology.org/2026.emnlp-main.57/
[2] *SkillRevise: Improving LLM-Authored Agent Skills via Trace-Conditioned Skill Revision*, 2026 —
https://arxiv.org/html/2606.01139v3
[3] *Agent Skills Work But The Research Shows Most Teams Are Building Them Wrong*, 2026 —
https://thenuancedperspective.substack.com/p/agent-skills-work-but-the-research
Also: *SkillRL* (https://arxiv.org/html/2602.08234), *Library Drift* / *Demystifying Agent Skills* /
*SkillOps* (see prior rounds), *Voyager* (https://arxiv.org/abs/2305.16291).
