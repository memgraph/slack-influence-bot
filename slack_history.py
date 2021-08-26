"""
Slack history handler

Handler can help you out to fetch the following:
    - A list of users
    - A list of channels where the bot is added
    - A list of events (messages, replies and reactions) where each
      event will match the structure of the Events API stream service

Before running a handler, make sure to set SLACK_BOT_TOKEN in your
environment.

Usage:
    slack_history.py users
    slack_history.py channels
    slack_history.py events [-n=LIMIT]
    slack_history.py -h | --help

Arguments:
    -h --help   Show this screen
    -n=LIMIT    Number of messages to fetch, max 1000 [default: 50]
"""

import os
import json
import time
from typing import Dict, Any
from slack_sdk import WebClient
from functools import lru_cache

slack_client = WebClient(os.environ["SLACK_BOT_TOKEN"])


def _wrap_rate_limit(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except SlackApiError as e:
        if e.response["error"] != "ratelimited":
            raise e

        # The `Retry-After` header will tell you how long to wait before retrying
        delay = int(e.response.headers['Retry-After'])
        time.sleep(delay)
        return func(*args, **kwargs)


@lru_cache(maxsize=None)
def get_channels():
    channels = []
    response = slack_client.conversations_list(types="public_channel,private_channel")
    for channel in response["channels"]:
        if channel["is_member"]:
            channels.append({
                "id" : channel["id"],
                "name" : channel["name"],
                "is_private": channel["is_private"]
            })
    return channels


@lru_cache(maxsize=None)
def get_channel_by_id(channel_id: str):
    return next((channel for channel in get_channels() if channel["id"] == channel_id), None)


@lru_cache(maxsize=None)
def get_users():
    users = []
    response = slack_client.users_list()
    for user in response["members"]:
        users.append({
            "id" : user["id"],
            "name" : user["name"],
            "real_name": user.get("real_name"),
            "profile": {
                "image": user["profile"].get("image_72"),
            }
        })
    return users


@lru_cache(maxsize=None)
def get_user_by_id(user_id: str):
    return next((user for user in get_users() if user["id"] == user_id), None)


def get_channel_events(channel_id: str, limit: int):
    viewed_message_ids = set()
    response_messages = _wrap_rate_limit(slack_client.conversations_history, channel=channel_id, limit=limit)
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

        yield _get_message_event(channel_id, message)
        yield from _get_reaction_events(channel_id, message)

        if message.get("reply_count", 0) > 0:
            response_replies = _wrap_rate_limit(slack_client.conversations_replies,
                channel=channel_id,
                ts=message_id,
                limit=limit)
            for reply in response_replies["messages"]:
                if reply["ts"] in viewed_message_ids:
                    continue
                viewed_message_ids.add(reply["ts"])
                yield _get_message_event(channel_id, reply, is_thread=True)


def _get_message_event(channel_id: str, message, is_thread=False):
    event = {
        "type": "message",
        "channel": channel_id,
        "channel_data": get_channel_by_id(channel_id),
        "user": message["user"],
        "user_data": get_user_by_id(message["user"]),
        "text": message["text"],
        "ts": message["ts"]
    }

    # Replies will have "thread_ts"
    if is_thread and message.get("thread_ts"):
        event["thread_ts"] = message["thread_ts"]

    return event


def _get_reaction_events(channel_id: str, message):
    for reaction in message.get("reactions", []):
        for user_id in reaction["users"]:
            yield {
                "type": "reaction_added",
                "user": user_id,
                "user_data": get_user_by_id(user_id),
                "reaction": reaction["name"],
                "item": {
                    "type": "message",
                    "channel": channel_id,
                    "ts": message["ts"],
                },
                "event_ts": message["ts"]
            }


def main(args: Dict[str, Any]):
    if args["users"]:
        for user in get_users():
            print(json.dumps(user))
        return

    if args["channels"]:
        for channel in get_channels():
            print(json.dumps(channel))
        return

    if args["events"]:
        for channel in get_channels():
            for event in get_channel_events(channel["id"], limit=int(args["-n"])):
                print(json.dumps(event))
        return


if __name__ == "__main__":
    from docopt import docopt
    main(docopt(__doc__))
