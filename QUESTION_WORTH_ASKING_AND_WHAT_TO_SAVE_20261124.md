# The Question Worth Asking — what is saved, and what is generalized

Date 2026-11-24. Branch `arena/39d26eb4-brain`. This answers the question the
mission actually asks, in three parts, and separates what was measured from what
was assumed.

---

## 1. The question, stated exactly

The user's question is not "build an agent". It is narrower and harder:

> After scanning an environment and fetching what is unknown, **what exactly
> should be saved, and what should be generalized?** The actions will never recur
> because environments keep changing, so saving the experience dumbly saves
> nothing.

That is a question about the **write** side of learning, and it has a precise
form. Given observations of an unseen environment:

1. What machine explains them?
2. Is that machine *forced* by the evidence, or one of many?
3. If many, what single experiment removes the most of the others?
4. When no experiment remains, what may be written down as permanent?

The project could already answer (3) for *code* (`evidence_demand_v1`:
`what_would_settle_it`) and could refute two candidate models when handed a trace
space (`consistency_vs_equivalence_v1`). It could not answer (1), (2) or (4) for
an arbitrary environment, and `right_question` in the Perfect Algorithm orders by
novelty and closeness — a heuristic that does not know what its uncertainty is
about.

## 2. What is saved (measured)

**Not the trajectory.** A trace is one path through a machine; the machine is the
closure of every path. Saving the path is what the user called "dumb". Saving the
machine is what makes one experience worth more than itself.

The saved row is:

| field | what it is | why it is not a trajectory |
|---|---|---|
| `machine` | deterministic Moore machine: states as integers, actions abstracted to first-use order | the same behaviour under different action names is **one** row (measured: digest equal for `tick` vs `turn`) |
| `vocabulary` | observed action name → canonical name | keeps the abstract row *probeable* in a new app |
| `unavailable` | actions known NOT to exist in a state | knowledge, not silence: "may I confirm now?" is answered, not guessed |
| `rivals_remaining` | how many competing machines this experience did not rule out | a row with rivals > 0 is labelled HYPOTHESIS, not promoted by being stored |
| `claim` | `SMALLEST_MACHINE_CONSISTENT_WITH_THESE_OBSERVATIONS` or the weaker form | minimality is claimed only when it was *proved* |
| `not_claimed` | `THE_MACHINE` | always present |

Transfer, measured end-to-end: 6 observations in app A (action `tick`) →
8 unseen observations in app B (action `turn`, deeper steps) → `ADMIT`.

## 3. The missing observable, measured on a real failure

The bottleneck document says: *"3 pages stop because the same look behaves
differently; that is a missing observable."* That is now a runnable app: a
three-step form whose step 1 and step 2 render an identical DOM.

```
DOM-keyed scan   12,832 probes, 4,000 nodes expanded, goal NOT reached
                 2,573 distinct search nodes share one DOM digest
                 -> not slow. Cannot terminate. It cannot tell "clicked once"
                    from "clicked twice".
Probe learner    9 probes -> 3-state machine, PROVED_MINIMAL
                 plan next,next,confirm -> executed on the real app -> submitted
```

**Availability is the observable.** An action that cannot be taken is a fact about
the state, and it is the strongest kind, because it is precisely what the DOM
omits. It is also free: it is the exception a probe already raises.

## 4. What may be written permanently

Nothing by this module. `admit_learnable_unit` returns a verdict and writes no
row, keeping the existing authority boundary intact. A unit admits only when:

* `PREDICTED` — it explains every observation it was built from;
* `GENERALISED` — the **whole** held-out set is predicted correctly (checking
  per-observation allowed one hit among many undefined probes to read as success);
* `NO_HARM` — nothing held-out is contradicted.

Otherwise it refuses and names which of the three failed, separately, because they
fail separately.

## 5. Honest limits, stated in the code

* **Minimality is not identification.** The module reports
  `SMALLEST_MACHINE_CONSISTENT_WITH_THESE_OBSERVATIONS` and always
  `not_claimed: THE_MACHINE`. Two different machines can explain the same
  evidence; measured example: `+1` and `+2` dials over 3 states are *not*
  separable by observation, and the module says so (`separating_word → None`)
  rather than calling them equal.
* **Exhaustive above 11 tree nodes refuses.** No SAT solver here, so no
  minimality claim is made above the limit — `UNREFINED__EXHAUSTIVE_LIMIT`, with
  the limit named. The 2026 literature (L#_□, CAV 2026) solves this with SMT; that
  is the honest route to raising it, and it is not built.
* **Access words must be observed roads.** An observation whose access word uses
  an action never seen to be available is refused
  (`REFUSED__ACCESS_USES_UNOBSERVED_ACTION`) because the machine could not be
  replayed against it.
* **Probing must restore.** A probe that mutates the app and is not restored is
  answering a different question. One earlier result in this session ("2 states
  from 4 probes") was an artefact of exactly that and was withdrawn.

## 6. Does asking better questions pay? Measured, modestly

On 12 random 3-state environments with a 16-probe budget, using the true machine
as the rival (the most favourable case for the strategy):

```
separating questions  solved 6/12
novelty-first order   solved 5/12
on the solved ones, median probes 16 -> 11
```

Real, modest, and not a triumph. The module does not claim more. The larger effect
is structural rather than statistical: the machine is vocabulary-independent, so
one experience transfers where a trace cannot.

## 7. What this does NOT establish

The mission's done-criteria are untouched. This work does not run SWE-bench Pro,
Terminal-Bench or OSWorld 2.0, and no number here is a benchmark score. The
environment is an in-memory app, not a browser over CDP — the adapter accepts the
real CDP snapshot shape, and wiring it to a live VM is unstarted because the
sandbox has no container runtime.

The bottleneck identified by the project is unchanged: **the verifier**. This
module improves *what is stored* and *how the next question is chosen*. It does
not make the verifier able to decide whether an arbitrary real-world attempt
succeeded, and that remains the term that multiplies everything else.
