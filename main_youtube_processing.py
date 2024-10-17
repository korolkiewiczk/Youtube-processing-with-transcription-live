import asyncio
import configparser
import logging
import os
from pathlib import Path
from airtable import Airtable
import json
from logging_setup import setup_logging
from airtable_manager import ensure_table_exists
from keys import AIRTABLE_API_KEY, AIRTABLE_BASE_ID
from utils import get_data_folder, hash_url, read_transcription_file
from urllib.parse import urlparse

async def fetch_unprocessed_urls():
    records = airtable_url_inputs.get_all(filterByFormula="NOT({Processed})")
    return [(record['id'], record['fields']['Url']) for record in records if 'Url' in record['fields']]

async def mark_url_as_processed(record_id):
    airtable_url_inputs.update(record_id, {"Processed": True})

async def save_summary_to_airtable(summary_json, url, title, author, hash):
    summary_data = json.loads(summary_json)  # Converts JSON string to dictionary
    summary_data = {key.capitalize(): value for key, value in summary_data.items()}
    summary_data['Title'] = title
    summary_data['Author'] = author
    summary_data['Url'] = url
    summary_data['Hash'] = hash

    airtable_youtube_summaries.insert(summary_data)

async def create_transcription(url, record_id):

    transcription_file_name = "transcription.txt"

    file_path = get_data_folder(hash_url(url), transcription_file_name)
    if os.path.exists(file_path):
        logger.info(f"Trancription file {file_path} already exists...")
        return file_path, hash_url(url)

    clients = [
        'WEB_EMBED', 'WEB_CREATOR', 'WEB_MUSIC', 'WEB_SAFARI',
        'ANDROID', 'WEB', 'ANDROID_MUSIC', 'ANDROID_CREATOR', 'ANDROID_VR', 'ANDROID_PRODUCER', 'ANDROID_TESTSUITE',
        'IOS', 'IOS_MUSIC', 'IOS_CREATOR',
        'MWEB', 'TV_EMBED', 'MEDIA_CONNECT'
    ]
    max_retries = 5
    retries = 0

    # Get current retry count from Airtable
    record = airtable_url_inputs.get(record_id)
    if 'Retries' in record['fields']:
        retries = record['fields']['Retries']

    while retries < max_retries:
        client = clients[retries % len(clients)]
        logger.info(f"Attempt {retries + 1} with client {client}")

        use_api = config.getboolean('WHISPER', 'use_api')
        command = ['python', 'main_transcribe_yt.py', '-c', url, '--client', client]
        if use_api:
            command.append('-a')

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=None, stderr=None
        )
        await process.communicate()

        file_path = get_data_folder(hash_url(url), transcription_file_name)
        if os.path.exists(file_path):
            return file_path, hash_url(url)

        retries += 1
        airtable_url_inputs.update(record_id, {"Retries": retries})

    logger.error(f"Failed to transcribe {url} after {max_retries} attempts")
    airtable_url_inputs.update(record_id, {"Processed": True, "Error": "Too many attempts"})
    return None, None

async def summarize_transcription(file_path):
    json_file_path = Path(file_path).with_name('summary.json')
    
    process = await asyncio.create_subprocess_exec(
        'python', 'main_gpt_summary.py', '-f', file_path,
        stdout=None, stderr=None
    )
    await process.communicate()

    # Read the summary from the generated JSON file with UTF-8 encoding
    with open(json_file_path, 'r', encoding='utf-8') as f:
        summary = f.read()

    return summary

async def process_url(record_id, url):
    try:
        file_path, hash = await create_transcription(url, record_id)
        if not file_path:
            return
        url, title, author, _ = read_transcription_file(file_path)

        summary_json = await summarize_transcription(file_path)
        await save_summary_to_airtable(summary_json, url, title, author, hash)
        await mark_url_as_processed(record_id)

    except Exception as e:
        logger.error(f"Failed to process {url}: {str(e)}")
        airtable_url_inputs.update(record_id, {"Processed": True, "Error": str(e)})

async def create_tables():
    await ensure_table_exists(URL_INPUTS_TABLE, [
        {"name": "Url", "type": "singleLineText"},
        {
            "name": "Processed",
            "type": "checkbox",
            "options": {
                "color": "greenBright",
                "icon": "check"
            }
        },
        {"name": "Error", "type": "multilineText"},
        {
            "name": "Retries",
            "type": "number",
            "options": {
                "precision": 0
            }
        }
    ])

    await ensure_table_exists(YOUTUBE_SUMMARIES_TABLE, [
        {"name": "Title", "type": "singleLineText"},
        {"name": "Author", "type": "singleLineText"},
        {"name": "Description", "type": "multilineText"},
        {"name": "Summary", "type": "multilineText"},
        {"name": "Url", "type": "singleLineText"},
        {"name": "Category", "type": "singleLineText"},
        {"name": "Hash", "type": "singleLineText"}
    ])

async def process_loop():
    await create_tables()

    while True:
        urls = await fetch_unprocessed_urls()
        if not urls:
            await asyncio.sleep(sleep_time)
            continue

        for record_id, url in urls:
            parsed_url = urlparse(url)
            if parsed_url.scheme and parsed_url.netloc:
                await process_url(record_id, url)
            else:
                logger.warning(f"Invalid URL: {url}")
                airtable_url_inputs.update(record_id, {"Processed": True, "Error": "Invalid URL"})

        await asyncio.sleep(sleep_time) 

config = configparser.ConfigParser()
config.read('config.ini')

URL_INPUTS_TABLE = config.get('AIRTABLE', 'inputs_table_name')
YOUTUBE_SUMMARIES_TABLE = config.get('AIRTABLE', 'summaries_table_name')

sleep_time = config.getint('PROCESSING', 'sleep_time')


# Airtable instance
airtable_url_inputs = Airtable(AIRTABLE_BASE_ID, URL_INPUTS_TABLE, AIRTABLE_API_KEY)
airtable_youtube_summaries = Airtable(AIRTABLE_BASE_ID, YOUTUBE_SUMMARIES_TABLE, AIRTABLE_API_KEY)

# Accessing the settings
logging_level = getattr(logging, config['LOGGING']['logging_level'])
# Set up logging
logger = setup_logging("youtube_processing", logging_level)

asyncio.run(process_loop())
