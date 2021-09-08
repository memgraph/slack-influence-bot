"""
Kafka JSON consumer

Usage:
    kafka_json_consumer.py KAFKA_TOPIC [KAFKA_SERVERS] [KAFKA_GROUP]
    kafka_json_consumer.py -h | --help

Arguments:
    -h --help      Show this screen
    KAFKA_TOPIC    Topic to listen for JSON data
    KAFKA_SERVERS  Bootstrap servers separated by comma [default: localhost:9092]
    KAFKA_GROUP    Consumer group [default: default-group]

"""

import json
import logging
from typing import Dict, Any
from kafka import KafkaConsumer

logging.basicConfig(format="%(asctime)-15s [%(levelname)s]: %(message)s")
logger = logging.getLogger("kafka_json_consumer")
logger.setLevel(logging.INFO)


def main(args: Dict[str, Any]):
    kafka_servers = args.get("KAFKA_SERVERS") or "localhost:9092"

    consumer = KafkaConsumer(
        args["KAFKA_TOPIC"],
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=args.get("KAFKA_GROUP") or "default-group",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        bootstrap_servers=[server.strip() for server in kafka_servers.split(",")],
    )

    for message in consumer:
        print(message.value)


if __name__ == "__main__":
    from docopt import docopt

    main(docopt(__doc__))
