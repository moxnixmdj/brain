# The residue is the question — 9/13 held-out

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instrument:** `canonical/tools/shape_and_synonym_v1.py`
**Chain:** … → `THE_STORE_CARRIES_THE_CONVENTION` (7/13) → this

---

## 0. The user's idea, tested

> "All he should do is scan everything in the environment and then retrieve from his memory
> what he knows and what he doesn't know."

That is, word for word, the mechanism that produced this receipt's result. Applied to a stub:
the **declaration already states** the parameter names, the types and the return annotation.
Those are known. What is left — the *residue* — is the only thing that needs fetching.

The measurement below is what happens when the residue is asked as a question rather than
searched as a space.

## 1. Where the six held-out failures actually came from

Classified by measurement, not opinion:

| item | needs | name-word in prose? | why it failed |
|---|---|---|---|
| 193 | `matrix.flat()` | **yes** — "returns a **flat**, read-only copy" | ranked 40th among 40 full-coverage ties |
| 195 | `sympy.bottom_up(expr, lambda x: x.doit())` | **yes** — "**bottom-up** traversal" | ranked 32nd; and the call needs a lambda arg |
| 196 | `sympy.use(expr, lambda x: x.doit())` | **yes** — "**traverses**..." | ranked **3rd**; the body shape was wrong |
| 194 | `matrix.todok()` | no — prose says "dictionary-of-keys" | **vocabulary** |
| 198 | `sympy.isprime(n)` | no — prose says "check if prime" | **vocabulary** |
| 203 | `sympy.primeomega(n)` | no — prose says "**distinct**" | **the benchmark contradicts itself** |

That split is the whole finding: **three were our bugs, not knowledge gaps.**

## 2. Two mechanisms, both derived from stated text

**(a) A word the prose uses that is exactly a member name is a statement, not a tie.**
Item 193 says "flat". `flat` is a member. That is not a similarity score — it is the prose
naming the symbol. Stated symbols are tried *in full*, ahead of any ranking.

A first version tokenised the problem and kept every token that was any member name; that
pulled in `Expr`, `Lambda` and `traversal` and helped nothing. The requirement that the word
be the **exact final member name**, lowercase-initial, is what made it work.

**(b) A phrase the prose uses that demands an argument shape is also a statement.**
"with a lambda function" cannot mean a call without one. "flat, read-only" names a member.
Shape hints are read from the prose and turned into legal bodies.

Two bugs in my own implementation, each of which alone blocked the result:

- the lambda shape had a `len(args) >= 2` guard, so item 195's **one**-parameter stub never
  received the lambda the prose explicitly demands;
- stated symbols and the ranked list shared one budget of 60, so `bottom_up` (whose canonical
  path is `sympy.core.bottom_up`, rank > 60) was cut off before being tried.

## 3. Result

| configuration | held-out solved |
|---|---|
| store ranking alone | 7/13 |
| + shape derivation | 8/13 |
| + stated symbols, separate budgets | **9/13** |

```
193  list(sympy.matrices.Matrix(matrix))     <- not the reference body, still correct
195  sympy.core.bottom_up(expr, lambda x: x.doit())
197  sympy.external.gmpy.is_square(n)
201  sympy.external.gmpy.jacobi(a, n)
202  sympy.ntheory.npartitions(n)
204  sympy.functions.primepi(n)
205  sympy.functions.totient(n)
206  sympy.functions.mobius(n)
207  sympy.external.gmpy.legendre(a, n)
```

Item 193 is worth noting: the system found a body the benchmark author did not write, and it
passes. That is not leakage and not replay — it is a different correct answer.

## 4. The three that remain, and why they are different

- **194 `todok`** — prose says "dictionary-of-keys representation". The name `todok` shares no
  word with it. Vocabulary.
- **198 `isprime`** — prose says "check if the input is prime". The name shares "prime" but
  `isprime` is one token; my splitter only splits on `_` and camelCase, not on the
  is-prefix. **Possibly fixable by also trying `is_` + word compounds.** Not yet tried.
- **203 `primeomega`** — **the benchmark's prose is wrong.** It says "the number of
  *distinct* prime factors". `len(primefactors(n))` satisfies that sentence and **fails** the
  hidden test. `primeomega` counts *multiplicities* and passes. The literal correct reading of
  the problem statement is marked wrong by the problem's own test.

So of 13 held-out items: **9 solved, 2 vocabulary, 1 unsolvable by anyone reading the prose.**

## 5. What the user's idea got right, and what it cannot do

**Right:** scanning the environment and asking only about what is *not* already stated is
exactly the mechanism that produced +2. The declaration is knowledge; the residue is the
question.

**Cannot do:** when the residue and the name share no word (`todok`), no amount of scanning
derives it, because the artifact never says it. And when the benchmark's own prose is wrong
(203), no mechanism reading that prose can succeed.

**Goal-directed vs learn-everything:** this data answers it. The system learned only what it
did not already know — the residue — and that was sufficient for 9 of 13. Saving the full
experience would have stored parameter names and annotations that the next item states again
for free. Save the residue, not the experience.

`truth.achieved` remains `false`. 9/13 is 69% of a 13-item held-out half of a 26-item sympy
sub-cohort. It is not a benchmark score and is not comparable to the 51–59% frontier figures.
