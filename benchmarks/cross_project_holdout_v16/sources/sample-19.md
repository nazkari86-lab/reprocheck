# Performance Audit and Runtime Guardrails

Date: April 15, 2026  
Scope: Frontend load path, runtime responsiveness, localization overhead, and CI regression controls.

## Baseline Improvements Already Landed

1. Production compare bundle output (`webpack --mode production`) replaced development-mode output.
2. D3 loading was narrowed to flow/tree pages instead of being globally loaded across every page.
3. Legacy page dependencies were stabilized with local vendor assets (`jquery`, `jquery-migrate`, `bootstrap`, `d3`) to avoid CDN runtime failures.
4. Image loading hints were improved (`loading='lazy'`, `decoding='async'`, `fetchpriority='high'` on the first critical image).
5. Static-server behavior for local testing added ETag and gzip support.

## i18n-Related Performance Notes

1. Site-wide i18n now runs through `_src/js/i18n-site.ts`.
- Locale resolution order is deterministic (`lang` query param, localStorage, `<html lang>`, browser locale).
- Translation application is selector-driven (`data-i18n*`) and runs once on init plus locale changes.
- Internal links are rewritten with `lang=<locale>` to avoid extra locale negotiation work after navigation.

2. Compare-page i18n now runs through `_src/js/compare/i18n.ts`.
- Compare labels/loading/errors/chart ARIA strings are locale-backed.
- Fallback language remains `en-US` to avoid missing-copy runtime crashes.

3. Legacy flow/treemap components now consume i18n keys for status/error labels and key UI controls.
- This prevents copy drift between React and non-React pages while adding negligible runtime overhead.

4. Legacy TypeScript browser output is post-processed by `scripts/strip-cjs-prologue.ts`.
- This removes CommonJS prologue lines that can block browser globals (`d3`, `jQuery`) in non-module script execution.
- The step runs automatically as part of `npm run build:legacy`.

4. Webpack performance hints are disabled in `webpack.config.ts`.
- This keeps local and E2E test logs focused on failures.
- Bundle size enforcement remains in `_src/test/perf-report.ts` via explicit raw+gzip thresholds.

## Current Measured Compare Bundle Result

File: `_src/generated/js/dist/compare.bundle.js`
- Before optimization pass: `2,569,415` bytes (~2.45 MiB)
- After optimization pass: `491,445` bytes (~480 KiB)
- Gzip: `159,906` bytes (~156 KiB)

Reduction: ~80.9% raw size decrease from the pre-optimization baseline.

## Regression Guardrails

Run from `_src/`:

- `npm run perf:report`
- `npm run bench`
- `npm run lint`
- `npm run format:biome`
- `npm run docs:jsdoc:check`
- `npm run docs:jsdoc:check` (first-party TS/JS scope; third-party vendored scripts are excluded)
- `npm run test:unit:coverage`
- `npm run test:a11y`
- `npm run test:e2e:preflight`
- `npm run test:i18n:smoke`
- `npm run test:e2e` (now includes legacy flow/tree locale coverage in English and Spanish)

Memory profiling helpers:
- `npm run probe:memory`
- `npm run probe:memory:csv`
- `npm run probe:memory:watch`
- `npm run probe:memory:watch:csv`

## CI/CD Enforcement

The workflows in `.github/workflows/` now enforce:
- lint (ESLint + Biome check) + unit coverage (CI) + a11y + perf + bench
- i18n unit smoke tests (compare + site runtime)
- Eleventy build + i18n asset sanity checks in generated output
- Puppeteer E2E validation with explicit Chromium dependencies
- Docker build target validation for `test` and `verify-parallel`

## Remaining Risks / Follow-up

1. Compare bundle remains large despite optimization progress.
- Follow-up: evaluate route/component-level code splitting for compare subviews.

2. Large source images still affect strict 3G scenarios.
- Follow-up: add responsive `srcset` plus WebP/AVIF variants.

3. i18n currently supports two locales only (`en-US`, `es-419`).
- Follow-up: add extraction/lint tooling to prevent untranslated key drift as more locales are added.
