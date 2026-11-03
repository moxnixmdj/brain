# The optimal plan — V7, after the generalization gap was measured *closed*

**2026-11-03.** Supersedes `OPTIMAL_PLAN_20261102_V6.md`, whose central premise — that a
learned code lesson cannot reach a differently-shaped instance — **is now measurably false on
this tree**. V6 was right about the mechanism it described and wrong about where the frontier is:
the narrowing machinery it proposed to build **already exists, is tested, and reaches 6/6 when its
opt-in flags are switched on.** The blocker is not missing machinery. It is a **flag default plus
a verifier-kind declaration**, and both are one-line integrations.

Authority: **NONE.** No capability, ownership, benchmark, terminal or sentience credit follows.
`truth.achieved` stays `false`. Model dependency 0. Spend $0.

---

## 0. What I measured today, and the one number that changes the plan

All fresh on `a70480d`. Three instruments, each with its own validity control.

### 0.1 The production path already generalizes — 6/6, 0 misapplications, 0 fallback search

`python3 -m canonical.tools.live_scoped_transfer_benchmark_v1` — the *real* production path
(`python_repair_apply_verified_v1` → `RetainedRepairSession` → `recall_and_apply_verified` →
`ProjectTestOracle`), three arms, fresh interpreters, an external audit separate from the visible
suite:

| case | cold | statement | generalized (`allow_operator_generalization`) |
|---|---|---|---|
| renamed | applied, 1 search | **hit** | **hit** |
| compound | applied, 1 search | **hit** (narrowed) | **hit** (narrowed) |
| if_statement | applied, 1 search | **hit** (narrowed) | **hit** (narrowed) |
| flipped | applied, 1 search | miss → 1 search | **hit** (`operator_generalization`) |
| negated | applied, 1 search | miss → 1 search | **hit** (`operator_generalization`) |
| disjunction | applied, 1 search | miss → 1 search | **hit** (`operator_generalization`) |
| negative_inclusive (control) | untouched | untouched | **untouched** |

`generalized`: **6/6 by memory, 0 search invocations, 0 oracle misapplications, control preserved.**

### 0.2 My own first attempt at this measurement was a false negative — the fifth of its species

My first probe used a **training suite that asserted the buggy semantics**, so teaching produced a
rule that could never promote a correct patch, and the honest result was 0/7. I also wrote module
bodies at column 12 so that "the method case" was not a method at all, and it reported a genuine
0. Two more instruments: the `CALLER_PREDICATE` default (0.3) and the missing pinned substrate
(§0.4).

Corrected probe, hand-written tests, per-case oracle-validity control (`buggy must fail`, `fixed
must pass`), through the same kernel:

| configuration | recalled & correct |
|---|---|
| contract + `TEST_SUITE`, flags **off** (the default) | **4 / 7** |
| contract + `TEST_SUITE`, `allow_scope_escalation` | **7 / 7** |
| contract + `TEST_SUITE`, `allow_operator_generalization` | **7 / 7** |
| negative controls where `<=` is **correct** (4 cases), flags on | **4 / 4 preserved** |

### 0.3 The published "1 of 7 novel shapes" is an artifact of a default, not a capability limit

`instant_learning_transfer_probe_20261101.py`, re-run today: 2/9 executed, 1/7 novel, 0/4
cross-language — **it calls `recall_and_apply_verified` without `required_verification_kind`, so it
runs at `CALLER_PREDICATE`.** I audited every call site by AST:

| | sites |
|---|---|
| total `recall_and_apply_verified` call sites | **55** |
| production | **14** |
| production at `TEST_SUITE` | **4** |
| production at the weak default `CALLER_PREDICATE` | **9** |
| production passing `allow_operator_generalization` | **0** (unreachable except one benchmark tool) |

Every headline number in the `INSTANT_LEARNING_SCOPE` family was produced on the weak path.
That is not fraud — the gate is doing exactly what it says. It is a **measurement conducted on the
least capable configuration and then reported as the system's reach.**

### 0.4 A silently missing substrate turns a capability into "unexpectedly None"

