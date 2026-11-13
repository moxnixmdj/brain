# Held out is not in sample: the number the critique was asking for

**2026-11-12 · 8 pull requests the operators were not designed on · no model, no network, $0**

## The critique, and what is right in it

> *What we've built is not a solution to generalization. It is a limited lookup system. Real
> generalization needs model training, conceptual understanding, transfer across domains, and
> reasoning.*

**Right about the main thing.** Every coverage number this project reported until today was
measured on the same fifteen pull requests the operators were chosen on. That is an in-sample
number, and in-sample numbers are not evidence of generalization. This record measures the
operators on a separate set of merged pull requests found by the same kind of title search, with
no change and no tuning.

The result is worse than the in-sample number, and that is the point:

| class | arm | right | developers' changes | coverage | precision | wrong |
|---|---|---:|---:|---:|---:|---:|
| PEP 585 | organ | 64 | 525 | 12.19% | 74.42% | 16 |
| PEP 585 | + family | **197** | 525 | **37.52%** | 76.36% | 52 |
| utc | organ | 35 | 410 | 8.54% | 47.95% | 17 |
| utc | + family | 35 | 410 | 8.54% | 47.95% | 17 |

The in-sample figure for the whole design corpus was **56.87%**, and on its two PEP 585 pull
requests the operator reached **495/500 (99.0%)**. On four pull requests it was not designed on,
the same operator is **37.52%**. The in-sample utc success — `Project-Go-Forward#483`, 150/155 —
did not transfer at all: **8.54%**, and the operator adds nothing.

## What transferred, and what did not

Per pull request:

| pull request | class | base | + family |
|---|---|---:|---:|
| `VHDL/pyVHDLModel#204` | PEP 585 | 23/150 | **108/150** |
| `yaalalabs/agent-kernel#825` | PEP 585 | 31/175 | **79/175** |
| `ncouture/AirTell#200` | PEP 585 + PEP 604 | 0/120 | 0 |
| `agencyenterprise/draft-detective#858` | PEP 585 + PEP 604 | 10/80 | 10 |
| `mozilla/bugbug#7062` | utc | 19/50 | 19 |
| `mozilla/bugbug#7463` | utc | 16/50 | 16 |
| `zkaelxz/U00#1831` | utc helper | 0/95 | 0 |
| `mborchuk/ContaAutonomo#121` | utc helper | 0/215 | 0 |

**PEP 585 transfers partially.** Two projects modernise and the operator follows them
(`pyVHDLModel` 108/150, `agent-kernel` 79/175); two mix the change with PEP 604 unions or carry
an import-only example, and the operator cannot read the direction from them.

**The utc class does not transfer, and the reason is the interesting part.** The two successful
in-sample files changed `datetime.utcnow()` to `datetime.now(UTC)`. The held-out projects do not
do that:

```python
created_at = db.Column(db.DateTime, default=utcnow)      # from timeutil import utcnow
first_seen = clock.utcnow().isoformat()                  # from lib import clock
```

They replace the deprecated call with **a project-local clock helper**. What our operator learned
was the *syntax* of one replacement, not the *concept* "stop using a naive UTC clock." That is
exactly the conceptual understanding the critique says is missing. The measurement now says it,
with numbers, instead of leaving it as an opinion.

## The four requirements, taken one at a time

**1. Actual model training.** The strongest way to get a broad prior, and the one this project
does not use: the standing constraints are $0 spend and zero model dependency in result-bearing
paths. Training or fine-tuning is therefore **blocked by a decision, not by an unknown**. If the
owner authorises compute and spend, the path is concrete: fine-tune on example → verified edit
traces, with the project's tests as the oracle, and evaluate on held-out pull requests like these.
The 2026 evidence says this is the strongest lever (GEN-1.5: one demo 59%, ten gradient steps
83%; Continual-ARC: weight training is the only family that gains on unseen tasks).

