#!/bin/bash
cd "$(dirname "$0")/../src"
python3 main_youtube_processing.py --once
cd "$(dirname "$0")" 