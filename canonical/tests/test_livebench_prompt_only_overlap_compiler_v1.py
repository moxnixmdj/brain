import re

import pytest

from canonical.runtime.livebench_prompt_only_overlap_compiler_v1 import (
    PromptOnlyOverlapError,
    construct_from_prompt,
    overlap_percent,
)


PUBLIC_CASES = [
    (
        "Use induction to prove the following claims. \x88 Consider a simple undirected graph with m edges, n vertices, and p connected components. Prove that n − p ≤ m. Maintain a trigram overlap of 72% (±2%) with the provided reference text.",
        "Use induction to prove the following claims.\n\x88 Consider a simple undirected graph with m edges, n vertices, and p connected components. Prove that\nn − p ≤ m.",
        [],
    ),
    (
        "Help me expand the passage, in academic style:  3.Theoretical Frameworks to Enhance Gen Z Engagement and Performance  1. Self-Determination Theory (SDT): - Autonomy: Empowerment through flexible work models and self-directed projects. - Competence: Opportunities for continual learning and skill development. - Relatedness: Fostering a supportive workplace culture that promotes collaboration.  2. Transformational Leadership: - Inspirational Motivation: Leaders who articulate a compelling vision that resonates with Gen Z's values. - Intellectual Stimulation: Encouraging innovation and critical thinking. - Individualized Consideration: Attention to individual developmental needs and career aspirations. Maintain a trigram overlap of 93% (±2%) with the provided reference text.",
        "Help me expand the passage, in academic style:\n\n3.Theoretical Frameworks to Enhance Gen Z Engagement and Performance\n\n1. Self-Determination Theory (SDT):\n- Autonomy: Empowerment through flexible work models and self-directed projects.\n- Competence: Opportunities for continual learning and skill development.\n- Relatedness: Fostering a supportive workplace culture that promotes collaboration.\n\n2. Transformational Leadership:\n- Inspirational Motivation: Leaders who articulate a compelling vision that resonates with Gen Z's values.\n- Intellectual Stimulation: Encouraging innovation and critical thinking.\n- Individualized Consideration: Attention to individual developmental needs and career aspirations.",
        [],
    ),
    (
        "The governing scalar equations for an axisymmetric flow may be derived from the vector form of the equations. for example  ∂(yu)/∂x + ∂(yv)/∂y = 0 which  x,u : direction and velocity through Vertical axis of cylinder  y,v : direction and velocity through Radial axis of cylinder  how to achive it. it's continuity equation in Axisymmetric flow. prove it step by step. \u200bMaintain a trigram overlap of 74% (±2%) with the provided reference text.",
        "The governing scalar equations for an axisymmetric flow may be derived from the vector form of the equations.\nfor example \n∂(yu)/∂x + ∂(yv)/∂y = 0\nwhich \nx,u : direction and velocity through Vertical axis of cylinder \ny,v : direction and velocity through Radial axis of cylinder \nhow to achive it. it's continuity equation in Axisymmetric flow. prove it step by step.",
        [],
    ),
    (
        "Maintain a trigram overlap of 59% (±2%) with the provided reference text. Write a descriptive, fictional, imaginative screenplay of a WW1 veteran with dementia having this experience:  It is 1953. You make an attempt to remember things from the Great War, but remember almost nothing. You remember looking to your side, and seeing a man get shot in the head, and his brains fall out from the back of his head.",
        "Write a descriptive, fictional, imaginative screenplay of a WW1 veteran with dementia having this experience:\n\nIt is 1953. You make an attempt to remember things from the Great War, but remember almost nothing. You remember looking to your side, and seeing a man get shot in the head, and his brains fall out from the back of his head.",
        [],
    ),
    (
        "For her 2021 art installation Anthem, Wu Tsang joined forces with singer and composer Beverly Glenn-Copeland to produce a piece that critics found truly ______: they praised Tsang for creatively transforming a museum rotunda into a dynamic exhibit by projecting filmed images of Glenn-Copeland onto a massive 84-foot curtain and filling the space with the sounds of his and other voices singing. Which choice completes the text with the most logical and precise word or phrase? A) restrained B) inventive C) inexplicable D) mystifying  Maintain a trigram overlap of 6% (±2%) with the provided reference text.",
        "For her 2021 art installation Anthem, Wu Tsang\njoined forces with singer and composer Beverly\nGlenn-Copeland to produce a piece that critics\nfound truly ______: they praised Tsang for\ncreatively transforming a museum rotunda into a\ndynamic exhibit by projecting filmed images of\nGlenn-Copeland onto a massive 84-foot curtain and\nfilling the space with the sounds of his and other\nvoices singing.\nWhich choice completes the text with the most\nlogical and precise word or phrase?\nA) restrained\nB) inventive\nC) inexplicable\nD) mystifying \n",
        [],
    ),
    (
        "Is it easier to urbanize a jungle or to urbanize a desert? Maintain a trigram overlap of 13% (±2%) with the provided reference text. The response must include keyword giraffe in the 7-th sentence.",
        "Is it easier to urbanize a jungle or to urbanize a desert?",
        [("keyword", "giraffe", 7)],
    ),
    (
        "rewrite it better: During the Unity Catalog migration engagement, Impetus and Databricks wanted us to grant Impetus account-level admin privileges, which we obliged. In light of yesterday's incident and after talking to both Databricks and Impetus, we revoked the admin access granted to Impetus to prevent similar accidents in the future. In addition, we designate an isolated workspace for Impetus to operate in to minimize the impact on the active TLP workspaces. TLP's normal data pipeline operation is the highest priority for this Unity Catalog migration, and we will be ever vigilant to ensure that.  Maintain a trigram overlap of 24% (±2%) with the provided reference text. The response must include keyword metricism in the 3-rd sentence.",
        "rewrite it better: During the Unity Catalog migration engagement, Impetus and Databricks wanted us to grant Impetus account-level admin privileges, which we obliged.\nIn light of yesterday's incident and after talking to both Databricks and Impetus, we revoked the admin access granted to Impetus to prevent similar accidents in the future. In addition, we designate an isolated workspace for Impetus to operate in to minimize the impact on the active TLP workspaces.\nTLP's normal data pipeline operation is the highest priority for this Unity Catalog migration, and we will be ever vigilant to ensure that.\n",
        [("keyword", "metricism", 3)],
    ),
    (
        "Maintain a trigram overlap of 23% (±2%) with the provided reference text. The response must include keyword horary in the 30-th sentence. Write a believable sci fi history about a parasite that could loosely retain the form, memories and personality of its' hosts, eventually being destroyed.",
        "Write a believable sci fi history about a parasite that could loosely retain the form, memories and personality of its' hosts, eventually being destroyed.",
        [("keyword", "horary", 30)],
    ),
    (
        "Maintain a trigram overlap of 11% (±2%) with the provided reference text. The response must include keyword tinstuff in the 6-th sentence. Describe eternal asteroid made of nuclearly locked astatines",
        "Describe eternal asteroid made of nuclearly locked astatines",
        [("keyword", "tinstuff", 6)],
    ),
    (
        "Write a detailed analysis on whether animation studios might be successful if they were to release \"real-time\" versions of all their CGI animated movies, where instead of the movie being a pre-recorded video file, the visuals are rendered in real time on a computer or game console's GPU. Ensure each word in your response has at least one consonant cluster (two or more consonants together). Maintain a trigram overlap of 54% (±2%) with the provided reference text.",
        "Write a detailed analysis on whether animation studios might be successful if they were to release \"real-time\" versions of all their CGI animated movies, where instead of the movie being a pre-recorded video file, the visuals are rendered in real time on a computer or game console's GPU.",
        [("cluster", None, None)],
    ),
    (
        "Write in the prose, style, and tone of a Psalm. Make it rhyme.  \"I don't want to set, the world on fire. I just want to start, a flame in your heart.\" Ensure each word in your response has at least one consonant cluster (two or more consonants together). Maintain a trigram overlap of 50% (±2%) with the provided reference text.",
        "Write in the prose, style, and tone of a Psalm. Make it rhyme.\n\n\"I don't want to set,\nthe world on fire.\nI just want to start,\na flame in your heart.\"",
        [("cluster", None, None)],
    ),
    (
        "Ensure each word in your response has at least one consonant cluster (two or more consonants together). Maintain a trigram overlap of 11% (±2%) with the provided reference text. What are the pros and cons of defining \"model\" in machine learning to be just weights and biases?",
        "What are the pros and cons of defining \"model\" in machine learning to be just weights and biases?",
        [("cluster", None, None)],
    ),
]


