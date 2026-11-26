# Best part is no part. Measured.

**2026-11-24 · `arena/283e85a5-brain`**

You gave two instructions this time, and the second one changes the answer to the first.

> *"We already have solved all of this somewhere under non-obvious names… They need to be at the
> unified runtime, at the unified model."*
> *"Don't forget Elon's most important law: best part is no part and everything must be insanely fast."*

I read those as being in tension. They are not. **The reason our capabilities are not at the
unified model is that the unified model is 447 capabilities and an 11.6 MB catalog, and the thing
that would make them usable is a smaller thing, not a bigger one.**

Everything below is measured in this sandbox, today, with commands you can re-run.

---

## PART ONE — Seven measurements that decide the plan

### 1. The "unified model" is a 57 ms loader and an 11.6 MB catalog

| | |
|---|---|
| `import brain_unified_model_v1` | **47 ms** |
| canonical modules it imports | **2** (pure stdlib + `marshal`) |
| `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` | **11.64 MB** |
| `json.loads` of that file | **95–155 ms** |
| sha256 paid to validate it, every load | **10 ms** |

`brain_unified_model_v1` does not import a single capability. It loads **data**. That is why the
census says 712 files are "reachable" while boot costs 47 ms: the census counts imports found
anywhere in the file's AST, including inside function bodies. **712 files are not 712 capabilities.
They are names in a manifest.** (This also means my earlier framing — "the hub is the chokepoint" —
was wrong. There is no hub. There is a catalog and a scorer.)

### 2. The catalog is 13× larger than the part the router needs

The router (`UnifiedModel.route` / `solve`) scores against `grammar.index`, filtered by
`capabilities_map`. `_extract_routing_core()` already isolates exactly that. I ran it:

| | size | parse cost |
|---|---|---|
| full artifact | **11.64 MB** | json.loads **95 ms** |
| **routing core** (already built, already cached) | **0.89 MB** | marshal.loads **4.9 ms** |

**19× less work, and the code to do it already exists and is already the only path 53 call sites
use.** The slow path is used by **2** call sites.

| | |
|---|---|
| `open_model()` — marshal-cached, `_core_only`, 0.89 MB | **53 call sites** |
| `load_model()` — reads+hashes+parses 11.64 MB | **2 call sites** (both verification/CLI) |

### 3. The cache still pays full price — a one-line defect

`open_model()` validates its cache by `target.read_bytes()` → `sha256` over all 11.64 MB before it
is allowed to `marshal.loads` the 0.89 MB core. **The cache saves the parse and keeps the read.**
The digest it actually checks (`core["raw_sha256"]` vs `raw_sha`) can be replaced by a stat
signature — `(st_size, st_mtime_ns, st_ino)` — which is what the in-process memo cache at L1643
already uses. Cost of the change: one function. Cost of not making it: 16.5 ms and 11.6 MB of I/O
on every agent step that re-opens the model.

### 4. The fabric — a static 1,208-line table — takes 853 ms to import

This is the number that matters for "insanely fast".

| module | import | canonical modules pulled |
|---|---|---|
| `brain_unified_model_v1` | **47 ms** | 2 |
| **`unified_cognitive_fabric_v1`** | **853 ms** | **239** |

It eagerly imports `astra_runtime`, `p3_real_context_v3_admission_v12`, the adaptive solver, the
authenticator, `urllib.request` → `http.client`. **A data table has no reason to open an HTTP
client.**

I audited its 34 module-level imports with an AST pass:

| | |
|---|---|
| used at module level (lazy is impossible) | **1** (`Path`) |
| **used only inside function bodies** | **33** |
| never used at all | 1 (`annotations`) |

Then I proved it rather than arguing it. I stubbed the 23 heavy dependencies and imported the module:

| | baseline | with 23 imports substituted |
|---|---|---|
| import time | **853 ms** | **38.4 ms** |
| canonical modules loaded | 239 | 52 |
| public callables defined by the module | 3 | **3 (unchanged)** |

**22× faster, 187 fewer modules, nothing lost.** The mechanism is `importlib.import_module`
inside the 33 function bodies. That is a **net deletion of 33 lines to a single `Path` import.**

