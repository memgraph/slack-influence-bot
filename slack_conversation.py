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
        "Today I am really slow, yesterday was a drinking night but nobody told me to stop so I am totally wasted...",
        "Goddammit not today!",
        "It takes a bit to get results so I would like to share a crazy story I heard: So apparently there " + \
        "was a team that managed to infiltrate a Slack bot into a company saying it will do recommendations, " + \
        "analytics, and all other buzzwords (Machine Learning :joy:) but they used it just to spread gossip. What a time " + \
        "to be alive, ha?",
        "While we wait for the results, let me tell you a joke: Helvetica and Times New Roman walk into a bar... " + \
        "Meh, forget it, it is bad anyway.",
        "My philosophy is, basically this. And this is something that I live by. And I always have. And I always will. Don’t, ever, for any reason, do anything, to anyone, for any reason, ever, no matter what, no matter where, or who you are with, or, or where you are going, or, or where you’ve been. Ever. For any reason. Whatsoever.",
        "Do I need to be liked? Absolutely not. I like to be liked. I enjoy being liked. I have to be liked. But it’s not like this compulsive need like my need to be praised.",
        "Wikipedia is the best thing ever. Anyone in the world can write anything they want about any subject so you know you are getting the best possible information.",
        "Guess what? I have flaws. What are they? Oh I dunno, I sing in the shower? Sometimes I spend too much time volunteering. Occasionally I’ll hit somebody with my car. So sue me.",
        "While we wait for the results, look, it doesn’t take a genius to know that every organization thrives when it has two leaders. Go ahead, name a country that doesn’t have two presidents; a boat that sets sail without two captains. Where would Catholicism be without the popes?",
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


def get_personal_prefix_response() -> str:
    return random.choice([
        "Hello fellow Slacker! You've come to me to get some answers, yes?",
        "I present you...",
        "I must once again ask you to venture into your history, Slacker.",
        "No, no data for you! I said NO! ... Fine, have it.",
        "Do you feel it as I do, Slacker? A curiosity as pure and potent as sunshine?",
    ])

