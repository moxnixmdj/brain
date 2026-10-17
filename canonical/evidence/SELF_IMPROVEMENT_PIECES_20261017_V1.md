# The pieces for a system that improves itself

Search target: what exists for a machine that uses a computer, decides for
itself, and gets better on its own — restricted to what we can OWN.

## The one that matches our architecture exactly

**Self-Evolving Agent Harnesses via Gated Semantic Quality-Diversity**
(HarnessBank, arXiv:2607.13683)

> "a self-evolving agent-harness framework that **separates proposing changes
> from crediting them**: a language model diagnoses failures and proposes
> patches, while **all sampling, measurement, and significance testing are
> owned by deterministic code**, so every credited improvement is trustworthy
> by construction"

Their gates:

- **validity gate** — re-runs to exclude infrastructure failures
- **activation gate** — confirms the patch actually fired
- **paired-2σ significance test** on a **sealed test withheld from all
  decisions**

That is precisely the split we arrived at independently, and it is the split
our ownership rule demands: the model may *suggest*, only deterministic code
may *credit*. Every credited gain is trustworthy by construction rather than
by assertion.

## The strongest measured results

| Piece | Result | Source |
|---|---|---|
| Self-Harness | 40.5→61.9%, 23.8→38.1%, 42.9→57.1% across three models | arXiv:2606.09498 |
| Prime Agent | ARC-AGI-3 **30% → 95.5%** | arXiv:2608.23552 |
| Life-Harness | improves **116 of 126** model–environment settings, +88.5% avg | arXiv:2605.22166 |
| RRSI | up to +6.0 pts, **30% fewer tokens** | arXiv:2609.24972 |

Self-Harness notes its failure clustering is *"deterministic and
evaluator-grounded"* — cases group only when they agree on what the verifier
rejected, how behaviour contributed, and which mechanism was involved. That
is a procedure, not a judgement call.

Prime Agent is open source: github.com/PrimeIntellect-ai/prime-agent.
RRSI is open source: github.com/google-research/rrsi.

## The theory that bounds all of it

**The Self-Improvement Problem** (arXiv:2610.21646) formalises
verification-gated self-improvement and proves a sharp limit:

> "no terminating procedure can simultaneously guarantee reliability (never
> accepting a non-improvement) and non-conservatism (never missing an
> available improvement)"

They then identify the regime where it *is* achievable: bounded evaluation
plus a finite proposal budget, under which exhaustive simulation gives a
terminating procedure with the guarantees.

We should adopt those bounds deliberately. They are not a limitation to
discover later; they are the design envelope.

## Plan–Execute–Verify

**Code as Agent Harness** (arXiv:2605.18747) formalises PEV: plans form
contracts over intended changes, execution applies them in a sandboxed
permissioned environment, and verification uses **deterministic sensors** to
accept, revise, escalate or roll back.

## Why these qualify and others do not

Every piece above keeps the *crediting* deterministic. That is the whole test.
A method that asks a model whether it improved earns zero under our rule; a
method that asks deterministic code to decide, with a sealed test, earns full
credit.

## Recommendation

Harvest in this order:

1. **HarnessBank's gating triad** — validity, activation, paired-2σ on a
   sealed test. Small, pure code, directly ownable, and it is the thing that
   makes every later gain trustworthy.
2. **Self-Harness's weakness mining** — deterministic, evaluator-grounded
   clustering of failures.
3. **Prime Agent** for the execution substrate — persistent REPL, recursive
   subagents, retained skills. Open source.

Adopt the Self-Improvement Problem's bounds at the same time.
