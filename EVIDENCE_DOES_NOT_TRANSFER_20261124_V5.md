# EVIDENCE DOES NOT TRANSFER — a hypothesis tested on 72 ordered pairs and refuted
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Binding requirements restated: own model, zero runtime model calls; no parameter may warehouse
> world facts; every parameter derived and justified; knowledge outside the weights and removable
> without retraining; project before web; real limiting factor named; ideas killed before building;
> honest verified / unverified / failed; hardest real tests; never ask the user.
> §2 stays resolved as before. This round made no model call and stored no parameter.

---

## 1. The hypothesis, stated so it could fail

Last round ended on the one step that could plausibly move reach by an order of magnitude rather than
by one: *evidence should be inherited, not rediscovered.*

A confirmed law does not establish a fact about one atom. It establishes that a **projection** is
sufficient. If `IDENT` determines the effect of four atoms, then a fifth atom's single witness is no
longer standing alone.

```
H1: a projection confirmed by >= 2 distinct atoms licenses single-witness laws over it (within a machine)
H2: a projection confirmed on machine X licenses single-witness laws on machine Y (across machines)
```

H2 is the version that matters. If it holds, confirmation is paid once and a store of laws compounds.

## 2. H1 — sound, and buys nothing

Nine machines, depth 3, stable split:

| arm | predictions | wrong | refused | laws admitted |
|---|---|---|---|---|
| A — per-atom support ≥ 2 | 11 | 0 | 84 | 32 |
| B — A + inherited within the machine | **11** | **0** | 84 | 46 |
| C — inheritance only from a matched effect | 11 | 0 | 84 | 34 |
| D — inheritance after a single confirming atom | 22 | **11** | 73 | 246 |

Inheritance added **14 laws and zero predictions**. Every inherited law refused on every held-out
state it was asked about — because it is a single-witness law over a wide projection, and the held-out
states lie outside the narrow slice the projection reaches. Sound, and worth nothing.

Arm D is the tell: drop the requirement to *one* confirming atom and reach doubles (11 → 22) while
carrying **11 wrong out of 22**. The confirmation requirement is doing real work, and what it buys is
silence.

## 3. H2 — refuted, cleanly

72 ordered machine pairs, each student scored on its own held-out split:

| | predictions | wrong |
|---|---|---|
| own laws only | 88 | 0 |
| **+ laws inherited from another machine** | **149** | **56** |

Reach rose in 11 pairs. **Errors rose in exactly the same 11 pairs.** Cross-machine inheritance
injects a 38% error rate for a 69% reach increase, and the errors are not incidental — they are the
same events.

**Verdict: `cross_machine_inheritance_is_sound` = false.** A projection confirmed on one machine is
not evidence about another. The nine machines in this tree share a vocabulary of relations and do not
share a semantics, and the difference is exactly what the transfer destroys.

## 4. Why this is a result and not a failure

Three rounds have now produced one sound mechanism and three refuted ones, each refuted by
measurement rather than by argument:

| hypothesis | outcome |
|---|---|
| aliased vocabulary | **refuted** — 0 aliases, signatures == states, extension needed 0 times |
| minimal descriptors generalise | **refuted** — 10,050 → 210 literals, 29/30 held-out wrong |
| asking is the missing term | **refuted as a learner**, kept as a query policy (3.5× random) |
| projections give width | **confirmed at support ≥ 2** — 11 predictions, 0 wrong |
| evidence transfers between machines | **refuted** — 149 predictions, 56 wrong |

That is five hypotheses, five measurements, and the first durable positive: a law with two independent
witnesses over a vocabulary projection is right every time it speaks on held-out states. The refutations
are what make that positive trustworthy — they are the same instrument, the same split and the same
discipline applied to claims that flattered the design.

## 5. What the refutation implies about the architecture

The tree's §9 vision is *one store, compressing goal-driven experience into shared abstractions, so
that knowledge transfers between environments.* H2 is the minimal test of that vision, and it fails.
The reason is visible in the numbers: a projection like `CARD` confirmed on FILESYSTEM states nothing
about GIT, because in GIT branch identity and cardinality are conflated — the exact defect that made
GIT's two laws 4-for-4 wrong three rounds ago.

So the honest reading is not "transfer is impossible", it is **transfer requires the projection to be
confirmed per semantics, not per syntax**. A shared vocabulary is necessary and nowhere near
sufficient. The store can hold laws; it cannot yet hold *why* a law is valid, and without that, the
next machine re-derives everything.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0
```

42 tests green across six suites touching this machinery. Repo integrity guard PASS, 17 rules, 0
violations. Pushed to `arena/50c05c04-brain`.

## 7. Next bottleneck

Reach remains the wall — 11 sound held-out predictions across 9 machines — and this round removed the
last cheap hope of multiplying it. What is left is the question §5 names: **a law that carries not
only its projection but the reason it holds**, so that validity can be re-established cheaply on a new
environment instead of transferred blindly or rediscovered from scratch.

Concretely testable next step: state each law with the **contrast set** that justified it — the
specific observed contexts the projection had to separate — and on a new machine, check whether the
contrast set is satisfiable before admitting the law. If the contrast cannot be reproduced, the law is
not transferred; it is a claim to be re-tested. That converts blind transfer into a cheap verification,
and the cost is the one number this tree keeps paying for: honesty over reach.
