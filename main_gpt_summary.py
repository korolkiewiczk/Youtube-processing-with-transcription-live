import configparser
import argparse
import logging
import json
from pathlib import Path
import tiktoken
from logging_setup import setup_logging
from gpt import get_completions
from utils import find_nearest_sentence_boundary, read_transcription_file, read_prompt_template, save_as_json_to_file, read_prompt_template

separator_char = "†"
description_field = "description"
category_field = "category"
summary_field = "summary"

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
    summary_data = get_summary_data(transcription, title, prompt_template, model, max_tokens, temperature)

    # Read part prompt template
    description = summary_data[description_field]
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
    
    summary_data[summary_field] = full_summary
    return summary_data

def get_summary_data(transcription, title, prompt_template, model, max_tokens, temperature):
    full_prompt = prompt_template.replace("{transcription}", transcription).replace("{title}", title)
    full_summary_json = get_completions(full_prompt, model, max_tokens, temperature)
    summary_data = json.loads(full_summary_json)
    return summary_data

def replace_summarized_if_needed(prompt_template, summary_data, title, model, maxtokens, temperature):
    dagger_index = summary_data[description_field].find(separator_char, 0)
    if dagger_index > 0:
        description = summary_data[description_field]
        description = description.replace(separator_char, " ")
        new_summary_data = get_summary_data(description, title, prompt_template, model, maxtokens, temperature)
        summary_data[description_field] = new_summary_data[description_field]
        summary_data[category_field] = new_summary_data[category_field]

def count_tokens(text, model):
    tokenizer = tiktoken.encoding_for_model(model)
    tokens = tokenizer.encode(text)
    return len(tokens)

def generate_summary_recursive(transcription, title, prompt_template, model, max_tokens, temperature, token_limit, overlap_percentage):
    transcription_tokens = count_tokens(transcription, model)
    
    if transcription_tokens <= token_limit:
        return generate_summary(transcription, title, prompt_template, model, max_tokens, temperature)

    logger.info(f"Transcription has {transcription_tokens} tokens ({transcription_tokens - token_limit} above than limit)")
    midpoint = len(transcription) // 2
    overlap_size = int(len(transcription) * overlap_percentage)
    part1_end = find_nearest_sentence_boundary(transcription, midpoint + overlap_size, 1)
    part2_start = find_nearest_sentence_boundary(transcription, midpoint - overlap_size, -1)

    part1 = transcription[:part1_end]
    part2 = transcription[part2_start:]

    summary_part1 = generate_summary_recursive(part1, title, prompt_template, model, max_tokens, temperature, token_limit, overlap_percentage)
    summary_part2 = generate_summary_recursive(part2, title, prompt_template, model, max_tokens, temperature, token_limit, overlap_percentage)

    combined_summary = merge_summaries(summary_part1, summary_part2)
    
    return combined_summary

def merge_summaries(summary_part1, summary_part2):
    combined_description = summary_part1[description_field] + separator_char + summary_part2[description_field]
    combined_summary = summary_part1[summary_field] + "\n\n" + summary_part2[summary_field]
    combined_category = summary_part1[category_field] if summary_part1[category_field] == summary_part2[category_field] else summary_part1[category_field] + ", " + summary_part2[category_field]
    
    return {
        description_field: combined_description,
        summary_field: combined_summary,
        category_field: combined_category
    }

# INIT
config = configparser.ConfigParser()
config.read('config.ini')
gpt_model = config.get('GPT', 'gpt_model')
gpt_maxtokens = config.getint('GPT', 'gpt_maxtokens')
gpt_temperature = config.getfloat('GPT', 'gpt_temperature')
logging_level = getattr(logging, config['LOGGING']['logging_level'])
token_limit = config.getint('PROCESSING', 'token_limit')
overlap_percentage = config.getfloat('PROCESSING', 'overlap_percentage')
# Set up logging
logger = setup_logging("youtube_processing", logging_level)

parser = argparse.ArgumentParser(description='Script to generate a summary from a transcription.')
parser.add_argument('-f', '--file', type=str, required=True, help='Path to the input text file.')
args = parser.parse_args()
input_file_path = args.file
prompt_file_path = 'summary_prompt.txt'

# FILES
url, title, _, transcription = read_transcription_file(input_file_path)
prompt_template = read_prompt_template(prompt_file_path)

# SUMMARY
summary_data = generate_summary_recursive(transcription, title, prompt_template, gpt_model, gpt_maxtokens, gpt_temperature, token_limit, overlap_percentage)
replace_summarized_if_needed(prompt_template, summary_data, title, gpt_model, gpt_maxtokens, gpt_temperature)
logger.debug(summary_data)
output_file_path_json = Path(input_file_path).with_name('summary.json')
save_as_json_to_file(json.dumps(summary_data), output_file_path_json)

# Save summary to summary.md
output_file_path_md = Path(input_file_path).with_name('summary.md')
with open(output_file_path_md, 'w', encoding='utf-8') as file:
    file.write(summary_data[summary_field])
