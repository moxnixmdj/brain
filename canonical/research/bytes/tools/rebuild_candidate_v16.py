from pathlib import Path
_here=Path(__file__).resolve().parent
exec((_here/'rebuild_candidate_v15.py').read_text(),globals())
_ns={};exec((_here/'spent_profile_deadbody_v16.py').read_text(),_ns);_ns['apply'](DST)