Two tests in `test_optimal_unified_creature_and_prc2_v1.py` failed with
`compile_rule_to_cst_skeleton → unexpectedly None`. Cause: the pinned substrate
(`tree_sitter==0.20.4`, `tree_sitter_languages==1.10.2`) was not installed. After installing the
declared versions: **27 passed**. There are **10 sites** in production where an optional-substrate
import is wrapped in `try/except: pass` — among them
`verified_skill_crystallizer_v1.py:1262/1358/1474`, `rule_scope_learning_v1.py:559/673`,
`language_neutral_skill_bridge_v1.py:136`. A missing `z3` or CST parser silently narrows the
search space and reports a refusal that looks like a finding.

---

## 1. What this changes about the plan

V6 said: build apply-time narrowing, gated on verification kind. **That is built.** The real
frontier moved, and it moved to something much cheaper and much less flattering:

> The capability exists. Its best strategies are **off by default in production**, the defaults are
> **silently weak**, and the numbers that justify the plan were **measured on the weak path.**

That is the entire optimal plan in one sentence. It is integration and instrumentation work, not
research. And it is the only kind of work that can be *verified* in the current environment.

---

## 2. The plan — ranked by measured value per unit of risk

### P1. Make the weak verifier impossible to use by accident (highest value, lowest risk)

`required_verification_kind` defaults to `CALLER_PREDICATE` at 37 of 55 call sites, 9 of them in
production. A bool callback is auto-demoted to `CALLER_PREDICATE`, which is the configuration
where §0.2's identical transformation corrupts 3 of 4 correct sources.

**The change is not "flip the flags."** With one flag on, *any* `CALLER_PREDICATE` caller would
acquire broad patterns under a verifier that cannot reject a misapplication. The correct change is
the conjunction the kernel already encodes:

```
operator generalization is admitted  ⟺  required_verification_kind == 'TEST_SUITE'
                                        ∧ scope_id present ∧ language == python
```

and the ones that are **missing**: *the verifier must be the contract-checked `ProjectTestOracle`
type, not merely declared `TEST_SUITE`*. Right now a caller can simply assert
`required_verification_kind='TEST_SUITE'` and hand a bool lambda. That is a declaration, not a
capability, and it is the one real hole in the gate.

- **Success criterion:** a `TEST_SUITE`-declared call site whose verifier is not a contract oracle
  is **refused**, with a named reason, before any broadened pattern is generated. Negative control:
  delete the check and exactly the test that pins it must fail (the mistake recorded in V6 §3.4 —
  a gate test that stayed green with the check removed).
- **Progress class:** `VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN`.
- **Risk:** low; it can only refuse more, never accept more. It cannot regress a capability.

### P2. Admit `allow_operator_generalization` at exactly the sites that qualify

Do it per call site with evidence, not by changing a global default:

| site | verdict |
|---|---|
| `autonomous_awake_loop_v1.py:1027` (`project_oracle`, `TEST_SUITE`, scoped, escalation+cross-scope already on) | **admit** — already the most capable caller |
| `retained_repair_session_v1.py:69` | **admit**, but only via its own `config['allow_operator_generalization']`, which already exists and is validated |
| `polyglot_build_ci_engine_v1.py:214/684/829/987` (rust/go/ts/cpp) | **refuse** — weak verifiers (`*_source(cand)[3] == 'OK'`); language gate would refuse anyway |
| `compose_hardcore_swe_problem_inventory_v1.py:381/393` (`_parses`) | **refuse** — a parse check is a compilation check |
| `shared_skill_transfer_benchmark_v1.py:99` | **refuse** — benchmark arm must stay at the weak baseline it measures |
| `autonomous_awake_loop_v1.py:1040/1219` | **refuse** — `_verify_in_cow` / `poly_oracle` are declared `CALLER_PREDICATE` |

- **Success criterion:** re-run `live_scoped_transfer_benchmark_v1` **cold vs generalized** and
  show the 5-search → 0-search difference survives P1's new gate; and re-run §0.2's 4 negative
  controls at 4/4 preserved.
- **Progress class:** `VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN`.
- **Risk:** medium. This is the one place a mistake widens a claim; hence P1 first, and hence the
  negative controls are the deliverable, not the recall count.

### P3. Make a missing substrate a *refusal*, never a silent narrowing (minutes)

