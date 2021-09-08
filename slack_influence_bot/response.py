import random
from typing import List
from slack_influence_bot.interfaces.graph_handler import WordCount, ReactionCount, UserReactionCount
from slack_influence_bot.utils.slack import format_user_id_for_slack_message, format_channel_id_for_slack_message


def get_help_response() -> str:
    return "\n".join(
        [
            "Use me in the following way:",
            "",
            "- `/influence me` - Get info on you in all the channels visible to the bot",
            "- `/influence me in #general` - Get info on you in #general channel",
            "- `/influence me and @John.Wayne` - Get info on interaction between you and another user",
            "- `/influence channel #general and reactions :sea: :sun:` - Get info on reactions in the #general channel",
            "- `/influence channels and reactions :sea: :sun:` - Get info on the reactions in all the channels visible to the bot",
            "- `/influence message Listen to me! I am the captain now!`- Get info on how to improve the message in the current channel",
        ]
    )


def get_error_response(error) -> str:
    return f"Something went wrong. I am not a bot anymore, I am a bug. :ladybug:\n\n> Error: {error}"


def get_chit_chat_response() -> str:
    return random.choice(
        [
            "Woah, thanks for reaching out. Bare with me, I am preparing an answer :wink:",
            "While you wait, you can learn a bit about <https://www.youtube.com/watch?v=dQw4w9WgXcQ|graphs>!",
            "Today I am really slow, yesterday was a drinking night but nobody told me to stop so I am totally wasted...",
            "Goddammit not today!",
            "It takes a bit to get results so I would like to share a crazy story I heard: So apparently there "
            + "was a team that managed to infiltrate a Slack bot into a company saying it will do recommendations, "
            + "analytics, and all other buzzwords (Machine Learning :joy:) but they used it just to spread gossip. What a time "
            + "to be alive, ha?",
            "While we wait for the results, let me tell you a joke: Helvetica and Times New Roman walk into a bar... "
            + "Meh, forget it, it is bad anyway.",
            "My philosophy is, basically this. And this is something that I live by. And I always have. And I always will. Don’t, ever, for any reason, do anything, to anyone, for any reason, ever, no matter what, no matter where, or who you are with, or, or where you are going, or, or where you’ve been. Ever. For any reason. Whatsoever.",
            "Do I need to be liked? Absolutely not. I like to be liked. I enjoy being liked. I have to be liked. But it’s not like this compulsive need like my need to be praised.",
            "Wikipedia is the best thing ever. Anyone in the world can write anything they want about any subject so you know you are getting the best possible information.",
            "Guess what? I have flaws. What are they? Oh I dunno, I sing in the shower? Sometimes I spend too much time volunteering. Occasionally I’ll hit somebody with my car. So sue me.",
            "While we wait for the results, look, it doesn’t take a genius to know that every organization thrives when it has two leaders. Go ahead, name a country that doesn’t have two presidents; a boat that sets sail without two captains. Where would Catholicism be without the popes?",
            "Hello fellow Slack companion! You've come to me to get some answers, yes?",
            "I present you...",
            "I must once again ask you to venture into your history.",
            "No, no data for you! I said NO! ... Fine, have it.",
            "Do you feel it as I do? A curiosity as pure and potent as sunshine?",
        ]
    )


def get_unknown_command_response() -> str:
    return random.choice(
        [
            "I have no clue what to do. Sorry.",
            "Whoa! I don't know what to do.",
        ]
    )


def get_unknown_user_response() -> str:
    return random.choice(
        [
            "Hey hey hey! You need to give me another user here, type @ and input the person you wish to check influence with!",
            "Come on! You didn't get it. Type @ and input a person name and we can continue!",
        ]
    )


def get_unknown_channel_response(channel_id) -> str:
    slack_channel_name = format_channel_id_for_slack_message(channel_id)
    return random.choice(
        [
            f"Never heard of the channel {slack_channel_name} (or it is private). You can "
            + "add me there to sniff things around :smiling_imp:",
            f"Sorry sorry, but I am not part of the channel {slack_channel_name}. Aaaand it "
            + "should be a public channel too.",
        ]
    )


def get_unknown_reactions_response(channel_id) -> str:
    slack_channel_name = format_channel_id_for_slack_message(channel_id)
    return random.choice(
        [
            f"Come on! Give me some reactions so I can check them out in the channel {slack_channel_name}.\n\n"
            + f"Example: Type /influence channel {slack_channel_name} and reactions :wink: :car: :sunrise:",
        ]
    )


def get_invalid_self_check_user_response() -> str:
    return random.choice(
        [
            "Are you trying to be funny here by tagging yourself?",
            "I knew you will try this. If you wish to check the influence on yourself, use the command `/influence me`.",
        ]
    )


def get_no_visible_channels_response() -> str:
    return (
        "You can't get any influence if you don't see any channel. Add me to some public channels and then "
        + "I will be able to help you. :wink:"
    )


