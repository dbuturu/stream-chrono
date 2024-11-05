import ffmpeg
from chronostreamer.audio_processor import clean_audio


def test_clean_audio():
    input_stream = ffmpeg.input("test_audio.wav")
    cleaned_stream = clean_audio(input_stream)

    # Verify the filters are applied correctly by inspecting the filter graph
    assert cleaned_stream is not None
    assert "highpass" in str(cleaned_stream)
    assert "lowpass" in str(cleaned_stream)
    assert "afftdn" in str(cleaned_stream)
