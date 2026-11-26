# Nobody has executed it

*2026-11-25 · branch `arena/a0db4e27-brain` @ `f1066dbb` · $0, zero model calls*

---

## 0. I have to correct the previous three plans first

Last round I wrote a plan whose headline was **"629 harvested capabilities, 0 admitted — a gate with no
carrier."** I have now checked it. It was wrong twice over, and the way it was wrong is the most useful
thing I have measured in four rounds.

**Wrong once.** The receipt gate is not uncarried. It is working, right now, at scale:

```
load_verified_registry()          -> 462 routing targets
  capability_source: receipt_projection   309
  capability_source: bound registry       153
```

309 capabilities are admitted **today** on a producer receipt plus a different identity's reproduction
under a GitHub-signed OIDC claim. The loop is closed and has been walked 309 times.

**Wrong twice.** The `0` I quoted is not a failure count. `harvested_admitted` is computed as
`sum(1 for row in harvested if row["admitted"])` over rows that are *by construction* `admitted: False`
— the compiler builds the census after excluding every already-admitted module. It is the count of a
population that cannot contain a one. And a test asserts it stays `0`, so the number is pinned by the
test that would report it changing.

**Those are different populations.** Measured: `census ∩ admitted paths = 0 of 640`. The 309 receipt-backed
capabilities and the 640 census surfaces share no module. So:

> The gate works. Nothing has ever been taken to it. **The carrier is missing — I had the right
> diagnosis one paragraph before I attributed it to the wrong subsystem.**

---

## 1. The law

> **Verification that has never been attempted is indistinguishable from verification that failed.**
> Only one of those is fixable, and today the repository cannot tell them apart.

Every plan I have written — three of them — reasoned from counters in `counts`. Two of those counters
demonstrably cannot mean what they appear to mean. The instruments are unaudited and the plans inherited
the error. That is the finding, and it collapses the roadmap into one question:

**What is the cheapest experiment that turns a number into a measurement?**

---

## 2. Five instruments, ranked by how much of the roadmap they invalidate

I checked each of these this round. This is the order to fix them in, because each one is currently load-
bearing for a plan.

| # | instrument | says | does it mean that? |
|---|---|---|---|
| 1 | `harvested_admitted: 0` | nothing is admitted | **no.** Counts a disjoint population; pinned to 0 by a test |
| 2 | `receipt_backed_capabilities: 309` | 309 are trusted | **yes** — verified: 310/321 projection entries pass all 15 gate conditions, 309 land |
| 3 | the 640 census | 640 surfaces exist | yes, and **46% of the corpus is imported by nothing** |
| 4 | `native_route_hit_recall` | reachability | fixed last round (engines were invisible) |
| 5 | `research_index_records: 7404` | 7,404 records of research | **unknown.** No test I can find ever reads a single one |

Only #2 survives contact. #1 is the counter every one of my plans has quoted. #5 has never been examined
and is the largest number in the artifact.

---

## 3. The one door

### Door 8 — Take the census to the gate.

The gate exists, is credentialed, and admits. The census exists, is 640 rows, and has never been offered.
The task is to walk 640 rows into a working gate and **record a verdict for each** — almost all of which
will be refusals, and that is the point.

The reason it takes real work rather than a loop: **a surface that receives no arguments cannot be
replayed**, so its honest verdict is `UNREPLAYABLE__NO_DECLARED_INPUTS` and nothing gets admitted. The 309
that *did* get through are modules whose inputs were declared and snapshotted. For the census, the
declaration is frequently present but unparsed — `concept_library_v1` raises `DICT_UNPACK` on malformed
input, and that name is in its docstring. Nothing reads it.

Three moves:

1. **Extract the contract the code already states.** Argument names, the refusal strings a module raises,
   and its entrypoint are all in the source. Deriving them is not inference and costs no model call. A
   module whose required inputs cannot be derived gets a recorded reason, not a silence.
2. **Attempt replay, record the verdict, admit nothing.** Producer receipt via the existing lane; the
   independent identity still comes only from CI under OIDC. A local run must remain structurally unable
   to admit, and `test_harvested_capabilities_are_reachable_v1` already asserts that — keep it.
