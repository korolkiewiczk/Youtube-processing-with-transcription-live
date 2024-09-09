import whisper
import argparse
import configparser
import os
import io
from audio_manager import download_audio_as_bytes, split_audio
from convert_audio_to_16000hz import convert_audio_to_16000hz
import logging
from keys import OPENAI_API_KEY
from pytube_pollyfill import fix_pytube_issues
from transcribe_audio import transcribe_audio
import openai
from pydub import AudioSegment
from pydub.silence import split_on_silence

from utils import get_data_folder, hash_url, save_transcription_to_file

def get_audio_data(url, folder, filename):
    file_path = get_data_folder(folder, filename)
    if os.path.exists(file_path):
        logger.info(f"File '{file_path}' already exists. Loading from disk.")
        with open(file_path, 'rb') as f:
            audio_data = f.read()
    else:
        logger.info(f'Downloading {url}')
        audio_data = download_audio_as_bytes(url)
        if audio_data:
            logger.info(f'Downloaded {len(audio_data)} bytes of audio.')
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            logger.info(f'File saved as {file_path}.')
        else:
            logger.error(f"Failed to download audio from {url}")
            exit()
    return audio_data

def process_audio(audio_data):
    transcription_result = ""
    frame_rate = 44000

    chunks = split_audio(audio_data, chunk_duration_ms=25000)

    for idx, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {idx + 1} of {len(chunks)}")

        logger.debug("Converting chunk to 16000Hz")
        _, audio = convert_audio_to_16000hz(logger, frame_rate, chunk.raw_data)

        logger.debug("Transcribing chunk")
        texts = transcribe_audio(logger, model, audio)

        transcription_result += ''.join(texts)

    return transcription_result

def process_audio_with_whisper_api(audio_data, whisper_model):
    openai.api_key = OPENAI_API_KEY
    client = openai.Audio()
    
    if len(audio_data) <= 25 * 1024 * 1024:
        return transcribe_audio(client, audio_data, whisper_model)

    logger.info('Splitting audio...')
    audio_chunks = split_audio_into_chunks(audio_data)
    logger.info(f'Number of chunks: {len(audio_chunks)}')
    
    transcriptions = transcribe_audio_chunks(client, audio_chunks, whisper_model)
    
    return " ".join(transcriptions)

def transcribe_audio(client, audio_data, whisper_model):
    audio_buffer = io.BytesIO(audio_data)
    audio_buffer.name = "audio.mp3"
    transcription = client.transcribe(
        model=whisper_model,
        file=audio_buffer,
        response_format="text"
    )
    return transcription

def split_audio_into_chunks(audio_data):
    audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
    chunk_duration = 1500000
    audio_chunks = [audio[i:i + chunk_duration] for i in range(0, len(audio), chunk_duration)]
    return audio_chunks

def transcribe_audio_chunks(client, audio_chunks, whisper_model):
    transcriptions = []
    for idx, chunk in enumerate(audio_chunks):
        chunk_buffer = io.BytesIO()
        chunk.export(chunk_buffer, format="mp3")
        chunk_buffer.name = f"audio_chunk_{idx}.mp3"
        chunk_buffer.seek(0)
        transcription = client.transcribe(
            model=whisper_model,
            file=chunk_buffer,
            response_format="text"
        )
        transcriptions.append(transcription)
    return transcriptions

# SETUP
fix_pytube_issues()

config = configparser.ConfigParser()
config.read('config.ini')

# Accessing the settings
logging_level = getattr(logging, config['LOGGING']['logging_level'])
logging.basicConfig(level=logging_level)  # Set the desired log level (e.g., INFO, DEBUG, WARNING, ERROR)
logger = logging.getLogger()

whisper_model = config.get('WHISPER', 'api_model_name')

parser = argparse.ArgumentParser(description='Download audio from YouTube and transcribe it.')
parser.add_argument('-c', '--url', type=str, required=True, help='URL of the YouTube video')
parser.add_argument('-a', '--api', action='store_true', help='Use API for transcription')

# MAIN CODE
args = parser.parse_args()

url = args.url

file_hash = hash_url(url)
folder = file_hash
filename = "record.mp3"

audio_data = get_audio_data(url, folder, filename)

if args.api:
    transcription = process_audio_with_whisper_api(audio_data, whisper_model)
    logger.debug(f"Final transcription\n{transcription}")
    save_transcription_to_file(transcription, file_hash, url)
else:
    model_name = config.get('WHISPER', 'model_name')
    device_name = config.get('WHISPER', 'device_name')

    logger.info('loading model')
    if device_name == 'gpu':
        model = whisper.load_model(model_name)
    else:
        model = whisper.load_model(model_name, device=device_name)
    transcription = process_audio(audio_data)
    logger.debug(f"Final transcription\n{transcription}")
    save_transcription_to_file(transcription, file_hash, url)
