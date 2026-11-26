import pytest

from canonical.runtime.frame_program_v1 import Screen, compile_experience, explore_screen


class Port:
    def __init__(self, screens, commands):
        self.screens, self.commands = screens, commands
        self.moves = []
        self.at = 0

    def state(self):
        return self.screens[self.at]

    def act(self, a):
        assert a in self.state().offered
        self.moves.append(a)
        if a == self.commands[self.at]:
            self.at += 1

    def reset(self):
        self.moves.append('reset'); self.at = 0


# Asymmetric shapes, two clicks. Colours change again in the final state.
P = [bytes(v) for v in ([0,0,3,0,1,1,0,1,2], [0,0,0,0,1,1,0,2,2], [0,0,0,0,1,1,3,2,2])]
A = ['C:2:1:1', 'C:1:2:2']

def task(*, transpose=False, recolour=False):
    f = lambda c: 15-c if recolour else c
    grids = [bytes(f(p[x*3+y] if transpose else p[y*3+x]) for y in range(3) for x in range(3)) for p in P]
    actions = []
    for a in A:
        _, x, y, c = a.split(':'); x, y = (y,x) if transpose else (x,y)
        actions.append(f'C:{x}:{y}:{f(int(c))}')
    screens = [Screen(b, (a,), i==2) for i,(b,a) in enumerate(zip(grids,[*actions,'quit']))]
    return Port(screens, actions)


def test_one_exposure_verifies_receiver_effects_in_all_declared_encodings():
    e = explore_screen(task(), budget=2, record=True)['experience']
    for trans in [True,False]:
        for recolour in [True,False]:
            port = task(transpose=trans, recolour=recolour)
            r = explore_screen(port, budget=2, program=e['lifted'])
            assert (r['advanced'],r['replay']['confirmed_transitions'],r['replay']['terminal_revalidated'],r['cold']) == (True,2,True,None)
            assert port.moves == port.commands
    r = explore_screen(task(transpose=True,recolour=True), budget=2, program=e['raw'])
    assert (r['replay']['actions'], r['advanced']) == (0,True)  # cold success is not credited to memory
    assert explore_screen(task(), budget=2, program=e['raw'])['replay']['terminal_revalidated']


def test_symmetry_with_distinct_material_actions_is_not_a_binding():
    g = Screen(bytes([0]*9), ('C:0:0:0',)); end = Screen(bytes([1]*9),(),True)
    e = compile_experience([g,end], list(g.offered))['lifted']
    r = explore_screen(Port([g,end],list(g.offered)),budget=1,program=e)
    assert (r['advanced'],r['replay']['actions'],r['replay']['reason']) == (True,0,'AMBIGUOUS_OR_UNOFFERED')


def test_colour_binding_cannot_be_renegotiated_after_a_wrong_effect():
    p = task(); e = compile_experience(p.screens,p.commands)['lifted']
    s = p.screens[1]
    p.screens[1] = Screen(bytes(2 if v==1 else 1 if v==2 else v for v in s.pixels),s.offered)
    r = explore_screen(p,budget=3,program=e)
    assert r['replay']['reason']=='PREDICTION_REFUTED' and r['replay']['confirmed_transitions']==0
    assert p.moves == [A[0],'reset',A[0]] and not r['advanced'] and r['spent']==3


def test_data_only_version_budget_and_feedback_are_gates():
    p=task(); e=compile_experience(p.screens,p.commands)
    with pytest.raises(ValueError, match='terminal'):
        compile_experience(p.screens[:2],p.commands[:1])
    for program in [dict(e['raw'],version='old'),dict(e['lifted'],side=7),dict(e['raw'],zlib_frames='garbage')]:
        r=explore_screen(task(),budget=2,program=program)
        assert r['replay']['actions']==0 and r['replay']['reason']=='INAPPLICABLE_PROGRAM'
    p.screens[-1]=Screen(p.screens[-1].pixels,())
    r=explore_screen(p,program=e['lifted'],budget=2)
    assert not r['advanced'] and r['replay']['confirmed_transitions']==1 and r['replay']['reason']=='PREDICTION_REFUTED'
    assert explore_screen(task(),budget=1,program=e['lifted'])['spent']==1