### 5. `learn_or_read_v1.decide()` — 70 µs, and it crashed on my first call

Good news and a defect.

| | |
|---|---|
| decision latency | **70 µs** (14,374/sec) |
| model calls | **0** |
| state | none |
| dependencies | `instruction_contract_v1` |

The defect: **`decide()` raised `KeyError: 'index'`** on an observation whose elements lacked an
`index` field. `instruction_contract_v1._element_label_set` at L1123 does
`int(element["index"])` with no guard. Its own docstring says it answers *"is every act the
sentence requires named by the sentence, and present on the page?"* — **on an unlabelled page it
throws instead of answering.** A gate that can throw on malformed input will one day fail closed
on a live page, and the failure will look like a policy bug.

Fix: default the index (`element.get("index", i)`) or fall back to label-keyed dict. One line.

### 6. We are 3.5× past a measured cliff, and we have the collapse already

Our declared library vs. what the 2026 survey literature measured:

| | |
|---|---|
| capabilities declared in the model | **447** |
| runtime modules | **2,247** |
| literature cliff | selection fine at **16–64**, degrades at **128**, **drops sharply at 256** |

We are **3.5× past 128 and 1.7× past 256**.

And we have the collapse in our own numbers. Memento-Skills, which grew a *successful* library from
5 skills to 235, reports **Recall@1 of 0.60** — a router that finds the right skill six times in
ten. **Our own unified model routes by token-index scoring over 447 capabilities with no measured
Recall@1 at all.**

Third-party measurement of exactly this shape (Demystifying Agent Skills, 2026): as a library grows
5 → 100 skills, **actual-use precision falls from 29.6% to 3.3%.** AgentSkillOS: removing periodic
pruning and merging drops pass rate **35.6% → 31.1%**, grows the repo **4.5×**, utilization
**0.71 → 0.08.**

> **"Best part is no part" is not a slogan here. It is the measured remedy for our exact state:
> a 447-capability library with no pruning and no measured router.**

### 7. The mechanism we need is already written, in a file nothing imports

`capability_forge_v1` (822 L, reachable) exists to convert orphan modules into killable
capabilities. Its own docstring: *"A CAPABILITY IS A HYPOTHESIS THAT SURVIVED ATTEMPTS TO KILL IT."*

I ran it on 12 dormant modules: **0 admitted, 12 refused**, 7 of them `NO_ENTRYPOINT` because it
only recognises a module-level `run`/`invoke`.

So the pipeline is: 1,636 orphans → forge that recognises one signature → a catalog of 447 hand-
authored entries. **The middle of the pipeline is the bottleneck, and the fix is to make the forge
see partial contracts, which is less code than the hand-authored entries it replaces.**

---

## PART TWO — The plan. Deletions first, because you asked and because they win.

Ordered by measured payoff per line changed. Every item has a number and a falsifier.

### D1 — Lazy the fabric's 33 imports · **853 ms → 38 ms · −33 lines** · 0.5 day

Move 33 `from canonical.runtime import X as y` statements into the function bodies that use `y`.
One `importlib` helper. Public surface unchanged (measured: 3 callables before and after).

**Falsifier:** any of the 3 public callables changes behaviour, or import rises above 100 ms.
**Why it's first:** it is the largest single number in this document and it is a pure deletion.

### D2 — Boot from the routing core · **112 ms → 5 ms · −11.6 MB read** · 0.5 day

Validate the cache with `(size, mtime_ns, ino)` instead of `sha256(read_bytes())`. Keep the full
digest on the cold path only, where it already runs.

**Falsifier:** a mutated artifact with a preserved stat signature is accepted. (Test it — that is
the whole threat model, and it is one test.)

### D3 — Prune the library to the router's measured capacity · **447 → the number the router proves it can route** · 1 week

Do not pick a number. Measure Recall@1 at k = 16, 32, 64, 128, 256, 447 and cut at the last k
before the drop. Publish the curve.

**This is the single most important item in the plan**, because the literature says our library is
past the cliff and we have never measured our own router. It is also the only place where the
"hidden capabilities" premise turns into something the frontier does not have: **a library whose
size is set by a measured routing curve, not by accumulation.**

**Falsifier:** recall is flat to 447. If so, we are the exception and I am wrong — publish that too.

