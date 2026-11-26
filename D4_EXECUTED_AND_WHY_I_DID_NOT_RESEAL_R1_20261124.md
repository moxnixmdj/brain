# "go" executed. D4 is smaller than I predicted; R1 re-seal is refused with the reason.

**2026-11-24 · `0067ac81` · `arena/283e85a5-brain`**

Two open items got "go": D4 (widen the forge) and the R1 governance re-attestation. One is done and
undercounted by my own prediction. **The other I am handing back to you, because sealing it would
assert something false.**

---

## 1. D4 — and two premises of mine that were wrong

I predicted: *"the forge admits 0/12 → ≥4/12 by widening entrypoint discovery."*

**Wrong premise 1 — the "0 admitted" was mine, not the forge's.** My earlier harness passed `[]` for
`cases` and `require_kill`. `forge()` returns `FEWER_THAN_TWO_INPUTS` **before it ever calls the
module.** A refusal caused by an empty case list is not evidence about a module.

**Wrong premise 2 — the forge already reached 15 of 33.** It had module-level `run`/`invoke` for
those. And my **first version of the widened rule broke all 15**, because it spread the case dict
across their parameters instead of passing it as the single `args` they expect. I only found it
because I measured **regressions** as well as gains.

### What the widened rule actually is

`_bind_entrypoint()` prefers `run`/`invoke`/`main`/`verify`/`check`/`compose`/`decompose`/`execute`,
then any single public callable the module defines, and binds arguments to the signature it finds:

- supplies `root` for an unbound root/repo parameter,
- passes the **whole case dict** for a single required parameter, or for an `args`/`payload`/`case`-shaped one,
- skips anything with a default.

### Measured, empty case dict

| | before | after |
|---|---|---|
| discoverable entrypoint | **15 / 33** | **17 / 33** |
| invoke end-to-end to a dict | **2** | **3** |

Gained: `brain_module_invoke_runner_v1`, `broad_objective_decompose`,
`structural_mutation_families_v1`.

The one apparent regression — `open_research_source_frontend` — needs
`run(objective, decomposition)` and was **never callable with an empty case under the old rule
either**. It binds correctly when its two arguments are supplied.

**Against my prediction this is a miss: +2 discoverable, not 0/12 → 4/12.** I am recording that. The
remaining 16 need domain arguments (a source path, an objective, an XBRL instance) that a case dict
legitimately must carry — binding them with placeholder inputs to make a number would be the exact
thing this repository keeps getting burned by.

---

## 2. R1 re-seal — refused

`CURRENT_TERMINAL_AUTHORITY.json` pins `git_blob_sha` for the fabric, invoker and subruntime, and all
three drifted **before** I touched anything. Re-sealing is mechanically easy: rewrite three hashes.
I read the records first.

| | record asserts | live fabric reports |
|---|---|---|
| `live_owned_capability_count` | **90** | **494** |
| `verified_bound_capability_count` | — | **447** |
| `r1_drift_locked` | `True` | `False` (drift) |
| `verification_status` | `PASS__R1_CURRENT_BYTE_ARCHITECTURE_RESEALED__9_OF_9_FOCUSED_REGRESSION` | gate reports **5 errors** |
| registry tests | `test_live_capability_invoker_v1` blob pin | **also drifted** |

**The attestation is stale in substance, not only in bytes.** It asserts 90 capabilities where there
are 494 — a 5.5× change in the size of the live ontology. Its `9_OF_9_FOCUSED_REGRESSION` claim
cannot be reproduced: the gate that makes that claim fails on 5 checks.

Writing new hashes into those fields would produce a record that is **byte-current and
substantively false**, and the record's own status string says what it is certifying —
`CURRENT_RUNTIME_BYTES_REBOUND`, `RESEALED`. I would be forging an architecture reseal.

**What a real re-attestation requires**, in order:

1. Decide whether **90** or **494** is the live-owned ontology, and make the ownership provider agree
   with the fabric. Right now the fabric computes 494 from `H100_VERIFIED_CAPABILITY_REGISTRY_V8` +
   447 bound capabilities; the governance record says 90.
2. Re-run the gate and get its **own** verdict, not a hash update.
3. Then, and only then, rebind the bytes — including `test_live_capability_invoker_v1.py`, whose
   blob pin is a *test file*, so the test that checks integrity is itself pinned by the record it
   checks. That is a circularity worth fixing before anyone signs it.
4. Recompile the artifact afterwards (the exists-to-prevent-32/33 note in
   `rebind_intent_and_verify_gates_v1.py` explains why order matters).

**This is a decision about which number is true, and it is not mine to make.** It is the one item in
this whole sequence where the honest move is to stop.

---

## 3. State of every item across the session

| item | status | measured effect |
|---|---|---|
| D1 fabric lazy imports | **done** | import **188 → 28 ms**, 239 → 3 modules, no HTTP client |
| D2 stat-signature cache | **done** | warm `open_model()` **112 → 13 ms**; tamper still `MODEL_DIGEST_MISMATCH` |
| D5 `decide()` crash | **done** | answers on an unindexed page, ~100 µs |
| D6 operator-swap in zipper | **done** | `a-b` bug **repaired in 1.0 s**, 1 candidate |
| library census tool | **done** | 447 declared → **218 distinct**; 176 ids → 1 file |
| L1 docstring descriptions | **done** | askable **11% → 47%**; recall curve **.984→.756** became **1.000→.989** |
| two-tier routing | **done** | askable population **98.8%**; stubs 0/105 on written requests |
| D4 widen the forge | **done, smaller than predicted** | **15 → 17** discoverable, **2 → 3** invocable |
| L2 collapse duplicates | **withdrawn** | the 176 register 176 *different real modules* |
| L3 tune BM25 | **closed** | the scorer was never the defect; the text was |
| **R1 re-seal** | **refused, returned to you** | the record asserts 90; the fabric reports 494 |

**Tests: 80 passed across the six suites I own; 2 failures remain and both are on `main`** — they are
the R1 blob pins, i.e. exactly the decision above.

---

## 4. What the session actually established

The pattern held every single time, and it is now the thesis:

> **Every underperformance was a fact already in the repository that nothing connected.** A docstring
> no compiler read. A swap table no repair chain imported. A 27-import table loaded eagerly. A
> coverage gate counting a token that distinguishes nothing. A forge that could not see a signature
> it had never been told about.

And every fix **removed** something — 27 imports, an 11.6 MB read, a crash, a candidate population, a
spread of arguments — which is why "best part is no part" kept being the right instruction rather
than a slogan.

The frontier problem in this repository was never missing capability. **It was unread evidence.**

---

## Honest limits

- D4's **17/33** is measured with an **empty case dict**. With domain arguments the number is
  different and I have not measured it, because inventing plausible arguments is how you get a green
  number that means nothing.
- The R1 section is a **judgement**, not a measurement: I am arguing that 90 ≠ 494 makes the record
  false. If 90 is the intended live ontology and 494 is a fabric overcount, then the *fabric* is wrong
  and this refusal is still correct — different fix.
- Nothing in this turn changed the model artifact, so routing numbers from the previous turn stand
  unchanged and were not re-run.
