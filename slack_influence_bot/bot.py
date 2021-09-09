import re
import json
import random
from typing import Optional
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_influence_bot.interfaces import EventHandler, GraphHandler
from slack_influence_bot.utils.slack import (
    wrap_rate_limit,
    get_user_id_from_slack_message,
    get_channel_id_from_slack_message,
    get_reactions_from_slack_message,
)
from slack_influence_bot.utils.log import logger
import slack_influence_bot.response as response

DEFAULT_MESSAGES_LIMIT = 50
CHIT_CHAT_RESPONSE_CHANGE = 0.2


class SlackInfluenceBot:
    def __init__(self, slack_bot_token: str, slack_app_token: str):
        self.slack_bot_token = slack_bot_token
        self.slack_app_token = slack_app_token
        self.app = App(token=slack_bot_token)
        self.cached_channels = None
        self.cached_users = None

    def refresh_channels(self):
        self.get_channels(use_cache=False)

    def get_channels(self, use_cache: bool = True):
        if use_cache and self.cached_channels:
            return self.cached_channels

        channels = []
        cursor = ""
        while True:
            response = self.app.client.conversations_list(
                types="public_channel,private_channel", exclude_archived=True, cursor=cursor
            )
            cursor = response.get("response_metadata", {}).get("next_cursor")

            for channel in response["channels"]:
                if channel["is_member"]:
                    channels.append({"id": channel["id"], "name": channel["name"], "is_private": channel["is_private"]})

            if not cursor:
                break

        self.cached_channels = channels
        return channels

    def get_channel_by_id(self, channel_id: str):
        return next((channel for channel in self.get_channels() if channel["id"] == channel_id), None)

    def refresh_users(self):
        self.get_users(use_cache=False)

    def get_users(self, use_cache: bool = True):
        if use_cache and self.cached_users:
            return self.cached_users

        users = []
        cursor = ""
        while True:
            response = self.app.client.users_list(cursor=cursor)
            cursor = response.get("response_metadata", {}).get("next_cursor")

            for user in response["members"]:
                users.append(
                    {
                        "id": user["id"],
                        "name": user["name"],
                        "real_name": user.get("real_name"),
                        "profile": {
                            "image": user["profile"].get("image_72"),
                        },
                    }
                )

            if not cursor:
                break

        self.cached_users = users
        return users

    def get_user_by_id(self, user_id: str):
        return next((user for user in self.get_users() if user["id"] == user_id), None)

    def get_channel_history_events(self, channel_id: str, limit: int = DEFAULT_MESSAGES_LIMIT):
        viewed_message_ids = set()
        response_messages = wrap_rate_limit(self.app.client.conversations_history, channel=channel_id, limit=limit)
        for message in response_messages["messages"]:
            message_id = message["ts"]

            if not message.get("user"):
                continue

            # Regular messages do not have "subtype"!
            if message.get("subtype"):
                continue

            # Slack sometimes returns duplicate messages from API (mostly edited)
            if message_id in viewed_message_ids:
                continue
            viewed_message_ids.add(message_id)

            yield self._get_message_as_event(channel_id, message)
            yield from self._iter_reactions_as_events(channel_id, message)

            if message.get("reply_count", 0) == 0:
                continue

            response_replies = wrap_rate_limit(
                self.app.client.conversations_replies, channel=channel_id, ts=message_id, limit=limit
            )
            for reply in response_replies["messages"]:
                if reply["ts"] in viewed_message_ids:
                    continue
                viewed_message_ids.add(reply["ts"])
                yield self._get_message_as_event(channel_id, reply, is_thread=True)

    def _get_message_as_event(self, channel_id: str, message, is_thread=False):
        event = {
            "type": "message",
            "channel": channel_id,
            "channel_data": self.get_channel_by_id(channel_id),
            "user": message["user"],
            "user_data": self.get_user_by_id(message["user"]),
            "text": message["text"],
            "ts": message["ts"],
        }

        # Replies will have "thread_ts"
        if is_thread and message.get("thread_ts"):
            event["thread_ts"] = message["thread_ts"]

        return event

    def _iter_reactions_as_events(self, channel_id: str, message):
        for reaction in message.get("reactions", []):
            for user_id in reaction["users"]:
                yield {
                    "type": "reaction_added",
                    "user": user_id,
                    "user_data": self.get_user_by_id(user_id),
                    "reaction": reaction["name"],
                    "item": {
                        "type": "message",
                        "channel": channel_id,
                        "ts": message["ts"],
                    },
                    "event_ts": message["ts"],
                }

    def listen_for_commands(self, handler: Optional[GraphHandler] = None):
        help_command_regex = re.compile(r"^(help|info)$", re.IGNORECASE)
        personal_command_regex = re.compile(r"^(me|myself)\b.*?(<#.*?>)?", re.IGNORECASE)
        relationship_command_regex = re.compile(r"^(me|myself)\b.*?<@.*?>", re.IGNORECASE)
        channel_command_regex = re.compile(r"^channels?\b", re.IGNORECASE)
        message_command_regex = re.compile(r"^message\b", re.IGNORECASE)

        def _get_response_for_personal_command(event) -> str:
            """Text response for /influence (me|myself) (in #CHANNEL)?"""
            user_id = event["user_id"]
            message = event["text"]
            channel_id = get_channel_id_from_slack_message(message)

            all_channels = self.get_channels()
            channel = self.get_channel_by_id(channel_id)

            if channel_id and not channel:
                return response.get_unknown_channel_response(channel_id)

            if not channel_id and not all_channels:
                return response.get_no_visible_channels_response()

            channel_ids = [channel_id] if channel_id else [c["id"] for c in all_channels]
            word_counts = handler.influence_my_words(user_id, channel_id)
            reaction_counts = handler.influence_my_reactions(user_id, channel_id)

            channel_text = response.get_personal_channels_response(channel_ids)
            word_text = response.get_personal_words_response(word_counts)
            reaction_text = response.get_personal_reactions_response(reaction_counts)

            return f"{channel_text}\n\n{word_text} {reaction_text}"

        def _get_response_for_relationship_command(event) -> str:
            """Text response for /influence (me|myself) (and|with|&) [USER]"""
            user_id = event["user_id"]
            message = event["text"]
            another_user_id = get_user_id_from_slack_message(message)

            if not another_user_id:
                return response.get_unknown_user_response()

            if user_id == another_user_id:
                return response.get_invalid_self_check_user_response()

            reaction_counts = handler.influence_relationship_reactions(user_id, another_user_id)
            return response.get_relationship_reactions_response(another_user_id, reaction_counts)

        def _get_response_for_channel_command(event) -> str:
            """Text response for /influence channel [#CHANNEL] (and|with|&) reaction(s)? [REACTION...]"""
            message = event["text"]
            channel_id = get_channel_id_from_slack_message(message)
            reactions = get_reactions_from_slack_message(message)

            all_channels = self.get_channels()
            channel = self.get_channel_by_id(channel_id)

            if channel_id and not channel:
                return response.get_unknown_channel_response(channel_id)

            if not channel_id and not all_channels:
                return response.get_no_visible_channels_response()

            if not reactions:
                return response.get_unknown_reactions_response(channel_id)

            channel_ids = [channel_id] if channel_id else [c["id"] for c in all_channels]
            user_max_reactions = handler.influence_channel_send_max_reactions(reactions, channel_id)
            user_min_reactions = handler.influence_channel_send_min_reactions(reactions, channel_id)
            user_receive_reactions = handler.influence_channel_receive_max_reactions(reactions, channel_id)

            channel_text = response.get_channel_channels_response(channel_ids, reactions)
            user_max_reactions_text = response.get_user_max_reactions_response(reactions, user_max_reactions)
            user_min_reactions_text = response.get_user_min_reactions_response(reactions, user_min_reactions)
            user_receive_reactions_text = response.get_user_receive_reactions_response(
                reactions, user_receive_reactions
            )

            return f"{channel_text}\n\n{user_max_reactions_text}\n\n{user_min_reactions_text}\n\n{user_receive_reactions_text}"

        def _get_response_for_message_command(event) -> str:
            """Text response for /influence message [MESSAGE]"""
            message = event["text"]
            channel_id = event["channel_id"]
            user_message = re.sub(r"^\s*message\s+", "", message, flags=re.IGNORECASE)

            channel = self.get_channel_by_id(channel_id)
            if not channel:
                return response.get_unknown_channel_response(channel_id)

            words = handler.influence_message_words(user_message, channel_id)
            words_text = response.get_message_words_response(words)
            return f"{words_text}\n\n_Your original message:_\n{user_message}"

        def _get_response_for_command(event):
            message = event["text"]
            # Strip message because it is easier to regex match it (no need to note \s+)
            trimmed_message = re.sub(r"\s+", " ", message).strip()

            try:
                if help_command_regex.match(trimmed_message):
                    return response.get_help_response()

                if message_command_regex.match(trimmed_message):
                    return _get_response_for_message_command(event)

                if relationship_command_regex.match(trimmed_message):
                    return _get_response_for_relationship_command(event)

                if personal_command_regex.match(trimmed_message):
                    return _get_response_for_personal_command(event)

                if channel_command_regex.match(trimmed_message):
                    return _get_response_for_channel_command(event)
            except Exception as error:
                logger.error(error)
                return response.get_error_response(error)

            text = response.get_unknown_command_response()
            return f"{text}\n\n{response.get_help_response()}"

        @self.app.command("/influence")
        def handle_command_influence(ack, body):
            logger.info(f"New command: {json.dumps(body)}")
            ack()
            response_text = _get_response_for_command(body)

            chit_chat_text = ""
            if random.random() <= CHIT_CHAT_RESPONSE_CHANGE:
                chit_chat_text = f"{response.get_chit_chat_response()}\n\n"
            text = f"{chit_chat_text}{response_text}"

            loggable_text = re.sub(r"\s+", " ", text)
            logger.info(f"New command response: {loggable_text}")
            self.app.client.chat_postEphemeral(channel=body["channel_id"], user=body["user_id"], text=text)

    def listen_for_events(self, handler: Optional[EventHandler] = None):
        def _handle_event(event):
            logger.info(f"New processed event: {json.dumps(event)}")
            if handler:
                handler.handle_event(event)

        @self.app.event("member_joined_channel")
        def handle_channel_joined_event(event):
            logger.info(f"New event: {json.dumps(event)}")
            channel_id = event.get("channel")
            is_channel = event.get("channel_type") == "C"
            if not channel_id or not is_channel:
                logger.info(f"Skipped event because it is not a channel: {json.dumps(event)}")
                return

            # Refresh the channels cache (if it is a new channel)
            self.refresh_channels()

            events_count = 0
            for event in self.get_channel_history_events(channel_id):
                handler.handle_event(event)
                events_count += 1
            logger.info(f"Loaded {events_count} historical message and reaction events from the new channel {channel_id}")

        @self.app.event("message")
        def handle_message_event(event):
            logger.info(f"New event: {json.dumps(event)}")
            channel_id = event.get("channel")
            user_id = event.get("user")
            if not channel_id or not user_id:
                return
            processed_event = dict(
                **event, channel_data=self.get_channel_by_id(channel_id), user_data=self.get_user_by_id(user_id)
            )
            _handle_event(processed_event)

        @self.app.event("reaction_added")
        def handle_reaction_added_event(event):
            logger.info(f"New event: {json.dumps(event)}")
            user_id = event.get("user")
            if not user_id:
                return
            processed_event = dict(**event, user_data=self.get_user_by_id(user_id))
            _handle_event(processed_event)

        @self.app.event("reaction_removed")
        def handle_reaction_removed_event(event):
            logger.info(f"New event: {json.dumps(event)}")
            user_id = event.get("user")
            if not user_id:
                return
            processed_event = dict(**event, user_data=self.get_user_by_id(user_id))
            _handle_event(processed_event)

    def get_handler(self):
        return SocketModeHandler(self.app, self.slack_app_token)
