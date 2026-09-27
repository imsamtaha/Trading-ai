# ATLAS web app

Next.js frontend for the existing FastAPI service. The backend remains authoritative for MT5, account, risk, agents and execution. This frontend has no execution requests.

## Local run

Start FastAPI on `127.0.0.1:8011` using the existing project runtime. In a separate terminal:

```powershell
cd web
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open `http://127.0.0.1:3000`. The server-side Next rewrite uses `ATLAS_BACKEND_ORIGIN` (default `http://127.0.0.1:8011`). No browser-facing environment variable holds broker or service credentials.

## Verify and build

```powershell
npm test -- --run
npm run build
npm run lint
npm run start
```

The `/login` page serves the existing Google/Supabase auth bundle from `web/assets/google-auth.js` through a same-origin Next route. The root OAuth callback redirects to `/login` with its query preserved. Its session and OAuth callback behavior stay in that bundle. Sign-in alone does not authorize trading. See `docs/deployment/atlas-webapp.md` for routing and rollback.
