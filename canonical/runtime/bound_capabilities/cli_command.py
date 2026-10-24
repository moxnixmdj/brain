#!/usr/bin/env python3
"""Generic zero-shell adapter for verified local command-line suppliers."""
import hashlib
import pathlib
import subprocess


def _safe_path(root, raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p != root and root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    argv=args.get("argv")
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x for x in argv):
        raise RuntimeError("CLI_ARGV_REQUIRED")
    if len(argv)>64:
        raise RuntimeError("CLI_ARGV_TOO_LARGE")
    output_path=args.get("output_path")
    out=None
    if output_path:
        out=_safe_path(root,output_path)
        out.parent.mkdir(parents=True,exist_ok=True)
    proc=subprocess.run(
        argv,cwd=root,text=False,capture_output=True,timeout=max(1,min(int(args.get("timeout_s",60)),300))
    )
    result={
      "adapter":"bound_capability_cli",
      "argv":argv,
      "returncode":proc.returncode,
      "stdout":proc.stdout[-12000:].decode("utf-8","replace"),
      "stderr":proc.stderr[-12000:].decode("utf-8","replace")
    }
    if proc.returncode!=0:
        raise RuntimeError("CLI_COMMAND_FAILED:"+result["stderr"][-1200:])
    if out is not None:
        if not out.exists():
            # Whether a missing declared output is a FAILURE is a judgement about
            # what the sentence asked for, and this adapter is the producer -- it
            # is the one thing that must not be allowed to make it.  A command
            # that removes its operand (`rm A`, where the only path the sentence
            # names is the one being removed) leaves nothing to fingerprint, and
            # that is a fact worth reporting rather than an error worth raising.
            #
            # Only on the caller's explicit word, and reported as a fact with
            # output_verified False so no fingerprint is fabricated and nothing
            # downstream can read this as proof of a produced artifact.  Whether
            # the absence is what was asked for is decided by the acceptance
            # layer, which has the postcondition for exactly that.
            if str(args.get("output_may_be_consumed") or "").strip().lower() in ("1", "true", "yes"):
                result.update({
                  "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
                  "output_absent_after_run":True,
                  "output_bytes":0,
                  "output_verified":False
                })
                return result
            raise RuntimeError("CLI_EXPECTED_OUTPUT_MISSING")
        if out.is_dir():
            # `not out.is_file()` conflated two different facts: "the declared
            # output does not exist" and "the declared output is not a regular
            # file".  A directory the command just created is a real artifact
            # and the second fact is not a failure, so `mkdir D` -- which
            # produces exactly a directory -- raised CLI_EXPECTED_OUTPUT_MISSING
            # after having done its work.  Measured on cfd742d: the directory
            # was never even created, because the composer refused to dispatch a
            # command whose declared output could not be satisfied.
            #
            # A directory carries no bytes, so a byte-level expectation cannot
            # be met by one.  That case still refuses, and says which fact it is
            # reporting rather than claiming the output is missing.
            if str(args.get("output_prefix_hex") or "").strip() or args.get("output_text_utf8") is True:
                raise RuntimeError("CLI_EXPECTED_OUTPUT_NOT_A_FILE")
            result.update({
              "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
              "output_kind":"directory",
              "output_bytes":0,
              "output_verified":True
            })
            return result
        raw=out.read_bytes()
        prefix=str(args.get("output_prefix_hex") or "").strip().lower()
        if prefix:
            try:
                expected=bytes.fromhex(prefix)
            except ValueError as exc:
                raise RuntimeError("CLI_OUTPUT_PREFIX_HEX_INVALID") from exc
            if not raw.startswith(expected):
                raise RuntimeError("CLI_OUTPUT_PREFIX_MISMATCH")
        if args.get("output_text_utf8") is True:
            try:
                decoded=raw.decode("utf-8","strict")
            except UnicodeDecodeError as exc:
                raise RuntimeError("CLI_OUTPUT_NOT_UTF8") from exc
            if not decoded.strip():
                raise RuntimeError("CLI_OUTPUT_TEXT_EMPTY")
            result["output_text_utf8_verified"]=True
            result["output_text_excerpt"]=decoded[:4000]
        result.update({
          "output_path":str(out.relative_to(pathlib.Path(root).resolve())),
          "output_bytes":len(raw),
          "output_sha256":hashlib.sha256(raw).hexdigest(),
          "output_verified":True
        })
    return result
