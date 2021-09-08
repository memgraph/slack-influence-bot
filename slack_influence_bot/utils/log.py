import logging

LOGGER_NAME = "slack_influence_bot"

logging.basicConfig(format="%(asctime)-15s [%(levelname)s]: %(message)s")
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.INFO)
