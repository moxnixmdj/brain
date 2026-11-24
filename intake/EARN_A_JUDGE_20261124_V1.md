# A judge is earned, not written

**Round 11. Round 10 named its own ceiling: seven hand-written validators. This round makes the eighth cost one probe pair instead of new code — and finds a real defect in round 10 while auditing its output.**

Date: 2026-11-24 · Base: `62223e40` (PR #7059) · Branch: `arena/c5a50d2f-brain`

---

## 1. The ceiling, and why writing more validators is the wrong move

Round 10 shipped seven validators — `json`, `python`, `utf8_text`, `png`, `gzip`, `tar`, `zip` — each a sentence I typed. The set decides how much of an unseen environment can honestly be called known, so seven is a seed, not coverage.

Writing more is the move that never ends: every new environment brings kinds nobody wrote a validator for.

## 2. Everything needed was already in the repository

- **A refusal names a kind.** `a_refusal_is_a_specification_v1` yields `certificate`, `key`, `parameters`, `shared library`, `crl` — 601 of them on the enlarged openssl census.
- **A program's verdict on a file is a judgement about that kind.** `gzip -t` rejects what is not gzip; `unzip -t` what is not zip.
- **Round 10 already excluded `cat`** — for accepting everything, which is precisely the property a fake judge has.

So a judge does not need to be typed. It needs to be **measured**.

## 3. The loop

A candidate is admitted only on evidence:

1. **Discrimination** — exit 0 on a real file of the kind, non-zero on a decoy.
2. **Determinism** — same file, same verdict.
3. **No side effects** — the tree is unchanged after judging. (Round 10 got bitten by exactly this: `py_compile` wrote `__pycache__` and the scan read its own validator's output.)

The **real member of every probe pair is written by the program that defines the kind** — `zipfile`, `gzip`, `json.dump`, `tar -cf`, the interpreter. The authority is the probe pair, never my candidate table.

## 4. Measured

| | |
|---|---|
| earned | **7 of 8** — exactly round 10's seven |
| refused | `gzip.open(p,'rb')` — **0 on real, 0 on decoy** |
| earned set vs. typed set | **identical** |
| agreement on real files | **210 judgements, 30 files, 0 disagreements** |

The one refusal is the whole point:

```
python3 -c "import gzip,sys; gzip.open(sys.argv[1],'rb')"
  real=0  decoy=0   →  REFUSED__ACCEPTED_THE_DECOY_TOO_THIS_IS_cat
```

`gzip.open(..., 'rb')` is **lazy**. It reads nothing and hands back a handle for any file. That is `cat` wearing a library call.

Bad guesses are refused too, including one that looks right:

```
lazy bz2.open     0/0  refused
bzip2 -d          0/2  refused  (decompresses — wrong direction)
cat               1/0  refused
```

## 5. The ceiling moves

| file | round-10 typed judges | with 2 earned judges |
|---|---|---|
| `a.zip` | `('zip',)` | `('zip',)` |
| `c.json` | `('json','python','utf8_text')` | unchanged |
| **`e.bz2`** | **`()` unreadable** | **`('bz2',)`** |
| **`f.xz`** | **`()` unreadable** | **`('xz',)`** |

**Zero new validator code.** No regression on the other four.

## 6. A defect in round 10, found while auditing it

Round 10 reported 13 files in `intake/` as `UNKNOWN`. **All 13 were accepted by `utf8_text`.** They were unknown only because memory had never recorded that exact *subset* of validators — a statement about memory's bookkeeping, not about the file.

That inflated the unknown count and **aimed the next round's learning at markdown the machine could already read.**

Fixed to three verdicts:

| verdict | meaning | queued for learning? |
|---|---|---|
| `KNOWN` | signature recorded | no |
| `UNDERSTOOD` | a declared validator reads it; subset is new | **no** |
| `UNREAD` | nothing on this machine accepts it | **yes** |

Re-measured: `intake/` → **27 KNOWN, 13 UNDERSTOOD, 0 UNREAD**, learn queue empty. Correctly empty.

## 7. Two defects in my own probe

- **The decoy was `bytes(range(0,64))`** — perfectly valid UTF-8. `utf8_text` accepted it and was reported as `cat`. **The refusal was correct and my probe was wrong.** Decoy is now `0xFF` bytes.
- **I omitted `python` and `utf8_text` from the candidates**, assuming they were not earnable. Measured: both separate the pair cleanly. My omission, not a limit of the loop.

## 8. Honest limits

- **A candidate argv is still supplied by me.** The loop decides *whether* it is a judge, not *which program to try*. Choosing the program automatically is not done.
- Earning needs a producer or library for the kind on this machine.
- Seven is still small; the claim is only that the eighth costs a probe pair, not code.
- The scan falls back to the typed table when a program is absent.
- No benchmark task was run.

## 9. Next bottleneck

**Choosing which program to try, without me naming it.** The environment declares its own judges the same way it declared its own producers in round 9 — and the probe pair decides whether the declaration was honest.

Authority `NONE`, sandbox only, independent verification **OPEN**.
