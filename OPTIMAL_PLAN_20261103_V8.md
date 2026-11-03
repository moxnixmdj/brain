# The optimal plan — V8, after pricing every live refusal with the tree's own classifier

**2026-11-03.** Supersedes `OPTIMAL_PLAN_20261103_V7.md` only where measurement changed the
ranking. V7's P1 is **built, proven load-bearing, and pushed** (`a3d5a29`). This document is about
what is left, and it removes one item from V7's list because **the plan was trying to build a
capability that does not exist yet and cannot exist on this host.**

Authority: **NONE.** No capability, ownership, benchmark, terminal or sentience credit follows.
`truth.achieved` stays `false`. Model dependency 0. Spend $0.

---

## 0. What is already banked (do not re-plan it)

| item | state | evidence |
|---|---|---|
| P1 — a declared `TEST_SUITE` must be a contract oracle | **LANDED** `a3d5a29` | gate deleted → 4/6 gate tests fail; gate present → 6/6; 167 focused tests pass; guard 17/17 |
| Production repair path reaches novel shapes | **MEASURED, unchanged by P1** | `live_scoped_transfer_benchmark_v1`: generalized arm 6/6 by memory, **0 searches**, 7/7 external audits, inclusive-boundary control untouched |

So the generalization gap V6 was organised around is closed *on the path where the fix is real*,
and the gate that made it safe is now enforced instead of asserted. That is banked.

---

## 1. The measurement that re-ranks the plan: all 12 refusals, priced

I re-ran the live front-door census (`execution_guard/swe_advanced_probe_v1.py --json`, fresh
today) and priced every refusal with the tree's **own** classifier
(`compose_hardcore_swe_problem_inventory_v1.defect_owner`), not my judgement:

```
requests 49   served 37   refused 12

CAPABILITY (7)  FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
                #17 perf, #19 perf, #21 systems, #28 tests, #30 debug, #31 debug, #46 git
SELECTION  (1)  TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY                        #45
FIXTURE    (4)  NO_FLAKY_TEST_DETECTED, NO_REPRODUCIBLE_BUG_SPECIFIED_OR_OBSERVED,
                NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS, TARGET_SYMBOL_COLLISION
```

**Seven of twelve refusals are one single cause: no admitted confinement carrier.** They are not
seven defects. They are one gate refusing seven different sentences, all of which need to execute
something on the machine. That is a *concentration* measurement, and it points the plan at exactly
one thing — or at admitting honestly that the thing is out of reach here.

### 1.1 I checked whether that thing is reachable on this host. It is not.

| requirement (from `COMPUTER_EXECUTION_BOUNDARY_DRAFT_20261102.md`) | this host |
|---|---|
| user + mount + PID namespaces | **available** (`unshare -Umpf` succeeds) |
| **network namespace** | **FAILS** — `unshare -n` → `Operation not permitted` |
| bwrap / nsjail / docker / podman | **all missing** |
| cgroup v2 aggregate CPU/mem/PID limits | **not writable** — no user delegation |
| libseccomp present | yes (but a seccomp profile is not a filesystem/CPU boundary) |

The documented minimum for a production carrier is *"a pinned minimal tool/runtime image, reviewed
isolation and process cleanup, **aggregate CPU/memory/PID limits**, a bounded broker with
independent artifact/effect validation and no unsafe publication"*. **The aggregate-resource
requirement cannot be satisfied here at all**, and network isolation cannot either. Building the
carrier is therefore not a coding task on this host; it is a *procurement* task for a host with
delegated cgroups, and then an independent-verification task.

**Consequence for the plan: the single largest block of live refusals (7/12) is not addressable by
writing code in this repository right now.** Any plan that puts it first is a plan to feel
productive while the number does not move. It stays refused, correctly.

---

## 2. The plan

### P3 (do next) — a missing substrate must be a refusal, never a silent narrowing

This is the only item on the list that (a) I can complete here, (b) protects every other number,
and (c) is bounded.

**Already half-built, so this is REUSE not SYNTHESIS:** `test_the_declared_substrate_is_the_verified_substrate_v1.py`
already compares the pinned manifest against the kernel constant, and
`tree_sitter_swe_kernel_v1.parser_for` already raises `TREE_SITTER_SUBSTRATE_MISSING`. What is
missing is that **10 production sites wrap the optional-substrate import in `try/except: pass`**
(`verified_skill_crystallizer_v1.py:1262/1358/1474`, `rule_scope_learning_v1.py:559/673`,
`language_neutral_skill_bridge_v1.py:136`, and four more), so a missing parser becomes
`recall_strategy: None` — indistinguishable from "the rule genuinely does not apply".

- **Deliverable:** a `SubstrateUnavailable` result field (`SUBSTRATE_MISSING:<name>:<pinned_version>`)
  carried in the recall result, plus a preflight helper in `skill_verification_contract_v1`.
- **Success criterion:** with `tree_sitter_languages` made unimportable, the recall result carries
  `SUBSTRATE_MISSING`, and the affected capabilities **refuse** rather than return `None`;
  with it restored, the same calls reach the same 6/6 as today. Negative control: delete the
  preflight and the new test must fail.
