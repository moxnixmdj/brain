# The optimal plan — 2026-11-02

> **SUPERSEDED by `OPTIMAL_PLAN_20261102_V2.md`.** This V1 was ordered on a premise that
> `CREATURE_NEVER_STARTED_20261102_V1.md` then falsified: it filed sentience under "no
> instrument here", when in fact five instruments exist and pass, and the real gap is that the
> creature they describe is never started. V1's PR1–PR5 (bridge, semantic arm, orphan ratchet,
> routing, OSWorld) survive unchanged in V2; what V2 adds is **PR0 — start the creature — which
> comes first.** Kept, not deleted, so the correction trail is visible.

**Authority: NONE.** Zero capability, ownership, benchmark, terminal or sentience credit
follows from this document. It is a sequencing argument, not a receipt.

Companion to `INSTANT_LEARNING_VERDICT_20261102_V1.md`, which holds the measurements. This
file holds only the ordering and the acceptance gates.

---

## 0. The diagnosis that determines the ordering

Every mechanism the owner's claim needs is **built and passing its own tests**. All three
gaps found on 2026-11-02 are the *same* gap at three different places: **nothing switches it
on.**

| mechanism | tests | reachable from production? | the switch that is off |
|---|---:|---|---|
| cross-language bridge | **15 pass** | **no — zero callers** | `polyglot_build_ci_engine_v1.py:214` hard-codes `language="cpp"`, no bridge fallback, wrapped in `except Exception: pass` |
| semantic generalization (**6/6**, negative control refused) | **16 + 15 pass** | **no** | `allow_operator_generalization` defaults `False`; `=True` appears in exactly 2 files, both instruments |
| retained learning at the repair door | **13 + 8 pass** | **no** | `python_repair_apply_verified_v1.py:442` reads `args.get("retained_learning")`; **no non-test caller supplies it**. Confirmed by grep across `.py`/`.json`/`.md`: only the capability itself, `canonical/tests/`, `tools/live_scoped_transfer_benchmark_v1.py`, and verification receipts |
| version-space scope narrowing | **14 pass** | **yes** | already wired on 2026-11-01 (`select_probe` → `rule_scope_learning_v1`, 6/7 → 7/7) |

Row 4 is the proof that rows 1–3 are cheap: the identical defect was found, wired, and
produced a measured jump in one session.

**The census that says this is systemic, not incidental** (`census_orphan_capabilities_v1.py`,
run 2026-11-02):

| root | LIVE | TEST_ONLY | ORPHAN |
|---|---:|---:|---:|
| `canonical/swe_kernel` (24 files — the learning kernel) | 53 | 0 | **123** |
| `canonical/runtime` | 1,806 | 7 | **1,983** |
| whole tree | 2,166 | 1,170 | **1,018** |

Therefore: **the optimal plan is not to build anything.** It is to connect three existing
modules, then make disconnection visible, and only then buy the evidence the owner's plan
actually wants. New mechanisms are the one move guaranteed not to help, because the tree
already has a 70% orphan rate in the kernel that would contain them.

---

## 1. The sequence

Ordered by (measured capability gain × reuse breadth) ÷ (risk × wall-clock). PR1–PR3 are the
same shape and are deliberately consecutive: each one converts an already-tested module into
a reachable capability, which is the tree's own progress class
`VERIFIED_INTEGRATION_OF_OWNED_CAPABILITY`.

### PR1 — Wire the bridge. *(highest leverage per hour in the tree today)*

* **Change:** in `polyglot_build_ci_engine_v1.py`, after same-language recall returns `None`,
  fall back to `language_neutral_skill_bridge_v1.recall_across_languages(...)` with the
  **existing** verifier passed through unchanged. The verifier is mandatory in that function
  and cannot return an unverified patch — the safety property is already written.
* **Also fix:** replace `except Exception: pass` at that site with a **named refusal**. A
  silently swallowed bridge failure is how the next orphan hides, and `AGENTS.md` rule 6
  already treats swallowed assertions as a defect.
