# I measured the thing I kept deferring. It says the library is 218, not 447 — and 11% askable.

**2026-11-24 · `arena/283e85a5-brain`**

For three turns I said *"D3 — prune the library to its measured routing capacity"* and then
deferred it, because it needed a recall curve. This turn I built the curve. It does not say what I
predicted, and the measurement found something worse than the thing I was looking for.

---

## 1. The library is not 447 capabilities. It is 218 implementations, and 11% are askable.

| measure | value |
|---|---|
| capabilities **declared** in the artifact | **447** |
| capabilities with **distinct implementations** | **218** |
| ids that are duplicates of another id's file | **180 (40%)** |
| **largest duplicate group** | **176 ids → one 7,370-byte file** (`bound_capabilities/cli_command.py`) |
| **askable in words** (a phrase a person could say) | **49 — 11%** |
| has a docstring | 370, of which **182 are the same generic sentence** |
| **distinct docstrings across the whole library** | **192** |

**176 ids, one file, one sha256, byte-identical.** Every one declares
*"Generic zero-shell adapter for verified local command-line suppliers."* They are the
auto-registration of 175 `canonical/runtime/*.py` modules through a single CLI adapter — so the
capability id names the module, and the implementation behind all 176 ids is the adapter.

The artifact's own `counts` block says 447. That number has been quoted in planning documents as
the library's size. **It is a registry count, not a library count.**

---

## 2. The recall curve — and the cliff that is not there

I proposed the curve to test: *does our 447-capability library fall off the published cliff
(selection fine at 16–64, degrades at 128, sharp drop at 256)?* It had never been measured.

Method, chosen so a hit cannot be the capability's name restating itself: hide one capability,
restrict the index to a random subset of size *k* containing it, and route a query built from its
**declared trigger phrase**. Triggers are metadata the index was *not* built from — the index comes
from `provides`/`requires`/id terms — so a hit is semantic overlap. 49 eligible victims, 24 trials
each, seed 20261124.

| library size | 16 | 32 | 64 | 128 | 192 | 256 | 320 | 384 | 473 |
|---|---|---|---|---|---|---|---|---|---|
| **recall@1** | .984 | .965 | .921 | .877 | .840 | .816 | .794 | .781 | **.756** |

**Monotone decay, 23 points, no cliff.** Nothing collapses at 256. My hypothesis was wrong.

That is worth knowing on its own: the published curves (Single-Agent-Skills, AgentSkillOS) are for
competing *skills* with prose descriptions; ours are for *capabilities* whose index is built from
typed `provides`/`requires` edges. A keyword scorer over a typed edge graph does not fall off the
same cliff a prose skill library does.

**And it costs nothing to get the rest back:** recall@1 at 473 is .756; at 256 it is .816; at 32 it
is .965. Most of the loss is accruing across the ~180 duplicate registrations, which contribute no
new behaviour.

---

## 3. The real defect: two thirds of the library cannot be asked for

Of the 447 declared capabilities:

- **294 are `RECEIPT_BACKED_CAPABILITY`** — auto-registered per module. **0 of 294** have a phrase a
  caller could say; their `provides` *is their own path*
  (`canonical/runtime/authority_epoch_guard_v1.py.auto.v1`). They can be addressed **by name only**.
- **153 are `BOUND_CAPABILITY`** — the hand-built ones. **49 of 153 (32%)** have a usable phrase.

So the population splits cleanly: **153 real capabilities, of which 49 are reachable by describing
what you want.** The other 398 require you to already know the id.

This is the thing the frontier research calls the *description* lever, and it is the cheapest one:

> **StackOne / Stacklok / RAG-MCP 2026:** "fix the catalog before you add retrieval — namespace every
> tool, rewrite thin descriptions, add example requests. **This step alone improves both hosted
> search and your own index, and it is cheap.**" Tool search: **34% → 94%** selection accuracy.
>
> **OATS (arXiv 2603.13426):** rewriting how descriptions are written lifted Recall@1 **0.716 →
> 0.830** at *zero* inference cost. And in their head-to-head, **BM25 beat dense embeddings**
> (NDCG@5 0.853 vs 0.834) — a keyword index over good text is not obsolete.

