# Pre-registration — a vocabulary that grows, and a creature with a lifetime

**2026-11-04 · round 12 · before implementation · authority NONE**

## What eleven rounds got wrong, stated as a measurement

**M1 — the creature can write `x % 2` and cannot think "period 2".** Both are true right now:

```
mod 2 as STRINGS : PROVISIONAL  — 75 programs, one of them `((x / 1) % 2)`
mod 2 as CLASSES : ONTOLOGY_EXHAUSTED
```

`%` is in the operator inventory. "Remainder" is not in the hypothesis inventory. The two
vocabularies are **disjoint**, and every improvement in eleven rounds has been to make the reasoning
*about* the string inventory more careful — never to reconcile it with the class inventory.

**M2 — a new hypothesis kind enters the ontology only when I type a Python class.** The ontology is
`FAMILIES = {Affine, Power, Constant}`. Adding a fourth kind is a code edit by me. So the "creature"
is a fixed toolkit with increasingly good bookkeeping: exactly the static code the user keeps naming.
Everything about *primitive selection* is mine, permanently, and no amount of epistemics can move it.

**M3 — nothing persists.** A refutation is discarded when the call returns; the same question returns
the same verdict forever. `mod 2` was declared `ONTOLOGY_EXHAUSTED` twice, identically, with no record
of having been asked before. A statement whose truth cannot change under any experience is not a
belief, it is a constant.

**M4 — the failure is invisible downstream.** `demand_evidence` reports `PROVISIONAL` on `mod 2`; the
ontology reports exhausted; neither knows about the other. They have never disagreed in public
because they have never spoken.

## The response

Turn the ending of round 11 into a test. Round 11 wrote: *"`mod 2` remains unexplained by everything
in this repository; next round should make it the target."* A static toolkit cannot make a function
its target and come back with a new primitive. If rounds 7–11 were real capability rather than
scaffolding, they must be enough.

**A kind is recovered from evidence at run time, and enters the ontology by induction.** Specifically:
when the string sweep overflows, the survivors are MINE — they fit — so their free vocabulary is
evidence about which operators the target actually uses. Factor that vocabulary out, regenerate
candidates, test them for consistency, and admit the ones that survive. `mod 2` should yield
`{%, /, 1, 2}` and hence `x % 2`.

The induced hypothesis is then **named from its own incidence structure** (`period 2`, `in steps of
2`), not matched against a word I supplied. That is the whole claim: the label comes from the data
the hypothesis fits, so a kind becomes speakable without being hard-coded.

And a **persistent ontology** so the outcome is not discarded: what survives induction is kept, what
is refuted is recorded, and a second encounter is answered from memory rather than re-derived.

## Predictions

| id | prediction | how scored |
|---|---|---|
| **S1** | On `mod 2`, the surviving admissible programs share a restricted operator vocabulary, and `%` is in it while `+`/`-` are not. | the recovered set |
| **S2** | Regenerating candidates from that vocabulary yields a **periodic** hypothesis that reproduces all six observations exactly. | reproduction, no tolerance |
| **S3** | The periodic hypothesis is **named from its own parameters** (`period=2`, `remainder`) with no supplied label, and the name changes when the data do. | name for period-2 vs period-3 data |
| **S4** | Nothing about the recovery is specific to modulo: the same pathway over `x*x`-style data recovers `{*, 2}` rather than `{%}`. | recovered sets differ per target |
| **S5** | With a persistent ontology, `mod 2` is `ONTOLOGY_EXHAUSTED` on first encounter and **`DETERMINED` on the second**, from what was kept — with no new code run in between. | status pair, one process |
| **S6** | The kept record includes the refutations, so the second encounter can say *what was already ruled out* rather than re-testing from nothing. | `refuted` list non-empty and reused |
| **S7** | **The honest negative:** the same pathway does NOT invent a kind for data that has no structure — random-looking observations must still come back exhausted, not fitted. | still exhausted |
| **S8** | The mechanism agrees with its own epistemics: `demand_evidence` on the induced body reports one explanation, and the composed/string/class layers stop contradicting each other on this input. | counts agree |

S4 and S7 are the ones that stop this being "special-case modulo". A pathway that only works on the
example I built it for has learned nothing, and S7 is the prediction that must hold against the obvious
temptation to fit whatever it is given.

## Stop condition

If S1 fails — the survivors' vocabulary is not restricted enough to be evidence — then the induction
happens at the model level, not the data level, and it would work on any target I chose. That would
make S2 and S3 worthless, and I will report them as worthless rather than as a success.
