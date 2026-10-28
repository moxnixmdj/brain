#!/usr/bin/env python3
"""Real-time progress streaming for hardcore software engineering.

Provides WebSocket + Server-Sent Events (SSE) streaming of execution progress
during long-running SWE operations (patch search, test gates, fault
localization, distributed task execution).

Architecture:
  * EventBus — in-memory pub/sub; components publish ProgressEvent dicts.
  * StreamingHub — manages WebSocket and SSE subscribers, broadcasts events.
  * ProgressAdapter — hooks into astra_runtime goal execution to emit events.
  * HTTP server (aiohttp) exposing /events (SSE) and /ws (WebSocket).

Usage:
    from canonical.runtime.progress_streaming_v1 import hub, emit
    hub.start(host="0.0.0.0", port=8766)  # non-blocking
    emit("swe.stage.started", stage="fault_localization", ...)

Clients connect to http://host:8766/events (SSE) or ws://host:8766/ws.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = "PROJECT_BRAIN_PROGRESS_STREAMING_V1"

# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

class EventBus:
    """In-memory pub/sub for progress events.

    Subscribers are async callables receiving (event_type, payload).
    History is bounded so new subscribers get recent context.
    """

    def __init__(self, history_size: int = 500):
        self._subscribers: dict[str, list[Callable]] = {}
        self._history: deque[tuple[str, dict[str, Any]]] = deque(
            maxlen=history_size
        )
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str,
                  callback: Callable[[str, dict[str, Any]], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    def subscribe_all(self,
                      callback: Callable[[str, dict[str, Any]], None]) -> None:
        self._subscribers.setdefault("*", []).append(callback)

    def emit(self, event_type: str,
             payload: dict[str, Any] | None = None) -> None:
        payload = dict(payload or {})
        payload["_event_type"] = event_type
        payload["_ts"] = __import__("time").time()
        self._history.append((event_type, payload))

        # Fire-and-forget to subscribers (they're sync callbacks)
        for cb in list(self._subscribers.get(event_type, [])):
            try:
                cb(event_type, payload)
            except Exception:
                pass
        for cb in list(self._subscribers.get("*")):
            try:
                cb(event_type, payload)
            except Exception:
                pass

    def recent(self, since_ts: Optional[float] = None
               ) -> list[tuple[str, dict[str, Any]]]:
        if since_ts is None:
            return list(self._history)
        return [(et, p) for et, p in self._history if p.get("_ts", 0) >= since_ts]


bus = EventBus()


def emit(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Module-level emit convenience."""
    bus.emit(event_type, payload)


# ---------------------------------------------------------------------------
# Streaming hub (WebSocket + SSE)
# ---------------------------------------------------------------------------