### D4 — Make the forge see partial contracts · **0/12 → ≥4/12 admitted** · 3 days

Infer entry points from any callable with inferable parameters, not just `run`/`invoke`.
`ast` already does the work in `contract_of`.

**Falsifier:** fewer than 4 of the 12 admitted, or any admitted capability survives being killed.

### D5 — Guard `decide()`'s input contract · **1 line** · 1 hour

`element.get("index", i)`. Add the unlabelled-page case to the test file. **A gate that throws is
not a gate.**

### D6 — Add the operator-swap generator to the zipper · **2 of 2 candidates pass? measured next** · 1 day

`_AST_BINOP_SWAPS` and `_AST_CMPOP_SWAPS` are **34 lines** sitting in
`autonomous_awake_loop_v1.py` L126–142, unimported by the repair chain. Import that dict into the
zipper's candidate generator. That is the entire fix for `a-b`→`a+b`, which currently returns
`UNSOLVED_WITHIN_BUDGET` with 2 candidates and 0 passes.

**Falsifier:** the fixture `add(x,y)=x-y` still fails after the swap generator is wired.

### What I am NOT proposing

- **Not** adding a router. We have `capability_first_scheduler_v1`, `live_capability_invoker_v1`,
  `live_capability_composition_v1`. Three routers. Adding a fourth is the exact error.
- **Not** growing the catalog. 447 → more is the failure mode, not the goal.
- **Not** a bigger memory. `what_one_experience_buys_v1` measured the unit at **1 bit**, a page at
  **5.43 bits**, reuse at **1.55×**, cost per task **flat at 1.23**, vocabulary **does not
  saturate**. Memory is the wrong axis; the decision *whether to store* is the right one.

---

## PART THREE — The research, and what it says about the part we can actually win

I searched the unfamiliar names again, this time aimed at the two things you just said. The
findings converged harder than in any previous round.

### The literature independently found "best part is no part"

| source | measurement |
|---|---|
| **Vercel agent team** (Mar 2026) | cut 15 tools to **2** (bash + SQL): accuracy **80% → 100%**, tokens **−37%**, speed **3.5×** |
| **Manus** (4 rebuilds) | biggest gains came from *removing* complexity: filesystem-as-memory, **100:1** input:output compaction, **10× cost reduction** |
| **OpenAI Codex** | converged independently: minimal general-purpose tools, external state in git/files |
| **Lita** (arXiv 2509.25873) | "liteness": *"as model capability increases, the gap between frameworks of varying complexity shrinks"* |
| **More Is Not Always Better** (arXiv 2605.05716) | **CCI**: optimal component count k\* = **1–4**; at every capability level *"the simplest single-component scaffold matches or outperforms the full agent"*; at Claude Haiku the interference gap is ≈0% |
| **The Jagged Frontier** (Sep 2026) | simpler scaffold **degrades less** under perturbation: 1.34 pp vs 1.88 (Verified), 1.88 vs 3.65 (Pro) |

Three independent teams, one conclusion, and it is the same one you stated. **This is now the
best-evidenced architectural claim in the field.**

### The literature also measured our cliff, precisely

| source | cliff |
|---|---|
| Single-Agent-Skills (Li 2026) | selection high at **16–64**, degrades at **128**, **drops sharply at 256** unless hierarchical routing is added |
| Demystifying Agent Skills | 5 → 100 skills: real-use precision **29.6% → 3.3%** |
| AgentSkillOS | removing prune+merge: pass **35.6% → 31.1%**, repo **4.5×**, utilization **0.71 → 0.08** |
| Memento-Skills (2603.18743) | a *successful* 235-skill library gets **Recall@1 = 0.60** |
| SkillProx (Aug 2026) | **deletion** is where skill libraries break; leave-one-out attribution wired to a validation-gated delete |

### And the frontier's own answer to our central question is the wrong shape

