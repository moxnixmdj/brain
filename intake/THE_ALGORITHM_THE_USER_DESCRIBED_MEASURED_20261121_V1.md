# The algorithm the user described, measured

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 14 tests pass

> "all he should do is go into any new arbitrary environment and he doesn't know anything...
> scan everything, retrieve what memory knows and what it doesn't, fetch what it doesn't"

This idea is **right about the shape and wrong about the payoff**, and the measurement says
exactly where the line falls. Three claims were tested on a host the system had never seen
(`/usr/sbin`: 216 programs, **213 names never encountered** while learning on `/usr/bin`).

---

## 1. What the algorithm buys: 253× — real, and it is the whole speed story

| | cold (host never visited) | warm (memory present) |
|---|---|---|
| three roles over 216 programs | 21.0 s | **0.083 s** |
| scan alone | — | **0.048 s** |
| answers identical? | — | **yes, byte for byte** |

The mechanism is not clever: a **read** page is a fact. If a program's help page has been read
and did not state a flag for this role, asking again changes nothing. Storing that — keyed on
(content digest, name) so a changed binary is a miss — turns the warm visit into one scan.

The first version stored only *positive* answers and saved 4% (6.97 s vs 7.18 s). A memory that
saves 4% is not a memory. Reusing read negatives took it to 0.058 s, and the answer set did not
change. **Both facts were needed before the number was real.**

### And it is small

| form | bytes | says |
|---|---|---|
| literal record per program (the existing store) | 190,845 | 429 transcriptions |
| generalized (class + flag pattern, prose dropped) | 38,474 | 31 classes, 37 patterns |
| read-set + positives, digest recomputed by the scan | **8,240** | 4 positive facts, 2 read-sets |

The digest is not stored at all — the scan recomputes it every visit, so writing it into the
file was 17 KB of redundancy. 8,240 bytes is the honest size of "I have read these pages".

## 2. What it does NOT buy, measured, and this is the important part

**Predicting a flag from a class scores 0/45 on never-seen programs.**

The literal store reduces to only **74 of 429** records carrying any substantive role pattern,
and the largest class (`compress`, 18 programs) has **consistency 0.33 across 7 distinct
patterns**. Averaging them produces a confident answer that is wrong. This is why the module
never predicts: it asks, or it abstains.

**And no name transfers.** Across two real hosts on the same machine:

```
/usr/bin   635 names
/usr/sbin  216 names
name overlap            3   (init, ip, rpcinfo)   = 1.4%
bytes already seen     17
```

So a store keyed on identity is worth **1.4%** on a host change. This is the user's own concern
— "his actions will probably never be needed again, because the environments are always
changing" — quantified, and it is worse than the intuition.

**And the derivation itself reaches almost nothing on this host.** On `/usr/sbin`, only **4 of
216** programs even mention a role word in their help output, and 2 state any flag at all.

## 3. So what IS the generalization that survives a host change?

Three things, and only three, and each is a *question*, not an *answer*:

1. **The scan.** "What is here" is derivable in 48 ms for 216 programs, every time, always
   correct, and stores nothing. This is `ABSENT`-capable: `/usr/sbin` ships **no** `gzip`,
   `bzip2`, `xz` or `tar`, and the system says so instead of recalling a program that isn't
   there. **Abstention is a first-class result and it is free.**
2. **The question.** A closed set of English role words that names what to look for. This is
   the entire stored vocabulary of the mechanism, and it says nothing about any program.
3. **The read-set.** The only thing worth remembering per environment, because it is what makes
   the second visit 253× cheaper.

Everything else — which program does what, what flag it uses — is **asked of the artifact**,
because the artifact is the only source that is right about the current build.

> The user's phrasing was "ask the right question and know all of the things that he should
> know about". The measurement refines it: **the question is the generalizable part; the answer
> is not.** Save the question. Re-derive the answer from the environment, which costs 0.05 s
> once the question is right and the page has been read.

## 4. What this does not yet do

- It has never been run on a host it did not have a shell on — no GUI, no browser, no network.
- The role vocabulary is 5 words and was chosen for a filesystem task family. A general
  environment needs the vocabulary derived, not chosen, and that is unsolved here.
- **4/216 is not "instant knowledge of an environment".** It is a working mechanism for one
  narrow question family, measured honestly, with its ceiling in plain sight.

`truth.achieved` remains `false`.
