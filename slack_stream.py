"""
Slack stream handler

It will connect to the Slack Events API to listen for the following events:
    - New message in public or private channel where the bot is a member of
    - Reaction added on any message in public/private channel
    - Reaction removed from the message in public/private channel

Before running a handler, make sure to set the following environment
variables:
    - KAFKA_TOPIC (optional if KAFKA_TOPIC command line argument is sent)
    - KAFKA_BOOTSTRAP_SERVERS
    - SLACK_BOT_TOKEN
    - SLACK_APP_TOKEN

Usage:
    slack_stream.py [KAFKA_TOPIC]
    slack_stream.py -h | --help

Arguments:
    -h --help    Show this screen
    KAFKA_TOPIC  Kafka topic where the events will be streamed to. If not defined
                 then the environment variable KAFKA_TOPIC needs to be defined.
"""

import os
import sys
import json
import logging
from slack_bolt import App
from kafka import KafkaProducer
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(format="%(asctime)-15s [%(levelname)s]: %(message)s")
logger = logging.getLogger("slack_bot")
logger.setLevel(logging.INFO)

DEFAULT_KAFKA_PRODUCER_BATCH_WAIT_MS = 1000


def _get_required_env(name: str):
    env_value = os.getenv(name)
    if not env_value:
        raise Exception(f"Please define the following environment variable {name}")
    return env_value


def _get_kafka_producer(servers: str, batch_wait_ms=DEFAULT_KAFKA_PRODUCER_BATCH_WAIT_MS):
    return KafkaProducer(
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        bootstrap_servers=[server.strip() for server in servers.split(',')],
        linger_ms=batch_wait_ms)


def _get_slack_app(bot_token: str, event_handler=None):
    app = App(token=bot_token)

    @app.command("/help-me-out")
    def handle_some_command(ack, body, say):
        ack()
        logger.info(f"Command /help-me-out: {json.dumps(body}")
        say("I will help you out!")

    def _handle_event(event):
        logger.info(f"New event: {json.dumps(event)}")
        if event_handler:
            event_handler(event)

    @app.event("message")
    def handle_message_event(event):
        _handle_event(event)

    @app.event("reaction_added")
    def handle_reaction_added_event(event):
        _handle_event(event)

    @app.event("reaction_removed")
    def handle_reaction_removed_event(event):
        _handle_event(event)

    return app


def main(args):
    kafka_topic = args.get("KAFKA_TOPIC") or _get_required_env("KAFKA_TOPIC")
    kafka_servers = _get_required_env("KAFKA_BOOTSTRAP_SERVERS")
    slack_bot_token = _get_required_env("SLACK_BOT_TOKEN")
    slack_app_token = _get_required_env("SLACK_APP_TOKEN")

    producer = _get_kafka_producer(servers=kafka_servers)
    app = _get_slack_app(slack_bot_token, event_handler=lambda event: producer.send(kafka_topic, event))
    handler = SocketModeHandler(app, slack_app_token)
    handler.start()


if __name__ == "__main__":
    from docopt import docopt
    main(docopt(__doc__))
