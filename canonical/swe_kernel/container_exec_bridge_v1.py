#!/usr/bin/env python3
"""Thread-local container-execution bridge for zero-LLM SWE verification inside Harbor containers.

Allows host-side deterministic SWE engines (Python / Go / JS-TS) to execute reproducers,
unit tests, and candidate-patch verifications inside the live task container's real runtime
(its installed Python virtualenv + pytest + repo deps, prewarmed Go module cache, and real
node_modules) while keeping every file overlay strictly transactional (backed up and
restored on every invocation) and strictly confined to the repo workdir (never /tests).
"""
from __future__ import annotations

import base64
import contextlib
import pathlib
import shlex
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping

_TLS = threading.local()


@dataclass
class ContainerToolchain:
    """Detected container-side language toolchains inside the live task environment."""

    workdir: str
    python_exe: str = ""
    has_pytest: bool = False
    go_exe: str = ""
    node_exe: str = ""
    vitest_bin: str = ""
    jest_bin: str = ""


@dataclass
class ContainerExecBridge:
    """Thread-safe transactional command runner inside a Harbor task container."""

    workdir: str
    host_root: pathlib.Path
    exec_fn: Callable[[str, float], tuple[int, str, str]]
    toolchain: ContainerToolchain
    calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _safe_rel(self, rel: str) -> str:
        norm = pathlib.PurePosixPath(rel.replace("\\", "/").lstrip("/"))
        if ".." in norm.parts or not norm.parts:
            raise ValueError(f"Unsafe overlay path: {rel!r}")
        return norm.as_posix()

    def collect_modified_overlays(self, candidate_root: pathlib.Path, *, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        """Compute files that differ between `candidate_root` (e.g. isolated temp copy) and `host_root`."""
        overlays: dict[str, str] = {}
        try:
            cand_res = candidate_root.resolve()
            host_res = self.host_root.resolve()
        except OSError:
            cand_res, host_res = candidate_root, self.host_root
        if cand_res != host_res:
            # Diff only small source files that exist in candidate_root vs host_root
            for p in cand_res.rglob("*"):
                if not p.is_file():
                    continue
                if any(part in (".git", "node_modules", "vendor", ".venv", "__pycache__") for part in p.parts):
                    continue
                if p.suffix.lower() not in (".py", ".go", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".c", ".h", ".cpp"):
                    continue
                rel = p.relative_to(cand_res).as_posix()
                hp = host_res / rel
                try:
                    c_bytes = p.read_bytes()
                    if not hp.is_file() or hp.read_bytes() != c_bytes:
                        overlays[rel] = c_bytes.decode("utf-8", errors="replace")
                except OSError:
                    continue
        if extra:
            for k, v in extra.items():
                overlays[self._safe_rel(k)] = v
        return overlays

    def run_cmd(
        self,
        cmd_shell: str,
        *,
        overlays: Mapping[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> tuple[int, str, str]:
        """Run `cmd_shell` inside `self.workdir`, transactionally applying and restoring `overlays`."""
        safe_overlays: dict[str, str] = {}
        for rel, content in (overlays or {}).items():
            safe_overlays[self._safe_rel(rel)] = content

        with self._lock:
            self.calls += 1
            if not safe_overlays:
                full_cmd = f"cd {shlex.quote(self.workdir)} && {cmd_shell}"
                return self.exec_fn(full_cmd, timeout_s)

            tok = uuid.uuid4().hex[:10]
            bak_dir = f"/tmp/.brain_ce_{tok}"
            setup_lines: list[str] = [f"set -e", f"mkdir -p {shlex.quote(bak_dir)}", f"cd {shlex.quote(self.workdir)}"]
            restore_lines: list[str] = [f"cd {shlex.quote(self.workdir)}"]

            for idx, (rel, content) in enumerate(safe_overlays.items()):
                qrel = shlex.quote(rel)
                qparent = shlex.quote(str(pathlib.PurePosixPath(rel).parent))
                qbak = shlex.quote(f"{bak_dir}/f_{idx}")
                qex = shlex.quote(f"{bak_dir}/ex_{idx}")
                b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
                setup_lines.append(
                    f"if [ -f {qrel} ]; then cp -p {qrel} {qbak} && touch {qex}; fi"
                )
                if qparent != "'.'":
                    setup_lines.append(f"mkdir -p {qparent}")
                setup_lines.append(f"printf %s {shlex.quote(b64)} | base64 -d > {qrel}")
                restore_lines.append(
                    f"if [ -f {qex} ]; then cp -p {qbak} {qrel}; else rm -f {qrel}; fi"
                )
            restore_lines.append(f"rm -rf {shlex.quote(bak_dir)}")

            # Single atomic bash invocation with trap EXIT so container repo is ALWAYS restored cleanly!
            restore_script = "; ".join(restore_lines)
            setup_script = "\n".join(setup_lines)
            wrapped = (
                f"bash -c {shlex.quote(f'cleanup() {{ {restore_script}; }}; trap cleanup EXIT; {setup_script}; set +e; {cmd_shell}; rc=$?; exit $rc')}"
            )
            return self.exec_fn(wrapped, timeout_s)


def get_active_bridge() -> ContainerExecBridge | None:
    return getattr(_TLS, "bridge", None)


@contextlib.contextmanager
def activate_bridge(bridge: ContainerExecBridge | None) -> Iterator[ContainerExecBridge | None]:
    prev = getattr(_TLS, "bridge", None)
    _TLS.bridge = bridge
    try:
        yield bridge
    finally:
        _TLS.bridge = prev


def probe_container_toolchain(
    workdir: str,
    exec_fn: Callable[[str, float], tuple[int, str, str]],
) -> ContainerToolchain:
    """Fast single-shell probe (<0.5s) discovering real python/pytest/go/node paths in the container."""
    probe_cmd = (
        f"cd {shlex.quote(workdir)} 2>/dev/null || true; "
        "PY=$(which python3 2>/dev/null || which python 2>/dev/null || true); "
        "for cand in /opt/conda/envs/*/bin/python /opt/conda/bin/python /testbed/.venv/bin/python /app/.venv/bin/python /venv/bin/python /root/.local/bin/python3; do "
        "  if [ -x \"$cand\" ] && \"$cand\" -c 'import pytest' 2>/dev/null; then PY=\"$cand\"; break; fi; "
        "done; "
        "HAS_PT=0; if [ -n \"$PY\" ] && \"$PY\" -c 'import pytest' 2>/dev/null; then HAS_PT=1; fi; "
        "GO=$(command -v go 2>/dev/null || ([ -x /usr/local/go/bin/go ] && echo /usr/local/go/bin/go) || true); "
        "NODE=$(command -v node 2>/dev/null || true); "
        "VT=$([ -x node_modules/.bin/vitest ] && echo node_modules/.bin/vitest || true); "
        "JT=$([ -x node_modules/.bin/jest ] && echo node_modules/.bin/jest || true); "
        "printf 'PY=%s\\nHAS_PT=%s\\nGO=%s\\nNODE=%s\\nVT=%s\\nJT=%s\\n' \"$PY\" \"$HAS_PT\" \"$GO\" \"$NODE\" \"$VT\" \"$JT\""
    )
    rc, out, _ = exec_fn(probe_cmd, 15.0)
    kv: dict[str, str] = {}
    if rc == 0 or "PY=" in out:
        for line in (out or "").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip()
    return ContainerToolchain(
        workdir=workdir,
        python_exe=kv.get("PY", ""),
        has_pytest=kv.get("HAS_PT", "0") == "1",
        go_exe=kv.get("GO", ""),
        node_exe=kv.get("NODE", ""),
        vitest_bin=kv.get("VT", ""),
        jest_bin=kv.get("JT", ""),
    )
