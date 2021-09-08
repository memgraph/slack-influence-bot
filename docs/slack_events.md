# Slack events

## New message

Notes:

* If the `channel_type == 'channel'`, it is a message in a public channel.
* If the `channel_type == 'group'`, it is a message in a private channel.
* If the `channel_type == 'message_changed'`, the message content updated.
* If there is a key `thread_ts`, it is a thread message where the value is
  the source message on which the thread is created.

Example:

```json
{
  "client_msg_id": "400df46e-1111-2222-3333-44ff33555444",
  "type": "message",
  "text": "It is a message",
  "user": "U022Q0ZERT2",
  "ts": "1629885191.020400",
  "team": "T0F242E3B",
  "thread_ts": "1629881871.018500",
  "parent_user_id": "U022Q0ZERT2",
  "channel": "CSR01RS80",
  "event_ts": "1629885191.020400",
  "channel_type": "channel",
  "blocks": [
    {
      "type": "rich_text",
      "block_id": "mfD",
      "elements": [
        {
          "type": "rich_text_section",
          "elements": [
            {
              "type": "text",
              "text": "It is a message"
            }
          ]
        }
      ]
    }
  ]
}
```

## Reaction added

Notes:

* The value of `item.ts` is a timestamp of a message where the user
  added a reaction.

Example:

```json
{
  "type": "reaction_added",
  "user": "U12345678",
  "item": {
    "type": "message",
    "channel": "C12345678",
    "ts": "1629742385.001000"
  },
  "reaction": "wink",
  "item_user": "U12345678",
  "event_ts": "1629884735.000100"
}
```

## Reaction removed

Notes:

* The value of `item.ts` is a timestamp of a message where the user
  removed a reaction.

Example:

```json
{
  "type": "reaction_removed",
  "user": "U12345678",
  "item": {
    "type": "message",
    "channel": "C12345678",
    "ts": "1629742385.001000"
  },
  "reaction": "wink",
  "item_user": "U12345678",
  "event_ts": "1629884735.000100"
}
```

## Channel joined

Example:

```json
{
  "type": "member_joined_channel",
  "user": "W06GH7XHN",
  "channel": "C0698JE0H",
  "channel_type": "C",
  "team": "T024BE7LD",
  "inviter": "U123456789"
}
```
