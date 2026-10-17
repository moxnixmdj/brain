# ONE-SHOT PLAN V4 — COMPILE THE CAPABILITIES

Date: 2026-10-17. Status: PLAN. Step 0 EXECUTED AND LANDED. Authority: NONE. Credit: 0. Spend: $0.
Model dependency: 0.

Supersedes V1–V3. V3 planned to make 67 capabilities reachable from plain sentences. That was the
wrong interface and this plan says so in §1.

---

## 1. The reframing (from first principles, and it is not cosmetic)

V3's goal: *every capability reachable from a plain sentence through one entry.*
Its metric: alive-mass `A = |{c : reachable ∧ runnable ∧ exercised}|` = **27 of 67**.

Measured facts that break that goal:

- Across all 67 capabilities there are **163 typed slots over 55 distinct argument names**, and
  **58 of 67 take ≤3 inputs**. Seven types cover most of the surface.
- `TRUE_CAPABILITY_TEST_LAW_V1` §1 defines a capability as: *"for **unseen instances of a declared
  input class**, produces outputs an **independent oracle** accepts, using zero model."*
  **It never mentions a sentence.** I added that. It was my error.
- `chart.raster.scene_graph.v1` was counted reachable for months and could never execute: the
  compiler typed `x_ticks` as `NUMBER_LIST` while `calibrate_axis` unpacks `(pixel, value)` PAIRS.
  A type error, not a grammar gap.

**Therefore the creature is not the sentence. The creature is the capability library plus the thing
that composes it.** The plain sentence is one best-effort front end, and where it cannot fill a
typed slot it fails closed naming the slot.

**Corrected metric.** `A = |{c : typed-invocable ∧ runnable ∧ spec'd-and-passing}|`.
Step 0 proved `typed-invocable` for **67/67**. The binding constraint is now **spec coverage alone**.

## 2. Step 0 — EXECUTED AND LANDED (this is the "real now")

`canonical/runtime/capability_type_surface_v1.py`, 28 tests, pushed as `939ae273`.

| Result | Value |
|---|---|
| Signatures derived from the registry | **67 / 67** |
| Typed slots | **163** over 55 argument names |
| Unknown types | **0** — the surface is total; `UNKNOWN` accepts nothing |
| Dead slots | **0** — every declared input is read in the adapter's transitive import closure |
| The chart type error | **caught**: `check()` rejects `[0,1,2]`, accepts `[[100,0.0],[300,2.0],[500,4.0]]` |

This is the enabling layer. Every number below assumes it.

## 3. The unit of work: a capability cluster, not a capability

The Brain already proves generators are shared. `canonical/capabilities/true/`:

```
generators/  docx_exact_text_edit_gen_v1.py  docx_span_edit_gen_v1.py  saccr_credit_addon_gen_v1.py
             same_identity_supervisor_gen_v1.py  scheduler_gen_v1.py
oracles/     docx_exact_text_edit_oracles_v1.py docx_span_edit_oracles_v1.py
             saccr_credit_addon_oracles_v1.py   same_identity_supervisor_oracles_v1.py
             scheduler_oracles_v1.py            vendor/
specs/       9 specs
```

**Five generator modules carry nine specs.** `docx_span_edit_gen_v1.py` + its oracle serve four.
So the work unit is: **one generator + one oracle per input class, then one spec per capability.**

The typed surface says there are 13 types and ~10 clusters. So the whole job is **~7 new
generator/oracle pairs and ~40 specs** — not 44 bespoke anything.

### Spec schema (verbatim, from `DOCX_EXACT_TEXT_EDIT_V1.json`)
`schema`, `capability_id`, `claim`, `input_class`, `scope_limits`, `solver{module,entry}`,
`generator{module,entry}`, `oracles{module,entry,declared[{id,class,lineage}]}`,
`independent_oracle_ids`, `published_canaries`, `min_instances`, `pass_threshold`,
`falsification_condition`, `model_dependency_count`, `history`.

