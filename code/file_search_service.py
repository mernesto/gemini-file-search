"""logic for Gemini File Search service."""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types


@dataclass
class UploadResult:
    """Result of uploading a single file."""

    file_name: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class ClearStoreResult:
    """Result of clearing a store."""

    deleted: bool = False
    errors: list[str] = None


def get_or_create_store(client: genai.Client, display_name: str) -> str:
    """Return the store name matching display_name or create it."""
    stores = client.file_search_stores.list()
    for store in stores:
        if store.display_name == display_name:
            return store.name

    created = client.file_search_stores.create(config={"display_name": display_name})
    return created.name


@dataclass
class DocumentInfo:
    """Information about a document in the store."""

    name: str
    display_name: str
    state: Optional[str] = None


def list_store_documents(client: genai.Client, store_name: str) -> list[DocumentInfo]:
    """List all documents in the specified file search store.

    Args:
        client: google-genai client instance.
        store_name: Fully qualified File Search store name.

    Returns:
        List of DocumentInfo objects describing each document in the store.
    """
    documents = []
    try:
        for doc in client.file_search_stores.documents.list(parent=store_name):
            documents.append(
                DocumentInfo(
                    name=getattr(doc, "name", ""),
                    display_name=getattr(doc, "display_name", "Unknown"),
                    state=str(getattr(doc, "state", "UNKNOWN")),
                )
            )
    except Exception:
        # If listing fails, return empty list
        pass

    return documents


def document_exists(
    client: genai.Client, store_name: str, display_name: str
) -> Optional[DocumentInfo]:
    """Check if a document with the given display name already exists in the store.

    Args:
        client: google-genai client instance.
        store_name: Fully qualified File Search store name.
        display_name: Display name of the document to check for.

    Returns:
        DocumentInfo if a document with the same display_name exists, None otherwise.
    """
    try:
        for doc in client.file_search_stores.documents.list(parent=store_name):
            if getattr(doc, "display_name", "") == display_name:
                return DocumentInfo(
                    name=getattr(doc, "name", ""),
                    display_name=getattr(doc, "display_name", "Unknown"),
                    state=str(getattr(doc, "state", "UNKNOWN")),
                )
    except Exception:
        pass

    return None


def _detect_mime_type(file_name: str, provided_type: Optional[str] = None) -> str:
    """Detect MIME type from file name or use provided type.

    Args:
        file_name: Name of the file (used to detect extension).
        provided_type: MIME type provided by the upload (if any).

    Returns:
        MIME type string (application/pdf, text/plain, etc.).
    """
    if provided_type:
        return provided_type

    # Detect MIME type from file extension
    file_ext = os.path.splitext(file_name)[1].lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".text": "text/plain",
    }

    return mime_types.get(file_ext, "application/octet-stream")


