# One experience is enough — but only with three things this repository does not have

**2026-11-13** · branch `arena/bfec7b31-brain` · base `97e38b32` · **authority: NONE**
`truth.achieved` stays `false`. No capability registered, no family flipped, no weights updated,
`$0` spent. This note adds no new internal measurement. It does one thing the earlier notes could
not: it replaces citation-from-memory with a **pinned external evidence ledger**, and it reports
the defect that pinning immediately exposed.

New instrument: `canonical/tools/external_evidence_ledger_v1.py`
New record: `canonical/research_sources/EXTERNAL_EVIDENCE_LEDGER_V1.json` (5 full rows, 11 compact, 2 drift records, 3 unsourced claims)
New tests: `canonical/tests/test_external_evidence_ledger_v1.py` (19, all offline)

---

## 0. The answer to the question as asked

> "Give our model the most advanced coding actions, let it experience them once, and it learns them
> permanently. Doesn't that solve everything on a computer?"

**You are right about the mechanism and wrong about what it is missing, and the gap between those
two is measured.**

| what you said | verdict | the pinned evidence |
|---|---|---|
| An agent can execute a task **once** and keep the gain permanently | **TRUE — published, and it works** | ASCENT (2610.05303): *"The agent executes each task once, in one pass over the stream, and the executed trajectory with its verification result is the only learning signal for weight updates that persist across tasks."* |
| The obvious version of that idea works | **FALSE — it recovers 3.8%** | Experience Distillation (2607.21051): SFT on the collected experience recovers **3.8%** of the ICL gain; the correct construction recovers **64.8%+**. Same experiences. Different target construction. |
| Therefore more/better actions is the lever | **FALSE — actions are nearly free** | Agent S4 (2610.28601) got **3.8×** on OSWorld V2 by evolving *interfaces*, same model. StateAct (2607.22798) got **+6.3 pts** by changing where the agent looks. Neither added an action. |
| Therefore it generalises everywhere | **FALSE — measured on one scale** | Continual-ARC (2611.14505): *"No harness-based method gains on unseen tasks, whereas weight-based learning shows substantial gains."* Most harness methods score **below a cache-the-demonstrations floor.** |
| Therefore we solve any computer use | **FALSE, and orthogonal** | OSWorld 2.0 (2606.29537): best agent is **20.6% binary / 54.8% partial** on 108 real workflows. Its own failure taxonomy is *not* "couldn't emit the action". |
| We built a sentient creature | **NOT A MEASURABLE CLAIM** | nothing in this tree measures it, and nothing needs it. §5. |

The one sentence: **one experience is enough to learn from — it is not enough to learn *what
applies* from.** Your sentence is missing the three conditions under which the published version of
your sentence actually works.

---

## 1. The three missing conditions, from the papers that make your idea work

ASCENT is your idea, implemented properly, and it names all three:

1. **A verification signal at task end.** *"the executed trajectory with its verification result is
   the only learning signal"*. Without an oracle, the one experience is not evidence. This is why
   `ADMISSION_IS_THE_BOTTLENECK_20261113_V1.md` measured a lesson going ACTIVE after repairing one
   unseen program and breaking another.
2. **A target construction that is not imitation.** *"Directly imitating or reinforcing the
   generated tokens of this single attempt destabilizes the policy."* The teacher must be a **frozen
   copy** given the trajectory as hindsight. The naive construction — train on the trajectory you
   just produced — is the 3.8% arm.
3. **A substrate that persists the change.** ASCENT writes **persistent LoRA fast weights**. This
   repository writes Markdown, JSON and Python predicates. That is a legitimate substrate for
   procedures and it is the wrong one for *policies*.

Two more papers make the same point from the failure side, both published inside the last month:

- **FGSE** (2611.14326, 10 Nov 2026) is this repository's thesis, published by someone else:
  *"current self-improvement mechanisms often write episode-derived lessons directly into memory,
  making local success an unreliable signal"*. Its fix is the fix this tree already built —
  precondition, temporary application, falsification and regression probes, then commit or reject —
  and with it, harmful committed updates fall to **3.6%**, regression damage to **1.3%**.
- **Self-generated feedback destabilises TTT** (2610.05076): retaining generated-text updates makes
  prediction on *independent human text* worse, across 125M/760M/3B; checking the candidate on
  independent evidence before commitment removes the damage.
- **KEEL** (2610.34043): verifier evidence turns success into skills and failure into lessons, and
  the gain is **+4.2 to +21.7 pp** against **+2.4 to +9.6** for the accumulate-and-hope default.

So the frontier position in November 2026 is not "learn once, keep forever". It is: **hypothesise,
falsify before committing, version what survives.** Accumulation without a gate is measured to be
worse than a cache.

---

## 2. Why "more experience, faster" is the wrong lever — from first principles

Learning a task is compression, and a compression is only worth making when

```
expected cost saved on future instances  >  cost of forming and validating the abstraction
```

Three factors multiply, and multiplying is why speeding one of them up does nothing:

| factor | what it is | who is optimising it | is it the binding one? |
|---|---|---|---|
| **acquisition** | cost of one more experience | "let it try things, in every environment" | **no** — already the cheapest, and falling |
| **identifiability** | how much of the task *one* experience pins down | this is what `one_shot_identifiability_probe_20261112.py` measures | **YES** |
| **verification / credit assignment** | can you tell right from wrong, and which step caused it | the admission gate | **YES, and it gates the other two** |

The measured version of the middle row, already in this tree: one showing teaches the **names**,
two showings teach the **shape**, and only the shape transfers. At two showings the corpus stands at
**166/182 strict answers with 16 questions left**, and the census found that most of the residue is
*unknowable from the evidence shown* — the information-theoretic price of example-bound learning,
not a bug. On held-out pull requests the best arm is **37.52% coverage at 76.36% precision**, with
two of eight PRs at zero.