class StreamingHub:
    """Manages WebSocket and SSE subscribers; broadcasts events from the bus."""

    def __init__(self, bus: EventBus = bus):
        self.bus = bus
        self._ws_subscribers: set[Any] = set()  # websockets.WebSocketServerProtocol
        self._sse_queues: dict[str, asyncio.Queue] = {}
        self._server: Optional[asyncio.Server] = None
        self._http_runner: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Bridge: forward bus events to streaming subscribers
        bus.subscribe_all(self._forward_event)

    def _forward_event(self, event_type: str,
                       payload: dict[str, Any]) -> None:
        msg = json.dumps({"schema": SCHEMA, "type": event_type, **payload})
        # WebSocket broadcast (thread-safe: use loop.call_soon_threadsafe)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return
        for ws in list(self._ws_subscribers):
            try:
                loop.call_soon_threadsafe(
                    asyncio.ensure_future, self._ws_send(ws, msg)
                )
            except Exception:
                self._ws_subscribers.discard(ws)
        # SSE queues
        for qid, q in list(self._sse_queues.items()):
            try:
                loop.call_soon_threadsafe(q.put_nowait, msg)
            except Exception:
                self._sse_queues.pop(qid, None)

    async def _ws_send(self, ws: Any, msg: str) -> None:
        try:
            await ws.send(msg)
        except Exception:
            self._ws_subscribers.discard(ws)

    # -- WebSocket handler ----------------------------------------------------

    async def _ws_handler(self, ws: Any, path: str) -> None:
        import websockets  # type: ignore
        self._ws_subscribers.add(ws)
        try:
            # Send recent history on connect
            for et, p in self.bus.recent():
                try:
                    await ws.send(json.dumps({"schema": SCHEMA,
                                              "type": et, **p}))
                except Exception:
                    break
            # Keep connection alive; ignore inbound messages
            async for _ in ws:
                pass
        except websockets.ConnectionClosed:  # type: ignore[attr-defined]
            pass
        finally:
            self._ws_subscribers.discard(ws)

    # -- SSE handler ----------------------------------------------------------

    async def _sse_handler(self, request: Any) -> Any:
        import aiohttp.web  # type: ignore
        qid = str(uuid.uuid4())
        q: asyncio.Queue[str] = asyncio.Queue()
        self._sse_queues[qid] = q

        async def stream():
            # Send recent history first
            for et, p in self.bus.recent():
                yield f"data: {json.dumps({'schema': SCHEMA, 'type': et, **p})}\n\n"
            # Stream new events
            try:
                while True:
                    msg = await q.get()
                    yield f"data: {msg}\n\n"
                    q.task_done()
                    if q.empty() and q.qsize() == 0:
                        await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                self._sse_queues.pop(qid, None)
                raise

        return aiohttp.web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )  # placeholder; actual response built in _start_http

    async def _sse_handler_actual(self, request: Any) -> Any:
        import aiohttp.web  # type: ignore
        qid = str(uuid.uuid4())
        q: asyncio.Queue[str] = asyncio.Queue()
        self._sse_queues[qid] = q

        resp = aiohttp.web.StreamResponse()
        resp.content_type = "text/event-stream"
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Connection"] = "keep-alive"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        await resp.prepare(request)

        try:
            for et, p in self.bus.recent():
                line = json.dumps({"schema": SCHEMA, "type": et, **p})
                await resp.write(f"data: {line}\n\n".encode())
            while True:
                msg = await q.get()
                await resp.write(f"data: {msg}\n\n".encode())
                q.task_done()
        except (asyncio.CancelledError, ConnectionError, OSError):
            pass
        finally:
            self._sse_queues.pop(qid, None)
            try:
                await resp.write_eof()
            except Exception:
                pass
        return resp

    # -- HTTP server (aiohttp) ------------------------------------------------

    async def _start_http(self, host: str, port: int) -> None:
        import aiohttp.web  # type: ignore
        app = aiohttp.web.Application()
        app.router.add_get("/events", self._sse_handler_actual)
        app.router.add_get("/ws", self._ws_handler)
        app.router.add_get("/health", lambda r: aiohttp.web.json_response(
            {"status": "ok", "schema": SCHEMA}
        ))
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, host, port)
        await site.start()
        self._http_runner = runner  # type: ignore[assignment]

    # -- lifecycle ------------------------------------------------------------

    def start(self, host: str = "0.0.0.0", port: int = 8766) -> None:
        """Start the streaming HTTP server non-blocking.

        Runs the aiohttp server on a background thread with its own event loop.
        Safe to call from synchronous code (e.g. inside astra_runtime).
        """
        import threading

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_http(host, port))
            loop.run_forever()

        t = threading.Thread(target=_run, daemon=True, name="pb-streaming-hub")
        t.start()

    def stop(self) -> None:
        """Stop the streaming hub (best-effort)."""
        self._ws_subscribers.clear()
        self._sse_queues.clear()


hub = StreamingHub()


# ---------------------------------------------------------------------------
# Progress adapter: hooks into astra_runtime goal execution
# ---------------------------------------------------------------------------