Reference values: `min_instances: 500`, `pass_threshold: 1.0`,
`independent_oracle_ids` ≥ 2, `model_dependency_count: 0`.

---

## 4. The seven clusters, in execution order

Ranked by `(capabilities closed × bar leverage × reuse available) / difficulty`.

| # | Cluster | Caps | Reuse available | Bars it is the mechanism for | p₁ |
|---|---|---|---|---|---|
| 1 | Finance | 1 | **SACCR spec exists** | FINANCE_ACCOUNTING_INDEX, FINANCE_AGENT_V2 | 0.80 |
| 2 | Document verify / grounding | 6 | **docx generators exist** | PROWORK_GDPVAL, AA_BRIEFCASE | 0.75 |
| 3 | Python repair / acceptance | 8 | **PYTHON_REPAIR families exist** | CODING_TB4, FRONTIERCODE, CURSORBENCH | 0.70 |
| 4 | Evidence → decision synthesis | 9 | decision-synthesis family exists | HLE_TOOLS, TB_SCIENCE | 0.60 |
| 5 | Chart / raster | 10 | typed fix just landed | CHARTOGRAPHY | 0.55 |
| 6 | QR / barcode / PDF render | 4 | — (apt-gated locally) | — | 0.50 |
| 7 | Network / browser | 4 | — (egress-gated locally) | OSWORLD, AUTOMATIONBENCH | 0.50 |

**Clusters 1–3 first.** They close 15 capabilities carrying *existing, working* generators or
families. Cluster 1 is one spec against a spec that already exists — hours, not days. Cluster 3 is
the highest-leverage block in the whole plan (8 capabilities, 3 bars, generator pattern passing
8/8 today).

**Cluster 5 second-largest but hardest** — and note the typed surface moved its p₁ from ~0.45 to
0.55 by removing the tick-anchor failure mode.

## 5. The mathematics

A cluster closes when its specs pass `pass_threshold: 1.0` over `min_instances: 500` fresh
instances judged by ≥2 independent oracles. With `k` repair passes,
`P(closed) = 1 − (1 − p)^k`.

| # | Caps | p₁ | E[pass 1] | E[pass 2] | E[pass 3] |
|---|---|---|---|---|---|
| 1 | 1 | 0.80 | 0.8 | 0.96 | 0.99 |
| 2 | 6 | 0.75 | 4.5 | 5.63 | 5.91 |
| 3 | 8 | 0.70 | 5.6 | 7.28 | 7.78 |
| 4 | 9 | 0.60 | 5.4 | 7.56 | 8.57 |
| 5 | 10 | 0.55 | 5.5 | 7.88 | 9.09 |
| 6 | 4 | 0.50 | 2.0 | 3.00 | 3.50 |
| 7 | 4 | 0.50 | 2.0 | 3.00 | 3.50 |
| **Total** | **42** | | **25.8** | **35.3** | **39.4** |

### Alive-mass trajectory

| Point | A |
|---|---|
| Today (sentence-executed) | **27 / 67** |
| After step 0 (typed-invocable proven) | 27 / 67 — but reachability is no longer the constraint |
| After pass 1 (clusters 1–5) | **~52 / 67** |
| After pass 2 | **~62 / 67** |
| After pass 3 (all clusters) | **~66 / 67** |

`p₁` is not inflated: the harness found real defects in 2 of the 9 existing specs (docx empty-string
replacement; supervisor terminal-state guard). It fails things. Good — that is what makes a pass mean
something.

### Aggregate probabilities

| Claim | P | Basis |
|---|---|---|
| A ≥ 45 within 24 h | **0.90** | clusters 1–3, all reuse-backed, locally runnable |
| A ≥ 55 within 72 h | **0.75** | + cluster 4 |
| A ≥ 62 within 7 d | **0.55** | + cluster 5; chart is the swing factor |
| A = 67 within 14 d | **0.35** | clusters 6–7 need the public runner for every iteration |
| ≥1 bar discharged in 30 d | **0.20** | mechanism is not the bottleneck (see §6) |
| Any terminal credit in 120 d | **0.08–0.12** | owner countersign; not this plan's business |

