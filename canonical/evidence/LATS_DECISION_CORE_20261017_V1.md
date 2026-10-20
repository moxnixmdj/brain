# The decision core: LATS, and why it is ours to own

LATS — Language Agent Tree Search (Zhou et al., ICML 2024, arXiv:2310.04406).
Official code: github.com/lapisrocks/LanguageAgentTreeSearch.

## What it is

A framework that unifies **reasoning, acting and planning** by running Monte
Carlo Tree Search over an agent's actions. Four phases:

1. **Select** — pick the most promising node by upper confidence bound
2. **Expand and simulate** — sample candidate actions, execute them
3. **Evaluate + reflect** — score outcomes; on failure, produce a reflection
   that is fed back into later attempts
4. **Backpropagate** — update scores up the tree

Results: 92.7% pass@1 on HumanEval (GPT-4); 75.9 on WebShop web navigation,
comparable to gradient fine-tuning without any training.

## The part that matters: the search is arithmetic

UCB selection is a formula, not a model:

    UCB(node) = Q(node) + c x sqrt( ln(parent_visits) / node_visits )

Backpropagation is a running average:

    Q(node) <- ( Q(node) * (N(node) - 1) + V ) / N(node)

Selection, expansion bookkeeping, backpropagation, and best-trajectory
extraction are **all deterministic procedures**. They contain no model.

Only two steps in LATS need a model:
- generating candidate actions
- scoring a state

## Why that makes it ownable here

We already own the second one.

| LATS step | Needs | We have |
|---|---|---|
| Select (UCB) | arithmetic | arithmetic |
| Expand | candidate actions | capability candidates from grounding |
| **Evaluate** | a value for a state | **two independent model-free oracles** |
| Reflect | critique | decision.synthesis.* (owned) |
| Backpropagate | arithmetic | arithmetic |

Two oracles already verified at 500/500 with zero model dependency
(CrossHair/SMT and concrete execution) supply the value function. That is
exactly the slot LATS needs filled, and it is the slot where LATS originally
used a model.

So the model-dependent fraction of LATS shrinks to one step: proposing
candidate actions. And candidate actions can come from our own capability
grounding rather than from a model.

## The reflection loop is the second piece

LATS stores reflections from failed trajectories and feeds them into later
attempts. That directly targets three of the four failure modes recorded
earlier from the Princeton RSI study:

- adding caveats instead of changing strategy -> reflection changes the
  next attempt's context, not the wording of the answer
- failing to backtrack -> the search tree keeps alternatives alive with
  visit counts and values
- abandoning ambitious targets -> UCB keeps underexplored branches viable
  rather than committing to the first path

## Companion sources

- `FareedKhan-dev/all-agentic-architectures` — 35 architectures as a runnable
  library: Reflexion, LATS, Self-Consistency, Tree of Thoughts, Corrective
  RAG, Adaptive RAG, GraphRAG, BrowserAgent. A catalog to harvest from.
- `nibzard/awesome-agentic-patterns` — LATS pattern with reference code.
- LangGraph and LlamaIndex both ship maintained LATS implementations.

## Assessment

This is the strongest decision-making candidate found, because it is the one
where the deciding machinery is a formula. We do not need to own a model to
own a search.
