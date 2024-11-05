import time
import configparser
from functools import wraps


def load_config(config_file="config.ini"):
    """Load configuration from a specified INI file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def retry_on_failure(max_retries=3, delay=1, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
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
