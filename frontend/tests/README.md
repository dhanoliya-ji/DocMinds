# `frontend/tests/` — the test suite

**122 tests.** No database, no backend, no network — every one runs anywhere
`npm install` has been run.

```bash
cd frontend
npm test                    # watch mode, re-runs on save
npm run test:run            # once, for CI
npx vitest run tests/api.test.ts
npx vitest run -t "rollback"    # by name
```

---

## The files

| File | Tests | Covers |
|---|---|---|
| `api.test.ts` | 41 | `lib/api.ts` — the token, errors, the two bypasses |
| `ChatPanel.test.tsx` | 27 | Asking, the optimistic rollback, citations, feedback |
| `SearchPanel.test.tsx` | 21 | Searching, the two empty states, the score readout |
| `UploadZone.test.tsx` | 17 | Drag and drop, uploading, feedback |
| `ProjectPage.test.tsx` | 16 | The document polling, and the auth guard |
| `setup.ts` | — | Router, motion, `localStorage` and `location` stubs |

---

## What these tests are for

The same principle as the backend suite: they target the places where **a bug
does not announce itself**. A crash reports itself; a component that renders
confidently wrong output does not.

**`ChatPanel` — the optimistic rollback.** The question is added to the
transcript before the answer arrives, so the wait is legible. If the request
then fails, that placeholder must be *removed*. An optimistic update without
its rollback is the usual half-built version of this pattern, and it lies to
the user the first time a request fails — leaving a question in the transcript
that was never answered and never will be.

**`UploadZone` — `preventDefault` on both handlers.** Neither call is visible
to a reviewer reading the JSX, and both fail silently. Without it on
`onDragOver` the browser never fires `onDrop`, so the zone is a dead area of
the page with no error to explain it. Without it on `onDrop`, the browser
navigates away from the app to display the dropped file.

**`SearchPanel` — the two empty states.** "You have not searched yet" and
"your search matched nothing" must look different. Collapsing them tells a user
who just opened the tab that their documents contain no match for a query they
never ran.

**`api.ts` — the array-shaped error detail.** FastAPI sends `detail` as a
string for most errors and as an *array* for a 422. Handling only the string
case turns every "which field is wrong?" into a bare status code, at exactly
the moment the user needed to be told.

**`api.ts` — a 401 clears the token, a 404 does not.** The second half matters
as much as the first: clearing on any failure would log the user out over a
missing project.

**`ProjectPage` — the polling, from both ends.** It must keep asking while a
document is `pending` or `processing`, and it must *stop* once everything has
settled. And its `clearInterval` cleanup must fire: without it every re-render
stacks another timer and the app escalates into hammering the API. That symptom
— gradually increasing load with no obvious cause — does not reproduce on a
short visit, which is precisely why a test is the only thing that catches it.

---

## These were checked for the ability to fail

A test that passes against broken code is worse than no test, because it
reports coverage it does not have. Each of these was verified by breaking the
code it covers and confirming it went red:

| Mutation | Result |
|---|---|
| Remove `preventDefault` from `handleDragOver` | caught |
| Remove the optimistic rollback in `ChatPanel` | caught |
| Stop clearing the token on a 401 | caught |
| Handle only the string form of `detail` | caught |
| Stop trimming the search query | caught (2 tests) |
| Remove `ProjectPage`'s `clearInterval` cleanup | caught (2 tests) |
| Remove its "stop when settled" early return | caught (4 tests) |
| Remove its auth guard redirect | caught (2 tests) |

Do the same for any test you add. It takes under a minute and it is the only
way to know which kind of test you have written.

---

## `setup.ts` — four stubs, each for a reason

Everything here exists because jsdom is not a browser, and each stub is the
minimum that makes a real behaviour testable.

**`next/navigation`** — every page calls `useRouter()`, which throws outside a
Next.js server. The mock exports `pushMock`, so *where an unauthenticated
visitor is sent* becomes something a test can assert on rather than an
implementation detail.

**`window.location`** — replaced with a writable object. This silences jsdom's
"Not implemented: navigation to another Document" noise **and** makes the 401
redirect assertable.

**`Element.prototype.scrollIntoView`** — jsdom implements no layout, so the
method does not exist. `ChatPanel` calls it after every message, and without
the stub all 27 of its tests fail with "not a function" — an error pointing at
the component rather than at the missing browser API.

**`framer-motion`** — replaced with plain elements. Animated content arrives
mid-transition, so a query can match an element still at `opacity: 0`.

Plus two resets between tests: `localStorage.clear()`, because a token left
behind would silently authenticate the next test, and `cleanup()`, because
otherwise the DOM accumulates and a `getByText` that should match once starts
finding several.

---

## Conventions

**Query the way a user would.** `getByPlaceholderText`, `findByText`,
`getByRole` — not CSS classes. Restyling a component is routine and must not
break its tests; removing the text a user reads is a real change, and breaking
then is correct.

`UploadZone`'s drop-zone helper walks up from the instruction text for exactly
this reason. The feedback buttons in `ChatPanel` are the one exception — they
carry only an icon, so there is no accessible name and the lucide SVG class is
the only handle available. That helper **throws** when it finds nothing rather
than returning an empty list, so the test cannot quietly pass having asserted
nothing.

**`lib/api` is mocked in component tests.** What is under test there is the
component's behaviour; the client has its own file.

**Fake timers where a component schedules something.** `UploadZone` clears its
success message after 4 seconds. On real timers that fires after the test has
finished and the component has unmounted, which React reports as an `act()`
warning. Fake timers put it under the test's control — and make the 4-second
behaviour itself assertable rather than merely tolerated.

**Re-query an element before a second interaction.** A re-render can replace
the DOM node, and clicking a stale reference does nothing — a failure with no
relationship to the behaviour under test.

---

## Not covered

Honest gaps:

- **Three of the four pages.** `/project/[id]` is covered; `/login`,
  `/dashboard` and the landing page are not — so signup and login, project
  creation, and the dashboard's provider health check are unverified.
- **Tailwind styling and layout.** Out of reach for jsdom, which has no layout
  engine at all.
- **End to end.** Nothing drives a real browser against a real backend, so the
  hand-written interfaces in `lib/api.ts` can still drift from
  `backend/app/schemas/` with nothing to catch it.

## A note on dependencies

Vitest is pinned to `^3.2.6`, not the latest. Vitest 5 requires
`@types/node >= 22` while this project pins `^20`, and versions below 3.2.6
carry a critical advisory in the Vitest UI server. The test tooling adds **no**
vulnerabilities; `npm audit` reports the same five pre-existing high findings
(`next`, `postcss`, and the eslint config chain) as before it was added.
