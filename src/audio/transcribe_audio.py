import whisper
import logging
import time

def transcribe_audio(logger: logging, model: whisper, audio):
    start_time = time.time()  # Start timing

    result = model.transcribe(audio, fp16=False)

    end_time = time.time()  # End timing
    execution_time = (end_time - start_time) * 1000  # Convert to milliseconds

    logger.debug(f"Transcribe time: {execution_time} milliseconds")

    segments = result["segments"]
    texts = [item['text'] for item in segments]
    return texts