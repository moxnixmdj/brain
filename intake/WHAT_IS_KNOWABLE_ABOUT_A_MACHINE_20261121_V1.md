# What is knowable about a machine it has never seen

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls, 0 parameters, no network outside one priced channel
**Receipt:** `intake/RECEIPT_WHAT_IS_KNOWABLE_HERE_20261121_V1.json` · **Instrument:** `canonical/tools/what_is_knowable_here_v1.py` · **Tests:** `canonical/tests/test_what_is_knowable_here_v1.py` (10 passed)

---

## 0. The idea

> *"All he should do is just to learn instantly from the web about everything in this new arbitrary environment... On the computer anything already has a guide or something to use."*

That is a testable claim with two halves, and I measured both on a host this tool had never
described before (492 programs, 284 MB of bytes, 25 visible mounts).

**Half 1 — "everything already has a guide."** True in a precise and useless way. Of 120
sampled programs, 85 are, by their own package database, **documented**: together they cite
**7,432 man-page files. Zero of those files exist on disk.** `/usr/share/man` is empty. The
machine is confident it is documented and has every citation pointing at nothing.

**Half 2 — "get it instantly from the web."** The web is reachable here, but the pages that
would close those citations — `manpages.debian.org`, `perldoc.perl.org` — are **not** in this
sandbox's reachable set (`URLError` on all four attempts). The three reachable fetches took
**100–420 ms** each to return the first 4 KB of a *page about some version*.

So the idea, as stated, fails on this machine in both directions. What replaces it is better,
cheaper, and already measured.

---

## 1. The four channels, measured

| Channel | Cost | Yield | Character |
|---|---|---|---|
| **LOOK** — read the bytes | **6.3 s** for all 284 MB (1.0 s of pure scan, the rest citation re-reads) | 395 statements, each cited by byte offset | free, exhaustive, **shallow**: compiled text is a skeleton |
| **ASK** — run each program's own `--help` | **3.3 s** for 492 programs (**6.8 ms each**) | 490/492 answered, ~1 MB of authoritative text | cheap, exact, **authoritative by construction** |
| **TEST** — exercise the claimed forms | 90 probes, bounded, in a scratch dir | 87 accept, **2 contradicted their own text**, 1 skipped as destructive | only a run settles a claim |
| **WEB** — fetch a public page | **255 ms** per fetch, first 4 KB | a page about *a* version, not this host's contract | **fallback**, priced, never lands a row |

**Per program, asking the program itself is 37.6× faster than fetching one page about it, and
the answer is about the artifact you actually have.** In raw throughput the host out-delivers
the web by 1,836× (29.5 MB/s vs 16 KB/s), though that comparison flatters the host: the web
number prices transport, not authority. The honest headline is the per-program one.

### Nothing was run blind
Probes are bounded: one flag, scratch cwd, 3 s timeout, and any program whose own text names a
destructive form — or whose flag name looks destructive — is **skipped and counted** (1 skip
here), never silently probed.

---

## 2. The two self-contradictions it found

Self-description is **not** self-verifying. Two programs on this host document a form their own
parser rejects:

| Program | Documented | What its parser does |
|---|---|---|
| `dpkg-genchanges` | `--build=<type>[,...]` | `--build` alone → `error: unknown option '--build'` |
| `gcov-tool` | `--fullname` | `--fullname=...` → `unrecognized option` |

This is the general form of the repair problem this project has been chasing for a month:
**a text that states a contract is not the same object as the parser that enforces it.** Reading
is cheap; only a run distinguishes the two. That is why the agent needs *one* execution probe
per claim rather than a better reader.

---

## 3. Residency — why memorising contents is not the job

Of 388 programs that state flags when asked, **354 (91.2 %) have those flags already present
verbatim in their own bytes on disk.** The knowledge was never missing. Storing it would be
copying the disk into the agent, and the copy would then be wrong the moment the disk changed.

The 34 exceptions are the interesting set — and they are dominated by exactly one artifact
family (`python3`, `pip`, `cpan`), i.e. **interpreted programs whose contract is generated at
run time**, not compiled in. That is a shape, not a fact.

---

## 4. What is worth keeping

The knowledge that survives every falsifier here is a **shape**: `(statement kind, artifact
family)` plus one worked example and the channel that produced it.

