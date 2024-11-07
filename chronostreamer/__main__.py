import threading
from chronostreamer.audio_processor import process_audio, schedule_recording
from chronostreamer.sync_manager import scheduled_sync


def control_logic():
    threading.Thread(
        target=lambda: process_audio(
            stream_to_icecast=True,
            save_locally=True,
        )
    ).start()
    threading.Thread(target=scheduled_sync).start()
    schedule_recording()


if __name__ == "__main__":
    try:
        control_logic()
    except KeyboardInterrupt:
        print("Stopping the system...")
