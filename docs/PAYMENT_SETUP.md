# Payment setup and display preferences

The dashboard, subscription page and manual Whish page have Arabic/English and
light/dark controls. Preferences are stored in each browser. Market symbols,
provider names and original news headlines remain in their source language.

## Whish Money only: manual requests, not a gateway integration

Whish publicly offers merchant Checkout at:
https://www.whish.money/corporate-solutions

Merchant credentials and the official integration contract are required before
automated verification can be enabled. This ATLAS release uses no undocumented
API and does not approve payments automatically.

For this setup, the display contact is **Samir Taha — +961 76 420 910**
(also the WhatsApp support number). Configure the private server environment:

```text
ATLAS_WHISH_ENABLED=true
ATLAS_WHISH_RECIPIENT=Samir Taha
ATLAS_WHISH_SUPPORT=+96176420910
ATLAS_WHISH_DB=data/whish_requests.sqlite3
```

The recipient and support values are intentionally visible to customers; do not
put secrets there. `ATLAS_WHISH_DB` is a private local SQLite path. Back it up,
never serve it, and never commit it.

`/billing/whish/reader` and `/billing/whish/pro` accept an email and persist a
reference with `PENDING_REVIEW` status. Repeat pending requests reuse the
reference. This is request intake only: no transfer is initiated, no receipt is
treated as proof, no account access is granted, and no automatic renewal is
promised. The owner must reconcile each payment and add the subscriber to
Cloudflare Access manually.

`/billing/methods` reports configuration presence only; it does not verify
provider connectivity, wallet ownership, transfer completion, or membership
activation.
