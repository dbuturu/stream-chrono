import os
import ffmpeg
import time
import datetime
import threading
import configparser  # Module to load the config.ini file
from functools import wraps

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read("config.ini")

# Load values from the config.ini
ICECAST_URL = config.get("Icecast", "URL")
ICECAST_PASSWORD = config.get("Icecast", "Password")
REMOTE_SERVER = config.get("RemoteServer", "SyncPath")

# Load retry settings
MAX_RETRIES = config.getint("RetrySettings", "MaxRetries")
RETRY_DELAY = config.getint("RetrySettings", "RetryDelay")
BACKOFF_FACTOR = config.getint("RetrySettings", "BackoffFactor")


# Max retries and backoff parameters
def retry_on_failure(
    max_retries=MAX_RETRIES, delay=RETRY_DELAY, backoff=BACKOFF_FACTOR
):
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
                        print(f"Error in {func.__name__}: {e}. Retrying in {
                            sleep_time
                        } seconds... (Retry {retries}/{max_retries})")
                        time.sleep(sleep_time)
                    else:
                        print(f"Max retries reached for {
                              func.__name__}. Exiting.")
                        raise

        return wrapper

    return decorator


# Create the directory structure for recordings
@retry_on_failure()
def create_directory_structure():
    today = datetime.datetime.now()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    day = today.strftime("%d")
    directory = os.path.join("recordings", "testfm", year, month, day)
    os.makedirs(directory, exist_ok=True)
    return directory


# Function to clean the audio using FFmpeg filters
def clean_audio(input_stream):
    return (
        input_stream.filter("highpass", f=80)  # Improved bass
        .filter("lowpass", f=12000)  # Keep treble details
        .filter("afftdn", nr=12, nt="w")  # Adaptive noise reduction
        # .filter("dynaudnorm", p=0.6, m=100)  # Dynamic range compression
        .filter("loudnorm", I=-16, TP=-1.5, LRA=11)  # Loudness normalization
    )


# Unified function to capture, clean, and
# process audio for both streaming and recording
@retry_on_failure()
def process_audio(stream_to_icecast=True, save_locally=True):
    # Use pulse instead of ALSA for audio input
    input_stream = ffmpeg.input("default", f="pulse")  # pulse input

    # Clean the audio stream
    cleaned_stream = clean_audio(input_stream)

    # Split the cleaned stream if we are both streaming and saving locally
    if stream_to_icecast and save_locally:
        split_stream = cleaned_stream.filter_multi_output("asplit", 2)
    else:
        split_stream = [cleaned_stream]  # Single stream

    # Remux and stream to Icecast without saving a file
    if stream_to_icecast:
        (
            ffmpeg.output(
                split_stream[0],  # First stream goes to Icecast
                f"icecast://source:{ICECAST_PASSWORD}@{ICECAST_URL}",
                acodec="libopus",  # Ogg/Opus codec for streaming
                format="ogg",  # Set format to ogg
                content_type="application/ogg",  # Set content type header
                audio_bitrate="96k",  # Bitrate for Icecast stream
                buffer_size="512k",  # Buffer size
            ).run()
        )

    # Save to local file if required
    if save_locally:
        directory = create_directory_structure()
        current_time = datetime.datetime.now()
        filename = f"testfm_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp3"
        file_path = os.path.join(directory, filename)

        # Output the second stream to MP3 for local recording
        local_output = ffmpeg.output(
            split_stream[-1],  # Use the second stream for local recording
            file_path,
            acodec="libmp3lame",  # MP3 codec
            format="mp3",  # Output format
            audio_bitrate="192k",  # Higher bitrate for local recording
            t="01:10:00",  # Record for 1 hour 10 minutes
            qscale="2",  # Quality scale for MP3
        )

        local_output.run()


# Sync files to a remote server with retry logic
@retry_on_failure()
def sync_to_remote_server():
    os.system(f"rsync -avz recordings/ {REMOTE_SERVER}")


# Schedule the recordings to start exactly at the start of the next hour
def schedule_recording():
    while True:
        now = datetime.datetime.now()

        # Calculate time until the top of the next hour
        next_hour = (now + datetime.timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
        time_until_next_hour = (next_hour - now).total_seconds()

        print(
            f"Waiting {time_until_next_hour:.0f} seconds"
            "until the next hour starts..."
        )

        # Sleep until the top of the next hour
        time.sleep(time_until_next_hour)

        # Start the recording at the top of the hour in a new thread
        threading.Thread(
            target=lambda: process_audio(
                stream_to_icecast=False,
                save_locally=True,
            )
        ).start()

        print(f"Started recording at {next_hour.strftime('%H:%M')}")

        # Sleep for a small period before checking for the next hour
        time.sleep(10)  # Short sleep to prevent immediate re-triggering


# Control logic to manage both streaming and recording
def control_logic():
    # Start audio processing for both
    # streaming and recording in a separate thread
    capture_thread = threading.Thread(
        target=lambda: process_audio(
            stream_to_icecast=True,
            save_locally=True,
        )
    )
    capture_thread.start()

    # Schedule hourly recordings
    schedule_recording()


# Main function
if __name__ == "__main__":
    try:
        control_logic()
    except KeyboardInterrupt:
        print("Stopping the system...")
