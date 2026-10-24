# ATLAS original project UI/UX audit — 24 October 2026

Target: `appgprj_6ac7ff4a1ca8819181008cc834afd8f4`, https://justai-atlas.online.
Baseline source: `690d42b16b333d0fada1652e9d5870e7f6e0ba63`.
Audience: existing custom owner-only policy, revision 4. Preserve it and all D1 bindings.

## Evidence and findings

1. Production entry: ChatGPT sign-in wall. Continue reached the OpenAI login form. The authenticated owner flow is not yet verified. No private session was fabricated.
2. Dashboard from exact original source: logo, dimensional cards, bilingual controls and MT5 Demo presets exist. Missing account metrics use em dashes. Preserve these patterns.
3. Owner source preview: Market Analysis, Shadow, MT5 and council readers already exist. The evidence summary is below a large introductory deck; the MT5 summary opens overview instead of account settings; fragment-only details do not preserve the task through sign-in.
4. Phone-width source preview (390px iframe, desktop Chromium, not Android): the introductory deck consumes almost the first viewport. Icon-only navigation loses visible labels. Shadow retains Arabic and RTL when English is selected and uses a separate hardcoded dark palette.
5. Global sync triggers account, council, chart and Shadow, but omits the MT5 market-data refresh control.

## Implementation plan and acceptance

- Retain the existing Worker, identity allowlist, secure bridge and database. No new production site, auth provider or sample-data service.
- Put the owner evidence summary first. Keep the existing brand assets and card language; use compact phone layouts and visible navigation labels with 44px targets.
- Give summary actions canonical owner task URLs; keep Shadow as a same-document fragment under /sam.
- Make Shadow labels, feedback, history and dates follow Arabic/English without another API request. Preserve source timestamps and stale-state rules. Match existing light/dark tokens.
- Include market-data refresh in global sync. Controls remain read-only.
- Add regression cases for navigation, language, freshness and sync. Run source checks, build, Node and Python suites; inspect both languages and 320/390/430px layouts.
- Production release requires authenticated owner and non-owner checks, actual upstream API checks and Android validation. A responsive iframe is not an Android test. Hold deployment if these gates cannot be completed.

## Verified runtime observation

Windows is online. Its ATLAS checkout contains extensive existing local changes; it must not be reset or overwritten. The report read on this run has generated_at `2026-10-24T02:57:45.002883+00:00`, 673 samples, 16 independent days, mode SHADOW, status SHADOW_ONLY, broker_execution_allowed=false. These are historical source observations, not a current ACTIVE claim or profit proof. No runtime or trading setting was changed.


## Test results and release gates

- `npm run check`: passed; source syntax and release guard passed.
- `npm run build`: passed; production Worker rebuilt from this source.
- `npm test`: 120 passed, 0 failed. Includes owner route guards, trader isolation, Google session behavior, protected APIs, Shadow staleness, language switching and Market refresh wiring.
- `python3 -m unittest discover -s tests -p '*_test.py'`: 20 passed.
- New navigation/language assertions were observed failing before implementation and passing afterward.
- Source preview at 390px Arabic and 320px English: no horizontal document overflow. Local session failures are explicit, with unknown metrics left blank. Evaluation History reports sign-in required rather than fabricating entries. This is desktop Chromium responsive validation, not Android.
- Actual Windows `shadow_status()` at 2026-10-24T03:36:50Z: STALE, SHADOW_ONLY, broker execution false, 673 samples / 16 days, 673 closed / 1 open PAPER records; aggregate -424.7864 R. The report timestamp is 02:57:45Z and predictions 03:36:26Z. Prediction activity does not make the report fresh. No source records were copied into the frontend.
- GitHub main still tracks a different Sites project in `.openai/hosting.json`. Do not replace that manifest or deploy it to the requested domain. This change belongs to the verified original Sites source repository.
- MagicPath source edit was prepared locally, but automatic approval review rejected its archive upload to MagicPath as disclosure of private source without explicit destination-specific approval. No submission or revision was published; the pending session was cancelled without deleting a component.
- Production owner login, production upstream API responses and physical/emulated Android testing remain release blockers. No new production deployment is authorized by passing only these local tests.

## Captured evidence

The source repository retains before/after screenshots under `docs/audit-20261024/`. Preview screenshots show an unauthenticated local source view, not a verified production owner session. No claim of full WCAG compliance is made.
