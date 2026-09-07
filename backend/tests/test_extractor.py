"""
test_extractor.py
=================
WHAT THIS FILE TESTS
--------------------
`services/extractor.py` -- the ten parsers that turn 19 file extensions into
one shape: plain text plus metadata.

WHAT IT DELIBERATELY DOES NOT TEST
----------------------------------
PDF, DOCX, PPTX and XLSX extraction. Those need real binary fixtures, and a
generated one tests the library that generated it rather than this code.

What IS tested is everything that can be exercised with a file written from a
string -- text, Markdown, CSV, HTML, email, ZIP -- plus the dispatch table that
routes every extension, which is where a format silently stops working.

THE PROPERTY THAT MATTERS MOST
------------------------------
The page-break marker. Extraction writes "--- PAGE BREAK ---" between pages and
the chunker splits on exactly that string. It is the only reason a citation can
say "page 12", and a change to it on either side breaks citations without
breaking anything that raises. `test_chunker.py` asserts the reading half; this
file asserts the constant they must agree on.

TIER 1: writes to pytest's tmp_path. No database, no network.
"""

import zipfile

import pytest

from app.services.extractor import DocumentExtractor


def write(tmp_path, name: str, content: str, encoding="utf-8"):
    """Write a text file into the test's temporary directory."""
    path = tmp_path / name
    path.write_text(content, encoding=encoding)
    return str(path)


# ======================================================================
# Dispatch -- which parser handles which extension
# ======================================================================


class TestDispatch:
    """
    19 extensions map to 10 parsers. A missing branch means a format the UI
    offers and the backend rejects -- discovered by a user, not by a developer.
    """

    def test_an_unsupported_type_raises_a_useful_error(self, tmp_path):
        """
        Raised rather than returned, so the ingestion task marks the document
        "failed" with a message the user can act on.
        """
        path = write(tmp_path, "thing.xyz", "content")

        with pytest.raises(ValueError, match="Unsupported file type"):
            DocumentExtractor.extract(path, "xyz")

    def test_the_error_names_the_offending_type(self, tmp_path):
        path = write(tmp_path, "thing.xyz", "content")

        with pytest.raises(ValueError, match="exe"):
            DocumentExtractor.extract(path, "exe")

    @pytest.mark.parametrize("file_type", ["TXT", "Txt", "tXt"])
    def test_the_extension_is_case_insensitive(self, tmp_path, file_type):
        """
        `extract` lowercases again even though the upload endpoint already did,
        because ZIP extraction calls it with raw extensions from the archive.
        """
        path = write(tmp_path, "notes.txt", "Some content.")
        assert DocumentExtractor.extract(path, file_type).text.strip() == "Some content."


# ======================================================================
# The formats that can be tested from a string
# ======================================================================


class TestPlainText:
    def test_text_is_returned_unchanged(self, tmp_path):
        path = write(tmp_path, "notes.txt", "Hello world.\nSecond line.")
        result = DocumentExtractor.extract(path, "txt")

        assert "Hello world." in result.text
        assert "Second line." in result.text

    def test_markdown_is_read_as_text(self, tmp_path):
        """Markdown structure is preserved -- the markdown chunker needs it."""
        path = write(tmp_path, "doc.md", "# Heading\n\nBody paragraph.")
        result = DocumentExtractor.extract(path, "md")

        assert "# Heading" in result.text
        assert "Body paragraph." in result.text

    def test_an_empty_file_yields_empty_text(self, tmp_path):
        result = DocumentExtractor.extract(write(tmp_path, "empty.txt", ""), "txt")
        assert result.text.strip() == ""

    def test_unicode_survives(self, tmp_path):
        path = write(tmp_path, "unicode.txt", "Café — naïve — 密码 — 🔑")
        result = DocumentExtractor.extract(path, "txt")

        assert "密码" in result.text
        assert "Café" in result.text


class TestCsv:
    def test_cell_values_appear_in_the_text(self, tmp_path):
        path = write(tmp_path, "data.csv", "name,role\nAda,Engineer\nGrace,Admiral\n")
        result = DocumentExtractor.extract(path, "csv")

        for value in ("name", "Ada", "Engineer", "Grace"):
            assert value in result.text

    def test_an_empty_csv_does_not_raise(self, tmp_path):
        assert DocumentExtractor.extract(write(tmp_path, "empty.csv", ""), "csv") is not None


