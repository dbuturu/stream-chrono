import threading
import json
from chronostreamer.audio_processor import process_audio, schedule_recording
from chronostreamer.sync_manager import scheduled_sync
from chronostreamer.utils import load_config, deferred_config_reload


class SystemControlCenter:
    def __init__(self):
        self.config = load_config()
        self.is_streaming = False
        self.is_syncing = False

    def toggle_streaming(self, enable: bool):
        """Toggle streaming functionality."""
        self.is_streaming = enable
        if enable:
            self.start_streaming()
        else:
            self.stop_streaming()

    def toggle_syncing(self, enable: bool):
        """Toggle syncing functionality."""
        self.is_syncing = enable
        if enable:
            threading.Thread(target=scheduled_sync).start()
        else:
            self.stop_syncing()

    def start_streaming(self):
        threading.Thread(
            target=lambda: process_audio(
                stream_to_icecast=True,
                save_locally=True,
            )
        ).start()
        schedule_recording()

    def stop_streaming(self):
        print("Stopping streaming...")

    def stop_syncing(self):
        print("Stopping syncing...")

    def update_config(self, new_config):
        """Update configuration settings."""
        self.config.update(new_config)
        deferred_config_reload()

    def get_system_status(self):
        """Fetch the current status of the system."""
        status = {
            "is_streaming": self.is_streaming,
            "is_syncing": self.is_syncing,
        }
        return json.dumps(status)


# Example usage
control_center = SystemControlCenter()

# Toggle functions
control_center.toggle_streaming(True)
control_center.toggle_syncing(True)
