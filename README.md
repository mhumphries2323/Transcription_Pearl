# Transcription Pearl

A Python-based GUI application for transcribing and processing images containing historical handwritten text using Large Language Models (LLMs) via API services (OpenAI, Google, and Anthropic APIs). Designed for academic and research purposes.

## Manual

There is also a Transcription Pearl Manual available in the repository in PDF format with instructions on how to get and insert API keys as well as information on the various commands and functions.

## Recent Updates: 11 November 2024

MAJOR UPDATE: 1.0 beta Release

- Includes Image Preprocessing Utility
- Includes better functionality for storing settings
- Drag and drop functionality for PDFs
- Automatic rotation of photographs captured with phone cameras
- Ability to manually rotate images
- Ability to manually delete images
- Resizable image and text windows
- New requirements text (adds opencv-python==4.10.0.84)

Previous Update: 08 November 2024

There was an issue with the prompts file that was preventing the transcribed text from being sent to the correction function. The prompt was missing the {text_to_process} placeholder. That has now been fixed.

PDFs were also being imported at 72 DPI and this has been changed to 300 DPI which should improve readability.

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
- Image Pre-Processsing Tool

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
git clone https://github.com/mhumphries2323/Transcription_Pearl
```

2. Install required packages
```bash
pip install -r requirements.txt
```

3. Configure API keys in the Settings menu.

## Usage

Launch the application:
```bash
python TranscriptionPearl_beta-2024111.py
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
Mark Humphries and Lianne C. Leddy, 2024. Transcription Pearl 1.0 Beta. Department of History: Wilfrid Laurier University.
```

If you wish to cite the paper that explores this research cite:
```
Mark Humphries, Lianne C. Leddy, Quinn Downton, Meredith Legace, John McConnell, Isabella Murray, and Elizabeth Spence. Unlocking the Archives: Using Large Language Models to Transcribe Handwritten Historical Documents. Preprint: xxx.
```

## Authors

Mark Humphries (Programming, Funding, and Historical Work)
Wilfrid Laurier University, Waterloo, Ontario

Lianne Leddy (Funding, Historical Work, and Testing)
Wilfrid Laurier University, Waterloo, Ontario

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. The authors assume no liability for its use or any damages resulting from its use.

## Contributing

This project is primarily for academic and research purposes. Please contact the author for collaboration opportunities.

## Acknowledgments

- OpenAI API
- Google Gemini API
- Anthropic Claude API
