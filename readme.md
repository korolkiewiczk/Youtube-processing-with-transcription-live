# Transcription App

This application allows for real-time transcription of audio input using a graphical user interface (GUI) built with Tkinter. It employs Google's GPT (Generative Pre-trained Transformer) model for text completion and WebRTC VAD (Voice Activity Detection) for identifying speech segments. It also includes a module for automatic YouTube video transcription, Airtable integration for managing video URLs and storing summaries, support for multiple YouTube client types for improved reliability, automatic retries with different clients on failure, configurable chunking of audio for processing large files, support for both local Whisper model and OpenAI Whisper API, detailed logging system, error handling and tracking in Airtable, and batch processing of multiple videos.

## Overview

The application consists of several main components:

1. **YouTube Processing Module**
   - Handles downloading and processing of YouTube videos
   - Manages Airtable integration for URL tracking
   - Implements retry logic with multiple client types
   - Processes videos in batches or single runs

2. **Transcription Engine**
   - Supports both local Whisper model and OpenAI's Whisper API
   - Handles audio chunking for large files
   - Provides efficient audio processing pipeline
   - Includes voice activity detection

3. **Summary Generation**
   - Creates detailed summaries of transcribed content
   - Categorizes content automatically
   - Stores results in structured format
   - Supports multiple languages

4. **Data Management**
   - Maintains organized file structure
   - Implements caching for processed files
   - Handles data persistence
   - Manages configuration settings

The system is designed to be modular and extensible, allowing for easy addition of new features and modifications to existing functionality. It includes comprehensive error handling and logging to ensure reliable operation and easy debugging.


## Features

- Real-time transcription of audio input
- GPT-based text completion for enhancing transcriptions
- GUI for ease of use
- Configurable settings for recording and transcription
- Automatic YouTube video transcription
- Airtable integration for managing video URLs and storing summaries
- Support for multiple YouTube client types for improved reliability
- Automatic retries with different clients on failure
- Configurable chunking of audio for processing large files
- Support for both local Whisper model and OpenAI Whisper API
- Detailed logging system
- Error handling and tracking in Airtable
- Batch processing of multiple videos

## Requirements

- Python 3.x
- Libraries:
  - tkinter
  - configparser
  - pyaudiowpatch
  - whisper
  - webrtcvad
  - threading (built-in)
  - queue (built-in)
  - logging (built-in)
  - argparse (built-in)
  - airtable-python-wrapper (pip install airtable-python-wrapper)
  - pytubefix


## Installation

1. Clone the repository:

   ```bash
   git clone <repository_url>
   ```

2. Install the required libraries:

   ```bash
   pip install tkinter configparser pyaudiowpatch whisper webrtcvad
   ```

## Configuration

1. Update the `config.ini` file with desired settings. Configuration options include logging level, recording parameters, GPT settings, visual settings, and more.

## Usage

### Audio Transcription Live

1. Run the `main_audio_transcription_live.py` script:

   ```bash
   python main_audio_transcription_live.py
   ```

2. The GUI will open, allowing you to start recording audio and see the transcription in real-time.

3. Use keyboard shortcuts (1-9) to select text for GPT completion and arrow keys to navigate through the transcription.

### YouTube Processing

1. Run the `main_youtube_processing.py` script: 

   ```bash
   python main_youtube_processing.py
   ```
2. Program will process YouTube videos from Airtable table specified in `config.ini` file.

3. You can use `--once` flag to process videos once and exit.

## Contributing

Contributions are welcome! Please submit pull requests or open issues for any suggestions, bug reports, or improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
