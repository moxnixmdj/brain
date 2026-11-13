# The layer you named is the right layer, and it is not the bottleneck

You pasted an analysis that says: token-space learning is one layer, weight-space learning is the
other, and the missing piece is weight updates. **That analysis is correct, and every citation in it
is real.** I checked all four against 2026 sources before answering, and I measured what this repo
would have to feed such a layer.

The conclusion inverts the plan, though. **The engine is not what is missing. The fuel is.**

---

## 1. Your citations are real — verified, not taken on trust

| the claim you pasted | what the paper actually says | does it support the plan? |
|---|---|---|
| ASCENT, Oct 2026: trains weights on its own execution trajectories during deployment | arXiv **2610.05303**: self-distils **verifier-accepted** trajectories into persistent LoRA. 69.5% ± 5.6 vs **46.4%** base on ALFWorld, 4B scale. Gains grow later in the stream and transfer to held-out scenes | **Yes** — but the learning signal is *verification*, and the method "assumes a terminal verification signal" (its own stated boundary) |
| Experience Distillation, Jul 2026: converts transient ICL gains into permanent weights, model-free, one-step | arXiv **2607.21051**: retains **64.8–93.4%** of ICL gains, vs **3.8%** for direct SFT on the same experience, at **9.6× fewer** environment samples | **Yes** — and the 3.8% is the part nobody quotes: *naive* fine-tuning on experience barely works. The gain is in the distillation method, not the weights |
| Continual Learning Spectrum: memory ← we are here, post-training ← ultimate goal | Consistent with the memory-reuse literature I measured earlier (2604.27003, 2611.14320, 2609.12655) | **Yes** |
| Memory Models, Jun 2026: agents that learn will be *memory models*, trained with memory-native RL | Directionally consistent; memory and weights are being merged in that line of work | **Yes** |

So: not hype, not wrong. And one thing you should hold onto — **the same papers say the hard part is
the verifier, not the update.** ASCENT's own boundary section says learning from one trajectory "can
still be sensitive to noise and failure modes" and that extending it "to weaker, delayed, or more
open-ended feedback will be essential before online agent training can become routine in
deployment." **That is exactly our situation.**

## 2. The cost of adding weights without a verifier, measured by other people

This is the part that decides the order of work, and it is brutal:

* **TRACE benchmark:** LLaMA-2 13B sequential fine-tuning took GSM8K from **28.8% → 2%**. Not
  degraded — erased. Nobody noticed until something downstream broke.
* **OSFT (ICLR 2026):** on an 8-task TRACE sequence, standard fine-tuning reached **23.0%** average
  accuracy; OSFT reached **48.4%**. The same data, opposite result. The difference was *structure*,
  not compute.
