# Gemini File Search - Tutorial & Demo

A beginner-friendly tutorial and demo application for Google's **newly announced Gemini File Search Tool**. This project provides a complete, working example of how to build an intelligent document search and chat application using Gemini's File Search API. Upload your PDF and text documents, and ask questions about them using natural language. The application demonstrates how the File Search Tool automatically indexes your documents and provides accurate, citation-backed answers.

> **🚀 New Feature Alert!** Google's File Search Tool was just announced recently. This repository serves as a practical tutorial to help developers get started with this powerful new capability.

## What is This?

**For Everyone:**
Imagine having a smart assistant that can read all your PDFs and text files, understand what's in them, and answer any questions you have. That's what Gemini File Search does! You simply upload your documents (like research papers, reports, or notes), and then you can chat with an AI that has "read" all your files and can find the exact information you need.

**For Developers:**
This repository is a **tutorial and starter project** for learning Google's Gemini File Search Tool. It includes:
- A complete Streamlit-based web application demonstrating the File Search API
- Sample code showing how to upload and index PDF/TXT documents into a Gemini File Search Store
- Implementation of natural language queries against indexed documents
- Examples of handling citations and source references
- A user-friendly web interface for managing document collections

Perfect for developers who want to explore this new capability and understand how to integrate it into their own applications!

## Features

- 📄 **Document Upload**: Upload multiple PDF or TXT files at once
- 🔍 **Intelligent Search**: Ask questions in natural language about your documents
- 📚 **Citation Support**: Answers include citations pointing back to source documents
- 🎨 **Streamlit GUI**: Beautiful, intuitive web interface that runs in your browser
- ⚡ **Real-time Status**: See upload and indexing progress with periodic status updates
- ⏭️ **Duplicate Detection**: Automatically skips files that already exist in the store
- 🗑️ **Store Management**: Clear your document store with a single click

## Prerequisites

