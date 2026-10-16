"""Child process for brain_module_invoke_v1: install a read-only audit hook, then call one function.

The audit hook is installed before the target module is imported and cannot be removed
(PEP 578).  It refuses any write/append/create/truncate open, deletes, renames, directory
creation, permission changes, subprocesses, exec/fork/spawn and socket use.  Reading files is
allowed, so functions that read repository data still work.

The payload is matched to the signature, never guessed:
  * a JSON object whose keys are parameter names (and covers every required one) -> keyword call;
    a required ``root``/``repo_root`` parameter missing from the object receives the repository root;
  * otherwise, a function with exactly one required parameter receives the payload as that argument;
  * a function with no required parameters accepts an empty object;
  * anything else fails closed and names the signature.
"""
import contextlib
import inspect
import io
import json
import os
import pathlib
import sys

MARKER = "\x00BRAIN_MODULE_INVOKE_RESULT\x00"
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_REFUSED = {
    "os.remove", "os.unlink", "os.rmdir", "os.rename", "os.replace", "os.mkdir", "os.makedirs", "os.chmod",
    "os.chown", "os.truncate", "os.link", "os.symlink", "os.utime", "os.system", "os.exec", "os.posix_spawn",
    "os.spawn", "os.fork", "os.forkpty", "os.kill", "os.killpg", "os.putenv", "os.unsetenv",
    "shutil.rmtree", "shutil.move", "shutil.copyfile", "shutil.copytree", "shutil.chown", "shutil.make_archive",
    "subprocess.Popen", "pty.spawn",
    "socket.connect", "socket.bind", "socket.sendto", "socket.sendmsg", "socket.getaddrinfo", "socket.__new__",
    "urllib.Request", "http.client.connect", "ftplib.connect", "smtplib.connect", "webbrowser.open",
    "ctypes.dlopen", "ctypes.dlsym", "ctypes.call_function", "sys.setprofile", "sys.settrace",
}
_ARMED = [False]


def _hook(event, args):
    if not _ARMED[0]:
        return
    if event == "open":
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & _WRITE_FLAGS):
            raise PermissionError("BRAIN_MODULE_INVOKE_READ_ONLY:write refused:" + str(args[0])[:200])
        return
    if event in _REFUSED or event.startswith(("os.exec", "os.spawn", "os.posix_spawn")):
        raise PermissionError("BRAIN_MODULE_INVOKE_READ_ONLY:" + event + " refused")


def _bind(fn, payload, root):
    sig = inspect.signature(fn)
    params = [p for p in sig.parameters.values() if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
    required = [p for p in params if p.default is p.empty]
    names = {p.name for p in params}
    accepts_kwargs = any(p.kind is p.VAR_KEYWORD for p in sig.parameters.values())
    shape = "(" + ", ".join(p.name + ("" if p.default is p.empty else "=") for p in params) + ")"
    if isinstance(payload, dict) and payload and (set(payload) <= names or accepts_kwargs):
        kwargs = dict(payload)
        for p in required:
            if p.name not in kwargs and p.name in ("root", "repo_root") and p.kind is not p.POSITIONAL_ONLY:
                kwargs[p.name] = root
        missing = [p.name for p in required if p.name not in kwargs]
        if missing:
            raise TypeError("PAYLOAD_MISSING_REQUIRED_PARAMETERS:" + ",".join(missing) + " signature=" + shape)
        if any(p.kind is p.POSITIONAL_ONLY and p.name in kwargs for p in params):
            raise TypeError("PAYLOAD_NAMES_POSITIONAL_ONLY_PARAMETER signature=" + shape)
        return (), kwargs
    if len(required) == 1 and payload not in ({}, None):
        return (payload,), {}
    if not required and payload in ({}, None):
        return (), {}
    raise TypeError("PAYLOAD_DOES_NOT_MATCH_SIGNATURE signature=" + shape)


def _unserializable(obj):
    raise TypeError("RESULT_NOT_JSON:" + type(obj).__name__)


def main():
    request = json.loads(sys.stdin.read())
    root = pathlib.Path(request["root"])
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader
    sys.addaudithook(_hook)
    reply = {"ok": False}
    sink = io.StringIO()
    try:
        _ARMED[0] = True
        with contextlib.redirect_stdout(sink):
            fn = loader.load_symbol(root, request["source"], request["function"])
            if not callable(fn):
                raise TypeError("SYMBOL_NOT_CALLABLE")
            args, kwargs = _bind(fn, request["payload"], root)
            result = fn(*args, **kwargs)
        text = json.dumps({"ok": True, "result": result}, allow_nan=False, sort_keys=True,
                          default=lambda o: o.as_posix() if isinstance(o, pathlib.PurePath) else _unserializable(o))
    except BaseException as exc:  # the parent reports the failure; nothing is retried
        text = json.dumps({"ok": False, "error": type(exc).__name__ + ":" + str(exc)[:400]})
    _ARMED[0] = False
    sys.__stdout__.write(MARKER + text)
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
