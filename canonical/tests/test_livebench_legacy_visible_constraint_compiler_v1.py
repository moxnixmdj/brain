from canonical.runtime.livebench_legacy_visible_constraint_compiler_v1 import compile_visible_constraints, source_surface

def one(text):
    out=compile_visible_constraints(text)
    assert out['status']=='PASS', out
    assert len(out['constraints'])==1, out
    return out['constraints'][0]

def test_source_surface():
    s=source_surface()
    assert s['recognized_public_type_count']==25
    assert s['registered_legacy_type_count']==25
    assert s['all_registered_types_covered_by_recognizers'] is True
    assert s['fully_visible_parameter_type_count']==24
    assert s['parameter_incomplete_types']==['combination:repeat_prompt']

def test_dynamic_recovery():
    cases=[
      ("Include keywords ['alpha', 'beta'] in the response.",'keywords:existence','keywords',['alpha','beta']),
      ('In your response, the word kiwi should appear at least 3 times.','keywords:frequency','frequency',3),
      ("Do not include keywords ['bad', 'worse'] in the response.",'keywords:forbidden_words','forbidden_words',['bad','worse']),
      ('In your response, the letter Q should appear less than 4 times.','keywords:letter_frequency','letter','q'),
      ('Your ENTIRE response should be in French language, no other language is allowed.','language:response_language','language','fr'),
      ('Your response should contain at least 7 sentences.','length_constraints:number_sentences','num_sentences',7),
      ('There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***','length_constraints:number_paragraphs','num_paragraphs',3),
      ('Answer with less than 120 words.','length_constraints:number_words','num_words',120),
      ('The response must contain at least 3 placeholders represented by square brackets, such as [address].','detectable_content:number_placeholders','num_placeholders',3),
      ('At the end of your response, please explicitly add a postscript starting with P.S.','detectable_content:postscript','postscript_marker','P.S.'),
      ('Your answer must contain exactly 4 bullet points.','detectable_format:number_bullet_lists','num_bullets',4),
      ('Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*.','detectable_format:number_highlighted_sections','num_highlights',2),
      ('Your response must have 3 sections. Mark the beginning of each section with SECTION X, such as:','detectable_format:multiple_sections','num_sections',3),
      ('Finish your response with this exact phrase Any other questions?. No other words should follow this phrase.','startend:end_checker','end_phrase','Any other questions?'),
      ('In your response, words with all capital letters should appear at least 6 times.','change_case:capital_word_frequency','capital_frequency',6),
    ]
    for text,iid,key,value in cases:
        c=one(text)
        assert c['instruction_id']==iid
        assert c['slots'][key]==value

def test_static_and_fail_closed():
    cases={
      'detectable_format:title':'Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.',
      'combination:two_responses':'Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.',
      'combination:repeat_prompt':'First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)',
      'change_case:english_capital':'Your entire response should be in English, and in all capital letters.',
      'change_case:english_lowercase':'Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.',
      'punctuation:no_comma':'In your entire response, refrain from the use of any commas.',
      'startend:quotation':'Wrap your entire response with double quotation marks.',
    }
    for expected,text in cases.items(): assert one(text)['instruction_id']==expected
    repeat=one(cases['combination:repeat_prompt'])
    assert repeat['parameter_complete'] is False
    assert repeat['unresolved_parameters']==['prompt_to_repeat']
    dup=compile_visible_constraints('Answer with at least 5 words. Answer with less than 20 words.')
    assert dup['status']=='FAIL_CLOSED'
