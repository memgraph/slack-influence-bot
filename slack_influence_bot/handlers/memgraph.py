import re
from typing import Optional, List
from gqlalchemy import Memgraph
from slack_influence_bot.interfaces.graph_handler import (
    GraphHandler,
    WordCount,
    ReactionCount,
    UserReactionCount,
    DEFAULT_WORD_LIMIT,
    DEFAULT_REACTION_LIMIT,
)
from slack_influence_bot.utils.log import logger


MEMGRAPH_STREAM_NAME = "slackstream"


class MemgraphHandler(GraphHandler):
    def __init__(self, host: str, port: int):
        self.client = Memgraph(host, port)
        self.setup_indices()

    def setup_stream(self, topic_name: str, stream_name=MEMGRAPH_STREAM_NAME):
        results = self.client.execute_and_fetch("SHOW STREAMS")
        stream = next((r for r in results if r["name"] == stream_name), None)
        if not stream:
            logger.info(f"Creating new stream {stream_name} for topic {topic_name}")
            self.client.execute(
                f"""
                CREATE KAFKA STREAM {stream_name}
                TOPICS {topic_name}
                TRANSFORM transform.transformation
                BATCH_INTERVAL 100 BATCH_SIZE 10
            """
            )

        if not stream or not stream["is running"]:
            logger.info(f"Starting stream {stream_name} for topic {topic_name}")
            self.client.execute(f"START STREAM {stream_name}")

    def setup_indices(self):
        indexes = [
            "User(uuid)",
            "Channel(uuid)",
            "Message(uuid)",
            "Word(value)",
        ]
        for index in indexes:
            logger.info(f"Creating index for {index}")
            self.client.execute(f"CREATE INDEX ON :{index};")

    def influence_message_words(self, message: str, channel_id: str, limit: int = DEFAULT_WORD_LIMIT) -> List[str]:
        message_escaped = re.sub(r'"', '\\"', message)
        results = self.client.execute_and_fetch(
            f"""
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
        """
        )
        return [r["word"] for r in results][:limit]

    def influence_my_words(
        self, user_id: str, channel_id: Optional[str] = None, limit: int = DEFAULT_REACTION_LIMIT
    ) -> List[WordCount]:
        query_channel = f", (m:Message)-->(:Channel {{ uuid: '{channel_id}' }})" if channel_id else ""
        results = self.client.execute_and_fetch(
            f"""
            MATCH (u:User {{ uuid: "{user_id}" }})-[p:POSTED]-(m:Message)-[c:CONTAINS]-(w:Word){query_channel}
            WITH DISTINCT w.value as word, count(*) AS word_count
            RETURN word, word_count
            ORDER BY word_count DESC
            LIMIT {limit}
        """
        )
        return [WordCount(r["word"], r["word_count"]) for r in results]

    def influence_my_reactions(
        self, user_id: str, channel_id: Optional[str] = None, limit: int = DEFAULT_REACTION_LIMIT
    ) -> List[ReactionCount]:
        query_channel = f"-->(:Channel {{ uuid: '{channel_id}' }})" if channel_id else ""
        results = self.client.execute_and_fetch(
            f"""
            MATCH (u:User {{ uuid: "{user_id}" }})-[r:REACTED_ON]->(m:Message){query_channel}
            WITH DISTINCT r.reaction AS reaction , count(*) AS reaction_count
            RETURN reaction, reaction_count
            ORDER BY reaction_count DESC
            LIMIT {limit}
        """
        )
        return [ReactionCount(r["reaction"], r["reaction_count"]) for r in results]

    def influence_relationship_reactions(
        self, user_id: str, another_user_id: str, limit: int = DEFAULT_REACTION_LIMIT
    ) -> List[ReactionCount]:
        results = self.client.execute_and_fetch(
            f"""
            MATCH (:User {{ uuid: '{user_id}' }})-[:POSTED]->(m:Message)<-[r:REACTED_ON]-(:User {{ uuid: '{another_user_id}' }})
            WITH r.reaction as reaction, COUNT(*) AS reaction_count
            RETURN reaction, reaction_count
            ORDER BY reaction_count DESC
            LIMIT 5
        """
        )
        return [ReactionCount(r["reaction"], r["reaction_count"]) for r in results]

    def influence_channel_send_max_reactions(
        self, reactions: List[str], channel_id: Optional[str] = None
    ) -> List[UserReactionCount]:
        query_channel = ""
        if channel_id:
            query_channel = f"""
            MATCH (c:Channel {{ uuid: "{channel_id}" }})<--(m:Message)
            WITH m
            """

        query = f"""
            {query_channel}
            MATCH (m:Message)<-[r1:REACTED_ON]-(u:User)
            OPTIONAL MATCH (m)<-[r2:REACTED_ON]-(u:User)
            WHERE r2.reaction IN ["{'", "'.join(reactions)}"]
            WITH DISTINCT u.uuid as user, count(r1) as total_reactions, count(r2) as value_reactions
            WHERE value_reactions > 0
            RETURN user, total_reactions, value_reactions
            ORDER BY value_reactions DESC, total_reactions ASC
        """
        results = self.client.execute_and_fetch(query)
        return [UserReactionCount(r["user"], r["value_reactions"]) for r in results]

    def influence_channel_send_min_reactions(
        self, reactions: List[str], channel_id: Optional[str] = None
    ) -> List[UserReactionCount]:
        query_channel = ""
        if channel_id:
            query_channel = f"""
            MATCH (c:Channel {{ uuid: "{channel_id}" }})<--(m:Message)
            WITH m
            """

        query = f"""
            {query_channel}
            MATCH (m:Message)<-[r1:REACTED_ON]-(u:User)
            OPTIONAL MATCH (m)<-[r2:REACTED_ON]-(u:User)
            WHERE r2.reaction IN ["{'", "'.join(reactions)}"]
            WITH DISTINCT u.uuid as user, count(r1) as total_reactions, count(r2) as value_reactions
            WHERE value_reactions >= 0
            RETURN user, total_reactions, value_reactions
            ORDER BY value_reactions ASC, total_reactions DESC
        """
        results = self.client.execute_and_fetch(query)
        return [UserReactionCount(r["user"], r["value_reactions"]) for r in results]

    def influence_channel_receive_max_reactions(
        self, reactions: List[str], channel_id: Optional[str] = None
    ) -> List[UserReactionCount]:
        query_channel = ""
        if channel_id:
            query_channel = f"""
            MATCH (c:Channel {{ uuid: "{channel_id}" }})<--(m:Message)
            WITH m
            """

        query = f"""
            {query_channel}
            MATCH (u:User)-[:POSTED]->(m:Message)<-[r:REACTED_ON]-(:User)
            WHERE r.reaction IN ["{'", "'.join(reactions)}"]
            RETURN DISTINCT u.uuid as user, count(r) as value_reactions
            ORDER BY value_reactions DESC
        """
        results = self.client.execute_and_fetch(query)
        return [UserReactionCount(r["user"], r["value_reactions"]) for r in results]
