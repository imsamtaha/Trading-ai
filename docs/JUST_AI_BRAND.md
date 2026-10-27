# JUST AI master identity

Sam approved this identity across JUST AI projects on 2026-10-27.

- Orange #ff5a00; charcoal #171717; ivory #f7f3ee. Small accent text on ivory: #b83e00.
- Master logo: web/assets/just-ai-reference.webp. Transparent app icon: web/assets/just-ai-icon.webp.
- Shared presentation stylesheet: web/assets/just-ai-brand.css.
- Keep the ATLAS name/emblem and semantic gain/loss/risk colors.
- Preserve permissions, data, routes and live-trading-disabled behavior.
- Reuse brand-contract.json for future UI work.

The public home, centers directory and Python dashboard templates load the shared identity. Existing Sites publications have independent source repositories and have already been updated; merging this change does not restart a Windows service or redeploy an external host.

Validation: static public-site asset/link allowlist, Python template syntax, unchanged embedded dashboard scripts, existing Node authentication/demo tests, and browser visual inspection. No broker execution is enabled by this change.