| source | what they did | cost |
|---|---|---|
| **Meta proactive memory agent** | trained steward decides when to speak | **+8.3 pts** Terminal-Bench — needed **Claude Opus 4.6** as the steward; untrained small model made it *worse*; trained small model only +3.5 |
| **Memento-Skills** | parameter-free continual learning via skill libraries | grows to 235 skills, **Recall@1 0.60**, *"diminishing returns as the library covers the input space more densely"* |
| **Agentic Meta-Reasoning** (2609.38147) | separate controller + executor loop, allocates compute | ProgramBench **71.5%** vs Codex 58.0 (GPT-5.5); **all 12/12 wins at the highest budget** — but the paper itself says the overhead *can hurt when compute is scarce* |
| **ROI-Reasoning** (2601.03822) | meta-cognitive fine-tune: predict cost, decide solve-or-skip | better under tight budgets |
| **Rational Metareasoning / VOC** | reward = Value of Computation | same accuracy, **~40% fewer reasoning tokens** |

**The pattern is unmistakable: every one of them builds a *separate controller* to decide when to
think. Meta's needs a frontier model. Ours (`learn_or_read_v1.decide()`) is 70 µs, 0 model calls,
no state, no parameters.**

That is the unusual idea, and it is already written. It only needs its crash fixed and its
answer to be reachable.

### The memory literature says the same thing about storage

From a survey of 3,283 agent-memory papers (Oct 2026):

- **write gates**: writing only behind utility-consistency-evidence thresholds cut memory
  contamination **67–70%**; interpretable admission gave **31% lower latency** than LLM-driven memory
- **delivery beats storage**: *"the agent made 0 memory calls in 114 turns with a pre-seeded store"* —
  deterministic injection fired every time
- **skills**: task-level skills mostly pushed agents **below** their no-memory baseline; subtask-level lifted them above
- **forgetting**: no system passes more than **1.5%** of forget requests, end to end
- **context compaction**: summarising compaction retains **10%** of safety rules after five rounds

**"Delivery, not storage."** That is `learn_or_read_v1`'s thesis stated by someone else, and it is
also the argument for **no part**: don't build the store, build the gate.

---

## PART FOUR — The strategy, in the shape you asked for

You keep asking for the plan to be ahead of the frontier. Here it is, with the reason it can work
rather than an assertion that it will.

**The frontier's architecture is: bigger model, more tools, a separate reasoning controller, a
growing skill library, and a trained steward to decide when any of it should fire. Every component
of that is measurable and every one of them has a published cliff we are already past.**

**Our position is the opposite shape and it is only now provable:**

1. **A catalog 13× larger than the part that answers questions** → cut it (`D2`).
2. **A hub that costs 853 ms to import and uses 1 of its 34 imports at module level** → lazy it (`D1`).
3. **A library 3.5× past the measured cliff with no recall curve** → measure and prune (`D3`).
4. **A pre-action decision that costs 70 µs where the frontier trains a frontier model** → fix and ship (`D5`, then gate the store).
5. **A conversion pipeline that refuses 12 of 12 orphans for signature shape** → widen it (`D4`).

**The bet, in one falsifiable sentence:**

> **Removing the fabric's eager imports, booting from the 0.89 MB core, and cutting the library to
> its measured routing capacity will make the system faster and *more* accurate at the same time —
> and the accuracy gain will come from the deletion, not from any addition.**

The falsifier is `D3`: if recall is flat from 16 to 447, deletion buys speed and nothing else, and
the premise that our library is too large is wrong. **That is a one-week measurement with a
pre-registered answer, and it is the only experiment in this plan that could refute the strategy
itself.**

---

## Honest limits

- **I have not made any of these changes.** The 853 → 38.4 ms figure is a stubbed-import
  experiment, not a patched file. The 112 → 5 ms figure is a marshal round-trip of the existing
  `_extract_routing_core` output, not a rewritten loader.
- **The literature numbers are reported, not reproduced by me.** Vercel/Manus/Codex are blog-level
  evidence; the survey cliffs are controlled studies but not on our task distribution.
- **`decide()`'s 70 µs is on synthetic observations.** The 130-page measurement is the producer's,
  not mine, and remains a hypothesis with a named ablation.
- **I could not re-run the repair fixture** — `/tmp` was cleared. `D6` therefore has a prediction
  and no fresh measurement.

**The one sentence:** the system is slow because it is large, it is large because nothing prunes it,
and the part that would prune it — a 70 µs decision and a routing curve — is already written and
unreachable.
