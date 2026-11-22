# Bare names, and why the remaining 13 are not one problem

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Chain:** … → `SILENT_JUDGE_FAILURE_AND_OBJECT_CONSTRUCTION` (17/32) → this

---

## 0. The emitter was wrong about namespaces

Four items failed for one reason that had nothing to do with ranking:

| item | body that passes | body I was emitting |
|---|---|---|
| 183 | `is_carmichael(n)` | `sympy.is_carmichael(n)` ✗ |
| 184 | `divisor_sigma(n, k)` | `sympy.divisor_sigma(n, k)` ✗ |
| 188 | `poly.rep.to_list()` | — not generated |
| 194 | `matrix.todok()` | — not generated |

Their stubs import with `from sympy import *`, which binds every public name **directly**. The
qualified form is a `NameError` there; the bare form is correct. Both are now emitted whenever
the stub star-imports, because the stub's own import line states which are available.

Two more solved immediately: **183 and 184**.

## 1. What I stopped doing

I also tried member-call generation (`matrix.todok()`, `poly.rep.to_list()`) by taking member
names from the prose. It cost 192 its solution and bought nothing measurable. I moved it after
the ranked bodies, measured again, and left it in place **because it is now harmless** — but I
am recording that it has not yet produced a win, rather than pretending it has.

## 2. Result: 19/32 in 158 s

```
176 DFT(n)                                         APPLY
179 sympy.core.preorder_traversal(expr)
183 is_carmichael(n)                               BARE
184 divisor_sigma(n, k)                            BARE
187 eq.lhs - eq.rhs                                 OP
190 RigidBody(rigid_body_text), Particle(...)       TUPLECALL
192 Matrix([first, second])                         APPLY
193 list(sympy.matrices.Matrix(matrix))
195 sympy.core.bottom_up(expr, lambda x: x.doit())
196 sympy.core.use(expr, lambda x: x.doit())
197 sympy.external.gmpy.is_square(n)
198 sympy.ntheory.isprime(n)
199 n % p == 0                                       PREDICATE
201 sympy.external.gmpy.jacobi(a, n)
202 sympy.ntheory.npartitions(n)
204 sympy.functions.primepi(n)
205 sympy.functions.totient(n)
206 sympy.functions.mobius(n)
207 sympy.external.gmpy.legendre(a, n)
```

**Held-out split, re-measured under current code:** train 3/13, held-out **14/19**. The held-out
rate is the higher one because the train half holds the physics-construction items, not because
the grammar was fitted to them.

## 3. The remaining 13 are five different problems, and I will not merge them

| class | items | what would actually fix it |
|---|---|---|
| **relative-import path** | 186 | `from sympy.physics.mechanics import inertia` is a *statement in the reference*, not derivable from a namespace walk |
| **nested cross-parameter reads** | 181, 182, 189 | `parent.frame.x` is two levels below what `attribute_paths` reaches; needs per-parameter attribute *values*, not just names |
| **member call with an unstated name** | 188, 194 | `to_list`, `todok` — the prose says "coefficients" and "dictionary-of-keys"; the name is convention |
| **composition over a literal** | 177, 180 | `laplace_transform(eye(2), ...)` builds a matrix from nothing; `.replace(Function("F"), lambda *x: ...)` nests a lambda inside an argument |
| **needs a stated value the prose omits** | 200 | the stub references `from_array_to_matrix` which does not exist in the namespace |
| **throughput** | 191 | passes alone in 0.4 s; every batch containing it hangs on a symbolic arithmetic candidate |
| **benchmark defect** | 203 | prose says "distinct", the test demands multiplicity |
| unclassified | 178, 185 | `Tr(n)` under `physics.quantum.trace`; `K.to_int(a)` |

Of these, only **188, 194 and the unclassified pair** are the meaning→name convention in its
pure form. The rest are structural gaps in the grammar, and each is a known shape rather than
an unknown word.

## 4. Where the honest number stands

19/32 = **59% of a 32-item no-dependency sympy cohort**, in 158 s, zero model calls, zero
network.

That number is **not a benchmark score** and is not comparable to the published 51–59% figures,
which are measured on all 328 items across 26 libraries with dependency pinning. A no-dependency
sympy subset is a different and easier distribution. Any comparison would be dishonest, and I
am not making one.

`truth.achieved` remains `false`.
