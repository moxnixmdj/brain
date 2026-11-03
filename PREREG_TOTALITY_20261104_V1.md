# Pre-registration: a concept must be total on its own domain

**Written before implementing. 2026-11-04 · authority NONE · `truth.achieved` false**

## The structural defect

`_verify_candidate_concept` builds its certificate by looping over probe points and doing:

```python
except Exception:
    continue          # <- the whole defect
```

A probe that *raises* is silently skipped, not counted as a failure. The certificate is therefore
"deterministic and non-constant on the inputs where it happens to survive", which is a certificate
of nothing. The concept is then stored as universally valid and handed to the synthesizer as an
atomic building block.

Measured 2026-11-04 on a 40-program corpus: **2 of 2 admitted concepts raise on the repository's own
numeric probe grid.**

| concept | raises on |
|---|---|
| `(min(max(_v0,_v1),_v2) - _v1) / (_v2 - _v1)` | 4/26 probes (all equal-argument points) |
| `min(max(_v0,0.0),1.0) * _v1 / (_v1 + 1.0)` | 2/26 probes (`_v1 == -1`) |

Note what the library admitted *alongside* the first one: the guarded variant
`... if _v2 > _v1 else 0.0`, which is total. So the corpus contains the correct invention and the
broken one, and the gate could not tell them apart. That is the test.

## The change

A concept is admitted only if it is **total on its own declared domain**: zero undefined probes
(raise or non-finite) over the full grid for the domain it claims. `undefined_probes` is stored on
the entry so the fact is visible rather than silent. The numeric grid gains equal-argument points,
because that is exactly where division dies.

## Predictions (falsifiable, stated before the run)

**T1.** The unguarded concept is rejected; the guarded one is still admitted. The gate must
discriminate between them, which it provably could not before.

**T2.** No admitted concept raises on any probe of its domain. (Trivially true if implemented, but
the *count* is the measurement: 2/2 partial before, 0/n after.)

**T3 (the risk I am taking).** Downstream generalising reach must not fall. If it does, the totality
requirement is too strict and must be relaxed to domain-tracking instead of rejection. I predict it
does not fall, and specifically that the `+0.5` held-out problem is still solved, because the guarded
concept remains available.

**T4 (the honest counter-risk).** Some legitimately useful partial concept could be rejected. I
predict this benchmark will NOT be able to show that, because it only contains concepts I chose. This
prediction is here so the limit is recorded rather than discovered later.

**T5.** A partial concept must never be offered to the search as a total building block, since a body
built from it can crash on inputs the creature itself considers ordinary.
