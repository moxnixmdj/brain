# A silent judge failure, and object construction — 17/32

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Tests:** 40 passing (`test_batched_oracle_v1` 10, `test_learned_ranking_store_v1` 9,
`test_effect_predicate_binder_v1` 14, `test_data_map_convention_v1` 7)

---

## 0. The worst bug in this chain, and it was mine

When I changed the worker to **stream** verdicts, it stopped printing the single batch array
and started printing one `@@@`-prefixed line per verdict. I updated `judge_stream` — and
**forgot `judge_many`**, which kept parsing for a line starting with `[`.

The consequence: `judge_many` returned `worker_failed` for **every batch, every item, silently**.
Any caller still on the batched path was measuring nothing and reporting it as zero.

Found by asking why item 190's *reference solution* failed. A reference solution failing is
never a search problem — it means the instrument is broken. That check should have been the
first thing I ran after touching the judge, and now it is a test.

```python
def test_judge_many_parses_the_streamed_format():
    verdicts = B.judge_many(..., ["n", "sympy.totient(n)", "1"], ...)
    assert [v["passed"] for v in verdicts] == [False, True, False]
    assert all(v["why"] != "worker_failed" for v in verdicts)
```

Verified after the fix: **6 of 6 reference solutions pass** (176, 177, 178, 188, 190, 191).

**The lesson is general:** a judge that fails closed is indistinguishable from a system that
knows nothing. Every instrument in this chain must be validated against the reference solution
before any result it produces is believed.

## 1. Object construction: `TUPLECALL`

Item 190's stub imports with `*`, so its imports name nothing. Its **return annotation** does:
`tuple[sympy.physics.mechanics.RigidBody, sympy.physics.mechanics.Particle]`. That is a
statement, in order, of what the function must return.

With only that annotation and the parameter list, the body is
`RigidBody(rigid_body_text), Particle(particle_text)` — imported names paired positionally with
parameters.

**Three bugs before it worked, all mechanical:**

1. the annotation is **dotted**, so an `isidentifier()` check rejected every real name;
2. the block sat below the combinatorial grids, so the 600-candidate cap cut it — it was at
   position 36 of the *untruncated* space and absent from the truncated one;
3. the name list led with `'sympy.physics.mechanics'` and `'str'`, so positional pairing
   produced `sympy.physics.mechanics(rigid_body_text), ...`. Restricting to
   **capitalised identifiers** is what made the pairing correct.

Item 176 also fell out of the same work: `DFT(n)` alone passes; the reference's
`.as_explicit()` is not required.

## 2. Result

| | full sympy cohort (32) |
|---|---|
| start of this chain (different cohort) | 3/40 |
| store + shape + stated + squash | 12/32 |
| + composition grammar (streaming judge) | 15/32 |
| **+ TUPLECALL / annotation names / judge fix** | **17/32 in 163 s** |

```
176 DFT(n)                                         APPLY
179 sympy.core.preorder_traversal(expr)
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

## 3. The 15 that remain

| class | items | note |
|---|---|---|
| vocabulary — name shares no word with the prose | 183, 184, 185, 188, 194 | the real remaining limit |
| composition the grammar does not admit | 177, 180 | matrix built from a literal; `.replace(...)` chain |
| object construction with nested cross-parameter reads | 181, 182, 189 | needs `parent.frame.x`, two levels down |
| relative-import path | 186 | `from sympy.physics.mechanics import inertia` |
| throughput | 191 | passes alone in 0.4 s, never inside a batch |
| needs a stated value the prose does not give | 200 | `from_array_to_matrix` import |
| **benchmark defect** | 203 | prose says "distinct", test wants "multiplicity" |

`truth.achieved` remains `false`. 17/32 = 53% of a 32-item no-dependency sympy cohort. **This is
not a benchmark score.** It is not comparable to the 51–59% frontier figures on the full
328-item benchmark, which include all 26 libraries and dependency-bearing items.
