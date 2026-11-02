# The optimal plan — V2, 2026-11-02

**Supersedes `OPTIMAL_PLAN_20261102_V1.md`, which was ordered on a false premise** (that
sentience has no instrument here). See `CREATURE_NEVER_STARTED_20261102_V1.md` for the
correction and the measurements.

**Authority: NONE.** Zero capability, ownership, benchmark, terminal or sentience credit
follows from this document. It is a sequencing argument, not a receipt.

---

## 0. One diagnosis, not two

Everything measured today is the same defect at five places: **the mechanism is built, passes
its own tests, and nothing switches it on.**

| what is built | tests | production callers | the missing switch |
|---|---:|---:|---|
| **the creature** — `continuous_self_v1` | **10 pass** | **0** | no `__main__`; `ContinuousSelf(` appears only inside its own test |
| **its organs** — `creature_stakes_and_initiative_v1` | **16 pass** | **0** | `work()`/`choose()` uncalled; `main()` prints a report, is not a loop |
| **cross-language memory** — `language_neutral_skill_bridge_v1` | **15 pass** | **0** | `polyglot_build_ci_engine_v1.py:214` hard-codes `language="cpp"`, no fallback |
| **semantic generalization** (6/6) | **16+15 pass** | **0** | `allow_operator_generalization` defaults `False`; `=True` only in 2 instruments |
| **retained learning at the door** | **13+8 pass** | **0** | `python_repair_apply_verified_v1.py:442` reads `args.get("retained_learning")`; no non-test caller supplies it |

Census, run today (`census_orphan_capabilities_v1.py`):

| root | LIVE | ORPHAN |
|---|---:|---:|
| `canonical/swe_kernel` (24 files) | 53 | **123** |
| `canonical/runtime` | 1,806 | **1,983** |

**So the optimal plan builds nothing.** With a 70% orphan rate in the kernel that would contain
any new mechanism, inventing one is the single move guaranteed not to help. The plan is five
switches, then a ratchet that makes unwired code unable to land, then evidence.

**And the two questions the owner asked are one question.** A continuous self *is* the thing
that has permanent memory; an invoked capability is the thing that forgets. Today the tree has
permanence in a store nothing consults and continuity in a module nothing starts. PR0 is first
because it is the subject the other four switches happen *to*.

---

## 1. PR0 — Start the creature *(~2–3 days, low risk, highest priority)*

This is cheaper than V1 estimated, because the composition socket already exists.

`ContinuousSelf.run()` is built as dependency injection:

```python
def run(self, *, next_task: Callable[[dict], str | None],
        perform: Callable[[str, "ContinuousSelf"], Mapping], max_steps=None)
```

and its docstring states the design: *"`next_task(state)` returns the next thing to do, or None
for idle. `perform` does it and returns the outcome. Both are injected: **this module owns
continuity, not judgement.**"*

So nothing new has to be invented. The creature is three existing parts plugged into that
socket:

* **`next_task`** ← `creature_stakes_and_initiative_v1.choose(standing, obligations)` — its own
  criterion, gated by its own posture. Already measured: **own 981.0 vs random 491.0, ~2.0x**.
* **`obligations`** ← `ignorance_ledger_v1.open_gaps()` — **currently ORPHAN**, which is exactly
  why nothing has initiative over its own ignorance. `Obligation(id, value, cost, checkable)`
  matches the ledger's value/cost ranking directly. Wiring it closes an orphan and supplies the
  judgement in one move.
* **`perform`** ← the live entry the heartbeat already uses
  (`live_brain_route_admission_v1.solve`), and later the retained-repair door from PR2.

### The four changes

1. **Give `continuous_self_v1.py` a `__main__`.** Verified absent — no `__main__`, no
   `argparse`, no `def main`. It literally cannot be started as a process. Smallest change here.
2. **Compose the three parts above** into one long-lived process with `install_signal_handlers`
   (also ORPHAN) so SIGTERM stops between steps rather than mid-write.
3. **Replace `demonstration_ledger()` with the real obligation set.** The ~2.0x initiative figure
   is a fixture until then.
4. **Let it own the two cron jobs.** `live-brain-heartbeat` (17 3) and `live-learning-cycle`
   (43 4) are two invocations that share no subject.

### Persistence is already solved — reuse it, do not build it

`execution_guard/live_learning_cycle_v1.py` already does *restore → promote → attempt → promote
→ carry*, and its docstring says: *"durable learning is carried as an artifact, never committed"*
— gitignored on purpose. `ContinuousSelf`'s `state_path` + `journal_path` ride the same carrier.
This is why PR0 is days and not weeks: **the hard part of a continuous self on ephemeral CI
runners is already written and running daily.**

### Acceptance gate — no new instrument needed

