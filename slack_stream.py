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

import re
import os
import sys
import json
import logging
from slack_bolt import App
from gqlalchemy import Memgraph
from kafka import KafkaProducer
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_history import get_channel_by_id, get_user_by_id, get_channels
from slack_conversation import get_lazy_response, get_missing_user_response, \
    get_invalid_self_check_user_response, get_unknown_channel_response, \
    format_user_id_for_slack_message, format_channel_id_for_slack_message, \
    get_personal_prefix_response, get_incorrect_today_day

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


def get_user_id_from_slack_message(message: str):
    match = re.match(r'<@(U[A-Z0-9]+|.*?>)', message)
    if not match or len(match.groups()) < 1:
        return None
    return match.groups()[0]


def _get_message_influence_text(memgraph, event):
    channel_id = event["channel_id"]
    message = event["text"]
    message_escaped = re.sub(r'"', '\\"', message)

    # TODO: Call the recommender here
    results = memgraph.execute_and_fetch(f"""
        CALL tokenizer.tokenize("{message_escaped}") YIELD word
        WITH collect(word) as start_word_values

        MATCH (c:Channel)<--(m:Message)<-[r:REACTED_ON]-()
        WHERE c.uuid = '{channel_id}'
        WITH DISTINCT m, count(r) as reactions, start_word_values
        WITH avg(reactions) as avg_reactions, start_word_values

        MATCH (w:Word)<--(m:Message)-->(c:Channel)
        WHERE w.value IN start_word_values AND c.uuid = '{channel_id}'
        WITH DISTINCT m, start_word_values, avg_reactions

        MATCH (m:Message)-[c]->(w:Word)
        WHERE w.value IN start_word_values
        WITH m, collect(w) as old_words, start_word_values, avg_reactions

        MATCH (m:Message)<-[r:REACTED_ON]-()
        WITH m, count(r) as rating, old_words, start_word_values, avg_reactions

        MATCH (m:Message)-[c]->(w:Word)
        WHERE NOT w.value IN start_word_values
        WITH w, m, rating, old_words, start_word_values, avg_reactions
        RETURN DISTINCT w.value as word, sum(rating) as score, count(m) as messages, avg_reactions
        ORDER BY score DESC
    """)
    words = [f"`{result['word']}`" for result in list(results)][:5]
    channels = get_channels()
    channel_text = ', '.join([format_channel_id_for_slack_message(channel['id']) for channel in channels])
    text = "I can't really help you - I don't know you well. But no worries, I have a plan: " + \
           "Buy me a beer and let's hang out so we can meet each other. :wink:\n\n" + \
           "Btw also check if you are in the correct channel. I can help you only by checking the messages from " + \
           f"the channels that I can see: {channel_text}"
    if len(words) > 0:
        text = f"I know exactly what to do. But in a much more real sense, I have no idea what to do.\n\n" + \
               f"But, {get_incorrect_today_day()} and I am in a good mood to give recommendations, especially to you " + \
               f"{format_user_id_for_slack_message(event['user_id'])}, my best friend.\n\n" + \
               f"See if you can somehow mention the following words in your message: {', '.join(words)}"

    return f"{text}\n\n_Your original message:_\n{message}"


def _get_channel_highest_values_results(memgraph, channel_id):
    query_prefix = ""
    if channel_id:
        query_prefix = f"""
        MATCH (c:Channel {{ uuid: "{channel_id}" }})<--(m:Message)
        WITH m
        """

    query = f"""
        {query_prefix}
        MATCH (m:Message)<-[r1:REACTED_ON]-(u:User)
        OPTIONAL MATCH (m)<-[r2:REACTED_ON]-(u:User)
        WHERE r2.reaction =~ "value.*"
        RETURN DISTINCT u.uuid as user, count(r1) as total_reactions, count(r2) as value_reactions
        ORDER BY value_reactions DESC, total_reactions ASC
        LIMIT 5
    """
    return list(memgraph.execute_and_fetch(query))


def _get_channel_lowest_values_results(memgraph, channel_id):
    query_prefix = ""
    if channel_id:
        query_prefix = f"""
        MATCH (c:Channel {{ uuid: "{channel_id}" }})<--(m:Message)
        WITH m
        """

    query = f"""
        {query_prefix}
        MATCH (m:Message)<-[r1:REACTED_ON]-(u:User)
        OPTIONAL MATCH (m)<-[r2:REACTED_ON]-(u:User)
        WHERE r2.reaction =~ "value.*"
        RETURN DISTINCT u.uuid as user, count(r1) as total_reactions, count(r2) as value_reactions
        ORDER BY value_reactions ASC, total_reactions DESC
        LIMIT 5
    """
    return list(memgraph.execute_and_fetch(query))