- Python 3.11 or higher
- Package manager (choose one):
  - [uv](https://github.com/astral-sh/uv) - A fast Python package installer and resolver (recommended)
  - `pip` and `venv` - Standard Python package management (built into Python)
- A Google Gemini API key ([Get one here from AI Studio](https://makersuite.google.com/app/apikey))

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/gr8sk8s/gemini-file-search.git
cd gemini-file-search
```

### 2. Create Virtual Environment and Install Dependencies

Choose one of the following methods:

#### Option A: Using `uv` (Recommended - Much Faster!)

```bash
uv venv --python 3.11  # ... or the version of your choice. Note that the python version you select needs to already be installed on your system.
source .venv/bin/activate # ... to activate the virtual env
uv pip install -r requirements.txt # ... install required libs
```

#### Option B: Using `pip` and `venv` (Traditional Method)

**macOS/Linux:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Note:**
- On macOS/Linux, if `python3.11` is not available, try `python3` or `python`
- After activation, your terminal prompt should show `(.venv)` indicating the virtual environment is active
- To deactivate the virtual environment later, simply run `deactivate`

### 3. Configure Environment Variables

Copy the example environment file and add your API key:

```bash
cp env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Optional configuration:
- `USE_MODEL`: Gemini model to use (default: `gemini-2.5-flash`; the other supported model is `gemini-2.5-pro`)
- `FILE_SEARCH_STORE`: Display name for the file search store (default: `demo_filesearch_store`)

### 4. Run the Application

```bash
streamlit run code/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### 5. (Optional) Download Sample PDF Files for Testing

To help you get started and see the File Search Tool in action, we've provided some sample PDF files you can download. These are optional - you can use your own PDF files for your analysis, but these samples are perfect for beginners who are new to the File Search Tool!

**Download sample PDF files:**

```bash
# Download IRENA Renewable Energy Highlights 2025
curl --create-dirs --output-dir ./data -sSO \
  https://www.irena.org/-/media/Files/IRENA/Agency/Publication/2025/Jul/IRENA_DAT_Renewable_energy_highlights_2025.pdf

# Download IEA Renewables 2024 report
curl --create-dirs --output-dir ./data -sSO \
  https://www.developmentaid.org/api/frontend/cms/file/2024/10/Renewables2024.pdf
```

These sample PDFs are renewable energy reports that work well for testing the File Search Tool. Once downloaded, you can upload them through the Streamlit interface and ask questions like:
- "What are the key renewable energy trends for 2024?"
- "What does the report say about solar energy growth?"
- "Summarize the main findings from both documents"

**Note:** The `data/` directory will be created automatically if it doesn't exist. You can also use your own PDF or TXT files - just upload them through the web interface!

## Usage

### Uploading Documents

1. In the sidebar, click "**Browse files**" under "Upload documents"
2. Select one or more PDF or TXT files from the system (e.g. under the data/ folder if you downloaded your files there)
3. Click "**Upload & index**" to upload and index your documents
4. Wait for the indexing to complete.

**Note:** Large documents may take several minutes to index. The application will show periodic status updates during this process.

### Asking Questions

1. Once documents are uploaded and indexed, the chat interface becomes enabled
2. Type your question in the chat input at the bottom of the page
3. The AI will search through your documents and provide an answer with citations

**Example Questions:**
- "What are the main findings in the research paper?"
- "Summarize the key points from all documents"
- "What does the document say about [specific topic]?"

**If you downloaded the sample PDFs, try asking:**
- "What are the key renewable energy trends mentioned in the reports?"
- "What does the IRENA report say about solar energy capacity?"
- "Compare the findings between the two renewable energy reports"
- "What are the main challenges for renewable energy adoption?"

### Managing Documents

- **View Store Contents**: The sidebar shows all documents in your store with their status (✅ Active or ⏳ Processing)
- **Clear Store**: Click "Clear store" in the sidebar to remove all documents from the store

## How It Works

### For Technical Users

1. **File Upload**: Documents are uploaded to Google's Gemini File Search Store via the Gemini API
2. **Indexing**: Gemini processes and indexes the documents, making them searchable
3. **Query Processing**: When you ask a question, the application:
   - Sends your query to the Gemini model
   - Uses the File Search Tool to search through indexed documents
   - Returns an answer with citations from the source documents
4. **Streamlit Interface**: The web UI provides a user-friendly way to interact with the File Search API

### Architecture

- **`code/app.py`**: Streamlit web application with GUI components
- **`code/file_search_service.py`**: Core service layer for File Search API operations
  - Document upload and indexing
  - Store management (create, list, clear)
  - Document existence checking
  - Status polling with callbacks

## Project Structure

```
gemini-file-search/
├── code/
│   ├── app.py                 # Streamlit web application
│   └── file_search_service.py # File Search API service layer
├── data/                      # Sample PDF files (optional, created when downloading samples)
├── env.example                # Environment variables template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Dependencies

- `google-genai>=1.49.0` - Google Gemini AI SDK
- `streamlit>=1.40.0` - Web application framework
- `python-dotenv>=1.0.0` - Environment variable management

## Troubleshooting

### API Key Issues
- Make sure your `GEMINI_API_KEY` is set in the `.env` file
- Verify your API key is valid and has access to the File Search API

### Upload Failures
- Check that your files are valid PDF or TXT files
- Ensure files are not corrupted
- Large files may take longer to process; wait for the indexing to complete

### Model Errors
- Verify the model name in `USE_MODEL` is valid (e.g., the current supported models: `gemini-2.5-flash` or `gemini-2.5-pro`). There could be mnore in the future.
- Check your API quota and rate limits

## References and Additional Resources

### Central Resource: Google File Search Announcement

- **[File Search in the Gemini API - Google Blog](https://blog.google/technology/developers/file-search-gemini-api/)** - Official announcement and overview of the File Search Tool feature

### Google Gemini AI Documentation

- **[Gemini API Documentation](https://ai.google.dev/gemini-api/docs)** - Complete guide to the Gemini API, including setup, usage, and best practices
- **[Gemini API Reference](https://ai.google.dev/api)** - Detailed API reference documentation
- **[Google AI Studio](https://aistudio.google.com/)** - Interactive playground for testing Gemini models and features

### Streamlit Documentation

- **[Streamlit Documentation](https://docs.streamlit.io/)** - Official Streamlit documentation for building web apps
- **[Streamlit API Reference](https://docs.streamlit.io/library/api-reference)** - Complete API reference for all Streamlit components


## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! I appreciate your help in making this project better.

### How to Contribute

- 🐛 **Found a bug?** [Open an issue](https://github.com/<your-username>/gemini-file-search/issues) to report it
- 💡 **Have a feature idea?** [Open an issue](https://github.com/<your-username>/gemini-file-search/issues) to suggest it
- 🔧 **Want to contribute code?** Submit a [Pull Request](https://github.com/<your-username>/gemini-file-search/pulls)

When reporting bugs or issues, please include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment information (Python version, OS, etc.)
- Error messages or screenshots if applicable

Thank you for contributing! 🙏

- Conrad