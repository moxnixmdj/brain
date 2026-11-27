from canonical.runtime.livebench_legacy_ifeval_constructive_solver_v1 import synthesize

def test_constrained_response_singleton():
    p="Answer with one of the following options: ('My answer is yes.', 'My answer is no.', 'My answer is maybe.')"
    out=synthesize(p)
    assert out['status'].startswith('CANDIDATE_PASS')
    assert 'My answer is yes.' in out['response']

def test_keyword_title_no_comma_composition():
    p=("Include keywords ['nebula', 'quartz'] in the response. "
       "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
       "In your entire response, refrain from the use of any commas.")
    out=synthesize(p)
    assert out['status'].startswith('CANDIDATE_PASS')
    assert 'nebula' in out['response'].lower()
    assert 'quartz' in out['response'].lower()
    assert '<<' in out['response'] and '>>' in out['response']
    assert ',' not in out['response']

def test_word_lower_bound_is_filled_after_structure():
    out=synthesize('Answer with at least 25 words.')
    assert out['status'].startswith('CANDIDATE_PASS')
    import re
    assert len(re.findall(r'\\w+',out['response'])) >= 25

def test_forbidden_word_is_respected():
    out=synthesize("Do not include keywords ['alpha', 'beta'] in the response.")
    assert out['status'].startswith('CANDIDATE_PASS')
    low=out['response'].lower()
    assert 'alpha' not in low and 'beta' not in low

def test_quotation_wraps_last():
    out=synthesize('Wrap your entire response with double quotation marks.')
    assert out['status'].startswith('CANDIDATE_PASS')
    assert out['response'][0]=='\"' and out['response'][-1]=='\"'

def test_paragraph_exact_count():
    out=synthesize('There should be 4 paragraphs. Paragraphs are separated with the markdown divider: ***')
    assert out['status'].startswith('CANDIDATE_PASS')
    assert len(out['response'].split('***')) == 4

def test_section_count():
    p=('Your response must have 3 sections. Mark the beginning of each section with Section X, such as:\\n'
       'Section 1\\n[content of section 1]\\nSection 2\\n[content of section 2]')
    out=synthesize(p)
    assert out['status'].startswith('CANDIDATE_PASS')
    assert out['response'].count('Section ') >= 3


def test_sentence_bound_preserves_title_obligation():
    p=("Your response should contain at least 4 sentences. "
       "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.")
    out=synthesize(p)
    assert out['status'].startswith('CANDIDATE_PASS')
    assert '<<' in out['response'] and '>>' in out['response']
    # Regression for the destructive rewrite removed in the sentence stage.
    assert out['response'].count('.') >= 4


def test_sentence_bound_preserves_keyword_obligation():
    p=("Include keywords ['nebula', 'quartz'] in the response. "
       "Your response should contain at least 3 sentences.")
    out=synthesize(p)
    assert out['status'].startswith('CANDIDATE_PASS')
    low=out['response'].lower()
    assert 'nebula' in low and 'quartz' in low
    assert out['response'].count('.') >= 3