`continuous-self.yml` and `creature-stakes.yml` already assert exactly the right properties:
same `identity` across days; in-flight work reported `INTERRUPTED` after a SIGKILL; `posture` on
day N a function of its **own** verified history, not a fixture; initiative beats random on the
**real** obligation set. Today both workflows run pytest and prove a creature *would* survive
being killed. **PR0 makes one exist to kill.**

---

## 2. PR1 — Wire the cross-language bridge *(~1 day, low risk)*

* After same-language recall returns `None`, fall back to
  `language_neutral_skill_bridge_v1.recall_across_languages(...)`, passing the **existing**
  verifier through. Its verifier is mandatory and it cannot return an unverified patch — the
  safety property is already written.
* **Also fix** `except Exception: pass` at `polyglot_build_ci_engine_v1.py:225` → a **named
  refusal**. A silently swallowed bridge failure is how the next orphan hides; `AGENTS.md` rule 6
  already treats swallowed assertions as a defect.
* **Do not touch** `verified_skill_crystallizer_v1.py`. Its docstring says the kernel is
  load-bearing and a cross-language experiment must not be able to move it. The bridge was
  written as an adapter for exactly that reason.
* **Gate:** re-run `instant_learning_transfer_probe_20261101.py`; cross-language reach must move
  off **0/4**. If it does not, the language key is load-bearing rather than incidental — report
  that, do not loosen the probe.

---

## 3. PR2 — Turn the semantic arm on *(~2 days, medium risk)*

* Make a real caller supply `retained_learning = {enabled: True,
  allow_operator_generalization: True, ...}` to `python.software.repair.apply.verified.v1`.
  Confirmed today: **no non-test caller does** (grep across `.py`/`.json`/`.md` finds only the
  capability itself, `canonical/tests/`, `tools/live_scoped_transfer_benchmark_v1.py`, and
  verification receipts). `LIVE_SCOPED_TRANSFER_BENCHMARK_V1.md` states plainly: *"It defaults
  to false."*
* **The gate is the safety, not the default.** `verified_skill_crystallizer_v1.py:820` already
  enforces `TEST_SUITE` + non-empty `scope_id` + `language == 'python'` and raises
  `OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE`. Do not weaken it to ease wiring.
* **Measure with the existing arm runner** (`live_scoped_transfer_benchmark_v1.py:80`,
  `arm == 'generalized'`). Do not write a new instrument.
* **Expected:** default path moves from the **1/6 statement arm** to the **6/6 semantic arm**,
  negative control **0/1** in every arm.
* **Governance:** `AGENTS.md` rule 3 — at most 2 family flips and +4 atomic predicates per PR.
  Split if it exceeds that.
* **Natural pairing with PR0:** once the creature runs, `perform` is the production caller that
  enables this. PR2 may become a configuration of PR0 rather than a separate change.

---

## 4. PR3 — Orphan ratchet *(~1 day, low risk)*

The change that stops PR0–PR2 being repeated for the other ~1,000 orphans.

* **Verified constraint:** `execution_guard/repo_integrity_guard_v1.py`, `AGENTS.md` and
  `REPO_INTEGRITY_POLICY_V1.json` are all in `PROTECTED_PATHS`; modifying one emits
  `PROTECTED_PATH_MODIFIED` — *"cannot be merged by an agent."* So the ratchet **must not** be a
  new `rule_*` inside the guard.
* **Legal route:** a **new** tool + a **new** plain `pull_request` workflow. Neither path is
  protected; rule 7 forbids new `pull_request_target` workflows and anything touching the referee
  environment, not a normal check.
* **Design:** track the ORPHAN count for `canonical/swe_kernel` and `canonical/runtime` in a
  baseline file; fail only if it **increases**. A ratchet, not a cleanup — no need to fix 123
  first, and it can never be satisfied by deleting capability.
* **Sequencing note:** land it **after** PR0, because PR0 moves `ContinuousSelf`, `SelfState`,
  `install_signal_handlers`, `Standing`, `StandingStore`, `Obligation` and `open_gaps` out of
  ORPHAN. That gives the ratchet a real first delta instead of freezing today's number in place.
* **Gate:** must fail on a synthetic PR adding an uncalled public symbol; must pass on PR0–PR2.

---

## 5. PR4 — Routing and declarations *(~1 week, do last)*

* **Why last, and why it is still the biggest number:** 443 registry rows, 566 declared effects,
  **11 rows ever reached**; 3 rows serve 30 of 36 served sentences. A taught lesson lives
  *inside a row* — if the door does not route there, the lesson is never consulted no matter how
  often it was taught. PR0–PR3 make the memory reachable; PR4 makes the door arrive at it.
