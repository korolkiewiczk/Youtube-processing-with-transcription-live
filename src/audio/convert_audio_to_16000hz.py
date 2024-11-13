import numpy as np
import logging
import time
import numpy as np
import subprocess

def convert_audio_buffer(audio_buffer, sr, osr):
    """
    Convert an in-memory audio buffer using FFmpeg.

    Parameters:
    - audio_buffer: The audio buffer (as a bytes object or NumPy array).
    - sr: Sample rate of the audio.

    Returns:
    - The converted audio buffer.
    """
    # If the input is a NumPy array, convert it to bytes
    if isinstance(audio_buffer, np.ndarray):
        audio_buffer = audio_buffer.tobytes()

    # Define the FFmpeg command for conversion
    command = [
        'ffmpeg',
        '-hide_banner',
        '-loglevel', 'error',
        '-f', 's16le',  # Input format
        '-ar', str(sr),  # Input sample rate
        '-ac', '2',  # Number of audio channels in input
        '-i', 'pipe:0',  # Read from stdin
        '-f', 's16le',  # Output format
        '-acodec', 'pcm_s16le',  # Output codec
        '-ar', str(osr),  # Output sample rate
        '-ac', '1',  # Number of audio channels in output
        'pipe:1'  # Write to stdout
    ]

    # Start the FFmpeg process
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Send the audio buffer and read the output
    out, err = process.communicate(input=audio_buffer)

    # Check for errors
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg returned error: {err.decode()}")

    return out

def convert_audio_to_16000hz(logger: logging, frame_rate, all_frames):
    start_time = time.time()  # Start timing

    converted_buffer = convert_audio_buffer(all_frames, frame_rate, 16000)
    max = np.iinfo(np.int16).max
    audioi = np.frombuffer(converted_buffer, np.int16)
    audio = np.frombuffer(audioi, np.int16).astype(np.float32) / max

    end_time = time.time()  # End timing
    execution_time = (end_time - start_time) * 1000
    logger.debug(f"Convert time: {execution_time} milliseconds")
    return converted_buffer,audio