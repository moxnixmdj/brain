"""Harbor agent that drives the zero-model causal-angelic engine on real benchmark
containers (SWE-bench Pro V2 task format; the same code path works for any Harbor
task whose graded state lives in the container workdir).

Integrity design (read this before quoting any number from a run)
------------------------------------------------------------------
* The agent's ONLY inputs are (a) the container workdir tree, (b) the task
  instruction string Harbor hands to ``run()``, and (c) the engine's own
  external memory files (skill store / universal memory) given by explicit
  paths. The task directory -- which holds the hidden grading tests -- is never
  passed to, or readable by, the engine: the harness has no reference to it.
  Every report records the digests of exactly what the engine saw.
* ``model_calls == 0`` and ``cost_usd == 0.0`` are not aspirations here: the
  engine is a deterministic program (AST/CAFG search + spec replay). The agent
  writes those constants and the wall clock it measured.
* Nothing is reported as resolved by us. Resolution is decided exclusively by
  the task's own verifier (``tests/test.sh`` -> ``reward.txt``) running the
  official container image. The ``nop`` (empty patch) and ``oracle`` (reference
  patch) control arms in the workflow exist to prove that verifier is wired
  honestly: they must come back 0/N and N/N respectively, or no causal-engine
  number from that run is interpretable.
* Harbor import is optional so the pure helpers below stay unit-testable without
  the benchmark framework installed; the agent class degrades to a plain object
  in that case (it is only ever instantiated by Harbor).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping

# ---------------------------------------------------------------------------
# Harbor plumbing (optional at import time)
# ---------------------------------------------------------------------------

try:  # pragma: no cover - exercised only inside a Harbor trial
    from harbor.agents.base import BaseAgent as _BaseAgent

    _HAS_HARBOR = True
except Exception:  # pragma: no cover
    class _BaseAgent:  # type: ignore[no-redef]
        def __init__(self, logs_dir: pathlib.Path, model_name: str | None = None, **kwargs: Any) -> None:
            self.logs_dir = pathlib.Path(logs_dir)
            self.model_name = model_name

    _HAS_HARBOR = False


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2].parent

# Directories that are never part of a source patch and are huge in real repos.
TREE_EXCLUDES: tuple[str, ...] = (
    ".git",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".venv",
    "venv",
    ".tox",
    "coverage",
    ".next",
    ".turbo",
    "target",
    "vendor",
    ".gradle",
    ".terraform",
)

# Files above these limits are skipped: fail closed rather than thrash the runner.
MAX_FILE_BYTES = 1_500_000
MAX_TREE_BYTES = 400_000_000

_TEXT_SUFFIXES = frozenset(
    {
        ".py", ".pyi", ".go", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".java",
        ".kt", ".rb", ".php", ".rs", ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".mm",
        ".swift", ".scala", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".toml", ".yaml",
        ".yml", ".json", ".json5", ".md", ".txt", ".cfg", ".ini", ".html", ".css",
        ".scss", ".sql", ".proto", ".tf", ".gradle", ".xml", ".properties", ".vue",
        ".svelte", ".astro", ".pl", ".lua", ".r", ".jl", ".dart", ".ex", ".exs",
    }
)


class NetworkRefusedByHarness(RuntimeError):
    """Raised in place of an outbound connect while the harness has ``allow_web`` off.

    The engine is *told* it has no network (`inputs["allow_web"] = False`), and on one
    qutebrowser task that turned out to be a suggestion: a fallback path reached
    `urlopen`, the container-side proxy refused it, and the exception propagated out of
    the agent as a HARNESS_ERROR — so a capability question became a plumbing failure and
    the trial was scored 0 for the wrong reason.

    Enforcing the flag is the honest version of declaring it: nothing depends on remembering
    to check the flag at every call site, the count of refused attempts is reported, and the
    engine gets a typed error of its own language instead of a transport error. Covers
    in-process sockets and `urlopen`; a subprocess the engine spawns is its own process and
    is not covered, which is why the attempt count is an enforcement record, not a sandbox.
    """


def _is_local_endpoint(target: Any) -> bool:
    """Loopback and unix sockets are NOT the web.

    `allow_web` means 'no external knowledge', and the environment's own local services —
    a server the engine spawned itself, a DB on 127.0.0.1, a unix socket — are the thing
    the engine is supposed to probe, not a knowledge source. A guard that blocked these
    would quietly remove a capability instead of adding a constraint, so the rule is
    literal-address based (no DNS: resolving a name to decide is itself a lookup).
    """
    import ipaddress

    host: Any = target
    if isinstance(target, (tuple, list)) and target:
        host = target[0]
    if isinstance(host, (bytes, bytearray)):  # unix socket path
        return True
    if isinstance(host, str) and (host.startswith("/") or host.endswith(".sock")):
        return True  # AF_UNIX: a filesystem path, not an address
    if isinstance(host, str):
        h = host.strip("[]")
        if h == "localhost" or h.startswith("127.") or h == "::1":
            return True
        try:
            return ipaddress.ip_address(h).is_loopback
        except ValueError:
            return False
    return False  # unix socket objects pass a str/bytes address above; anything else: refuse


def network_guard(enabled: bool):
    """Context manager: refuse (and count) in-process outbound connects while enabled."""
    import contextlib
    import socket
    import urllib.parse
    import urllib.request

    attempts: list[str] = []
    if not enabled:

        @contextlib.contextmanager
        def _noop():
            yield

        return _noop(), attempts

    real_connect = socket.socket.connect
    real_create = socket.create_connection
    real_open = urllib.request.urlopen

    def _refuse_connect(self, *a, **k):  # noqa: ANN001 - monkeypatch target
        target = a[0] if a else None
        if _is_local_endpoint(target):
            return real_connect(self, *a, **k)
        attempts.append(f"socket.connect:{target!r}"[:160])
        raise NetworkRefusedByHarness("outbound connect refused: harness set allow_web=False")

    def _refuse_create(address, *a, **k):
        if _is_local_endpoint(address):
            return real_create(address, *a, **k)
        attempts.append(f"create_connection:{address!r}"[:160])
        raise NetworkRefusedByHarness("outbound connect refused: harness set allow_web=False")

    def _refuse_open(url, *a, **k):
        try:
            full = getattr(url, "full_url", url)
        except Exception:  # pragma: no cover - defensive against odd url objects
            full = url
        host = urllib.parse.urlparse(str(full)).hostname
        if _is_local_endpoint(host):
            return real_open(url, *a, **k)
        attempts.append(f"urlopen:{full!r}"[:160])
        raise NetworkRefusedByHarness("network fetch refused: harness set allow_web=False")

    @contextlib.contextmanager
    def _guard():
        socket.socket.connect = _refuse_connect  # type: ignore[method-assign]
        socket.create_connection = _refuse_create  # type: ignore[assignment]
        urllib.request.urlopen = _refuse_open  # type: ignore[assignment]
        try:
            yield
        finally:
            socket.socket.connect = real_connect  # type: ignore[method-assign]
            socket.create_connection = real_create  # type: ignore[assignment]
            urllib.request.urlopen = real_open  # type: ignore[assignment]

    return _guard(), attempts


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_is_included(rel_path: str) -> bool:
    """Whether a relative path is editable source we are allowed to touch."""
    parts = rel_path.split("/")
    if any(p in TREE_EXCLUDES for p in parts):
        return False
    name = parts[-1]
    if name in {".DS_Store", "package-lock.json", "yarn.lock", "go.sum", "poetry.lock"}:
        return False
    if name.startswith("."):
        return False
    suffix = "." + name.rsplit(".", 1)[1] if "." in name else ""
    return suffix in _TEXT_SUFFIXES


def snapshot_tree(root: pathlib.Path) -> dict[str, tuple[int, str]]:
    """Map included file rel-path -> (size, sha256). Ignores everything else."""
    out: dict[str, tuple[int, str]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in TREE_EXCLUDES]
        for fn in filenames:
            p = pathlib.Path(dirpath) / fn
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:  # pragma: no cover
                continue
            if not file_is_included(rel):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_size > MAX_FILE_BYTES or not st.st_size:
                continue
            try:
                raw = p.read_bytes()
            except OSError:
                continue
            if b"\x00" in raw[:4096]:
                continue
            out[rel] = (st.st_size, _sha256_bytes(raw))
    return out


def tree_digest(snap: Mapping[str, tuple[int, str]]) -> str:
    payload = "\n".join(f"{k}:{v[1]}" for k, v in sorted(snap.items()))
    return _sha256_bytes(payload.encode("utf-8"))


def diff_trees(before: Mapping[str, tuple[int, str]], after: Mapping[str, tuple[int, str]]) -> dict[str, list[str]]:
    """Classify edits: modified/added/removed rel-paths (removed = unsupported)."""
    modified = sorted(k for k in after.keys() & before.keys() if after[k] != before[k])
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    return {"modified": modified, "added": added, "removed": removed}


def extract_engine_edits(result: Mapping[str, Any]) -> dict[str, str]:
    """Pull ``{rel_path: source}`` edits out of an engine result, if it carries any.

    Used only as a fallback when the kernel reported edits instead of applying them
    to the workspace; a bare ``{}`` means "the engine changed the tree itself".
    """
    candidates: list[Mapping[str, Any]] = [result]
    inner = result.get("epistemic_result")
    if isinstance(inner, Mapping):
        candidates.insert(0, inner)
        for key in ("swe_result", "python_result", "blind_python"):
            sub = inner.get(key)
            if isinstance(sub, Mapping):
                candidates.append(sub)
    for src in candidates:
        for key in ("patched_files", "patch_files"):
            val = src.get(key)
            if isinstance(val, Mapping) and val:
                return {str(k): str(v) for k, v in val.items()}
    return {}


def apply_edits(tree: pathlib.Path, edits: Mapping[str, str], *, before: Mapping[str, tuple[int, str]]) -> list[str]:
    """Write reported edits into `tree`, refusing deletions and foreign paths."""
    written: list[str] = []
    for rel, source in edits.items():
        rel_norm = rel.replace("\\", "/").lstrip("/")
        if rel_norm.startswith("..") or "/" not in rel_norm and not file_is_included(rel_norm):
            continue
        if not file_is_included(rel_norm):
            continue
        target = tree / rel_norm
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
            written.append(rel_norm)
        except OSError:
            continue
    return written


def load_store(path: str | pathlib.Path | None) -> tuple[dict[str, Any], str]:
    """Load the external skill store. Returns (store, provenance_note).

    Never fabricates history: a missing file yields a genuinely empty store; a
    file that fails schema validation yields an empty store plus an explicit note
    that is written into the run report, so a corrupted store can never be
    mistaken for "the system had no skills".
    """
    from canonical.runtime import instant_swe_skill_store_v1 as SKILL_STORE

    fresh = SKILL_STORE.new_store()
    if not path:
        return fresh, "NO_STORE_PATH"
    p = pathlib.Path(path)
    if not p.is_file():
        return fresh, "STORE_FILE_ABSENT"
    try:
        return SKILL_STORE.load_store(p), "STORE_LOADED"
    except Exception as exc:
        return fresh, f"STORE_UNREADABLE_FRESH:{type(exc).__name__}"


def save_store(store: Mapping[str, Any], path: str | pathlib.Path | None) -> bool:
    """Persist the store; a write failure must never discard real edits."""
    if not path:
        return False
    from canonical.runtime import instant_swe_skill_store_v1 as SKILL_STORE

    try:
        SKILL_STORE.save_store(store, pathlib.Path(path))
        return True
    except Exception:
        return False


def run_engine_on_tree(
    tree: pathlib.Path,
    instruction: str,
    *,
    store_path: str | pathlib.Path | None = None,
    memory_path: str | pathlib.Path | None = None,
    ablate_store: bool = False,
    timeout_s: float = 900.0,
    python_exe: str | None = None,
    solver: Callable[..., dict[str, Any]] | None = None,
    inputs_allow_web: bool = False,
) -> dict[str, Any]:
    """Run the un-gated engine on a downloaded copy of a repo tree.

    ``solver`` exists purely so tests can inject a stand-in for the kernel; the
    production path calls ``open_model().solve(..., mode="EPISTEMIC")``.
    """
    t0 = time.monotonic()
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    store_note = "STORE_ABLATED" if ablate_store else ""
    store: dict[str, Any] | None = None
    if not ablate_store:
        store, store_note = load_store(store_path)
    before = snapshot_tree(tree)

    guard, net_attempts = network_guard(not inputs_allow_web)

    inputs: dict[str, Any] = {
        "workspace": str(tree),
        "python_exe": python_exe or sys.executable,
        # one source of truth: the guard enforces exactly what the engine is told
        "allow_web": bool(inputs_allow_web),  # default False: zero-knowledge house
        "timeout_s": float(timeout_s),
    }
    if memory_path:
        inputs["memory_path"] = str(memory_path)
    if store is not None:
        inputs["skill_store"] = store

    with guard:
        if solver is not None:
            result = solver(instruction=instruction, tree=tree, inputs=inputs)
        else:
            from canonical.runtime.brain_unified_model_v1 import open_model

            result = open_model().solve(instruction[:40000], inputs=inputs, mode="EPISTEMIC")

    edits_reported = extract_engine_edits(result if isinstance(result, Mapping) else {})
    applied_by = "tree-mutation"
    if edits_reported:
        after_probe = snapshot_tree(tree)
        if diff_trees(before, after_probe) == {"modified": [], "added": [], "removed": []}:
            written = apply_edits(tree, edits_reported, before=before)
            applied_by = "harness-apply" if written else "none"

    after = snapshot_tree(tree)
    diff = diff_trees(before, after)
    n_skills_before = len((store or {}).get("skills") or {})
    store_saved = False
    if store is not None and store_path:
        store_saved = save_store(store, store_path)

    return {
        "engine_result_status": str((result or {}).get("status") or "UNKNOWN"),
        "engine_pass": bool((result or {}).get("pass")),
        "changed": diff,
        "edits_applied_by": applied_by,
        "tree_bytes_before": sum(v[0] for v in before.values()),
        "n_files_tracked": len(after),
        "model_calls": 0,
        "cost_usd": 0.0,
        "seconds": round(time.monotonic() - t0, 3),
        "store_ablated": bool(ablate_store),
        "skills_in_store_after": len(((store or {}).get("skills") or {})) if store is not None else 0,
        "skills_newly_admissible": len((store or {}).get("skills") or {}) - n_skills_before,
        "store_note": store_note or "NO_STORE",
        "store_saved": store_saved,
        "timeout_s": float(timeout_s),
        "allow_web": bool(inputs_allow_web),
        # Field names the shard collector reads. They are aliases of data already
        # computed above, not new measurement: without them the report showed
        # tree_changed=None and fell back to harbor's timestamps for wall time.
        "network_attempts": len(net_attempts),
        "network_attempt_samples": net_attempts[:3],
        "network_guard": "enforced" if not inputs_allow_web else "open",
        "tree_changed": bool(diff.get("modified") or diff.get("added") or diff.get("removed")),
        "wall_seconds": round(time.monotonic() - t0, 3),
        "notes": [
            f"store: {store_note or 'NO_STORE'}",
            f"engine said: {str((result or {}).get('status') or 'UNKNOWN')}",
        ]
        + [str(s) for s in (((result or {}).get("explanation") or "") .split("\n") if isinstance((result or {}).get("explanation"), str) else [])][:3],
    }


class CausalEngineAgent(_BaseAgent):  # type: ignore[misc,valid-type]
    """Harbor agent: download tree -> engine -> upload the engine's edits."""

    def __init__(
        self,
        logs_dir: pathlib.Path,
        model_name: str | None = None,
        *,
        store_path: str | None = None,
        memory_path: str | None = None,
        ablate_store: bool = False,
        agent_timeout_s: float = 900.0,
        max_tree_bytes: int = MAX_TREE_BYTES,
        default_workdir: str = "/app",
        **kwargs: Any,
    ) -> None:
        super().__init__(logs_dir=logs_dir, model_name=model_name, **kwargs)
        self.store_path = store_path
        self.memory_path = memory_path
        self.ablate_store = bool(ablate_store)
        self.agent_timeout_s = float(agent_timeout_s)
        self.max_tree_bytes = int(max_tree_bytes)
        self.default_workdir = str(default_workdir)

    @staticmethod
    def name() -> str:  # pragma: no cover - Harbor registry hook
        return "causal_engine"

    def version(self) -> str:  # pragma: no cover
        return "1.0.0"

    async def setup(self, environment: Any) -> None:  # pragma: no cover
        return None

    async def run(self, instruction: str, environment: Any, context: Any) -> None:
        report = await self._run_trial(instruction, environment)
        try:
            (self.logs_dir / "causal_engine_report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
            )
        except OSError:
            pass
        if context is not None:
            context.cost_usd = 0.0
            context.n_input_tokens = 0
            context.n_output_tokens = 0
            context.n_cache_tokens = 0
            context.metadata = {
                "causal_engine": {
                    k: v
                    for k, v in report.items()
                    if k not in {"changed"}
                }
            }

    async def _run_trial(self, instruction: str, environment: Any) -> dict[str, Any]:  # pragma: no cover
        t0 = time.monotonic()
        workdir = self.default_workdir
        try:
            pwd = await environment.exec("pwd", timeout_sec=30)
            got = (getattr(pwd, "stdout", "") or "").strip()
            if got.startswith("/"):
                workdir = got
        except Exception:
            pass

        tmp = pathlib.Path(tempfile.mkdtemp(prefix="causal_engine_tree_"))
        tree = tmp / "repo"
        report: dict[str, Any] = {
            "workdir": workdir,
            "instruction_sha256": _sha256_bytes(instruction.encode("utf-8"))[:32],
            "store_path": self.store_path,
            "memory_path": self.memory_path,
            "store_ablated": self.ablate_store,
            "model_calls": 0,
            "cost_usd": 0.0,
        }
        try:
            await environment.download_dir_with_exclusions(
                source_dir=workdir, target_dir=str(tree), exclude=list(TREE_EXCLUDES)
            )
            snap = snapshot_tree(tree)
            nbytes = sum(v[0] for v in snap.values())
            report["tree_bytes"] = nbytes
            report["tree_digest_before"] = tree_digest(snap)
            if not snap:
                report["status"] = "EMPTY_TREE"
                return report
            if nbytes > self.max_tree_bytes:
                report["status"] = "TREE_TOO_BIG"
                return report

            rep = run_engine_on_tree(
                tree,
                instruction,
                store_path=self.store_path,
                memory_path=self.memory_path,
                ablate_store=self.ablate_store,
                timeout_s=self.agent_timeout_s,
            )
            report.update({k: v for k, v in rep.items() if k != "changed"})
            changed = rep["changed"]
            report["changed"] = changed
            if changed["removed"]:
                report["unsupported_removals"] = changed["removed"][:20]

            targets = changed["modified"] + changed["added"]
            uploaded = 0
            fallback_used = 0
            upload_failures: list[str] = []
            for rel in targets:
                src_file = tree / rel
                dst = f"{workdir}/{rel}"
                try:
                    await environment.upload_file(source_path=str(src_file), target_path=dst)
                    uploaded += 1
                except Exception:
                    # Permission-walled repos: retry once as root through exec, and
                    # say so in the report rather than quietly dropping the edit.
                    if await self._force_upload(environment, src_file, dst):
                        uploaded += 1
                        fallback_used += 1
                    else:
                        upload_failures.append(rel)
            report["uploaded_files"] = uploaded
            report["upload_fallback_root_exec"] = fallback_used
            report["upload_failures"] = upload_failures[:20]
            if uploaded:
                report["status"] = "EDITS_UPLOADED"
            elif upload_failures:
                report["status"] = "UPLOAD_BLOCKED"
            else:
                report["status"] = "NO_EDITS"
            return report
        except Exception as exc:  # never fake a fix: record the failure and stop
            report["status"] = "HARNESS_ERROR"
            report["error"] = f"{type(exc).__name__}: {exc}"[:400]
            return report
        finally:
            report["wall_seconds"] = round(time.monotonic() - t0, 3)
            shutil.rmtree(tmp, ignore_errors=True)


    async def _force_upload(self, environment: Any, src: pathlib.Path, dst: str) -> bool:  # pragma: no cover
        """Last-resort write path: base64 through ``exec(user='root')``."""
        import base64
        import shlex

        try:
            payload = base64.b64encode(pathlib.Path(src).read_bytes()).decode("ascii")
        except OSError:
            return False
        parent = dst.rsplit("/", 1)[0] or "/"
        tmp_b64 = f"/tmp/.causal_engine_upload_{os.getpid()}.b64"
        try:
            await environment.exec(f"mkdir -p {shlex.quote(parent)}", user="root", timeout_sec=60)
            await environment.exec(f": > {shlex.quote(tmp_b64)}", user="root", timeout_sec=60)
            chunk = 90_000
            for i in range(0, len(payload), chunk):
                await environment.exec(
                    f"printf %s '{payload[i : i + chunk]}' >> {shlex.quote(tmp_b64)}",
                    user="root",
                    timeout_sec=120,
                )
            res = await environment.exec(
                f"base64 -d {shlex.quote(tmp_b64)} > {shlex.quote(dst)} "
                f"&& chmod 644 {shlex.quote(dst)} && rm -f {shlex.quote(tmp_b64)}",
                user="root",
                timeout_sec=120,
            )
            return int(getattr(res, "return_code", 1) or 0) == 0
        except Exception:
            return False


def describe_harness() -> dict[str, Any]:  # pragma: no cover - introspection helper
    return {
        "harbor_available": _HAS_HARBOR,
        "agent_import_path": "canonical.eval.harbor.swebench_pro_v2_agent:CausalEngineAgent",
        "tree_excludes": list(TREE_EXCLUDES),
        "max_file_bytes": MAX_FILE_BYTES,
        "max_tree_bytes": MAX_TREE_BYTES,
        "model_calls": 0,
    }
