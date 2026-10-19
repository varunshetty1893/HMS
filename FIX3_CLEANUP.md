# Fix 3: cleanup (apply AFTER fixes 1 and 2)

Copy these files over the repo (same paths). No migration, no backend change.

## Done in this zip
1. admin-web: the dev-only mock API (`mockRouter.ts` + `mockData.ts`, ~1.5k lines) is now loaded with a
   dynamic import behind `import.meta.env.DEV`, and the two "demo customer" buttons are guarded the same
   way, so production builds no longer contain them.
2. admin-web: route-level `React.lazy` for the 9 modules. Main chunk 510 kB -> 232 kB; the >500 kB warning is gone.
3. `.env.example` (admin-web, customer-web) and `docs/14` no longer contain the real Render URL
   (`https://<your-render-app>.onrender.com`).
4. README: structure and "Implementation Status" updated (it still said Phase 0 / "scheduled").

## Not done on purpose (destructive; run only if you approve)
- `kitchen-app/` is NOT a byte-for-byte duplicate of `waiter-app/lib/kitchen/` (several files differ).
  Compare before deleting. It is not built in CI. SPECIFICATION.md and docs/01, docs/06 still mention it.
    git rm -r kitchen-app
- Root `src/`, `index.html`, `vite.config.ts`, `tsconfig.json`, `package.json`, `metadata.json` look like a
  leftover scaffold (src/ is 3 files). Check nothing deploys from the repo root (`render.yaml`, `Caddyfile`,
  `docker-compose.yml`) first.
- `docs/` has two numbering sets (`01-...` and `01_...`). They cross-reference each other, so merging
  them needs a doc pass, not a delete.

## Known leftover
customer-web still ships its small demo-session code (gated at runtime by `isProd`, so inert; the
backend rejects `demo-token-*`). Not changed.

Verified: admin-web and customer-web `tsc` + build, backend `ruff` + 397 tests on PostgreSQL 16.
