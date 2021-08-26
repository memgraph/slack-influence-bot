import random
from datetime import datetime
from typing import Optional


def format_user_id_for_slack_message(user_id: str):
    return f"<@{user_id}>"


def format_channel_id_for_slack_message(channel_id: str):
    return f"<#{channel_id}>"


def get_incorrect_today_day() -> str:
    index = datetime.today().weekday()
    days = [
        "it is Monday",
        "yesterday was Monday",
        "it is middle of the week",
        "tomorrow is Friday",
        "it is Friday",
        "it is the craziest Saturday",
        "it is crazy Sunday",
    ]
    return days[index]


def get_lazy_response() -> str:
    return random.choice([
        f"Hey, {get_incorrect_today_day()} so give me a break. I will get you the response in a sec!",
        "Woah, thanks for reaching out. Bare with me, I am preparing an answer :wink:",
        "While you wait, you can learn a bit about <https://www.youtube.com/watch?v=dQw4w9WgXcQ|graphs>!",
        "Today I am really slow, it was a drinking night. I am packaging the response",
        "Just a second...",
        "It takes a bit to get results so I would like to share a crazy story I heard: So apparently there " + \
        "was a team that managed to infiltrate a double agent into a company saying it will do recommendations, " + \
        "analytics, and all other buzzwords (Machine Learning :joy:) but they used it to spread gossip. What a time " + \
        "to be alive, ha?",
        "While we wait for the results, let me tell you a joke: Helvetica and Times New Roman walk into a bar... " + \
        "Meh, forget it, it is bad anyway.",
    ])


def get_missing_user_response() -> str:
    return random.choice([
        "Hey hey hey! You need to give me another user here, type @ and input the person you wish to check influence with",
        "Come on! You got it. Type @ and input a person name and we can continue",
    ])


def get_invalid_self_check_user_response() -> str:
    return random.choice([
        "Are you trying to be funny here by tagging yourself?",
        "I knew you will try this. If you wish to check the influence on yourself, use the command `/influence-me`",
    ])


def get_unknown_channel_response(formatted_channel_name) -> str:
    return random.choice([
        f"Never heard of the channel {format_channel_id_for_slack_message(channel_id)} (or it is private). You can " + \
        "add me there to sniff things around :smiling_imp:",
        f"Sorry sorry, but I am not part of the channel {format_channel_id_for_slack_message(channel_id)}. Aaaand it " + \
        "should be a public channel too.",
    ])