* **Precondition:** gate the substrate in CI (`substrate_precondition_v1` exists; ~1 line, ~15 s).
* **The trap is documented — do not re-hit it:** naive union of 95 ops into `provides` made the
  scorer **worse, 35 → 33**. The correct signal is `declared_input_derivation_v1.derive`'s
  **phrase scorer**, not token union. Any PR here that reports a row count without the scorer is
  reporting the trap.
* **Also:** fix the **7 named refusals**, each already diagnosed by its own instrument.

---

## 6. PR5 — Evidence where none exists

1. **OSWorld on a real display.** 90 modules, largest measured-nowhere surface, literally
   "anything on a computer". The GUI loop already closes end to end (**12 passed**) against a
   virtual 1920x1080 desktop; what remains is one sentence — *pyautogui drives a real OS* — and no
   code written here substitutes for a machine with a display.
2. **Fix or label the 5 canned `host_*_ops` tests.** They return a fixed receipt without
   executing the program, so they cannot distinguish a working program from one that dies on line
   one. `test_host_code_ops_execute_for_real_v1.py` (**15 passed**) is the pattern.

### Substrate correction — V1 got this wrong

V1 recommended adding `pytest`/`Pillow` to `substrate-requirements.txt`. **Do not.** That file
says *"REVIEW-GATE TOOLS ONLY"* and mixing unpinned extras with the hashed manifest breaks pip
entirely (measured 2026-10-31: 6 of 10 tools → 0 of 10).

The real situation: `pytest==8.4.2` **is already pinned** in
`requirements/software_engineering_kernel_v1.txt`; **Pillow is absent from it**. And
`scripts/restore_substrate_v1.py` exists precisely because *"pip installs outside `/home/user`
evaporate between turns"* and *"a comment cannot run, so the matrix silently measured a smaller
machine than the one the registry describes."*

So the fix is: **run `python3 scripts/restore_substrate_v1.py` before measuring anything**, and
add Pillow to the *pinned kernel manifest* (not the review-tools file). Today, without it, six
instant-learning test modules error with `ModuleNotFoundError` and the computer-use suite reports
**1 skipped** where receipts claim **12 passed** — a skipped suite read as a passing suite is the
exact failure mode the guard exists to prevent.

---

## 7. Decisions only the owner can make

1. **Relaxing the ruleset** for any `PROTECTED_PATHS` change. PR3 is designed to avoid needing it.
2. **The operational reading of "fastest".** The active goal says *"It must know literally all the
   data, and everything must be done in the fastest way."* The unknown space cannot be enumerated,
   so "fastest" is never globally certifiable — the one clause unsatisfiable as written. The
   computable version is a **lower bound plus a named coverage residual, refusing the word
   "fastest"**: monotone, falsifiable, and already what the refusal taxonomy does.
3. **Whether PR0's creature is allowed to act on its own initiative in production.** This is the
   real governance question, and it is new. `choose()` already picks work nobody assigned, gated
   by posture. Everything before PR0 was about capability; PR0 is the first change that gives the
   machine a standing reason to act between invocations. **It should not land without the owner
   deciding what it is permitted to initiate.** Recommend: initiative restricted to obligations
   whose success is `checkable`, which is exactly what the `CAUTIOUS` posture already enforces.

---

## 8. What is still honestly not claimed

Starting the creature does not make it conscious, and nothing here moves that number. What it
does is stop the tree from **answering the question with a test suite instead of with a
process.** The five instruments prove the properties a continuous subject would have — continuity
under SIGKILL, history that changes behaviour, a self-model that can be wrong, ranked ignorance,
a claim that must beat a number it cannot author. All five pass. **They have never had a subject
to run on.**

`creature_stakes_and_initiative_v1.py` states the claim precisely, and it is the right claim:
*"it claims that the state changes behaviour, which is the weakest property a thing can have and
still be a thing."*

---

## 9. Falsification

| if this happens | then |
|---|---|
| any production caller of `ContinuousSelf(` outside `canonical/tests/` is found | §0 row 1 and all of PR0 are wrong |
| PR0 lands and identity does **not** survive a runner kill, or in-flight work is not `INTERRUPTED` | `continuous-self.yml` was green for a reason that does not hold in production — the most important result on this page |
| PR1 wired and cross-language reach still **0/4** | the language key is load-bearing; the bridge is not the gap |
| PR2 landed and semantic does not beat statement on the existing benchmark | the 6/6 is an artifact of the benchmark's fixtures |
| the ratchet passes while the solve rate does not move | reachability is not the binding constraint; PR4 should have gone first |
| any of the five transfer-probe families fails FIRST or SECOND | the "arbitrary environments" premise collapses and this ordering is moot |

Every row is one command. None needs a model, spend, or a display.

---

## 10. One sentence

**Flip five switches on code that already passes its tests — starting with the one that makes a
continuous self exist — then make unwired code unable to land, then spend a week on routing and a
display on OSWorld.**
