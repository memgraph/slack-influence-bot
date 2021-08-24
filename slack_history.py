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
    -n=LIMIT    Number of messages to fetch [default: 50]
"""

import os
import json
from typing import Dict, Any
from slack import WebClient

slack_client = WebClient(os.environ["SLACK_BOT_TOKEN"])

def get_channels():
    response = slack_client.conversations_list()
    for channel in response["channels"]:
        if channel["is_member"]:
            yield {
                "id" : channel["id"],
                "name" : channel["name"]
            }

def get_users():
    response = slack_client.users_list()
    for user in response["members"]:
        yield {
            "id" : user["id"],
            "name" : user["name"],
            "real_name": user.get("real_name"),
            "profile": {
                "image_original": user["profile"].get("image_original"),
                "real_name": user["profile"].get("real_name"),
                "image_72": user["profile"].get("image_72"),
            }
        }


def get_channel_events(channel_id: str, limit: int):
    response_messages = slack_client.conversations_history(channel=channel_id, limit=limit)
    for message in response_messages["messages"]:
        if not message.get("user"):
            continue

        yield _get_message_event(channel_id, message)
        yield from _get_reaction_events(channel_id, message)

        if message.get("reply_count", 0) > 0:
            response_replies = slack_client.conversations_replies(
                channel=channel_id,
                ts=message["ts"],
                limit=limit)
            for reply in response_replies["messages"]:
                yield _get_message_event(channel_id, reply, is_thread=True)


def _get_message_event(channel_id: str, message, is_thread=False):
    event = {
        "type": "message",
        "channel": channel_id,
        "user": message["user"],
        "text": message["text"],
        "ts": message["ts"]
    }

    # Regular messages do not have "subtype"!
    if message.get("subtype"):
        event["subtype"] = message["subtype"]

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
