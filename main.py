"""
Slack Influence Bot

Slack bot that helps you understand and influence your slack community.

Before running a handler, make sure to set the following environment
variables:
    - KAFKA_TOPIC             (e.g. slack-events)
    - KAFKA_BOOTSTRAP_SERVERS (e.g. localhost:9092)
    - SLACK_BOT_TOKEN         (e.g. xoxb-...)
    - SLACK_APP_TOKEN         (e.g. xapp-...)
    - MEMGRAPH_HOST           (e.g. localhost)
    - MEMGRAPH_PORT           (e.g. 7687)

The bot will connect to the Slack Events API to listen for the following events:
    - New message in public channel where the bot is a member of
    - Reaction added on any message in public channel the bot is a member of
    - Reaction removed from the message in public channel the bot is a member of

Other commands can help you out to fetch the following:
    - `main.py users`    - A list of users
    - `main.py channels` - A list of channels where the bot is added
    - `main.py history`  - A list of events (messages, replies and reactions)
                           where each event will match the structure of the
                           Events API stream service

Usage:
    main.py [--history-message-count=SIZE]
    main.py users
    main.py channels
    main.py history [--channel=CHANNEL_NAME] [--message-count=SIZE]
    main.py -h | --help

Arguments:
    -h --help                    Shows this screen
    --channel=CHANNEL_NAME       Name of the channel
    --history-message-count=SIZE Number of historical messages to fetch, max 1000 [default: 10]
    --message-count=SIZE         Number of messages to fetch, max 1000 [default: 10]
"""

import json
from typing import Optional, Any
from slack_influence_bot import SlackInfluenceBot
from slack_influence_bot.utils.log import logger
from slack_influence_bot.utils.env import get_required_env
from slack_influence_bot.handlers.memgraph import MemgraphHandler
from slack_influence_bot.handlers.kafka import KafkaHandler

DEFAULT_MESSAGE_FETCH_LIMIT = 10


def _handle_users(bot: SlackInfluenceBot) -> None:
    for user in bot.get_users():
        print(json.dumps(user))


def _handle_channels(bot: SlackInfluenceBot) -> None:
    for channel in bot.get_channels():
        print(json.dumps(channel))


def _handle_history(bot: SlackInfluenceBot, channel_name: Optional[str] = None, limit: int = 10) -> None:
    channels = bot.get_channels()
    if channel_name:
        channels = [c for c in channels if c["name"] == channel_name]
        if not channels:
            raise Exception(f"Failed to get messages from channel {channel_name}. Am I, the bot, added there?")

    for channel in channels:
        for event in bot.get_channel_history_events(channel["id"], limit=limit):
            print(json.dumps(event))


def _handle_bot(bot: SlackInfluenceBot, limit: int = 10) -> None:
    kafka_topic = get_required_env("KAFKA_TOPIC")
    logger.info("Connecting to Kafka...")
    kafka = KafkaHandler(
        kafka_topic,
        kafka_servers=get_required_env("KAFKA_BOOTSTRAP_SERVERS"),
    )
    # Auto-create the topic with test event
    kafka.handle_event({"type": "test_event"})

    logger.info("Connecting to Memgraph...")
    memgraph = MemgraphHandler(host=get_required_env("MEMGRAPH_HOST"), port=int(get_required_env("MEMGRAPH_PORT")))
    memgraph.setup_stream(kafka_topic)

    logger.info("Producing historical data to Kafka...")
    for channel in bot.get_channels():
        logger.info(f"Producing {limit} messages from channel #{channel['name']} to Kafka...")
        for event in bot.get_channel_history_events(channel["id"], limit=limit):
            kafka.handle_event(event)

    logger.info("Connecting to Slack...")
    bot.listen_for_commands(handler=memgraph)
    bot.listen_for_events(handler=kafka)
    handler = bot.get_handler()
    handler.start()


def main(args: dict[str, Any]) -> None:
    bot = SlackInfluenceBot(
        slack_bot_token=get_required_env("SLACK_BOT_TOKEN"), slack_app_token=get_required_env("SLACK_APP_TOKEN")
    )

    if args["users"]:
        return _handle_users(bot)

    if args["channels"]:
        return _handle_channels(bot)

    if args["history"]:
        channel_name = args.get("--channel")
        limit = int(args["--message-count"]) if args.get("--message-count") else DEFAULT_MESSAGE_FETCH_LIMIT
        return _handle_history(bot, channel_name, limit)

    limit = int(args["--history-message-count"]) if args.get("--history-message-count") else DEFAULT_MESSAGE_FETCH_LIMIT
    return _handle_bot(bot, limit)


if __name__ == "__main__":
    from docopt import docopt

    args = docopt(__doc__)
    main(args)
