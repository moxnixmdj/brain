"""Count real candidate executions, preserving two fresh winner replays."""
from pathlib import Path
import tempfile
import pytest
from canonical.runtime.bound_capabilities import python_provenance_guided_coupled_repair_v1 as repair


@pytest.mark.parametrize('mode', ['single','pair','unrepairable'])
def test_search_scores_each_single_once_and_still_replays_winner_twice(mode, monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        first = 'def lower(x): return x < 3\n'
        second = 'def upper(x): return x > 5\n' if mode == 'pair' else 'def upper(x): return x >= 5\n'
        (root/'m.py').write_text(first)
        (root/'n.py').write_text(second)
        test = ('from m import lower\nfrom n import upper\n'
                'assert lower(3)\nassert upper(5)\nassert lower(2)\n'
                'assert not lower(4)\nassert not upper(4)\nassert upper(6)\n')
        if mode == 'unrepairable':
            test += 'raise RuntimeError("deliberately outside edit basis")\n'
        (root/'test_all.py').write_text(test)
        calls = []
        real = repair._COUPLED._run_candidate

        def counted(repo, originals, candidate, argv, timeout, env):
            changed = sum(text != originals[p].decode() for p,text in candidate.items())
            result = real(repo, originals, candidate, argv, timeout, env)
            calls.append((changed, result['returncode']))
            return result

        monkeypatch.setattr(repair._COUPLED, '_run_candidate', counted)
        result = repair.run({'source_root':'.', 'test_paths':['test_all.py'],
                             'output_path':'report.json','timeout_s':3,
                             'mutations_per_file':12,'max_pair_candidates':100},root)
        assert result['source_restored'] is True
        assert (root/'m.py').read_text() == first
        assert (root/'n.py').read_text() == second
        assert (root/'test_all.py').read_text() == test
        if mode == 'unrepairable':
            assert result['pass'] is False
            assert result['verification_replays'] == []
            extra = 0
        else:
            assert result['pass'] is True, result
            assert result['winner_mode'] == ('SINGLE_GUIDED' if mode == 'single' else 'COUPLED_PAIR_GUIDED')
            assert len(result['verification_replays']) == 2
            assert all(row['returncode'] == 0 for row in result['verification_replays'])
            assert calls[-2:] == ([(1,0)]*2 if mode == 'single' else [(2,0)]*2)
            extra = 2 if mode == 'single' else 0
        assert sum(changed == 1 for changed,code in calls) == result['single_candidates_tested'] + extra
