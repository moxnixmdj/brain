# PRE-REGISTRATION — *The library that nobody reads, and the closure that replaces it*

2026-11-04, V1, round 24. Written **before** implementation, after measuring.
Base `72e27486` (= `origin/main`, round 23 merged). `truth.achieved` false, `authority: NONE`, $0.

---

## 1. Round 22's diagnosis was wrong, and I am correcting it first

Round 22's note said: *"the concept library receives zero concepts because the bridge admits only
single-`return` bodies, so nothing accumulates."* That was measured on round-20 writer organs, whose
bodies were `Assign, Assign, Return`.

Round 23 replaced those with searched organs whose bodies are a single `Return`. Re-measured now:

```
concepts before: 0
  P=3  concepts=1
  P=5  concepts=2
  P=7  concepts=3
```

**The bridge fires. Concepts are admitted.** Round 22's causal claim was therefore about a symptom that
round 23 happened to remove, not about the reason the creature does not improve.

## 2. The real finding: the library is admissible and inert

Same shape, with and without three learned tables:

| task | cold | after periods 3, 5, 7 are in the library |
|---|---|---|
| `T(x) + x` | REFUSED | **REFUSED** |
| `2*T(x) - 1` | 6/6 | 6/6 |
| `T(x) * x` | REFUSED | **REFUSED** |
| `T(x) + U(x)` | 6/6 (via the period writer) | 6/6 |

**Identical.** Three concepts sit in `G_t` and change nothing. And the compounding test is flat for a
reason that cannot be fixed by making the library better:

```
period-12 cold : 2 questions
period-12 warm : 2 questions   (after 3,5,7 admitted)
```

2 is the information floor (one observation per block entry). Round 23 already reached the floor, so
**cost cannot be the measure of learning any more** — a library that made a floor-cost problem cheaper
would be beatable only by knowing the world for free.

So "does it compound" must be asked differently: **does experience let the creature express a structure
it could not express before?** Today the answer is no, and here is the class that proves it — a table
*composed* with something (`T(x)+x`, `T(x)*x`) is refused cold and refused warm.

## 3. Why: the grammar has nodes but no closure

Round 23 added one node (`_solve_parametric_table`). That fixed one shape. It did not change the fact
that every expressible form is one a human wrote a rule for. Adding a second node for "table plus x"
would repeat the mistake one level up, and a third for "table times x" after that.

The first-principles statement: **the expressible set should be the closure of a small basis under
composition, not a list of composed forms somebody anticipated.** The basis stays tiny (the input, a
solved table, an affine form, a solved table with a different period). Composition is then a *rule*, not
a menu item.

Prototype measured before writing this, solving rather than guessing — for each candidate
`f(x) = T_k(x) ⊙ g(x)`, invert `⊙` and check the residual is constant per residue:

```
T(x) + x       -> solved period 3, block [5.0, -2.0, 7.0]
T(x) - x       -> solved period 3, block [5.0, -2.0, 7.0]
T(x) * x       -> solved period 3, block [5.0, -2.0, 7.0]
2*T(x) - 1     -> solved period 3, block [9.0, -5.0, 13.0]
T(x) + x*x     -> solved period 3, block [5.0, -2.0, 7.0]
```

The parameters are *solved*, exactly as in round 23. Nothing is enumerated blindly (which is how a
grammar generates a million false positives and calls it capability).

## 4. What I will build

**Depth-1 compositional closure over the existing basis, with parameters solved.** For each pairing of
a small basis element with one arithmetic combining operation, invert the operation and test whether the
residual is a constant-per-residue block. Candidates enter the same version space as everything else.

Explicitly bounded:

- **Depth 1 only.** No transitive closure, no unbounded nesting. A fixed, small number of candidates.
- **Every candidate is still checked against every example** by the existing filter; the version space
  and held-out refutation decide. This adds candidates, never authority.
- **No new refusal bypass.** If nothing survives, the answer remains a refusal.

I will **not** wire the concept library as a template source in this round. The measurement above says
it is inert; making it load-bearing without evidence that it helps would be decoration. Its honest
status across all rounds is: it accumulates, and nothing reads it.

## 5. Predictions — stated so they can fail

- **P1 (compositions that were refused).** `T(x)+x`, `T(x)-x`, `T(x)*x` and `2*T(x)-1` are each
  expressed, and exact on held-out inputs never shown.
- **P2 (composition does not require the library).** The same results cold, i.e. with an empty concept
  library. If they only work warm, the claim in §2 is wrong and I will say so.
- **P3 (no false structure).** The refusal set is not weakened: `x*x`, `x^3`, `floor(x/7)`, and a
  pseudo-random mapping must still refuse. This is the prediction most likely to fail, because widening
  a grammar is exactly how false positives enter.
- **P4 (bounded cost).** Candidate count and wall clock stay within a stated multiple of round 23's, and
  the reported question count still equals what was asked.
- **P5 (no regression).** Every previously-merged suite passes unchanged; round 20's protections and
  round 23's nine tests still hold.

**Explicitly NOT predicted:** that anything compounds across *separate* problems. Composition widens what
one problem can express; it does not by itself make a later problem cheaper, and §2 explains why cost is
the wrong measure now. If I later claim compounding, this paragraph is the record that I said it would
need a different kind of evidence.

## 6. Non-claims

- Compositional closure is still a **design decision**. It is strictly less static than N hand-written
  nodes, and it is not emergence. One rule instead of many is smaller, not arisen.
- The basis is unchanged and still small; closures over a small basis do not become generally capable.
- `truth.achieved` false. `authority: NONE`. $0. No external models, no neural weights, no dynamic code
  execution in result-bearing modules.
