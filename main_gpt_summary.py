import configparser
import argparse
import logging
from pathlib import Path

from gpt import get_completions
from utils import read_transcription_file, read_prompt_template, save_as_json_to_file

def generate_summary(url, transcription, prompt_template, model, max_tokens, temperature):
    prompt = prompt_template.replace("{url}", url).replace("{transcription}", transcription)
    return get_completions("", prompt, model, max_tokens, temperature)

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
parser.add_argument('-p', '--prompt', type=str, default='summary_prompt.txt', help='Path to the prompt template file (with {url} & {transcription} tags)')
args = parser.parse_args()
input_file_path = args.file
prompt_file_path =  args.prompt

# FILES
url, transcription = read_transcription_file(input_file_path)
prompt_template = read_prompt_template(prompt_file_path)

# SUMMARY
summary_json = generate_summary(url, transcription, prompt_template, gpt_model, gpt_maxtokens, gpt_temperature)
logger.debug(summary_json)
output_file_path = Path(input_file_path).with_name('summary.json')
save_as_json_to_file(summary_json, output_file_path)
