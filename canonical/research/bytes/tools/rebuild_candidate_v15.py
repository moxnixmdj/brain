from pathlib import Path
_here=Path(__file__).resolve().parent
exec((_here/'rebuild_candidate_v14.py').read_text(),globals())
_ns={};exec((_here/'compact_builtin_errors_v15.py').read_text(),_ns);_ns['apply'](DST)