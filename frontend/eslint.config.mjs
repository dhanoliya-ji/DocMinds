/**
 * eslint.config.mjs
 * =================
 * ESLint's "flat config", which replaced `.eslintrc.json`.
 *
 * WHY THIS FILE REPLACED .eslintrc.json
 * -------------------------------------
 * ESLint 9 reads only this format, and `eslint-config-next` 16 requires
 * ESLint 9. The old `.eslintrc.json` is not merely deprecated -- it is not
 * read at all, so leaving it in place would lint nothing while still
 * reporting success.
 *
 * WHY `eslint` AND NOT `next lint`
 * --------------------------------
 * Next.js 16 removed the `next lint` command; the `lint` script now calls
 * ESLint directly.
 *
 * WHY THESE ARE IMPORTED, NOT PASSED THROUGH FlatCompat
 * -----------------------------------------------------
 * Most migration guides wrap the old config names in `FlatCompat`. That is
 * for packages still publishing eslintrc-style configs -- and running
 * eslint-config-next 16 through it fails outright with "Converting circular
 * structure to JSON", because version 16 already exports flat config arrays.
 * Importing them directly is both simpler and the supported path.
 */

import coreWebVitals from "eslint-config-next/core-web-vitals";
import typescriptConfig from "eslint-config-next/typescript";

const config = [
  // The same two rule sets the old .eslintrc.json extended:
  //   core-web-vitals  Next.js's rules plus the performance ones
  //                    (an unoptimised <img>, a synchronous script)
  //   typescript       the TypeScript rules
  ...coreWebVitals,
  ...typescriptConfig,

  {
    // Build output, dependencies, coverage. Linting generated code produces
    // noise nobody can act on.
    ignores: [".next/**", "node_modules/**", "coverage/**", "next-env.d.ts"],
  },

  {
    // ---- Test files ----
    // Tests legitimately do things application code should not.
    files: ["tests/**/*.{ts,tsx}"],
    rules: {
      // Mock factories and fixture builders take deliberately loose shapes.
      // The point of a fixture is to stand in for anything the API might
      // send -- including the malformed responses several tests exist to
      // cover.
      "@typescript-eslint/no-explicit-any": "off",
      // setup.ts destructures framer-motion's animation props purely to DROP
      // them before passing the rest to a real DOM element. The unused
      // bindings are the mechanism, not an oversight.
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
];

export default config;