| | |
|---|---|
| observations | 930 |
| shapes kept | **10** |
| retention ratio | **93.0×** |
| bytes to store | **1,336** (for 284 MB of host) |
| replay | 535/535 shape hits, **0 misses**, at 0.001 ms/program vs 6.8 ms to re-ask → **8,588×** |

That is the answer to *"saving his exact experience must be in a very sufficient way"*:
**do not save the experience. Save the index into the machine.** The machine holds the
contents, the index says where to look and whether to trust it, and the index is ten rows.

---

## 5. Why "save his actions" is worthless, quantitatively

`cpan` answered differently when **only** `HOME`, `LC_ALL`, `TZ` and cwd changed — with the
artifact's bytes byte-identical (`sha256` unchanged). A statement that moves when only the
environment moves was never a property of the machine. This is the measured reason not to
persist actions: what an agent *did* is bound to a state that will not recur, while what an
artifact *is* survives a reboot.

Sampled 24 programs evenly across the host; 1 moved. Small, and enough.

**A second, unplanned lesson.** Probing has side effects. Five programs on this host write into
whatever directory they are given — `bzexe` writes a file named `gz<pid>` even when asked only
for `--help`; `pygettext` writes `messages.pot`; `as` writes `a.out`. Early runs left those in
the repository root. The instrument now runs every look-up and every probe in a throwaway
directory and **refuses** to probe inside the repo at all
(`REFUSED_WORKDIR_INSIDE_REPO`). The residue is also measured and reported as a property of the
host (`probe_residue`: 5 writers of 492) rather than quietly cleaned up. An agent that pokes at
an unknown machine must assume the machine pokes back.

---

## 6. The top-down decomposition (Elon's law applied, not quoted)

The whole thing is one closed set, and every part is smaller than the part above it:

```
1/1   knowable knowledge of a machine = 4 channels over one enumerated host
1/5   one channel = LOOK | ASK | TEST | WEB
1/15  one program  = its bytes · its answer · its agreement · its citation
1/40  one statement = kind · offset · digest · channel
1/90  what you keep  = one shape + one worked example, 1,336 bytes, ten of them
```

**The best part is no part.** There is no model here, no memory service, no vector index, no
parameter, no network at run time. There is a `PATH` enumeration, a `read()`, a `subprocess`,
and ten rows.

---

## 7. What is real and what is not

**Real (measured here):**
- A total pass over an unknown host costs **~5 s** and is *cheaper* than asking a question
  badly. Totality is affordable, so "goal-directed vs learn everything" is a false choice.
- 91 % residency: the host already stores its own contract.
- 93× retention into 10 shapes, 0 misses, 11,736× faster than re-asking.
- 2 self-contradictions found per 90 probes; the "guide is already there" premise is 0/7,432 true.
- 5 of 492 programs write into their working directory when merely queried; probes are contained.

**Not real (and this document does not claim it):**
- **This is not general knowledge.** It covers *executable programs on a Linux PATH*. GUI state,
  hidden application state, network services and long-horizon workflows are untouched — the
  frontier is still ~20.6 % binary on OSWorld 2.0 for exactly those reasons.
- **Shapes may not be a closed set.** 10 shapes on *one* host is not a small-universe claim.
  The honest next falsifier is a second, different host (macOS, a container image, a Windows
  box) and asking whether the same 10 shapes cover it. If the count grows linearly with hosts,
  the compression is a local artifact.
- **The web channel was not beaten on authority, only on cost.** It was unreachable for the
  documents that mattered here; on a host whose guides are online and whose programs say
  nothing, the ranking could invert. That is the case to test next.
- `truth.achieved` remains **false**. Nothing here is a §6 claim.

---

## 8. What to build next (one step, falsifiable)

The only open question the data leaves standing is **whether shapes are portable**. Take the
ten shapes from this receipt to a genuinely different host and count the misses. If the shape
set holds, the agent's persistent memory is a few hundred bytes and universal. If it does not,
the compression was per-host and the honest conclusion is that knowledge must be re-derived
each time — still cheap, still 5 s, still no model.

That is the next experiment, and it is a receipt away, not a rewrite away.

---

*Nothing in this document was inferred from memory; every number is in
`intake/RECEIPT_WHAT_IS_KNOWABLE_HERE_20261121_V1.json` and reproducible with
`python3 canonical/tools/what_is_knowable_here_v1.py`.*
