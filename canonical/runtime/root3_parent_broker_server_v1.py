from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any

from canonical.runtime.root3_broker_rpc_v1 import serve_loop
from canonical.runtime.root3_parent_driver_registry_v1 import dispatch

SCHEMA = "PROJECT_BRAIN_ROOT3_PARENT_BROKER_SERVER_V1"


class ParentBrokerServerError(RuntimeError):
    pass


def serve_fd(
    fd: int,
    *,
    repo_root: str | Path,
    authority_context: dict[str, str] | None = None,
    max_requests: int = 1024,
) -> dict[str, Any]:
    if not isinstance(fd, int) or isinstance(fd, bool) or fd < 0:
        raise ParentBrokerServerError("BROKER_FD_INVALID")
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ParentBrokerServerError("REPO_ROOT_INVALID")

    dup = os.dup(fd)
    sock = socket.socket(fileno=dup)
    try:
        loop = serve_loop(
            sock,
            lambda request: dispatch(
                root,
                request,
                authority_context=authority_context,
            ),
            max_requests=max_requests,
        )
    finally:
        sock.close()

    return {
        "schema": SCHEMA,
        "status": loop["status"],
        "requests_served": loop["requests_served"],
        "closed_driver_registry": True,
        "generic_effect_fallback": False,
        "terminal_credit_delta": 0,
    }
