# Checkout CDN asset failures

Symptom: checkout page broken, missing checkout.js, CORS noise from partners.
Mitigation:
- Purge CDN path for release assets
- Verify content hash in release manifest
- Confirm partner origins in CORS allowlist