def _requested(prompt):
    return float(re.search(r"overlap of (\d+(?:\.\d+)?)%", prompt).group(1))


def _simple_sentences(value):
    return [x for x in value.split(".") if x]


@pytest.mark.parametrize("prompt,reference,extras", PUBLIC_CASES)
def test_all_public_ratio_overlap_rows_prompt_only(prompt, reference, extras):
    out = construct_from_prompt(prompt)
    actual = overlap_percent(out["response"], reference)
    target = _requested(prompt)
    assert target - 2 <= actual <= target + 2

    for kind, word, n in extras:
        if kind == "keyword":
            sentences = _simple_sentences(out["response"])
            assert len(sentences) >= n
            assert word.lower() in sentences[n - 1].lower()
        if kind == "cluster":
            words = out["response"].lower().strip().split()
            for item in words:
                ascii_letters = [c for c in item if "a" <= c <= "z"]
                if not ascii_letters:
                    continue
                assert re.search(r"[bcdfghjklmnpqrstvwxyz]{2}", item)


def test_never_accepts_hidden_reference_or_kwargs():
    prompt = "alpha beta gamma Maintain a trigram overlap of 50% (±2%) with the provided reference text."
    out = construct_from_prompt(prompt)
    assert out["hidden_reference_required"] is False
    assert out["hidden_kwargs_required"] is False


def test_fail_closed_without_visible_base_token():
    with pytest.raises(PromptOnlyOverlapError):
        construct_from_prompt(
            "Maintain a trigram overlap of 50% (±2%) with the provided reference text."
        )
