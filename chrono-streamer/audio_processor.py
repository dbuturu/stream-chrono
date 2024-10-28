import os
import ffmpeg
import time
import threading
from datetime import datetime, timedelta
from chrono_streamer.utils import retry_on_failure, load_config

# Load configuration from config.ini
config = load_config()

# Load Icecast and retry settings from config.ini
ICECAST_URL = config.get("Icecast", "URL")
ICECAST_USERNAME = config.get("Icecast", "Username")
ICECAST_PWD = config.get("Icecast", "Password")
MAX_RETRIES = config.getint("RetrySettings", "MaxRetries")
RETRY_DELAY = config.getint("RetrySettings", "RetryDelay")
BACKOFF_FACTOR = config.getint("RetrySettings", "BackoffFactor")


@retry_on_failure(
    max_retries=MAX_RETRIES,
    delay=RETRY_DELAY,
    backoff=BACKOFF_FACTOR,
)
def create_directory_structure():
    today = datetime.now()
    directory = os.path.join(
        "recordings",
        "testfm",
        today.strftime("%Y"),
        today.strftime("%m"),
        today.strftime("%d"),
    )
    os.makedirs(directory, exist_ok=True)
    return directory


def clean_audio(input_stream):
    return (
        input_stream.filter("highpass", f=80)
        .filter("lowpass", f=12000)
        .filter("afftdn", nr=12, nt="w")
        .filter("loudnorm", I=-16, TP=-1.5, LRA=11)
    )


@retry_on_failure()
def process_audio(
    input_source="default",
    input_is_network=False,
    stream_to_icecast=True,
    save_locally=True,
):
    input_stream = ffmpeg.input(
        input_source if input_is_network else "default", f="pulse"
    )
    cleaned_stream = clean_audio(input_stream)

    split_stream = (
        cleaned_stream.filter_multi_output("asplit", 2)
        if stream_to_icecast and save_locally
        else [cleaned_stream]
    )

    if stream_to_icecast:
        ffmpeg.output(
            split_stream[0],
            f"icecast://{ICECAST_USERNAME}:{ICECAST_PWD}@{ICECAST_URL}",
            acodec="libopus",
            format="ogg",
            content_type="application/ogg",
            audio_bitrate="96k",
            buffer_size="512k",
        ).global_args("-hide_banner").run()

    if save_locally:
        directory = create_directory_structure()
        filename = f"testfm_{
            datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp3"
        ffmpeg.output(
            split_stream[-1],
            os.path.join(directory, filename),
            acodec="libmp3lame",
            format="mp3",
            audio_bitrate="192k",
            t="01:10:00",
            q_a="2",
        ).global_args("-hide_banner").run()


def schedule_recording():
    while True:
        next_hour = (datetime.now() + timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
        time_until_next_hour = (next_hour - datetime.now()).total_seconds()
        time.sleep(time_until_next_hour)

        threading.Thread(
            target=lambda: process_audio(
                stream_to_icecast=False,
                save_locally=True,
            )
        ).start()
        time.sleep(10)
