import mgp
import json
from tokenizer import tokenize_text


def get_message_queries(payload):
    counter = tokenize_text(payload["text"])
    total_words = sum(counter.values())

    query = """
    MERGE (c:Channel { uuid: $channel_uuid })
    MERGE (u:User { uuid: $user_uuid })
    CREATE (u)-[:POSTED]->(:Message { uuid: $msg_uuid, text: $text, total_words: $total_words })-[:IN]->(c);
    """

    yield mgp.Record(
        query=query,
        parameters={
            "channel_uuid": payload["channel"],
            "user_uuid": payload["user"],
            "msg_uuid": payload["ts"],
            "text": payload["text"],
            "total_words": total_words
        })

    for word, count in counter.items():
        word_query = """
        MATCH (m:Message { uuid: $msg_uuid })
        MERGE (w:Word { value: $value })
        CREATE (m)-[:CONTAINS { count: $count, freq: $freq }]->(w);
        """
        yield mgp.Record(
            query=word_query,
            parameters={
                "msg_uuid": payload["ts"],
                "value": word,
                "count": count,
                "freq": count / total_words
            })


def get_reaction_added_queries(payload):
    query = """
    MATCH (m:Message { uuid: $msg_uuid })
    MERGE (u:User { uuid: $user_uuid })
    CREATE (u)-[:REACTED_ON { reaction: $reaction }]->(m);
    """

    yield mgp.Record(
        query=query,
        parameters={
            "msg_uuid": payload["item"]["ts"],
            "user_uuid": payload["user"],
            "reaction": payload["reaction"]
        })


def get_reaction_removed_queries(payload):
    query = """
    MATCH (u:User { uuid: $user_uuid })-[r:REACTED_ON { reaction: $reaction }]->(m:Message { uuid: $msg_uuid })
    DELETE r;
    """

    yield mgp.Record(
        query=query,
        parameters={
            "msg_uuid": payload["item"]["ts"],
            "user_uuid": payload["user"],
            "reaction": payload["reaction"]
        })


def is_message_payload(payload):
    channel_type = payload.get("channel_type") or ""
    return payload["type"] == "message" and channel_type in {"channel", "group", ""}


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
