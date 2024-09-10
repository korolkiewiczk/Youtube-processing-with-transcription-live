import hashlib
import json
import os
import random
import re

def get_random_color():
    color_palette = ['#99341e',
        '#1e9934',
        '#1e3499',
        '#991e99',
        '#99691e',
        '#1e9969',
        '#691e99',
        '#1e6999',
        '#991e1e',
        '#1e9949',
        '#693499',
        '#34991e',
        '#89341e',
        '#1e9634',
        '#341e99',
        '#991e69',
        '#69991e',
        '#99591e',
        '#1e6949',
        '#691e49',
        '#791e1e',
        '#1e6934',
        '#1e3499',
        '#991e89',
        '#996934',
        '#1e9969',
        '#69341e',
        '#346999',
        '#341e69',
        '#699934',
        '#691e79',
        '#1e5934']
    return random.choice(color_palette)


def console_loop(shared_queue):
    global still_listening
    try:
        while True:
            if input() == 'c':
                shared_queue.put(None)  # Send termination signal to the queue
                still_listening = False
                break
    except KeyboardInterrupt:
        pass


def change_font_size(event, text_font):
    # Check if Control key is pressed
    if event.state & 0x0004:
        new_size = text_font.cget("size")
        if event.delta > 0:
            new_size += 1  # Increase font size
        else:
            new_size -= 1  # Decrease font size
        new_size = max(new_size, 8)  # Set a minimum font size
        text_font.configure(size=new_size)


def find_sentences(text):
    # Split the text into sentences based on punctuation
    sentences = re.split(r'(?<=[.?!])(\s+)', text)
    # Find start and end indices of each sentence in the text
    indices = []
    start = 0
    skip_next = False
    for sentence in sentences:
        if skip_next:
            skip_next = False
            continue

        # Check if next item is whitespace and include it in the current sentence
        if sentences.index(sentence) < len(sentences) - 1:
            next_item = sentences[sentences.index(sentence) + 1]
            if next_item.isspace():
                sentence += next_item
                skip_next = True

        end = start + len(sentence)
        indices.append((start, end))
        start = end

    return indices

# FILES

def get_data_folder(folder, file_name):
    folder_path = f"data/{folder}/"
    
    # Check if the folder exists, if not, create it
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Return the full path with the provided file name, if any
    if file_name:
        return os.path.join(folder_path, file_name)
    return folder_path

def save_transcription_to_file(transcription, file_hash, youtube_url):
    file_path = get_data_folder(file_hash, "transcription.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"{youtube_url}\n")
        f.write(transcription)

def hash_url(url):
    return hashlib.sha1(url.encode()).hexdigest()

def read_transcription_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        url = lines[0].strip()
        transcription = ''.join(lines[1:]).strip()
    return url, transcription

def read_prompt_template(prompt_file_name):
    prompt_file_path = f'prompts/{prompt_file_name}'
    with open(prompt_file_path, 'r', encoding='utf-8') as file:
        prompt_template = file.read()
    return prompt_template

def save_as_json_to_file(json_text, output_file_path):
    with open(output_file_path, 'w', encoding='utf-8') as file:
        json.dump(json.loads(json_text), file, ensure_ascii=False, indent=4)
