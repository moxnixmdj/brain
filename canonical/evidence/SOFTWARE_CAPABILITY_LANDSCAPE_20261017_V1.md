# Software capability landscape — 2026-10-17

Inventory of what we hold, what exists outside, and how each maps onto the
Theory. Sourced from the repo and the open internet.

## The Theory (recap)

```
EFFECTIVE FRONTIER INTELLIGENCE
  = BRAIN-OWNED CAPABILITY MECHANISMS   <- owned. never outsourced.
  + EXTERNAL JIT KNOWLEDGE              <- content only. fetch, use, destroy.
  + GENERAL COMPUTATION SUBSTRATE       <- checkpoint, survive, resume.
```

Credit rule: a tool whose capability IS a model call earns **zero**. Only the
mechanism we own counts.

## What we already hold (repo)

| Artifact | Class under Theory |
|---|---|
| `mini_swe_agent_2_4_6`, `mini_swe_agent_04d809c` | SUBSTRATE (harness runtime) |
| `superpowers_6_4_2` (skills) | CAPABILITY (methodology, owned config) |
| `supreme_c062bec` (SKILL.md) | CAPABILITY (methodology) |
| `mini_swe_superpowers_v1` (composed) | CAPABILITY — the owned composition |
| `python_contract_mutation_gen_v1` | CAPABILITY — deterministic generator |
| `crosshair_contract_oracle` (SMT/Z3) | CAPABILITY — oracle 1, model-free |
| `concrete_execution_oracle` | CAPABILITY — oracle 2, model-free |
| `same_identity_supervisor` | SUBSTRATE (identity/continuity) |
| `theory_runtime_v1` | the loop that binds all three terms |

## External candidates

| Candidate | Headline | Ownable? |
|---|---|---|
| **retro-harness (RHO)** | self-supervised harness evolution, **59% → 78% SWE-Bench Pro in one round, no labels** | **YES — top target** |
| live-SWE-agent | 77.4% SWE-bench Verified, self-evolving scaffold | YES (scaffold, not model) |
| NOOA (NVIDIA) | 82.2% at half the tokens; tool results **pass by reference**, no context compaction | YES — architecture is ownable |
| Confucius Code Agent | 59% Resolve@1 SWE-Bench-Pro; persistent cross-session notes | YES (meta-agent, memory) |
| OpenHands | MIT, ~44k stars, reference scaffold | YES |
| SWE-agent | MIT, Princeton/Stanford, the ACI reference | YES |
| Qwen3-Coder-Next / DeepSWE / open models | 40–70% Verified | **NO — capability IS the model** |
| SWE-bench / task corpora | datasets | NO — this is JIT KNOWLEDGE, not capability |

## The finding that keeps replicating

Harness choice dominates model choice, and it is now measured four independent
ways:

| Evidence | Same model, different harness |
|---|---|
| NVIDIA AVO (ARC-AGI-3) | Opus 5: **30% → 100%**, identical weights |
| Vals AI (TB4, mini-swe) | Opus 5.5 65.15% vs Sonnet 5.5 64.14% — **1.01 pts apart** |
| Claw-SWE-Bench | GLM 5.1: **19.1% → 73.4%** on adapter design alone |
| AINews / SWE-bench Pro | GLM-5.2 **23% → 52%**; Gemma 4 26B **15% → 36%** |

Model identity: ~1 point. Harness: 30–50 points.

RHO is the sharpest form of this because it needs **no ground-truth labels** —
it improves the harness from the agent's own trajectories via self-validation,
self-consistency, and pairwise self-preference. That is a procedure, not a
model call, which is exactly what our credit rule rewards.

## Why SWE-bench Verified is no longer the bar

Saturated as of 2026-09-01: Opus 5 (mini-SWE) **97.00%**, DeepSeek V4 Pro
**96.40%**, GPT-5.6 Sol **96.20%**. Nothing discriminates there. SWE-bench
**Pro** is the live frontier (best external ~78%).

## Next acquisition

**retro-harness (RHO).** It is the only candidate that (a) is a procedure
rather than a model, (b) needs no labelled data we would have to license or
fetch, and (c) has a measured double-digit effect. Harvest order per the
canon: reuse → substitute → compose → configure → verify.

## Sources

- awesome-harness-engineering (ai-boost), 2026-10-14 — RHO, live-SWE-agent, CCA
- NVIDIA, "Six Agent Harness Capabilities", 2026-08-20 — NOOA 82.2%, by-reference
- Vals AI SWE-bench Verified, 2026-09-01 — saturation
- Claw-SWE-Bench arXiv 2606.12344 — adapter design 19.1% → 73.4%
- AINews via best-of-Agent-Harnesses — 23→52, 15→36
- arxiv 2604.26275 — SWE-bench Verified 1.96% → 78.4% (Oct 2023 → Apr 2026)
