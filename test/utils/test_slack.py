from pytest import mark
from slack_influence_bot.utils.slack import (
    format_user_id_for_slack_message,
    get_channel_id_from_slack_message,
    get_user_id_from_slack_message,
)


@mark.parametrize(
    "user_id, expected_message",
    [
        ("", "<@>"),
        ("U129S", "<@U129S>"),
    ],
)
def test_format_user_id_for_slack_message(user_id, expected_message):
    assert format_user_id_for_slack_message(user_id) == expected_message


@mark.parametrize(
    "message, user_id",
    [
        ("user <@U0F242E3T|john.wayne>", "U0F242E3T"),
        ("user <@U0F242E3T>", None),
        ("user @U0F242E3T", None),
    ],
)
def test_get_user_id_from_slack_message(message, user_id):
    assert get_user_id_from_slack_message(message) == user_id


@mark.parametrize(
    "message, channel_id",
    [
        ("channel <#C0F242E3T|general> and reaction :fire:", "C0F242E3T"),
        ("channel <#C0F242E3T> and reaction :fire:", None),
        ("channel #C0F242E3T and reaction :fire:", None),
    ],
)
def test_get_channel_id_from_slack_message(message, channel_id):
    assert get_channel_id_from_slack_message(message) == channel_id
