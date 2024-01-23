# Transcription App

This application allows for real-time transcription of audio input using a graphical user interface (GUI) built with Tkinter. It employs Google's GPT (Generative Pre-trained Transformer) model for text completion and WebRTC VAD (Voice Activity Detection) for identifying speech segments.

## Features

- Real-time transcription of audio input
- GPT-based text completion for enhancing transcriptions
- GUI for ease of use
- Configurable settings for recording and transcription

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

1. Run the `main.py` script:

   ```bash
   python main.py
   ```

2. The GUI will open, allowing you to start recording audio and see the transcription in real-time.

3. Use keyboard shortcuts (1-9) to select text for GPT completion and arrow keys to navigate through the transcription.

## Contributing

Contributions are welcome! Please submit pull requests or open issues for any suggestions, bug reports, or improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
