# CLAUDE.md (frontend)

Guidance for Claude Code when working in `frontend/` — the React client for Measured. See the [root CLAUDE.md](../CLAUDE.md) for the project overview.

## Stack

React 19 + TypeScript + Vite + React Router + Tailwind CSS + shadcn/ui (Radix UI primitives).

## Commands

```bash
npm run dev       # dev server on port 5173
npm run build     # TypeScript check + Vite build
npm run lint      # ESLint
npm run preview   # preview production build locally
```

## Structure (`src/`)
- `pages/` — `LogSession`, `Sessions`, `Projects`, `Charts`
- `components/` — `Layout` (responsive sidebar), `DateIntervalChooser`, `ProjectFilterSelect`, `SessionsChart`, `ColorDot`, `Tooltip`, shadcn/ui components in `ui/`
- `hooks/` — `useProjects`, `useSessions` (fetch with loading/error states, abort signal cleanup)
- `lib/` — shared TypeScript types, formatting utilities, project filtering/sorting
- `config.ts` — runtime config (reads `VITE_API_URL`)

`@/` is the path alias for `src/`.

## Environment

Reads `VITE_API_URL` for the backend URL. Local dev: put it in `frontend/.env.local` (e.g. `http://localhost:8000/api`).

## Deployment

Vercel, auto-deployed on push to `main` (Root Directory `frontend`, build command `npm run build`, output `dist`). Pull requests get preview deployments. After changing the deployed frontend domain, update the backend's CORS allowlist in `backend/app/main.py`. Full setup steps: [README.md](README.md).
