"""
test_llm_prompt.py
==================
WHAT THIS FILE TESTS
--------------------
`LLMService.build_context_prompt` -- the function that assembles retrieved
chunks and a question into the text sent to the language model.

WHY THIS ONE FUNCTION DESERVES ITS OWN FILE
-------------------------------------------
In a RAG system the prompt is not configuration around the real work. The
prompt IS the work. Two of the project's central guarantees live entirely
inside this function:

  1. CITATIONS. Excerpts are numbered, and the model writes those numbers into
     its answer. That numbering is the whole mechanism by which "[2]" resolves
     to a real file and page. Break it and citations point at the wrong source
     while continuing to look authoritative.

  2. NO SILENT FALLBACK. When retrieval finds nothing, the prompt says so
     explicitly rather than shipping an empty context block. An empty block
     leaves the model free to answer from its training data -- which is
     precisely the hallucination the whole architecture exists to prevent.

Neither failure crashes anything. Both produce confident, wrong output.

TIER 1: builds a string. No model is called, no key needed, no network.
"""

import uuid

import pytest

from app.services.llm import LLMService


def chunk(content: str, filename: str = "handbook.pdf", page=12, **extra) -> dict:
    """A retrieval result, shaped the way RetrievalService.search returns them."""
    result = {
        "chunk_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "filename": filename,
        "page_number": page,
        "chunk_index": 0,
        "content": content,
        "score": 0.83,
    }
    result.update(extra)
    return result


# ======================================================================
# The numbering that makes citations possible
# ======================================================================


class TestExcerptNumbering:
    def test_numbering_starts_at_one(self):
        """Humans count citations from [1], not [0]."""
        prompt = LLMService.build_context_prompt("Q?", [chunk("First excerpt.")])
        assert "EXCERPT [1]" in prompt
        assert "EXCERPT [0]" not in prompt

    def test_every_chunk_is_numbered_consecutively(self):
        chunks = [chunk(f"Excerpt {i} content.") for i in range(4)]

        prompt = LLMService.build_context_prompt("Q?", chunks)

        for n in (1, 2, 3, 4):
            assert f"EXCERPT [{n}]" in prompt
        assert "EXCERPT [5]" not in prompt

    def test_numbers_follow_retrieval_order(self):
        """
        Retrieval returns the closest match first, and the numbering must
        preserve that. If [1] were not the best match, the model would be
        subtly steered towards the weaker source.
        """
        chunks = [chunk("Alpha content."), chunk("Bravo content."), chunk("Charlie content.")]

        prompt = LLMService.build_context_prompt("Q?", chunks)

        assert prompt.index("Alpha") < prompt.index("Bravo") < prompt.index("Charlie")
        assert prompt.index("EXCERPT [1]") < prompt.index("EXCERPT [2]")


class TestSourceAttribution:
    def test_the_filename_is_included(self):
        prompt = LLMService.build_context_prompt("Q?", [chunk("Text.", filename="policy.docx")])
        assert "policy.docx" in prompt

    def test_the_page_number_is_included(self):
        prompt = LLMService.build_context_prompt("Q?", [chunk("Text.", page=42)])
        assert "page 42" in prompt

    def test_no_page_is_mentioned_when_there_is_none(self):
        """
        A CSV or an email has no pages. Writing "page None" would be noise the
        model might echo into its answer as a fake citation detail.
        """
        prompt = LLMService.build_context_prompt(
            "Q?", [chunk("Row data.", filename="data.csv", page=None)]
        )

        assert "data.csv" in prompt
        assert "page" not in prompt.lower().split("question:")[0]

    def test_each_excerpt_keeps_its_own_source(self):
        chunks = [
            chunk("Leave policy text.", filename="handbook.pdf", page=12),
            chunk("Finance text.", filename="finance.xlsx", page=None),
        ]

        prompt = LLMService.build_context_prompt("Q?", chunks)

        assert "handbook.pdf" in prompt and "page 12" in prompt
        assert "finance.xlsx" in prompt


# ======================================================================
# The content itself
# ======================================================================


class TestPromptContent:
    def test_the_question_is_present(self):
        question = "How much annual leave do I get?"
        prompt = LLMService.build_context_prompt(question, [chunk("Text.")])

        assert question in prompt
        assert "QUESTION:" in prompt

    def test_every_chunk_body_is_present(self):
        """The model can only ground its answer in text that actually arrives."""
        bodies = ["Employees accrue 1.75 days per month.", "Unused leave carries over."]

        prompt = LLMService.build_context_prompt("Q?", [chunk(b) for b in bodies])

        for body in bodies:
            assert body in prompt

    def test_the_question_comes_after_the_excerpts(self):
        """Context first, then the task. The excerpts are what the question is about."""
        prompt = LLMService.build_context_prompt("The question here?", [chunk("Excerpt text.")])

        assert prompt.index("Excerpt text.") < prompt.index("The question here?")

    def test_excerpts_are_separated_by_blank_lines(self):
        """
        So the model reads them as separate documents rather than one run-on
        passage -- which would invite it to merge two sources into one claim.
        """
        prompt = LLMService.build_context_prompt(
            "Q?", [chunk("First excerpt."), chunk("Second excerpt.")]
        )

        between = prompt[prompt.index("First excerpt.") : prompt.index("EXCERPT [2]")]
        assert "\n\n" in between


# ======================================================================
# The no-results case -- the anti-hallucination guarantee
# ======================================================================


class TestNoChunks:
    def test_it_says_none_were_found(self):
        """
        Explicit, not empty. This is the line that stops the model quietly
        answering from its training data when the corpus has nothing to say.
        """
        prompt = LLMService.build_context_prompt("Anything?", [])

        assert "none found" in prompt.lower()

    def test_the_question_is_still_included(self):
        prompt = LLMService.build_context_prompt("What is the policy?", [])
        assert "What is the policy?" in prompt

    def test_no_excerpt_is_invented(self):
        prompt = LLMService.build_context_prompt("Anything?", [])
        assert "EXCERPT [1]" not in prompt


# ======================================================================
# Robustness
# ======================================================================


class TestMissingFields:
    """
    Retrieval results are dictionaries, so a field can be absent. The prompt
    builder must degrade rather than raise -- a KeyError here would take down
    the request that a user is waiting on.
    """

    def test_a_missing_filename_does_not_raise(self):
        result = {"content": "Some text.", "page_number": 3}
        prompt = LLMService.build_context_prompt("Q?", [result])

        assert "Some text." in prompt
        assert "EXCERPT [1]" in prompt

    def test_a_missing_content_key_does_not_raise(self):
        prompt = LLMService.build_context_prompt("Q?", [{"filename": "a.pdf"}])
        assert "EXCERPT [1]" in prompt

    def test_an_entirely_empty_result_does_not_raise(self):
        assert "EXCERPT [1]" in LLMService.build_context_prompt("Q?", [{}])

    @pytest.mark.parametrize(
        "question", ["", "?", "a" * 3000, "What about [1] brackets?", "Ünïcödé 密码?"]
    )
    def test_unusual_questions_are_handled(self, question):
        prompt = LLMService.build_context_prompt(question, [chunk("Text.")])
        assert isinstance(prompt, str) and prompt
