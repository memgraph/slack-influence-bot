import re
import time
from typing import Optional, Any, Callable
from slack_sdk.errors import SlackApiError


def wrap_rate_limit(func: Callable, *args, **kwargs) -> Any:
    try:
        return func(*args, **kwargs)
    except SlackApiError as e:
        if e.response["error"] != "ratelimited":
            raise e

        # The `Retry-After` header will tell you how long to wait before retrying
        delay = int(e.response.headers["Retry-After"])
        time.sleep(delay)
        return func(*args, **kwargs)


def format_user_id_for_slack_message(user_id: str) -> str:
    return f"<@{user_id}>"


def format_channel_id_for_slack_message(channel_id: str) -> str:
    return f"<#{channel_id}>"


def format_url_for_slack_message(url: str, title: str = "") -> str:
    return f"<{url}|{title or url}>"


def get_user_id_from_slack_message(message: str) -> Optional[str]:
    users = re.findall(r"<@(U[A-Z0-9]+)\|.*?>", message)
    return users[0] if users else None


def get_channel_id_from_slack_message(message: str) -> Optional[str]:
    channels = re.findall(r"<#(C[A-Z0-9]+)\|.*?>", message)
    return channels[0] if channels else None


def get_reactions_from_slack_message(message: str) -> Optional[str]:
    return re.findall(r":([a-z0-9-_+]+):", message)
