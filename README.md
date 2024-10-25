# Transcription Pearl

A Python-based GUI application for transcribing and processing images containing historical handwritten text using Large Language Models (LLMs) via API services (OpenAI, Google, and Anthropic APIs). Designed for academic and research purposes.

## Overview

Transcription Pearl helps researchers process and transcribe image-based documents using various AI services. It provides a user-friendly interface for managing transcription projects and leverages multiple AI providers for optimal results.

## Features

- Multi-API OCR capabilities (OpenAI, Google, Anthropic)
- Batch processing of images
- Text correction and validation
- PDF import and processing
- Drag-and-drop interface
- Project management system
- Find and replace functionality
- Progress tracking
- Multiple text draft versions

## Prerequisites

- Python 3.8+
- Active API keys for:
  - OpenAI
  - Google Gemini
  - Anthropic Claude

## Dependencies

- tkinter
- tkinterdnd2
- pandas
- PyMuPDF (fitz)
- pillow
- openai
- anthropic
- google.generativeai

## Installation

1. Clone the repository
```bash
git clone [repository-url]
```

2. Install required packages
```bash
pip install -r requirements.txt
```

3. Configure API keys in `util/API_Keys_and_Logins.txt`

## Usage

Launch the application:
```bash
python main.py
```

Basic workflow:
1. Create new project or open existing
2. Import images or PDF
3. Process text using AI services
4. Edit and correct transcriptions
5. Export processed text

## Configuration

The application uses several configuration files:
- `util/API_Keys_and_Logins.txt` - API credentials
- `util/prompts.csv` - AI processing prompts
- `util/default_settings.txt` - Application settings

## License

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

This work is licensed under a [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

This means you are free to:
- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material

Under the following terms:
- Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made
- NonCommercial — You may not use the material for commercial purposes

## Citation

If you use this software in your research, please cite:
```
[Citation information to be added]
```

## Author

Mark Humphries
Wilfrid Laurier University, Waterloo, Ontario

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The authors assume no liability for its use or any damages resulting from its use.

## Contributing

This project is primarily for academic and research purposes. Please contact the author for collaboration opportunities.

## Acknowledgments

- OpenAI API
- Google Gemini API
- Anthropic Claude API
