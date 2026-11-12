# The corpus can only come from real work

**2026-11-12.** Base `e88e9c00`. Branch `arena/0087950f-brain`. Round 20.

Round 19 gave every receipt its inputs and left the corpus at zero, because the history has none. The
obvious way to seed it is the documents the repository already ships: run each capability that takes a
file input against a fixture, keep the ones that succeed. This round did exactly that, on all 145
curated capabilities.

```
registry capabilities                           145
  declare at least one input                    126
  take a file input                              56
fixture documents available                      10
documents tried per capability                    6

ran to a success status                           0
no valid instance found                          54
no adapter module                                 2
```

**Zero, out of 56.** Every file-input capability in this tree was handed every document the tree
ships, six attempts each, five-second budget, output redirected to a temporary directory. Not one
reached a success status.

## Why the zero is not a bug in the probe

Because it reproduces what the earlier rounds kept rediscovering from the other side. The failures are
specific and they are about environment, not about the document:

```
auto.npm.dfinity-cbor      NODE_CODEC_PACKAGE_ROOT_REQUIRED
auto.pypi.bson-modern      PYTHON_CODEC_CONTRACT_INCOMPLETE
archive.tar_gz.create_...  MANIFEST_INPUT_REQUIRED
python.issue...parse...    ISSUE_SCHEMA_MISSING:issue_id
```

A capability is not a function of one file. It is a function of a document **and** the packages,
roots, contracts and sibling artifacts of the environment it was built for. A fixture borrowed from
another corner of the tree supplies the first and none of the rest.

## What that means for the question, stated flatly

> *Give it a try in all those new environments, once each, and it keeps them.*

The corpus entry for a try is **the inputs of a real task**. This repository has:

* 532 receipts and one recorded argument (round 19),
* 56 capabilities that want a file and zero documents that satisfy any of them (this round),
* 296 independently verified executions, all of them zero-argument module runs (round 17).

So the corpus is not thin, and it is not mis-measured. It is **empty by construction**, because the
system has never taken a real task's inputs and kept them. Environments cannot fix that: an
environment is a place to run, not an instance to learn from. Demonstrations cannot fix it either, for
the reason round 13 measured — a demonstration without an input space is a constant.

**The only thing that fills the corpus is doing work with a verifier attached.** Two thousand
instances means two thousand real executions. That is the honest price, it is the same price the 2026
record pays (a 200-instance stream, one pass each), and it is the first time this project has been
able to state it as a number rather than a metaphor.

## What is already in place to collect it

| piece | state |
|---|---|
| take a real invocation's inputs | shipped round 19 (`snapshot_inputs`, content-addressed) |
| vary them deterministically | shipped round 18 (`--instance-index`) |
| have a second party confirm the result | shipped and running (296 OIDC reproductions) |
| refuse an update that does not improve | shipped round 11 and the registry predicates |
| **actually run real tasks** | **not shipped — this is the missing piece, and only work supplies it** |

Four of the five are code. The fifth is a workload, and no amount of engineering substitutes for it.

## The one thing to do next

Stop generating instruments. Run the tree's own capabilities on its own real work — the repository
has thousands of real files, real diffs and real failing checks — and let `input_digests` do the
collecting. Every merged PR is a handful of real instances. The number that matters now is not how
many capabilities exist, not how many environments were tried, but **how many real executions the
system has recorded with their inputs, their outputs and a second party's confirmation.** That number
is zero today and it is the only honest measure of progress left.

## Receipts

```
python3 fixtures_cannot_seed_the_corpus_probe_20261112.py
python3 -m pytest -q canonical/tests/test_fixtures_cannot_seed_the_corpus_v1.py     5 passed
```

## Non-claims

This is a seeding experiment, not a capability measurement: it says nothing about whether these
capabilities work in their intended environments, only that borrowed fixtures do not constitute one.
The probe writes nothing into the tree and touches no registry. `truth.achieved` false, $0, zero model
dependency.
