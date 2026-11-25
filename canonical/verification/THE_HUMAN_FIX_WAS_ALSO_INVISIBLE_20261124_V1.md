# The human fix was invisible too

**2026-11-24.** Measured with the trace hook used to pick the zip's target symbol.

## The number

For `httpx 7b19cd5f4b` — the maintainers' commit "Move utility functions from `_utils.py`
to `_client.py`", the cleanest multi-file propagation row in the 1200 commits I mined:

```
same_origin          executed during tests/:  NEVER
is_https_redirect    executed during tests/:  NEVER
port_or_default      executed during tests/:  NEVER
```

All three. The commit's entire subject line, executing zero times across 1389 tests.

## Why this is the real explanation

Three earlier observations now collapse into one cause:

1. My blind relocation scored **identically** to the human fix (28 failed / 1386 passed on
   both) — because no test distinguishes them.
2. The fix's own 17 new tests passed on my tree — because they test header behaviour, not
   the relocated predicates.
3. My first zip loop "converged" while corrupting `conftest.py` — because there was no
   visible debt to fail against.

I spent three attempts blaming my loop's mechanics. The mechanics were partly wrong, but
the deeper point is that **this row offers no evidence either way about propagation**.
A commit that moves three dead functions is a change the test suite cannot score.

## What this says about the corpus question

Wall 3 was described as "100-line patches across 4.1 files". Two separate failures had to
happen before the honest version appeared:

- **My corpus**: 0/45 commits touch more than one source file — unexamined, not solved.
- **This repo**: 9 multi-file commits in 1200, and the cleanest of them moves functions
  the suite never calls.

So "multi-file" and "tested by the suite" are close to orthogonal in real history too. A
maintainer reorganising code does not have to make the suite exercise it, and the suite
stays green while three functions become unreachable-by-test.

## The rule this leaves

> Propagation is only measurable where the moved code is **executed**. Everything from
> `62411c16`'s aliasing bug through the docstring relations through every store ablation to
> this row obeys the same law: **a green suite does not constrain what it never runs.**

The only reason the synthetic zip worked is that I chose the symbol *by executed call
count* (1891 for `_normalize_header_key`) instead of by convenience. That choice is the
whole difference between "586 failures → one hop → baseline" and "nothing observable".

## Environment note, logged once

GitHub became unreachable at the TLS layer mid-session:

```
git push          -> gnutls_handshake() failed
api.github.com    -> SSL_ERROR_SYSCALL
pypi.org          -> 200   (so it is host-specific, not a general outage)
```

DNS resolves. This is a sandbox network fault, not authentication. Commits are local on
`arena/94363358-brain` and preserved; the last five commits are unpushed. Nothing in the
work depends on the connection, so I continue rather than idle — but this branch is
**not backed up remotely** until the connection returns, and that is worth stating plainly
rather than burying.

## Ledger

| | value |
|---|---|
| corpus solved | 22/45 (unchanged — no new solve today) |
| zip demonstrated | yes, on a synthetic move with 1891 executed calls |
| zip on historical rows | no — the cleanest candidate moves dead code |
| §6 | not met; still no container, browser or GUI result |
