# L1 executed. The library went from 11% askable to 47%, and the routing slope vanished.

**2026-11-24 · `b3b9ee19` · `arena/283e85a5-brain`**

"go" taken as authorisation to execute L1 + L2. L2 I did **not** do, and §4 explains why.
L1 is done, measured, and it turned three tests green that had been red on `main`.

---

## 1. What L1 actually was

The compiler emitted `provides: <module path>` and nothing else. So a capability whose author had
already written *"Write a JSON document to a repository-local file"* directly above the function was
addressable **by filename only**.

Meanwhile **188 distinct sentences sat on disk, read by nobody.**

The change, in `_capability_row`:

- `_module_docstring_sentence()` reads the module's own first sentence.
- It joins the capability's triggers and is carried as `described_as`.
- **Sentences shared by more than one capability are dropped.** 176 modules open with the same
  *"Generic zero-shell adapter…"* line; counting it would make 176 capabilities tie on the only
  words meant to separate them.
- Description tokens are weighted **1**, below declared triggers (2/3) and id tokens (3) — so a
  description can promote a capability on a verb it never declared, but can never outrank one that
  declares it.

---

## 2. Measured, before → after

| | before | after |
|---|---|---|
| askable in words | **49 / 447 (11%)** | **211 / 447 (47%)** |
| capabilities carrying a description | **0** | **188** |
| self-locate by its own recorded description | **impossible** (no description stored) | **126/188 = 67.0%** |
| self-locate, isolated from generic siblings | 25.0% | **98.9% (186/188)** |
| **recall@1 curve (188 victims, pool 473)** | **.984 → .756** | **1.000 → .989** |

The recall curve is the one that matters. Before, every added capability cost accuracy —
.984 at k=16 down to .756 at k=473. **Now it is flat: 1.000 → 0.989 across a 30× change in library
size.** The slope was not a property of the scorer. It was a property of the *descriptions*.

| k | 16 | 32 | 64 | 128 | 192 | 256 | 320 | 384 | 473 |
|---|---|---|---|---|---|---|---|---|---|
| before | .984 | .965 | .921 | .877 | .840 | .816 | .794 | .781 | **.756** |
| **after** | **1.000** | **.999** | **.997** | **.997** | **.994** | **.994** | **.992** | **.990** | **.989** |

---

## 3. Two safety defects the suite caught — one of them pre-existing

Adding descriptions made `"write a poem about the sea"` route **confidently to `json.file.write`**.
The verifier's stability tests failed on five seeds. I chased it rather than loosening the test, and
found two separate causes:

**Cause 1 — my change.** `about` appeared in exactly **one** description. With `df=1` its IDF is
~224, so a single weight-1 posting cleared the 0.34 coverage floor on its own. Fix:
`DESCRIPTION_SKIPWORDS` — function words a request does not turn on. Descriptions keep their nouns
and verbs; they lose their grammar.

**Cause 2 — pre-existing, and worse.** Coverage counted a token as *matched* if it appeared in any
posting **at all**, including a single one. **A token with one posting cannot separate
capabilities, so it cannot support a claim that the model recognised the ask.** `route()` now
requires `len(postings) > 1`.

I verified this against `git HEAD` rather than assuming: **the original artifact also routed
"write a poem about the sea" → `json.file.write`.** It simply wasn't confident. L1 did not create
the bad route; it raised its confidence. The fix removes the bad route from both.

---

## 4. What I refused to do: L2

I proposed collapsing the 176 duplicate ids. **I did not**, and the reason is a measurement.

- The 176 share one file, `bound_capabilities/cli_command.py` — but each names a **different
  module** (`canonical/runtime/<name>_v1.py`), and those modules **exist and have their own tests**.
- 29 of 40 sampled ids are imported by real `.py` files.
- So the duplication is not a stale artifact — it is a **generic CLI adapter registered 176 times
  to keep 176 real modules invocable.** Deleting the ids unregisters real bindings.

The measurement that *would* justify a collapse does not exist yet, because the trigger-set union
is not built. **L2 stays open with that method specified, not guessed.**

---

## 5. Corrected numbers for the record

| claim | status |
|---|---|
| "447 capabilities" | **registry count.** 218 distinct implementations. |
| "11% askable" | **fixed → 47%.** |
| "recall .756 at 447" | **was .756, now .989.** The old number is superseded by L1. |
| "library is past the cliff" | **wrong.** The cliff was the descriptions. |
| "prune to 256" | **withdrawn.** At .994 there is nothing to prune for. |

---

## 6. Test state

| suite | before this session | now |
|---|---|---|
| `test_brain_unified_model_v1` | **3 failed** / 58 passed / 919 subtests | **61 passed / 919 subtests** |
| `test_unified_model_library_census_v1` | — | **10 passed** |
| `test_measured_boot_and_repair_speed_v1` | — | **7 passed** |
| `test_instruction_contract_v1` | 21 passed | 21 passed |

**The three failures on `main` were all routing-quality failures. L1 fixed them.**

One guard had to change: it previously asserted the *defect* — that under 25% of the library was
askable. **A guard that pins a bug stops you from fixing the bug.** It now asserts ≥150 askable and
≥40% self-location, and the docstring says why it flipped.

---

## 7. Cost

| | |
|---|---|
| compile | **10 s** |
| artifact | 11.64 → **11.84 MB** |
| `open_model()` cold | 287 ms |
| `open_model()` warm | **13 ms** (the stat-signature cache still holds) |
| routing tokens | 1,729 → **1,872** |
| new digest | `c69bed93…` (the old artifact was already stale vs its own source) |

---

## Honest limits

- **67% full-library self-location, not 98.9%.** The 98.9% is isolated from generic siblings; against
  the whole library, capabilities like `current_escape_o11_objective_acceptance_law_gate` compete on
  shared family vocabulary and lose. That gap is real and is the next thing worth fixing — family
  vocabulary needs the same treatment function words just got.
- **The 98.9% is a self-location measurement**, which is a *necessary* condition for a capability
  being findable, not a benchmark score. It does not mean a user's real request will route correctly
  98.9% of the time.
- **The recall curve still uses declared trigger phrases as queries**, and those are now partly the
  same sentences that were added. It is inflated relative to a held-out user request set. The
  *shape* (flat vs steep) is the finding; the absolute endpoints are optimistic.
- L1 changes the model digest, so any externally pinned digest must be re-attested. I checked: only
  two files reference the digest value and both read it dynamically.

**One sentence:** the library was not too large and the router was not too weak — 89% of the
capabilities had never been told what they were, and saying it out loud made adding capabilities stop
costing accuracy.
