import tkinter as tk
import configparser
from tkinter import scrolledtext
from tkinter import font
import pyaudiowpatch as pyaudio
import whisper
import threading
import queue
import webrtcvad
import logging

from convert_audio_to_16000hz import convert_audio_to_16000hz
from utils import change_font_size, find_sentences, get_random_color
from gpt import get_completions
from gpt_stream import get_completions_stream
from pyaudio_manager import get_device_info, get_stream, initialize_pyaudio
from frame_validator import is_valid_frame, to_mono
from save_wav import save_wav
from transcribe_audio import transcribe_audio

### FUNCTIONS ###

def read_stream(stream, chunk, frame_rate, shared_queue):
    vad = webrtcvad.Vad(vad_mode)
    frames = []
    silent_frames = 0
    while still_listening:
        data = stream.read(chunk)
        mono_frame = to_mono(data)
        is_speech = False
        if is_valid_frame(mono_frame, frame_rate, 10):
            is_speech = vad.is_speech(mono_frame, frame_rate)
        else:
            logger.error("Invalid frame")

        frames.append(data)

        if not is_speech:
            silent_frames += 1
        else:
            silent_frames = 0

        # Check if the accumulated frames exceed the desired record_seconds
        # and if there is enough silence indicating the end of a sentence
        if len(frames) * chunk >= frame_rate * record_seconds and silent_frames >= required_silence_length\
            or len(frames) * chunk >= frame_rate * max_record_seconds:
            all_frames = b''.join(frames)
            logger.info("processing chunk of duration: " + str(len(all_frames) / frame_rate / channel / 2) + " sec")
            shared_queue.put(all_frames)
            frames.clear()
            silent_frames = 0

def process_audio(shared_queue: queue):
    iter = 1
    while True:
        all_frames = shared_queue.get()
        if all_frames is None:  # None is used as a signal to stop the thread
            break

        logger.debug("converting chunk")
        converted_buffer, audio = convert_audio_to_16000hz(logger, frame_rate, all_frames)

        if save_wav:
            logger.debug("saving chunk")
            save_wav(p_audio, 1, 16000, audio_format, converted_buffer, "out_"+str(iter)+".wav")

        logger.debug("transcribing chunk")
        texts = transcribe_audio(logger, model, audio)

        transcription_queue.put(''.join(texts))
        logger.debug(texts)
        conversation.extend(texts)
        shared_queue.task_done()
        iter = iter + 1


def update_gui_from_queue(root, transcription_queue, text_area):
    global sentence_indices, current_selection
    if root.winfo_exists():  # Check if the root window still exists
        try:
            # Update transcription
            if updating_completion == False:
                while not transcription_queue.empty():
                    full_text = update_text_area(transcription_queue, text_area)
                    
                    sentence_indices = find_sentences(full_text)
                    current_selection = (0, 0)
        except queue.Empty:
            pass

        # Schedule the next queue check
        if still_listening:
            root.after(100, update_gui_from_queue, root, transcription_queue, text_area)

def update_text_area(transcription_queue, text_area):
    sentence = transcription_queue.get_nowait()
    toggle_text_area_state(text_area, tk.NORMAL)
    text_area.tag_configure('default', foreground='black')
    text_area.insert(tk.END, sentence + '\n', 'default')
    toggle_text_area_state(text_area, tk.DISABLED)
    full_text = text_area.get('1.0', tk.END)
    text_area.see(tk.END)
    return full_text

def send_to_gpt(promptNo, text):
    prompt = "Podsumuj"
    if len(prompts) >= promptNo:
        prompt = prompts[promptNo - 1]
    logger.debug('Using prompt: "' + prompt + '" with text "' + text + '"')
    completions = get_completions(text, gpt_model, gpt_maxtokens, gpt_temperature, prompt)
    logger.debug(completions)
    return completions

def send_to_gpt_stream(promptNo, text):
    prompt = "Podsumuj"
    if len(prompts) >= promptNo:
        prompt = prompts[promptNo - 1]
    logger.debug('Using prompt: "' + prompt + '" with text "' + text + '"')
    completions = get_completions_stream(text, gpt_model, gpt_maxtokens, gpt_temperature, prompt)
    return completions

