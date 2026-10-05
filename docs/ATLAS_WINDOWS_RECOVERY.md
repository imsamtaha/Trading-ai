# ATLAS Windows web recovery

The supervisor watches the existing private backend on 8012 and frontend on
8011. Three failed checks and persisted backoff permit recovery of only the
two named web tasks. A successful restart request is reported as RECOVERING;
the next successful HTTP probe establishes HEALTHY. Five attempted restarts
per outage exhaust recovery. A healthy probe resets that budget. Broker and
council tasks are never restarted by this recovery path.

`scripts/start_atlas_tunnel.ps1` runs the existing ATLAS tunnel using HTTP/2
and the user's existing `.cloudflared/ATLAS-Window.token`. It does not expose
the credential, create a new tunnel, or change DNS. The executable and token
file paths can be configured with parameters.

Deployment on 2026-10-05 uses the user-level scheduled task **ATLAS Tunnel
Recovery**, starting at user logon, with three retries on process failure.
The existing administrator-owned Cloudflared service is left in place. The
user task requires an active Windows login; it does not provide availability
while the computer is powered off or before that user logs in.

The backend health endpoint checks process liveness independently of the
synchronous worker pool. A healthy response does not prove successful market
data, authentication, broker connectivity, or execution readiness.
