import mgp
import json
from tokenizer import tokenize_text
from datetime import datetime


def slack_timestamp_to_iso_date(timestamp):
    return datetime.utcfromtimestamp(float(timestamp)).isoformat()


def get_message_queries(payload):
    counter = tokenize_text(payload["text"])
    total_words = sum(counter.values())

    # In order to handle duplicate message, we will remove the message
    # if it already exists with the same message ID
    yield mgp.Record(
        query="MATCH (m:Message { uuid: $msg_uuid }) DETACH DELETE m",
        parameters={"msg_uuid": payload["ts"]},
    )

    query = """
    MERGE (c:Channel { uuid: $channel_uuid, name: $channel_name })
    MERGE (u:User { uuid: $user_uuid, name: $user_name, image: $user_image })
    CREATE (u)-[:POSTED]->(:Message { uuid: $msg_uuid, text: $text, total_words: $total_words, created_at: $created_at })-[:IN]->(c);
    """

    channel_data = payload.get("channel_data") or dict()
    user_data = payload.get("user_data") or dict()
    user_profile = user_data.get("profile") or dict()

    yield mgp.Record(
        query=query,
        parameters={
            "channel_uuid": payload["channel"],
            "channel_name": channel_data.get("name", "(private)"),
            "user_uuid": payload["user"],
            "user_name": user_data.get("name", ""),
            "user_image": user_profile.get("image", ""),
            "msg_uuid": payload["ts"],
            "text": payload["text"],
            "created_at": slack_timestamp_to_iso_date(payload["ts"]),
            "total_words": total_words,
        },
    )

    for word, count in counter.items():
        word_query = """
        MATCH (m:Message { uuid: $msg_uuid })
        MERGE (w:Word { value: $value })
        CREATE (m)-[:CONTAINS { count: $count, freq: $freq }]->(w);
        """
        yield mgp.Record(
            query=word_query,
            parameters={"msg_uuid": payload["ts"], "value": word, "count": count, "freq": count / total_words},
        )


def get_reaction_added_queries(payload):
    query = """
    MATCH (m:Message { uuid: $msg_uuid })
    MERGE (u:User { uuid: $user_uuid, name: $user_name, image: $user_image })
    MERGE (u)-[:REACTED_ON { reaction: $reaction }]->(m);
    """

    user_data = payload.get("user_data") or dict()
    user_profile = user_data.get("profile") or dict()

    yield mgp.Record(
        query=query,
        parameters={
            "msg_uuid": payload["item"]["ts"],
            "user_uuid": payload["user"],
            "user_name": user_data.get("name", ""),
            "user_image": user_profile.get("image", ""),
            "reaction": payload["reaction"],
        },
    )


def get_reaction_removed_queries(payload):
    query = """
    MATCH (u:User { uuid: $user_uuid })-[r:REACTED_ON { reaction: $reaction }]->(m:Message { uuid: $msg_uuid })
    DELETE r;
    """

    yield mgp.Record(
        query=query,
        parameters={"msg_uuid": payload["item"]["ts"], "user_uuid": payload["user"], "reaction": payload["reaction"]},
    )


def is_message_payload(payload):
    channel_type = payload.get("channel_type") or ""
    return payload["type"] == "message" and not payload.get("subtype") and channel_type in {"channel", "group", ""}


def get_queries(payload):
    if is_message_payload(payload):
        yield from get_message_queries(payload)
        return

    if payload["type"] == "reaction_added":
        yield from get_reaction_added_queries(payload)
        return

    if payload["type"] == "reaction_removed":
        yield from get_reaction_added_queries(payload)
        return


@mgp.transformation
def transformation(messages: mgp.Messages) -> mgp.Record(query=str, parameters=mgp.Nullable[mgp.Map]):
    queries = []

    for i in range(messages.total_messages()):
        message = messages.message_at(i)
        payload = json.loads(message.payload().decode("utf-8"))
        for query in get_queries(payload):
            queries.append(query)

    return queries
