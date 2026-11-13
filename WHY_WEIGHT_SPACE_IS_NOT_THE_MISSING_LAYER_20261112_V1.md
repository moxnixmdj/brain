# Weight-space learning is not the missing layer. It is the layer you cannot reach, and the reason is not the law.

**Answering the "brutal truth", measured.** Record:
`canonical/verification/WHY_WEIGHT_SPACE_IS_NOT_THE_MISSING_LAYER_20261112_V1.json`.

---

## 1. The brutal truth is wrong on three of its four bullets, and I measured it

> "It's a limited lookup system. It cannot count different things, cannot work on different files, cannot handle
> different task structures."

I tested each claim on the shipped organ rather than arguing about it.

**"It cannot work on different files."** Every one of the **440 askings** in the corpus *is* a different file.
One demonstration, applied to another file of the same project: **493 of 1,674** of the developers' non-import
changes recovered, at **29.45%** coverage. A system that could not work on different files would score 0.

**"It cannot count different things (if statements vs functions)."** Shown one change on an `if`, then applied to
a file holding an `if`, a `while` and a `def`:

```
shown:   if x: pass        ->  if x: raise ValueError('x')
target:  if a: / while b: / def f():
result:  changed 3 sites -- all three block positions
```

Shown once, applied to three identical-shape sites: **changed 3**. Shown in one function body, applied where two
functions exist: **changed 1, the matching one, and left the other**. It counts, and it crosses constructs.

**"It is a limited lookup system."** This is the one worth measuring precisely, because a lookup system has a
signature: **it dies when the wording changes even though the change does not.** So I re-worded the same change on
both sides of every pair — `assertEquals`→`assertEqual`, `self.assertEqual`→`self.assert_equal`,
`six.moves.xrange`→`six.moves.range`, `logger.warn`→`log.warn`, `warnings.warn`→`warn`, `utcnow`→`utc_now` — and
ran all 440 askings again:

| | right | denominator | coverage |
|---|---|---|---|
| untouched | 493 | 1,674 | **29.45%** |
| same change, re-worded | **332** | 1,384 | **23.99%** |

**A lookup system recovers zero here.** This recovers **332**. What falls is 5.46 pp of *fit*, not the ability to
transfer. It is not a lookup table. It is a rule that is less well matched to unfamiliar words.

## 2. Where the real wall is — and it is not weights

The same corpus has a second arm already built in: give the organ an example of **one kind** of change and point
it at files where a **different kind** belongs.

| arm | changes recovered | denominator | coverage | of what it attempted, how much was right |
|---|---|---|---|---|
| same kind of change, another file | 493 | 1,674 | **29.45%** | 91.8% |
| **another kind of change, these files** | **0** | **4,444** | **0.00%** | **0 of 19** |

That zero is a real zero, not a small number: **it recovered none of 4,444 changes, and all 19 changes it
attempted were not the developers'.** It does not merely fail to transfer across kinds — it actively writes wrong
code. And the largest single refusal class, **168 of 440 (38.2%)**, says *nothing in the file has the form the
example changed*: there is no such code, so no method can generalise to it.

**So the limiting factor is not the storage layer.** It is that the organ holds an abstraction that survives a
change of *file* and a change of *wording*, and nothing that survives a change of *kind*. Weights would not fix
that. A weight update on this data would learn the same thing the rule learns — this text becomes that text —
because that is all the data contains.

## 3. Why the weight layer is not available here, in order of how fatal each reason is

**First, it is forbidden — and the law names this exact proposal.** `GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_
OWNERSHIP_LAW_V4.md`, CANONICAL / MANDATORY / FAIL-CLOSED:

> "A general-purpose pretrained model acting as reasoner/planner/agent is not made admissible by **storing its
> weights inside Brain**."
>
> "The prohibition is identity- and hosting-independent. It applies equally to … open-weight models, copied or
> vendored weights, self-hosted model servers … and models invoked through runtimes such as llama.cpp, vLLM,
> Ollama, transformers."

