"""Fail-closed Root3 effect-class firewall for subprocess authorization.

This wrapper does not create semantic authority. It resolves the currently executing
subprocess call back to the exact content-addressed 29-site registry while the
Python caller stack is still live. Sites classified ARBITRARY_COMMAND_EXECUTION
are denied before the downstream canonical authorizer is called.

Unknown, missing, ambiguous, or drifted call-site identity also denies. All other
known classes are delegated unchanged to the downstream canonical authorizer.

The purpose is deletion, not proof-by-label: generic shell / generic CLI escape
hatches are excluded from credited runtime instead of pretending their arbitrary
child effects have been proved safe.
"""
from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from canonical.runtime.root3_subprocess_effect_class_registry_v1 import EXPECTED

SCHEMA = "PROJECT_BRAIN_ROOT3_SUBPROCESS_EFFECT_CLASS_FIREWALL_V1"
DENIED_CLASSES = frozenset({"ARBITRARY_COMMAND_EXECUTION"})
SUPPORTED_APIS = frozenset({"subprocess.run", "subprocess.Popen"})


class EffectClassFirewallError(RuntimeError):
    pass


def _normalize_repo_path(filename: str, repo_root: str | Path) -> str | None:
    if not isinstance(filename, str) or not filename or filename.startswith("<"):
        return None
    root = Path(repo_root).resolve()
    try:
        path = Path(filename).resolve()
        rel = path.relative_to(root)
    except (OSError, ValueError):
        return None
    return rel.as_posix()


def _live_frame_rows() -> list[dict[str, Any]]:
    """Capture only path/line metadata; do not retain frame objects."""
    rows: list[dict[str, Any]] = []
    frame = inspect.currentframe()
    try:
        if frame is not None:
            frame = frame.f_back
        while frame is not None:
            rows.append(
                {
                    "filename": frame.f_code.co_filename,
                    "lineno": int(frame.f_lineno),
                    "function": frame.f_code.co_name,
                }
            )
            frame = frame.f_back
    finally:
        del frame
    return rows


def resolve_effect_site(
    api: str,
    frame_rows: Iterable[Mapping[str, Any]],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if api not in SUPPORTED_APIS:
        raise EffectClassFirewallError("SUBPROCESS_API_UNSUPPORTED:" + str(api))

    matches: list[dict[str, Any]] = []
    for row in frame_rows:
        if not isinstance(row, Mapping):
            continue
        rel = _normalize_repo_path(str(row.get("filename") or ""), repo_root)
        if rel is None:
            continue
        try:
            lineno = int(row.get("lineno"))
        except (TypeError, ValueError):
            continue
        key = (rel, lineno, api)
        effect_class = EXPECTED.get(key)
        if effect_class is not None:
            matches.append(
                {
                    "module_path": rel,
                    "lineno": lineno,
                    "process_api": api,
                    "function": str(row.get("function") or ""),
                    "effect_class": effect_class,
                }
            )

    if not matches:
        raise EffectClassFirewallError("PROCESS_SITE_NOT_IN_FROZEN_EFFECT_REGISTRY")
    unique = {
        (m["module_path"], m["lineno"], m["process_api"], m["effect_class"])
        for m in matches
    }
    if len(unique) != 1:
        raise EffectClassFirewallError(
            "PROCESS_SITE_AMBIGUOUS:" + ",".join(
                f"{a}:{b}:{c}:{d}" for a, b, c, d in sorted(unique)
            )
        )
    return matches[0]


def make_effect_class_firewall(
    downstream_authorizer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    repo_root: str | Path,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    if not callable(downstream_authorizer):
        raise EffectClassFirewallError("DOWNSTREAM_AUTHORIZER_NOT_CALLABLE")
    root = Path(repo_root).resolve()

    def authorize(mediator_request: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            if not isinstance(mediator_request, Mapping):
                raise EffectClassFirewallError("MEDIATOR_REQUEST_NOT_MAPPING")
            api = mediator_request.get("api")
            if not isinstance(api, str):
                raise EffectClassFirewallError("MEDIATOR_API_INVALID")

            site = resolve_effect_site(
                api,
                _live_frame_rows(),
                repo_root=root,
            )
            effect_class = site["effect_class"]
            if effect_class in DENIED_CLASSES:
                return {
                    "schema": SCHEMA,
                    "allowed": False,
                    "reason": "EFFECT_CLASS_FORBIDDEN_FROM_CREDITED_RUNTIME:"
                    + effect_class,
                    "effect_class": effect_class,
                    "process_site": site,
                    "downstream_authorizer_called": False,
                    "acceptance_credit_delta": 0,
                }

            verdict = downstream_authorizer(mediator_request)
            if not isinstance(verdict, Mapping):
                raise EffectClassFirewallError(
                    "DOWNSTREAM_AUTHORIZER_RESULT_NOT_MAPPING"
                )
            out = dict(verdict)
            out["root3_effect_class"] = effect_class
            out["root3_process_site"] = site
            out["root3_effect_class_firewall"] = SCHEMA
            return out
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "allowed": False,
                "reason": type(exc).__name__ + ":" + str(exc),
                "downstream_authorizer_called": False,
                "acceptance_credit_delta": 0,
            }

    return authorize