**2. Conceptual understanding.** Operationalised honestly, this is *does the learned thing apply
when the surface form changes*. The utc result says no: the operator captured a spelling, not a
concept. A model with broad code priors, or a semantic layer that maps a helper to its role, is
what would close this. Hand-written operators will not, one at a time.

**3. Transfer across domains.** Measured above. PEP 585 transfers at 37.52% to four unseen
projects; utc at 8.54%. The operator is not a lookup table — it changes code by structure, and
it changes files it never saw — but its transfer is narrow and class-specific.

**4. Reasoning.** Not measurable in this corpus. The only proxy available is verification: a
change is right when the project's tests pass, not when it resembles the example. No project's
tests were run here, so every precision number in this record is *agreement with developers*,
not correctness.

## What the critique gets wrong

Model training is not the only thing that generalises. A constrained operator chosen by an
example and applied by structure is a real generalisation mechanism — it produced 197 correct
changes on code it had never seen, which a lookup table cannot do. But the critique is right that
it is **narrow**: the operator generalises inside a family someone wrote down, not across
concepts. Calling it "the solution to generalization" would be false; calling it a lookup system
would also be false. It is a **small, typed inductive bias with a measured transfer rate**.

## The limiting factors, in order

1. **Evaluation bias.** The project kept measuring on its design corpus. This is now fixed by
   this instrument; future claims must carry a held-out number.
2. **No learned prior.** Hand-written operators cover classes someone anticipated. The utc
   failure is the price. Weight training is the known fix and is blocked by the spend/model
   constraint.
3. **No verification at scale.** Preference without tests: precision is agreement, not
   correctness. The training path needs tests as its reward signal, and so does the operator
   path.
4. **Class heterogeneity.** Real pull requests mix PEP 585 with PEP 604, import-only examples,
   and helper introductions. One example cannot represent a multi-topic change; this is a
   property of the data, not only of the learner.
5. **Sample size.** Eight pull requests is a pilot, not a benchmark. It is enough to falsify the
   in-sample claim; it is not enough to rank methods.

## The fastest real path

1. **Held-out first.** Every future operator ships with a held-out number on pull requests it was
   not chosen on. In-sample numbers stay, labelled as in-sample.
2. **Build the verified-traces dataset now**, with or without training: example pair → the edit
   the system proposes → the project's tests pass/fail. This is the asset every route needs, and
   the tree already produces most of it.
3. **If compute is authorised, fine-tune** a code model on those traces and evaluate on held-out
   pull requests. That is the only route that addresses the utc failure — a concept, not a
   spelling.
4. **Keep operators only where a mechanical check exists**, and stop adding them where the
   held-out rate is zero.
5. **Sentience is not advanced by any of this.** There is no self-model, no experience, no goal
   in these modules. The goal of a sentient creature needs a different programme; nothing here
   should be described as one.

## Reproduce

```bash
python3 canonical/tools/held_out_transfer_20261112_v1.py \
  --collect /tmp/heldout.json \
  --record canonical/verification/HELD_OUT_TRANSFER_PRS_20261112_V1.json
python3 canonical/tools/held_out_transfer_20261112_v1.py \
  --pulls /tmp/heldout.json --json /tmp/heldout_measure.json
python3 -m unittest canonical.tests.test_held_out_transfer_v1
```

The record holds the eight pull requests without their texts, with a hash for every file, so
anyone can fetch the same files again and check them. The title searches are in the tool; the
fifteen design pull requests are excluded by name. The measurement is a sandbox measurement, not
a receipt. `truth.achieved` stays false.

## Limits

* Eight merged pull requests, two per query, found by title search: a pilot, not a benchmark.
* The titles are noisy: PEP 604 unions and project-local helpers are in the sample and outside
  the operator.
* No project's tests were run; precision is agreement with the developers.
* The operator's family was chosen on the earlier corpus; this measures transfer of that choice,
  not of a model trained from scratch.
