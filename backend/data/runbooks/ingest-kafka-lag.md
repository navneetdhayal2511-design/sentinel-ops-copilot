# Ingest worker Kafka lag and OOM

Symptom: KafkaConsumerLagExceeded and OOMKilled replicas.
Mitigation:
- Scale workers and raise memory limits
- Pause low-priority consumers
- Inspect message size distribution and poison pills
