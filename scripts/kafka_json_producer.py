"""
Kafka JSON stdin producer

Every line should be a valid JSON object that will be sent
to Kafka server to a defined input topic.
If there is a line that is not a valid JSON, it will stop
producing.

Usage:
    kafka_json_producer.py KAFKA_TOPIC [KAFKA_SERVERS]
    kafka_json_producer.py -h | --help

Arguments:
    -h --help      Show this screen
    KAFKA_TOPIC    Topic for data input
    KAFKA_SERVERS  Bootstrap servers separated by comma [default: localhost:9092]

"""

import sys
import json
import logging
from typing import Dict, Any
from kafka import KafkaProducer

logging.basicConfig(format="%(asctime)-15s [%(levelname)s]: %(message)s")
logger = logging.getLogger("kafka_json_producer")
logger.setLevel(logging.INFO)

DEFAULT_KAFKA_PRODUCER_BATCH_WAIT_MS = 2000


def is_valid_json(line: str) -> bool:
    try:
        json.loads(line)
        return True
    except Exception:
        return False


def main(args: Dict[str, Any]):
    kafka_servers = args.get("KAFKA_SERVERS") or "localhost:9092"

    producer = KafkaProducer(
        value_serializer=lambda v: v.encode("utf-8"),
        bootstrap_servers=[server.strip() for server in kafka_servers.split(",")],
        linger_ms=DEFAULT_KAFKA_PRODUCER_BATCH_WAIT_MS,
    )

    for line in sys.stdin:
        trim_line = line.strip()

        if not trim_line:
            continue

        if not is_valid_json(trim_line):
            logger.error(f"Invalid JSON line: {line}")
            break

        logger.info(f"Producing line {trim_line}")
        producer.send(args["KAFKA_TOPIC"], trim_line)
    producer.flush()


if __name__ == "__main__":
    from docopt import docopt

    main(docopt(__doc__))
