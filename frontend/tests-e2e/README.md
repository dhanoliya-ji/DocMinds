# `frontend/tests-e2e/` — end to end

**14 tests.** One browser, one journey, the real backend. ~16 seconds once
warm.

```bash
npm run test:e2e          # needs the stack running — see below
npm run test:e2e:ui       # step through it visually
```

---

## Why these exist

Every other test in this repository mocks the boundary nearest to it. The
Vitest suite mocks `lib/api`; the backend suite calls Python functions or hits
the ASGI app in-process. So the one thing neither can see is **whether the two
halves still agree.**

That is not a theoretical gap. `lib/api.ts` hand-writes nine TypeScript
interfaces mirroring `backend/app/schemas/`, and nothing checks they match.

### This was verified, not assumed

Renaming `filename` to `file_name` in `SearchResult` and `Citation` — a
one-line change of exactly the kind a backend refactor makes:

| Suite | Result |
|---|---|
| Backend, 234 tests | **all passed** |
| Frontend unit, 122 tests | **all passed** |
| **This suite** | **failed** at the search step |

356 tests green against an app whose search results render no filename. These
14 are the only thing in the repository that noticed.

---

## Running them

Four processes. The Playwright config starts the fifth (`next dev`) itself.

```bash
# 1. Postgres + Redis
cd backend && docker compose up -d

# 2. The API                     ┐ both need these three env vars
# 3. The Celery worker           ┘
export EMBEDDING_PROVIDER=local LLM_PROVIDER=mock OCR_PROVIDER=mock
uvicorn app.main:app --port 8000
celery -A app.core.celery_app worker --loglevel=info --pool=solo   # Windows: --pool=solo

# 4. The tests
cd frontend && npm run test:e2e
```

### The provider settings are not arbitrary

**`LLM_PROVIDER=mock`** — no API key needed, and the answer's wording is not
what these tests assert on. What they check is that a reply arrived carrying
citations.

**`EMBEDDING_PROVIDER=local`, and specifically *not* `mock`** — this one is
worth understanding before "simplifying" it.

The mock provider hashes the text it is given: identical text gives an
identical vector, and anything else gives an unrelated one. Perfect for unit
tests, useless here. A short document becomes **one** chunk, so searching for a
sentence *from* that document produces a vector unrelated to the chunk's, a
similarity below `RETRIEVAL_MIN_SCORE`, and zero results.

That is not a guess — it is what happened while this file was being written.
The stored chunk turned out to be the full 109-character document rather than
the sentence being searched for. Meaning-based retrieval is the product's
central claim, and only a real model can demonstrate it.

The first run downloads `all-MiniLM-L6-v2` (~90 MB) and caches it.

---

## The one-time cost, and why there is a warm-up step

The local model loads **lazily, per process**. The worker pays ~40 seconds for
it on the first document — visible in that document's own `processing_seconds`
— and the API process pays it again, separately, on its first search.

So there is a deliberate throwaway request (`the API's embedding model is
warm`) that asserts nothing beyond "the endpoint answered". Without it, that
second load lands *inside* the search assertion, whose timeout then has to
cover a model load as well as a query.

That is not hypothetical either: the timeout was 45 s and failed on exactly
that boundary. The pipeline had worked perfectly and the test still went red.
Paying the cost in its own step means every timeout after it measures what it
claims to.

---

## The journey

| # | Step | What passing it proves |
|---|---|---|
| 1 | Backend reachable | The stack is up, with the right providers |
| 2 | Sign up | Organisation + user created, token issued |
| 3 | Token stored | `localStorage` wiring works |
| 4 | Model warm | The API can embed |
| 5 | Create a project | `RoleChecker` admits the org's Admin |
| 6 | Project opens | Routing and the three tabs render |
| 7 | Upload | Multipart reaches disk, a row exists |
| 8 | **Reaches "Ready"** | **All seven ingestion stages ran** |
| 9 | Search finds it | Retrieval **and** the schema contract |
| 10 | Score shown | The number survived as a number |
| 11 | Passage is intact | Extraction and chunking preserved the text |
| 12 | Chat answers | Retrieve → prompt → generate → save |
| 13 | Answer cites the file | The citation chain, end to end |
| 14 | No console errors | Nothing broke quietly along the way |

**Step 8 is the one that justifies the file.** Reaching it means the API queued
a job, Redis carried it, a worker took it, and extract → chunk → embed → store
all ran. Nothing else here verifies that chain.

Note the UI shows **"Ready"**, not `"completed"`. The status column's value and
its label are deliberately different things.

---

## Conventions

**One serial journey, not fourteen independent tests.** Normally shared state
between tests is a mistake; here the state *is* the subject. You cannot search
a document you have not uploaded. Splitting it up would mean redoing the whole
setup fourteen times against a pipeline that takes real seconds — or faking the
setup, which is what these tests exist not to do. `describe.serial` also stops
at the first failure rather than reporting five consequences of one cause.

**A fresh identity per run.** `Date.now().toString(36)` seeds the email, org and
project name, because these write real rows. A hard-coded email would collide
with the previous run on the second execution — a failure that looks like a bug
in signup.

**Every selector was read from the markup, not guessed.** The first draft used
`getByLabel(...)` and failed on all ten steps, because these forms label their
inputs with placeholders rather than `<label>` elements. Read the component
before changing a locator here.

**`.first()` where a match is legitimately ambiguous**, with a comment saying
why. The uploaded filename appears twice — in the confirmation and in the row —
and Playwright's strict mode fails on that rather than picking one silently,
which is the right default.

**No retries locally, one in CI.** A test that only passes on the second
attempt is telling you something; retrying hides it. CI gets one, where a slow
container start is a real and uninteresting cause.

---

## Not covered

- **Failure paths.** No test covers a document that fails ingestion, a
  duplicate upload, or an expired session mid-journey.
- **A second tenant.** Isolation is covered by the backend's four
  `TestTenantIsolation` tests against real SQL; nothing here drives two
  browsers.
- **The real LLM.** `groq` is never exercised, so a change to
  `generate_answer` that breaks only the live provider would pass.
- **Other browsers.** Chromium only.
