from canonical.runtime.instruction_following_brain_configuration_v1 import compile_instruction_configuration, messages_for_prompt

def test_prompt_only_and_deterministic():
    p="The report must include a checksum and retain the title."
    a=compile_instruction_configuration(p)
    b=compile_instruction_configuration(p)
    assert a==b
    assert a["user"]==p
    assert a["hidden_evaluator_information_consumed"] is False
    assert messages_for_prompt(p)[1]["content"]==p

def test_explicit_list_is_reused_when_unambiguous():
    p="- Include the source.\n- Preserve the filename."
    out=compile_instruction_configuration(p)
    assert out["deterministic_extraction"]["explicit_compound_obligations"]==[
        "Include the source.","Preserve the filename."
    ]

def test_ambiguous_parser_failure_does_not_invent_constraints():
    p="Explain this and make it useful."
    out=compile_instruction_configuration(p)
    assert out["deterministic_extraction"]["explicit_compound_obligations"]==[]

def test_empty_prompt_fails_closed():
    try:
        compile_instruction_configuration(" ")
    except ValueError as exc:
        assert str(exc)=="PROMPT_REQUIRED"
    else:
        raise AssertionError("expected fail closed")
