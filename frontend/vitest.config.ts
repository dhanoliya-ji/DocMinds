/**
 * vitest.config.ts
 * ================
 * How the frontend test suite is run.
 *
 *     npm test              watch mode, re-runs on save
 *     npm run test:run      once, for CI
 *     npm run test:ui       the browser reporter
 *
 * WHY VITEST RATHER THAN JEST
 * ---------------------------
 * It reads this project's TypeScript and JSX with no separate transform step
 * to configure, and it resolves the `@/` alias from tsconfig the same way
 * Next.js does. Jest would need babel or ts-jest wired up by hand, and the two
 * configurations would then have to be kept in agreement forever.
 */

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  plugins: [react()],

  // tsconfig.json sets `"jsx": "preserve"`, because Next.js does its own JSX
  // transform at build time. Vitest has no Next.js build, so it must be told
  // to do the transform itself -- and to use the AUTOMATIC runtime, which
  // injects the jsx import rather than requiring `React` to be in scope.
  //
  // Without this every .tsx test fails with "React is not defined", which
  // points at the test file rather than at the transform actually responsible.
  esbuild: { jsx: "automatic" },

  resolve: {
    alias: {
      // Mirrors the `@/*` path in tsconfig.json, so a test imports a component
      // by exactly the same specifier the application uses.
      "@": path.resolve(__dirname, "."),
    },
  },

  test: {
    // jsdom gives us a DOM in Node: document, window, localStorage, events.
    // Without it, rendering a React component has nothing to render INTO.
    environment: "jsdom",

    // Runs before every test file. Registers jest-dom's matchers and clears
    // the state that would otherwise leak between tests.
    setupFiles: ["./tests/setup.ts"],

    // `describe`, `it` and `expect` without importing them in every file,
    // matching what most React examples assume.
    globals: true,

    include: ["tests/**/*.test.{ts,tsx}"],

    coverage: {
      provider: "v8",
      include: ["lib/**", "components/**", "app/**"],
    },
  },
});
