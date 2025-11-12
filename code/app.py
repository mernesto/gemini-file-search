"""Streamlit app for Gemini File Search.

This includes core functionality:
- Upload and index files (PDF or TXT) with periodic status updates every 10 seconds
- Clear the store
- Chat with the indexed documents

"""

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
    document_exists,
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
    """Upload files (PDF or TXT) with periodic status updates and show final status.

    Args:
        files: List of uploaded file objects.
        skip_duplicates: If True, skip files that already exist in the store.
                         If False, upload anyway (creating duplicates).
    """
    if not files:
        st.sidebar.warning("No files selected.")
        st.session_state.files_ready = False
        return

    successes = 0
    failures = 0
    skipped = 0

    for uploaded_file in files:
        # Create a status container for this file
        file_container = st.sidebar.container()
        size_mb = uploaded_file.size / (1024 * 1024) if uploaded_file.size else 0
        file_container.markdown(f"**{uploaded_file.name}** · {size_mb:.2f} MB")

        # Check for duplicate before uploading
        existing_doc = document_exists(client, store_name, uploaded_file.name)

        if existing_doc and skip_duplicates:
            # Document already exists - skip it
            file_container.warning(
                f"⏭️ **{uploaded_file.name}** - Already exists in store (skipped to avoid duplicate)"
            )
            skipped += 1
            continue

        # Create a status area that will show updates
        # Note: Streamlit updates won't appear in real-time during blocking operations,
        # but we'll accumulate messages and display them when the operation completes
        status_messages = []
        status_display = file_container.empty()

        # Create a status callback that tracks elapsed time
        def create_status_callback(messages_list, display_area):
            """Create a callback that tracks status updates."""

            def status_update(elapsed_seconds: float) -> None:
                # Add the status message to our list
                message = f"⏳ Still processing... ({elapsed_seconds:.0f}s elapsed)"
                messages_list.append(message)
                # Try to update the display (may not show until operation completes)
                # We'll display all messages at the end

            return status_update

        status_callback = create_status_callback(status_messages, status_display)

        # Show initial status immediately
        status_display.info("⏳ Starting upload and indexing...")

        # Upload the file with status callback
        upload_start = time.time()
        result: UploadResult = upload_single_file(
            client, store_name, uploaded_file, status_callback=status_callback
        )
        upload_elapsed = time.time() - upload_start

        # IMPORTANT: Streamlit doesn't show UI updates in real-time during blocking operations.
        # All updates will be visible when the operation completes.

        # Display all accumulated status messages when operation completes
        if status_messages:
            # Show the full status history with all periodic updates
            all_messages = ["⏳ Starting upload and indexing..."] + status_messages
            # Add a final status if we have updates
            if status_messages:
                all_messages.append(f"✅ Completed in {upload_elapsed:.1f}s")
            status_text = "\n\n".join(all_messages)
            # Use markdown for better formatting
            status_display.markdown(f"**Status History:**\n\n{status_text}")
        else:
            # If completed quickly (before first 10s callback), show completion message
            if upload_elapsed < 10:
                status_display.success(f"✅ Completed quickly in {upload_elapsed:.1f}s")
            else:
                status_display.info(f"⏳ Processing completed in {upload_elapsed:.1f}s")

        # Show final result (this appears as a separate message)
        if result.success:
            successes += 1
            file_container.success(
                f"✅ **{uploaded_file.name}** - uploaded and indexed successfully"
            )
        else:
            failures += 1
            file_container.error(
                f"❌ **{uploaded_file.name}** - {result.error_message}"
            )

    # Show summary
    if successes > 0:
        st.session_state.files_ready = True
        summary_parts = [f"✅ {successes} succeeded"]
        if failures > 0:
            summary_parts.append(f"❌ {failures} failed")
        if skipped > 0:
            summary_parts.append(f"⏭️ {skipped} skipped (duplicates)")
        st.sidebar.info(f"Upload complete: {', '.join(summary_parts)}")
        # Refresh to show updated document list in sidebar
        st.rerun()
    else:
        if skipped > 0 and failures == 0:
            # All files were skipped (duplicates)
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

    if result.removed > 0:
        st.sidebar.success(f"Store cleared: {result.removed} document(s) removed")
    elif result.errors:
        st.sidebar.error(f"Errors: {', '.join(result.errors)}")
    else:
        st.sidebar.info("Store is already empty")

    # Refresh the page to update the document list (files_ready will be set to False automatically)
    st.rerun()

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
