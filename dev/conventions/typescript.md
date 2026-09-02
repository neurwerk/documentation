# TypeScript Conventions

These conventions apply to the Studio web application. Files in the Dify web
overlay follow the conventions of the pinned upstream Dify source.

## Studio Web Application

Studio is a pnpm workspace managed with Turbo. `studio/apps/web/` uses Next.js
16, React 19, the App Router, and strict TypeScript.

- `app/` contains routes and layouts.
- `components/` contains shared UI and feature components.
- `lib/api/` contains typed API clients and contracts.
- `lib/auth/` contains session and role helpers.
- `lib/oidc/` contains OIDC settings.
- `test/` contains shared test setup.

## Code Style

- Preserve `strict` and `noUncheckedIndexedAccess` in `tsconfig.json`.
- Use type-only imports. ESLint enforces them.
- Define external API request and response types near the API client.
- Add `"use client"` only to components that need browser APIs, state, effects,
  or client-side context.
- Prefer server components when browser state or effects are unnecessary.
- Use the `@/*` path alias for imports within `apps/web/`.
- Follow `apps/web/eslint.config.mjs` and `apps/web/.prettierrc`.

Do not weaken lint rules or add files to lint exceptions without a concrete
reason.

## User Interface

Use the existing Tailwind CSS utilities and CSS variables. Reuse established
layout, typography, color tokens, and interaction patterns.

Controls must have:

- clear labels;
- keyboard support;
- loading and error states where needed;
- responsive layouts.

## Tests

Use Vitest and Testing Library for frontend tests. Test user-visible behavior,
and prefer role, label, and text queries over implementation details. Mock API
client modules in `lib/api/` rather than HTTP implementation details.

## Validation

Run these commands from `studio/`:

```bash
pnpm install
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

## Dify Overlay

Files under `dify_ce_builder/overlay/web/` mirror paths in the upstream Dify
source. Match the surrounding upstream formatting, imports, components, and
internationalization patterns. Do not add a separate frontend toolchain for the
overlay.
