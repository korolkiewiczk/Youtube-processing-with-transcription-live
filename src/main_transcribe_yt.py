import argparse
import configparser
import io
import logging
import os
import whisper

from openai import OpenAI
from pydub import AudioSegment

from audio.audio_manager import download_audio_as_bytes, get_title_author, split_audio
from audio.convert_audio_to_16000hz import convert_audio_to_16000hz
from keys import OPENAI_API_KEY
from audio.transcribe_audio import transcribe_audio
from utils.utils import get_data_folder, hash_url, save_transcription_to_file
from utils.logging_setup import setup_logging

def get_audio_data(url, folder, filename, client):
    file_path = get_data_folder(folder, filename)
    title = None
    author = None
    if os.path.exists(file_path):
        logger.info(f"File '{file_path}' already exists. Loading from disk.")
        with open(file_path, 'rb') as f:
            audio_data = f.read()
            title, author = get_title_author(url)
    else:
        logger.info(f'Downloading {url}')
        audio_data, title, author = download_audio_as_bytes(url, client=client)
        if audio_data:
            logger.info(f'Downloaded {len(audio_data)} bytes of audio.')
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            logger.info(f'File saved as {file_path}.')
        else:
            logger.error(f"Failed to download audio from {url}")
            exit()
    return audio_data, title, author

def process_audio(audio_data):
    transcription_result = ""
    frame_rate = 44000

    chunks = split_audio(audio_data, chunk_duration_ms=chunk_duration_ms)

    for idx, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {idx + 1} of {len(chunks)}")

        logger.debug("Converting chunk to 16000Hz")
        _, audio = convert_audio_to_16000hz(logger, frame_rate, chunk.raw_data)

        logger.debug("Transcribing chunk")
        texts = transcribe_audio(logger, model, audio)

        transcription_result += ''.join(texts)

    return transcription_result

def process_audio_with_whisper_api(audio_data, whisper_model):
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    if len(audio_data) <= 25 * 1024 * 1024:
        return transcribe_audio_whisper(client, audio_data, whisper_model)

    logger.info('Splitting audio...')
    audio_chunks = split_audio_into_chunks(audio_data)
    logger.info(f'Number of chunks: {len(audio_chunks)}')
    
    transcriptions = transcribe_audio_chunks(client, audio_chunks, whisper_model)
    
    return " ".join(transcriptions)

def transcribe_audio_whisper(client, audio_data, whisper_model):
    audio_buffer = io.BytesIO(audio_data)
    audio_buffer.name = "audio.mp3"
    response = client.audio.transcriptions.create(
        model=whisper_model,
        file=audio_buffer
    )
    return response.text

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
        response = client.audio.transcriptions.create(
            model=whisper_model,
            file=chunk_buffer
        )
        transcriptions.append(response.text)
    return transcriptions

# SETUP

config = configparser.ConfigParser()
config.read('config.ini')

# Accessing the settings
logging_level = getattr(logging, config['LOGGING']['logging_level'])
# Set up logging
logger = setup_logging("youtube_processing", logging_level)

whisper_model = config.get('WHISPER', 'api_model_name')
chunk_duration_ms = config.getint('PROCESSING', 'chunk_duration_ms')

parser = argparse.ArgumentParser(description='Download audio from YouTube and transcribe it.')
parser.add_argument('-c', '--url', type=str, required=True, help='URL of the YouTube video')
parser.add_argument('-a', '--api', action='store_true', help='Use API for transcription')
parser.add_argument('--client', type=str, default='WEB_CREATOR', help='Client to use for YouTube download')

# MAIN CODE
args = parser.parse_args()

url = args.url

file_hash = hash_url(url)
folder = file_hash
filename = "record.mp3"

audio_data, title, author = get_audio_data(url, folder, filename, client=args.client)

if args.api:
    transcription = process_audio_with_whisper_api(audio_data, whisper_model)
    logger.debug(f"Final transcription\n{transcription}")
    save_transcription_to_file(transcription, file_hash, url, title, author)
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
    save_transcription_to_file(transcription, file_hash, url, title, author)