Ten `try/except: pass` sites sit in front of optional substrates. Replace each with a named
refusal (`SUBSTRATE_MISSING:<name>:<declared_version>`) recorded in the recall result, so a
capability that did not run is never reported as a capability that refused. Add a startup
assertion against `requirements/software_engineering_kernel_v1.txt`.

- **Success criterion:** with the substrate removed, the recall result carries
  `SUBSTRATE_MISSING:tree_sitter` instead of `None`; with it restored, 27/27 again.
- **Progress class:** `GOVERNANCE_GUARD_NO_PROGRESS_CLAIM` (truth-telling, not capability).
- **Risk:** trivial. Do it first because it protects every other measurement.

### P4. Wire rule expiry + scope calibration through the production repair path (one edge)

`RetainedRepairSession.teach()` already calls `rule_expiry_v1.record_taught` and
`calibrate_rule_scope` — inside `try/except: pass`. But `propose()` **never consults expiry**, and
`live_brain_route_admission_v1` never mentions `rule_expiry` at all. So a rule can be recalled
without anyone asking whether the world under it changed.

- **Success criterion:** a rule taught under interpreter/platform A and recalled under a changed
  world is reported `STALE` and **not offered**, until `reverify()` moves it to `FRESH`. Negative
  control: with the check removed, the stale rule is offered.
- **Progress class:** `VERIFIED_RELIABILITY_GENERALIZATION_OR_EFFICIENCY_GAIN`.
- **Risk:** low, fail-closed by construction.

### P5. Feed recall *misses* back as scope evidence (the only path to a wider hypothesis space)

`rule_scope_learning_v1` owns the mathematics (`select_probe`, `update_version_space`) and is wired
to the awake loop and the retained-repair path — but nothing consumes a **production** miss. My
probe produced exactly such signals: 3 misses under flags-off, 0 under flags-on. A miss on a
structurally similar instance is a falsification of the current scope, and it is the raw material
the tree keeps saying it lacks.

- **Success criterion:** with flags off, the store's own scope estimate moves from
  `SCOPE_STATEMENT` toward `SCOPE_OPERATOR` **because the probe failed**, not because a human said
  so — and the rule then recalls the 3 cases it used to miss, with the 4 negative controls intact.
- **Progress class:** `VERIFIED_REUSABLE_CAPABILITY_GAIN`.
- **Risk:** medium-high; it changes what the system believes about itself. Keep it behind the
  hysteresis the module already has and require the counterexample to be *executed*, not inferred.

### P6. Do **not** connect the learner to the unified front door yet, and do not run unattended

Freshly measured: `coding_goal_reuse_probe_20261102.py` → all three raw-goal arms stop at
`BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT`. That is **correct behaviour on an unmet
precondition**. P1–P5 improve the *direct* production path, which is where the 6/6 was measured.
Closing the last hop needs a distinct verifier with a real run reference — a person, not a flag.
A creature that closes 0/112 should not be placed on a cron.

---

## 3. Where the real frontier is, stated so it cannot be mistaken for a to-do item

§0.1 raised recall from 4/7 to 6/6 **without a single new abstraction**: the operator-generalization
module already knew that `not (x > hi)` and `x < hi or x == hi` mean the same bound, and a human
wrote it. The remaining reach problem is the same one `INSTANT_LEARNING_SCOPE` names: the machine
narrows a lesson's **scope** by measurement, but a person still authors **which shapes are
representable**. P5 attacks it; nothing on this list solves it. Claiming otherwise would be the
error the laws exist to prevent.

And the observation boundary is untouched: everything above concerns *code*, where a real test
suite is the oracle. **Pixels are still not a hashable state**, the CLI/GUI recipe layer is still
documented-but-unimplemented, and "anything on a computer" remains gated on that layer, not on
learning speed.

---

## 4. Non-claims for this document

Nothing here registers a capability, flips a family, moves a ledger row or claims sentience.
§0.1's 6/6 is a **non-blind constructed** benchmark on one lesson family, produced by the same
person who wrote the plan; it is a measurement, not an independent qualification. Every number
above carries its instrument, and four of today's five instrument defects are recorded in §0.2 and
§0.4 precisely so the next session does not inherit them as facts.