You cannot fix identifiability by experiencing more of the same kind faster. One point does not
identify a function; it identifies the equivalence class your prior already had. That is why the
"semantic generalisation" was a lookup — the prior *was* the lookup.

**Therefore the two levers that actually move the number are:**

1. **Improve the prior** — train weights on verified traces. This is the only arm that gains on
   unseen tasks (Continual-ARC). It is blocked here by the repository's own $0 / no-model-in-
   result-bearing-paths rule. That is a decision the owner must make, not a fact about the world.
2. **Make the task identifiable** — change what the agent can see and do so that one experience
   carries more bits. This is free, and it is where 2026's largest measured wins came from:

| change | measured effect | source |
|---|---|---|
| evolve the **interfaces**, select on held-out validation | **3.8×** on OSWorld V2, same model, above GPT-5.5 and Opus 4.8 | 2610.28601 |
| ground action in **program state** rather than pixels | 20.6% → **26.9%** binary, **~9× cheaper** per task | 2607.22798 |
| gate admission with **falsification probes** | harmful committed updates → **3.6%** | 2611.14326 |
| curate the knowledge instead of self-generating it | **+16.6 pp** (v4); self-generated often negative | 2602.12670, 2605.24117 |

Read the third row carefully, because it is the uncomfortable one: **curated** procedural knowledge
is worth a great deal and **self-generated** procedural knowledge is worth approximately nothing, or
less. That is precisely the difference between "the model experienced it once" and "someone who knew
what the answer was wrote it down once".

And read the OSWorld 2.0 failure taxonomy, because it is the actual target list for "anything on a
computer" and not one entry in it is an action the agent lacked:

> *"they lose track of constraints, miss information that arrives mid-task, guess rather than ask
> the user, and skip verification, struggling most when a task hinges on hidden state they must
> recover."*

Hidden state recovery, mid-task information, asking instead of guessing, verification. Four
capabilities. The bottleneck is not the action vocabulary.

---

## 3. The defect that pinning the citations exposed

Nothing in this tree recorded a paper's **version**. The ledger found two live defects:

- **SkillsBench (2602.12670).** Seven documents repeat *"+16.2 pp, self-generated −1.3 pp, 16 of 84
  tasks"*. That is an earlier preprint. Current is **v4**: 87 tasks, **+16.6 pp**, pass rate
  33.9% → 50.5%, and the current abstract **does not carry the self-generated arm at all**.
- **SoK: Agentic Skills (2602.20867).** The `−1.3 pp` number is attributed to this survey. The
  survey carries the *direction* — *"self-generated skills may degrade them"* — and not the number.
  That is a citation of a summary of a measurement: two steps from the measurement.

Neither number is false. Both are **stale or second-hand**, and they were repeated as current fact
across the corpus, including in documents that argued the strategy. Do not rewrite the dated
records — they are records of what was believed. The ledger carries the correction in one place, and
the census now reports every citation the tree has not audited: today **139 citations, 65 pinned, 74
unpinned over 45 ids.**

Also recorded, because it is worse than a stale number: **three quotations in the strategic prose
have no primary source at all** — the "five-level continual learning spectrum", the "memory models
trained with memory-native RL" quotation, and a "model-free one-step distillation" sentence that is
a review site's paraphrase of a real paper. The ladder is a reasonable summary. It is *this
repository's* summary, and it was being read as a citation. A project that steers by its own prose
is steering by nothing.

---

## 4. So what is the smartest thing to do

Not more environments. Not more operators. Not more documents. Ranked by information per dollar:

1. **Adopt FGSE's protocol as the admission spec** (2611.14326). The tree already has the parts —
   preconditions, temporary application, probes, commit/reject — scattered across three modules and
   one round-22 diagnosis. Making it one named gate, with its 5.0% / 1.3% / 3.6% targets as the
   acceptance test, converts the strongest published result into a local measurement.
2. **Attack identifiability by construction, not by exposure.** State-grounding and typed interfaces
   are the two largest measured wins of 2026 and both are $0. For this tree that means: prefer
   reading program state over parsing prose reports, and prefer a typed tool interface over a
   natural-language instruction.
3. **Build the held-out distribution before building anything else.** The project's own PREREG
   series says this; nothing since has improved on it. Every number that improved in this tree
   improved against a distribution the operators were designed on.
4. **Only if the owner lifts the $0 / no-model rule:** ASCENT's recipe, in ASCENT's order —
   verified single-attempt trajectories, a frozen copy as hindsight teacher, persistent LoRA, and
   weekly forgetting checks. Not SFT on the trajectories. That arm is 3.8%.
5. **Do not** buy breadth, longer context, more organs, or background runs. Measured to buy nothing
   before 1–3 exist.

---

## 5. On the sentient creature

Nothing here is a step toward sentience, and no measurement in this repository bears on it. What is
real and measurable is **continuity**: state that survives restart, a self-model that predicts its
own next action, and goals that persist. `living_self_model_probe_v1.py` measures the middle one.
That is a creature in the engineering sense — an agent with identity and history — and calling it
sentient does not add a capability, it removes a falsification test. The goal you actually stated —
anything on a computer, including advanced software engineering — is not advanced by the word.

---

## 6. What this note does not claim

No new internal measurement was run for it. The external numbers are as reported by their authors,
at the versions pinned in the ledger, read on 2026-11-13, and **not independently reproduced here**.
`authority: NONE`, `truth.achieved: false`. The ledger is one producer reading abstracts on one date;
it is worth exactly that, and it is worth more than what it replaced.
