# Auth service JWT secret mismatch

Symptom: 401 spike on /oauth/token after canary deploy.
Root pattern: canary pods mounted stale JWT_SECRET from old secret version.
Mitigation:
- Rollback canary
- Sync vault secret revision
- Bounce auth-service and watch token success rate
