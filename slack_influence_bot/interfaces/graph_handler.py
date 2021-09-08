from typing import Optional, List
from abc import ABC, abstractmethod
from collections import namedtuple

DEFAULT_WORD_LIMIT = 5
DEFAULT_REACTION_LIMIT = 3

WordCount = namedtuple("WordCount", "word, count")
ReactionCount = namedtuple("ReactionCount", "reaction, count")
UserReactionCount = namedtuple("UserReactionCount", "user_id, reaction_count")
UserReactionTotalCount = namedtuple("UserReactionCount", "user_id, reaction_count")


class GraphHandler(ABC):
    @abstractmethod
    def influence_message_words(self, message: str, channel_id: str, limit: int = DEFAULT_WORD_LIMIT) -> List[str]:
        pass

    @abstractmethod
    def influence_my_words(
        self, user_id: str, channel_id: Optional[str] = None, limit: int = DEFAULT_REACTION_LIMIT
    ) -> List[WordCount]:
        pass

    @abstractmethod
    def influence_my_reactions(
        self, user_id: str, channel_id: Optional[str] = None, limit: int = DEFAULT_REACTION_LIMIT
    ) -> List[ReactionCount]:
        pass

    @abstractmethod
    def influence_relationship_reactions(
        self, user_id: str, another_user_id: str, limit: int = DEFAULT_REACTION_LIMIT
    ) -> List[ReactionCount]:
        pass

    @abstractmethod
    def influence_channel_send_max_reactions(
        self, reactions: List[str], channel_id: Optional[str] = None
    ) -> List[UserReactionCount]:
        pass

    @abstractmethod
    def influence_channel_send_min_reactions(
        self, reactions: List[str], channel_id: Optional[str] = None
    ) -> List[UserReactionCount]:
        pass

    @abstractmethod
    def influence_channel_receive_max_reactions(
        self, reactions: List[str], channel_id: Optional[str] = None
    ) -> List[UserReactionCount]:
        pass