* **Naive shared LoRA across 5 domains:** prior-task loss **+42.96%** drift (one seed: +351%, the
  legal domain's held-out loss 0.17 → 1.18).
* **Reinforcement fine-tuning vs SFT in continual post-training:** SFT **−10.4%** forgetting
  (ScienceQA 95.2% → 76.1%); RFT **−1.8%** and preserved general capability.

The lesson is not "weights are bad". It is: **weights make learning permanent, including the
mistakes.** A token-space lesson that is wrong costs one wrong edit and is visible in the file. A
weight-space lesson that is wrong costs a capability you had yesterday and cannot see leaving. Which
means the ordering in your pasted analysis — *option 3, combine both* — is right about the
destination and wrong about the sequence. **You cannot safely add the layer that makes errors
permanent while the part that detects errors is missing.**

## 3. What I measured: this repo has a real event stream, and it is thin

I built a gauge (`canonical/tools/weight_space_fuel_v1.py`) that counts what a shaper could actually
train on, and reported `NOT_COUNTABLE` where it could not count. Two of its first versions were
wrong, and the corrections are the point:

| source | records | units | of those verified | verdict |
|---|---|---|---|---|
| execution receipts | 305 | **0** | 0 | NO_SIGNAL |
| the hand-seeded trajectory store | 24 | 66 | **0** | NO_SIGNAL |
| taught-action corpora | 0 | 0 | 0 | NO_SIGNAL |
| **controller checkpoints** | 449 | **192** | 64 | **THIN_BUT_REAL** |

**My first answer was "there is nothing to train on." That was wrong**, because I had not looked at
`canonical/astra_runtime/state/`. Those 449 files hold **320 agent steps**, each a
`{plan, declared_plan, result}` triple with a committed `expect` — a real (situation → action →
verdict) shape. Of those, **128 are `finish` steps with no verdict by design**, leaving **192 work
steps: 175 passed, 17 failed — an 8.9% real failure rate.**

That 8.9% matters more than the count. **It is the natural label split a shaper needs**, and it is
the exact opposite of the hand-seeded store, which is 100% success and therefore cannot teach a
policy where to stop. Compare with the ASCENT precondition: a verified stream. We have one. It is
just small.

**Scale, honestly:** 192 units, ~20 distinct capabilities, 87 distinct situations. The threshold where
a held-out split is even meaningful is around **5,000 units**. We are at **258 total, 64 verified —
about 4% of the way.** Meanwhile the repo *produces* **2,790 changed lines per merge** and throws that
shape away, because it keeps the lesson and not the change.

## 4. Where your analysis is wrong — three specific things

1. **"Memory systems ← we are here" understates what we have.** Memory here is not a lookup table:
   one demonstration is measured at **0.529 of a real developer's work with 0 wrong changes** on 12
   merged PRs, and a second showing takes it to 0.891. That is a genuine learning mechanism, not a
   retrieval cache. The token-space layer is further along than the spectrum suggests.

2. **"Weight updates are the missing piece" is half right.** The missing piece is
   **verification-grounded fuel at scale**. ASCENT is not "train on trajectories" — it is
   "self-distil *verifier-accepted* trajectories with a frozen teacher". Run directly on trajectories,
   RFT still forgets by −1.8% and SFT by −10.4%. The engine without the filter is the thing that
   erases GSM8K.

3. **"True instant learning requires BOTH layers"** — for *permanence*, yes. But permanence is a
   property of the **substrate**, not of the learning. A tree of verified edits is permanent too, and
   it is auditable, reversible, and free. Weights are permanent but opaque. Which one you want
   depends on whether you can check them — and today, on real files, **the check could not run on 0
   of 42**. That is the binding constraint on both layers.

## 5. The smartest path — and why it is not "start fine-tuning"

**The one thing that unlocks both layers is the verifier. Build that first; it is also the fuel
refinery.**

1. **Make the check cheap to stand up** (dependency resolution for the 6 tasks that needed an
   uninstalled package, a test-entry-point finder for the 6 with no importing module). This is
   already the next step from the last round, and it now has a second reason: it is what turns our
   event stream into *training* data.
2. **Record every action with its verdict, at the moment it happens.** We already do this for
   controller steps. Extend it to edits: store `(before, after, check_result)` with the lesson. That
   is the 2,790-lines-per-merge stream, currently thrown away, converted into fuel — for free,
   forever.
3. **Then, and only then, try weight-space learning on the seed.** With ~5,000 verified events, a
   held-out split, and a backward-transfer measurement (does the new capability cost an old one?).
   ASCENT's recipe — frozen teacher, verified-only, LoRA fast weights — is the one to copy, because
   it is the one that reports held-out transfer instead of just claiming gains.
4. **Never train on unverified events.** Every paper above that measured it found the same thing:
   unverified experience teaches confidence, not competence. This repo already has a 100%-success
   store to prove the point locally.

**Killed before implementation, with the reason:**

* *"Add fine-tuning now to get the missing layer."* No verifier at scale + 64 verified events. Direct
  SFT on experience retains **3.8%** of the gain (2607.21051) and costs GSM8K-level capability
  (TRACE). It would spend real money to make the system worse in a way that is hard to see.
* *"Use our causal models as training data."* They are descriptions of what should hold, not events.
  Zero of them are (situation → action → verdict) triples. Measured above.
* *"Online test-time training in deployment, like ASCENT."* ASCENT needs a terminal verifier per
  episode. We do not have one on real code (0 of 42 files). Copying the method without its
  precondition copies its instability instead of its gains.
* *"More memory entries will become weights eventually."* No mechanism connects the two. Memory grows
  linearly; weights need a distillation objective, a teacher, and a held-out split. None exist here.

## 6. Am I right or wrong — final

* **You are right** that token-space learning is real, that the system genuinely learns from
  experience, and that weight-space is the other layer that would make it permanent.
* **You are right** that this is a different and better way to make agents learn than static
  prompting — and the 2026 numbers (64.8–93.4% retention vs 3.8% for naive SFT) say it is worth
  building.
* **You are wrong** that adding weight-space training now is the fastest path. It is the fastest path
  to *silent capability loss*. The bottleneck is not the update mechanism — it is **verified
  experience at scale**, which is the same bottleneck that stops the token-space layer from
  verifying its edits.
* **The sentient-creature framing:** what separates a cache from a creature in these measurements is
  not weights. It is (a) learning a *shape* from more than one showing, (b) knowing **where a lesson
  stops applying**, and (c) carrying the result forward forever. We have (a) and (c) in token space;
  (b) needs a check. Weights would make (c) cheaper, not make (b) exist.

*One number to keep in view:* 192 real agent steps, 8.9% of them failures. That is the seed of a
weight-space layer — and the reason it is safe to use is that every one of those failures was
**observed**, not assumed. Keep that property above all else.

## Receipts

```
python3 canonical/tools/weight_space_fuel_v1.py --out canonical/verification/WEIGHT_SPACE_FUEL_20261113_V1.json
python3 -m pytest canonical/tests/test_weight_space_fuel_v1.py -q
```

$0, zero model calls, no capability registered, no family flipped, `truth.achieved` stays `false`.

Sources: arXiv 2610.05303 (ASCENT), 2607.21051 (Experience Distillation), 2604.27003, 2611.14320,
2609.12655 (memory reuse); OSFT / Sculpting Subspaces (ICLR 2026) and the TRACE benchmark results;
Reinforcement Fine-Tuning in Continual Post-Training (arXiv 2507.05386).
