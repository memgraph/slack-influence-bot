# Entropy-crusade

Changing the way of how influence is created in Slack.

* [Requirements](#requirements)
* [Quick start](#quick-start)

## Requirements

* [Docker >= 20.0.0](https://docs.docker.com/get-docker/)
* [Slack bot app](https://slack.com/intl/en-hr/help/articles/115005265703-Create-a-bot-for-your-workspace)

## Quick start

### Setup Slack bot application

Make sure to setup a Slack bot application where you will need 
two tokens for the application to work

* Application token: `xapp-...` _(step 2 below)_
* Bot token: `xoxb-...` _(step 5 below)_

Follow the steps below to create the bot, setup scopes and get the tokens:

1. Create a Slack app if you don't already have one, or select 
   an existing app you've created.
2. Under **Basic Information > App-Level Tokens** create a new **App Token**
   with a scope `connections:write`.
3. Under **Socket Mode** make sure to enable the socket mode.
4. Under **Slash Commands** create the following commands:
    * TBD
    * TBD
5. Under **OAuth & Permissions* generate a **Bot User OAuth Token** and add the
   following scopes to "Bot Token Scopes":
    * `app_mentions:read`
    * `channels:history`, `channels:read`
    * `chat:write`
    * `commands`
    * `groups:history`, `groups:read`
    * `im:history`, `im:read`
    * `reactions:read`
    * `users:read`, `users.profile:read`
6. Under **Event Subscriptions** make sure to enable Events and to select the
   following events for "Subscribe to bot events":
   * `message.channels`
   * `message.groups`
   * `reaction_added`
   * `reaction_removed`
7. Add the bot to all the public/private channels that you want to handle with
   the project
8. Once you have two tokens, feel free to save them locally in the `.env` file
   in the following format:
   
```
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
```

### Start the platform

#### Environment

Before starting a platform that consists of the Slack bot application, Kafka,
Zookeeper, and Memgraph, make sure to have environment variables `SLACK_BOT_TOKEN`
and `SLACK_APP_TOKEN` defined.

You can check if the environment variables are set by calling the following command:

```bash
docker-compose config
```

In the output you should see the values of your tokens in the following two lines:

```
...
      - SLACK_BOT_TOKEN=xoxb-...
      - SLACK_APP_TOKEN=xapp-...
...
```

#### Build and run

Run the platform with the following command:

```
docker-compose up
```

#### Tools

#### Connect to Memgraph

Download [Memgraph Lab](https://memgraph.com/download) and connect to running Memgraph:

```
Username: <Empty>
Password: <Empty>
Endpoint: localhost 7687
Encrypted: Off
``` 

#### Connect to Kafka

If you wish the check the state of Kafka and the topic where slack events have been
produced to, run the following command:

```
docker run -it -p 9000:9000 -e KAFKA_BROKERCONNECT=localhost:9092 obsidiandynamics/kafdrop
```

> Note: If you are running Docker on Mac or Windows, the value of `KAFKA_BROKERCONNECT`
> should be `host.docker.internal:9093`.

Open up the internet browser and to the address [localhost:9000](http://localhost:9000).


### Load the historical data

When you start the platform you will start to receive events from that point on.
If you wish to include messages and reactions from public/private channels where
bot is member of, you can use the utility functions to load up the last N messages
(including reactions and thread replies) from channels:

```
# Get 100 messages (with threads and reactions) from public/private channels where
# bot is member of and forward it to the local file `events.json`
python3 slack_history.py events -n=100 > events.json

# For every slack historical event, forward it to the Kafka so Memgraph can fetch it
# and update the graph model
cat events.json | python3 utils/kafka_json_producer.json slack-events
```

## Events

### New message

Notes:

* If the `channel_type == 'channel'`, it is a message in a public channel.
* If the `channel_type == 'group'`, it is a message in a private channel.
* If the `channel_type == 'message_changed'`, the message content updated.
* If there is a key `thread_ts' it is a thread message where the value is
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

### Reaction added

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

### Reaction removed

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
