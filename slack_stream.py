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
    - MEMGRAPH_HOST
    - MEMGRAPH_PORT

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
from gqlalchemy import Memgraph
from kafka import KafkaProducer
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_history import get_channel_by_id, get_user_by_id

logging.basicConfig(format="%(asctime)-15s [%(levelname)s]: %(message)s")
logger = logging.getLogger("slack_bot")
logger.setLevel(logging.INFO)

DEFAULT_KAFKA_PRODUCER_BATCH_WAIT_MS = 1000

COMMAND_MESSAGE_INFLUENCE = "/influence-the-message"
COMMAND_CHANNEL_INFLUENCE = "/influence-the-channel"
COMMAND_PERSONAL_INFLUENCE = "/influence-me"
COMMAND_RELATIONSHIP_INFLUENCE = "/influence-you-and-me"


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


def _get_slack_app(bot_token: str, memgraph, event_handler=None):
    app = App(token=bot_token)

    def _get_message_influence_text(event):
        message = event["text"]
        results = memgraph.execute_and_fetch(f"""
            CALL tokenizer.tokenize("{message}") YIELD *;
        """)

        return f"You want me to influence this? {message}: {list(results)}"

    def _handle_command(event):
        logger.info(f"New command: {json.dumps(event)}")
        text = f"What the hell are you doing? I have no clue what to do for {event['command']}. Sorry."

        if event["command"] == COMMAND_MESSAGE_INFLUENCE:
            text = _get_message_influence_text(event)

        app.client.chat_postEphemeral(
            channel=event["channel_id"],
            user=event["user_id"],
            text=text)

    # Body contains: channel_id, channel_name, user_id, user_name, text, command
    @app.command(COMMAND_MESSAGE_INFLUENCE)
    def handle_message_influence(ack, body):
        ack()
        _handle_command(body)

    @app.command(COMMAND_CHANNEL_INFLUENCE)
    def handle_channel_influence(ack, body):
        ack()
        _handle_command(body)

    @app.command(COMMAND_PERSONAL_INFLUENCE)
    def handle_personal_influence(ack, body):
        ack()
        _handle_command(body)

    @app.command(COMMAND_RELATIONSHIP_INFLUENCE)
    def handle_relationship_influence(ack, body):
        ack()
        _handle_command(body)

    def _handle_event(event):
        logger.info(f"New event: {json.dumps(event)}")
        if event_handler:
            event_handler(event)

    @app.event("message")
    def handle_message_event(event):
        processed_event = dict(
            **event.items(),
            channel_data=get_channel_by_id(event["channel"]),
            user_data=get_user_by_id(event["user"]))
        _handle_event(processed_event)

    @app.event("reaction_added")
    def handle_reaction_added_event(event):
        processed_event = dict(
            **event.items(),
            user_data=get_user_by_id(event["user"]))
        _handle_event(processed_event)

    @app.event("reaction_removed")
    def handle_reaction_removed_event(event):
        processed_event = dict(
            **event.items(),
            user_data=get_user_by_id(event["user"]))
        _handle_event(processed_event)

    return app


def setup_memgraph(memgraph, kafka_topic):
    stream_name = 'slackstream'
    indexes = [
        'User(uuid)',
        'Channel(uuid)',
        'Message(uuid)',
        'Word(value)',
    ]
    for index in indexes:
        memgraph.execute(f"CREATE INDEX ON :{index};")

    results = memgraph.execute_and_fetch("SHOW STREAMS")
    stream = next((result for result in results if result["name"] == stream_name), None)
    if not stream:
        memgraph.execute(f"""
            CREATE STREAM {stream_name}
            TOPICS {kafka_topic}
            TRANSFORM transform.transformation
            BATCH_INTERVAL 100 BATCH_SIZE 10
        """)

    if not stream or not stream["is running"]:
        memgraph.execute(f"START STREAM {stream_name}")


def main(args):
    kafka_topic = args.get("KAFKA_TOPIC") or _get_required_env("KAFKA_TOPIC")
    kafka_servers = _get_required_env("KAFKA_BOOTSTRAP_SERVERS")
    slack_bot_token = _get_required_env("SLACK_BOT_TOKEN")
    slack_app_token = _get_required_env("SLACK_APP_TOKEN")
    memgraph_host = _get_required_env("MEMGRAPH_HOST")
    memgraph_port = _get_required_env("MEMGRAPH_PORT")

    memgraph = Memgraph(memgraph_host, int(memgraph_port))
    setup_memgraph(memgraph, kafka_topic)
    producer = _get_kafka_producer(servers=kafka_servers)

    app = _get_slack_app(
        slack_bot_token,
        memgraph=memgraph,
        event_handler=lambda event: producer.send(kafka_topic, event))
    handler = SocketModeHandler(app, slack_app_token)
    handler.start()


if __name__ == "__main__":
    from docopt import docopt
    main(docopt(__doc__))
