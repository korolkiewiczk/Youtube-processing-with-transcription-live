import io
from pytubefix import YouTube
import ffmpeg
from pydub import AudioSegment

def download_audio_as_bytes(youtube_url, client='WEB_CREATOR'):
    yt = YouTube(youtube_url, client=client)
    audio_stream = yt.streams.filter(only_audio=True).first()

    audio_buffer = io.BytesIO()
    audio_stream.stream_to_buffer(audio_buffer)
    audio_buffer.seek(0)

    process = (
        ffmpeg
        .input('pipe:0')
        .output('pipe:1', format='mp3')
        .run_async(pipe_stdin=True, pipe_stdout=True, pipe_stderr=True)
    )

    stdout, _ = process.communicate(input=audio_buffer.read())

    return stdout, yt.title, yt.author

def get_title_author(youtube_url):
    yt = YouTube(youtube_url)
    return yt.title, yt.author

def split_audio(audio_data, chunk_duration_ms):
    audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
    chunks = []

    for i in range(0, len(audio), chunk_duration_ms):
        chunks.append(audio[i:i + chunk_duration_ms])

    return chunks