* **Do not touch:** `verified_skill_crystallizer_v1.py`. Its own docstring says the kernel is
  load-bearing and a cross-language experiment must not be able to move it. The bridge was
  written as an adapter for exactly that reason. Respect it.
* **Acceptance gate:** re-run `instant_learning_transfer_probe_20261101.py`. Cross-language
  reach must move off **0/4**, and the probe must still report the same 15-test bridge suite
  green. If reach is still 0/4 after wiring, the language key is load-bearing rather than
  incidental and §0 row 1 is wrong — report that, do not loosen the probe.
* **Cost:** ~1 day. **Risk:** low — the module proposes, never applies.

### PR2 — Turn the semantic arm on at the production door.

* **Change:** make a real caller supply
  `retained_learning = {enabled: True, allow_operator_generalization: True, ...}` to
  `python.software.repair.apply.verified.v1`. The gate at
  `verified_skill_crystallizer_v1.py:820` already enforces `TEST_SUITE` + non-empty
  `scope_id` + `language == 'python'` and raises
  `OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE` otherwise. **The gate is the
  safety; the default is not.** Do not weaken the gate to make wiring easier.
* **Measurement vehicle already exists:** `tools/live_scoped_transfer_benchmark_v1.py:80`
  runs both arms (`arm == 'generalized'`). Use it. Do not write a new instrument.
* **Expected effect:** the default path moves from the **1/6 statement arm** to the **6/6
  semantic arm** — the largest single measured jump available in the code-repair learner,
  with **0/1** on the negative control in every arm.
* **Governance constraint:** `AGENTS.md` rule 3 — at most **2 families flip to PASS per PR**,
  at most **+4 atomic predicates**. If this wiring flips more than two families, split it.
* **Cost:** ~2 days. **Risk:** medium — it changes a production door, so it needs the referee
  green and honest before/after numbers, not a narrative.

### PR3 — Make disconnection blocking: an orphan ratchet.

This is the change that stops PR1 and PR2 from having to be repeated for the other ~1,000
orphans.

* **Critical constraint, verified:** `execution_guard/repo_integrity_guard_v1.py`,
  `AGENTS.md`, and `REPO_INTEGRITY_POLICY_V1.json` are all in `PROTECTED_PATHS`. Touching any
  of them emits `PROTECTED_PATH_MODIFIED` — *"this PR cannot be merged by an agent."* So the
  ratchet **must not** be added as a new `rule_*` in the guard.
* **The legal route:** a **new** tool plus a **new** workflow. Neither path is protected, and
  adding a non-`pull_request_target` workflow is permitted (rule 7 forbids *new*
  `pull_request_target` workflows and anything touching the referee environment — a plain
  `pull_request` check is fine).
* **Design:** record the current ORPHAN count for `canonical/swe_kernel` and
  `canonical/runtime` in a tracked baseline file; the check fails only if the count
  **increases**. A ratchet, not a cleanup — it does not require fixing 123 orphans first, and
  it can never be satisfied by deleting capability.
* **Acceptance gate:** the new check must fail on a synthetic PR that adds an uncalled public
  symbol, and pass on PR1 and PR2 (which *reduce* the orphan count).
* **Cost:** ~1 day. **Risk:** low.

### PR4 — Declarations and routing. *(highest total value, highest cost, do it last)*

* **Why last:** 443 registry rows / 566 declared effects / **11 rows ever reached**; 3 rows
  serve 30 of 36 served sentences. A taught lesson lives *inside a row* — if the door does not
  route a sentence to that row, the lesson is never consulted no matter how often it was
  taught. So the owner's "give it a try in all the new environments" collides with a
  **declaration table first and a memory table second.** PR1–PR3 make the memory reachable;
  PR4 makes the door arrive at it.
* **Precondition, already identified:** gate the substrate in CI (`substrate_precondition_v1`
  exists; ~1 workflow line, ~15 s).
* **The trap is already documented and must not be re-hit:** naive union of 95 ops into
  `provides` made the scorer **worse, 35 → 33**. The correct signal is
  `declared_input_derivation_v1.derive`'s **phrase scorer**, not token union. Any PR here that
  reports a row count without reporting the scorer is reporting the trap.
