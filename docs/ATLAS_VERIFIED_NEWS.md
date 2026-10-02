# ATLAS publisher news and Arabic display

The existing dashboard news panel replaces its previous feed with **at most three headline rows**. Arabic is the default for new visitors; a saved English preference is respected. Switching language refreshes `/dashboard/market-briefing?language=ar|en`, and an older request cannot overwrite the latest selection.

## Publisher feeds

| Source | Publisher-owned feed | Coverage / original language |
|---|---|---|
| Federal Reserve | https://www.federalreserve.gov/feeds/press_monetary.xml | US monetary policy / English |
| European Central Bank | https://www.ecb.europa.eu/rss/press.html | ECB announcements and speeches / English |
| BBC Arabic | https://feeds.bbci.co.uk/arabic/rss.xml | Regional and international news / Arabic |

The Federal Reserve lists the monetary feed at https://www.federalreserve.gov/feeds/feeds.htm; the ECB lists its press feed at https://www.ecb.europa.eu/home/html/rss.en.html. All three endpoints returned HTTP 200 and valid RSS during the October 2, 2026 integration check. This is a point-in-time availability check, not an uptime guarantee.

`source_verified=true` means a fixed HTTPS publisher feed and an exact allowed publisher article domain. It does **not** mean every claim in an article was independently fact-checked. Redirects, external article hosts, embedded credentials, malformed publication dates and dates more than five minutes in the future are rejected. RSS descriptions and full articles are not republished.

Each row links to its original article and shows publisher, publication time, freshness and translation status. Old statements remain labelled old; a successfully fetched feed does not make an old statement current. One available article from each source is selected before filling remaining slots by publication time. Provider failure does not remove articles from other working providers.

## Arabic mode

Original Arabic headlines require no news or translation API key. English headlines use the runtime's existing `OPENAI_API_KEY` when available, with `OPENAI_TRANSLATION_MODEL` defaulting to `gpt-4.1-mini` (or an existing `OPENAI_MODEL` override when no translation-specific model is set). Only public headline text is sent, with response storage disabled, a 12-second timeout and no automatic retries. Machine translations are labelled; their originals remain in the API.

Translations with the wrong count, invalid values, no Arabic letters or changed numeric/percentage tokens are rejected. These checks do not prove semantic translation accuracy. The cache stores translated text only, then attaches the current article's own URL and metadata. Successful translations are preserved; missing translations are filled by native BBC Arabic headlines when enough are available. Otherwise the original is shown with an explicit Arabic-translation-unavailable label.

Live paid translation was **not** exercised in the integration workspace because no API key was present. The translation path and failure handling were tested with controlled provider responses. Native Arabic RSS and all three publisher feeds were tested live.

## Configuration and boundaries

- `ATLAS_NEWS_CACHE_SECONDS=300`: publisher request cache.
- `ATLAS_NEWS_FRESH_SECONDS=86400`: maximum publication age labelled recent.
- `ATLAS_TRANSLATION_CACHE_SECONDS=900`: translated-text cache.
- `OPENAI_TRANSLATION_MODEL=gpt-4.1-mini`: optional private translator model.

The RSS integration supplies dashboard context. It does not fill missing macro, event-calendar, geopolitical or portfolio risk scores, create the automatic worker's analytical context snapshot, or authorize a trade. Missing/stale execution context continues to block entries. Execution settings remain unchanged.
