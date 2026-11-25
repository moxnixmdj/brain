# A judge must reject other real kinds

**Round 12. Round 11 claimed seven judges. The honest number was five. One decoy cannot find a judge that says yes to a kind that is not its own.**

Date: 2026-11-24 · Base: `bc54ee86` (PR #7060) · Branch: `arena/21d380ce-brain`

---

## 1. The bottleneck was real, so I measured it first

Before building anything, I checked whether last round's named bottleneck actually binds. Scanned four real system directories:

| directory | unreadable |
|---|---|
| `/usr/share/doc` | 0% |
| `/usr/lib/python3` | 0% |
| `/etc` | 32.5% |
| **`/usr/bin`** | **73.3%** |

Yes — 73% of a real binary directory could not be read. And the unread class was almost entirely **ELF binaries**, which four programs on this machine judge happily.

## 2. Then the measurement destroyed round 11's result

Run every judge against every *other* real kind, not against a nonsense blob:

```
judge        zip  gzip  json  python  text  elf  tar  png
gzip           0     0     1       1     1    1    1    1   <- says yes to a ZIP
tar            2     0     2       2     2    2    0    2   <- says yes to a gzip
python/ast     1     1     0       0     1    1    1    1   <- says yes to JSON
utf8_text      1     1     0       0     0    1    0    1   <- says yes to tar
```

`gzip -t` on a real zip prints **"OK" and exits 0** (gzip 1.12). `tar -tf` on a real gzip exits 0. And a JSON document **is** a valid Python program — `{"a": 1}` parses as an expression statement.

**Round 11's decoy was a single nonsense blob.** That test cannot tell "rejects what is not my kind" from "accepts my kind *plus* some other real kinds". All four of the above passed it.

The consequence is not academic: a scan built on them would have reported a **zip file as gzip** — exactly the lying-name failure round 10 fixed, coming back through the validator instead of the suffix.

## 3. The fix, and the recovery

A candidate must **reject every other real kind in the corpus**, and the refusal names which kinds it accepted.

`gzip` and `tar` were then *recovered* by asking a different question of the same program:

| candidate | real | decoy | other kinds accepted |
|---|---|---|---|
| `gzip -t` | 0 | 1 | zip → refused |
| `gzip.open(p,'rb').read(1)` | 0 | 1 | **none → earned** |
| `tar -tf` | 0 | 2 | gzip → refused |
| `tarfile.open(p)` | 0 | 2 | **none → earned** |

`gzip -t` tests *integrity* and calls a zip OK. Reading a byte through the decompressor asks *"is this a gzip stream"* and a zip fails it.

## 4. The second correction: nested kinds

With the strict rule alone, **five judges remained and 0% of `/usr/share/doc` and `/usr/lib/python3` was readable.** Because a `.py` file *is* utf8 text, and JSON *is* parseable python — those judges must accept a superset to be correct at all.

So there are two admission classes:

| class | test | may it prove a file is *not* something else? |
|---|---|---|
| **EXCLUSIVE** | rejects every other real kind | yes |
| **NESTED** | accepts a superset — correct for a nested kind | **no** |

Final honest set: **exclusive** `elf, gzip, json, png, tar, zip` · **nested** `python, utf8_text`.

## 5. An API trap found while auditing

`Item.path` is relative to the scan root. So `signature(item.path, judges)` resolves against the caller's cwd, finds nothing, and returns `()`. Measured: **0% of `/usr/share/doc` looked readable** through that route while the same files read fine by absolute path. Any caller re-judging what it was given would report every file unreadable.

Fixed: `Item` keeps the absolute path alongside the relative one, and `rejudge()` uses it.

## 6. Coverage on a real machine

| directory | readable |
|---|---|
| `/usr/share/doc` | 80/80 |
| `/usr/lib/python3` | 80/80 |
| `/etc` | 73/80 |
| `/usr/bin` | **80/80** (was 73% unreadable) |
| `/usr/lib/x86_64-linux-gnu` | 80/80 |
| **total** | **393/400 = 98.2%** |

`elf` was earned from `readelf -h`; `strings` was refused as a candidate *in advance* because it accepts everything.

## 7. What I corrected in my own earlier work

Four round-11 tests now asserted things that are false. I updated them to assert the measured truth rather than leaving a contradiction in the tree:

- ~~"earned set == hand-typed set"~~ → the earned set is a **subset that has been independently judged, plus `elf`**
- "every admitted judge separated its pair" → now admits `EARNED` **or** `NESTED`
- the `cat`-shaped candidate is looked up by **candidate name**, not by kind

## 8. Limits

- The candidate argv is **still supplied by me**. The loop decides *whether* it is a judge, not *which program to try*.
- "Exclusive" is a statement about the probe corpus, not a proof — a kind outside the corpus could still be accepted.
- `NESTED_KINDS` is declared, so a genuinely nested kind not named there is refused rather than classified.
- No benchmark task was run.

## 9. Next bottleneck

**Choosing the candidate without me naming it.** This round shows exactly why: every judge that survived was recovered by asking a *different question of the same program* — `gzip -t` → `gzip.open().read(1)`, `tar -tf` → `tarfile.open`. A fixed candidate list cannot make that move. The environment can.

Authority `NONE`, sandbox only, independent verification **OPEN**.
