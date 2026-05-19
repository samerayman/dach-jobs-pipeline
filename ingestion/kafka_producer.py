"""Thin wrapper around confluent-kafka Producer with sensible defaults."""

from __future__ import annotations

import os

import structlog
from confluent_kafka import KafkaError, Producer

log = structlog.get_logger()


def _delivery_report(err: KafkaError | None, msg) -> None:
    if err is not None:
        log.error("kafka.delivery.failed", error=str(err), topic=msg.topic())
    # success path: stay quiet — we'd flood logs at 1k+ msg/run


class JobsProducer:
    """Produces JSON-serialized IngestionEnvelopes to the raw jobs topic."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
    ) -> None:
        self.topic = topic or os.getenv("KAFKA_TOPIC_RAW", "jobs.raw")
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers
                or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"),
                "client.id": "dach-jobs-ingestion",
                "enable.idempotence": True,
                "acks": "all",
                "compression.type": "zstd",
                "linger.ms": 50,
                "batch.num.messages": 1000,
            }
        )

    def produce(self, key: bytes, value: bytes) -> None:
        # poll(0) to surface delivery callbacks without blocking
        self._producer.poll(0)
        self._producer.produce(
            topic=self.topic,
            key=key,
            value=value,
            on_delivery=_delivery_report,
        )

    def flush(self, timeout: float = 10.0) -> int:
        return self._producer.flush(timeout)
