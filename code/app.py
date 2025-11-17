"""Streamlit app for Gemini File Search.

This includes core functionality:
- Upload and index files (PDF or TXT) with periodic status updates every 10 seconds
- Clear the store
- Chat with the indexed documents

"""

import concurrent.futures
import os
import time
import traceback

import streamlit as st
from dotenv import load_dotenv
from file_search_service import (
    ClearStoreResult,
    DocumentInfo,
    UploadResult,
    clear_store,
    get_or_create_store,
    list_store_documents,
    upload_single_file,
)
from google import genai
from google.genai import types

load_dotenv()

st.set_page_config(page_title="Gemini File Search - use GUI", layout="wide")
st.title("🔍 Gemini File Search - use GUI")

# Configuration
api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("USE_MODEL", "gemini-2.5-flash")
store_display_name = os.getenv("FILE_SEARCH_STORE", "demo_filesearch_store")

if not api_key:
    st.error("Set GEMINI_API_KEY in your environment before running the app.")
    st.stop()

st.sidebar.success("API key loaded.")
st.sidebar.info(f"Using model: `{model_name}`")

# Initialize client and file search store
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

client: genai.Client = st.session_state.client

if "store_name" not in st.session_state:
    st.session_state.store_name = get_or_create_store(client, store_display_name)

store_name = st.session_state.store_name
st.sidebar.success(f"Using store: `{store_name}`")

# Check for existing documents in the store
existing_docs: list[DocumentInfo] = list_store_documents(client, store_name)
st.session_state.existing_doc_names = {doc.display_name for doc in existing_docs}

# Display existing documents info and set files_ready state
if existing_docs:
    st.sidebar.subheader(f"📄 Store Contents ({len(existing_docs)} document(s))")
    for doc in existing_docs:
        # Show document name, truncate if too long
        doc_name = doc.display_name
        if len(doc_name) > 40:
            doc_name = doc_name[:37] + "..."
        state_icon = "✅" if doc.state == "ACTIVE" else "⏳"
        st.sidebar.text(f"{state_icon} {doc_name}")

    # Enable chat if documents exist (always set based on current store state)
    st.session_state.files_ready = True
else:
    st.sidebar.info("Store is empty. Upload documents to get started.")
    # Disable chat if no documents exist
    st.session_state.files_ready = False

# Upload & index documents
st.sidebar.subheader("Upload documents")
uploaded_files = st.sidebar.file_uploader(
    "PDF or TXT files",
    type=["pdf", "txt"],
    accept_multiple_files=True,
)


def upload_files(files, skip_duplicates: bool = True):
    """Upload files (PDF or TXT) in parallel with status updates.

    Args:
        files: List of uploaded file objects.
        skip_duplicates: If True, skip files that already exist in the store.
    """
    if not files:
        st.sidebar.warning("No files selected.")
        st.session_state.files_ready = False
        return

    successes = 0
    failures = 0
    skipped = 0

    # Filter out files that already exist
    files_to_upload = []
    if skip_duplicates:
        for uploaded_file in files:
            if uploaded_file.name in st.session_state.get("existing_doc_names", set()):
                st.sidebar.warning(
                    f"⏭️ **{uploaded_file.name}** - Already exists (skipped)."
                )
                skipped += 1
            else:
                files_to_upload.append(uploaded_file)
    else:
        files_to_upload = files

    if not files_to_upload:
        st.sidebar.info("No new files to upload.")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_file = {
            executor.submit(
                upload_single_file, client, store_name, uploaded_file
            ): uploaded_file
            for uploaded_file in files_to_upload
        }

        for future in concurrent.futures.as_completed(future_to_file):
            uploaded_file = future_to_file[future]
            try:
                result: UploadResult = future.result()
                if result.success:
                    st.sidebar.success(
                        f"✅ **{uploaded_file.name}** - Uploaded successfully."
                    )
                    successes += 1
                else:
                    st.sidebar.error(
                        f"❌ **{uploaded_file.name}** - {result.error_message}"
                    )
                    failures += 1
            except Exception as exc:
                st.sidebar.error(
                    f"❌ **{uploaded_file.name}** - Generated an exception: {exc}"
                )
                failures += 1

    # Show summary
    if successes > 0:
        st.session_state.files_ready = True
        summary_parts = [f"✅ {successes} succeeded"]
        if failures > 0:
            summary_parts.append(f"❌ {failures} failed")
        if skipped > 0:
            summary_parts.append(f"⏭️ {skipped} skipped")
        st.sidebar.info(f"Upload complete: {', '.join(summary_parts)}")
        # Refresh to show updated document list in sidebar
        st.rerun()
    else:
        if skipped > 0 and failures == 0:
            st.sidebar.warning(
                f"All {skipped} file(s) were skipped (already exist in store)."
            )
        else:
            st.session_state.files_ready = False
            st.sidebar.error("No files uploaded successfully.")


