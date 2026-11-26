# Play 1 — route by contract. Killed by its own ablation, in one run.

**Date:** 2026-11-26 · **Cost:** 22 s, 0 model calls, 0 network calls, 845-module pool
**Artifact:** `canonical/verification/PLAY_1_ROUTE_BY_CONTRACT_20261126_V1.json`
**Instrument:** `canonical/tools/contract_first_routing_v1.py` · **Tests:** `canonical/tests/test_contract_first_routing_v1.py`

## The frontier failure this was aimed at

Frontier agents route by picking a tool description out of a large catalogue. On 3,616 MCP
tools the best published hybrid retriever reports 98.2 % Recall@15 — but the same route
falls to 83.1 % dense-only, and an independent review found the ground truth was the
gateway's own recommendation (label circularity). Our own version of the problem was
measured last round: over the atlas's 1,260 domain candidates the source index reaches a
module of the right *function* at 0.76 mean recall@5, while `route()` — the channel
`solve()` uses — reaches 0.33, and 0.00 for instant learning and world model.

The reading was: the router is broken. Play 1 tested that reading.

## The unusual move

Stop scoring text. Read each module's **contract** from its own AST: the leading verb of
every public callable (`expire_rule` → `expire`), what those callables act on (`rule`), and
the exception messages they raise as stated refusals. Then admit a module only if it shares
a **verb** with the request, or at least two objects. Topic overlap alone is refused — the
one thing a bag-of-words ranker structurally cannot do.

## Kill criterion, fixed before the run

Mean recall@5 below 0.53 (the incumbent's 0.33 + twenty points), **or** a topic-only bag of
words over the same pool doing at least as well, **or** less than twenty points over the
topic-sharing chance baseline.

## Measured

| quantity | value |
|---|---:|
| pool (modules the atlas classifies into a domain) | 845 |
| queries (the same 42, frontier and repository phrasing) | 42 |
| **contract recall@5** | **0.905** |
| contract recall@1 | 0.548 |
| incumbent `find_source` recall@5, same queries, same top-5 | 0.667 |
| **topic-only ablation recall@5** (gate removed, verbs ignored) | **0.952** |
| topic-only ablation recall@1 | 0.476 |
| **chance: random 5 from the topic-sharing sub-pool** | **0.846** |
| chance: random 5 from all 845 | 0.006 |
| contract recall@5 on entries the runtime can execute | 0.000 |

Per domain, contract recall@5: instant_learning 1.00, memory 1.00, computer_use 1.00,
coding_agents 1.00, verification_abstention 1.00, world_model 0.83, continual_learning 0.50.

## Verdict: KILLED

Not on the pre-registered 0.53 floor — 0.905 clears it — but on the two clauses the first
run made necessary:

1. **The ablation beats the mechanism.** A pure bag of words, with the contract gate removed
   and verbs ignored, scores 0.952 against the contract router's 0.905. Whatever the gate
   contributes at rank 5 is negative.
2. **The metric saturates.** A *random* five drawn from the modules that share any query word
   already lands in the right domain 84.6 % of the time. 0.905 is +0.06 over a coin-like
   baseline, inside the noise of 42 queries.

The one thing that survived: at rank 1 the contract gate scores 0.548 against the ablation's
0.476, a seven-point gain — precision at one, not recall at five. That is a lead, not a
result, and 42 queries cannot carry it.

## What this actually found

The number that mattered was not the router's. The ground truth is built from the same
vocabulary as the pool: a module is "in the memory domain" because its name and docstring use
the memory words. Any ranker that draws from that pool inherits the label. So domain-level
recall cannot discriminate between routers at all — it is measuring the label's coherence, and
the label is coherent.

Which means the previous round's headline — "routing is the wall, 0.33" — was measured against
a chance baseline of 0.013–0.143 over a *different* pool (449 capabilities). The two numbers
are not comparable, and neither is a routing measurement. **Recalibrated claim: routing is not
yet measured. The label is the bottleneck.**

## First measurable step of the next play (replacing this one)

Exact targets, derived without a human: for every receipt in the tree that records an action
and the module that served it, the pair is a labelled instance. Build recall@1 over *those*
pairs — target is one module, chance is 1/845 — and re-run the contract router unchanged. If
it does not beat topic-only on exact targets, the contract idea is dead; if it does, the
domain atlas was never the right scoreboard.

**No number here was borrowed.** Every value is a row in the artifact named above, produced by
the instrument named above on this tree, by local code with no model calls and no network.
Independent reproduction is open; producer-run only.
