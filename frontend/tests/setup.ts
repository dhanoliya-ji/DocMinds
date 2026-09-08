/**
 * setup.ts
 * ========
 * Runs before every test file. Its job is to make each test start from a
 * clean, identical world.
 *
 * WHY THAT MATTERS MORE THAN IT SOUNDS
 * ------------------------------------
 * The three things reset below are all *module-level* or *global* state:
 * localStorage, the DOM, and the mocked router. Anything left behind in them
 * leaks into the next test, and the failure that results is the worst kind --
 * it depends on the order the tests happened to run in, so it passes alone and
 * fails in the suite, or passes locally and fails in CI.
 */

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

// ----------------------------------------------------------------------
// Next.js router
// ----------------------------------------------------------------------
// Every page here calls `useRouter()` and redirects with `router.push`.
// Outside a Next.js server there is no router, so the real hook throws.
//
// The mock is hoisted to module scope so a test can import `pushMock` and
// assert on it -- "did this page send an unauthenticated visitor to /login?"
// is a real behaviour worth checking, and this is how it becomes observable.
export const pushMock = vi.fn();
export const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

// ----------------------------------------------------------------------
// framer-motion
// ----------------------------------------------------------------------
// Animation adds nothing to a test and a great deal of noise: elements arrive
// mid-transition, so a query can find an item that is technically present but
// still at opacity 0. Replacing `motion.x` with a plain `<x>` renders the same
// content instantly and deterministically.
vi.mock("framer-motion", async () => {
  const React = await import("react");

  const passthrough = (tag: string) =>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ({ children, ...props }: any) => {
      // Strip the animation-only props so React does not warn about unknown
      // attributes on a real DOM element.
      const {
        initial, animate, exit, transition, variants, whileHover, whileTap,
        whileInView, viewport, layout, layoutId, ...rest
      } = props;
      return React.createElement(tag, rest, children);
    };

  return {
    motion: new Proxy({}, { get: (_t, tag: string) => passthrough(tag) }),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
    useAnimation: () => ({ start: vi.fn(), stop: vi.fn() }),
  };
});

// ----------------------------------------------------------------------
// window.location
// ----------------------------------------------------------------------
// api.ts redirects with `window.location.href = "/login"` when a request comes
// back 401. jsdom cannot navigate, so it logs "Not implemented: navigation to
// another Document" and carries on -- noise that buries real output.
//
// Replacing `href` with a plain writable property does two things: it silences
// that, and it turns the redirect into something a test can ASSERT on. Where
// an unauthenticated user is sent is behaviour, not an implementation detail.
const originalLocation = window.location;

beforeEach(() => {
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { ...originalLocation, href: "http://localhost:3000/", assign: vi.fn() },
  });

  // A token left behind by one test would silently authenticate the next one.
  localStorage.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  // Unmounts every rendered component. Without it the DOM accumulates, and a
  // `getByText` that should match once starts finding several.
  cleanup();
});
