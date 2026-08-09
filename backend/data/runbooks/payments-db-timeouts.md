# Payments API database timeouts

Symptom: elevated 5xx, TimeoutError to postgres primary, circuit breaker open.
Checks:
1) Compare primary vs replica lag and connection saturation
2) Inspect recent schema migrations / long transactions
3) Confirm pool size after last deploy
Mitigation:
- Shift reads to replica
- Restart unhealthy payments-api pods
- Page DB on-call if primary recovery > 5 minutes
