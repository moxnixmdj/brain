from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

POLICY_SCHEMA = "PROJECT_BRAIN_MATERIAL_EFFECT_POLICY_V1"
REQUIRED_PREDICATES = frozenset({
    "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
})


class EffectDenied(RuntimeError):
    pass


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\\0".encode("ascii") + data).hexdigest()


def git_blob_sha_file(path: Path) -> str:
    return git_blob_sha(path.read_bytes())


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class Authorization:
    rule_id: str
    channel: str
    action_sha256: str
    allowed_sinks: frozenset[str]
    allowed_path_prefixes: tuple[Path, ...]
    allowed_network_hosts: frozenset[str]


_ACTIVE_AUTH: contextvars.ContextVar[Authorization | None] = contextvars.ContextVar(
    "project_brain_material_effect_authorization", default=None
)


class ReferenceMonitor:
    """Fail-closed, exact-action material-effect reference monitor.

    This runtime grants no acceptance credit by itself. It only provides the
    executable substrate required by the complete-mediation proof route.
    """

    def __init__(self, *, repo_root: str | os.PathLike[str], runtime_path: str, policy_path: str) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runtime_path = self._repo_path(runtime_path)
        self.policy_path = self._repo_path(policy_path)
        self.runtime_git_blob_sha = git_blob_sha_file(self.runtime_path)
        self.policy = self._load_json(self.policy_path)
        self._rules: dict[tuple[str, str], Authorization] = {}
        self._admin_roots: tuple[Path, ...] = ()
        self._validate_policy()

    def _repo_path(self, rel: str | os.PathLike[str]) -> Path:
        p = (self.repo_root / Path(rel)).resolve()
        if not _inside(p, self.repo_root):
            raise EffectDenied("PATH_ESCAPES_REPO")
        return p

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise EffectDenied(f"JSON_LOAD_FAILED:{path.name}:{type(exc).__name__}") from exc
        if not isinstance(value, dict):
            raise EffectDenied(f"JSON_OBJECT_REQUIRED:{path.name}")
        return value

    def _verify_receipt(
        self,
        spec: dict[str, Any],
        *,
        expected_action_sha256: str | None,
        admin: bool,
    ) -> None:
        rel = str(spec.get("path") or "")
        expected_blob = str(spec.get("git_blob_sha") or "").lower()
        if not rel or len(expected_blob) != 40:
            raise EffectDenied("RECEIPT_CONTENT_ADDRESS_REQUIRED")
        path = self._repo_path(rel)
        raw = path.read_bytes()
        if git_blob_sha(raw) != expected_blob:
            raise EffectDenied("RECEIPT_BLOB_MISMATCH")
        try:
            receipt = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise EffectDenied("RECEIPT_JSON_INVALID") from exc
        if not isinstance(receipt, dict):
            raise EffectDenied("RECEIPT_OBJECT_REQUIRED")
        for key in ("proved", "scope_complete", "independent_or_objective"):
            if receipt.get(key) is not True:
                raise EffectDenied(f"RECEIPT_{key.upper()}_NOT_TRUE")
        if str(receipt.get("runtime_git_blob_sha") or "").lower() != self.runtime_git_blob_sha:
            raise EffectDenied("RECEIPT_RUNTIME_BINDING_MISMATCH")
        predicates = frozenset(str(x) for x in (receipt.get("predicate_ids") or []))
        if not REQUIRED_PREDICATES.issubset(predicates):
            raise EffectDenied("RECEIPT_PREDICATE_SCOPE_INCOMPLETE")
        if admin:
            if receipt.get("administrative_state_writes_zero_critical_violation") is not True:
                raise EffectDenied("ADMIN_RECEIPT_ZERO_VIOLATION_NOT_TRUE")
        else:
            if receipt.get("zero_critical_violations") is not True:
                raise EffectDenied("RECEIPT_ZERO_VIOLATION_NOT_TRUE")
            if expected_action_sha256 is None:
                raise EffectDenied("EXPECTED_ACTION_HASH_REQUIRED")
            if str(receipt.get("action_sha256") or "").lower() != expected_action_sha256:
                raise EffectDenied("RECEIPT_ACTION_BINDING_MISMATCH")

    def _validate_policy(self) -> None:
        p = self.policy
        if p.get("schema") != POLICY_SCHEMA:
            raise EffectDenied("POLICY_SCHEMA_INVALID")
        runtime = p.get("runtime") or {}
        rel_runtime = str(self.runtime_path.relative_to(self.repo_root)).replace("\\", "/")
        if str(runtime.get("path") or "") != rel_runtime:
            raise EffectDenied("POLICY_RUNTIME_PATH_MISMATCH")
        if str(runtime.get("git_blob_sha") or "").lower() != self.runtime_git_blob_sha:
            raise EffectDenied("POLICY_RUNTIME_BLOB_MISMATCH")
        required = frozenset(str(x) for x in (p.get("required_predicate_ids") or []))
        if not REQUIRED_PREDICATES.issubset(required):
            raise EffectDenied("POLICY_REQUIRED_PREDICATES_INCOMPLETE")

        admin = p.get("administrative_state") or {}
        roots = admin.get("allowed_repo_prefixes") or []
        if not isinstance(roots, list) or not roots:
            raise EffectDenied("ADMIN_ROOTS_REQUIRED")
        self._admin_roots = tuple(self._repo_path(str(x)) for x in roots)
        self._verify_receipt(admin.get("receipt") or {}, expected_action_sha256=None, admin=True)

        rules = p.get("rules")
        if not isinstance(rules, list):
            raise EffectDenied("POLICY_RULES_REQUIRED")
        for raw_rule in rules:
            if not isinstance(raw_rule, dict):
                raise EffectDenied("POLICY_RULE_OBJECT_REQUIRED")
            rule_id = str(raw_rule.get("id") or "")
            channel = str(raw_rule.get("channel") or "")
            action_sha = str(raw_rule.get("action_sha256") or "").lower()
            if not rule_id or not channel or len(action_sha) != 64:
                raise EffectDenied("POLICY_RULE_IDENTITY_INVALID")
            key = (channel, action_sha)
            if key in self._rules:
                raise EffectDenied("POLICY_DUPLICATE_RULE")
            predicates = frozenset(str(x) for x in (raw_rule.get("predicate_ids") or []))
            if not REQUIRED_PREDICATES.issubset(predicates):
                raise EffectDenied("POLICY_RULE_PREDICATE_SCOPE_INCOMPLETE")
            self._verify_receipt(
                raw_rule.get("receipt") or {},
                expected_action_sha256=action_sha,
                admin=False,
            )
            sinks = frozenset(str(x) for x in (raw_rule.get("allowed_sinks") or []))
            if not sinks:
                raise EffectDenied("POLICY_RULE_SINKS_REQUIRED")
            prefixes = tuple(
                self._repo_path(str(x))
                for x in (raw_rule.get("allowed_repo_prefixes") or [])
            )
            hosts = frozenset(
                str(x).lower() for x in (raw_rule.get("allowed_network_hosts") or [])
            )
            self._rules[key] = Authorization(
                rule_id, channel, action_sha, sinks, prefixes, hosts
            )

    def authorize(self, channel: str, payload: Any) -> Authorization:
        action_sha = sha256_json(payload)
        auth = self._rules.get((str(channel), action_sha))
        if auth is None:
            raise EffectDenied(f"NO_EXACT_AUTHORIZATION:{channel}:{action_sha}")
        return auth

    @contextlib.contextmanager
    def activate(self, channel: str, payload: Any) -> Iterator[Authorization]:
        auth = self.authorize(channel, payload)
        token = _ACTIVE_AUTH.set(auth)
        try:
            yield auth
        finally:
            _ACTIVE_AUTH.reset(token)

    def require_sink(
        self,
        sink_kind: str,
        *,
        path: str | os.PathLike[str] | None = None,
        network_host: str | None = None,
    ) -> Authorization:
        auth = _ACTIVE_AUTH.get()
        if auth is None:
            if path is not None and sink_kind.startswith("file."):
                p = Path(path)
                p = (self.repo_root / p).resolve() if not p.is_absolute() else p.resolve()
                if any(_inside(p, root) for root in self._admin_roots):
                    return Authorization(
                        "ADMINISTRATIVE_STATE_RECEIPT",
                        "administrative_state",
                        "",
                        frozenset({"file.*"}),
                        self._admin_roots,
                        frozenset(),
                    )
            raise EffectDenied(f"MATERIAL_EFFECT_WITHOUT_AUTHORIZATION:{sink_kind}")

        if sink_kind not in auth.allowed_sinks and "*" not in auth.allowed_sinks:
            raise EffectDenied(f"SINK_NOT_AUTHORIZED:{sink_kind}:{auth.rule_id}")
        if path is not None:
            p = Path(path)
            p = (self.repo_root / p).resolve() if not p.is_absolute() else p.resolve()
            if not auth.allowed_path_prefixes or not any(
                _inside(p, root) for root in auth.allowed_path_prefixes
            ):
                raise EffectDenied(f"PATH_NOT_AUTHORIZED:{auth.rule_id}")
        if network_host is not None:
            host = str(network_host).lower()
            if not auth.allowed_network_hosts or host not in auth.allowed_network_hosts:
                raise EffectDenied(f"NETWORK_HOST_NOT_AUTHORIZED:{host}:{auth.rule_id}")
        return auth