* **Also:** fix the **7 named refusals** — each is already diagnosed by its own instrument
  (`extract_function` region invalid, `git_branch` target not in stdlib, `find_definition`
  unserved, +4). Cheapest capability gain inside this PR.
* **Cost:** ~1 week. **Risk:** medium — it moves the denominator, so every number must be
  reported before and after.

### PR5+ — Buy evidence where none exists.

1. **OSWorld against a real display.** 90 modules, the largest measured-nowhere surface, and
   it is literally "anything on a computer." The GUI loop already closes end to end
   (**12 passed**) against a virtual 1920x1080 desktop; what remains is one sentence —
   *pyautogui drives a real OS* — and no code written here substitutes for a machine with a
   display.
2. **Fix or label the 5 canned `host_*_ops` tests.** They return a fixed receipt without
   executing the program, so they verify routing and **cannot distinguish a working program
   from one that dies on line one**. `test_host_code_ops_execute_for_real_v1.py` (**15
   passed**) is the pattern to copy.
3. **Environment note for any agent running these:** this tree needs `pytest` and `Pillow`.
   Without them, six instant-learning test modules error with `ModuleNotFoundError` and the
   computer-use suite silently reports **1 skipped** where the receipts claim **12 passed**.
   A skipped suite that is read as a passing suite is the exact failure mode the guard exists
   to prevent. Consider declaring both in `substrate-requirements.txt`.

---

## 2. Decisions only the owner can make

These are not tasks. An agent must not self-authorize any of them.

1. **Relaxing the ruleset** for any change to a `PROTECTED_PATHS` file. PR3 is designed to
   avoid needing this; if the ratchet is wanted *inside* the guard instead, it requires the
   owner in the web UI for that one merge.
2. **The operational reading of "fastest".** The active goal says *"It must know literally all
   the data, and everything must be done in the fastest way."* The unknown space cannot be
   enumerated, so "fastest" can never be certified globally — this is the one clause that
   cannot be satisfied as written. The computable version is a **lower bound plus a named
   coverage residual, refusing the word "fastest"**, which is monotone, falsifiable, and
   already what the refusal taxonomy does. Adopting it is an owner decision, not agent
   reinterpretation.
3. **Sentience stays a non-claim.** No instrument in this tree measures it, and the canonical
   objective asks for `THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_
   SOLVING_SYSTEM_POSSIBLE`. The measurable half — `ignorance_ledger_v1`, **13 tests passing**,
   a self-model of ignorance ranked by the value of closing each gap — is real and worth
   extending. The word is not the objective, and asserting it would put every real number
   above at risk.

---

## 3. The one-sentence version

**Connect the three modules that already pass their tests, make disconnection a blocking
check, and only then spend a week on routing and a display on OSWorld.**

The owner's instinct — *give it a try in all the new environments and it learns permanently* —
is correct, and the transfer probe reproduces it exactly (5/5 families, 10/10 new instances by
recalled plan, four families at **1 trial**). But it is **step 4, not step 1**. Until the door
can reach what the store already knows, every new environment teaches the machine something it
cannot retrieve, and the lesson count rises while the solve rate does not — which is precisely
the 6/9-vs-6/9 result already on record.

---

## 4. What would falsify this plan

* **PR1 wired and cross-language reach still 0/4** → the language key is load-bearing, §0 row 1
  is wrong, and the bridge is not the gap.
* **PR2 landed and the semantic arm does not beat the statement arm on
  `live_scoped_transfer_benchmark_v1.py`** → §0 row 2 is wrong and the 6/6 is an artifact of
  the benchmark's own fixtures.
* **The orphan ratchet passes while the solve rate does not move** → reachability is not the
  binding constraint, and PR4 (routing) should have gone first.
* **Any of the five transfer-probe families failing FIRST or SECOND** → the
  "arbitrary environments" premise collapses and this whole ordering is moot.

Each is one command. None needs a model, spend, or a display.
