"""Runtime closed-world channel observer for strict composition execution.

This module is deliberately narrower than the material-effect authorization
stack.  It grants no authority and no acceptance credit.  Its job is to turn
ambient runtime state into content-bound evidence and to fail closed when an
action escapes into a channel whose returned evidence cannot yet be made
complete (network, child process, or native escape).

The strict proof subset currently mediates:
- file reads, including absence, by pre-read SHA-256;
- directory enumeration by a content-addressed entry manifest;
- file/directory mutations by pre/post state hashes;
- process environment and cwd by an ambient-state digest.

Network, subprocess/exec/spawn, and ctypes native escape are rejected while a
strict capture is active.  That is intentional: until their returned evidence
is content-bound end-to-end, allowing them would merely rename the C1 hole.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "PROJECT_BRAIN_COMPOSITION_RUNTIME_CHANNEL_GUARD_V1"

# Strict mode is intentionally small.  These actions execute entirely in the
# in-process deterministic dispatcher and their acceptance-relevant state is
# file/directory/env state observable by this guard.  Any action that can
# delegate to third-party code, a child process, network I/O, or native code is
# excluded until its own channel boundary is independently closed.
STRICT_C1_ACTION_TYPES = frozenset({
    "read_file",
    "list_tree",
    "search_text",
    "write_json_records",
    "assert_file_exists",
    "assert_json_fields_equal",
    "assert_text_contains_json_keys",
    "project_browser_result_json",
    "join_runtime_json_arrays",
    "assert_runtime_json_join",
    "aggregate_runtime_json_arrays",
    "assert_runtime_json_aggregate",
    "derive_grouped_records",
    "assert_grouped_derived_records",
    "select_ranked_record",
    "assert_ranked_record",
    "assert_hex_prefix_bucket",
    "assert_collection_length_bucket",
})


class CompositionChannelError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


_INTERNAL: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "project_brain_composition_channel_internal", default=False
)
_ACTIVE: contextvars.ContextVar["Capture | None"] = contextvars.ContextVar(
    "project_brain_composition_channel_capture", default=None
)
_HOOK_INSTALLED = False


@contextlib.contextmanager
def _internal() -> Iterator[None]:
    token = _INTERNAL.set(True)
    try:
        yield
    finally:
        _INTERNAL.reset(token)


def _safe_path_text(path: Any, root: Path) -> tuple[Path | None, str]:
    if isinstance(path, int) or path is None:
        return None, "fd:" + str(path)
    try:
        raw = os.fspath(path)
    except TypeError:
        return None, "unrepresentable:" + type(path).__name__
    if isinstance(raw, bytes):
        raw = os.fsdecode(raw)
    p = Path(raw)
    if not p.is_absolute():
        p = (root / p)
    try:
        resolved = p.resolve(strict=False)
    except Exception:
        resolved = p.absolute()
    try:
        rel = resolved.relative_to(root)
        label = "repo:" + rel.as_posix()
    except ValueError:
        label = "abs:" + str(resolved)
    return resolved, label


def _file_state(path: Path | None, label: str) -> dict[str, Any]:
    if path is None:
        return {
            "path": label,
            "exists": None,
            "regular_file": False,
            "sha256": None,
            "size": None,
        }
    with _internal():
        try:
            st = path.stat()
        except FileNotFoundError:
            return {
                "path": label,
                "exists": False,
                "regular_file": False,
                "sha256": None,
                "size": None,
            }
        except Exception as exc:
            return {
                "path": label,
                "exists": None,
                "regular_file": False,
                "sha256": None,
                "size": None,
                "error": type(exc).__name__,
            }
        is_file = stat.S_ISREG(st.st_mode)
        digest = None
        if is_file:
            try:
                digest = _sha256_file(path)
            except Exception as exc:
                return {
                    "path": label,
                    "exists": True,
                    "regular_file": True,
                    "sha256": None,
                    "size": st.st_size,
                    "error": type(exc).__name__,
                }
        return {
            "path": label,
            "exists": True,
            "regular_file": is_file,
            "sha256": digest,
            "size": st.st_size,
        }


def _repo_snapshot(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    with _internal():
        for p in sorted(root.rglob("*"), key=lambda x: str(x.relative_to(root))):
            rel = p.relative_to(root).as_posix()
            try:
                if p.is_symlink():
                    records.append({
                        "path": rel,
                        "kind": "symlink",
                        "target": os.readlink(p),
                    })
                elif p.is_dir():
                    records.append({"path": rel, "kind": "dir"})
                elif p.is_file():
                    st = p.stat()
                    records.append({
                        "path": rel,
                        "kind": "file",
                        "size": st.st_size,
                        "sha256": _sha256_file(p),
                    })
                else:
                    records.append({"path": rel, "kind": "other"})
            except Exception as exc:
                records.append({
                    "path": rel,
                    "kind": "unreadable",
                    "error": type(exc).__name__,
                })
    return {
        "entry_count": len(records),
        "sha256": _sha256_value(records),
    }


def _directory_state(path: Path | None, label: str) -> dict[str, Any]:
    if path is None:
        return {"path": label, "exists": None, "manifest_sha256": None}
    with _internal():
        try:
            entries = []
            for item in os.scandir(path):
                try:
                    st = item.stat(follow_symlinks=False)
                    mode = st.st_mode
                    kind = (
                        "file" if stat.S_ISREG(mode)
                        else "dir" if stat.S_ISDIR(mode)
                        else "symlink" if stat.S_ISLNK(mode)
                        else "other"
                    )
                    entries.append({
                        "name": item.name,
                        "kind": kind,
                        "size": st.st_size,
                        "mtime_ns": st.st_mtime_ns,
                    })
                except Exception as exc:
                    entries.append({
                        "name": item.name,
                        "kind": "unknown",
                        "error": type(exc).__name__,
                    })
            entries.sort(key=lambda x: x["name"])
            return {
                "path": label,
                "exists": True,
                "entry_count": len(entries),
                "manifest_sha256": _sha256_value(entries),
            }
        except FileNotFoundError:
            return {
                "path": label,
                "exists": False,
                "entry_count": 0,
                "manifest_sha256": None,
            }
        except Exception as exc:
            return {
                "path": label,
                "exists": None,
                "entry_count": None,
                "manifest_sha256": None,
                "error": type(exc).__name__,
            }


@dataclass
class Capture:
    repo_root: Path
    strict: bool = True
    action_type: str | None = None
    file_reads: dict[str, dict[str, Any]] = field(default_factory=dict)
    directory_reads: dict[str, dict[str, Any]] = field(default_factory=dict)
    mutation_pre: dict[str, dict[str, Any]] = field(default_factory=dict)
    mutation_paths: dict[str, Path | None] = field(default_factory=dict)
    forbidden_events: list[dict[str, Any]] = field(default_factory=list)
    ambient_input: dict[str, Any] = field(default_factory=dict)
    _finished: bool = False
    _receipt: dict[str, Any] | None = None

    def begin(self) -> None:
        if self.strict and self.action_type not in STRICT_C1_ACTION_TYPES:
            raise CompositionChannelError(
                "STRICT_C1_ACTION_TYPE_UNAUDITED:" + str(self.action_type)
            )
        env = {str(k): str(v) for k, v in os.environ.items()}
        self.ambient_input = {
            "cwd": str(Path.cwd().resolve()),
            "environment_sha256": _sha256_value(env),
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": sys.version,
            "repo_pre_state": _repo_snapshot(self.repo_root) if self.strict else None,
        }

    def _record_file_read(self, raw_path: Any) -> None:
        p, label = _safe_path_text(raw_path, self.repo_root)
        if label not in self.file_reads:
            state = _file_state(p, label)
            self.file_reads[label] = state
            if state.get("exists") is None or (
                state.get("exists") is True
                and state.get("regular_file") is True
                and not state.get("sha256")
            ):
                self._forbid("file.read_unbound", {"path": label})

    def _record_directory_read(self, raw_path: Any) -> None:
        p, label = _safe_path_text(raw_path, self.repo_root)
        if label not in self.directory_reads:
            state = _directory_state(p, label)
            self.directory_reads[label] = state
            if state.get("exists") is None:
                self._forbid("directory.read_unbound", {"path": label})

    def _record_mutation(self, raw_path: Any) -> None:
        p, label = _safe_path_text(raw_path, self.repo_root)
        if label not in self.mutation_pre:
            self.mutation_pre[label] = _file_state(p, label)
            self.mutation_paths[label] = p

    def _forbid(self, event: str, detail: dict[str, Any] | None = None) -> None:
        row = {"event": event, **(detail or {})}
        self.forbidden_events.append(row)
        if self.strict:
            raise CompositionChannelError("UNMEDIATED_RUNTIME_CHANNEL:" + event)

    def observe(self, event: str, args: tuple[Any, ...]) -> None:
        if event == "open":
            raw_path = args[0] if args else None
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else 0
            write_mode = isinstance(mode, str) and any(ch in mode for ch in "wax+")
            write_flags = isinstance(flags, int) and bool(
                flags
                & (
                    getattr(os, "O_WRONLY", 0)
                    | getattr(os, "O_RDWR", 0)
                    | getattr(os, "O_CREAT", 0)
                    | getattr(os, "O_TRUNC", 0)
                    | getattr(os, "O_APPEND", 0)
                )
            )
            if write_mode or write_flags:
                self._record_mutation(raw_path)
            else:
                self._record_file_read(raw_path)
            return

        if event in {"os.listdir", "os.scandir"}:
            self._record_directory_read(args[0] if args else ".")
            return

        if event in {"os.remove", "os.unlink", "os.rmdir", "os.mkdir"}:
            self._record_mutation(args[0] if args else None)
            return

        if event in {"os.rename", "os.replace"}:
            self._record_mutation(args[0] if args else None)
            self._record_mutation(args[1] if len(args) > 1 else None)
            return

        if event in {
            "os.chmod", "os.chown", "os.truncate", "os.utime",
            "os.symlink", "os.link",
        }:
            self._record_mutation(args[0] if args else None)
            return

        if (
            event == "subprocess.Popen"
            or event == "os.system"
            or event.startswith("os.exec")
            or event.startswith("os.spawn")
        ):
            self._forbid("process.spawn")
            return

        if event in {"socket.connect", "socket.bind"}:
            address = args[1] if len(args) > 1 else None
            self._forbid("network." + event.split(".", 1)[1], {"address": repr(address)})
            return

        if event in {"ctypes.dlopen", "ctypes.dlsym", "ctypes.dlsym/handle"}:
            self._forbid("native.escape")
            return

    def finish(self) -> dict[str, Any]:
        if self._finished and self._receipt is not None:
            return self._receipt
        mutations = []
        for label in sorted(self.mutation_pre):
            post = _file_state(self.mutation_paths[label], label)
            mutations.append({
                "path": label,
                "pre": self.mutation_pre[label],
                "post": post,
            })
        reads = [self.file_reads[k] for k in sorted(self.file_reads)]
        dirs = [self.directory_reads[k] for k in sorted(self.directory_reads)]
        body = {
            "schema": SCHEMA,
            "action_type": self.action_type,
            "strict_action_type_audited": self.action_type in STRICT_C1_ACTION_TYPES,
            "ambient_input": self.ambient_input,
            "repo_post_state": _repo_snapshot(self.repo_root) if self.strict else None,
            "file_reads": reads,
            "directory_reads": dirs,
            "mutations": mutations,
            "forbidden_events": list(self.forbidden_events),
        }
        body["file_and_ambient_inputs_content_bound"] = not self.forbidden_events
        body["network_response_evidence_complete"] = not any(
            str(x.get("event", "")).startswith("network.")
            for x in self.forbidden_events
        )
        body["child_process_state_excluded"] = not any(
            x.get("event") == "process.spawn" for x in self.forbidden_events
        )
        body["native_escape_excluded"] = not any(
            x.get("event") == "native.escape" for x in self.forbidden_events
        )
        body["closed_world_observed_subset"] = (
            not self.forbidden_events
            and body["strict_action_type_audited"]
            and (
                not self.strict
                or (
                    isinstance(self.ambient_input.get("repo_pre_state"), dict)
                    and isinstance(body.get("repo_post_state"), dict)
                )
            )
        )
        body["status"] = "PASS" if body["closed_world_observed_subset"] else "FAIL_CLOSED"
        body["acceptance_credit_delta"] = 0
        body["channel_manifest_sha256"] = _sha256_value(body)
        self._finished = True
        self._receipt = body
        return body


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    if _INTERNAL.get():
        return
    capture = _ACTIVE.get()
    if capture is None:
        return
    capture.observe(event, args)


def ensure_audit_hook() -> None:
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED:
        return
    sys.addaudithook(_audit_hook)
    _HOOK_INSTALLED = True


@contextlib.contextmanager
def capture_runtime_channels(
    repo_root: str | os.PathLike[str],
    *,
    strict: bool = True,
    action_type: str | None = None,
) -> Iterator[Capture]:
    ensure_audit_hook()
    cap = Capture(
        Path(repo_root).resolve(),
        strict=bool(strict),
        action_type=str(action_type) if action_type is not None else None,
    )
    cap.begin()
    token = _ACTIVE.set(cap)
    try:
        yield cap
    finally:
        _ACTIVE.reset(token)
        cap.finish()