- **Why it is first:** today I made two tests go from *fail* to *pass* merely by installing two
  declared packages. Every capability number produced without this check is ambiguous.
- **Risk:** low; it can only cause more refusals. **Progress class:** `GOVERNANCE_GUARD_NO_PROGRESS_CLAIM`.

### P4 — bind rule validity to the last verification, not to nothing

`rule_expiry_v1` is recorded at teach time (`record_taught`, inside `try/except: pass`) and
**never consulted at recall time**; `live_brain_route_admission_v1` does not mention `rule_expiry`
at all. A rule can therefore be recalled without anyone asking whether the world under it moved.

- **Deliverable:** consult expiry inside `RetainedRepairSession.propose()` before recall; offer
  only `FRESH`; `reverify()` is the only transition back.
- **Success criterion:** teach under world A, change the recorded fingerprint, recall → rule is
  `STALE` and **not offered**; `reverify()` with a real verifier restores it. Negative control:
  remove the consultation and the stale rule is offered.
- **Risk:** low, fail-closed by construction. It will *reduce* retained hits in any environment
  whose fingerprint is unstable — that is the point, and it must be reported, not hidden.

### P5 — feed production misses to the version-space diagnoser (the real frontier)

`rule_scope_learning_v1` owns the mathematics and `select_probe` is now called from it, but nothing
consumes a **production** miss. In §0 the flags-off path produced three such misses and the
flags-on path produced none: that is a falsification of the current scope, sitting unused.

- **Deliverable:** on a recall miss under a contract oracle, feed `(instance, outcome)` to
  `refine_scope_from_counterexample`; let the store's own `learned_scope` move.
- **Success criterion:** with broadening flags off, the store moves `SCOPE_STATEMENT` →
  `SCOPE_OPERATOR` **because a probe failed**, and then recalls the three cases it used to miss,
  with the four `<=`-is-correct controls still preserved.
- **Risk:** high — it changes what the system believes about itself. Gate it on an *executed*
  counterexample, never on inference, and keep the existing hysteresis.
- **Route order note:** this is `INTEGRATE`, not `SYNTHESIZE_NEW_PRIMITIVE`; both endpoints exist.

### P6 — the seven confinement refusals: decide, do not drift

Three options, and only one of them is honest on this host:

1. **Build a production carrier here** — impossible as specified (§1.1). Do not attempt.
2. **Weaken the guard so the seven serve** — forbidden. It would convert seven honest refusals
   into unconfined host execution with the caller's authority, which the tree already measured as a
   real defect once.
3. **Write the qualification harness now, run it where the carrier can exist.** Ship: the exact
   host requirements as an executable preflight (namespaces, cgroup delegation, image pin), a
   broker interface with independent artifact/effect validation, and the refusal that already
   exists. Then the seven flip in one admission step on a capable host, with a separate verifier.
   **This is the only item with real reach and it cannot be finished here.** Its honest status is
   `BLOCKED_ON_HOST`, not "in progress".

### Do not do

- **Do not flip `allow_operator_generalization` in production callers** (V7's P2) before P3 and P4.
  Prod sites that could receive it are weak-verifier sites (P1 now refuses them) or the awake
  loop/retained path (already capable via `allow_scope_escalation`). There is no gain left there;
  there is only risk.
- **Do not connect the learner to the unified front door.** Freshly measured: all three raw-goal
  arms stop at `BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT`. That is correct.
- **Do not run unattended.** 0/112 self-authored obligations closed is the honest number.

---

## 3. What the ranked list looks like once the unbuildable is removed

| rank | item | reachable here | moves a live refusal | risk |
|---|---|---|---|---|
| 1 | P3 substrate refusal | **yes** | no (protects all numbers) | low |
| 2 | P4 expiry at recall | **yes** | no (prevents false hits) | low |
| 3 | P5 miss → scope | **yes** | indirectly | high |
| 4 | P6 carrier qualification harness | **no — host-blocked** | **yes, 7/12** | n/a |
| — | P2 generalization flags | yes but no gain left | no | — |
| — | front-door connection | gated on a person | — | — |

The uncomfortable conclusion, stated plainly: **the largest remaining block of refusals is blocked
by the host, not by the code.** The best available work is to make the remaining numbers
unambiguous (P3, P4) and to attack the one frontier that is genuinely a synthesis problem (P5).
A plan that claims otherwise would be the exact failure mode `GOVERNANCE_GUARD` exists to prevent.

---

## 4. Non-claims

§0's 6/6 is a non-blind constructed benchmark produced by the person who wrote the plan — a
measurement, not an independent qualification. §1's prices come from the tree's own classifier
applied to a fresh census; the classifier's `OWNER_OF_REMEDY` table is narrower than reality, and
one row (#45) is priced `selection` where the adapter's own refusal names a different cause. P1 is
on the branch and **unadmitted**: V22 prewrite admission, a recursive OBS receipt, a valid
blocker-lease key and independent verification are still missing, and none of them can be
manufactured by an agent.