3. **Make the counter honest.** `harvested_admitted` must count admissions *of census rows*, and a second
   counter must report the verdict distribution. `0` with 640 reasons is a measurement; `0` with no reasons
   is the number that has been misleading three plans.

**Acceptance:** `sum(verdicts) == 640`, every verdict a named reason, and `harvested_admitted` computed over
the census rather than pinned by a test. If the answer is that 0 of 640 are replayable, that is a
legitimate result and enormously informative — it would mean 46% of the corpus is not merely unimported
but **unrunnable**, which is a much stronger and more useful claim than "unindexed."

**What this door refuses.** It will not lower the independence requirement. It will not mint a
verification record locally. It will not write the registry. If the only way to move the number is a local
promotion, the correct output is zero and a report explaining why.

---

## 4. Why this beats the frontier and does not merely tidy up

1. **Receipt-gated self-extension is the property nobody else can ship.** *Hardening Agent Benchmarks*
   (arXiv 2606.08960) found **16% of 1,968** tasks hackable and answered it with a loop of models. Here
   independence is a different identity and a hash comparison, over programs with deterministic outputs.
   That is cheaper, stronger, and already running 309 times.
2. **The cost curve is receipts, not inference.** 17.1 ms to re-use a verified program. 0 model calls.
   Every admitted surface is a mechanism that never costs a token again. 640 un-executed surfaces are
   mechanisms paying full price forever.
3. **Honest inventory is the only durable moat.** `Library Drift` and `The Blind Curator` both describe
   stores that grow past what can be trusted. A store that admits nothing avoids drift by being inert —
   safe and worthless. This repository is the rare system that can grow and cannot lie about what it added.
   It has simply never tried growth on its own census.

---

## 5. What I measured, and what I refuse to claim

Measured this turn: 309 `receipt_projection` capabilities in the live registry; 310 of 321 projection
entries pass all fifteen gate conditions; 322 producer receipts; 311 independent verification records;
**0** of those naming a census path; `census ∩ admitted = 0 of 640`; `harvested_admitted` computed over a
population that is `admitted: False` by construction and asserted to 0 by a test.

**Not claimed:** that any census surface should be admitted. Most are CLIs and contract surfaces with no
declared inputs, and the correct verdict for those is a named refusal. **Not claimed:** that replay is
safe. A surface that mutates the tree is not safely replayable and must be refused, not sandboxed into a
lie. **Not claimed:** that this makes the machine smarter. It makes its inventory honest, which is the
precondition for every other number here meaning anything.

**And the correction I owe:** for three rounds I wrote plans that assumed the counters beneath them were
measurements, including one I titled *"the frontier is not out there"* on the strength of a `0.000` that
turned out to be my instrument's blindness. That has now happened twice, in two different subsystems, with
the same shape. **The most valuable asset in this repository is not its 462 capabilities. It is that its
evidence is auditable — and the audit has never been run on the numbers being planned against.**

---

## 6. Reproduce

```bash
python3 -c "
import sys, pathlib, collections; sys.path.insert(0,'.')
from canonical.runtime import live_integrated_brain_v1 as L
reg = L.load_verified_registry()
print(len(reg), collections.Counter(c.get('capability_source') for c in reg.values()))
"
# 462 Counter({'receipt_projection': 309, None: 153})   <- the gate works, today

python3 -c "
import json; m=json.load(open('canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json'))
c=m['counts']; print('bound',c['bound_capabilities'],'+ receipt',c['receipt_backed_capabilities'],
      '=',c['capabilities']); print('harvested',c['harvested_capabilities'],
      'admitted',c['harvested_admitted'])
"
# bound 153 + receipt 309 = 462
# harvested 636 admitted 0     <- counts a population that cannot contain a one

grep -n 'harvested_admitted' canonical/runtime/compile_brain_unified_model_v1.py canonical/tests/test_harvested_capabilities_are_reachable_v1.py
# the counter, and the test that pins it to 0
```
