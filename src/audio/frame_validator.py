import numpy as np

def is_valid_frame(frame, frame_rate, frame_duration_ms):
    """
    Check if the frame is valid for webrtcvad.

    :param frame: The audio frame to check.
    :param frame_rate: The sample rate of the audio (8000, 16000, 32000, or 48000).
    :param frame_duration_ms: The duration of the frame in milliseconds (10, 20, or 30).
    :return: True if the frame is valid, False otherwise.
    """
    # Check if the sample rate is valid
    if frame_rate not in [8000, 16000, 32000, 48000]:
        return False

    # Calculate the number of samples in the frame
    num_samples = frame_rate * frame_duration_ms // 1000

    # Calculate the expected frame size in bytes (16-bit audio = 2 bytes per sample)
    expected_frame_size = num_samples * 2

    # Check if the frame size matches the expected size
    if len(frame) != expected_frame_size:
        return False

    return True


def stereo_to_mono(stereo_frame):
    # Assuming stereo_frame is a NumPy array with shape (2, N) where N is the number of samples
    mono_frame = np.mean(stereo_frame, axis=0)
    return mono_frame.astype(stereo_frame.dtype)


def to_mono(data):
    stereo_frame = np.frombuffer(data, dtype=np.int16)
    stereo_frame = stereo_frame.reshape(-1, 2).T
    mono_frame = stereo_to_mono(stereo_frame).tobytes()
    return mono_frame