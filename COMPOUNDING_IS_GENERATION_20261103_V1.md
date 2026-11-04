# Compounding is generation, not selection — and this repository already has the right organ

**2026-11-03**, on `d24db24`. Third answer to the same question, and the first one that is not
"no". Measured, with two instruments that caught three of my own errors before they became
findings.

## 1. Why my last two answers were both "no", in one sentence

| attempt | what it did | measured |
|---|---|---|
| transition model across kinds | selected among remembered **facts** | NO — 10/10 identical cost |
| learning to choose a search policy | selected among five fixed **procedures** | NO — 3/10 vs a coin flip |
| **inventing a concept** | **added an option** | **YES** |

The first two are the same move: **pick better among a fixed set.** No amount of learning makes a
better choice than the best member of that set, and no fixed set reaches a problem outside it.
The third move is different in kind: it **grows the set**. Measured on held-out problems that
need a concept nobody wrote for them:

```
held-out problems requiring a clamped interval (budget max_weight=3)
  EMPTY library (G0)     reachable 4/5   mean  84.8 ms
  AFTER invention (G1)   reachable 5/5   mean  29.5 ms      ← 2.9x faster, 5/5
```

One taught concept, from two example programs, took held-out solve rate **4/5 → 5/5** and cut the
time **2.9×**. That is the first real compounding measured in this project, and it was already
built: `canonical/swe_kernel/concept_library_v1.py`, admitted under `ΔB_exec < 0`, non-constancy
across probes, and at least one killed mutant.

**I spent the previous two rounds inventing selection mechanisms to reproduce something the
repository already does — in the one form where it works.**

## 2. The limit, measured precisely — and it is the important part

If the organ were a general inductive engine, teaching the *same idea* written differently would
work. It does not:

| teaching pair | admitted |
|---|---|
| two clamped-normalisation bodies sharing a real subtree | **1** |
| `max(p,q) - min(p,q)` vs `abs(s-t)` — same idea, different syntax | **0** |
| `(p+q)/2.0` vs `s/2.0 + t/2.0` — same idea, different syntax | **0** |
| two bodies with identical shape | 0 (nothing to compress) |
| `100.0*p/q` vs `(s/t)*100.0` — same idea, different syntax | **0** |

**It induces by syntactic anti-unification: it can only invent a concept that literally appears
in two programs it has already written, with variables substituted.**

That is the exact difference between a growing library and a mind:

> It can **reuse** what it wrote. It cannot **notice that two different programs mean the same
> thing.**

Everything that feels sentient-like lives on the far side of that sentence.

## 3. Three instrument failures caught before they became findings

Each of these would have produced a confident, wrong number:

1. **A ladder of four rungs where 3 of 4 were solved with an EMPTY library.** They measured the
   weight budget, not the mechanism. The benchmark now flags non-discriminating rungs and excludes
   them from every total; on the corrected ladder it reports **0 of 4 rungs discriminating** rather
   than "12/12 solved".
2. **A rung chain where each rung taught one program** — but `sleep_abstract` needs **two**
   programs to unify, so the library never grew and the ladder measured nothing.
3. **A "948,766× prize"** (earlier round) that was arithmetic about a `10⁶` penalty constant
   applied to unsolvable kinds.

The pattern is consistent and worth stating for whoever comes next: **my first instrument always
flatters the hypothesis.** Three times in three rounds. The correction was never in the data; it
was in the design.

## 4. So what is the smartest approach, from first principles?

Not more selection mechanisms. **Finish the generative one.** The pieces for the next rung are
already in the tree and have never been joined:

- `concept_library_v1` admits concepts by **syntactic** anti-unification;
- `discover_ast_operator_morphisms` in the *same module* already finds equivalences by
  **observational** agreement on probe vectors.

Joining them is one experiment: find a sub-expression pair that differs syntactically but agrees
on every probe, anti-unify through that correspondence, and admit the result under the same three
gates (`ΔB_exec < 0`, non-constant on ≥4 probes, kills ≥1 mutant). If it admits a concept from
`max(p,q)-min(p,q)` and `abs(s-t)`, the organ generalises semantically and the limit above moves.
If it admits nothing, that limit is structural and says so.

Ranked:

1. **Semantic anti-unification** — the only step that moves the limit measured in §2. Small,
   bounded, uses only existing machinery, and has a falsifiable success criterion.
2. **Keep the generative organ on the primary path** — it is the only mechanism in this
   repository that has ever produced compounding. It is currently reachable from a cognitive-core
   buffer, not from the front door.
3. **Composition of invented concepts** — rung after rung, does the library solve problems TWO
   concepts away? Untested; the ladder above could not reach it.
4. The backlog — still last, and now for a sharper reason than "it's not the point".

## 5. Non-claims

`truth.achieved` false. No capability registered, no family flipped. Pure Python over small
numeric tuples: no I/O, no host execution, no GUI. Whether this mechanism reaches a shell or a
browser is **not** answered here — that lane is still gated on the carrier review, and the gate is
correct. One concept invented, on constructed problems, by a producer-run benchmark.