def handle_key(event, no, text_area: scrolledtext.ScrolledText):
    toggle_text_area_state(text_area, tk.NORMAL)
    selected_text = text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
    text_tag = get_random_color()

    # Apply the color to the selected text
    text_area.tag_add(text_tag, tk.SEL_FIRST, tk.SEL_LAST)
    text_area.tag_config(text_tag, foreground=text_tag)

    if gpt_streaming == False:
        # Get the GPT response and append it to the text area
        update_nostreaming_gpt(no, text_area, selected_text, text_tag)
    else:
        start_streaming_gpt(no, text_area, selected_text, text_tag) 

def start_streaming_gpt(no, text_area, selected_text, text_tag):
    toggle_text_area_state(text_area, tk.DISABLED)
    thread = threading.Thread(target=update_completion_thread, args=(no, selected_text, text_area, text_tag, conversation))
    thread.start()

def update_nostreaming_gpt(no, text_area, selected_text, text_tag):
    response = send_to_gpt(no, selected_text)

    text_area.insert(tk.END, "\n*" + response + "*\n", text_tag)
    conversation.append("\n*" + response + "*\n")
    toggle_text_area_state(text_area, tk.DISABLED)
    text_area.see(tk.END)  

updating_completion = False
def update_completion_thread(no, selected_text, text_area, text_tag, conversation):
    global updating_completion
    response = send_to_gpt_stream(no, selected_text)

    # Since we are updating the UI, these operations should be done in the main thread
    # We use text_area.after to schedule these updates in the main thread
    try:
        updating_completion = True
        text_area.after(0, text_area.insert, tk.END, "\n", text_tag)
        text_area.after(0, conversation.append, "\n*")
        for chunk in response:
            try:
                text_area.after(0, toggle_text_area_state, text_area, tk.NORMAL)
                chunk_text = chunk.choices[0].delta.content

                text_area.after(0, text_area.insert, tk.END, chunk_text, text_tag) # insert response
                text_area.after(0, conversation.append, chunk_text)
                
                text_area.after(0, toggle_text_area_state, text_area, tk.DISABLED)
                text_area.after(0, text_area.see, tk.END)
            except:
                pass

        text_area.after(0, text_area.insert, tk.END, "\n", text_tag)
        text_area.after(0, conversation.append, "*\n")
        text_area.after(0, toggle_text_area_state, text_area, tk.DISABLED)
    finally:
        updating_completion = False

# Allow modifications in the script
def toggle_text_area_state(text_area, state):
    text_area['state'] = state

def handle_arrows(event, direction, text_area):
    global current_selection, sentence_indices

    if direction == 'left':
        # Extend selection to include the previous sentence
        if current_selection == (0, 0) and sentence_indices:
            # If nothing is selected, select the last sentence
            current_selection = sentence_indices[-1]
        else:
            # Find the sentence before the current start and extend the selection
            for i, (start, end) in enumerate(sentence_indices):
                if start == current_selection[0] and i > 0:
                    current_selection = (sentence_indices[i - 1][0], current_selection[1])
                    break

    elif direction == 'right':
        # Shrink selection to exclude the last sentence
        if current_selection != (0, 0):
            for i, (start, end) in enumerate(sentence_indices):
                if end == current_selection[1] and i < len(sentence_indices) - 1:
                    current_selection = (current_selection[0], sentence_indices[i + 1][1])
                    break
                elif end == current_selection[1]:  # If at the end, deselect all
                    current_selection = (0, 0)
                    break

    elif direction == 'up':
        # Select the last sentence, or extend selection backwards
        if current_selection == (0, 0):
            current_selection = sentence_indices[-1]
        else:
            # Find the previous sentence
            for i, (start, end) in enumerate(sentence_indices):
                if start == current_selection[0]:
                    if i > 0:
                        current_selection = sentence_indices[i - 1]
                    break

    elif direction == 'down':
        # Unselect the last sentence, or shrink selection forwards
        if current_selection != (0, 0):
            for i, (start, end) in enumerate(sentence_indices):
                if end == current_selection[1]:
                    if i < len(sentence_indices) - 1:
                        current_selection = sentence_indices[i + 1]
                    else:
                        current_selection = (0, 0)  # Deselect all
                    break
    
    # Update the selection in the text area
    text_area.tag_remove('sel', '1.0', tk.END)
    logger.debug('selecting ' + f'1.0+{current_selection[0]}c' + ' - ' + f'1.0+{current_selection[1]}c')
    text_area.tag_add('sel', f'1.0+{current_selection[0]}c', f'1.0+{current_selection[1]}c')
    # Scroll to the start of the selection
    text_area.see(f'1.0+{current_selection[0]}c')


