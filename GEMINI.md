# GEMINI.md

## Project Overview

This is a Python project that provides a web-based graphical user interface (GUI) for interacting with the Gemini File Search API. The application is built using the Streamlit framework.

The primary purpose of this project is to demonstrate the capabilities of the Gemini File Search API. It allows users to:

*   Upload PDF and text documents.
*   Index the content of the uploaded documents.
*   Ask natural language questions about the documents and receive intelligent answers.

The backend is powered by the `google-genai` Python library, which communicates with the Gemini API. The core logic for file uploading, indexing, and store management is encapsulated in the `code/file_search_service.py` module. The main application, `code/app.py`, handles the user interface and the chat functionality.

## Building and Running

### Prerequisites

*   Python 3.11 or higher
*   A Google Gemini API key

### Setup and Execution

1.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Environment Variables:**

    Create a `.env` file in the root of the project by copying the `env.example` file. Then, add your Gemini API key to the `.env` file:

    ```
    GEMINI_API_KEY=your_api_key_here
    ```

3.  **Run the Application:**

    ```bash
    streamlit run code/app.py
    ```

    The application will be accessible at `http://localhost:8501`.

### Testing

The project includes a `tests` directory, but there are no specific instructions on how to run the tests in the `README.md`. Based on the file `tests/test_file_search_service.py`, the tests use Python's built-in `unittest` module. To run the tests, you can use the following command:

```bash
python -m unittest discover tests
```

## Development Conventions

*   **Styling:** The code follows the PEP 8 style guide for Python.
*   **Typing:** The code uses type hints for better readability and maintainability.
*   **Modularity:** The code is organized into modules with clear responsibilities. The `file_search_service.py` module separates the core logic from the presentation layer in `app.py`.
*   **Error Handling:** The code includes error handling to manage potential issues with API calls and file operations.
*   **Dependencies:** Project dependencies are managed in the `requirements.txt` file.
*   **Environment:** Environment variables are used for configuration, with an `env.example` file provided as a template.
