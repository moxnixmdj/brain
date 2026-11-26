"""Evaluate a trusted, in-memory JSON predictor from a fresh POSIX CoW snapshot.

This isolates Python state, NOT filesystem or network effects. Real surface
observations need their own disposable room. A crashed/timed-out worker is
missing measurement, never an outcome that can 'identify' a hypothesis.
"""
from __future__ import annotations

import json
import multiprocessing
import tempfile


def predict(fn, arg, *, timeout=1.0):
    with tempfile.TemporaryFile() as out:
        def worker():
            try:
                value = json.dumps(fn(arg), allow_nan=False, sort_keys=True).encode()
                if len(value) <= 65536:
                    out.write(value); out.flush()
            except (Exception, SystemExit):
                return
        proc = multiprocessing.get_context('fork').Process(target=worker)
        proc.start()
        try:
            proc.join(timeout)
            if proc.is_alive():
                proc.kill(); proc.join(); raise ValueError('probe timed out')
            if proc.exitcode != 0:
                raise ValueError('probe worker failed')
            out.seek(0)
            return json.load(out)
        finally:
            proc.close()
