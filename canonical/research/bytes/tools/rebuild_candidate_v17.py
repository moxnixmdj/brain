from pathlib import Path
_here=Path(__file__).resolve().parent
exec((_here/'rebuild_candidate_v16.py').read_text(),globals())
_ns={};exec((_here/'fresh_quartic_unify_repair_v17.py').read_text(),_ns);_ns['apply'](DST)