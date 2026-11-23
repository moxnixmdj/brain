# The wall is not the algorithm: the documentation is not reachable

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls

---

## The decisive measurement

84 leak-free rows from GitChameleon — real prose written by someone who never saw the answer,
ground truth set by the benchmark. Corpus fetched from pypi for 16 unseen libraries.

```
truth present in the fetched corpus : 13/84   (15.5%)
truth in source but NO docstring    :  0/84
truth NOT in the sdist at all       : 71/84   (84.5%)

TOP-1 correct                       :  3/75   (4.0%)
```

**84.5% of the time the answer was never in the corpus.** No ranker can fix that. The 4.0% is not
a failure of ranking; it is a failure of *supply*.

---

## Why: the network is five hosts, and none of them is documentation

Measured, one by one:

| host | reachable |
|---|---|
| `pypi.org` | **OPEN** |
| `registry.npmjs.org` | **OPEN** |
| `github.com` | **OPEN** |
| `api.github.com` | **OPEN** (5,000 requests/hour, exhausted by one run) |
| `codeload.github.com` | **OPEN** |
| `docs.python.org` | **BLOCKED** |
| `docs.scipy.org` | **BLOCKED** |
| `numpy.org`, `pandas.pydata.org`, `librosa.org` | **BLOCKED** |
| `readthedocs.org` | **BLOCKED** |
| `en.wikipedia.org` | **BLOCKED** |
| `stackoverflow.com` | **BLOCKED** |
| `arxiv.org`, `raw.githubusercontent.com` | **BLOCKED** |

The public names of `numpy`, `scipy`, `pandas`, `librosa`, `torch` are documented on hosts that
are not reachable from this sandbox. That is why `log_ndtr` (a torch C-extension) and the librosa
beat functions never appeared: **the sdist ships code, the guide ships names, and the guide is
off.** PyPI's `description` field is a 4 KB blurb, not an index (measured: librosa's names 3
distinct, all from its citation block).

---

## What this does and does not change

**It does not change the algorithm.** Scan → know the gap → fetch → use is still sound. Three of
its four steps are measured working:

| step | status |
|---|---|
| scan | **works** — 216 programs, 48 ms |
| know what you don't know | **works** — 0 probes |
| fetch instantly | **works** — no quota, ~1 request/library, no model call |
| ground the goal | **blocked by supply, then 10–25%** |

**It changes what I can honestly claim.** "Instant knowledge from the web" is *demonstrated* for
the one artifact class this sandbox can reach — **package source on GitHub/PyPI** — and
**undemonstrated** for everything whose guide is a website. Since §6 requires behaviour on hosts
never seen, and the hardest hosts' guides are unreachable here, I cannot verify that claim from
this sandbox, and I will not report it as verified.

---

## The boundary, stated so it can be attacked

Not a constraint of the *system*; a constraint of the *recorder*:

> The system's fetch step is a function of which hosts answer. It has no privileged channel, and
> in this sandbox those hosts are five. On a real machine it would have the machine's own help
> pages (`--help`, `man`, `pydoc`, `inspect`) **plus** its network — and the local half is
> already built and measured (`scan_retrieve_fetch_v1`, 125/125 answers, 0 probes).

So the honest statement of capability is: **fetch works wherever the artifact can be asked.** On
`/usr/bin` it is measured sufficient. On a library whose only self-description is an HTML page,
it is blocked *here*, and the fix is a host list, not a mechanism.

---

## What I would build next, if the host list opened

One thing, and it is small: point `fetch_units` at `pydoc`/`inspect` on the *installed* library
instead of the sdist. `inspect.getmembers` + `__doc__` returns exactly the 84.5% the sdist
dropped, because an installed package has its C extensions and its full module tree. That is not
a new component; it is the same channel reading the artifact where the artifact actually lives.

**It cannot be measured here** — numpy/scipy/torch are not installed in this sandbox — so it stays
unproven, and stating it as a plan rather than a result is the whole point of this receipt.

---

## Status

`truth.achieved` = **`false`**. The one thing this session changed is that the failure is now
located precisely: **supply, not search** — and I can prove which, because the 71 missing truths
are *absent from the corpus entirely*, not ranked low in it.
