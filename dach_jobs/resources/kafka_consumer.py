"""Kafka consumer resource. Drains a topic until poll times out."""

from __future__ import annotations

import os

from confluent_kafka import Consumer, TopicPartition
from dagster import ConfigurableResource


class KafkaConsumerResource(ConfigurableResource):
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    group_id: str = "dach-jobs-bronze"
    poll_timeout_seconds: float = 2.0
    max_messages: int = 10_000

    def drain(self, topic: str) -> list[bytes]:
        """Read currently-available messages from `topic`, return their values.

        Earliest-offset consumer; we commit after every successful drain so the
        next run picks up where we left off. Stops when a poll returns nothing.
        """
        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        try:
            consumer.subscribe([topic])
            values: list[bytes] = []
            empty_polls = 0
            while len(values) < self.max_messages:
                msg = consumer.poll(timeout=self.poll_timeout_seconds)
                if msg is None:
                    empty_polls += 1
                    if empty_polls >= 2:
                        break
                    continue
                if msg.error():
                    continue
                empty_polls = 0
                v = msg.value()
                if v is not None:
                    values.append(v)
            if values:
                consumer.commit(asynchronous=False)
            return values
        finally:
            consumer.close()

    def reset_offsets(self, topic: str) -> None:
        """Helper for local dev: rewind this consumer group to the start."""
        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "enable.auto.commit": False,
            }
        )
        try:
            md = consumer.list_topics(topic, timeout=10)
            tps = [
                TopicPartition(topic, p, 0) for p in md.topics[topic].partitions
            ]
            consumer.assign(tps)
            for tp in tps:
                consumer.seek(tp)
            consumer.commit(asynchronous=False)
        finally:
            consumer.close()
