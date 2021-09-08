import os


def get_required_env(name: str):
    env_value = os.getenv(name)
    if not env_value:
        raise Exception(f"Please define the following environment variable {name}")
    return env_value
