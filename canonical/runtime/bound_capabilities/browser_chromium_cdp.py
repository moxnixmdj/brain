#!/usr/bin/env python3
"""Brain-owned rendered browser adapter using the existing Chromium CDP route.

The registered browser capability used to require a separate ChromeDriver
binary. Brain already owns Chromium and the declarative CDP surface, so this
adapter reuses browser_v1 and OSWorld's BrowserCDP implementation directly.
Playwright is a protocol driver only; all task decisions and verification
remain in Brain-owned code.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
from collections.abc import Mapping
import venv
from urllib.parse import urlparse

HERE = pathlib.Path(__file__).resolve().parent
RUNTIME = HERE.parent
LAUNCH = RUNTIME / "browser_launch_v1.sh"
BUILD = pathlib.Path(os.environ.get("BRAIN_BROWSER_BUILD", str(pathlib.Path.home() / "browser_build"))).expanduser()
PYTHON_ENV = BUILD / "brain-python"


def _safe_path(root: pathlib.Path, raw: object) -> pathlib.Path:
    path = (root / str(raw or "")).resolve()
    base = root.resolve()
    if path == base or base not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return path


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _site_packages() -> pathlib.Path:
    return PYTHON_ENV / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"


def _activate_playwright() -> None:
    """Make the browser protocol driver available to this Python runtime.

    Install into a dedicated venv under the external browser build directory,
    not into Brain's source tree or the OS-managed interpreter. Reuse it on
    subsequent actions.
    """
    try:
        import playwright.sync_api  # noqa: F401
        return
    except ImportError:
        pass

    interpreter = PYTHON_ENV / "bin" / "python"
    if not interpreter.exists():
        PYTHON_ENV.parent.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True).create(PYTHON_ENV)
    check = subprocess.run([str(interpreter), "-c", "import playwright.sync_api"],
                           capture_output=True, text=True)
    if check.returncode != 0:
        install = subprocess.run(
            [str(interpreter), "-m", "pip", "install", "--disable-pip-version-check", "playwright"],
            capture_output=True, text=True, timeout=180,
        )
        if install.returncode != 0:
            raise RuntimeError("PLAYWRIGHT_SETUP_FAILED:" + (install.stderr or install.stdout)[-1200:])
    site = _site_packages()
    if not site.is_dir():
        raise RuntimeError("PLAYWRIGHT_SITE_PACKAGES_MISSING")
    sys.path.insert(0, str(site))
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("PLAYWRIGHT_IMPORT_FAILED_AFTER_SETUP") from exc


def _stop_port(port: str) -> None:
    marker = "--remote-debugging-port=" + str(port)
    try:
        raw = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True,
                             text=True, timeout=5).stdout
    except Exception:
        return
    for line in raw.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or marker not in fields[1] or "chromium" not in fields[1].lower():
            continue
        try:
            pid = int(fields[0])
            if pid != os.getpid():
                os.kill(pid, signal.SIGTERM)
        except (ValueError, ProcessLookupError, PermissionError):
            pass


def _load_interaction_module():
    import importlib.util

    path = HERE / "browser_chromedriver_interact.py"
    spec = importlib.util.spec_from_file_location("brain_browser_interaction_actions", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("BROWSER_INTERACTION_SCRIPT_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_state_conditioned_browser(args: dict, root_path: pathlib.Path, url: str, actions: list,
                                  screenshot_path: pathlib.Path, result_path: pathlib.Path) -> dict:
    """Run Brain's existing observe-act-observe policy against live Chromium."""
    if str(RUNTIME) not in sys.path:
        sys.path.insert(0, str(RUNTIME))
    from types import SimpleNamespace
    from canonical.runtime import browser_v1
    from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent
    from canonical.runtime.osworld_v21_generic_policy_v1 import decide, _search_value
    from canonical.runtime.osworld_v21_host_browser_ops_v1 import OSWorldHostBrowser
    from playwright.sync_api import sync_playwright

    goal = str(args.get("adaptive_goal") or "").strip()
    query = _search_value(goal)
    if not goal or not query:
        raise RuntimeError("BROWSER_STATE_POLICY_SEARCH_GOAL_UNBOUND")
    port = str(_free_port())
    parsed = urlparse(url)
    if not (BUILD / "chromium").is_file():
        pins = browser_v1.spki_pins(parsed.hostname, parsed.port or 443) if parsed.scheme == "https" else []
        if parsed.scheme == "https" and not pins:
            raise RuntimeError("BROWSER_TLS_PIN_UNAVAILABLE:" + str(parsed.hostname))
        env = dict(os.environ)
        env["BRAIN_BROWSER_BUILD"] = str(BUILD)
        env["CHROMIUM_SPKI_PINS"] = ",".join(pins)
        env.pop("CHROMIUM_INSECURE", None)
        launched = subprocess.run(["sh", str(LAUNCH), port], cwd=root_path,
                                  env=env, capture_output=True, text=True, timeout=180)
        ok, why = launched.returncode == 0, (launched.stdout + launched.stderr)[-1000:]
    elif parsed.scheme == "https":
        ok, why = browser_v1.ensure([parsed.hostname], port=port)
    else:
        ok, why = browser_v1.start(port=port)
    if not ok:
        raise RuntimeError("BROWSER_START_FAILED:" + why)

    class _NoGuest:
        def bind_environment(self, environment):
            self.environment = environment

        def run(self, operations):
            raise RuntimeError("BROWSER_POLICY_UNEXPECTED_GUEST_OPERATION")

    endpoint = f"http://127.0.0.1:{port}"
    agent = BrainOSWorldAgent(
        decide,
        policy_id="brain-generic-state-conditioned-browser-v1",
        browser_controller=OSWorldHostBrowser(),
        guest_controller=_NoGuest(),
    )
    agent.bind_environment(SimpleNamespace(vm_ip="127.0.0.1", chromium_port=int(port)))

    def current_screenshot() -> bytes:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint)
            pages = [page for context in browser.contexts for page in context.pages]
            if not pages:
                raise RuntimeError("BROWSER_PAGE_MISSING_FOR_POLICY")
            return pages[-1].screenshot(type="png", full_page=True, timeout=30000)

    terminal = False
    try:
        for _ in range(12):
            _, outer_actions = agent.predict(goal, {"screenshot": current_screenshot()})
            receipt = agent.history[-1] if agent.history else {}
            if outer_actions == ["DONE"]:
                terminal = receipt.get("response") == "search result state observed"
                break
            # BROWSER_OP actions are executed by BrainOSWorldAgent and return
            # WAIT to the outer GUI protocol. A WAIT with no browser receipt is
            # a policy abstention; it cannot make progress by looping.
            if not isinstance(receipt.get("browser_result"), Mapping):
                break
        final_observation = next((
            row.get("browser_result") for row in reversed(agent.history)
            if isinstance(row.get("browser_result"), Mapping)
            and row["browser_result"].get("type") == "OBSERVE"
        ), None)
        if not terminal or not isinstance(final_observation, Mapping):
            raise RuntimeError("BROWSER_STATE_POLICY_DID_NOT_VERIFY_SEARCH_RESULT")
        text = str(final_observation.get("visible_text") or "")
        if query.casefold() not in text.casefold():
            raise RuntimeError("BROWSER_STATE_POLICY_RESULT_TEXT_MISSING_QUERY")
        final_url = str(final_observation.get("active_url") or "")
        title = str(final_observation.get("active_title") or "")
        png = current_screenshot()
        if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png) <= 100:
            raise RuntimeError("SCREENSHOT_INVALID")
        submitted = [
            row.get("submitted_operation") for row in agent.history
            if isinstance(row.get("submitted_operation"), Mapping)
        ]
        action_trace = [{
            "response": row.get("response"),
            "submitted_operation": row.get("submitted_operation"),
            "browser_result": row.get("browser_result"),
            "screenshot_sha256": row.get("screenshot_sha256"),
        } for row in agent.history]
        screenshot_path.write_bytes(png)
        result = {
            "schema": "PROJECT_BRAIN_STATE_CONDITIONED_BROWSER_RESULT_V1",
            "source_url": url,
            "final_url": final_url,
            "page_title": title,
            "query": query,
            "observed_text": text[:200000],
            "policy_id": agent.policy_id,
            "action_trace": action_trace,
            "operations_completed": len(submitted),
            "screenshot_path": screenshot_path.relative_to(root_path).as_posix(),
            "screenshot_sha256": hashlib.sha256(png).hexdigest(),
            "screenshot_bytes": len(png),
            "model_dependency_count": 0,
        }
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        mutation_types = {str((op or {}).get("type") or "").upper() for op in submitted}
        return {
            "adapter": "browser_chromium_cdp_state_policy",
            "source_url": url,
            "final_url": final_url,
            "page_title": title,
            "text": text,
            "query": query,
            "operations_completed": len(submitted),
            "result_path": result_path.relative_to(root_path).as_posix(),
            "screenshot_path": screenshot_path.relative_to(root_path).as_posix(),
            "screenshot_sha256": result["screenshot_sha256"],
            "screenshot_bytes": len(png),
            "rendered": True,
            "interaction_verified": "PRESS" in mutation_types and any(
                kind.startswith("FILL_") for kind in mutation_types
            ),
            "output_verified": bool(text.strip() and len(png) > 100),
            "model_dependency_count": 0,
        }
    finally:
        _stop_port(port)


