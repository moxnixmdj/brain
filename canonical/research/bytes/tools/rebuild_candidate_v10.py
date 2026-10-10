from pathlib import Path

# Reconstruct the accepted V9 donor-derived candidate, then apply the exact
# hash-bound V10 intra-module fail-closed trim. Standard trace/slice tools
# produce the final 277-file executable closure.
_here = Path(__file__).resolve().parent
exec((_here / "rebuild_candidate_v9.py").read_text(), globals())
_ns = {}
exec((_here / "intra_module_failclosed_trim_v10.py").read_text(), _ns)
_ns["apply"](DST)
