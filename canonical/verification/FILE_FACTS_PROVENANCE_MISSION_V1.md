# Mission: the two file-fact rows answer exactly, and refuse what they cannot read

Authority: NONE. This document describes what must be true for
`file.line_count.v1` and `file.stat.v1` to be executed by the front door. It
grants no capability credit, no benchmark credit and no terminal credit.

## Why the rows exist

Measured on `ec94c97` with 25 ordinary requests through
`canonical.runtime.live_brain_route_admission_v1.solve`: 1 served, 12 refused
with the computer-execution boundary, 6 misrouted, 6 unroutable.

The 12 refusals were not safety decisions. Instrumenting the door showed
`selected_capability: None` and an empty candidate list: routing proposed
nothing, and the boundary was the last tier answering for an absent row. The
registry had writers and extractors but no row that answers a question about a
file it only reads.

## What is required of the rows

1. `file.line_count.v1` returns the number of `str.splitlines()` elements of the
   decoded UTF-8 file, and refuses: a non-UTF-8 file, a directory, a missing
   file, and any path that does not resolve inside the repository.
2. `file.stat.v1` returns `size_bytes` and `permissions_octal` from metadata,
   and the size must follow the bytes on disk across two reads.
3. Neither adapter spawns a process, imports the target, or writes outside a
   declared `output_path` inside the repository.

## How compliance is decided

`canonical/runtime/verify_file_facts_provenance_v1.py` builds a world whose
answers are known by construction (five lines, three lines without a trailing
newline, zero lines, a known size, a known permission bit), computes the
expected answers itself with the standard library, reaches the adapters through
the real dispatcher, and compares. Its receipt records
`independent_personnel_verification: false` on purpose: the check is
independent of the adapter's code, not of its author. No stronger claim is made
anywhere.

The receipt is anchored to this file by `mission_path` and `mission_sha256`, so
a fabricated receipt would have to fabricate this document and its digest too.