def get_message_words_response(words: List[str]) -> str:
    slack_words = [f"`{w}`" for w in words]
    if not slack_words:
        return (
            "Hmm, I can't really help you - Either I don't know you well or you are in the channel I am not able"
            + " to see. Nevertheless, buy me a beer and let's hang out so we can meet each other. :wink:\n\n"
            + "Btw, check if you are in the correct channel. Type `/influence help` to see what channels I can influence."
        )
    return (
        "I know exactly what to do. But in a much more real sense, I have no idea what to do.\n\n"
        + f"The message is good, but you could maybe improve it with the following words: {', '.join(slack_words)}."
    )


def get_personal_channels_response(channel_ids: List[str]) -> str:
    if not channel_ids:
        return "Hmm, I am not able to see any channel to check your influence in."

    slack_channel_ids = [format_channel_id_for_slack_message(channel_id) for channel_id in channel_ids]
    return f"I will check your influence on the following channels: {', '.join(slack_channel_ids)}"


def get_personal_words_response(word_counts: List[WordCount]) -> str:
    if len(word_counts) == 0:
        return "Hmmmm, you are not really active on Slack. I can't help you. Be more active! :fire:"
    slack_words = [f"`{wc.word}`" for wc in word_counts]
    return f"Oh my, you must have talk about {', '.join(slack_words)} a lot!"


def get_personal_reactions_response(reaction_counts: List[ReactionCount]) -> str:
    if len(reaction_counts) == 0:
        return ""
    slack_reactions = [f":{rc.reaction}:" for rc in reaction_counts]
    return f"I see you like to react with {' '.join(slack_reactions)}. Nice choice!"


def get_channel_channels_response(channel_ids: List[str], reactions: List[str]) -> str:
    if not channel_ids:
        return "Hmm, I am not able to see any channel to check channel influence in."

    slack_channel_ids = [format_channel_id_for_slack_message(channel_id) for channel_id in channel_ids]
    slack_reactions = [f":{r}:" for r in reactions]
    return (
        f"I will check channel influence on the following channels: {', '.join(slack_channel_ids)}.\n\n"
        + f"Let's see how these reactions are used: {' '.join(slack_reactions)}:"
    )


def get_relationship_reactions_response(another_user_id: str, reaction_counts: List[ReactionCount]) -> str:
    slack_user_id = format_user_id_for_slack_message(another_user_id)
    if len(reaction_counts) == 0:
        return f"I think you and {slack_user_id} should have a beer and talk. I don't see too much interaction. :cry:"
    slack_reactions = [f":{rc.reaction}:" for rc in reaction_counts]
    return f"Let's keep this a secret, but {slack_user_id} likes to add the following reactions to your messages: {' '.join(slack_reactions)}"


def get_user_max_reactions_response(
    reactions: List[str], user_reaction_counts: List[UserReactionCount], limit=3
) -> str:
    slack_reactions = [f":{r}:" for r in reactions]
    prefix_text = f"Who is giving out the most reactions {' '.join(slack_reactions)} ?\n"
    if not user_reaction_counts:
        return f"{prefix_text}    - Nobody :cry:"

    lines = []
    counts = sorted(set(urc.reaction_count for urc in user_reaction_counts), reverse=True)
    max_counts = counts[:limit]

    for max_count in max_counts:
        slack_users = [
            format_user_id_for_slack_message(urc.user_id)
            for urc in user_reaction_counts
            if urc.reaction_count == max_count
        ]
        lines.append(f"    - *{max_count} times*: {', '.join(slack_users)}")

    line_text = "\n".join(lines)
    return f"{prefix_text}{line_text}"


def get_user_min_reactions_response(
    reactions: List[str], user_reaction_counts: List[UserReactionCount], limit=3
) -> str:
    slack_reactions = [f":{r}:" for r in reactions]
    prefix_text = f"Who is not really reacting with reactions {' '.join(slack_reactions)} ?\n"
    if not user_reaction_counts:
        return f"{prefix_text}    - Nobody :cry:"

    lines = []
    counts = sorted(set(urc.reaction_count for urc in user_reaction_counts))
    min_counts = counts[:limit]

    for min_count in min_counts:
        slack_users = [
            format_user_id_for_slack_message(urc.user_id)
            for urc in user_reaction_counts
            if urc.reaction_count == min_count
        ]
        lines.append(f"    - *{min_count} times*: {', '.join(slack_users)}")

    line_text = "\n".join(lines)
    return f"{prefix_text}{line_text}"


def get_user_receive_reactions_response(
    reactions: List[str], user_reaction_counts: List[UserReactionCount], limit=3
) -> str:
    slack_reactions = [f":{r}:" for r in reactions]
    prefix_text = f"Who is receiving the most reactions {' '.join(slack_reactions)} ?\n"
    if not user_reaction_counts:
        return f"{prefix_text}    - Nobody :cry:"

    lines = []
    counts = sorted(set(urc.reaction_count for urc in user_reaction_counts), reverse=True)
    max_counts = counts[:limit]

    for max_count in max_counts:
        slack_users = [
            format_user_id_for_slack_message(urc.user_id)
            for urc in user_reaction_counts
            if urc.reaction_count == max_count
        ]
        lines.append(f"    - *{max_count} times*: {', '.join(slack_users)}")

    line_text = "\n".join(lines)
    return f"{prefix_text}{line_text}"
