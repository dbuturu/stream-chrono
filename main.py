from chronostreamer.audio_processor import process_audio, schedule_recording
from chronostreamer.sync_manager import sync_to_remote_server
import threading
from chronostreamer.utils import load_config

# Load configuration for the remote server path
config = load_config()
REMOTE_SERVER_PATH = config.get("RemoteServer", "SyncPath")


def control_logic():
    threading.Thread(
        target=lambda: process_audio(stream_to_icecast=True, save_locally=True)
    ).start()
    schedule_recording()
    sync_to_remote_server(REMOTE_SERVER_PATH)


if __name__ == "__main__":
    try:
        control_logic()
    except KeyboardInterrupt:
        print("Stopping the system...")
