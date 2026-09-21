# Project Brain Canonical

This directory is the provider-independent canonical control plane for Project Brain.

## Authority model

- **GitHub (this private repository):** canonical human/auditable state, manifests, event history, laws, hashes, and pointers.
- **Google Drive:** immutable binary/evidence mirror for large snapshots and artifacts.
- **SQLite:** active working authority/cache. It must be reconstructable from canonical evidence and must never be the only durable source.
- **Execution providers:** replaceable and non-canonical. Val Town, browser providers, agent platforms, CI, and model surfaces may execute work but cannot define canonical truth by themselves.

## Current sealed snapshot

- Snapshot: `PROJECT_BRAIN_CANONICAL_SNAPSHOT_2026-09-21.zip`
- SHA-256: `000606bc93206eea18b3046c0f6536f1bc3c5b3272c47b410fdecc37c01b0162`
- Bytes: 42,353,579
- Embedded canonical-state SHA-256: `5da4d719127b0ddbb6c4d878c3a27eaa75a7e25fec7aae55600e2567549d1762`
- Google Drive mirror file ID: `1Z3j5g21evQwIP8Eq0YpOd4FL33gvqS1x`

## Current frontier

- Astra non-global predicates: 48/51 PROVEN, 3 UNPROVEN.
- `RECOVERY-ASTRA-HOTPATH-REPROVE-V2`: COMPLETE.
- `RECOVERY-ASTRA-HOTPATH-VERIFY-V2`: COMPLETE.
- `RECOVERY-ASTRA-FRESH-SUCCESSOR-BUILD-V1`: COMPLETE.
- `RECOVERY-ASTRA-FRESH-SUCCESSOR-VERIFY-V1`: COMPLETE.
- `RECOVERY-ASTRA-HIDDEN-EXECUTE-V1`: READY.
- Super-Worker real population remains 0 pending whole-definition independent qualification.

## Non-negotiable law

Provider loss, suspension, deletion, outage, or account failure must not destroy canonical truth or prevent reconstruction.

Val Town is not canonical. If legitimate access returns, its retained data is reconciled as evidence and it may be used as an executor only.
