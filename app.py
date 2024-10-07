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
        input_stream.filter(
            "highpass", f=200
        )  # Remove low-frequency hum (below 200 Hz)
        .filter("lowpass", f=3000)  # Remove high-frequency noise (above 3 kHz)
        # Noise reduction, default noise amount is 15 dB
        .filter("afftdn", nr=15)
        .filter("loudnorm")  # Apply volume normalization
    )


# Unified function to capture, clean, and
# process audio for both streaming and recording
@retry_on_failure()
def process_audio(stream_to_icecast=True, save_locally=True):
    # Use pulse instead of ALSA for audio input
    input_stream = ffmpeg.input("default", f="pulse")  # pulse input

    # Clean the audio stream
    # cleaned_stream = clean_audio(input_stream)
    cleaned_stream = input_stream

    # Split the cleaned stream if we are both streaming and saving locally
    if stream_to_icecast and save_locally:
        split_stream = cleaned_stream.filter_multi_output(
            "asplit", 2
        )  # Splitting into 2 streams
    else:
        split_stream = [cleaned_stream]  # Only one output needed

    # Stream to Icecast if required
    if stream_to_icecast:
        icecast_output = ffmpeg.output(
            split_stream[0],  # Use the first stream for streaming
            f"icecast://voltron:{ICECAST_PASSWORD}@{ICECAST_URL}",
            acodec="libmp3lame",
            format="mp3",
        )

    # Save to local file if required
    if save_locally:
        directory = create_directory_structure()
        current_time = datetime.datetime.now()
        filename = f"testfm_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp3"
        file_path = os.path.join(directory, filename)

        local_output = ffmpeg.output(
            split_stream[-1],  # Use the second stream for local recording
            file_path,
            acodec="libmp3lame",
            format="mp3",
            t="01:10:00",  # Record for 1 hour 10 minutes
        )

    # Combine the outputs and execute
    if stream_to_icecast and save_locally:
        ffmpeg.merge_outputs(icecast_output, local_output).run()
    elif stream_to_icecast:
        icecast_output.run()
    elif save_locally:
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
