import time
import configparser
from functools import wraps


def deferred_config_reload():
    """Reloads configuration settings dynamically for scheduled tasks."""
    global config, SYNC_INTERVAL, REMOTE_SERVER_PATH, ICECAST_URL, ICECAST_USERNAME, ICECAST_PWD, MAX_RETRIES, RETRY_DELAY, BACKOFF_FACTOR, RECORDING_ROOT_DIR, FILE_LENGTH
    config = load_config()
    SYNC_INTERVAL = config.getint("ScheduleSettings", "SyncInterval")
    REMOTE_SERVER_PATH = config.get("RemoteServer", "SyncPath")
    ICECAST_URL = config.get("Icecast", "URL")
    ICECAST_USERNAME = config.get("Icecast", "Username")
    ICECAST_PWD = config.get("Icecast", "Password")
    MAX_RETRIES = config.getint("RetrySettings", "MaxRetries")
    RETRY_DELAY = config.getint("RetrySettings", "RetryDelay")
    BACKOFF_FACTOR = config.getint("RetrySettings", "BackoffFactor")
    RECORDING_ROOT_DIR = config.get("LocalRecording", "RecordingRootDir")
    FILE_LENGTH = config.getint("LocalRecording", "FileLength")


def load_config(config_file="config.ini"):
    """Load configuration from a specified INI file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def save_config(config, filename="config.ini"):
    """
    Saves the configuration dictionary to an INI file.

    Args:
        config (dict): The configuration data to save.
        filename (str): The path to the config file (default is "config.ini").
    """
    config_parser = configparser.ConfigParser()

    # Add sections and settings to the config
    for section, settings in config.items():
        config_parser[section] = settings

    try:
        with open(filename, "w") as config_file:
            config_parser.write(config_file)
        print("Configuration saved successfully.")
    except Exception as e:
        print(f"Error saving configuration: {e}")


def retry_on_failure(max_retries=3, delay=1, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    deferred_config_reload()
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries < max_retries:
                        sleep_time = delay * (backoff ** (retries - 1))
                        print(
                            f"Error in {func.__name__}: {e}. "
                            f"Retrying in {sleep_time} seconds... "
                            f"(Retry {retries}/{max_retries})"
                        )
                        time.sleep(sleep_time)
                    else:
                        print(
                            f"Max retries reached for {func.__name__}. ",
                            "Exiting.",
                        )
                        raise

        return wrapper

    return decorator