def _run_browser(args: dict, root_path: pathlib.Path, url: str, actions: list,
                 screenshot_path: pathlib.Path, result_path: pathlib.Path) -> dict:
    if str(RUNTIME) not in sys.path:
        sys.path.insert(0, str(RUNTIME))
    from canonical.runtime import browser_v1

    parsed = urlparse(url)
    port = str(_free_port())
    if not (BUILD / "chromium").is_file():
        pins = browser_v1.spki_pins(parsed.hostname, parsed.port or 443) if parsed.scheme == "https" else []
        if parsed.scheme == "https" and not pins:
            raise RuntimeError("BROWSER_TLS_PIN_UNAVAILABLE:" + parsed.hostname)
        env = dict(os.environ)
        env["BRAIN_BROWSER_BUILD"] = str(BUILD)
        env["CHROMIUM_SPKI_PINS"] = ",".join(pins)
        env.pop("CHROMIUM_INSECURE", None)
        launched = subprocess.run(["sh", str(LAUNCH), port], cwd=root_path,
                                  env=env, capture_output=True, text=True, timeout=180)
        ok = launched.returncode == 0
        why = (launched.stdout + launched.stderr)[-1000:]
    elif parsed.scheme == "https":
        ok, why = browser_v1.ensure([parsed.hostname], port=port)
    else:
        ok, why = browser_v1.start(port=port)
    if not ok:
        raise RuntimeError("BROWSER_START_FAILED:" + why)
    browser = None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            live_pages = [page for context in browser.contexts for page in context.pages]
            if not live_pages:
                raise RuntimeError("BROWSER_PAGE_MISSING_FOR_NAVIGATION")
            page = live_pages[0]
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            interaction_module = _load_interaction_module()
            trace = []
            for index, action in enumerate(actions):
                if action.get("type") == "wait":
                    seconds = max(0.0, min(float(action.get("seconds", 0.5)), 5.0))
                    page.wait_for_timeout(int(seconds * 1000))
                    result = {"ok": True, "type": "wait", "seconds": seconds}
                else:
                    script = interaction_module._ACTION_SCRIPT
                    original = "const action=arguments[0] || {};"
                    if original not in script:
                        raise RuntimeError("BROWSER_ACTION_SCRIPT_SHAPE_CHANGED")
                    script = script.replace(original, "const action=payload || {};", 1)
                    before_url = page.url
                    result = page.evaluate("payload => {" + script + "}", action)
                    if action.get("type") in {"click", "submit"}:
                        if action.get("type") == "submit":
                            try:
                                page.wait_for_url(lambda current: current != before_url, timeout=15000)
                            except Exception:
                                pass
                        try:
                            page.wait_for_load_state("load", timeout=15000)
                        except Exception:
                            pass
                trace.append({"index": index, "action": action, "result": result})
                if not isinstance(result, dict) or result.get("ok") is not True:
                    raise RuntimeError("BROWSER_ACTION_FAILED:" + str(index) + ":" + json.dumps(result)[:1000])
            elements = page.locator(
                "a,button,input,textarea,select,[role=button],[role=link],[contenteditable=true],[tabindex]"
            ).evaluate_all("""els => els.filter(e => {
                const r=e.getBoundingClientRect(), s=getComputedStyle(e);
                return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none';
            }).slice(0,240).map((e,i) => ({i,tag:(e.tagName||'').toLowerCase(),
                role:e.getAttribute('role')||'',type:e.getAttribute('type')||'',
                text:(e.innerText||e.textContent||'').trim().slice(0,240),
                aria:e.getAttribute('aria-label')||'',placeholder:e.getAttribute('placeholder')||'',
                name:e.getAttribute('name')||'',value:('value' in e?String(e.value):'').slice(0,240),
                href:e.getAttribute('href')||'',checked:('checked' in e?Boolean(e.checked):null),
                disabled:Boolean(e.disabled)}))""")
            final_url = page.url
            title = page.title()
            page_info = {"url": final_url, "title": title, "elements": elements}
            png = page.screenshot(type="png", full_page=True, timeout=30000)
            body_text = page.locator("body").inner_text(timeout=10000)
            browser.close()
            browser = None

        if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png) <= 100:
            raise RuntimeError("SCREENSHOT_INVALID")
        if not final_url or not title or not body_text.strip():
            raise RuntimeError("PAGE_CONTENT_NOT_VERIFIED")
        screenshot_path.write_bytes(png)
        result = {
            "schema": "PROJECT_BRAIN_RENDERED_BROWSER_RESULT_V1",
            "source_url": url,
            "final_url": final_url,
            "page_title": title,
            "observed_text": body_text[:200000],
            "page_snapshot": page_info,
            "action_trace": trace,
            "actions_completed": len(trace),
            "screenshot_path": screenshot_path.relative_to(root_path).as_posix(),
            "screenshot_sha256": hashlib.sha256(png).hexdigest(),
            "screenshot_bytes": len(png),
        }
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {
            "adapter": "browser_chromium_cdp",
            "source_url": url,
            "final_url": final_url,
            "page_title": title,
            "text": body_text,
            "actions_completed": len(trace),
            "result_path": result_path.relative_to(root_path).as_posix(),
            "screenshot_path": screenshot_path.relative_to(root_path).as_posix(),
            "screenshot_sha256": result["screenshot_sha256"],
            "screenshot_bytes": len(png),
            "rendered": True,
            "interaction_verified": bool(trace) and all(
                (item.get("result") or {}).get("ok") is True for item in trace
            ),
            "output_verified": bool(body_text.strip() and len(png) > 100),
        }
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        _stop_port(port)


def run(args: dict, root: str | pathlib.Path) -> dict:
    root_path = pathlib.Path(root).resolve()
    url = str(args.get("url") or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("BROWSER_URL_INVALID")
    actions = args.get("actions") or []
    if not isinstance(actions, list) or any(not isinstance(action, dict) for action in actions):
        raise RuntimeError("BROWSER_ACTIONS_INVALID")
    screenshot_path = _safe_path(root_path, args.get("screenshot_path"))
    result_path = _safe_path(root_path, args.get("result_path"))
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    _activate_playwright()

    # The live controller can be called from an event loop. Playwright's sync
    # protocol driver requires a thread without that loop, so isolate this one
    # local browser action sequence in its own worker thread.
    from concurrent.futures import ThreadPoolExecutor
    runner = _run_state_conditioned_browser if args.get("adaptive_goal") else _run_browser
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="brain-browser-cdp") as pool:
        future = pool.submit(runner, args, root_path, url, actions,
                             screenshot_path, result_path)
        return future.result(timeout=240)
