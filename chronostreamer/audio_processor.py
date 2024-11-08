import os
import ffmpeg
import time
import threading
from datetime import datetime, timedelta
from chronostreamer.utils import (
    retry_on_failure,
    load_config,
    deferred_config_reload,
)

# Load configuration from config.ini
config = load_config()

# Load Icecast and retry settings from config.ini
ICECAST_URL = config.get("Icecast", "URL")
ICECAST_USERNAME = config.get("Icecast", "Username")
ICECAST_PWD = config.get("Icecast", "Password")
MOUNT_POINT = config.get("Icecast", "MountPoint")
MAX_RETRIES = config.getint("RetrySettings", "MaxRetries")
RETRY_DELAY = config.getint("RetrySettings", "RetryDelay")
BACKOFF_FACTOR = config.getint("RetrySettings", "BackoffFactor")

# Load audio processing settings
HIGHPASS_FILTER = config.getint("AudioSettings", "HighPassFilter")
LOWPASS_FILTER = config.getint("AudioSettings", "LowPassFilter")
NOISE_REDUCTION = config.getint("AudioSettings", "NoiseReduction")
NOISE_TYPE = config.get("AudioSettings", "NoiseType")
INTEGRATED_LOUDNESS_TARGET = config.getfloat("AudioSettings", "IntegratedLoudnessTarget")
LOUDNESS_RANGE_TARGET = config.getint("AudioSettings", "LoudnessRangeTarget")
TRUE_PEAK = config.getfloat("AudioSettings", "TruePeak")
AUDIO_CODEC = config.get("AudioSettings", "AudioCodec")
AUDIO_FORMAT = config.get("AudioSettings", "AudioFormat")
STREAM_AUDIO_BITRATE = config.get("AudioSettings", "AudioBitrate")
BUFFER_SIZE = config.get("AudioSettings", "BufferSize")

# Load local recording settings
LOCAL_AUDIO_CODEC = config.get("LocalRecording", "AudioCodec")
LOCAL_AUDIO_FORMAT = config.get("LocalRecording", "AudioFormat")
LOCAL_AUDIO_BITRATE = config.get("LocalRecording", "AudioBitrate")
FILE_LENGTH = config.get("LocalRecording", "FileLength")
RECORDING_ROOT_DIR = config.get("LocalRecording", "RecordingRootDir") #"recordings"


@retry_on_failure(
    max_retries=MAX_RETRIES,
    delay=RETRY_DELAY,
    backoff=BACKOFF_FACTOR,
)
def create_directory_structure():
    today = datetime.now()
    directory = os.path.join(
        RECORDING_ROOT_DIR,
        MOUNT_POINT,
        today.strftime("%Y"),
        today.strftime("%m"),
        today.strftime("%d"),
    )
    os.makedirs(directory, exist_ok=True)
    return directory


def clean_audio(input_stream):
    return (
        input_stream.filter("highpass", f=HIGHPASS_FILTER)
        .filter("lowpass", f=LOWPASS_FILTER)
        .filter("afftdn", nr=NOISE_REDUCTION, nt=NOISE_TYPE)
        .filter("loudnorm", I=INTEGRATED_LOUDNESS_TARGET, TP=TRUE_PEAK, LRA=LOUDNESS_RANGE_TARGET)
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
        threading.Thread(
            target=lambda: output_to_icecast(split_stream)).start()

    if save_locally:
        threading.Thread(target=lambda: output_to_file(split_stream)).start()


@retry_on_failure()
def output_to_icecast(split_stream):
    ffmpeg.output(
        split_stream[0],
        f"icecast://{ICECAST_USERNAME}:{ICECAST_PWD}@{ICECAST_URL}",
        acodec=AUDIO_CODEC,
        format=AUDIO_FORMAT,
        content_type="application/ogg",
        audio_bitrate=STREAM_AUDIO_BITRATE,
        buffer_size=BUFFER_SIZE,
    ).global_args("-hide_banner").run()


@retry_on_failure()
def output_to_file(split_stream):
    directory = create_directory_structure()
    datetime_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{MOUNT_POINT}_{datetime_now}.{LOCAL_AUDIO_FORMAT}"

    ffmpeg.output(
        split_stream[-1],
        os.path.join(directory, filename),
        acodec=LOCAL_AUDIO_CODEC,
        format=LOCAL_AUDIO_FORMAT,
        audio_bitrate=LOCAL_AUDIO_BITRATE,
        t=FILE_LENGTH,
    ).global_args("-hide_banner").run()


def schedule_recording():
    while True:
        deferred_config_reload()
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