Fine-tuning a pretrained LLM on our traces and shipping those weights is precisely the forbidden route. Consequence
is total: capability, benchmark, acceptance, ownership, promotion and terminal credit all go to **zero**. The V22
admission gate enforces `producer_cognition_model_dependency_count == 0`. This is not a rule I am choosing to hide
behind — it is one the owner set, and it is the correct rule for a system whose entire claim is that *it* does the
reasoning.

**Second, it is impossible on this host.** 2 CPU cores, 3 GB RAM, no GPU, no `torch`. ASCENT needs an open-weight
base model and a GPU to distil full next-token distributions into LoRA fast weights. Experience Distillation needs
749 curated SWE tasks of rollout plus teacher sampling at every history step. Any number I produced here would not
be a measurement — it would be a fabrication, and fabricating one is worse than saying no.

**Third — and this is the part that changes the strategy — the weight layer is downstream of the layer we have.**
Experience Distillation's own ablation is the decisive number:

> on the same collected experience, **direct supervised fine-tuning recovers 3.8%** of the in-context gain.
> The distillation method recovers **64.8%**.

The weight layer does not *replace* the experience layer; it **distils** it. You cannot distil experience you never
collected. Every honest path to weights runs *through* a token-space representation good enough to be worth
distilling — which is the work already in hand.

And the direction of the trade is not obvious even where weights are legal. Full fine-tuning shows **~89%
forgetting** on prior tasks, LoRA **~71%** in some settings, sparse memory layers **~11%**. The same experience kept
as an inspectable, deletable artifact forgets **nothing**, and can be corrected without retraining.

## 4. What the citations actually say, since they were quoted at me

They are real, and they say what was claimed — I checked rather than assuming:

- **ASCENT** (arXiv 2610.05303), Oct 2026: online test-time training; a frozen copy of the initial model reads a
  *verifier-accepted* trajectory with hindsight and distils it into persistent LoRA weights. **+22 points** exact
  success on ALFWorld/WebShop, transfers to held-out scenes. Its own stated limits: **requires a terminal
  verification signal**, is sensitive to noise on a single trajectory, and **"requires full next-token
  distributions, so it applies to open-weight models."**
- **Experience Distillation** (arXiv 2607.21051), Jul 2026: converts ICL gains into weights with no extra
  environment interaction; retains **≥64.8%** where direct SFT retains **3.8%**.

Note what ASCENT's gate is: *verified* experience. That is a **check**, and it is exactly the asset this repo
already treats as load-bearing. The weight-update step sits **after** the verification step. We are not missing the
verification step. On this corpus we are missing cross-kind abstraction, which no amount of re-storing knows how to
build.

## 5. What is real, what is not, and the smartest next move

**Real:** 29.45% of the developers' non-import changes from **one** demonstration, permanently, for $0; transfers to
another file of the same kind; survives re-wording with 332 changes recovered; counts across `if`/`while`/`def`.
Precision 91.8%; the 19 changes it gets wrong it *knows* are tries.

**Not real:** that this is a lookup system; that it cannot count or cross constructs or work on other files; that
"the LLM doesn't learn, so nothing is learned" — the organ is not the LLM, and it is what learns, verifiably; and
that weight-space learning is a step we could take today at any credit.

**The smartest move is not Option 1, 2 or 3 as posed.** Options 2 and 3 are closed on three independent grounds
(forbidden, impossible here, and downstream of the layer that is actually weak). The wall is the **0/4,444**
cross-kind arm and the **38.2%** "no such form in the file" class. If we want the largest single capability jump
available, it is making one demonstration yield an abstraction that survives a change of *kind* — and the
repo already has the machinery to price that honestly: the same corpus, the same refutation-first loop, the same
rule that a success teaches applicability nothing while chosen failures teach it fast.

Authority **NONE**. Cost **$0**. Model calls **0**. No weights touched, no capability registered, no guard
weakened, `truth.achieved` false.
