# React / Refine migration target

This directory is isolated from the currently verified native application in `apps/web/`.
A production build is intended to be served at `/app-next/`; FastAPI does not mount that route
unless `dist/` exists. The legacy `/app/` and native WebGL viewer remain the regression reference.

```bash
npm install
npm run typecheck
npm test
npm run build
```

The current sandbox could not reach the npm registry. Source parsing and dependency declarations
are checked by `scripts/check-web-react-source.sh`, but that local source gate is not a substitute
for a real dependency typecheck, Vitest run, Vite production build or browser E2E.
