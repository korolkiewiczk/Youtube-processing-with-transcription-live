import configparser
import argparse
import logging
import json
from pathlib import Path

from gpt import get_completions
from utils import read_transcription_file, read_prompt_template, save_as_json_to_file, read_prompt_template

def divide_transcription(transcription, model, max_tokens, temperature):
    divide_prompt = read_prompt_template('divide_prompt.txt')
    prompt = divide_prompt.replace("{transcription}", transcription)
    parts = get_completions(prompt, model, max_tokens, temperature)
    return parts.split("\n\n")  # Assuming parts are separated by double newlines

def generate_summary(transcription, title, prompt_template, model, max_tokens, temperature):
    # Divide the transcription into parts
    parts = divide_transcription(transcription, model, max_tokens, temperature)
    logger.debug(f"Parts:\n{parts}")
    
    # Generate full document summary
    full_prompt = prompt_template.replace("{transcription}", transcription).replace("{title}", title)
    full_summary_json = get_completions(full_prompt, model, max_tokens, temperature)
    summary_data = json.loads(full_summary_json)

    # Read part prompt template
    description = summary_data["description"]
    part_prompt_template = read_prompt_template('part_prompt.txt').replace("{description}", description)
    part_summaries = []
    for part in parts:
        part_prompt = part_prompt_template.replace("{full_summary}", description).replace("{part}", part)
        part_summary = get_completions(part_prompt, model, max_tokens, temperature)
        part_summaries.append(part_summary)
    
    # Generate a single summary from part summaries
    part_summaries_text = "\n".join(part_summaries)
    part_summary_prompt = read_prompt_template('part_summary_prompt.txt').replace("{part_summaries}", part_summaries_text)
    full_summary = get_completions(part_summary_prompt, model, max_tokens, temperature)
    
    summary_data["summary"] = full_summary
    return summary_data

# INIT
config = configparser.ConfigParser()
config.read('config.ini')
gpt_model = config.get('GPT', 'gpt_model')
gpt_maxtokens = config.getint('GPT', 'gpt_maxtokens')
gpt_temperature = config.getfloat('GPT', 'gpt_temperature')
logging_level = getattr(logging, config['LOGGING']['logging_level'])
logging.basicConfig(level=logging_level)  # Set the desired log level (e.g., INFO, DEBUG, WARNING, ERROR)
logger = logging.getLogger()

parser = argparse.ArgumentParser(description='Script to generate a summary from a transcription.')
parser.add_argument('-f', '--file', type=str, required=True, help='Path to the input text file.')
args = parser.parse_args()
input_file_path = args.file
prompt_file_path = 'summary_prompt.txt'

# FILES
url, title, transcription = read_transcription_file(input_file_path)
prompt_template = read_prompt_template(prompt_file_path)

# SUMMARY
summary_data = generate_summary(transcription, title, prompt_template, gpt_model, gpt_maxtokens, gpt_temperature)
logger.debug(summary_data)
output_file_path_json = Path(input_file_path).with_name('summary.json')
save_as_json_to_file(json.dumps(summary_data), output_file_path_json)

# Save summary to summary.md
output_file_path_md = Path(input_file_path).with_name('summary.md')
with open(output_file_path_md, 'w', encoding='utf-8') as file:
    file.write(summary_data["summary"])
