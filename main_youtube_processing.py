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

async def fetch_unprocessed_urls():
    records = airtable_url_inputs.get_all(filterByFormula="NOT({Processed})")
    return [(record['id'], record['fields']['Url']) for record in records]

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

async def create_transcription(url):
    hash_value = hash_url(url)
    file_path = get_data_folder(hash_value, "transcription.txt")
    
    # Check if the transcription file already exists
    if not os.path.exists(file_path):
        use_api = config.getboolean('WHISPER', 'use_api')
        command = ['python', 'main_transcribe_yt.py', '-c', url]
        if use_api:
            command.append('-a')
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=None, stderr=None
        )
        await process.communicate()
    else:
        logger.debug(f"Transcription {file_path} exists")

    return file_path, hash_value

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
        file_path, hash = await create_transcription(url)
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
        {"name": "Error", "type": "multilineText"}
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
            await process_url(record_id, url) 

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