class TestHtml:
    def test_visible_text_is_extracted(self, tmp_path):
        html = "<html><body><h1>Title</h1><p>Paragraph text.</p></body></html>"
        result = DocumentExtractor.extract(write(tmp_path, "page.html", html), "html")

        assert "Title" in result.text
        assert "Paragraph text." in result.text

    def test_tags_are_stripped(self, tmp_path):
        """
        Otherwise every chunk would be padded with markup, wasting the token
        budget and diluting the meaning the embedding is supposed to capture.
        """
        html = "<html><body><p>Just the words.</p></body></html>"
        result = DocumentExtractor.extract(write(tmp_path, "page.html", html), "html")

        assert "<p>" not in result.text
        assert "Just the words." in result.text

    def test_script_and_style_contents_are_not_treated_as_prose(self, tmp_path):
        html = (
            "<html><head><style>.a{color:red}</style>"
            "<script>var x = 1;</script></head>"
            "<body><p>Real content.</p></body></html>"
        )
        result = DocumentExtractor.extract(write(tmp_path, "page.html", html), "html")

        assert "Real content." in result.text
        assert "var x = 1" not in result.text

    def test_htm_is_the_same_as_html(self, tmp_path):
        path = write(tmp_path, "page.htm", "<html><body><p>Content.</p></body></html>")
        assert "Content." in DocumentExtractor.extract(path, "htm").text


class TestEmail:
    def test_subject_and_body_are_extracted(self, tmp_path):
        raw = (
            "From: ada@example.com\n"
            "To: grace@example.com\n"
            "Subject: Quarterly report\n"
            "\n"
            "The report is attached and the numbers look good.\n"
        )
        result = DocumentExtractor.extract(write(tmp_path, "mail.eml", raw), "eml")

        assert "Quarterly report" in result.text
        assert "numbers look good" in result.text


class TestZip:
    """
    The recursive case: a ZIP is unpacked and every member is sent back through
    `extract`. Worth testing because it is the one parser that calls the
    dispatch table rather than being called by it.
    """

    def test_member_contents_are_extracted(self, tmp_path):
        archive = tmp_path / "bundle.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("first.txt", "Content of the first file.")
            zf.writestr("second.txt", "Content of the second file.")

        result = DocumentExtractor.extract(str(archive), "zip")

        assert "first file" in result.text
        assert "second file" in result.text

    def test_unsupported_members_do_not_fail_the_whole_archive(self, tmp_path):
        """
        One unreadable file among twenty must not lose the other nineteen --
        the whole document would be marked failed over a stray binary.
        """
        archive = tmp_path / "mixed.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("readable.txt", "This text should survive.")
            zf.writestr("mystery.xyz", "binary-ish content")

        result = DocumentExtractor.extract(str(archive), "zip")

        assert "This text should survive." in result.text

    def test_an_empty_archive_does_not_raise(self, tmp_path):
        archive = tmp_path / "empty.zip"
        with zipfile.ZipFile(archive, "w"):
            pass

        assert DocumentExtractor.extract(str(archive), "zip") is not None


# ======================================================================
# The shape every parser must return
# ======================================================================


class TestExtractionResult:
    def test_it_carries_text_and_metadata(self, tmp_path):
        result = DocumentExtractor.extract(write(tmp_path, "a.txt", "Some text."), "txt")

        assert isinstance(result.text, str)
        assert isinstance(result.metadata, dict)

    def test_it_reports_whether_ocr_is_needed(self, tmp_path):
        """A text file always has text, so it can never need OCR."""
        result = DocumentExtractor.extract(write(tmp_path, "a.txt", "Plenty of text."), "txt")
        assert result.needs_ocr is False


class TestLanguageDetection:
    def test_english_is_detected(self):
        text = "The quick brown fox jumps over the lazy dog and runs away quickly."
        assert DocumentExtractor.detect_language(text) == "en"

    @pytest.mark.parametrize("text", ["", "   ", "x"])
    def test_unusable_input_does_not_raise(self, text):
        """
        Detection on an empty or single-character string is meaningless, and a
        raise here would fail the whole ingestion over a cosmetic field.
        """
        assert isinstance(DocumentExtractor.detect_language(text), str)


# ======================================================================
# The constant the chunker depends on
# ======================================================================


def test_the_page_break_marker_is_unchanged():
    """
    Extraction writes this marker; the chunker splits on it. They are in
    different files with no shared constant, so this test is the only thing
    holding them together.

    If it fails, page numbers are about to silently disappear from every
    citation in a multi-page document -- with nothing raising.
    """
    import inspect

    source = inspect.getsource(DocumentExtractor)
    assert "--- PAGE BREAK ---" in source

    from app.services.chunker import ChunkerService

    assert ChunkerService._page_pattern.search("text\n--- PAGE BREAK ---\nmore")