def upload_single_file(
    client: genai.Client,
    store_name: str,
    uploaded_file: Any,
    status_callback: Optional[Callable[[float], None]] = None,
) -> UploadResult:
    """Upload a single file (PDF or TXT) to the File Search store.

    Args:
        client: google-genai client instance.
        store_name: Fully qualified File Search store name.
        uploaded_file: Streamlit uploaded file object (PDF or TXT).
        status_callback: Optional callback function that receives elapsed seconds.
                        Called every 10 seconds during indexing to provide status updates.

    Returns:
        UploadResult with success status.
    """
    tmp_path: Optional[str] = None
    staged_file_name: Optional[str] = None

    try:
        # Save uploaded file to temporary location
        suffix = os.path.splitext(uploaded_file.name)[1] or ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        # Detect MIME type
        mime_type = _detect_mime_type(uploaded_file.name, uploaded_file.type)

        # Try direct upload first
        try:
            operation = client.file_search_stores.upload_to_file_search_store(
                file=tmp_path,
                file_search_store_name=store_name,
                config={
                    "display_name": uploaded_file.name,
                    "mime_type": mime_type,
                },
            )
        except genai_errors.APIError:
            # Fallback to Files API import
            file_resource = client.files.upload(
                file=tmp_path,
                config=types.UploadFileConfig(
                    display_name=uploaded_file.name,
                    mime_type=mime_type,
                ),
            )
            staged_file_name = getattr(file_resource, "name", None)
            if not staged_file_name:
                return UploadResult(
                    file_name=uploaded_file.name,
                    success=False,
                    error_message="Files API did not return a resource name.",
                )

            operation = client.file_search_stores.import_file(
                file_search_store_name=store_name,
                file_name=staged_file_name,
            )

        # Poll until operation completes with exponential backoff.
        op_name = getattr(operation, "name", None)
        if not op_name:
            return UploadResult(
                file_name=uploaded_file.name,
                success=False,
                error_message="Operation has no name attribute.",
            )

        current = operation
        timeout_seconds = 15 * 60  # 15 minutes
        start_time = time.time()
        last_status_update = 0.0
        status_interval = 10.0  # Update every 10 seconds
        wait_time = 2  # Initial wait time in seconds
        max_wait_time = 32  # Maximum wait time in seconds

        while not getattr(current, "done", False):
            elapsed = time.time() - start_time

            # Check timeout
            if elapsed > timeout_seconds:
                return UploadResult(
                    file_name=uploaded_file.name,
                    success=False,
                    error_message=f"Indexing timed out after {timeout_seconds} seconds.",
                )

            # Call status callback every 10 seconds
            if status_callback and (elapsed - last_status_update >= status_interval):
                status_callback(elapsed)
                last_status_update = elapsed

            # Wait before polling again
            time.sleep(wait_time)

            # Exponentially increase wait time for the next poll, up to a maximum.
            # This avoids spamming the API with requests during long-running operations.
            wait_time = min(wait_time * 2, max_wait_time)

            current = client.operations.get(current)

        # Check if operation succeeded
        error = getattr(current, "error", None)
        if error:
            return UploadResult(
                file_name=uploaded_file.name,
                success=False,
                error_message=f"{getattr(error, 'code', 'UNKNOWN')} | {getattr(error, 'message', '')}",
            )

        # Verify document state if available
        response = getattr(current, "response", None)
        document_name = getattr(response, "document_name", None) if response else None
        if document_name:
            try:
                document = client.file_search_stores.documents.get(name=document_name)
                document_state = document.state
                if document_state == types.DocumentState.ACTIVE:
                    return UploadResult(file_name=uploaded_file.name, success=True)
                else:
                    return UploadResult(
                        file_name=uploaded_file.name,
                        success=False,
                        error_message=f"Document state: {document_state}",
                    )
            except Exception:
                # If we can't verify, assume success if no error
                pass

        # If we got here with no error, assume success
        return UploadResult(file_name=uploaded_file.name, success=True)

    except Exception as exc:
        return UploadResult(
            file_name=uploaded_file.name,
            success=False,
            error_message=str(exc),
        )

    finally:
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # Clean up staged file if used
        if staged_file_name:
            try:
                client.files.delete(name=staged_file_name)
            except Exception:
                pass


def delete_document(client: genai.Client, store_name: str, display_name: str) -> bool:
    """Delete a specific document from the store by display name.

    Args:
        client: google-genai client instance.
        store_name: Fully qualified File Search store name.
        display_name: Display name of the document to delete.

    Returns:
        True if the document was deleted, False otherwise.
    """
    try:
        for doc in client.file_search_stores.documents.list(parent=store_name):
            if getattr(doc, "display_name", "") == display_name:
                try:
                    client.file_search_stores.documents.delete(
                        name=doc.name, config={"force": True}
                    )
                    return True
                except Exception:
                    return False
    except Exception:
        pass

    return False


def clear_store(client: genai.Client, store_name: str) -> ClearStoreResult:
    """Delete the entire file search store.

    Args:
        client: google-genai client instance.
        store_name: Fully qualified File Search store name.

    Returns:
        ClearStoreResult indicating if the store was deleted.
    """
    try:
        client.file_search_stores.delete(name=store_name)
        return ClearStoreResult(deleted=True)
    except Exception as exc:
        return ClearStoreResult(deleted=False, errors=[str(exc)])