def bind_keys(root, text_area):
    for i in range(1, 10):
        root.bind(str(i), lambda event, num=i: handle_key(event, num, text_area))

    root.bind('<Left>', lambda event: handle_arrows(event, 'left', text_area))
    root.bind('<Right>', lambda event: handle_arrows(event, 'right', text_area))
    root.bind('<Control-Left>', lambda event: handle_arrows(event, 'up', text_area))
    root.bind('<Control-Right>', lambda event: handle_arrows(event, 'down', text_area))

def create_gui():
    root = tk.Tk()
    root.title("Transcription App")

     # Get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate window size as 75% of the screen size
    window_width = int(screen_width * 0.20)
    window_height = int(screen_height * 0.8)

     # Calculate position coords for the window to be centered
    position_right = 50
    position_down = 50

    # Set the window size
    root.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")

    # Transcription display
    text_font = font.Font(family=font_name, size=font_size)
    transcription_frame = tk.Frame(root)
    transcription_frame.pack(fill=tk.BOTH, expand=True)
    text_area = scrolledtext.ScrolledText(transcription_frame, wrap=tk.WORD, height=font_size, font=text_font)
    text_area.pack(fill=tk.BOTH, expand=True)
    text_area['state'] = tk.DISABLED
    text_area.bind("<MouseWheel>", lambda event: change_font_size(event, text_font))
    
    # Schedule the first GUI update from the queue
    root.after(100, update_gui_from_queue, root, transcription_queue, text_area)

    def on_closing(root):
        global still_listening
        shared_queue.put(None)  # Send termination signal to the queue
        still_listening = False
        root.destroy()

    bind_keys(root, text_area)
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))

    root.mainloop()

def init_prompts_from_config(config, prompts):
    try:
        for i in range(1, 10):
            prompts.append(config.get('PROMPTS', f'P{i}'))
    except:
        pass

### MAIN ###

# Load the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Accessing the settings
logging_level = getattr(logging, config['LOGGING']['logging_level'])

record_seconds = config.getint('RECORDING', 'record_seconds')
max_record_seconds = config.getint('RECORDING', 'max_record_seconds')
audio_format = pyaudio.paInt16
required_silence_length = config.getint('RECORDING', 'required_silence_length')
save_wav = config.getboolean('RECORDING', 'save_wav')
vad_mode = config.getint('RECORDING', 'vad_mode')

gpt_streaming = config.getboolean('GPT', 'gpt_streaming')
gpt_model = config.get('GPT', 'gpt_model')
gpt_temperature = config.getfloat('GPT', 'gpt_temperature')
gpt_maxtokens = config.getint('GPT', 'gpt_maxtokens')

font_name = config.get('VISUAL', 'font_name')
font_size = config.getint('VISUAL', 'font_size')

model_name = config.get('WHISPER', 'model_name')
device_name = config.get('WHISPER', 'device_name')

prompts = []

init_prompts_from_config(config, prompts)

logging.basicConfig(level=logging_level)  # Set the desired log level (e.g., INFO, DEBUG, WARNING, ERROR)
logger = logging.getLogger()

 # Queues for thread communication
transcription_queue = queue.Queue()
still_listening = True
conversation = []
current_selection = (0, 0)  # Start and end indices of the current selection
sentence_indices = []

p_audio = pyaudio.PyAudio()

default_speakers = initialize_pyaudio(p_audio)
channel, frame_rate, chunk_size, input_index = get_device_info(default_speakers)

logger.debug(f"Recording from: ({default_speakers['index']}){default_speakers['name']}")
logger.debug("Frame rate: " + str(frame_rate) + ", Channels: " + str(channel) + ", Chunk size is " + str(chunk_size))
stream = get_stream(p_audio, audio_format, channel, frame_rate, chunk_size, input_index)

logger.info('loading model')
if device_name == 'gpu':
    model = whisper.load_model(model_name)
else:
    model = whisper.load_model(model_name, device=device_name)

# Shared queue for communication between threads
shared_queue = queue.Queue()

logger.info("Recording started")
# Start threads
thread1 = threading.Thread(target=read_stream, args=(stream, chunk_size, frame_rate, shared_queue))
thread2 = threading.Thread(target=process_audio, args=(shared_queue,))

thread1.start()
thread2.start()

create_gui()

# Wait for both threads to finish
thread1.join()
thread2.join()

logger.info("stop")
logger.info(''.join(conversation))
stream.stop_stream()
stream.close()
p_audio.terminate()
