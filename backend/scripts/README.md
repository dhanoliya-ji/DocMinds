# `backend/scripts/` — run by hand, never by the app

Standalone utilities. Nothing in the API or the worker imports anything here,
and nothing in here runs automatically.

That separation is the point of the folder. These scripts previously lived in
`app/tasks/`, where everything else is a Celery job — so a reader had no way to
tell "runs on every upload" from "someone ran this once". Moving them out made
`tasks/` mean one thing.

| Script | Does |
|---|---|
| `generate_architecture_pdf.py` | Renders a printable architecture document to PDF |

---

## `generate_architecture_pdf.py`

```bash
pip install reportlab
cd backend
python scripts/generate_architecture_pdf.py
```

**`reportlab` is deliberately not in `requirements.txt`.** The application does
not need it, and adding it would make every deployment install a PDF library to
serve HTTP requests. A dependency used by one manual script belongs to that
script.

The interesting piece of code in it is `NumberedCanvas`, a two-pass canvas
subclass. Page footers want to read *"Page 3 of 12"*, but the total is unknown
until the last page is laid out — so the class buffers each page's state on
`showPage()` and writes the footers on `save()`, once the count is finally
known. That is the standard reportlab answer to a genuinely circular problem.

### Its content is hand-maintained

The architecture text is written into the script as literal strings. Nothing
checks it against the code, so it goes stale silently — and a stale
architecture document is worse than none, because it is believed.

The folder READMEs across `backend/` cover the same ground, render on GitHub
without installing anything, and sit next to the code they describe, which is
what gives them a chance of being updated alongside it. Prefer those; reach for
the PDF when someone specifically wants something printable.

---

## Adding a script here

Two rules keep the folder honest:

- **Nothing in `app/` may import it.** The moment it does, it is application
  code and belongs there instead.
- **Its dependencies stay out of `requirements.txt`.** Document them in a
  docstring, as `generate_architecture_pdf.py` does.
