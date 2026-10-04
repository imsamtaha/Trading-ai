# ATLAS headline routing experiment

The existing `/dashboard/market-briefing` headlines now include `routing` metadata:
`category`, `agent`, `method`, and `dispatch: METADATA_ONLY`. The dashboard displays
the market category in Arabic or English, retaining the maximum of three rows.
The agent is a proposed analysis destination, not a dispatched job. This change
does not create broker context, alter risk approval, or authorize execution.

## Default: local rules

No additional API call is made by default. English and Arabic headline rules
select MACRO, FX, COMMODITIES, DIGITAL_ASSETS, EQUITIES, or GENERAL. Priority is
macro policy, digital assets, commodities, currencies, then equities. Mixed
headlines receive one primary category. These keyword heuristics are approximate,
not calibrated financial relevance or confidence scores.

## Optional small-model experiment

Set the following in the private backend environment:

```dotenv
ATLAS_NEWS_ROUTING_ENABLED=true
ATLAS_NEWS_ROUTING_MODEL=gpt-6-luna
```

The existing private `OPENAI_API_KEY` is required. Only original public headlines
with `source_verified=true` and `fresh=true` are sent. Publisher-origin verification
is not independent fact checking. At most three headlines are classified in one
Responses API request, with `store=false`, a six-second timeout, zero SDK retries,
and a 1200-token output limit. Headline text is treated as untrusted data.

Output count, unique integer IDs and the category allowlist are validated before
accepting any model route. Failures and malformed results use local rules with
`method: RULES_FALLBACK`. Successful classifications use `method: MODEL`; other
local classifications use `method: RULES`. No model confidence is invented.

Successes and failures share a five-minute cache bounded to 128 entries per
process, keyed by model and original headline. Current URLs, timestamps,
translations and provenance are always attached from the current story. The cache
is not shared across hosts or process restarts. Set the flag to `false` for
immediate rollback to local classification.

## Validation and deployment

The bilingual fixtures and controlled provider responses validate category
selection, output rejection, provider failure fallback, caching, fresh/verified
eligibility and integration after Arabic headline selection. Frontend tests check
language labels, unknown category rejection, row limits and escaping.

Live paid inference has not been exercised in this workspace. Before enabling
the optional model in production, compare at least 20 manually labelled real
headlines against local rules, measure latency and actual token cost, and confirm
`MODEL` routes in the API. Deploy the backend and frontend assets together and
retain `ATLAS_NEWS_ROUTING_ENABLED=false` until that comparison is complete.
