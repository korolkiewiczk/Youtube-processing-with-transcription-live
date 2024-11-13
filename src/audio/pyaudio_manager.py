import pyaudiowpatch as pyaudio

def initialize_pyaudio(p_audio: pyaudio.PyAudio):
    try:
    # Get default WASAPI info
        wasapi_info = p_audio.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        print("Looks like WASAPI is not available on the system. Exiting...")
        exit()

    default_speakers = p_audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

    if not default_speakers["isLoopbackDevice"]:
        for loopback in p_audio.get_loopback_device_info_generator():
            """
        Try to find loopback device with same name(and [Loopback suffix]).
        Unfortunately, this is the most adequate way at the moment.
        """
            if default_speakers["name"] in loopback["name"]:
                default_speakers = loopback
                break
        else:
            print("Default loopback output device not found.\n\nRun `python -m pyaudiowpatch` to check available devices.\nExiting...\n")
            exit()
    return default_speakers

def calculate_chunk_size(frame_rate):
    samples_per_ms = frame_rate / 1000  # Number of samples per millisecond
    samples_in_10ms = int(samples_per_ms * 10)  # Number of samples in 10 ms
    return samples_in_10ms

def get_device_info(default_speakers):
    channel = default_speakers["maxInputChannels"]
    frame_rate = int(default_speakers["defaultSampleRate"])
    chunk_size = calculate_chunk_size(frame_rate)
    input_index = default_speakers["index"]
    return channel,frame_rate,chunk_size,input_index


def get_stream(p_audio, audio_format, channel, frame_rate, chunk_size, input_index):
    stream = p_audio.open(
    format=audio_format,
    channels=channel,
    rate=frame_rate,
    input=True,
    input_device_index=input_index,
    frames_per_buffer=chunk_size,
)

    return stream