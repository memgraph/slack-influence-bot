import json
from typing import Dict, Any
from kafka import KafkaProducer
from slack_influence_bot.interfaces.event_handler import EventHandler

DEFAULT_KAFKA_PRODUCER_BATCH_WAIT_MS = 1000


class KafkaHandler(EventHandler):
    def __init__(self, kafka_topic: str, kafka_servers: str):
        self.kafka_topic = kafka_topic
        self.producer = KafkaProducer(
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            bootstrap_servers=[server.strip() for server in kafka_servers.split(",")],
            linger_ms=DEFAULT_KAFKA_PRODUCER_BATCH_WAIT_MS,
        )

    def handle_event(self, event: Dict[str, Any]) -> None:
        self.producer.send(self.kafka_topic, event)