class ProgressAdapter:
    """Emits progress events for SWE execution stages.

    Call these from within goal action handlers (or wrap _goal_action) to
    stream real-time progress to connected clients.
    """

    def __init__(self, hub: StreamingHub = hub, bus: EventBus = bus):
        self.hub = hub
        self.bus = bus

    def stage_started(self, goal_id: str, stage: str,
                      detail: dict[str, Any] | None = None) -> None:
        emit("swe.stage.started", {
            "goal_id": goal_id, "stage": stage, **(detail or {}),
        })

    def stage_progress(self, goal_id: str, stage: str,
                       processed: int, total: int,
                       detail: dict[str, Any] | None = None) -> None:
        pct = (processed / total * 100) if total else 0.0
        emit("swe.stage.progress", {
            "goal_id": goal_id, "stage": stage,
            "processed": processed, "total": total,
            "percent": round(pct, 1), **(detail or {}),
        })

    def stage_completed(self, goal_id: str, stage: str,
                        result: dict[str, Any] | None = None) -> None:
        emit("swe.stage.completed", {
            "goal_id": goal_id, "stage": stage, **(result or {}),
        })

    def stage_failed(self, goal_id: str, stage: str,
                     error: str,
                     detail: dict[str, Any] | None = None) -> None:
        emit("swe.stage.failed", {
            "goal_id": goal_id, "stage": stage, "error": error,
            **(detail or {}),
        })

    def candidate_evaluated(self, goal_id: str,
                            candidate_index: int,
                            test_results: dict[str, Any]) -> None:
        emit("swe.patch.candidate_evaluated", {
            "goal_id": goal_id,
            "candidate_index": candidate_index,
            "test_results": test_results,
        })

    def fault_found(self, goal_id: str,
                    source_file: str,
                    suspiciousness: float) -> None:
        emit("swe.fault.found", {
            "goal_id": goal_id, "source_file": source_file,
            "suspiciousness": suspiciousness,
        })

    def patch_verified(self, goal_id: str,
                       patch_hash: str,
                       verified: bool) -> None:
        emit("swe.patch.verified", {
            "goal_id": goal_id, "patch_hash": patch_hash, "verified": verified,
        })

    def goal_completed(self, goal_id: str,
                       final_result: dict[str, Any]) -> None:
        emit("swe.goal.completed", {
            "goal_id": goal_id, "result": final_result,
        })


# ---------------------------------------------------------------------------
# Streaming consumer — consumes progress events from the event bus
# ---------------------------------------------------------------------------

class StreamingConsumer:
    """Consumes progress events from the event bus.

    Subscribes to all events and queues them for consumption. Use this to
    drive a dashboard, CLI tail, or IDE plugin that shows real-time SWE
    repair progress.
    """

    def __init__(self, bus: EventBus = bus):
        self.bus = bus
        self._queue: list[tuple[str, dict[str, Any]]] = []
        self._subscribed = False

    def start(self) -> None:
        """Subscribe to all bus events."""
        if not self._subscribed:
            self.bus.subscribe_all(self._on_event)
            self._subscribed = True

    def stop(self) -> None:
        """Best-effort unsubscribe (bus has no unsubscribe; clear queue)."""
        self._queue.clear()

    def _on_event(self, event_type: str,
                  payload: dict[str, Any]) -> None:
        self._queue.append((event_type, dict(payload)))

    def consume(self, timeout_s: float | None = None
                ) -> list[tuple[str, dict[str, Any]]]:
        """Return all consumed events since the last call, clearing the queue."""
        events = list(self._queue)
        self._queue.clear()
        return events

    def tail(self, since_ts: float | None = None
             ) -> list[tuple[str, dict[str, Any]]]:
        """Return recent history from the bus (useful for late joiners)."""
        return self.bus.recent(since_ts)


consumer = StreamingConsumer()


def stream_events(goal_id: str | None = None,
                  timeout_s: float | None = None
                  ) -> list[tuple[str, dict[str, Any]]]:
    """Convenience: consume all pending progress events.

    If ``goal_id`` is given, only events for that goal are returned.
    """
    consumer.start()
    events = consumer.consume(timeout_s)
    if goal_id is not None:
        events = [(et, p) for et, p in events
                  if p.get("goal_id") == goal_id]
    return events


def stream_events_goal(goal_id: str,
                       timeout_s: float | None = None
                       ) -> list[tuple[str, dict[str, Any]]]:
    """Consume all pending progress events for a specific goal."""
    return stream_events(goal_id=goal_id, timeout_s=timeout_s)


adapter = ProgressAdapter()
