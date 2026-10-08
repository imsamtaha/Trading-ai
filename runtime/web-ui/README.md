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

The `/login` page reads the private backend's public `/auth/config` and uses Supabase for Google sign-in and email OTP. If `GOOGLE_CLIENT_ID` is set, it uses Google ID tokens; otherwise it uses Supabase Google OAuth with the existing `/?auth=callback` return. After Supabase returns an access token, `/auth/session` verifies it server-side and sets an HttpOnly cookie. Account telemetry is read only from authenticated `/api/user/dashboard`; chart and market briefing use authenticated `/api/user/...` routes. Sign-in alone does not authorize trading. See `docs/deployment/atlas-webapp.md` for routing and rollback.