def _get_channel_influence_text(memgraph, event):
    channel_id = event["channel_id"]
    is_all_channels = re.match("(tell|give)?\s*(me)?\s*(all|everything)", event["text"].lower())

    if not is_all_channels:
        results = list(memgraph.execute_and_fetch(f"""
            MATCH (c:Channel {{ uuid: '{channel_id}' }})
            RETURN c as channel
        """))
        db_channel = results[0].get("channel") if len(results) > 0 else None
        if not db_channel:
            return get_unknown_channel_response(channel_id)

    results_highest = _get_channel_highest_values_results(memgraph, None if is_all_channels else channel_id)
    results_lowest = _get_channel_lowest_values_results(memgraph, None if is_all_channels else channel_id)

    text = f"So, I just went to see what is going on in {format_channel_id_for_slack_message(channel_id)} regarding our values."
    if is_all_channels:
        text = "Ooh, we have someone who knows cheats. Ok, ok, ok. So you want to know everything, all the channels? :partyparrot:\n"
        text += "I will check value reactions in the following channels:\n"
        channels = get_channels()
        for channel in channels:
            text += f"-   {format_channel_id_for_slack_message(channel['id'])}\n"

    text += "\n\n"
    text += ":value-relationship: :value-lead: :value-learn: :value-communicate: :value-invent:"

    text += "\n\n"
    text += "Who is giving the most `value-` reactions?\n"
    if len(results_highest) == 0:
        text += "   - Nobody :cry:"
    else:
        for result in results_highest:
            text += f"   - *{result['value_reactions']}* - {format_user_id_for_slack_message(result['user'])}\n"

    text += "\n\n"
    text += "Who is not really reacting with `value-` reactions?\n"
    if len(results_lowest) == 0:
        text += "   - Nobody :cry:"
    else:
        for result in results_lowest:
            text += f"   - *{result['value_reactions']}* - {format_user_id_for_slack_message(result['user'])}\n"

    return text


def _get_personal_influence_text(memgraph, event):
    self_user_id = event["user_id"]
    results = list(memgraph.execute_and_fetch(f"""
        MATCH (u:User {{ uuid: "{self_user_id}" }})-[p:POSTED]-(m:Message)-[c:CONTAINS]-(w:Word)
        WITH DISTINCT w.value as word_value, count(*) AS word_count
        RETURN word_value, word_count
        ORDER BY word_count DESC
        LIMIT 3
    """))

    results_reactions = list(memgraph.execute_and_fetch(f"""
        MATCH (u:User {{ uuid: "{self_user_id}" }})-[r:REACTED_ON]->(m:Message)
        WITH DISTINCT r.reaction AS reaction , count(*) AS reaction_count
        RETURN reaction, reaction_count
        ORDER BY reaction_count DESC
        LIMIT 3
    """))

    text = get_personal_prefix_response()
    text += "\n\n"

    if len(results) == 0:
        text += "Hmmmm, you are not really active on Slack. I can't help you. Be more active!"
    else:
        words = ", ".join([f"`{r['word_value']}`" for r in results])
        text += f"Oh my, you must have talk about {words} a lot!"

    if len(results_reactions) > 0:
        reactions = " ".join([f":{r['reaction']}:" for r in results_reactions])
        text += f" I see you like to react with {reactions}. Nice choice!"

    return text


def _get_relationship_influence_text(memgraph, event):
    message = event["text"]
    self_user_id = event["user_id"]
    another_user_id = get_user_id_from_slack_message(message)
    if not another_user_id:
        return get_missing_user_response()

    if self_user_id == another_user_id:
        return get_invalid_self_check_user_response()

    results = list(memgraph.execute_and_fetch(f"""
        MATCH (:User {{ uuid: '{self_user_id}' }})-[:POSTED]->(m:Message)<-[r:REACTED_ON]-(:User {{ uuid: '{another_user_id}' }})
        WITH r.reaction as reaction, COUNT(*) AS reaction_count
        RETURN reaction, reaction_count
        ORDER BY reaction_count DESC
        LIMIT 5
    """))
    reactions = " ".join([f":{r['reaction']}:" for r in results])

    if not reactions:
        return f"I think you and {format_user_id_for_slack_message(another_user_id)} should have a beer and talk. I don't see too much interaction. :cry:"

    return f"Let's keep this a secret, but {format_user_id_for_slack_message(another_user_id)} likes to add the following reactions to your messages: {reactions}"


def _get_slack_app(bot_token: str, memgraph, event_handler=None):
    app = App(token=bot_token)

    # Event contains: channel_id, channel_name, user_id, user_name, text, command
    def _handle_command(event):
        logger.info(f"New command: {json.dumps(event)}")
        text = ""
        default_text = f"What the hell are you doing? I have no clue what to do for {event['command']}. Sorry."

        app.client.chat_postEphemeral(
            channel=event["channel_id"],
            user=event["user_id"],
            text=get_lazy_response())

        try:
            if event["command"] == COMMAND_MESSAGE_INFLUENCE:
                text = _get_message_influence_text(memgraph, event)

            if event["command"] == COMMAND_CHANNEL_INFLUENCE:
                text = _get_channel_influence_text(memgraph, event)

            if event["command"] == COMMAND_PERSONAL_INFLUENCE:
                text = _get_personal_influence_text(memgraph, event)

            if event["command"] == COMMAND_RELATIONSHIP_INFLUENCE:
                text = _get_relationship_influence_text(memgraph, event)
        except Exception as e:
            logger.error(e)
            text = "Something went wrong. Not good, not good. I think I am not a bot anymore, I am a huge pile of bugs."

        app.client.chat_postEphemeral(
            channel=event["channel_id"],
            user=event["user_id"],
            text=text or default_text)

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
        logger.info(f"New processed event: {json.dumps(event)}")
        if event_handler:
            event_handler(event)

    @app.event("message")
    def handle_message_event(event):
        logger.info(f"New event: {json.dumps(event)}")
        processed_event = dict(
            **event,
            channel_data=get_channel_by_id(event["channel"]),
            user_data=get_user_by_id(event["user"]))
        _handle_event(processed_event)

    @app.event("reaction_added")
    def handle_reaction_added_event(event):
        logger.info(f"New event: {json.dumps(event)}")
        processed_event = dict(
            **event,
            user_data=get_user_by_id(event["user"]))
        _handle_event(processed_event)

    @app.event("reaction_removed")
    def handle_reaction_removed_event(event):
        logger.info(f"New event: {json.dumps(event)}")
        processed_event = dict(
            **event,
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
