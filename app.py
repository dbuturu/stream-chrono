import os
import ffmpeg
import time
import datetime
import threading
import schedule
import configparser  # Module to load the config.ini file
from functools import wraps

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read("config.ini")

# Load values from the config.ini
ICECAST_URL = config.get("Icecast", "URL")
ICECAST_PASSWORD = config.get("Icecast", "Password")
REMOTE_SERVER = config.get("RemoteServer", "SyncPath")
AUDIO_DEVICE = config.get("Audio", "Device")

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
                        print(f"Max retries reached for {func.__name__}. Exiting.")
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


# Capture audio input, clean it, split it, and route it to two destinations


@retry_on_failure()
def start_audio_capture_and_split():
    # Modify based on your input source
    input_stream = ffmpeg.input(AUDIO_DEVICE, f="alsa")

    # Clean the audio stream
    cleaned_stream = clean_audio(input_stream)

    # Split the cleaned stream for two outputs
    split_stream = cleaned_stream.filter_multi_output(
        "asplit", 2
    )  # Splitting into 2 streams

    # Define the Icecast output stream
    icecast_output = ffmpeg.output(
        split_stream[0],  # Use the first split output for streaming
        f"icecast://voltron:{ICECAST_PASSWORD}@{ICECAST_URL}",
        acodec="libmp3lame",
        format="mp3",
    )

    # Define the local recording stream
    directory = create_directory_structure()
    current_time = datetime.datetime.now()
    filename = f"testfm_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp3"
    file_path = os.path.join(directory, filename)

    local_output = ffmpeg.output(
        split_stream[1],  # Use the second split output for local recording
        file_path,
        acodec="libmp3lame",
        format="mp3",
    )

    # Use `merge_outputs` to handle tee muxing and execute the command
    ffmpeg.merge_outputs(icecast_output, local_output).run()


# Schedule hourly recordings with overlap
@retry_on_failure()
def record_audio_locally():
    directory = create_directory_structure()
    current_time = datetime.datetime.now()
    filename = f"testfm_{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.mp3"
    file_path = os.path.join(directory, filename)

    # Create a recording stream that lasts 1 hour with a 10-minute overlap
    input_stream = ffmpeg.input(AUDIO_DEVICE, f="alsa")

    # Clean the audio before recording
    cleaned_stream = clean_audio(input_stream)

    # Split the stream for recording only (no need for streaming here)
    split_stream = cleaned_stream.filter_multi_output("asplit", 1)

    ffmpeg.output(
        split_stream[0],  # Use the split output for recording
        file_path,
        acodec="libmp3lame",
        format="mp3",
        t="01:10:00",  # Record for 1 hour 10 minutes
    ).run()


# Sync files to a remote server with retry logic


@retry_on_failure()
def sync_to_remote_server():
    os.system(f"rsync -avz recordings/ {REMOTE_SERVER}")


# Schedule the recordings
def schedule_recording():
    while True:
        schedule.every().hour.at(":00").do(record_audio_locally)
        time.sleep(1)


# Control logic to manage both streaming and recording
def control_logic():
    # Start audio splitting and streaming in a separate thread
    capture_thread = threading.Thread(target=start_audio_capture_and_split)
    capture_thread.start()

    # Schedule recordings
    schedule_recording()


# Main function
if __name__ == "__main__":
    try:
        control_logic()
    except KeyboardInterrupt:
        print("Stopping the system...")
