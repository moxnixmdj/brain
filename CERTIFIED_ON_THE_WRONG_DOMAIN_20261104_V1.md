# Certified on the Wrong Domain

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

Fifth time asked whether this is the smartest approach. Rather than answer again, I looked for the
shape all my work shares.

**Every module I have built this week runs the same algorithm:** search a fixed space, score
candidates by agreement with observations *I supply*, keep the winners. Concept invention, semantic
unification, lifecycle, attribution — four names, one loop. So the question "is this the smartest
approach?" has an uncomfortable answer: **there has been only one approach.** What varied was the
space being searched.

That reframing sent me looking for the thing that is *not* that loop, and it turned up a defect that
is structural rather than incidental, and that no amount of better search would have fixed.

---

## 1. The defect: a certificate that certifies nothing

`_verify_candidate_concept` builds the justification for admitting a concept by looping over probe
points. Inside the loop:

```python
except Exception:
    continue          # <-- the whole defect
```

A probe that **raises is skipped, not counted.** So the certificate is not "this concept is
deterministic and non-constant". It is "this concept is deterministic and non-constant *on the inputs
where it happens to survive*" — and that subdomain is chosen, silently, by the concept itself.

The admitted concept is then stored as a universally valid atomic building block and handed to the
synthesizer. Every program built on it inherits whatever it does on the inputs nobody checked.

Measured on a 40-program corpus, before any change:

| | |
|---|---|
| admitted concepts | 2 |
| **admitted concepts that raise on the repository's own numeric grid** | **2** |

Both were divide-by-`(_v2 - _v1)` shapes. And the reason they were never caught is worse than the
`except`:

> **Every probe in the grid had distinct coordinates.** So `_v1 == _v2` — the one input where the
> expression dies — was never evaluated. Not once.

The corpus contained the guarded variant of the same idea (`... if _v2 > _v1 else 0.0`) alongside
the unguarded one. **The gate could not tell the right invention from the broken one.** That is the
test the fix has to pass.

---

## 2. What changed

1. The numeric probe grid gains **equal-argument points**, because that is exactly where division
   dies.
2. An undefined probe is a **failure**, not a skip. Rejection names the cause:
   `PARTIAL_DOMAIN:numeric:ZeroDivisionError`.

Pre-registered in `PREREG_TOTALITY_20261104_V1.md`; **3/3 findings as predicted.**

| finding | measured |
|---|---|
| gate discriminates totality | guarded **ADMIT**, unguarded **REJECT**, `abs`/mean/guarded-ratio **ADMIT**, `1.0/_v0` **REJECT** |
| no admitted concept is partial | 2 admitted, **0/2 raise** (was 2/2) |
| strictness costs no reach | empty library 0/2 → strict library **2/2**, via `concept_640d4492(v, l, h) + 0.5` |

The third row is the risk I stated in advance: a stricter gate could have thrown away the useful
concept. It did not, because the guarded form survives and gets used.

---

## 3. What the change broke, which is the interesting part

The stricter gate invalidated an earlier test's premise — and the failure was informative.

That test asserted, at a thin corpus, *"two spellings admit fewer concepts than one spelling, and the
bridged corpus recovers the difference."* After the totality gate, the ordering **inverted**: at sizes
5–16 the mixed corpus admits **more** than either single spelling (2 vs 1), because one spelling's
surface form is total and the other's is not, so the two corpora surface different viable subtrees.

And at size 5, bridging now **reduces** admission (2 → 1): rewriting every program into one spelling
homogenises the corpus, destroying the subtree diversity the totality gate depends on.

I had already rewritten that test once this session for the same class of reason. So instead of
patching it a second time to whatever holds today, I narrowed it to a claim that does not depend on
which gate is currently in force — the bridge is mechanically sound and the corpus stays learnable —
and added `test_join_admission_direction_is_not_claimed`, which fails if anyone later asserts a
direction. **Two consecutive tests of mine asserted a fact about my own mechanism that stopped being
true when the mechanism improved.** That is a property of my testing, not of the code: I was writing
tests that pinned observations rather than invariants.

---

## 4. Why this is the deepest thing I have found

The previous four rounds produced mechanisms that make the creature's *answers* better. This one
changes what the creature can be **confident about**, and the failure it fixes is one that no better
search could repair.

Consider what a partial concept does to a system like this. The synthesizer treats a concept as an
atomic constant of weight 2. It composes it with everything. If that concept is undefined on a region
of its own declared domain, then the creature's grammar contains a landmine: perfectly reasonable
programs that pass every example and crash on inputs it believes are ordinary. And because the
admission certificate was produced by *skipping* the crashing probes, **the failure mode was
self-certifying** — the more partial a concept was, the smaller its effective test suite, the more
easily it passed.

That is a general lesson and not a Python one:

> **A verifier that ignores the cases where it raises will admit exactly the things it cannot
> handle.** The set of passing tests is not the set of behaviours; it is the set of behaviours that
> did not embarrass the test.

For a creature the consequence is concrete. It can now only build on parts it has checked are
defined everywhere it claims. It cannot yet say "defined here, not there" — that is domain
*tracking*, and I explicitly predicted this benchmark cannot show whether rejecting useful partial
concepts is a real cost, because it only contains candidates I chose. A guarded reciprocal that callers
promise never to feed zero is a legitimate concept that this gate throws away.

---

## 5. The shape of the thing, stated honestly

Five rounds have produced, in order: a working generative mechanism, a way to see that two
differently-written programs share an idea, a memory that can be wrong about itself, an ability to
attribute a failure to the right part, and now a guarantee that the parts are defined on their
domains. Each is measured. None was in the repository's behaviour a week ago.

And the honest accounting of the *approach*: I still search a fixed space and score against
observations I supply. What has changed across the five rounds is not that. It is that the outputs of
that loop are now **checked for self-consistency before they are trusted** — total on their domain,
attributable when wrong, revocable when wrongly retired. The creature's intelligence has not grown in
the last two rounds. Its **error structure** has, and that is what a system needs before more
intelligence is worth having.

**The one thing still absent, unchanged:** nothing here notices that it failed. The initiator is
still missing, and it is still the top-ranked move. What this round adds is that when the notice
arrives, the creature will not be building on a certified-broken part.

**Non-claims.** No sentience. Pure Python over small numeric tuples; no I/O, no host execution, no
GUI; nothing here bears on reaching a shell or browser, which remain gated. Totality is checked on a
probe grid, not proved — a concept can still raise at a point the grid does not contain.
`truth.achieved` stays false. $0 spent.

---

## 6. Ranked next moves

1. **The initiator.** Unchanged and still first. Everything downstream is now built and measured.
2. **Domain tracking instead of rejection.** Let a concept declare the region it is total on and have
   the synthesizer respect it, rather than discarding partial concepts. This is the direct answer to
   the counter-risk in §4, and the totality gate has already produced the data it needs.
3. **Guarantee the probe grid covers the expression's singularities**, derived from the expression
   rather than fixed in advance — the equal-argument hole shows a fixed grid is a guess.
4. Repair rather than discard a refuted concept; composition of invented concepts; the front door.
