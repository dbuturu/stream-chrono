import threading
import time
from chronostreamer.audio_processor import process_audio, schedule_recording
from chronostreamer.sync_manager import sync_to_remote_server
from chronostreamer.utils import load_config

# Initial configuration load
config = load_config()

# Get initial config values
SYNC_INTERVAL = config.getint("ScheduleSettings", "SyncInterval")
REMOTE_SERVER_PATH = config.get("RemoteServer", "SyncPath")


def deferred_config_reload():
    """Reloads configuration settings dynamically for scheduled tasks."""
    global config, SYNC_INTERVAL, REMOTE_SERVER_PATH
    config = load_config()
    SYNC_INTERVAL = config.getint("ScheduleSettings", "SyncInterval")
    REMOTE_SERVER_PATH = config.get("RemoteServer", "SyncPath")


def scheduled_audio_processing():
    """Scheduled task for processing audio with config reloading."""
    while True:
        deferred_config_reload()  # Reload configuration
        threading.Thread(
            target=lambda: process_audio(
                stream_to_icecast=True,
                save_locally=True,
            )
        ).start()
        time.sleep(10)  # Sleep until the next cycle


def scheduled_sync():
    """Scheduled task for syncing to the remote server
    with config reloading."""
    while True:
        deferred_config_reload()  # Reload configuration
        sync_to_remote_server(REMOTE_SERVER_PATH)  # Use updated path
        time.sleep(SYNC_INTERVAL * 60)  # Wait for the next sync interval


def control_logic():
    # Start audio processing and syncing in separate threads
    threading.Thread(target=scheduled_audio_processing).start()
    threading.Thread(target=schedule_recording).start()
    threading.Thread(target=scheduled_sync).start()


if __name__ == "__main__":
    try:
        control_logic()
    except KeyboardInterrupt:
        print("Stopping the system...")
