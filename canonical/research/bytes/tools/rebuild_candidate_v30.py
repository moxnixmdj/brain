from pathlib import Path
_here=Path(__file__).resolve().parent
exec((_here/'rebuild_candidate_v29.py').read_text(),globals())
_ns={};exec((_here/'conservative_hyperexpand_prune_v30.py').read_text(),_ns);_ns['apply'](DST)