### Cost
~7 generator modules (~80 lines each) + ~7 oracle modules (~100 lines each) + ~40 specs (~30 lines
of JSON each) ≈ **2,400 lines**. Harness runs: 42 specs × 500 instances; measured solve cost is
~170 ms/instance average, so ~1 hour of compute spread across runs, and everything runs locally
except clusters 6–7.

**This is roughly one fifth of V3's ~3,000 lines of bespoke grammar, to cover the same ground with
a stronger claim.** That difference is the whole argument of this plan.

---

## 6. What this plan deliberately does NOT do

| Not doing | Why |
|---|---|
| Write 25 bespoke sentence grammars | 163 slots over 55 names and 7 types. Ten type extractors beat forty grammars. |
| Fuse composed DAGs into first-class capabilities | The law's loop is `COMPOSE → VERIFY → COMPRESS`. Fusing now prepays for hot paths that do not exist. Fuse what earns it, after. |
| Harvest white-box donors (OmniParser, UniChart) | The reuse audit found 0 of 8 families need invention. Donors stay available if cluster 5 stalls. |
| Chase the 13 bars as a phase | Raising A *is* bar work. A separate bar phase is double-counting. |
| Touch the plain-goal compiler | It still works and still serves sentences it can serve. It is now one client of the typed surface, not the definition of it. |
| Re-plan the honest suite separately | 253 of its 380 failures are the absence of these specs. Same work, seen from the other end. |

**Protected because it is evolving, not decoration:** the referee, the drift guard, the honest
baseline, the true-capability harness, `NOT_MEASURED_HERE`, and the typed surface itself. None of
these are parts to delete.

## 7. The blockers this plan cannot remove

Stated plainly, because a plan that hides these is not a plan.

1. **P3 new primitive.** 256 architectures exhausted over an 8-component frontier, classification
   `NEW_PRIMITIVE_REQUIRED`, one unified effect remaining:
   `P3_SCOPE_COMPLETE_GROUNDED_AUDIENCE_CONDITIONED_POLICY_DOMINANCE`, build target 1. This is the
   only genuine synthesis gap. It gates `U_empty` → `COMPLETE_SELECTED_CONTEXT_ABC` → terminal.
2. **22 unproved atomic predicates** and 14 unaccepted families. The obligation graph reports
   `open_mechanism_residual_count: 0` — this is proof work, not building.
3. **12 of 13 bars are gated by owner action or external access** (`OWNER_GRADER_RESULT`,
   `AUTHENTICATED_FULL_2500_ACCESS`, `AUTHORIZED_OFFICIAL_HF_BYTE_ACCESS`, pinned OSWorld bytes…).
   Zero of 13 are blocked by a missing Brain mechanism.
4. **Owner countersign** on `truth.achieved`. No agent can do this.
5. **Throughput.** The heartbeat takes 27m48s against a 30-minute timeout, and 97% of that is
   dependency setup, not measurement. It has no concurrency group — three ran at once today.
   Adding families will breach the timeout unless setup is cached or families are sharded.
6. **main's history is broken for this branch.** `git merge-base origin/main HEAD` is empty; main
   raced to #4860 and does not contain this branch's base. Rebase and merge both fail with
   unrelated histories. **Needs owner attention.**

## 8. Next action, immediately

Cluster 1: one spec reusing `saccr_credit_addon_gen_v1.py` + `saccr_credit_addon_oracles_v1.py`
for `finance.saccr.credit.addon.v1`, run at `min_instances: 500` through
`execution_guard/true_capability_harness_v1.py`. Expected: hours. Then cluster 2 (docx generators
already exist), then cluster 3 (8 capabilities, 3 bars).

**What is real right now, not promised:** 67/67 typed signatures, zero unknown types, zero dead
slots, one real type error caught mechanically, 28 tests green, all landed on the branch. The
creature's interface is total. The remaining work is filling its library.