if st.sidebar.button("Upload & index") and uploaded_files:
    upload_files(uploaded_files)

# Clear store
if st.sidebar.button("Clear store"):
    result: ClearStoreResult = clear_store(client, store_name)

    if result.deleted:
        st.sidebar.success("Store cleared successfully.")
        # Remove the store name from the session state to create a new one on next run
        if "store_name" in st.session_state:
            del st.session_state.store_name
    elif result.errors:
        st.sidebar.error(f"Errors: {', '.join(result.errors)}")
    else:
        st.sidebar.info("Store is already empty or could not be deleted.")

    # Refresh the page to update the document list
    st.rerun()


def handle_chat_prompt(
    prompt: str, client: genai.Client, model_name: str, store_name: str
):
    """Handles the user's chat prompt, generates a response, and updates the chat history."""
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        answer = None
        citations = None
        response = None

        with st.spinner("Thinking…"):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part(text=prompt)],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        tools=[
                            types.Tool(
                                file_search=types.FileSearch(
                                    file_search_store_names=[store_name]
                                )
                            )
                        ]
                    ),
                )
            except Exception as e:
                error_msg = f"Error generating response: {str(e)}"
                answer = error_msg
                st.error(error_msg)

        # Safely extract the answer from the response (if we got one)
        if response is not None:
            try:
                if (
                    not hasattr(response, "candidates")
                    or not response.candidates
                    or len(response.candidates) == 0
                ):
                    answer = "Error: No candidates in the response."
                else:
                    candidate = response.candidates[0]

                    # Check for finish reason (blocked content, etc.)
                    finish_reason = getattr(candidate, "finish_reason", None)
                    if finish_reason:
                        finish_reason_str = str(finish_reason)
                        if (
                            "SAFETY" in finish_reason_str.upper()
                            or "BLOCKED" in finish_reason_str.upper()
                        ):
                            answer = (
                                "Error: The response was blocked for safety reasons."
                            )
                        elif "OTHER" in finish_reason_str.upper():
                            answer = (
                                "Error: The response was blocked for other reasons."
                            )

                    # Try to extract text content (only if we haven't already set an error)
                    if answer is None:
                        if not hasattr(candidate, "content") or not candidate.content:
                            answer = "Error: Response candidate has no content."
                        elif (
                            not hasattr(candidate.content, "parts")
                            or not candidate.content.parts
                            or len(candidate.content.parts) == 0
                        ):
                            answer = "Error: Response has no content parts."
                        else:
                            # Check if it's text content
                            first_part = candidate.content.parts[0]
                            if hasattr(first_part, "text") and first_part.text:
                                answer = first_part.text
                            else:
                                answer = (
                                    "Error: Response does not contain text content."
                                )

                    # Extract citations if available
                    citations = getattr(candidate, "citation_metadata", None)

            except Exception as e:
                answer = f"Error parsing response: {str(e)}"
                st.error(f"Details: {traceback.format_exc()}")
        elif answer is None:
            answer = "Error: No response received from the model."

        # Display the answer or error
        if answer:
            st.markdown(answer)

            # Display citations if available
            if citations and hasattr(citations, "citations") and citations.citations:
                st.markdown("**Citations**")
                for citation in citations.citations:
                    label = (
                        getattr(citation, "title", None)
                        or getattr(citation, "uri", None)
                        or "Source"
                    )
                    uri = getattr(citation, "uri", None)
                    if uri:
                        st.markdown(f"- [{label}]({uri})")
                    else:
                        st.markdown(f"- {label}")
        else:
            st.error("Error: Unable to extract answer from the response.")
            answer = "Error: Unable to extract answer from the response."

    if answer:
        st.session_state.chat_history.append({"role": "assistant", "content": answer})


# Chat interface
st.markdown("Upload documents in the sidebar, then ask questions below.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input(
    "Ask a question about the uploaded documents…",
    disabled=not st.session_state.get("files_ready", False),
)

if not st.session_state.get("files_ready", False):
    st.info("Upload and index documents (PDF or TXT) to enable questions.")

if prompt:
    handle_chat_prompt(prompt, client, model_name, store_name)
