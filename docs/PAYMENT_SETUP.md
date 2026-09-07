# Payment setup and display preferences

The dashboard, subscription page and manual Whish page now have Arabic/English
and light/dark controls. Preferences are stored in each browser. Market symbols,
provider names and original news headlines remain in their source language.

## Stripe

Configure server-side on Windows; never commit real keys:
The server reads the repository-root .env file without overriding existing
process environment variables. Restart the server after configuration changes.

- STRIPE_RESTRICTED_KEY
- ATLAS_APP_URL: your stable public HTTPS origin
- ATLAS_STRIPE_PRICE_READER: $49/month recurring USD Price
- ATLAS_STRIPE_PRICE_PRO: $99/month recurring USD Price
- STRIPE_WEBHOOK_SECRET
- Existing Supabase billing audit configuration

Both Stripe plans retain a 3-day trial. Dynamic payment methods remain enabled.
Checkout no longer guesses a return origin from an incoming Host header.
Configure the signed webhook at /billing/webhook. Unknown subscription states
never activate access; subscription events retrieve the current provider state.

Not yet validated: live account configuration, public webhook delivery, database
schema alignment (the older migration uses trader while the code uses pro),
authenticated user-to-checkout binding, and subscriber access enforcement.
Do not treat payment collection alone as a complete membership system.
Tax settings require review of applicable registrations before enabling collection.

## Whish Money: manual requests, not a gateway integration

Whish publicly offers merchant Checkout at:
https://www.whish.money/corporate-solutions
Merchant credentials and the official integration contract are still required for
automated verification. No undocumented API or automatic payment approval is used.

For this ATLAS setup, the display contact is **Samir Taha — +961 76 420 910**
(also the WhatsApp support number). Set ATLAS_WHISH_ENABLED=true only after
verifying this is the receiving wallet and configuring
ATLAS_WHISH_RECIPIENT=Samir Taha and ATLAS_WHISH_SUPPORT=+96176420910.
These two values are intentionally public to customers; do not place secrets there.
ATLAS_WHISH_DB optionally specifies a private local SQLite path
(default data/whish_requests.sqlite3). Back it up and never serve or commit it.

/billing/whish/reader and /billing/whish/pro accept an email and persist a reference
with PENDING_REVIEW status. Repeat pending requests reuse the reference.
This is a request intake only: no payment is initiated, no receipt is accepted as
proof, no account access is granted, and no automatic renewal is promised.
Owner support must arrange the 3-day trial and confirm the payment instructions.
There is no remote approval endpoint. Manual reconciliation and authenticated
membership activation remain to be integrated before public paid launch.

/billing/methods reports configuration presence only; it does not verify provider
connectivity, account eligibility, actual Price values or webhook delivery.
