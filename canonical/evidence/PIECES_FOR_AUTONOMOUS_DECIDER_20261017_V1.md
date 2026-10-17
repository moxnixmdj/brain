# Pieces for a self-directing computer-using intelligence

Goal as stated: *the most powerful intelligence system that uses the computer
and takes the right decisions by itself.*

Method as stated: gather the right pieces, from this repo, other repos, and
research papers.

## Already in this repo (found by capability scan)

| Capability | What it gives |
|---|---|
| `decision.synthesis.typed.stdlib` | synthesise a decision from typed evidence |
| `decision.synthesis.verify.stdlib` | independently verify a decision |
| `plain_goal.bound_capability.grounding.stdlib` | plain goal -> bound capability |
| `terminal.kstar.root.assess.stdlib` | K* root assessment for terminal decisions |
| `web.browser.rendered.capture.chromedriver` | real browser, rendered capture |
| `python.software.repair.loop.test_guided.ast.v1` | closed repair loop |
| `python.patch.search.test_guided.ast.v1` | guided patch search |
| `objective_evidence_unit_extract` | objective-grounded evidence (now working) |
| `knowledge_status_adapter` | verified retrieval provenance (added today) |

The decision layer is not missing. It is unwired from the computer-use layer.

## Piece 1 — the architecture selector (highest value)

Google Research, *Towards a science of scaling agent systems* (2026-01-28).

180 agent configurations. Two findings that matter:

- multi-agent coordination **dramatically improves** parallelizable tasks but
  **degrades** sequential ones;
- they built a **predictive model that identifies the optimal architecture for
  87% of unseen tasks** (R^2 = 0.513), from measurable task properties:
  tool count and decomposability.

Why this is the piece: it is a **procedure that chooses how to think** before
thinking. That is literally "takes the right decisions by itself", and it is
deterministic — tool count and decomposability are countable, not guessed. No
model in the loop.

## Piece 2 — meta-reasoning

*Meta-reasoning in autonomous agents* (2026-03).

Gains scale with task complexity:

    GAIA Level 3 (5+ steps)   +42.1% TCR
    GAIA Level 1              +18.7%
    AgentBench tool-chaining  +38.4%
    AgentBench single-tool    +24.1%

The harder the task, the more it helps. Our target is long-horizon work, which
is exactly where this pays.

## Corroboration that the harness is the lever (third independent source)

Agentick, arXiv 2605.06869 — 27 configurations, 90,000+ episodes:

> "the reasoning harness multiplies LLM performance by 3–10x"

and "no single approach dominates". Best overall score is only 0.309
oracle-normalized — enormous headroom.

This is now measured three separate ways (AVO 30->100, harness 23->52 / 15->36,
harness 3-10x). The brain is a component; the surrounding system is the product.

## Known failure modes to design against

Princeton RSI study of autonomous research agents:

- ended tasks with **under 50% of resources unspent** — no resource awareness;
- given feedback, **added caveats instead of changing strategy**;
- **failed to backtrack**;
- abandoned ambitious targets within the first day.

APB (arXiv 2606.04874), 4,209 cases: systematic weakness in long-horizon
planning, tool-noise robustness, **calibrated refusal**, inference-time
refinement.

Calibrated refusal is notable: your machine already does this (it refuses to
admit a source without coverage). That is the behaviour the field reports as
scarce.

## Computer-use bar to aim at

OSWorld 2.0: 108 long-horizon workflows, median **1.6 hours** human time,
**318 tool calls** each, scored across **27.25 checkpoints**. Top systems
83–86%. OSWorld-Verified (361 desktop tasks) tops at 83–86% and is nearly
saturated; 2.0 is the live target.

## Recommended order

1. Wire the repo's existing decision layer to the browser/terminal layer.
   The parts exist; they are not connected.
2. Harvest the architecture selector. Model-free, measured, and directly on
   target for "decides by itself".
3. Add meta-reasoning; the payoff grows with horizon length.
4. Design explicitly against the four Princeton failure modes.

## Constraint reminder

Only procedures are ownable. Any piece whose ability IS a model call earns
zero credit under our rule. The two pieces above qualify because they are
counting and reasoning procedures, not models.
