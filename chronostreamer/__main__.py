import threading
from chronostreamer.audio_processor import process_audio, schedule_recording
from chronostreamer.sync_manager import scheduled_sync
from chronostreamer.thread_manager import ThreadManager
from chronostreamer.utils import deferred_config_reload, load_config

config = load_config()
thread_manager = ThreadManager()


def get_status():
    return {
        "threads": thread_manager.list_threads(),
        "config": {key: config[key] for key in config.keys()},
    }


def toggle_feature(feature, enable):
    if feature == "streaming":
        if enable:
            thread_manager.start_thread(
                "audio_stream",
                process_audio,
                (True, True),
            )
        else:
            thread_manager.stop_thread("audio_stream")
    # More feature toggles here
    return {"status": "updated"}


def control_logic():
    # Initialize the Thread Manager
    thread_manager = ThreadManager()
    deferred_config_reload()

    if config.getboolean("SystemSettings", "EnableStreaming"):
        thread_manager.start_thread(
            "audio_stream",
            process_audio,
            (True, True),
        )

    if config.getboolean("SystemSettings", "EnableSync"):
        thread_manager.start_thread("scheduled_sync", scheduled_sync)

    if config.getboolean("SystemSettings", "EnableRecording"):
        thread_manager.start_thread("schedule_recording", schedule_recording)

    print(thread_manager.list_threads())
    # Monitor and handle shutdown
    return thread_manager


if __name__ == "__main__":
    try:
        thread_manager = control_logic()
    except KeyboardInterrupt:
        # TODO: add thread stopping functionality on exit.
        print("Stopping the system...")