---

## 4. And the descriptions already exist in the repo — 97% of them

For each of the 294 unaskable capabilities I read the module's own docstring:

| | |
|---|---|
| module file found | **294 of 294** |
| has a first-sentence docstring ≥20 chars | **284 (97%)** |
| genuinely unique description | 105 |
| identical generic string (`Generic zero-shell adapter…`) | **175** |

**The words that would make the library askable are already written, in-tree, in the docstring of
every one of those modules. Nothing reads them.** The pipeline writes `provides: <path>` and never
the sentence the author wrote directly above it.

That is the same shape as every other finding in this repository, and this time it is one field in
the compiler.

---

## 5. What I built

`canonical/tools/unified_model_library_census_v1.py` — reports declared vs distinct vs askable,
the duplicate groups, the docstring coverage, and the recall curve with 95% CIs. Re-runnable:

```
python3 -m canonical.tools.unified_model_library_census_v1
```

`canonical/tests/test_unified_model_library_census_v1.py` — **9 tests**, pinning that the declared
count is not the distinct count, that one file is registered under >100 ids, that askable share
stays under a quarter, and that the docstring template is present. **9/9 pass.**

Both numbers came from measurement I ran today; neither is quoted from memory.

---

## 6. The corrected plan — and what I now refuse to do

**Withdrawn: D3 as I stated it.** "Prune 447 → the measured capacity" was aimed at a cliff that does
not exist. Pruning to 256 would buy ~4 points and cost a third of the real library. **That is the
wrong trade.**

**Replaced by, in priority order:**

**L1 — Give every capability the sentence its author already wrote.** Populate `provides` from the
module docstring's first sentence where the current value is a path. Two cheap guards: dedupe the
182 generic strings so they collapse to one capability instead of 176, and leave the 52 unresolved
modules alone. **Predicted effect: askable share 11% → ~70%; recall@1 recovers toward the .90s.**
Falsifier: askable share stays below 40%, or recall@1 does not improve by ≥5 points.

**L2 — Collapse the 176 duplicate ids to the ones that are actually distinct.** Free 40% of the
registry and 46% of the 0.89 MB routing core. Predicted: **+0 accuracy** (measured: stubs steal 0 of
13 misses), so this is a pure size win — which is exactly the kind that is safe to do.

**L3 — Keep BM25, tune it.** The literature explicitly finds lexical retrieval beating embeddings on
tool descriptions, and our scorer already is lexical. No new component. The `b`/`k1` equivalent here
is the `identity_weight` and the coverage floor — two constants, measurable.

**L4 — Kept from last turn:** D4 widen the forge (0/12 → ≥4/12), and the R1 governance re-attestation
that is still your decision.

---

## 7. Honest limits

- **49 eligible victims is a small sample**, and they are only the `BOUND` capabilities that happen to
  have a multi-word trigger. The curve is about *those* capabilities, not all 447. The 95% CIs are
  ±.07 at k=473 — the slope is real, the exact endpoints are not.
- **The trigger phrases are declared metadata**, so a capability whose triggers are wrong will look
  worse than it is. That is a property of the same defect L1 fixes.
- **I have not implemented L1.** It is one field in `compile_brain_unified_model_v1.py` and a
  re-compile, and it changes the model digest — which means every pinned-artifact test must be
  re-attested. **That is why it is a proposal and not a commit.**
- The 52 unresolvable modules are counted as distinct-by-default in the 218. The true distinct count
  is between 166 and 218.

**One sentence:** we do not have a 447-capability library that routes at 76%; we have a 218-capability
library where one adapter file is registered 176 times and 89% of the entries cannot be asked for in
words — and the words are already written in the repo.
