from pathlib import Path
_here = Path(__file__).resolve().parent
exec((_here / "rebuild_candidate_v10.py").read_text(), globals())
_ns={}
exec((_here / "compact_failclosed_stubs_v11.py").read_text(), _ns)
_ns["apply"](DST)
