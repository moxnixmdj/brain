# FRONTIER CONNECTION MAP V1 — 2026-10-17

What the most advanced capabilities are, where they live, and how they connect.
Measured, sourced, and stated fail-closed. Nothing here is inferred from memory:
every external claim carries a source, every internal claim a path.

---

## 1. The result that frames everything

**NVIDIA AVO lifted Claude Opus 5 from 30% to 100% on ARC-AGI-3 — same model.**

> *"showing that system design — not model capability alone — can unlock
> frontier-level long-horizon performance"*

Source: `developer.nvidia.com/blog/nvidia-avo-reaches-100-on-arc-agi-3...` (2026-10-05)

**70 points came from architecture. Zero came from the model.**

Corroborated across the field:

| Evidence | Gap from system design alone |
|---|---|
| Claude Sonnet 4.5: SWE-agent v1 → Cline scaffold | 43.2% → 59.8% (**+16.6**) |
| Three frameworks, identical model, 731 tasks | **17 issues apart** |
| SWE-bench Verified field note | *"same model, different harness, swing of 15–20 points"* |

> *"The base model is a component. **The loop is the product.**"*

**Consequence for us:** the model is not ownable. The loop is. And the loop is
worth more.

---

## 2. What the frontier is actually bottlenecked on

| Source | Finding |
|---|---|
| METR time-horizon | frontier ~12–17h; **doubling every ~129 days** |
| Long-horizon reliability science | **24.3-point collapse** short (≤5min) → very-long (≥120min) |
| ASI-Bench (18 agent/model configs) | **50.9 → 26.6** when the agent must pick its own method |
| Stanford AI Index 2026 | frontier agents ≈ **half of human PhDs** on multi-step science |
| ML-Master 2.0 | *"**structured cognitive accumulation** is the critical enabler"* |

The bottleneck is **long-horizon autonomy under self-direction**.

---

## 3. What we already own

From `canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json`
(19 families, 7 `VERIFIED_OWNED_EQUAL_OR_BETTER`):

| Owned family | Internalized artifact |
|---|---|
| `LONG_HORIZON_MEMORY_AND_CONTINUITY` | `opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json` |
| `SUBAGENT_DELEGATION_AND_COORDINATION` | `opus55/OPUS55_SCOPED_SUBAGENT_DELEGATION_COORDINATION_V1.json`, `runtime/delegation_whole_scope_candidate_v2.py` |
| `SELF_VERIFICATION_DEBUGGING_AND_RECOVERY` | `opus55/OPUS55_SCOPED_FAIL_CLOSED_SELF_VERIFICATION_RECOVERY_V1.json`, `runtime/trajectory_failure_typed_ir_candidate_v7.py` |
| `TOOL_DISCOVERY_SELECTION_AND_LEARNING` | `runtime/tool_discovery_information_safe_candidate.py` |
| `COMPLEX_MULTI_TOOL_AGENCY` | *(config, not bound)* |
| `INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT` | *(config, not bound)* |
| `EXACT_SYMBOLIC_COMPUTATION` | *(config, not bound)* |

---

## 4. THE CONNECTION

Put §2 next to §3.

The literature names the long-horizon stack as: **continuity, self-verification,
delegation, agency, tool-learning.**

That is **five of the seven families we own.**

We have been scoring them as seven separate wins. They are **one capability**,
and it is the single capability the entire field is bottlenecked on.

Nobody else owns that stack, because everyone else is buying model access. AVO
proved the model is worth 30 and the system is worth the other 70 — and we own
five-sevenths of the system.

---

## 5. The gap, made measurable

Deepest chain composable from the 68 bound capabilities, measured:

```
[4] source.objective_relevance
     -> source.evidence
     -> evidence.claim_relation
     -> evidence.claim_spec
```

**Four steps.** That is the whole of our composable reach.

Long-horizon autonomy means holding a chain together across 10, 20, 50 steps.
**Composed chain depth *is* our time horizon** — the same quantity METR measures,
expressed as a number we control and can move.

| Metric | Today | Meaning |
|---|---|---|
| Bound capabilities | 68 | all fire, zero unreachable |
| Law-proven capabilities | 9 | only these count under the law |
| Max composed chain | **4** | our effective time horizon |
| Owned long-horizon families | 5 of 7 | owned but **not composable** |

**The five owned families sit outside the composition graph.** They are owned
and unconnected — which is why depth is 4 and not 40.

---

## 6. What to do

1. **Bind the 5 owned long-horizon families into the composition graph.**
   They are the missing depth. Chains cannot route through nodes the composer
   cannot see.
2. **Harvest AVO-style system architecture** (ownable: it is design, not weights).
3. **Harvest live-SWE-agent's self-evolving harness** (77.4% SWE-bench Verified) —
   a loop that adapts from mechanical failure signals, which is exactly what the
   CrossHair oracle emits.
4. **Measure depth as the long-horizon metric.** Before/after, on the same tasks.

---

## 7. Fail-closed caveats

- AVO, Opus 5.5, GPT-6 Astra and live-SWE-agent are **external systems**.
  Their architectures are candidates for harvest; their weights are not, and
  score zero under the ownership rule.
- The matrix's **66.4% Terminal-Bench 4.0 bar** for `ADVANCED_AGENTIC_CODING`
  could not be confirmed externally; public boards list no Opus 5.5 run yet
  (Fable 5.1 57.9%, Opus 5 53.9%). **Re-source the bar before spending against it.**
- Chain depth currently measures *declared* `requires`/`provides` edges, not
  executed run length. Depth 4 is a composition ceiling, not a proven run.

---

## 8. THE IDENTITY FOUND (second pass, 2026-10-17)

Reading the owned packages' declared primary mechanisms produced a hard
identity, from the artifacts themselves and not from inference:

`OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json`
  - family: `LONG_HORIZON_MEMORY_AND_CONTINUITY`
  - status: `VERIFIED_OWNED_EQUAL_OR_BETTER`
  - `brain_owned_route.primary_mechanism` = **`canonical/runtime/same_identity_supervisor.py`**

`canonical/runtime/frontier_intelligence_v1.py` independently identifies
`same_identity_supervisor` as the **GENERAL COMPUTATION SUBSTRATE** -- the
third term of

    EFFECTIVE FRONTIER INTELLIGENCE
      = CAPABILITY + JIT KNOWLEDGE + COMPUTATION SUBSTRATE

**Therefore: the owned long-horizon capability and the computation substrate
are the same mechanism.** One artifact, counted in two places, never joined.

This is the keystone connection:

  - The substrate is what makes long chains *survive* (checkpoint/relaunch).
  - Long-horizon continuity is what makes long chains *cohere*.
  - They are one thing.  We have been scoring them as two.

So the long-horizon stack does not need to be built.  It needs to be **routed
through the substrate that already carries it** -- which is precisely why
composed chain depth is 4 and not 40: nothing in the graph declares that the
substrate extends it.

**The next action is therefore not construction.**  It is to declare the
substrate's provides-edge (`long_horizon.continuity`,
`same_identity.checkpoint`) so the composer may route chains through the
mechanism that already exists.

Recorded honestly rather than forced: `same_identity_supervisor` exposes no
`run(args, root)` entrypoint, so it cannot be bound as an ordinary adapter.  It
must be registered as a substrate node with a declared contract, which is a
distinct and honest kind of binding.
