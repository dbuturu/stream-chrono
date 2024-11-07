import os
import time
from chronostreamer.utils import (
    retry_on_failure,
    deferred_config_reload,
    load_config,
)

# Load configuration for the remote server path
config = load_config()

# Get initial config values
SYNC_INTERVAL = config.getint("ScheduleSettings", "SyncInterval")
REMOTE_SERVER_PATH = config.get("RemoteServer", "SyncPath")


@retry_on_failure()
def sync_to_remote_server(remote_path):
    os.system(f"rsync -avz recordings/ {remote_path}")


def scheduled_sync():
    """Scheduled task for syncing to the remote server
    with config reloading."""
    while True:
        deferred_config_reload()  # Reload configuration
        sync_to_remote_server(REMOTE_SERVER_PATH)  # Use updated path
        time.sleep(SYNC_INTERVAL * 60)  # Wait for the next sync interval
