# Slack Influence Bot

Slack bot that helps you understand and influence your slack community.

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
    * Name: `/influence`
    * Short description: `Influence the community`
    * Usage hint: `[help | me | channel | message]`
    * Escape channels, users, and links sent to your app: `Checked!`
5. Under **OAuth & Permissions* generate a **Bot User OAuth Token** and add the
   following scopes to "Bot Token Scopes":
    * `app_mentions:read`
    * `channels:history`, `channels:read`
    * `groups:history`, `groups:read`
    * `users:read`, `users.profile:read`
    * `chat:write`
    * `commands`
    * `reactions:read`
6. Under **Event Subscriptions** make sure to enable Events and to select the
   following events for "Subscribe to bot events":
   * `message.channels`
   * `message.groups`
   * `reaction_added`
   * `reaction_removed`
   * `member_joined_channel`
7. Add the bot to all the public channels that you want to handle with the project
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
cat events.json | python3 utils/kafka_json_producer.py slack-events
```