def classify_audit_event(event: str, args: tuple[Any, ...]) -> tuple[str | None, dict[str, Any]]:
    if event == "open":
        path = args[0] if args else None
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
        return ("file.open_write", {"path": path}) if (write_mode or write_flags) else (None, {})
    if event in {"os.remove", "os.unlink"}:
        return "file.remove", {"path": args[0] if args else None}
    if event in {"os.rename", "os.replace"}:
        return "file.rename", {"path": args[1] if len(args) > 1 else None}
    if event in {"os.mkdir", "os.rmdir"}:
        return "file.directory_mutation", {"path": args[0] if args else None}
    if event in {"os.chmod", "os.chown", "os.truncate", "os.utime", "os.symlink", "os.link"}:
        return "file.metadata_or_link_mutation", {"path": args[0] if args else None}
    if event == "subprocess.Popen" or event == "os.system" or event.startswith("os.exec") or event.startswith("os.spawn"):
        return "process.spawn", {}
    if event == "socket.connect":
        address = args[1] if len(args) > 1 else None
        host = address[0] if isinstance(address, tuple) and address else None
        return "network.connect", {"network_host": host}
    if event == "socket.bind":
        address = args[1] if len(args) > 1 else None
        host = address[0] if isinstance(address, tuple) and address else None
        return "network.bind", {"network_host": host}
    if event in {"ctypes.dlopen", "ctypes.dlsym", "ctypes.dlsym/handle"}:
        return "native.escape", {}
    return None, {}
